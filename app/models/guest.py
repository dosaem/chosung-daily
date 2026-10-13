import uuid
from datetime import datetime

from app.extensions import db
from app.models.enums import PuzzleLanguage
from app.utils.time import utcnow


class Guest(db.Model):
    __tablename__ = "guest"

    id: int = db.Column(db.Integer, primary_key=True)
    token: str = db.Column(
        db.String(36), nullable=False, unique=True, default=lambda: str(uuid.uuid4())
    )
    # 플레이어가 고르는 문제의 언어 선호. 기기 UI 언어와 별개다(CONTEXT.md).
    puzzle_language: PuzzleLanguage = db.Column(
        db.Enum(PuzzleLanguage, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=PuzzleLanguage.KO,
        server_default=PuzzleLanguage.KO.value,
    )
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
