"""힌트 미리 보기(Early Hint) — spec §A.5, §A.2 "힌트 표시 규칙".

보상형 광고를 본 플레이어가 3번째 오답 전에 힌트를 여는 경로다. 서버는 광고를
봤는지 알 수 없으므로(AdMob SSV 미사용, README "설계 판단") 호출 자체를 막지
않는다 — 대신 "열었다"는 사실만 퍼즐당 한 번 기록하고, 그게 시도·순위에 전혀
영향을 주지 않는다는 걸 여기서 고정한다.
"""

from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import (
    Attempt,
    DailyPuzzle,
    Guest,
    GuestStats,
    HintUnlock,
    PuzzleLanguage,
    Word,
    WordCategory,
)
from app.services.guest_service import issue_guest


def _headers(guest):
    return {"Authorization": f"Bearer {guest.token}"}


def _guest_of(headers):
    token = headers["Authorization"].removeprefix("Bearer ")
    return Guest.query.filter_by(token=token).one()


def _today(client, headers):
    return client.get("/api/v1/puzzles/today", headers=headers).get_json()


def _guess(client, headers, puzzle_id, text):
    return client.post(
        "/api/v1/puzzles/today/guesses",
        headers=headers,
        json={"puzzle_id": puzzle_id, "guess": text},
    )


def _unlock(client, headers, puzzle_id):
    payload = {} if puzzle_id is None else {"puzzle_id": puzzle_id}
    return client.post("/api/v1/puzzles/today/hint-unlock", headers=headers, json=payload)


# --- 여는 경로 ---------------------------------------------------------------


def test_unlock_returns_the_hint_and_records_one_row(client, guest_headers, today_puzzle):
    res = _unlock(client, guest_headers, today_puzzle.id)

    assert res.status_code == 200
    assert res.get_json() == {"hint": "빨간 과일"}

    guest_id = _guest_of(guest_headers).id
    row = db.session.get(HintUnlock, (guest_id, today_puzzle.id))
    assert row is not None
    assert row.unlocked_at is not None


def test_unlocked_hint_comes_back_on_a_new_client(app, client, guest_headers, today_puzzle):
    """재진입·다른 기기에서도 힌트가 계속 채워져 와야 한다(티켓 What to build)."""
    _unlock(client, guest_headers, today_puzzle.id)

    body = _today(app.test_client(), guest_headers)

    assert body["hint_unlocked"] is True
    assert body["hint"] == "빨간 과일"


def test_unlocked_hint_is_filled_in_the_guess_response(client, guest_headers, today_puzzle):
    """`hint` 규칙 = `show_hint OR hint_unlocked` 는 제출 응답에도 걸린다(spec §A.2)."""
    assert _guess(client, guest_headers, today_puzzle.id, "바바").get_json()["hint"] is None

    _unlock(client, guest_headers, today_puzzle.id)

    assert _guess(client, guest_headers, today_puzzle.id, "바바").get_json()["hint"] == "빨간 과일"


def test_unlock_is_separate_per_puzzle(client, make_today_puzzle):
    """PK(guest_id, puzzle_id) — ko 를 열어도 en 퍼즐은 잠겨 있다."""
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    en_puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")
    guest = issue_guest(PuzzleLanguage.KO)
    headers = _headers(guest)

    _unlock(client, headers, ko_puzzle.id)

    client.patch("/api/v1/me", headers=headers, json={"puzzle_language": "en"})
    body = _today(client, headers)

    assert body["puzzle_id"] == en_puzzle.id
    assert body["hint_unlocked"] is False
    assert body["hint"] is None


# --- 거절하는 경로 -----------------------------------------------------------


def test_second_unlock_is_rejected(client, guest_headers, today_puzzle):
    _unlock(client, guest_headers, today_puzzle.id)

    res = _unlock(client, guest_headers, today_puzzle.id)

    assert res.status_code == 409
    assert res.get_json()["code"] == "HINT_ALREADY_UNLOCKED"
    assert HintUnlock.query.count() == 1


