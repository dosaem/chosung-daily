import redis
from authlib.integrations.flask_client import OAuth
from flask import current_app, has_app_context
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

_REDIS_EXTENSION_KEY = "chosung_redis"
_OAUTH_EXTENSION_KEY = "chosung_oauth"


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


def init_oauth(app):
    """앱마다 새 OAuth() 인스턴스를 만들어서 app.extensions에 저장한다.

    처음엔 "Authlib이 db/migrate처럼 앱별로 알아서 관리해준다"고 믿고 모듈 전역
    `oauth = OAuth()` 하나를 여러 앱이 공유하게 했는데, 틀렸다. Authlib 소스를
    보면 OAuth.init_app(app)은 `self.app = app`으로 단일 참조를 덮어쓸 뿐이고,
    등록된 클라이언트는 `self._clients`에 **인스턴스 자신**한테 영구 캐싱된다
    (`create_client`가 처음 만든 걸 프로세스 수명 내내 재사용). redis_client와
    똑같은 함정이었다 — 여기서도 같은 해법(앱마다 따로 저장)으로 고친다.
    """
    client = OAuth()
    client.init_app(app)
    app.extensions[_OAUTH_EXTENSION_KEY] = client

    if app.config["GOOGLE_CLIENT_ID"]:
        client.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email"},
        )

    if app.config["KAKAO_CLIENT_ID"]:
        client.register(
            name="kakao",
            client_id=app.config["KAKAO_CLIENT_ID"],
            client_secret=app.config["KAKAO_CLIENT_SECRET"],
            access_token_url="https://kauth.kakao.com/oauth/token",
            authorize_url="https://kauth.kakao.com/oauth/authorize",
            api_base_url="https://kapi.kakao.com/",
            client_kwargs={"scope": "account_email"},
        )


def get_oauth() -> OAuth | None:
    """현재 앱 컨텍스트의 OAuth 레지스트리를 돌려준다. get_redis()와 같은 이유,
    같은 패턴이다."""
    if not has_app_context():
        return None
    return current_app.extensions.get(_OAUTH_EXTENSION_KEY)
