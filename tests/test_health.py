import pytest
from sqlalchemy.exc import OperationalError

from app.extensions import db


@pytest.fixture
def broken_db(app, monkeypatch):
    """DB 쿼리가 전부 실패하는 상태. broken_redis(conftest.py)의 DB 버전이다."""

    def _raise(*_args, **_kwargs):
        raise OperationalError("SELECT 1", {}, Exception("simulated db outage"))

    monkeypatch.setattr(db.session, "execute", _raise)


def test_health_is_ok_when_db_and_redis_are_up(client):
    res = client.get("/health")

    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["redis"] == "ok"
    # 애플 설정이 있는 testing 설정에선 만료 시각이 채워진다 — 어떤 값인지는
    # tests/test_apple_secret_renewal.py 가 본다(티켓 11, 스펙 §A.13).
    assert body["apple_secret_expires_at"] is not None


def test_health_is_degraded_but_still_200_when_redis_is_down(client, broken_redis):
    """Redis 는 캐시·랭킹·통계용이라 죽어도 게임은 돌아간다 — 업타임 모니터가
    여기서 깨우면 안 된다(스펙 §C.29)."""
    res = client.get("/health")

    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "degraded"
    assert body["db"] == "ok"
    assert body["redis"] == "down"


def test_health_is_503_when_db_is_down(client, broken_db):
    res = client.get("/health")

    assert res.status_code == 503
    body = res.get_json()
    assert body["status"] == "down"
    assert body["db"] == "down"


def test_health_reports_db_down_even_if_redis_is_also_down(client, broken_db, broken_redis):
    res = client.get("/health")

    assert res.status_code == 503
    body = res.get_json()
    assert body["status"] == "down"
    assert body["db"] == "down"
    assert body["redis"] == "down"
    # 애플 secret 은 DB·Redis 와 무관하게 프로세스 안에서 서명한 값이라 그대로 나온다.
    assert body["apple_secret_expires_at"] is not None
    assert set(body) == {"status", "db", "redis", "apple_secret_expires_at"}
