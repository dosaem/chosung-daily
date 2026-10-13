import threading

from app.extensions import db
from app.models import Attempt, Guest, GuestStats
from app.services.guess_service import submit_guess


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
