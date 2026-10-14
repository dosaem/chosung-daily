import threading
from unittest.mock import patch

from app.extensions import db
from app.models import (
    AccessLog,
    Attempt,
    DailyPuzzle,
    Guest,
    GuestStats,
    HintUnlock,
    PuzzleLanguage,
    Word,
    WordCategory,
)
from app.repositories import attempt_repository
from app.services import access_log_service, guess_service
from app.services.guess_service import submit_guess
from app.services.hint_service import unlock_hint
from app.services.puzzle_schedule_service import replace_assignment
from app.services.puzzle_service import get_today_puzzle_view


def test_concurrent_correct_guesses_do_not_double_count(app, today_puzzle, guest_headers):
    """같은 게스트가 정답을 동시에 두 번 제출해도 attempt_no가 꼬이거나
    streak/solved_count가 두 번 올라가면 안 된다 (스펙 요구사항).

    GuestStats 행의 SELECT ... FOR UPDATE 잠금으로 두 스레드를 직렬화하는
    설계(app/services/guess_service.py)를 검증한다. 하나는 성공하고,
    뒤따라온 하나는 ALREADY_FINISHED로 막혀야 한다.
    """
    token = guest_headers["Authorization"].removeprefix("Bearer ")
    guest_id = Guest.query.filter_by(token=token).one().id
    puzzle_id = today_puzzle.id

    results = []
    barrier = threading.Barrier(2)

    def worker():
        with app.app_context():
            barrier.wait()
            guest = db.session.get(Guest, guest_id)
            try:
                response = submit_guess(guest, puzzle_id, "사과")
                results.append(("ok", response.is_correct))
            except Exception as exc:
                results.append(("error", type(exc).__name__))
            finally:
                db.session.remove()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    outcomes = sorted(outcome for outcome, _ in results)
    assert outcomes == ["error", "ok"]
    assert ("error", "AlreadyFinishedError") in results
    assert ("ok", True) in results

    stats = db.session.get(GuestStats, guest_id)
    assert stats.solved_count == 1
    assert stats.current_streak == 1

    # attempt_no가 꼬이지 않았는지도 직접 확인한다 — 두 스레드가 동시에 밀어넣어도
    # Attempt 행은 정확히 하나, attempt_no는 1이어야 한다 (둘 다 1을 쓰려다 충돌하면
    # 둘 다 성공하는 게 아니라 하나만 커밋되는 게 맞는 동작).
    attempts = Attempt.query.filter_by(guest_id=guest_id).all()
    assert len(attempts) == 1
    assert attempts[0].attempt_no == 1
    assert attempts[0].is_correct is True


