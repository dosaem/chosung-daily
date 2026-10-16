"""LLM 단어 후보 생성 — HTTP 경계(`requests.post`) 하나만 mock 하고 나머지는 실제
MySQL·Redis 로 돈다. 모델 응답은 Anthropic Messages API 의 실제 모양(content[0].text 에
JSON, usage 에 토큰)으로 꾸민다."""

import json
from decimal import Decimal

import pytest
import requests

from app.clients import anthropic
from app.extensions import db, get_redis
from app.models import CandidateStatus, LlmCall, LlmCallResult, PuzzleLanguage, Word, WordCandidate
from app.services import operator_alert_service
from app.services import word_generation_service as svc
from app.utils.time import utcnow


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def messages_payload(candidates: list[dict], model="claude-sonnet-5-5", in_tok=1200, out_tok=800):
    return {
        "model": model,
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps({"candidates": candidates})}],
        "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
    }


@pytest.fixture
def llm_app(app):
    app.config["ANTHROPIC_API_KEY"] = "test-key"
    app.config["LLM_MODEL"] = "claude-sonnet-5-5"
    return app


@pytest.fixture
def post_calls(monkeypatch):
    """requests.post 를 가로채 보낸 요청을 기록하고 미리 정한 응답을 돌려준다."""
    calls = []
    responses = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    calls_holder = {"calls": calls, "responses": responses}
    return calls_holder


def test_valid_candidates_become_proposed_and_rule_failures_are_rejected_with_reasons(
    llm_app, post_calls
):
    db.session.add(Word(language=PuzzleLanguage.KO, answer="사과", category="general", hint="과일"))
    db.session.commit()
    post_calls["responses"].append(
        FakeResponse(
            200,
            messages_payload(
                [
                    {"answer": "책상", "hint": "공부할 때 앞에 두는 가구"},
                    {"answer": "의자", "hint": "의자에 앉는다"},  # 힌트에 정답 음절
                    {"answer": "사과", "hint": "빨갛고 아삭한 과일"},  # 단어 풀 중복
                    {"answer": "책상", "hint": "책을 올려두는 가구"},  # 같은 배치 중복
                    {"answer": "a", "hint": "영문"},  # 완성형 한글 아님 + 길이
                ]
            ),
        )
    )

    result = svc.generate_candidates(PuzzleLanguage.KO, count=5)

    assert (result.proposed, result.rejected) == (1, 4)
    assert result.pass_rate == pytest.approx(0.2)
    rows = {c.answer + "/" + c.hint: c for c in WordCandidate.query.all()}
    assert rows["책상/공부할 때 앞에 두는 가구"].status is CandidateStatus.PROPOSED
    assert "정답 음절" in rows["의자/의자에 앉는다"].reject_reason
    assert "단어 풀 에 이미 있는" in rows["사과/빨갛고 아삭한 과일"].reject_reason
    assert "같은 파일 안에서 중복" in rows["책상/책을 올려두는 가구"].reject_reason
    assert "완성형 한글" in rows["a/영문"].reject_reason
    assert all(c.batch_id == result.batch_id for c in rows.values())


def test_request_uses_structured_output_and_logs_tokens_cost_and_latency(llm_app, post_calls):
    post_calls["responses"].append(
        FakeResponse(
            200, messages_payload([{"answer": "책상", "hint": "가구"}], in_tok=1000, out_tok=500)
        )
    )

    svc.generate_candidates(PuzzleLanguage.KO, count=1)

    sent = post_calls["calls"][0]
    assert sent["url"] == anthropic.MESSAGES_URL
    assert sent["headers"]["x-api-key"] == "test-key"
    assert sent["json"]["model"] == "claude-sonnet-5-5"
    assert sent["json"]["output_config"]["format"]["type"] == "json_schema"
    assert "tool_choice" not in sent["json"]
    assert (
        "사과" not in sent["json"]["messages"][0]["content"]
    )  # 풀이 비어 있으니 '피하라' 목록 없음

    call = LlmCall.query.one()
    assert (call.purpose, call.result) == ("word_generation", LlmCallResult.SUCCESS)
    assert (call.input_tokens, call.output_tokens) == (1000, 500)
    # $2/1M 입력 + $10/1M 출력: 1000*2e-6 + 500*1e-5 = 0.007
    assert call.cost_usd == Decimal("0.007000")
    assert call.latency_ms >= 0
    assert call.batch_id is not None


def test_known_answers_are_sent_as_avoid_list(llm_app, post_calls):
    db.session.add(
        Word(language=PuzzleLanguage.EN, answer="apple", category="general", hint="fruit")
    )
    db.session.commit()
    post_calls["responses"].append(
        FakeResponse(200, messages_payload([{"answer": "window", "hint": "an opening in a wall"}]))
    )

    svc.generate_candidates(PuzzleLanguage.EN, count=1)

    assert "apple" in post_calls["calls"][0]["json"]["messages"][0]["content"]


@pytest.mark.parametrize(
    ("response", "exc_type", "logged_result"),
    [
        (
            FakeResponse(429, {"error": {"message": "rate limited"}}),
            anthropic.AnthropicTransientError,
            LlmCallResult.RETRIED,
        ),
        (
            FakeResponse(503, {"error": {"message": "overloaded"}}),
            anthropic.AnthropicTransientError,
            LlmCallResult.RETRIED,
        ),
        (requests.Timeout(), anthropic.AnthropicTransientError, LlmCallResult.RETRIED),
        (
            FakeResponse(401, {"error": {"message": "bad key"}}),
            anthropic.AnthropicConfigError,
            LlmCallResult.FAILURE,
        ),
        (
            FakeResponse(400, {"error": {"message": "bad schema"}}),
            anthropic.AnthropicConfigError,
            LlmCallResult.FAILURE,
        ),
    ],
)
def test_transient_errors_are_retryable_and_config_errors_are_not(
    llm_app, post_calls, response, exc_type, logged_result
):
    post_calls["responses"].append(response)

    with pytest.raises(exc_type):
        svc.generate_candidates(PuzzleLanguage.KO, count=3)

    call = LlmCall.query.one()
    assert call.result is logged_result
    assert call.error
    assert WordCandidate.query.count() == 0


