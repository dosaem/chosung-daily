import redis
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
_redis_client: redis.Redis | None = None


def init_redis(app):
    global _redis_client
    _redis_client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    return _redis_client


def get_redis() -> redis.Redis | None:
    """현재 redis 클라이언트를 돌려준다.

    `from app.extensions import redis_client`로 직접 가져오면 init_redis()가
    나중에 재할당한 값이 그 이름에는 안 보인다(바인딩 시점에 값이 복사됨).
    항상 이 함수로 조회해야 최신 클라이언트를 받는다.
    """
    return _redis_client
