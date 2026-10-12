from datetime import datetime

from app.extensions import db
from app.utils.time import utcnow


class Attempt(db.Model):
    __tablename__ = "attempt"
    __table_args__ = (
        db.UniqueConstraint(
            "guest_id", "puzzle_id", "attempt_no", name="uq_attempt_guest_puzzle_no"
        ),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    guest_id: int = db.Column(db.Integer, db.ForeignKey("guest.id"), nullable=False)
    puzzle_id: int = db.Column(db.Integer, db.ForeignKey("daily_puzzle.id"), nullable=False)
    guess: str = db.Column(db.String(50), nullable=False)
    is_correct: bool = db.Column(db.Boolean, nullable=False)
    attempt_no: int = db.Column(db.Integer, nullable=False)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
