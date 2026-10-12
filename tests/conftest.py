from datetime import datetime

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app import create_app
from app.config import KST
from app.extensions import _REDIS_EXTENSION_KEY, db, get_redis
from app.models import DailyPuzzle, Word, WordCategory
from app.services.guest_service import issue_guest


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # 캐시/랭킹/통계/rate limit 전부 Redis 상태를 쓰기 때문에, 테스트 DB(인덱스 1)를
        # 비워두지 않으면 이전 테스트가 심어둔 puzzle:{date} 캐시나 ratelimit 카운터가
        # 다음 테스트로 샌다 (실제로 이걸 안 했다가 테스트가 깨졌었음).
        get_redis().flushdb()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    return db.session


@pytest.fixture
def today_puzzle(app):
    """오늘(KST) 날짜로 Word + DailyPuzzle을 만든다."""
    word = Word(answer="사과", category=WordCategory.GENERAL, hint="빨간 과일")
    db.session.add(word)
    db.session.flush()

    today = datetime.now(KST).date()
    puzzle = DailyPuzzle(puzzle_date=today, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


@pytest.fixture
def guest_headers(app):
    guest = issue_guest()
    return {"Authorization": f"Bearer {guest.token}"}


class _BrokenRedis:
    """모든 메서드 호출이 Redis 장애를 흉내 낸다."""

    def __getattr__(self, _name):
        def _raise(*args, **kwargs):
            raise RedisConnectionError("simulated redis outage")

        return _raise


@pytest.fixture
def broken_redis(app, monkeypatch):
    monkeypatch.setitem(app.extensions, _REDIS_EXTENSION_KEY, _BrokenRedis())
    yield
