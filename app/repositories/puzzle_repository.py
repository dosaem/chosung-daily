from datetime import date

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage


def find_by_date(puzzle_date: date, language: PuzzleLanguage) -> DailyPuzzle | None:
    """퍼즐은 (날짜, 언어)당 하나다 — 언어를 생략할 수 없게 인자로 받는다."""
    return (
        db.session.query(DailyPuzzle)
        .filter_by(puzzle_date=puzzle_date, language=language)
        .first()
    )
