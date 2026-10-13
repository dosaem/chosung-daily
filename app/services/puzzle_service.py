from datetime import datetime

from app.config import KST
from app.errors import NoPuzzleTodayError
from app.models import DailyPuzzle, Guest, PuzzleLanguage
from app.repositories.attempt_repository import list_for_guest_puzzle
from app.repositories.hint_unlock_repository import is_unlocked
from app.repositories.puzzle_repository import find_by_date
from app.schemas.puzzle import AttemptView, TodayPuzzleResponse
from app.services.game_rules import (
    MAX_ATTEMPTS,
    compare_letters,
    compute_reveal,
    normalize_for_compare,
    summarize_attempts,
)
from app.services.puzzle_cache import CachedPuzzle, cache_puzzle, get_cached_puzzle
from app.utils.mask import mask_length, mask_to_text


def get_today_puzzle_or_404(language: PuzzleLanguage) -> DailyPuzzle | CachedPuzzle:
    """오늘(KST) 그 언어의 퍼즐을 찾는다. 없으면 404.

    Cache-Aside: 먼저 Redis(`puzzle:{date}:{lang}`)를 보고, 없으면 DB에서 읽어
    캐시에 채운다. 캐시에서 온 CachedPuzzle은 DailyPuzzle과 같은 속성(id,
    puzzle_date, language, word.chosung/answer/hint/category/mask)을 노출해서
    호출부가 둘을 구분할 필요가 없다. Redis가 죽어 있으면 get_cached_puzzle이
    조용히 None을 돌려주고 DB로 그냥 넘어간다(safe_redis_call).

    언어는 호출부(게스트 선호 또는 `?language=`)가 정해서 넘긴다 — 한 언어의
    퍼즐이 없어도 다른 언어는 정상 동작한다(자정 배정이 언어별로 따로 돈다).

    "오늘"을 여기서 한 번만 계산하고 이후엔 puzzle.puzzle_date를 쓴다 — 호출부가
    각자 datetime.now(KST)를 다시 부르면 자정 근처 요청에서 날짜가 두 번 다르게
    계산될 수 있다. guess_service.submit_guess도 이 함수를 그대로 쓴다.
    """
    today = datetime.now(KST).date()

    cached = get_cached_puzzle(today, language)
    if cached is not None:
        return cached

    puzzle = find_by_date(today, language)
    if puzzle is None:
        raise NoPuzzleTodayError()

    cache_puzzle(puzzle)
    return puzzle


def get_today_puzzle_view(guest: Guest) -> TodayPuzzleResponse:
    puzzle = get_today_puzzle_or_404(guest.puzzle_language)
    attempts = list_for_guest_puzzle(guest.id, puzzle.id)
    word = puzzle.word

    solved, wrong_count = summarize_attempts(attempts)
    finished, show_hint = compute_reveal(len(attempts), wrong_count, solved)

    hint_unlocked = is_unlocked(guest.id, puzzle.id)

    if solved:
        status = "success"
    elif finished:
        status = "fail"
    else:
        status = "in_progress"

    return TodayPuzzleResponse(
        puzzle_id=puzzle.id,
        date=puzzle.puzzle_date,
        language=puzzle.language,
        mask=word.mask,
        chosung=_compat_chosung(puzzle.language, word),
        length=mask_length(word.mask),
        category=word.category,
        attempts_left=MAX_ATTEMPTS - len(attempts),
        attempts=_attempt_views(puzzle.language, word.answer, attempts),
        status=status,
        hint_unlocked=hint_unlocked,
        hint=word.hint if (show_hint or hint_unlocked) else None,
        answer=word.answer if finished else None,
    )


def _attempt_views(language: PuzzleLanguage, answer: str, attempts) -> list[AttemptView]:
    """시도 이력을 보드 한 줄씩으로 바꾼다(spec §A.2 "시도 이력 복원").

    피드백은 저장하지 않고 정답과 다시 비교해서 만든다 — 같은 비교 규칙이 제출과
    조회에 두 벌로 존재하면 언젠가 어긋난다. 정답 행은 글자가 전부 같으니 자연히
    전부 `true` 가 된다(스펙 "미정 항목" 12 를 이 티켓에서 이렇게 확정했다).

    저장된 guess 도 한 번 더 정규화한다 — 구분자 규칙이 지금과 달랐던 때의 행이
    남아 있어도 `length` 와 같은 길이의 보드로 그려진다.
    """
    normalized_answer = normalize_for_compare(language, answer)
    views = []
    for attempt in attempts:
        guess = normalize_for_compare(language, attempt.guess)
        views.append(AttemptView(guess=guess, feedback=compare_letters(guess, normalized_answer)))
    return views


def _compat_chosung(language: PuzzleLanguage, word) -> str:
    """ko 호환 필드(`chosung`)를 만든다.

    ko 는 `Word.chosung` 컬럼의 현행 값 그대로 — 기존 웹 클라이언트가 보는 문자열이
    한 글자도 바뀌지 않아야 한다. en 은 그 컬럼이 자리표시자뿐이라 쓸 수 없어서
    `mask` 의 보이는 글자로 같은 모양의 문자열을 만든다(`app/utils/mask.py`).
    """
    if language == PuzzleLanguage.KO:
        return word.chosung
    return mask_to_text(word.mask)
