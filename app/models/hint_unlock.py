from datetime import datetime

from app.extensions import db
from app.utils.time import utcnow


class HintUnlock(db.Model):
    """힌트 미리 보기를 쓴 사실. 게스트와 퍼즐 하나당 최대 한 행이다.

    PK 가 곧 "퍼즐당 1회" 규칙(`CONTEXT.md` "힌트 미리 보기")이라서 별도의
    카운터나 플래그 컬럼이 없다 — 행이 있으면 열린 것이다.
    """

    __tablename__ = "hint_unlock"

    guest_id: int = db.Column(db.Integer, db.ForeignKey("guest.id"), primary_key=True)
    puzzle_id: int = db.Column(db.Integer, db.ForeignKey("daily_puzzle.id"), primary_key=True)
    unlocked_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
