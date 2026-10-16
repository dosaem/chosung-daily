"""Anthropic Messages API 래퍼 — 외부 호출 한 곳(README "01. 외부 호출 래퍼와 도메인
판정 함수의 분리", google_books.py 와 같은 층).

이 모듈이 아는 건 "HTTP 로 어떻게 묻고 무엇이 돌아오나" 뿐이다. 프롬프트를 짜고
결과를 단어 후보로 바꾸는 건 `app/services/word_generation_service.py` 가 한다.
SDK 대신 `requests` 를 쓴 이유: 호출이 한 모양(구조화 출력 한 번)뿐이고, 테스트가
mock 할 경계를 HTTP 한 곳으로 좁히기 위해서다(다른 외부 호출과 같은 방식).

구조화 출력은 `output_config.format`(json_schema)으로 받는다 — 이 프로젝트가 쓰는
Claude Sonnet 5.5 는 `tool_choice` 로 도구를 강제하는 방식을 거부한다(400).

단가표는 Claude API 문서(2026-10 기준, USD / 1M 토큰)에서 옮겨 적은 값이다. 호출
시점에 비용을 계산해 `llm_call.cost_usd` 로 굳힌다 — 표가 바뀌면 이 상수만 고친다.
"""

import json
import time
from dataclasses import dataclass
from decimal import Decimal
from http import HTTPStatus

import requests
from flask import current_app

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# 생성 한 번이 40개 후보를 JSON 으로 쓰는 정도라 길지 않지만, 모델이 생각하는 시간이
# 있어서 운영자 폼 호출(5초)보다 넉넉히 둔다. Celery 태스크 안에서만 부른다.
TIMEOUT_SECONDS = 120

# USD / 1M 토큰 (input, output). 출처: Claude API 문서 모델 표(2026-10).
PRICE_PER_MILLION_USD: dict[str, tuple[Decimal, Decimal]] = {
    "claude-sonnet-5-5": (Decimal("2.00"), Decimal("10.00")),
    "claude-opus-5-5": (Decimal("4.00"), Decimal("20.00")),
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
}


class AnthropicError(Exception):
    """래퍼가 던지는 예외의 공통 조상. `retryable` 로 재시도 여부를 가른다."""

    retryable = False

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class AnthropicConfigError(AnthropicError):
    """키·모델·요청 모양이 잘못됐다(4xx, 429 제외). 다시 보내도 같은 답이다."""


class AnthropicTransientError(AnthropicError):
    """429·5xx·타임아웃·연결 끊김. 잠시 뒤 다시 보낼 수 있다."""

    retryable = True


@dataclass(frozen=True)
class StructuredResponse:
    """구조화 출력 호출 한 번의 결과. `data` 는 스키마대로 파싱된 JSON 이다."""

    data: dict
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """호출 한 건의 비용. 단가표에 없는 모델은 0 으로 적되 조용히 넘기지 않고
    호출부 로그에 남게 `model` 을 그대로 돌려준다(장부의 model 열로 추적)."""
    prices = PRICE_PER_MILLION_USD.get(model)
    if prices is None:
        return Decimal("0")
    input_price, output_price = prices
    million = Decimal(1_000_000)
    cost = (Decimal(input_tokens) * input_price + Decimal(output_tokens) * output_price) / million
    return cost.quantize(Decimal("0.000001"))


def generate_structured(
    *, system: str, user: str, schema: dict, max_tokens: int = 8000, model: str | None = None
) -> StructuredResponse:
    """시스템·사용자 프롬프트를 보내고 `schema` 모양의 JSON 하나를 받는다.

    `model` 을 주지 않으면 설정의 `LLM_MODEL`. 심사는 생성과 다른 모델을 쓸 수 있다.
    """
    api_key = current_app.config["ANTHROPIC_API_KEY"]
    if not api_key:
        raise AnthropicConfigError("ANTHROPIC_API_KEY 가 비어 있습니다.")
    model = model or current_app.config["LLM_MODEL"]

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
        "output_config": {"format": {"type": "json_schema", "schema": schema}},
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }

    started = time.monotonic()
    try:
        response = requests.post(MESSAGES_URL, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.Timeout as err:
        raise AnthropicTransientError(f"timeout after {TIMEOUT_SECONDS}s") from err
    except requests.ConnectionError as err:
        raise AnthropicTransientError(f"connection error: {err}") from err
    latency_ms = int((time.monotonic() - started) * 1000)

    status = response.status_code
    if status == HTTPStatus.TOO_MANY_REQUESTS or status >= HTTPStatus.INTERNAL_SERVER_ERROR:
        raise AnthropicTransientError(
            f"HTTP {response.status_code}: {_error_message(response)}", response.status_code
        )
    if status >= HTTPStatus.BAD_REQUEST:
        raise AnthropicConfigError(
            f"HTTP {response.status_code}: {_error_message(response)}", response.status_code
        )

    payload = response.json()
    if payload.get("stop_reason") == "refusal":
        raise AnthropicConfigError("모델이 요청을 거부했습니다 (stop_reason=refusal).")
    text = next(
        (
            block.get("text", "")
            for block in payload.get("content", [])
            if block.get("type") == "text"
        ),
        "",
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise AnthropicTransientError(f"응답이 JSON 이 아닙니다: {err}") from err

    usage = payload.get("usage", {})
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    return StructuredResponse(
        data=data,
        model=payload.get("model", model),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_cost_usd(model, input_tokens, output_tokens),
        latency_ms=latency_ms,
    )


def _error_message(response: requests.Response) -> str:
    try:
        return response.json().get("error", {}).get("message", response.text[:200])
    except ValueError:
        return response.text[:200]
