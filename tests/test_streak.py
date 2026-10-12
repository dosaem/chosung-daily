from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import Guest, GuestStats


def _today(headers):
    token = headers["Authorization"].removeprefix("Bearer ")
    return Guest.query.filter_by(token=token).one()


def test_streak_increments_when_solved_on_consecutive_day(client, guest_headers, today_puzzle):
    guest = _today(guest_headers)
    stats = db.session.get(GuestStats, guest.id)
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    stats.current_streak = 3
    stats.max_streak = 3
    stats.last_solved_date = yesterday
    db.session.commit()

    client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "사과"}
    )

    stats = db.session.get(GuestStats, guest.id)
    assert stats.current_streak == 4
    assert stats.max_streak == 4


def test_streak_resets_when_a_day_was_skipped(client, guest_headers, today_puzzle):
    guest = _today(guest_headers)
    stats = db.session.get(GuestStats, guest.id)
    two_days_ago = datetime.now(KST).date() - timedelta(days=2)
    stats.current_streak = 5
    stats.max_streak = 5
    stats.last_solved_date = two_days_ago
    db.session.commit()

    client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "사과"}
    )

    stats = db.session.get(GuestStats, guest.id)
    assert stats.current_streak == 1
    assert stats.max_streak == 5


def test_me_stats_endpoint_reflects_solve(client, guest_headers, today_puzzle):
    client.post("/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "사과"})

    res = client.get("/api/v1/me/stats", headers=guest_headers)
    body = res.get_json()

    assert body["current_streak"] == 1
    assert body["max_streak"] == 1
    assert body["solved_count"] == 1
