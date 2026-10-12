from datetime import date

from app.extensions import db


class GuestStats(db.Model):
    __tablename__ = "guest_stats"

    guest_id: int = db.Column(db.Integer, db.ForeignKey("guest.id"), primary_key=True)
    current_streak: int = db.Column(db.Integer, nullable=False, default=0)
    max_streak: int = db.Column(db.Integer, nullable=False, default=0)
    solved_count: int = db.Column(db.Integer, nullable=False, default=0)
    last_solved_date: date | None = db.Column(db.Date, nullable=True)
