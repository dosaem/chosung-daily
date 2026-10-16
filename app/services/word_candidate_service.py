"""LLM 단어 후보의 승인·거절(LLM 출제 파이프라인, 사람 검수 단계).

후보는 LLM 이 만들고 **운영자가 승인해야** `word` 가 된다 — 승인은 기존
`word_service.create_word` 를 그대로 타서, 손으로 추가한 단어와 같은 검증(길이·
문자 규칙·중복)과 같은 가림 계산을 받는다. 이 모듈은 상태 전이만 안다.
"""

from dataclasses import dataclass, field

from flask import g

from app.errors import ValidationError
from app.extensions import db
from app.models import CandidateStatus, PuzzleLanguage, WordCandidate
from app.services import word_service
from app.utils.time import utcnow

DEFAULT_REJECT_REASON = "운영자 거절"


@dataclass
class ReviewResult:
    approved: list[WordCandidate] = field(default_factory=list)
    rejected: list[WordCandidate] = field(default_factory=list)
    # (후보, 사유) — 승인하려 했지만 단어 규칙·중복에 걸려 거절로 돌린 것.
    failed: list[tuple[WordCandidate, str]] = field(default_factory=list)


def list_pending(language: PuzzleLanguage | None = None) -> list[WordCandidate]:
    query = WordCandidate.query.filter(WordCandidate.status == CandidateStatus.PROPOSED)
    if language is not None:
        query = query.filter(WordCandidate.language == language)
    # 같은 배치끼리 묶여 보이게 배치 → 생성 순. 운영자는 배치 단위로 훑는다.
    return query.order_by(WordCandidate.batch_id, WordCandidate.id).all()


def pending_counts() -> dict[PuzzleLanguage, int]:
    rows = (
        db.session.query(WordCandidate.language, db.func.count(WordCandidate.id))
        .filter(WordCandidate.status == CandidateStatus.PROPOSED)
        .group_by(WordCandidate.language)
        .all()
    )
    counts = dict.fromkeys(PuzzleLanguage, 0)
    counts.update(dict(rows))
    return counts


def approve(candidate_ids: list[int], hints: dict[int, str]) -> ReviewResult:
    """고른 후보를 단어로 만든다. `hints` 에 있는 후보는 운영자가 고친 힌트로 저장한다.

    한 후보가 실패해도(승인 사이에 같은 단어가 손으로 추가된 경우 등) 나머지는 계속
    간다 — 실패한 후보는 `rejected` 로 돌리고 사유를 남겨 운영자가 표에서 본다.
    `create_word` 가 후보마다 커밋하므로 성공한 승인은 뒤의 실패에 휩쓸리지 않는다.
    """
    result = ReviewResult()
    for candidate in _pending_by_ids(candidate_ids):
        hint = hints.get(candidate.id, candidate.hint)
        try:
            word = word_service.create_word(
                candidate.language.value, candidate.category.value, candidate.answer, hint
            )
        except ValidationError as err:
            db.session.rollback()
            _mark(candidate, CandidateStatus.REJECTED, reason=err.message)
            result.failed.append((candidate, err.message))
            continue
        candidate.hint = hint
        candidate.word_id = word.id
        _mark(candidate, CandidateStatus.APPROVED)
        result.approved.append(candidate)
    db.session.commit()
    return result


def reject(candidate_ids: list[int], reason: str | None) -> ReviewResult:
    result = ReviewResult()
    for candidate in _pending_by_ids(candidate_ids):
        _mark(candidate, CandidateStatus.REJECTED, reason=reason or DEFAULT_REJECT_REASON)
        result.rejected.append(candidate)
    db.session.commit()
    return result


def _pending_by_ids(candidate_ids: list[int]) -> list[WordCandidate]:
    """승인 대기 중인 것만 — 다른 탭에서 이미 처리한 후보를 두 번 처리하지 않는다."""
    if not candidate_ids:
        return []
    return (
        WordCandidate.query.filter(
            WordCandidate.id.in_(candidate_ids),
            WordCandidate.status == CandidateStatus.PROPOSED,
        )
        .order_by(WordCandidate.id)
        .all()
    )


def _mark(candidate: WordCandidate, status: CandidateStatus, reason: str | None = None) -> None:
    candidate.status = status
    candidate.reject_reason = reason
    candidate.reviewed_by = getattr(g, "admin_email", None)
    candidate.reviewed_at = utcnow()
