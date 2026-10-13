import os
from typing import ClassVar
from zoneinfo import ZoneInfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

KST = ZoneInfo("Asia/Seoul")


class Config:
    TIMEZONE = KST
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily?charset=utf8mb4",
    )
    # MySQL 기본 격리수준(REPEATABLE READ)에서는 트랜잭션 안의 일반 SELECT가
    # 트랜잭션 시작 시점 스냅샷을 계속 본다 — SELECT ... FOR UPDATE로 잠금을
    # 걸고 기다려서 받아도, 그 뒤의 일반 SELECT는 잠금을 건 시점이 아니라
    # "이 트랜잭션이 맨 처음 뭔가를 읽은 시점"의 스냅샷을 쓴다. FOR UPDATE 기반
    # 동시성 제어(app/services/guess_service.py)가 막 커밋된 데이터를 보려면
    # READ COMMITTED가 필요하다 (MySQL 공식 문서가 이 조합을 권장).
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {
        "pool_pre_ping": True,
        "isolation_level": "READ COMMITTED",
    }
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # 운영자 알림(단어 잔량·배정 실패·백업 실패 등)을 받을 Slack Incoming Webhook.
    # 비어 있으면 app/clients/slack.py 가 전송을 건너뛴다 — 개발·테스트 기본값.
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

    # 구글/애플 콘솔에 앱을 등록해야 실제로 채워지는 값들. 비어 있으면 그 provider의
    # 로그인 버튼은 "설정 안 됨" 에러를 내도록 처리한다(app/extensions.py의 init_oauth).
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # 앱(네이티브) 구글 로그인이 보내는 id_token 의 aud 로 받아들일 클라이언트 ID.
    # iOS 는 iOS 클라이언트 ID, Android 는 serverClientId 로 넘긴 "웹" 클라이언트
    # ID 가 aud 에 들어온다(ADR 0002 의 aud 매트릭스). 비어 있으면 그 쪽 토큰은
    # 전부 INVALID_ID_TOKEN 이다 — 검증을 건너뛰지 않는다.
    GOOGLE_IOS_CLIENT_ID = os.environ.get("GOOGLE_IOS_CLIENT_ID", "")
    GOOGLE_WEB_CLIENT_ID = os.environ.get("GOOGLE_WEB_CLIENT_ID", "")

    # 애플은 client_secret이 고정값이 아니라 ES256으로 서명한 JWT다(매번
    # app/extensions.py의 apple_client_secret이 생성). 그래서 KEY_ID/TEAM_ID/
    # 서명용 private key까지 필요하다 — 구글보다 설정값이 하나 더 많다.
    # Services ID (예: com.chosungdaily.web)
    APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "")
    APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "")
    APPLE_KEY_ID = os.environ.get("APPLE_KEY_ID", "")
    # .p8 파일 내용(PEM) 그대로. .env 한 줄에 넣어야 해서 줄바꿈을 "\n" 문자로
    # 넣으면 아래서 실제 줄바꿈으로 되돌린다.
    APPLE_PRIVATE_KEY = os.environ.get("APPLE_PRIVATE_KEY", "").replace("\\n", "\n")
    # 앱(iOS) 애플 로그인용 client. 웹은 Services ID(APPLE_CLIENT_ID), 앱은 앱 번들
    # ID 를 aud 로 받고 client_secret 도 번들 ID 로 서명해야 애플이 받아준다
    # (TEAM_ID/KEY_ID/private key 는 웹과 같은 값을 쓴다 — Sign in with Apple 키
    # 하나가 같은 App ID 와 그 Services ID 를 모두 서명한다).
    APPLE_APP_BUNDLE_ID = os.environ.get("APPLE_APP_BUNDLE_ID", "")

    # 스토어 링크. `GET /api/v1/config` 의 store_urls 와 웹 Smart App Banner
    # (티켓 18)가 같은 값을 쓴다 — 스토어에 앱을 올리기 전에는 비어 있고, 그때
    # /config 응답에는 null 로 나간다.
    STORE_URL_IOS = os.environ.get("STORE_URL_IOS", "")
    STORE_URL_ANDROID = os.environ.get("STORE_URL_ANDROID", "")
    # App Store 숫자 ID. Smart App Banner 메타 태그(`app-id=...`)에만 쓰고
    # /config 응답에는 넣지 않는다(스펙 §A' 응답 필드 4개).
    APP_STORE_ID = os.environ.get("APP_STORE_ID", "")

    # 비어 있으면 Sentry 를 아예 초기화하지 않는다(app/observability.py).
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    # 릴리스 태그. 배포 스크립트가 배포한 커밋을 넣는다 — 비어 있으면 Sentry
    # 이벤트에 릴리스 없이 환경만 붙는다.
    SENTRY_RELEASE = os.environ.get("SENTRY_RELEASE", "")

    # 로그인 CSRF 방어(app/api/oauth.py의 sync_session 독스트링 참고)의 핵심 설정.
    # SameSite=Lax면 공격자 사이트/링크를 통한 요청엔 이 세션 쿠키가 안 실린다.
    # Secure는 HTTPS 뒤에서만 쿠키를 보내게 하는 옵션인데, 로컬 개발(http)에선
    # 켜면 쿠키 자체가 안 먹어서 꺼둔다 — 실제 배포(HTTPS) 때는 반드시 켜야 한다.
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # Cloudflare Tunnel이 TLS를 엣지에서 끝내고 내부로는 평문 HTTP로 넘긴다.
    # 이걸 모르면 url_for(..., _external=True)가 OAuth redirect_uri를 http://로
    # 만들어버려서 구글/애플 콘솔에 등록한 https:// URI와 안 맞아 로그인이 막힌다
    # (실제로 겪은 문제). ProxyFix가 X-Forwarded-Proto를 읽어 스킴을 바로잡는다.
    TRUST_PROXY = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test?charset=utf8mb4",
    )
    REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")
    # 테스트에서도 OAuth 클라이언트가 "등록은 돼 있는" 상태를 보려고 더미 값을 둔다.
    # 실제 제공자에 네트워크 요청하는 지점(authorize_access_token 등)까진 테스트가
    # 안 가니, 이 값이 진짜 유효한 키일 필요는 없다 — 라우팅/가드 로직만 검증한다.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "test-google-client-id")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "test-google-client-secret")

    GOOGLE_IOS_CLIENT_ID = os.environ.get("GOOGLE_IOS_CLIENT_ID", "test-ios-client-id")
    GOOGLE_WEB_CLIENT_ID = os.environ.get("GOOGLE_WEB_CLIENT_ID", "test-web-client-id")

    APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "com.example.test")
    APPLE_APP_BUNDLE_ID = os.environ.get("APPLE_APP_BUNDLE_ID", "com.example.test.app")
    APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "TESTTEAMID")
    APPLE_KEY_ID = os.environ.get("APPLE_KEY_ID", "TESTKEYID")
    # ES256 서명엔 진짜 형식을 갖춘 EC 개인키가 있어야 해서(문자열 더미로는 안 됨),
    # 테스트 프로세스 안에서 한 번 쓰고 버릴 키를 즉석에서 만든다.
    APPLE_PRIVATE_KEY = (
        ec.generate_private_key(ec.SECP256R1())
        .private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        .decode()
    )


class ProductionConfig(Config):
    TRUST_PROXY = True

    # 애플은 콜백을 cross-site top-level POST(response_mode=form_post)로 보낸다.
    # SameSite=Lax 쿠키는 cross-site POST엔 기본적으로 안 실려서(실제로 겪음 —
    # /auth/apple/login에서 심은 oauth_pending_guest_id 세션이 콜백에서 안 보임,
    # UnauthorizedError "로그인 세션이 만료됐습니다"), 세션 쿠키를 None으로 풀어야
    # 애플 로그인이 동작한다. 브라우저는 SameSite=None 쿠키에 Secure가 없으면
    # 통째로 버리므로, env var 설정을 깜빡해도 깨지지 않게 여기서 강제한다.
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
