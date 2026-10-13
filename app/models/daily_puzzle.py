from datetime import date, datetime

from app.extensions import db
from app.models.enums import PuzzleLanguage
from app.utils.time import utcnow


class DailyPuzzle(db.Model):
    """오늘의 퍼즐 — 한 날짜에 퍼즐 언어마다 하나씩 있다(CONTEXT.md).

    유니크 키에 언어가 들어가서 같은 날짜에 ko/en 퍼즐이 공존한다. 자정 배정이
    언어별로 따로 돌기 때문에(한 언어 실패가 다른 언어를 막지 않는다) DB 쪽에서도
    "날짜당 하나"가 아니라 "날짜·언어당 하나"가 맞다.
    """

    __tablename__ = "daily_puzzle"
    __table_args__ = (
        db.UniqueConstraint("puzzle_date", "language", name="uq_daily_puzzle_date_language"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    puzzle_date: date = db.Column(db.Date, nullable=False)
    language: PuzzleLanguage = db.Column(
        db.Enum(PuzzleLanguage, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=PuzzleLanguage.KO,
        server_default=PuzzleLanguage.KO.value,
    )
    word_id: int = db.Column(db.Integer, db.ForeignKey("word.id"), nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)

    word = db.relationship("Word")