def test_hint_unlock_and_guess_are_serialized(app, today_puzzle, guest_headers):
    """힌트 미리 보기와 제출이 동시에 들어와도 같은 GuestStats 잠금 뒤에 한 줄로
    서야 한다(티켓 06). 어느 쪽이 먼저 들어가든 상태가 일관돼야 한다:

    - 미리 보기가 먼저면 둘 다 성공하고 열림 행이 하나 남는다.
    - 제출이 먼저면 퍼즐이 그 자리에서 끝나므로 미리 보기는 ALREADY_FINISHED 다
      (정답을 이미 보여준 퍼즐의 힌트를 광고와 바꾸게 두지 않는다).

    어느 쪽이든 시도는 하나, solved_count 는 1 이다 — 미리 보기는 시도도 통계도
    건드리지 않는다.
    """
    token = guest_headers["Authorization"].removeprefix("Bearer ")
    guest_id = Guest.query.filter_by(token=token).one().id
    puzzle_id = today_puzzle.id

    results = {}
    barrier = threading.Barrier(2)

    def run(name, call):
        with app.app_context():
            barrier.wait()
            guest = db.session.get(Guest, guest_id)
            try:
                call(guest)
                results[name] = "ok"
            except Exception as exc:
                results[name] = type(exc).__name__
            finally:
                db.session.remove()

    threads = [
        threading.Thread(target=run, args=("guess", lambda g: submit_guess(g, puzzle_id, "사과"))),
        threading.Thread(target=run, args=("unlock", lambda g: unlock_hint(g, puzzle_id))),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results["guess"] == "ok"
    assert results["unlock"] in ("ok", "AlreadyFinishedError")

    unlocks = HintUnlock.query.filter_by(guest_id=guest_id).all()
    assert len(unlocks) == (1 if results["unlock"] == "ok" else 0)

    attempts = Attempt.query.filter_by(guest_id=guest_id).all()
    assert len(attempts) == 1
    assert attempts[0].attempt_no == 1

    stats = db.session.get(GuestStats, guest_id)
    assert stats.solved_count == 1


def test_concurrent_hint_unlocks_insert_one_row(app, today_puzzle, guest_headers):
    """같은 퍼즐의 미리 보기를 동시에 두 번 눌러도 행은 하나다 — 뒤에 온 쪽은
    잠금을 받은 뒤에 앞 요청이 만든 행을 보고 HINT_ALREADY_UNLOCKED 로 끝난다."""
    token = guest_headers["Authorization"].removeprefix("Bearer ")
    guest_id = Guest.query.filter_by(token=token).one().id
    puzzle_id = today_puzzle.id

    outcomes = []
    barrier = threading.Barrier(2)

    def worker():
        with app.app_context():
            barrier.wait()
            guest = db.session.get(Guest, guest_id)
            try:
                unlock_hint(guest, puzzle_id)
                outcomes.append("ok")
            except Exception as exc:
                outcomes.append(type(exc).__name__)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(outcomes) == ["HintAlreadyUnlockedError", "ok"]
    assert HintUnlock.query.filter_by(guest_id=guest_id).count() == 1


def _replacement_word():
    word = Word(
        answer="학교",
        language=PuzzleLanguage.KO,
        category=WordCategory.GENERAL,
        hint="아이들이 공부하는 곳",
    )
    db.session.add(word)
    db.session.commit()
    return word


def _assert_one_truth(winner, guest_id, puzzle_id, word_ids, outcomes):
    """교체와 첫 제출의 경합 뒤에 남아야 하는 상태는 둘 중 하나뿐이다(D-23-1).

    - 제출이 이겼으면: 시도 1건 + 옛 단어 그대로 + 교체는 "시도 있는 날짜" 거부.
    - 교체가 이겼으면: 시도 0건 + 새 단어 + 제출은 PUZZLE_CHANGED.

    둘 다 성공하면 "성공 상태인데 보드의 정답 행이 전부 오답" 인 모순된 보드가
    복원된다 — 복원된 보드까지 같이 본다.
    """
    original_word_id, replacement_word_id = word_ids
    submit_outcome, replace_outcome = outcomes

    db.session.remove()
    puzzle = db.session.get(DailyPuzzle, puzzle_id)
    attempts = Attempt.query.filter_by(puzzle_id=puzzle_id).all()

    if winner == "submission":
        assert submit_outcome == ("ok", True), (submit_outcome, replace_outcome)
        assert replace_outcome == ("error", "ValidationError"), replace_outcome
        assert puzzle.word_id == original_word_id
        assert len(attempts) == 1
        assert attempts[0].is_correct is True
    else:
        assert submit_outcome == ("error", "PuzzleChangedError"), submit_outcome
        assert replace_outcome == ("ok",), (submit_outcome, replace_outcome)
        assert puzzle.word_id == replacement_word_id
        assert attempts == []

    view = get_today_puzzle_view(db.session.get(Guest, guest_id))
    if view.status == "success":
        # 성공으로 복원된 보드의 마지막 줄은 정답 행이라 글자가 전부 맞아야 한다.
        assert all(view.attempts[-1].feedback), (view.answer, view.attempts)


def test_replacement_that_wins_the_lock_turns_the_submission_away(
    app, today_puzzle, guest_headers
):
    """운영자 교체가 "시도 0건" 을 읽은 직후 첫 제출이 들어오는 경합(D-23-1).

    교체가 퍼즐 행 잠금을 먼저 잡았으므로 교체가 이기고, 뒤에 온 제출은 잠금을
    기다렸다가 바뀐 정답을 보고 PUZZLE_CHANGED 로 끊긴다 — 옛 정답으로 판정된
    시도 행이 남지 않는다.
    """
    token = guest_headers["Authorization"].removeprefix("Bearer ")
    guest_id = Guest.query.filter_by(token=token).one().id
    puzzle_id = today_puzzle.id
    puzzle_date = today_puzzle.puzzle_date
    original_word_id = today_puzzle.word_id
    replacement_word_id = _replacement_word().id

    counted = threading.Event()
    submitted = threading.Event()
    submit_outcome = []

    def submit_worker():
        counted.wait(10)
        with app.app_context():
            guest = db.session.get(Guest, guest_id)
            try:
                response = submit_guess(guest, puzzle_id, "사과")
                submit_outcome.append(("ok", response.is_correct))
            except Exception as exc:
                submit_outcome.append(("error", type(exc).__name__))
            finally:
                db.session.remove()
        submitted.set()

    original_count = attempt_repository.count_by_puzzle

    def count_then_wait_for_the_submission(ids):
        counts = original_count(ids)
        counted.set()
        # 수정 전: 제출이 아무것도 막지 않으니 바로 커밋되고 깨어난다.
        # 수정 후: 제출이 공유 잠금에서 막혀 있어 여기서 timeout 된다.
        submitted.wait(3)
        return counts

    thread = threading.Thread(target=submit_worker)
    thread.start()
    replace_outcome = []
    try:
        with patch.object(
            attempt_repository, "count_by_puzzle", side_effect=count_then_wait_for_the_submission
        ):
            replace_assignment(puzzle_date, PuzzleLanguage.KO, replacement_word_id)
        replace_outcome.append(("ok",))
    except Exception as exc:
        replace_outcome.append(("error", type(exc).__name__))
    finally:
        counted.set()
        thread.join(30)

    assert not thread.is_alive()
    _assert_one_truth(
        "replacement",
        guest_id,
        puzzle_id,
        (original_word_id, replacement_word_id),
        (submit_outcome[0], replace_outcome[0]),
    )


def test_submission_that_wins_the_lock_blocks_the_replacement(
    app, today_puzzle, guest_headers
):
    """반대 순서: 첫 제출이 퍼즐 행을 먼저 잡고 운영자 교체가 뒤에 오는 경합.

    제출이 커밋되면 그 날짜는 "시도 있는 날짜" 라서 교체가 거부돼야 한다 — 교체가
    제출 트랜잭션 도중에 끼어들어 정답을 갈아끼우면 안 된다.
    """
    token = guest_headers["Authorization"].removeprefix("Bearer ")
    guest_id = Guest.query.filter_by(token=token).one().id
    puzzle_id = today_puzzle.id
    puzzle_date = today_puzzle.puzzle_date
    original_word_id = today_puzzle.word_id
    replacement_word_id = _replacement_word().id

    locked = threading.Event()
    replaced = threading.Event()
    replace_outcome = []

    def replace_worker():
        locked.wait(10)
        with app.app_context():
            try:
                replace_assignment(puzzle_date, PuzzleLanguage.KO, replacement_word_id)
                replace_outcome.append(("ok",))
            except Exception as exc:
                replace_outcome.append(("error", type(exc).__name__))
            finally:
                db.session.remove()
        replaced.set()

    original_list = guess_service.list_for_guest_puzzle

    def list_then_wait_for_the_replacement(guest_id_arg, puzzle_id_arg):
        attempts = original_list(guest_id_arg, puzzle_id_arg)
        locked.set()
        # 수정 전: 교체가 잠금 없이 끼어들어 커밋하고 깨운다.
        # 수정 후: 교체가 FOR UPDATE 에서 막혀 timeout 된다.
        replaced.wait(3)
        return attempts

    thread = threading.Thread(target=replace_worker)
    thread.start()
    submit_outcome = []
    try:
        with patch.object(
            guess_service, "list_for_guest_puzzle", side_effect=list_then_wait_for_the_replacement
        ):
            guest = db.session.get(Guest, guest_id)
            response = submit_guess(guest, puzzle_id, "사과")
        submit_outcome.append(("ok", response.is_correct))
    except Exception as exc:
        submit_outcome.append(("error", type(exc).__name__))
    finally:
        locked.set()
        thread.join(30)

    assert not thread.is_alive()
    _assert_one_truth(
        "submission",
        guest_id,
        puzzle_id,
        (original_word_id, replacement_word_id),
        (submit_outcome[0], replace_outcome[0]),
    )


def test_concurrent_access_log_appends_keep_one_chain(app):
    """36: 동시에 들어온 두 기록이 체인을 두 갈래로 갈라놓지 않는다.

    `append` 는 직전 행을 `SELECT ... FOR UPDATE` 로 잠그고 읽어서 두 요청을 한 줄로
    세운다(`app/repositories/access_log_repository.py`). 잠글 행이 있어야 하는
    설계라 기준점 한 행을 먼저 넣고 두 스레드를 같이 출발시킨다.
    """
    def record(actor):
        access_log_service.record_access(
            action="me.history.read",
            actor=actor,
            remote_ip="127.0.0.1",
            target=None,
            status_code=200,
        )

    record("guest.1")  # 기준점 — 잠글 직전 행
    barrier = threading.Barrier(2)
    errors = []

    def worker(actor):
        with app.app_context():
            barrier.wait()
            try:
                record(actor)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=worker, args=(f"guest.{n}",)) for n in (2, 3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], errors
    rows = db.session.query(AccessLog).order_by(AccessLog.id).all()
    assert len(rows) == 3
    # 한 줄로 이어져 있다 — 두 갈래면 아래 verify 가 끊긴 지점을 찍는다.
    assert [row.prev_hash for row in rows[1:]] == [row.hash for row in rows[:-1]]
    assert access_log_service.verify_chain().broken_at is None
