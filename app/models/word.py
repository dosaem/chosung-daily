from datetime import datetime

from sqlalchemy import event

from app.extensions import db
from app.models.enums import PuzzleLanguage, WordCategory
from app.utils.chosung import extract_chosung
from app.utils.mask import build_mask
from app.utils.time import utcnow


class Word(db.Model):
    __tablename__ = "word"

    id: int = db.Column(db.Integer, primary_key=True)
    answer: str = db.Column(db.String(50), nullable=False)
    language: PuzzleLanguage = db.Column(
        db.Enum(PuzzleLanguage, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        server_default=PuzzleLanguage.KO.value,
    )
    # 언어에 맞는 가림 타일 목록 (app/utils/mask.py). 플레이어가 보는 문제 그 자체다.
    mask: list[dict[str, str]] = db.Column(db.JSON, nullable=False)
    # ko 응답 호환용으로 남겨둔 컬럼 (GET /puzzles/today 의 `chosung` 필드).
    # 신규 클라이언트는 `mask`를 쓰고, 이 컬럼은 모든 클라이언트가 옮겨간 뒤에
    # 지운다 (스펙 "미정 항목" 10). en 단어에선 초성이 없어 자리표시자만 남는다.
    chosung: str = db.Column(db.String(50), nullable=False)
    category: WordCategory = db.Column(
        db.Enum(WordCategory, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    hint: str = db.Column(db.String(200), nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)


@event.listens_for(Word, "before_insert")
@event.listens_for(Word, "before_update")
def _set_mask(_mapper, _connection, target: Word) -> None:
    """answer/language 저장 전 가림을 항상 다시 계산한다. Spring의
    @PrePersist/@PreUpdate 대응 — 저장 경로(CLI 시드·책 등록·관리자 CRUD)가
    여러 개라서, 각 호출부가 가림 계산을 기억하게 두지 않고 여기 한 곳으로 모았다.

    language는 여기서 직접 기본값을 넣는다 — 컬럼 default는 INSERT 문을 만들 때
    적용돼서 이 이벤트보다 늦고, 그러면 build_mask가 None을 받는다.
    """
    if target.language is None:
        target.language = PuzzleLanguage.KO
    target.mask = build_mask(target.language, target.answer)
    target.chosung = extract_chosung(target.answer)
