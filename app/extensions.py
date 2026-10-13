import time

import jwt
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

    apple_configured = all(
        [
            app.config["APPLE_CLIENT_ID"],
            app.config["APPLE_TEAM_ID"],
            app.config["APPLE_KEY_ID"],
            app.config["APPLE_PRIVATE_KEY"],
        ]
    )
    if apple_configured:
        client.register(
            name="apple",
            client_id=app.config["APPLE_CLIENT_ID"],
            client_secret=apple_client_secret(app, app.config["APPLE_CLIENT_ID"]),
            server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
            client_kwargs={
                "scope": "name email",
                # 애플은 콜백을 GET 리다이렉트가 아니라 POST(form_post)로 보낸다 —
                # 그래서 app/api/oauth.py의 callback 라우트가 POST도 받는다.
                "response_mode": "form_post",
                # Authlib 기본값은 client_secret_basic(HTTP Basic 헤더)인데, 애플
                # 토큰 엔드포인트는 client_id/client_secret을 POST 바디로만 받는다
                # (실제로 겪음 — Basic으로 보내면 애플이 자격증명을 아예 못 읽고
                # invalid_client를 돌려줌. curl로 바디에 직접 넣어 보내면 정상
                # 통과하는 걸로 확인). authlib의 `register()`는 client_kwargs에
                # 담긴 값만 실제 OAuth2Client 생성자로 전달한다 — 바깥에 바로
                # 써도 조용히 무시된다.
                "token_endpoint_auth_method": "client_secret_post",
            },
        )


def apple_client_secret(app, client_id: str) -> str:
    """애플은 client_secret이 고정값이 아니라 ES256으로 서명한 JWT다(발급받은
    .p8 private key로 서명). 최대 6개월까지 유효하게 만들 수 있는데, 여기선
    150일로 넉넉히 잡았다 — 그보다 오래 앱 프로세스가 안 죽고 살아있으면(재배포도
    없이) 새로 발급해야 한다. 실제 애플 콘솔 등록 전까진 검증 못 해본 부분.

    `client_id`(= JWT 의 `sub`)를 인자로 받는 이유: 같은 키로 서명하지만 웹
    로그인은 Services ID, 앱 로그인은 앱 번들 ID 로 발급해야 애플이 받아준다
    (app/services/app_login_service.py). TEAM_ID·KEY_ID·private key 는 둘이 같다.
    """
    now = int(time.time())
    payload = {
        "iss": app.config["APPLE_TEAM_ID"],
        "iat": now,
        "exp": now + 60 * 60 * 24 * 150,
        "aud": "https://appleid.apple.com",
        "sub": client_id,
    }
    return jwt.encode(
        payload,
        app.config["APPLE_PRIVATE_KEY"],
        algorithm="ES256",
        headers={"kid": app.config["APPLE_KEY_ID"]},
    )


def get_oauth() -> OAuth | None:
    """현재 앱 컨텍스트의 OAuth 레지스트리를 돌려준다. get_redis()와 같은 이유,
    같은 패턴이다."""
    if not has_app_context():
        return None
    return current_app.extensions.get(_OAUTH_EXTENSION_KEY)
