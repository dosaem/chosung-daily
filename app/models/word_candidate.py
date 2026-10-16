from datetime import datetime

from app.extensions import db
from app.models.enums import CandidateStatus, PuzzleLanguage, WordCategory
from app.utils.time import utcnow


class WordCandidate(db.Model):
    """LLM 이 만든 단어 후보 한 행(LLM 출제 파이프라인).

    `word` 와 다른 테이블인 이유: 후보는 **사람이 승인하기 전까지 퍼즐이 아니다**.
    승인 전 행이 `word` 에 섞이면 자정 배정(`ensure_today_puzzle`)이 검수 안 된
    단어를 뽑는다. 승인하면 기존 `create_word` 경로로 `word` 행이 생기고 이 행은
    `approved` 로 남아 이력이 된다.

    `batch_id` 는 생성 호출 한 번(= `llm_call` 한 행)이 만든 후보 묶음이다 —
    "이 배치에서 몇 개가 규칙을 통과했나" 가 통과율이다.
    """

    __tablename__ = "word_candidate"

    id: int = db.Column(db.Integer, primary_key=True)
    language: PuzzleLanguage = db.Column(
        db.Enum(PuzzleLanguage, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    category: WordCategory = db.Column(
        db.Enum(WordCategory, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    answer: str = db.Column(db.String(50), nullable=False)
    hint: str = db.Column(db.String(200), nullable=False)
    status: CandidateStatus = db.Column(
        db.Enum(CandidateStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=CandidateStatus.PROPOSED,
        index=True,
    )
    # 규칙 탈락·운영자 거절 사유. 승인 대기·승인 행은 비어 있다.
    reject_reason: str | None = db.Column(db.String(300), nullable=True)
    batch_id: str = db.Column(db.String(36), nullable=False, index=True)
    # 승인/거절한 운영자 이메일(마스킹 안 함 — 운영자 두 명뿐이고 접속기록과 같은 기준)과 시각.
    reviewed_by: str | None = db.Column(db.String(191), nullable=True)
    reviewed_at: datetime | None = db.Column(db.DateTime, nullable=True)
    # 승인해서 만들어진 word 행. 거절·탈락이면 NULL.
    word_id: int | None = db.Column(db.Integer, db.ForeignKey("word.id"), nullable=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
