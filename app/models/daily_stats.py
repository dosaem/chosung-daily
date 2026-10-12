from datetime import date

from app.extensions import db


class DailyStats(db.Model):
    __tablename__ = "daily_stats"

    puzzle_date: date = db.Column(db.Date, primary_key=True)
    distribution: dict = db.Column(db.JSON, nullable=False, default=dict)
    solver_count: int = db.Column(db.Integer, nullable=False, default=0)
