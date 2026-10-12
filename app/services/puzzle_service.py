from datetime import datetime

from app.config import KST
from app.errors import NoPuzzleTodayError
from app.models import DailyPuzzle, Guest
from app.repositories.attempt_repository import list_for_guest_puzzle
from app.repositories.puzzle_repository import find_by_date
from app.schemas.puzzle import TodayPuzzleResponse
from app.services.game_rules import MAX_ATTEMPTS, compute_reveal, summarize_attempts


def get_today_puzzle_or_404() -> DailyPuzzle:
    """오늘(KST) 날짜의 DailyPuzzle을 찾는다. 없으면 404.

    "오늘"을 여기서 한 번만 계산하고 이후엔 puzzle.puzzle_date를 쓴다 — 호출부가
    각자 datetime.now(KST)를 다시 부르면 자정 근처 요청에서 날짜가 두 번 다르게
    계산될 수 있다. guess_service.submit_guess도 이 함수를 그대로 쓴다.
    """
    today = datetime.now(KST).date()
    puzzle = find_by_date(today)
    if puzzle is None:
        raise NoPuzzleTodayError()
    return puzzle


def get_today_puzzle_view(guest: Guest) -> TodayPuzzleResponse:
    puzzle = get_today_puzzle_or_404()
    attempts = list_for_guest_puzzle(guest.id, puzzle.id)
    word = puzzle.word

    solved, wrong_count = summarize_attempts(attempts)
    finished, show_hint = compute_reveal(len(attempts), wrong_count, solved)

    if solved:
        status = "success"
    elif finished:
        status = "fail"
    else:
        status = "in_progress"

    return TodayPuzzleResponse(
        date=puzzle.puzzle_date,
        chosung=word.chosung,
        length=len(word.answer),
        category=word.category,
        attempts_left=MAX_ATTEMPTS - len(attempts),
        status=status,
        hint=word.hint if show_hint else None,
        answer=word.answer if finished else None,
    )
