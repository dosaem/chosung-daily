import redis
from flask import current_app, has_app_context
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

_REDIS_EXTENSION_KEY = "chosung_redis"


def init_redis(app):
    client = redis.from_url(app.config["REDIS_URL"], decode_responses=True)
    app.extensions[_REDIS_EXTENSION_KEY] = client
    return client


def get_redis() -> redis.Redis | None:
    """현재 앱 컨텍스트의 redis 클라이언트를 돌려준다.

    예전엔 모듈 전역 변수 하나에 저장했는데, 그러면 Flask 앱 인스턴스가 두 개
    이상 생기는 순간(예: pytest 프로세스 안에서 테스트용 앱과 celery_app.py가
    자체적으로 만드는 앱이 공존할 때) 나중에 만들어진 앱이 전역을 덮어써서
    먼저 만든 앱이 엉뚱한 Redis(DB 인덱스)를 보게 되는 문제가 실제로 있었다.
    db/migrate가 Flask-SQLAlchemy/Flask-Migrate 내부에서 앱별로 상태를 들고
    있는 것과 같은 방식으로, redis 클라이언트도 `app.extensions`에 앱마다
    따로 저장한다.
    """
    if not has_app_context():
        return None
    return current_app.extensions.get(_REDIS_EXTENSION_KEY)
