from datetime import UTC, datetime, timedelta
from typing import NamedTuple

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
_APPLE_SECRET_EXTENSION_KEY = "chosung_apple_client_secrets"

# 애플이 허용하는 client_secret JWT 수명은 최대 6개월이다. 150일로 잡은 건 그
# 상한에 붙지 않게 여유를 둔 값이고, 갱신 창(7일)보다 훨씬 길어야 갱신이 요청
# 경로에서 어쩌다 한 번 일어난다(스펙 §A.13).
APPLE_SECRET_LIFETIME = timedelta(days=150)
APPLE_SECRET_RENEW_WITHIN = timedelta(days=7)


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

    # 웹 로그인용 Services ID 와 서명 키가 다 있어야 등록할 수 있다 — "서명할 수
    # 있는 client 목록"은 apple_client_ids 가 한 곳에서 판단한다.
    if app.config["APPLE_CLIENT_ID"] in apple_client_ids(app):
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


class _AppleClientSecret(NamedTuple):
    jwt: str
    expires_at: datetime


def _apple_secrets(app) -> dict[str, _AppleClientSecret]:
    """이 앱이 들고 있는 client_id 별 client_secret. redis 클라이언트·Authlib
    레지스트리와 같은 이유로 모듈 전역이 아니라 `app.extensions` 에 둔다 — 설정
    (서명 키·Services ID)이 앱마다 다르니 섞이면 엉뚱한 키로 서명한 secret 을 쓴다.
    """
    return app.extensions.setdefault(_APPLE_SECRET_EXTENSION_KEY, {})


def apple_client_secret(app, client_id: str) -> str:
    """애플 로그인에 쓸 유효한 client_secret JWT. 만료가 임박하면 재서명해 교체한다.

    애플은 client_secret 이 고정값이 아니라 ES256 으로 서명한 JWT(발급받은 .p8
    private key 로 서명)고, 수명이 최대 6개월이다. 예전엔 앱 시작 시점에 한 번만
    서명해뒀는데, 그러면 재배포 없이 프로세스가 150일을 넘기는 순간 애플 로그인만
    조용히 실패한다 — 다른 기능은 멀쩡해서 알아채기도 어렵다.

    그래서 Beat 로 재서명하는 대신 **요청 경로에서** 갱신한다(스펙 §A.13, README
    "설계 판단" 11). 갱신 결과는 외부에 저장하지 않고 이 프로세스의
    `app.extensions` 에만 둔다 — gunicorn 워커가 몇 개로 늘어도 각 워커가 자기 몫을
    스스로 갱신하고, 공유 저장소도 잠금도 필요 없다. 같은 secret 을 두 워커가 따로
    서명해도 애플 입장에선 둘 다 유효한 JWT 라 문제가 없다.

    `client_id`(= JWT 의 `sub`)를 인자로 받는 이유: 같은 키로 서명하지만 웹 로그인은
    Services ID, 앱 로그인은 앱 번들 ID 로 발급해야 애플이 받아준다
    (`app/services/app_login_service.py`). TEAM_ID·KEY_ID·private key 는 둘이 같다.
    공개 함수라 계정 삭제 때의 애플 revoke 경로도 이 접근자를 그대로 쓴다.
    """
    cached = _apple_secrets(app).get(client_id)
    if cached is not None and cached.expires_at - datetime.now(UTC) >= APPLE_SECRET_RENEW_WITHIN:
        return cached.jwt
    return _sign_apple_client_secret(app, client_id).jwt


def apple_client_ids(app) -> tuple[str, ...]:
    """client_secret 을 서명해야 하는 애플 client — 웹 Services ID 와 앱 번들 ID.

    Sign in with Apple 키 하나가 App ID 와 그 Services ID 를 모두 서명하기 때문에
    둘의 차이는 `sub` 뿐이다(스펙 "미정 17" 확정). 서명 키가 하나라도 비어 있으면
    아무것도 서명할 수 없으니 빈 튜플이다 — 호출부가 "애플이 설정 안 됨" 을 그걸로
    판단한다.
    """
    config = app.config
    if not all([config["APPLE_TEAM_ID"], config["APPLE_KEY_ID"], config["APPLE_PRIVATE_KEY"]]):
        return ()
    return tuple(
        client_id
        for client_id in (config["APPLE_CLIENT_ID"], config["APPLE_APP_BUNDLE_ID"])
        if client_id
    )


def apple_client_secret_expiries(app) -> dict[str, datetime]:
    """지금 이 프로세스가 들고 있는 client_id 별 client_secret 만료 시각.

    접근자와 달리 **갱신하지 않는다** — 관측이 갱신까지 하면 "만료 임박" 이 보이는
    순간 사라져서 Beat 만료 알림이 영원히 안 울리는 죽은 분기가 된다. 운영자가
    알아야 하는 건 "이 프로세스가 들고 있는 secret 이 언제 끝나는가" 그 자체다.

    아직 서명한 적 없는 client 는 여기서 한 번 서명한다. 번들 ID 쪽 secret 은 첫 앱
    로그인 때까지 안 만들어지는데, 그때까지 `/health` 가 절반만 보여주면 "채워진다"
    가 아니다. 애플 설정이 없으면 빈 딕셔너리.
    """
    return {
        client_id: _signed_apple_client_secret(app, client_id).expires_at
        for client_id in apple_client_ids(app)
    }


def apple_secret_expires_at(app) -> datetime | None:
    """애플 client_secret 중 **더 이른** 만료 시각. `/health` 가 이 값을 노출한다.
    애플 설정이 없으면 None."""
    expiries = apple_client_secret_expiries(app)
    return min(expiries.values()) if expiries else None


def _signed_apple_client_secret(app, client_id: str) -> _AppleClientSecret:
    """캐시에 있으면 그대로, 없으면 서명해서. 만료가 임박해도 교체하지 않는다."""
    cached = _apple_secrets(app).get(client_id)
    if cached is not None:
        return cached
    return _sign_apple_client_secret(app, client_id)


def _sign_apple_client_secret(app, client_id: str) -> _AppleClientSecret:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + APPLE_SECRET_LIFETIME
    token = jwt.encode(
        {
            "iss": app.config["APPLE_TEAM_ID"],
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "aud": "https://appleid.apple.com",
            "sub": client_id,
        },
        app.config["APPLE_PRIVATE_KEY"],
        algorithm="ES256",
        headers={"kid": app.config["APPLE_KEY_ID"]},
    )
    signed = _AppleClientSecret(token, expires_at)
    _apple_secrets(app)[client_id] = signed
    return signed


def get_oauth() -> OAuth | None:
    """현재 앱 컨텍스트의 OAuth 레지스트리를 돌려준다. get_redis()와 같은 이유,
    같은 패턴이다."""
    if not has_app_context():
        return None
    return current_app.extensions.get(_OAUTH_EXTENSION_KEY)