def test_missing_api_key_is_a_config_error_without_any_http_call(app, post_calls):
    app.config["ANTHROPIC_API_KEY"] = ""

    with pytest.raises(anthropic.AnthropicConfigError):
        svc.generate_candidates(PuzzleLanguage.KO, count=3)

    assert post_calls["calls"] == []


def test_refusal_is_a_config_error(llm_app, post_calls):
    post_calls["responses"].append(
        FakeResponse(200, {"model": "m", "stop_reason": "refusal", "content": [], "usage": {}})
    )

    with pytest.raises(anthropic.AnthropicConfigError):
        svc.generate_candidates(PuzzleLanguage.KO, count=3)


def test_monthly_cost_and_pending_count_read_the_ledger(llm_app, post_calls):
    post_calls["responses"].append(
        FakeResponse(
            200, messages_payload([{"answer": "책상", "hint": "가구"}], in_tok=1000, out_tok=500)
        )
    )
    svc.generate_candidates(PuzzleLanguage.KO, count=1)

    assert svc.monthly_cost_usd(utcnow()) == Decimal("0.007000")
    assert svc.pending_count(PuzzleLanguage.KO) == 1
    assert svc.pending_count(PuzzleLanguage.EN) == 0


# --- 안전장치(run_generation) -------------------------------------------


@pytest.fixture
def operator_alerts(monkeypatch):
    messages = []
    monkeypatch.setattr(
        operator_alert_service, "post_webhook_message", lambda text: messages.append(text) or True
    )
    return messages


@pytest.fixture
def enabled_app(llm_app):
    llm_app.config["LLM_WORD_GENERATION_ENABLED"] = True
    llm_app.config["LLM_MAX_PENDING_CANDIDATES"] = 3
    llm_app.config["LLM_MONTHLY_BUDGET_USD"] = 1.0
    llm_app.config["LLM_CANDIDATES_PER_CALL"] = 2
    return llm_app


def test_feature_flag_off_skips_without_calling_the_api(llm_app, post_calls, operator_alerts):
    llm_app.config["LLM_WORD_GENERATION_ENABLED"] = False

    outcome = svc.run_generation(PuzzleLanguage.KO)

    assert "기능 플래그" in outcome.skipped
    assert post_calls["calls"] == []
    assert operator_alerts == []


def test_generation_runs_and_reports_to_slack(enabled_app, post_calls, operator_alerts):
    post_calls["responses"].append(
        FakeResponse(
            200,
            messages_payload(
                [{"answer": "책상", "hint": "가구"}, {"answer": "의자", "hint": "의자 아님"}]
            ),
        )
    )

    outcome = svc.run_generation(PuzzleLanguage.KO, trigger="admin")

    assert outcome.skipped is None
    assert (outcome.result.proposed, outcome.result.rejected) == (1, 1)
    assert post_calls["calls"][0]["json"]["messages"][0]["content"].startswith(
        "한국어 일상 단어 2개"
    )
    assert len(operator_alerts) == 1
    assert "ko 후보 1개 생성 · 탈락 1개 (통과율 50%" in operator_alerts[0]
    assert "/admin/candidates" in operator_alerts[0]


def test_too_many_pending_candidates_skip_generation(enabled_app, post_calls, operator_alerts):
    db.session.add_all(
        WordCandidate(
            language=PuzzleLanguage.KO,
            category="general",
            answer=f"후보{i}",
            hint="h",
            status=CandidateStatus.PROPOSED,
            batch_id="b",
        )
        for i in range(3)
    )
    db.session.commit()

    outcome = svc.run_generation(PuzzleLanguage.KO)

    assert "승인 대기 후보 3개" in outcome.skipped
    assert post_calls["calls"] == []


def test_monthly_budget_reached_skips_and_alerts(enabled_app, post_calls, operator_alerts):
    db.session.add(
        LlmCall(
            purpose="word_generation",
            model="claude-sonnet-5-5",
            cost_usd=Decimal("1.25"),
            result=LlmCallResult.SUCCESS,
        )
    )
    db.session.commit()

    outcome = svc.run_generation(PuzzleLanguage.EN)

    assert "월 예산 도달" in outcome.skipped
    assert post_calls["calls"] == []
    assert "LLM 월 예산 도달" in operator_alerts[0]


def test_language_lock_prevents_concurrent_runs_and_is_released_after(
    enabled_app, post_calls, operator_alerts
):
    get_redis().set("llm:wordgen:ko", "other-worker", nx=True, ex=60)
    assert "이미 실행 중" in svc.run_generation(PuzzleLanguage.KO).skipped
    assert post_calls["calls"] == []

    get_redis().delete("llm:wordgen:ko")
    post_calls["responses"].append(
        FakeResponse(200, messages_payload([{"answer": "책상", "hint": "가구"}]))
    )
    assert svc.run_generation(PuzzleLanguage.KO).skipped is None
    assert get_redis().get("llm:wordgen:ko") is None  # 끝나면 락 해제


def test_lock_is_released_when_the_api_call_fails(enabled_app, post_calls, operator_alerts):
    post_calls["responses"].append(FakeResponse(503, {"error": {"message": "down"}}))
    with pytest.raises(anthropic.AnthropicTransientError):
        svc.run_generation(PuzzleLanguage.KO)
    assert get_redis().get("llm:wordgen:ko") is None
