"""LLM 심사관 — 생성된 후보 배치를 한 번 더 보고 승인/거절까지 한다(LLM 출제 파이프라인 2단계).

생성(`word_generation_service`)은 "그럴듯한 단어를 많이" 만드는 쪽으로 기울고, 규칙
(`word_rules`)은 형식만 본다. 그 사이의 빈칸 — 실제로 쓰는 말인가, 힌트가 정확한가,
아이들이 봐도 되는가, 초성만 보고 맞힐 만한가 — 을 심사관 프롬프트가 본다. 승인은
운영자 승인과 **같은 경로**(`word_candidate_service.approve` → `create_word`)를 타서
같은 검증·가림 계산을 받고, 심사관 이름은 `llm:<모델>` 로 남는다.

심사관이 힌트를 고쳐 주면 고친 힌트도 규칙을 통과해야 쓴다 — 아니면 원래 힌트.
판정이 안 온 후보는 그대로 승인 대기로 남아 운영자가 본다(조용히 버리지 않는다).
"""

from dataclasses import dataclass, field
from decimal import Decimal

from flask import current_app
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from app.clients import anthropic
from app.errors import ValidationError
from app.extensions import db
from app.models import CandidateStatus, LlmCall, LlmCallResult, PuzzleLanguage, WordCandidate
from app.services import word_candidate_service, word_rules
from app.services.operator_alert_service import notify_operator
from app.services.word_service import parse_word_input

PURPOSE = "word_review"
TASK_NAME = "tasks.review_word_candidates"


class Verdict(BaseModel):
    id: int
    verdict: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=1, max_length=200)
    hint: str | None = Field(default=None, max_length=200)


class VerdictBatch(BaseModel):
    verdicts: list[Verdict] = Field(min_length=1, max_length=300)


RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["approve", "reject"]},
                    "reason": {"type": "string"},
                    "hint": {"type": "string"},
                },
                "required": ["id", "verdict", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

_PROMPTS = {
    PuzzleLanguage.KO: (
        "너는 한국어 초성 퀴즈의 출제 심사위원이다. 후보 단어와 힌트를 하나씩 엄격하게 심사한다.",
        "아래 후보를 심사해라. 각 후보에 approve 또는 reject 와 한 줄 사유를 적어라.\n"
        "reject 기준: 표준국어대사전에 없거나 일상에서 잘 안 쓰는 말, 고유명사·브랜드·유행어·"
        "비속어·차별적 표현, 힌트가 틀리거나 다른 단어로도 해석되는 힌트, 힌트에 정답 글자가 "
        "들어간 경우, 초성만으로 맞히기엔 너무 전문적인 말. 힌트가 조금만 고치면 되면 "
        "approve 하고 hint 에 고친 힌트({hint_max}자 이내, 정답 글자 없이)를 넣어라.\n"
        "후보 목록 (id | 정답 | 힌트):\n{items}",
    ),
    PuzzleLanguage.EN: (
        "You are the review judge for a daily English word game where vowels are hidden. "
        "Review each candidate word and clue strictly.",
        "Review the candidates below. For each, give approve or reject with a one-line reason.\n"
        "Reject when: not a common everyday English word, a proper noun/brand/slang/offensive "
        "term, the clue is wrong or fits other words better, the clue contains the answer or "
        "its plural, or the word is too technical to guess from consonants. If the clue only "
        "needs a small fix, approve and put the fixed clue in hint (max {hint_max} chars, "
        "without the answer).\n"
        "Candidates (id | answer | hint):\n{items}",
    ),
}


@dataclass
class ReviewOutcome:
    batch_id: str
    language: PuzzleLanguage | None = None
    skipped: str | None = None
    reviewed: int = 0
    approved: int = 0
    rejected: int = 0
    # 심사관이 판정을 안 줬거나 승인 중 중복 등으로 실패 → 운영자 몫으로 남은 수
    left_for_operator: int = 0
    cost_usd: Decimal = Decimal("0")
    reasons: list[str] = field(default_factory=list)


def review_batch(batch_id: str) -> ReviewOutcome:
    """배치 하나의 승인 대기 후보를 심사해 승인/거절한다. 호출 실패는 그대로 올린다."""
    config = current_app.config
    outcome = ReviewOutcome(batch_id)
    if not config["LLM_REVIEW_ENABLED"]:
        outcome.skipped = "심사 꺼짐 (LLM_REVIEW_ENABLED)"
        return outcome

    pending = (
        WordCandidate.query.filter(
            WordCandidate.batch_id == batch_id,
            WordCandidate.status == CandidateStatus.PROPOSED,
        )
        .order_by(WordCandidate.id)
        .all()
    )
    if not pending:
        outcome.skipped = "심사할 후보 없음"
        return outcome

    language = pending[0].language
    outcome.language = language
    model = config["LLM_REVIEW_MODEL"] or config["LLM_MODEL"]
    system, user_template = _PROMPTS[language]
    user = user_template.format(
        hint_max=word_rules.HINT_MAX_LENGTH,
        items="\n".join(f"{c.id} | {c.answer} | {c.hint}" for c in pending),
    )

    try:
        response = anthropic.generate_structured(
            system=system, user=user, schema=RESPONSE_SCHEMA, model=model
        )
    except anthropic.AnthropicError as err:
        _log_call(
            batch_id=batch_id,
            model=model,
            response=None,
            result=LlmCallResult.RETRIED if err.retryable else LlmCallResult.FAILURE,
            error=str(err)[:500],
        )
        db.session.commit()
        raise

    _log_call(
        batch_id=batch_id, model=response.model, response=response, result=LlmCallResult.SUCCESS
    )
    outcome.cost_usd = response.cost_usd
    db.session.commit()

    try:
        batch = VerdictBatch.model_validate(response.data)
    except PydanticValidationError as err:
        outcome.reasons.append(f"응답 모양 오류: {err.errors()[0]['msg']}")
        outcome.left_for_operator = len(pending)
        return outcome

    _apply_verdicts(outcome, pending, batch.verdicts, reviewer=f"llm:{response.model}")
    return outcome


def _apply_verdicts(outcome, pending, verdicts, *, reviewer: str) -> None:
    by_id = {c.id: c for c in pending}
    approve_ids: list[int] = []
    hints: dict[int, str] = {}
    reject_reasons: dict[int, str] = {}
    for verdict in verdicts:
        candidate = by_id.get(verdict.id)
        if candidate is None:
            continue
        if verdict.verdict == "approve":
            approve_ids.append(candidate.id)
            fixed = _usable_hint(candidate, verdict.hint)
            if fixed:
                hints[candidate.id] = fixed
        else:
            reject_reasons[candidate.id] = f"LLM 심사 거절: {verdict.reason}"[:300]

    outcome.reviewed = len(set(approve_ids) | set(reject_reasons))
    approved = word_candidate_service.approve(approve_ids, hints, reviewer=reviewer)
    outcome.approved = len(approved.approved)
    for candidate, reason in approved.failed:
        outcome.reasons.append(f"{candidate.answer}: {reason}")
    # 거절 사유는 후보마다 달라서 하나씩 적는다.
    for cid, reason in reject_reasons.items():
        word_candidate_service.reject([cid], reason, reviewer=reviewer)
    outcome.rejected = len(reject_reasons) + len(approved.failed)
    outcome.left_for_operator = len(pending) - outcome.reviewed


def run_review(batch_id: str) -> ReviewOutcome:
    """심사 한 번 + Slack 요약. 재시도는 Celery 태스크 몫."""
    outcome = review_batch(batch_id)
    if outcome.skipped is None:
        lang = outcome.language.value if outcome.language else "?"
        notify_operator(
            "LLM 단어 후보 심사",
            f"{lang} 승인 {outcome.approved} · 거절 {outcome.rejected} · 보류 "
            f"{outcome.left_for_operator} (${outcome.cost_usd}) · 보류분은 "
            f"{current_app.config.get('PUBLIC_BASE_URL', '')}/admin/candidates",
        )
    return outcome


def _usable_hint(candidate: WordCandidate, hint: str | None) -> str | None:
    """심사관이 고친 힌트가 규칙을 통과하면 그 힌트, 아니면 None(원래 힌트 유지)."""
    if not hint or hint.strip() == candidate.hint:
        return None
    try:
        parsed = parse_word_input(
            candidate.language.value, candidate.category.value, candidate.answer, hint
        )
    except ValidationError:
        return None
    if word_rules.candidate_reasons(parsed):
        return None
    return parsed.hint


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
