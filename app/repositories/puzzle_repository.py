from datetime import date

from app.extensions import db
from app.models import DailyPuzzle


def find_by_date(puzzle_date: date) -> DailyPuzzle | None:
    return db.session.query(DailyPuzzle).filter_by(puzzle_date=puzzle_date).first()
