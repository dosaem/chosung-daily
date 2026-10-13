from datetime import date

from app.extensions import db
from app.models.enums import PuzzleLanguage


class DailyStats(db.Model):
    """하루치 시도 분포. 퍼즐이 날짜·언어마다 하나라서 키도 (날짜, 언어)다."""

    __tablename__ = "daily_stats"

    puzzle_date: date = db.Column(db.Date, primary_key=True)
    language: PuzzleLanguage = db.Column(
        db.Enum(PuzzleLanguage, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        primary_key=True,
        default=PuzzleLanguage.KO,
        server_default=PuzzleLanguage.KO.value,
    )
    distribution: dict = db.Column(db.JSON, nullable=False, default=dict)
    solver_count: int = db.Column(db.Integer, nullable=False, default=0)
