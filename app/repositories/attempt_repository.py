from datetime import date
from typing import NamedTuple

from app.extensions import db
from app.models import Attempt, DailyPuzzle, PuzzleLanguage


def list_for_guest_puzzle(guest_id: int, puzzle_id: int) -> list[Attempt]:
    return (
        db.session.query(Attempt)
        .filter_by(guest_id=guest_id, puzzle_id=puzzle_id)
        .order_by(Attempt.attempt_no)
        .all()
    )


class DaySummary(NamedTuple):
    attempts: int
    solved: bool


def summarize_by_date_and_language(
    guest_id: int, start_date: date, end_date: date
) -> dict[tuple[date, PuzzleLanguage], DaySummary]:
    """기간 안에서 게스트가 시도한 (날짜, 언어)별 시도 수와 정답 여부.

    기록 화면은 하루 2칸(ko/en)씩 7~31일을 한 번에 그려서, 날짜마다 따로 조회하면
    쿼리가 수십 개가 된다 — GROUP BY 로 한 번에 읽는다. 시도가 아예 없는 날은 키가
    없고, 호출부가 그 빈자리를 `none` 으로 채운다.
    """
    rows = (
        db.session.query(
            DailyPuzzle.puzzle_date,
            DailyPuzzle.language,
            db.func.count(Attempt.id),
            db.func.max(Attempt.is_correct),
        )
        .join(Attempt, Attempt.puzzle_id == DailyPuzzle.id)
        .filter(
            Attempt.guest_id == guest_id,
            DailyPuzzle.puzzle_date >= start_date,
            DailyPuzzle.puzzle_date <= end_date,
        )
        .group_by(DailyPuzzle.puzzle_date, DailyPuzzle.language)
        .all()
    )
    return {
        (puzzle_date, language): DaySummary(attempts=attempts, solved=bool(solved))
        for puzzle_date, language, attempts, solved in rows
    }
