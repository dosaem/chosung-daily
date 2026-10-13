from datetime import datetime, timedelta

from app.config import KST
from app.errors import AlreadyFinishedError, PuzzleChangedError, ValidationError
from app.extensions import db
from app.models import Attempt, Guest, GuestStats
from app.repositories.attempt_repository import list_for_guest_puzzle
from app.repositories.guest_stats_repository import lock_for_guest
from app.repositories.hint_unlock_repository import is_unlocked
from app.schemas.guess import GuessResponse
from app.services.game_rules import (
    MAX_ATTEMPTS,
    compare_letters,
    compute_reveal,
    normalize_for_compare,
    summarize_attempts,
)
from app.services.puzzle_metrics import record_finish, record_leaderboard
from app.services.puzzle_service import get_today_puzzle_or_404


def submit_guess(guest: Guest, puzzle_id: int | None, raw_guess: str) -> GuessResponse:
    """정답 제출 하나 = 트랜잭션 하나.

    실행 순서: 퍼즐 조회(일반 SELECT) → GuestStats 잠금(SELECT ... FOR UPDATE) →
    이후 attempts 재조회. 잠금보다 먼저 일반 SELECT가 있는데도 안전한 이유는
    app/config.py에서 격리수준을 READ COMMITTED로 낮췄기 때문이다 — MySQL 기본
    REPEATABLE READ였다면, 잠금 뒤의 일반 SELECT(attempts)가 이 트랜잭션이 맨
    처음 읽은 시점의 스냅샷을 계속 봐서, 잠금을 기다렸다가 받아도 방금 커밋된
    데이터를 못 보는 문제가 있었다 (실제로 겪은 버그, tests/test_concurrency.py
    참고). READ COMMITTED에서는 문장마다 최신 커밋을 보기 때문에, 잠금 "이전"에
    다른 SELECT가 있어도 문제없다.

    동시성 설계 자체: 같은 게스트가 두 요청을 동시에 보내면 뒤에 도착한 요청은
    GuestStats 잠금에서 블락되고, 앞 요청이 커밋(또는 롤백)할 때까지 기다린다.
    그래서 attempts를 다시 읽을 때는 항상 앞 요청이 만든 변경까지 반영된 최신
    상태를 본다 — attempt_no 중복도, streak 이중 증가도 이 한 지점에서 막힌다.

    다른 선택지(unique 제약 + 재시도)도 attempt_no 자체는 막아주지만, "이미 정답을
    맞췄는지"를 재확인하는 시점의 재시도 타이밍에 따라 streak 이중 증가를 완전히
    막는다고 보장하기 어려워서(두 트랜잭션이 서로의 커밋을 못 보는 구간이 생길 수
    있음) 고르지 않았다. Attempt의 unique(guest_id, puzzle_id, attempt_no) 제약은
    혹시 이 경로를 안 타는 변경이 생겨도 DB가 마지막으로 막아주는 보험으로 남겨둔다.
    """
    puzzle = get_today_puzzle_or_404(guest.puzzle_language)
    if puzzle_id != puzzle.id:
        # 퍼즐 고정(CONTEXT.md). 자정이 지났거나 다른 기기에서 언어를 바꾼 뒤라
        # 클라이언트가 보던 퍼즐과 지금의 "오늘 x 내 언어" 퍼즐이 다르다. 잠금도
        # 걸기 전에 끊어서 시도 행도 GuestStats 도 건드리지 않는다.
        raise PuzzleChangedError()

    stats = lock_for_guest(guest.id)

    word = puzzle.word
    answer = normalize_for_compare(puzzle.language, word.answer)
    guess = normalize_for_compare(puzzle.language, raw_guess)

    if len(guess) != len(answer):
        raise ValidationError(f"정답은 {len(answer)}글자입니다.")

    attempts = list_for_guest_puzzle(guest.id, puzzle.id)
    solved, prior_wrong_count = summarize_attempts(attempts)
    if solved:
        raise AlreadyFinishedError("이미 정답을 맞춘 퍼즐입니다.")
    if len(attempts) >= MAX_ATTEMPTS:
        raise AlreadyFinishedError("이미 기회를 모두 사용한 퍼즐입니다.")

    attempt_no = len(attempts) + 1
    is_correct = guess == answer

    db.session.add(
        Attempt(
            guest_id=guest.id,
            puzzle_id=puzzle.id,
            guess=guess,
            is_correct=is_correct,
            attempt_no=attempt_no,
        )
    )

    wrong_count = prior_wrong_count + (0 if is_correct else 1)
    finished, show_hint = compute_reveal(attempt_no, wrong_count, is_correct)
    # 힌트 표시 규칙은 조회와 제출이 같다 — `show_hint OR hint_unlocked`(spec §A.2).
    hint_unlocked = is_unlocked(guest.id, puzzle.id)

    if is_correct:
        _record_solve(stats, puzzle.puzzle_date)

    db.session.commit()

    _record_metrics(puzzle, guest.id, attempt_no, is_correct, finished)

    return GuessResponse(
        is_correct=is_correct,
        feedback=None if is_correct else compare_letters(guess, answer),
        attempts_left=MAX_ATTEMPTS - attempt_no,
        hint=word.hint if (show_hint or hint_unlocked) else None,
        answer=word.answer if finished else None,
    )


def _record_metrics(
    puzzle, guest_id: int, attempt_no: int, is_correct: bool, finished: bool
) -> None:
    """DB 커밋이 끝난 뒤에만 호출한다 — 커밋이 롤백되면 이 기록도 안 남아야 하니까.
    둘 다 safe_redis_call을 거쳐서 Redis가 죽어 있어도 이 요청 자체에는 영향이 없다.

    통계·리더보드 키는 언어별로 갈리므로 퍼즐의 언어를 같이 넘긴다.
    """
    if finished:
        record_finish(puzzle.puzzle_date, puzzle.language, is_correct, attempt_no)
    if is_correct:
        record_leaderboard(
            puzzle.puzzle_date, puzzle.language, guest_id, attempt_no, datetime.now(KST)
        )


def _record_solve(stats: GuestStats, today) -> None:
    """정답 하나를 기록한다. 연속 기록(streak)은 퍼즐 언어와 무관하다.

    "그 날 하나라도 맞추면 이어진다" 규칙이라, 이미 오늘 맞춘 적이 있으면(두 번째
    언어를 맞춘 경우) streak 은 손대지 않는다 — 안 그러면 같은 날 ko·en 을 둘 다
    맞춘 사람의 streak 이 하루에 2 오른다. 반면 `solved_count` 는 "푼 퍼즐 수"라서
    언어마다 센다(spec §A.4).
    """
    if stats.last_solved_date != today:
        yesterday = today - timedelta(days=1)
        if stats.last_solved_date == yesterday:
            stats.current_streak += 1
        else:
            stats.current_streak = 1
        stats.max_streak = max(stats.max_streak, stats.current_streak)
        stats.last_solved_date = today

    stats.solved_count += 1
