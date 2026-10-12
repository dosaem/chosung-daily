import unicodedata
from datetime import datetime, timedelta

from app.config import KST
from app.errors import AlreadyFinishedError, ValidationError
from app.extensions import db
from app.models import Attempt, Guest, GuestStats
from app.repositories.attempt_repository import list_for_guest_puzzle
from app.repositories.guest_stats_repository import lock_for_guest
from app.schemas.guess import GuessResponse
from app.services.game_rules import MAX_ATTEMPTS, compute_reveal, summarize_attempts
from app.services.puzzle_metrics import record_finish, record_leaderboard
from app.services.puzzle_service import get_today_puzzle_or_404


def submit_guess(guest: Guest, raw_guess: str) -> GuessResponse:
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
    puzzle = get_today_puzzle_or_404()
    stats = lock_for_guest(guest.id)

    guess = unicodedata.normalize("NFC", raw_guess.strip())
    word = puzzle.word

    if len(guess) != len(word.answer):
        raise ValidationError(f"정답은 {len(word.answer)}글자입니다.")

    attempts = list_for_guest_puzzle(guest.id, puzzle.id)
    solved, prior_wrong_count = summarize_attempts(attempts)
    if solved:
        raise AlreadyFinishedError("이미 정답을 맞춘 퍼즐입니다.")
    if len(attempts) >= MAX_ATTEMPTS:
        raise AlreadyFinishedError("이미 기회를 모두 사용한 퍼즐입니다.")

    attempt_no = len(attempts) + 1
    is_correct = guess == word.answer

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

    if is_correct:
        _record_solve(stats, puzzle.puzzle_date)

    db.session.commit()

    _record_metrics(puzzle.puzzle_date, guest.id, attempt_no, is_correct, finished)

    return GuessResponse(
        is_correct=is_correct,
        feedback=None if is_correct else _compare(guess, word.answer),
        attempts_left=MAX_ATTEMPTS - attempt_no,
        hint=word.hint if show_hint else None,
        answer=word.answer if finished else None,
    )


def _compare(guess: str, answer: str) -> list[bool]:
    return [g == a for g, a in zip(guess, answer, strict=True)]


def _record_metrics(
    puzzle_date, guest_id: int, attempt_no: int, is_correct: bool, finished: bool
) -> None:
    """DB 커밋이 끝난 뒤에만 호출한다 — 커밋이 롤백되면 이 기록도 안 남아야 하니까.
    둘 다 safe_redis_call을 거쳐서 Redis가 죽어 있어도 이 요청 자체에는 영향이 없다.
    """
    if finished:
        record_finish(puzzle_date, is_correct, attempt_no)
    if is_correct:
        record_leaderboard(puzzle_date, guest_id, attempt_no, datetime.now(KST))


def _record_solve(stats: GuestStats, today) -> None:
    yesterday = today - timedelta(days=1)
    if stats.last_solved_date == yesterday:
        stats.current_streak += 1
    else:
        stats.current_streak = 1
    stats.max_streak = max(stats.max_streak, stats.current_streak)
    stats.solved_count += 1
    stats.last_solved_date = today