def test_unlock_on_a_solved_puzzle_is_rejected(client, guest_headers, today_puzzle):
    _guess(client, guest_headers, today_puzzle.id, "사과")

    res = _unlock(client, guest_headers, today_puzzle.id)

    assert res.status_code == 409
    assert res.get_json()["code"] == "ALREADY_FINISHED"
    assert HintUnlock.query.count() == 0


def test_unlock_after_every_attempt_is_used_is_rejected(client, guest_headers, today_puzzle):
    for _ in range(5):
        _guess(client, guest_headers, today_puzzle.id, "바바")

    res = _unlock(client, guest_headers, today_puzzle.id)

    assert res.status_code == 409
    assert res.get_json()["code"] == "ALREADY_FINISHED"
    assert HintUnlock.query.count() == 0


def test_unlock_without_a_puzzle_id_is_rejected_as_puzzle_changed(
    client, guest_headers, today_puzzle
):
    """제출과 같은 규칙 — 할 일이 "새로고침" 하나뿐이라 400 으로 가르지 않는다."""
    res = _unlock(client, guest_headers, None)

    assert res.status_code == 409
    assert res.get_json()["code"] == "PUZZLE_CHANGED"
    assert HintUnlock.query.count() == 0


def test_unlock_for_yesterdays_puzzle_is_rejected_as_puzzle_changed(
    client, guest_headers, today_puzzle
):
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    word = Word(
        answer="수박", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="여름 과일"
    )
    db.session.add(word)
    db.session.flush()
    stale = DailyPuzzle(puzzle_date=yesterday, language=PuzzleLanguage.KO, word_id=word.id)
    db.session.add(stale)
    db.session.commit()

    res = _unlock(client, guest_headers, stale.id)

    assert res.status_code == 409
    assert res.get_json()["code"] == "PUZZLE_CHANGED"
    assert HintUnlock.query.count() == 0


# --- 공정성: 시도·순위에 영향 없음 -------------------------------------------


def test_unlock_does_not_consume_an_attempt(client, guest_headers, today_puzzle):
    before = _today(client, guest_headers)["attempts_left"]

    _unlock(client, guest_headers, today_puzzle.id)

    after = _today(client, guest_headers)
    assert after["attempts_left"] == before == 5
    assert after["attempts"] == []
    assert Attempt.query.count() == 0


def test_unlock_does_not_touch_guest_stats(client, guest_headers, today_puzzle):
    guest_id = _guest_of(guest_headers).id

    _unlock(client, guest_headers, today_puzzle.id)

    db.session.expire_all()
    stats = db.session.get(GuestStats, guest_id)
    assert (stats.solved_count, stats.current_streak, stats.max_streak) == (0, 0, 0)
    assert stats.last_solved_date is None


def test_unlock_does_not_change_the_leaderboard_entry(client, today_puzzle):
    """힌트를 열고 1번째 시도에 맞춘 사람과 그냥 맞춘 사람이 같은 줄로 들어간다."""
    unlocker = issue_guest()
    _unlock(client, _headers(unlocker), today_puzzle.id)
    _guess(client, _headers(unlocker), today_puzzle.id, "사과")

    plain = issue_guest()
    _guess(client, _headers(plain), today_puzzle.id, "사과")

    body = client.get(
        "/api/v1/puzzles/today/leaderboard", headers=_headers(unlocker)
    ).get_json()

    attempts = {entry["display"]: entry["attempts"] for entry in body["entries"]}
    assert len(attempts) == 2
    assert set(attempts.values()) == {1}
    # 걸린 초(= 리더보드 점수의 tie-breaker)도 힌트 때문에 벌어지지 않는다.
    seconds = [entry["seconds"] for entry in body["entries"]]
    assert max(seconds) - min(seconds) <= 1
    assert body["me"]["attempts"] == 1
