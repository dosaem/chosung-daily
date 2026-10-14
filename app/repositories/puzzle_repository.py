from datetime import date

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage


def find_by_date(puzzle_date: date, language: PuzzleLanguage) -> DailyPuzzle | None:
    """퍼즐은 (날짜, 언어)당 하나다 — 언어를 생략할 수 없게 인자로 받는다."""
    return (
        db.session.query(DailyPuzzle)
        .filter_by(puzzle_date=puzzle_date, language=language)
        .first()
    )


def list_in_range(
    language: PuzzleLanguage, start_date: date, end_date: date
) -> list[DailyPuzzle]:
    """기간 안의 그 언어 퍼즐. 운영자 배정표가 30일을 한 번에 읽는다 —
    날짜마다 `find_by_date` 를 부르면 쿼리가 30개가 된다.

    단어까지 같이 읽는다(`joinedload`) — 배정표는 행마다 정답·카테고리·가림을
    그려서, 지연 로딩이면 쿼리가 다시 30개로 돌아간다.
    """
    return (
        db.session.query(DailyPuzzle)
        .options(joinedload(DailyPuzzle.word))
        .filter(
            DailyPuzzle.language == language,
            DailyPuzzle.puzzle_date >= start_date,
            DailyPuzzle.puzzle_date <= end_date,
        )
        .order_by(DailyPuzzle.puzzle_date)
        .all()
    )
