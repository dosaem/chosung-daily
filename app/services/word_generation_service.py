"""LLM 단어 후보 생성 — 잔량이 부족한 언어의 `general` 후보를 만들어 승인 대기열에 올린다.

흐름: 프롬프트 → `app.clients.anthropic.generate_structured`(JSON 스키마) → pydantic
(모양) → `parse_word_input`(형식) → `word_rules`(후보 규칙) → DB 중복(단어 풀·기존
후보) → 통과는 `proposed`, 탈락은 `rejected` + 사유. 탈락 행도 남기는 이유: 배치별
통과율이 프롬프트 품질 지표다(README "설계 판단").

`book_title` 은 만들지 않는다 — LLM 은 없는 책을 지어내기 쉬워서(README "운영: 단어
CSV 업로드"), 책 제목은 `flask search-books` 로 실존 확인한 것만 넣는다.

이 모듈은 Celery 를 모른다. 재시도·락·예산·알림은 `app/tasks/llm.py` 가 두르고,
여기는 "한 번 생성해서 저장" 만 한다 — 테스트가 HTTP 경계 하나만 mock 하면 끝까지
돈다.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from flask import current_app
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from app.clients import anthropic
from app.errors import ValidationError
from app.extensions import db, get_redis
from app.models import (
    CandidateStatus,
    LlmCall,
    LlmCallResult,
    PuzzleLanguage,
    Word,
    WordCandidate,
    WordCategory,
)
from app.services import task_dispatch, word_rules
from app.services.operator_alert_service import notify_operator
from app.services.word_service import parse_word_input
from app.utils.time import utcnow

PURPOSE = "word_generation"
TASK_NAME = "tasks.generate_word_candidates"
# 심사 태스크 이름 — word_review_service 와 같은 값(순환 import 를 피하려고 여기 적는다).
REVIEW_TASK_NAME = "tasks.review_word_candidates"

# 언어별 중복 실행 방지 락. 생성 한 번이 2분을 넘지 않으니(클라이언트 타임아웃
# 120초) 10분이면 죽은 워커가 쥔 락도 풀린다.
LOCK_TTL_SECONDS = 600


# pydantic 이 모양을 보고, 글자 규칙은 word_rules 가 본다 — 길이 상한은 둘 다 두되
# 여기 것은 "말도 안 되게 긴 값" 만 거르는 느슨한 울타리다.
class CandidateItem(BaseModel):
    answer: str = Field(min_length=1, max_length=50)
    hint: str = Field(min_length=1, max_length=200)


class CandidateBatch(BaseModel):
    candidates: list[CandidateItem] = Field(min_length=1, max_length=200)


# 모델에 보내는 JSON 스키마. pydantic 모델과 같은 모양이어야 한다(`additionalProperties`
# 를 닫아야 구조화 출력이 받아들인다).
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "hint": {"type": "string"},
                },
                "required": ["answer", "hint"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

# README "운영: 단어 CSV 업로드" 의 프롬프트 골자를 그대로 옮겼다. 규칙 숫자는
# word_rules 의 상수를 끼워 넣어 프롬프트와 검증이 어긋나지 않게 한다.
_PROMPTS = {
    PuzzleLanguage.KO: (
        "너는 한국어 초성 퀴즈 출제자다. 플레이어는 초성만 보고 단어를 맞힌다.",
        "한국어 일상 단어 {count}개를 만들어라. 조건: {low}~{high}글자 명사, 초성만 보고 "
        "맞힐 수 있을 만큼 일상적인 말(인명·지명·브랜드·유행어 제외), 정답에 공백·숫자·"
        "기호·영문 없음, 힌트는 한 줄({hint_max}자 이내)이고 **정답 글자를 하나도 포함하지 "
        "않으며** 뜻·용도·분류로만 설명, 따옴표·쉼표 없음, 서로 중복 없음. 난이도는 "
        "쉬움·보통·어려움을 대략 4:4:2 로 섞어라. 이미 있는 단어는 피하라: {known}",
    ),
    PuzzleLanguage.EN: (
        "You write clues for a daily word game where vowels are hidden and players "
        "guess the word from its consonant skeleton.",
        "Produce {count} common English nouns. Rules: lowercase a-z only, {low}-{high} "
        "characters, at most one space or hyphen (two words max), no proper nouns, "
        "vowels must be at most half of the letters so the consonant skeleton is a real "
        "clue. The hint is one line (max {hint_max} characters), must not contain the "
        "answer or its plural, and describes meaning or use only; no quotes or commas; no "
        "duplicates. Mix difficulty roughly 4:4:2 easy:medium:hard. Avoid these existing "
        "words: {known}",
    ),
}


@dataclass
class GenerationResult:
    """생성 한 번의 결과 요약. 태스크 로그와 Slack 문구가 이걸 읽는다."""

    batch_id: str
    language: PuzzleLanguage
    requested: int
    proposed: int = 0
    rejected: int = 0
    reasons: list[str] = field(default_factory=list)
    cost_usd: Decimal = Decimal("0")

    @property
    def pass_rate(self) -> float:
        total = self.proposed + self.rejected
        return self.proposed / total if total else 0.0


@dataclass
class RunOutcome:
    """안전장치를 거친 실행 한 번의 결과. `skipped` 가 차 있으면 생성을 안 한 것이다."""

    language: PuzzleLanguage
    skipped: str | None = None
    result: GenerationResult | None = None


def run_generation(language: PuzzleLanguage, trigger: str = "schedule") -> RunOutcome:
    """안전장치(기능 플래그·락·대기열 상한·월 예산)를 거쳐 생성 한 번을 돌린다.

    LLM 호출 실패(`AnthropicError`)는 그대로 올린다 — 재시도·실패 알림은 Celery
    태스크(app/tasks/llm.py)가 한다. 여기서 알리는 건 "생성을 건너뛴 이유" 와
    "생성 결과" 뿐이다.
    """
    config = current_app.config
    if not config["LLM_WORD_GENERATION_ENABLED"]:
        return RunOutcome(language, skipped="기능 플래그 꺼짐 (LLM_WORD_GENERATION_ENABLED)")

    pending = pending_count(language)
    if pending >= config["LLM_MAX_PENDING_CANDIDATES"]:
        return RunOutcome(language, skipped=f"승인 대기 후보 {pending}개 — 먼저 승인/거절")

    spent = monthly_cost_usd(utcnow())
    budget = Decimal(str(config["LLM_MONTHLY_BUDGET_USD"]))
    if spent >= budget:
        notify_operator(
            "LLM 월 예산 도달",
            f"이번 달 ${spent} / 상한 ${budget} — {language.value} 후보 생성을 건너뜀",
            channel="alerts",
        )
        return RunOutcome(language, skipped=f"월 예산 도달 (${spent} / ${budget})")

    redis_client = get_redis()
    lock_key = f"llm:wordgen:{language.value}"
    if redis_client is not None and not redis_client.set(
        lock_key, trigger, nx=True, ex=LOCK_TTL_SECONDS
    ):
        return RunOutcome(language, skipped="같은 언어 생성이 이미 실행 중")

    try:
        result = generate_candidates(language, config["LLM_CANDIDATES_PER_CALL"])
    finally:
        if redis_client is not None:
            redis_client.delete(lock_key)

    # 2단계: LLM 심사관이 승인/거절까지 한다(설정으로 끌 수 있다). 생성 태스크 안에서
    # 바로 부르지 않고 큐에 넣는 이유: 심사 호출이 일시 오류로 재시도될 때 생성까지
    # 다시 돌아(= 과금) 가지 않게 — 심사 태스크는 배치 id 만 받아 멱등하게 돈다.
    review = config["LLM_REVIEW_ENABLED"] and result.proposed > 0
    if review:
        task_dispatch.enqueue_task(REVIEW_TASK_NAME, result.batch_id)

    notify_operator(
        "LLM 단어 후보 생성",
        f"{language.value} 후보 {result.proposed}개 생성 · 탈락 {result.rejected}개 "
        f"(통과율 {result.pass_rate:.0%}, ${result.cost_usd}) · "
        + (
            "LLM 심사 대기열에 넣음"
            if review
            else f"승인 대기 → {config.get('PUBLIC_BASE_URL', '')}/admin/candidates"
        ),
    )
    return RunOutcome(language, result=result)


def generate_candidates(language: PuzzleLanguage, count: int) -> GenerationResult:
    """언어 하나의 후보 `count`개를 LLM 에 요청해 검증·저장한다.

    호출 자체가 실패하면(`AnthropicError`) `llm_call` 에 실패 행을 남기고 예외를 그대로
    올린다 — 재시도 판단은 호출부(Celery 태스크)의 몫이다.
    """
    batch_id = uuid.uuid4().hex[:32]
    known = _known_answers(language)
    system, user_template = _PROMPTS[language]
    low, high = (
        word_rules.KO_ANSWER_RANGE if language is PuzzleLanguage.KO else word_rules.EN_ANSWER_RANGE
    )
    user = user_template.format(
        count=count,
        low=low,
        high=high,
        hint_max=word_rules.HINT_MAX_LENGTH,
        known=", ".join(sorted(known)[:300]) or "(없음)",
    )

    try:
        response = anthropic.generate_structured(system=system, user=user, schema=RESPONSE_SCHEMA)
    except anthropic.AnthropicError as err:
        _log_call(
            batch_id=batch_id,
            model=None,
            response=None,
            result=LlmCallResult.RETRIED if err.retryable else LlmCallResult.FAILURE,
            error=str(err)[:500],
        )
        db.session.commit()
        raise

    _log_call(
        batch_id=batch_id, model=response.model, response=response, result=LlmCallResult.SUCCESS
    )
    result = GenerationResult(batch_id, language, count, cost_usd=response.cost_usd)

    try:
        batch = CandidateBatch.model_validate(response.data)
    except PydanticValidationError as err:
        # 스키마를 지켰는데 pydantic 이 거부하는 건 빈 목록·과한 길이뿐이다. 호출은
        # 성공으로 남기고 후보 0개로 끝낸다 — 호출부가 "0개" 를 보고 알린다.
        result.reasons.append(f"응답 모양 오류: {err.errors()[0]['msg']}")
        db.session.commit()
        return result

    seen: dict[tuple[str, str, str], int] = {}
    for index, item in enumerate(batch.candidates, start=1):
        candidate, reasons = _validate(language, item, seen, known, index)
        candidate.batch_id = batch_id
        if reasons:
            candidate.status = CandidateStatus.REJECTED
            candidate.reject_reason = " / ".join(reasons)[:300]
            result.rejected += 1
            result.reasons.extend(reasons)
        else:
            candidate.status = CandidateStatus.PROPOSED
            result.proposed += 1
        db.session.add(candidate)

    db.session.commit()
    return result


def _validate(
    language: PuzzleLanguage,
    item: CandidateItem,
    seen: dict[tuple[str, str, str], int],
    known: set[str],
    index: int,
) -> tuple[WordCandidate, list[str]]:
    """후보 하나를 형식·규칙·중복 순서로 본다. 어느 단계에서 걸려도 행은 남긴다."""
    candidate = WordCandidate(
        language=language,
        category=WordCategory.GENERAL,
        answer=item.answer.strip()[:50],
        hint=item.hint.strip()[:200],
    )
    try:
        parsed = parse_word_input(
            language.value, WordCategory.GENERAL.value, item.answer, item.hint
        )
    except ValidationError as err:
        return candidate, [err.message]

    reasons = word_rules.candidate_reasons(parsed)
    known_keys = {(language.value, answer, WordCategory.GENERAL.value) for answer in known}
    reasons += word_rules.duplicate_reasons(parsed, seen, known_keys, index, "단어 풀")
    return candidate, reasons


def _known_answers(language: PuzzleLanguage) -> set[str]:
    """이미 퍼즐 풀에 있거나 승인 대기 중인 정답. 프롬프트에 "피하라" 로 넣고,
    그래도 겹치면 중복으로 탈락시킨다."""
    words = db.session.query(Word.answer).filter(
        Word.language == language, Word.category == WordCategory.GENERAL
    )
    pending = db.session.query(WordCandidate.answer).filter(
        WordCandidate.language == language,
        WordCandidate.status.in_([CandidateStatus.PROPOSED, CandidateStatus.APPROVED]),
    )
    return {row[0] for row in words} | {row[0] for row in pending}


def _log_call(
    *,
    batch_id: str,
    model: str | None,
    response: anthropic.StructuredResponse | None,
    result: LlmCallResult,
    error: str | None = None,
) -> None:
    db.session.add(
        LlmCall(
            purpose=PURPOSE,
            model=model or current_app.config["LLM_MODEL"],
            input_tokens=response.input_tokens if response else 0,
            output_tokens=response.output_tokens if response else 0,
            cost_usd=response.cost_usd if response else Decimal("0"),
            latency_ms=response.latency_ms if response else 0,
            result=result,
            error=error,
            batch_id=batch_id,
        )
    )


def monthly_cost_usd(now: datetime) -> Decimal:
    """이번 달(UTC) 호출 비용 합. 월 예산 판정이 쓴다."""
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.session.query(db.func.coalesce(db.func.sum(LlmCall.cost_usd), 0))
        .filter(LlmCall.created_at >= month_start)
        .scalar()
    )
    return Decimal(str(total))


def pending_count(language: PuzzleLanguage) -> int:
    return (
        db.session.query(db.func.count(WordCandidate.id))
        .filter(
            WordCandidate.language == language,
            WordCandidate.status == CandidateStatus.PROPOSED,
        )
        .scalar()
    )
