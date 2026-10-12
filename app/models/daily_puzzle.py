from datetime import date, datetime

from app.extensions import db
from app.utils.time import utcnow


class DailyPuzzle(db.Model):
    __tablename__ = "daily_puzzle"

    id: int = db.Column(db.Integer, primary_key=True)
    puzzle_date: date = db.Column(db.Date, nullable=False, unique=True)
    word_id: int = db.Column(db.Integer, db.ForeignKey("word.id"), nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)

    word = db.relationship("Word")
