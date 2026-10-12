import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

import app.extensions as extensions


class _BrokenRedis:
    """모든 메서드 호출이 Redis 장애를 흉내 낸다."""

    def __getattr__(self, _name):
        def _raise(*args, **kwargs):
            raise RedisConnectionError("simulated redis outage")

        return _raise


@pytest.fixture
def broken_redis(app, monkeypatch):
    monkeypatch.setattr(extensions, "_redis_client", _BrokenRedis())
    yield


def test_today_still_works_when_redis_is_down(client, guest_headers, today_puzzle, broken_redis):
    res = client.get("/api/v1/puzzles/today", headers=guest_headers)

    assert res.status_code == 200
    assert res.get_json()["chosung"] == "ㅅㄱ"


def test_guess_submission_still_works_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "사과"}
    )

    assert res.status_code == 200
    assert res.get_json()["is_correct"] is True


def test_stats_returns_empty_instead_of_erroring_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.get("/api/v1/puzzles/today/stats", headers=guest_headers)

    assert res.status_code == 200
    assert res.get_json()["total_solved"] == 0


def test_leaderboard_returns_empty_instead_of_erroring_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.get("/api/v1/puzzles/today/leaderboard", headers=guest_headers)

    assert res.status_code == 200
    assert res.get_json()["entries"] == []


def test_rate_limit_does_not_block_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    for _ in range(12):
        res = client.post(
            "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "바바"}
        )
        assert res.status_code != 429
