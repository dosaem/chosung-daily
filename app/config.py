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

    # 광고 제거 구독(ADR 0003). 스토어에 앱과 상품을 등록해야 채워지는 값들이고,
    # 비어 있으면 app/clients/app_store.py·play.py 가 STORE_UNAVAILABLE(503)로
    # 막는다 — 개발·테스트에서 결제 없이 나머지 API 를 돌릴 수 있어야 한다.
    SUBSCRIPTION_PRODUCT_ID = os.environ.get("SUBSCRIPTION_PRODUCT_ID", "adfree_monthly")

    # App Store Server API. KEY_ID/ISSUER_ID/.p8 는 App Store Connect >
    # 사용자 및 액세스 > 통합 > In-App Purchase 키에서 같이 발급된다.
    # BUNDLE_ID 는 iOS 앱 번들 ID — 영수증(JWS)의 bundleId 와 대조하는 값이다.
    APP_STORE_BUNDLE_ID = os.environ.get("APP_STORE_BUNDLE_ID", "")
    # App Store Connect 의 숫자 앱 ID(Apple ID 필드). 공식 검증기가 Production
    # 환경에서 필수로 요구한다 — 비어 있으면 프로덕션 영수증을 아예 못 받는다.
    APP_STORE_APP_APPLE_ID = os.environ.get("APP_STORE_APP_APPLE_ID", "")
    APP_STORE_ISSUER_ID = os.environ.get("APP_STORE_ISSUER_ID", "")
    APP_STORE_KEY_ID = os.environ.get("APP_STORE_KEY_ID", "")
    # APPLE_PRIVATE_KEY 와 같은 요령으로 .p8 내용을 한 줄에 담는다. 로그인용
    # "Sign in with Apple" 키와는 다른 키다(용도가 달라 따로 발급해야 한다).
    APP_STORE_PRIVATE_KEY = os.environ.get("APP_STORE_PRIVATE_KEY", "").replace("\\n", "\n")
    # JWS 서명 체인을 검증할 Apple Root CA 인증서(.cer, DER) 경로들. Apple PKI
    # 페이지에서 받아 서버에 두고 콤마로 나열한다. 비어 있으면 검증을 할 수 없다.
    APP_STORE_ROOT_CERT_PATHS = os.environ.get("APP_STORE_ROOT_CERT_PATHS", "")

    # Google Play Developer API. 서비스 계정 JSON 키 파일 경로와 Android 패키지명.
    # Play Console > API 액세스에서 서비스 계정을 만들고 "재무 데이터" 권한을 준다.
    PLAY_PACKAGE_NAME = os.environ.get("PLAY_PACKAGE_NAME", "")
    PLAY_SERVICE_ACCOUNT_FILE = os.environ.get("PLAY_SERVICE_ACCOUNT_FILE", "")

    # Google Books API 키. **선택 설정**(스펙 미정 3) — 공개 volume 검색은 키
    # 없이도 되고, 키는 쿼터를 호출 IP 가 아니라 GCP 프로젝트에 붙이는 역할이다.
    # 비어 있으면 app/clients/google_books.py 가 키 없이 호출한다.
    GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

    # 운영자 알림(단어 잔량·배정 실패·백업 실패 등)을 받을 Slack Incoming Webhook.
    # 비어 있으면 app/clients/slack.py 가 전송을 건너뛴다 — 개발·테스트 기본값.
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
    # 봇 토큰 + 용도별 채널(2026-10-16). 토큰이 비면 위 웹훅 하나로 다 간다.
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ALERTS = os.environ.get("SLACK_CHANNEL_ALERTS", "#chosung-alerts")
    SLACK_CHANNEL_OPS = os.environ.get("SLACK_CHANNEL_OPS", "#chosung-ops")

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
    # [티켓 51] Sentry 내부 통합(Internal Integration) 웹훅 → Slack + GitHub 이슈 → Claude Code
    # Action. 비밀키가 비면 `/api/v1/ops/sentry` 는 503 으로 닫혀 있다.
    SENTRY_WEBHOOK_SECRET = os.environ.get("SENTRY_WEBHOOK_SECRET", "")
    # issues 쓰기만 되는 fine-grained PAT. 비면 GitHub 이슈 없이 Slack 만 간다(태스크가 알림).
    GITHUB_ISSUES_TOKEN = os.environ.get("GITHUB_ISSUES_TOKEN", "")
    GITHUB_ISSUES_REPO = os.environ.get("GITHUB_ISSUES_REPO", "dosaem/chosung-daily")
    OPS_ISSUE_LABEL = os.environ.get("OPS_ISSUE_LABEL", "sentry")

    # 로그인 CSRF 방어(app/api/oauth.py의 sync_session 독스트링 참고)의 핵심 설정.
    # SameSite=Lax면 공격자 사이트/링크를 통한 요청엔 이 세션 쿠키가 안 실린다.
    # Secure는 HTTPS 뒤에서만 쿠키를 보내게 하는 옵션인데, 로컬 개발(http)에선
    # 켜면 쿠키 자체가 안 먹어서 꺼둔다 — 실제 배포(HTTPS) 때는 반드시 켜야 한다.
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # 법적 문서(/privacy, /terms)에 싣는 공개 정보.
    # 연락처는 CONTEXT.md "운영자" 의 Play 조직 계정이라 기본값이 있고, 사업자 정보는
    # 아직 등록 전이라 전부 빈 문자열이다 — app/web.py 가 값이 있는 항목만 렌더하고
    # 전부 비면 서비스명과 연락처만 보여준다. 값을 코드에 지어 넣지 않는다
    # (출시 전 사람이 채울 값: docs/RELEASE.md "### 09.").
    # `.env` 에 키만 있고 값이 비어 있어도(= 빈 문자열이 환경에 들어온다) 기본값으로
    # 떨어지게 `or` 를 쓴다 — 문서의 연락처가 비는 건 스토어 심사에서 반려 사유다.
    #
    # 전화번호(`LEGAL_BUSINESS_PHONE`)와 보호책임자 성명(`LEGAL_PRIVACY_OFFICER`)은
    # 사용자 결정(2026-10-14, 스펙 미정 21)에 따라 **자리만 둔다**: 비면 그 행·성명을
    # 렌더하지 않고(전화는 미표시, 책임자는 직책 "운영자" 로 표기), 나중에 값을 채우면
    # 코드를 고치지 않고 표시된다. 주소도 같은 이유로 **값 자체를 사람이 축약해 넣는다**
    # (코드가 자르지 않는다 — 시·구까지만 + "상세 주소는 요청 시 제공").
    LEGAL_CONTACT_EMAIL = os.environ.get("LEGAL_CONTACT_EMAIL") or "hsseo@dosaem.com"
    LEGAL_BUSINESS_NAME = os.environ.get("LEGAL_BUSINESS_NAME", "")
    LEGAL_REPRESENTATIVE = os.environ.get("LEGAL_REPRESENTATIVE", "")
    LEGAL_BUSINESS_REG_NO = os.environ.get("LEGAL_BUSINESS_REG_NO", "")
    LEGAL_MAIL_ORDER_REG_NO = os.environ.get("LEGAL_MAIL_ORDER_REG_NO", "")
    LEGAL_BUSINESS_ADDRESS = os.environ.get("LEGAL_BUSINESS_ADDRESS", "")
    LEGAL_BUSINESS_PHONE = os.environ.get("LEGAL_BUSINESS_PHONE", "")
    LEGAL_PRIVACY_OFFICER = os.environ.get("LEGAL_PRIVACY_OFFICER", "")

    # 개인정보처리시스템 접속기록(감사 로그·접근 로그 파일)의 보관 기간.
    # **개인정보의 안전성 확보조치 기준**(개인정보보호위원회 고시 제2023-6호)
    # 제8조 제1항이 1년 이상을 요구한다. 2년 이상은 ① 5만명 이상 정보주체
    # ② 고유식별정보·민감정보 처리 ③ 기간통신사업자인 경우인데 이 서비스는 셋 다
    # 아니라서(수집 항목은 /privacy #collection) 기본값이 법정 최소치인 365일이다.
    # 정보주체가 5만명을 넘으면 이 값만 730 으로 올린다 — 코드는 안 고친다.
    # `.env.example` 처럼 키만 두고 값이 비어 있어도(= 빈 문자열) 기본값으로 떨어지게
    # `or` 를 쓴다 — `int("")` 는 ValueError 라 앱이 기동조차 못 한다.
    ACCESS_LOG_RETENTION_DAYS = int(os.environ.get("ACCESS_LOG_RETENTION_DAYS") or 365)

    # 운영자 페이지(/admin)에 들어올 수 있는 구글 계정 이메일. 쉼표로 여러 개.
    # **기본값 없음** — 설정을 깜빡한 환경에서는 아무도 운영자가 아니다(전부 403).
    # 판정은 세션의 게스트에 연결된 Account.email 로 한다(app/admin.py) — 세션에는
    # 이메일이 없고 게스트 ID 만 있다. 비교 전에 소문자로 맞춘다: 구글이 돌려주는
    # 이메일의 대소문자를 운영자가 .env 에서 맞춰 적게 만들지 않는다.
    ADMIN_EMAILS = tuple(
        email.strip().lower()
        for email in os.environ.get("ADMIN_EMAILS", "").split(",")
        if email.strip()
    )

    # Cloudflare Tunnel이 TLS를 엣지에서 끝내고 내부로는 평문 HTTP로 넘긴다.
    # 이걸 모르면 url_for(..., _external=True)가 OAuth redirect_uri를 http://로
    # 만들어버려서 구글/애플 콘솔에 등록한 https:// URI와 안 맞아 로그인이 막힌다
    # (실제로 겪은 문제). ProxyFix가 X-Forwarded-Proto를 읽어 스킴을 바로잡는다.
    TRUST_PROXY = False
    # 믿을 프록시 홉 수(ProxyFix x_for). cloudflared 만 있으면 1, 그 앞에 Caddy 가
    # 있으면 2(Caddy 가 XFF 뒤에 cloudflared 의 IP 를 덧붙인다 — docker-compose.prod.yml).
    # 틀리면 rate limit·접속기록이 모든 요청을 같은 IP 로 본다.
    PROXY_FIX_X_FOR = int(os.environ.get("PROXY_FIX_X_FOR") or 1)

    # [LLM 출제] Anthropic API. 키가 비면 생성 태스크는 아무것도 안 하고 끝난다
    # (dry-run·테스트는 HTTP 경계 mock 으로만 돈다 — 다른 프로젝트 키를 끌어다 쓰지
    # 않는다). 모델은 환경변수로 바꾼다; 단가표는 app/clients/anthropic.py.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "claude-sonnet-5-5")
    # 기능 플래그. 끄면 잔량 감지·어드민 버튼 모두 생성을 큐에 넣지 않는다.
    LLM_WORD_GENERATION_ENABLED = os.environ.get("LLM_WORD_GENERATION_ENABLED", "") in (
        "1",
        "true",
        "yes",
    )
    # 월 예산 상한(USD). 이번 달 llm_call.cost_usd 합이 넘으면 생성하지 않고 Slack 알림.
    LLM_MONTHLY_BUDGET_USD = float(os.environ.get("LLM_MONTHLY_BUDGET_USD") or 5)
    # 승인 안 된 후보가 이미 이만큼 쌓여 있으면 그 언어는 생성을 건너뛴다 —
    # 승인을 안 하는 동안 매일 과금되는 걸 막는다.
    LLM_MAX_PENDING_CANDIDATES = int(os.environ.get("LLM_MAX_PENDING_CANDIDATES") or 60)
    # 한 번에 요청하는 후보 수. 규칙·중복 탈락분을 감안해 필요량보다 넉넉히 받는다.
    LLM_CANDIDATES_PER_CALL = int(os.environ.get("LLM_CANDIDATES_PER_CALL") or 40)
    # 생성된 후보를 LLM 심사관이 한 번 더 보고 승인/거절까지 한다(사용자 결정 2026-10-16,
    # "검증까지 AI 로"). 끄면 후보는 승인 대기로 남고 운영자가 /admin/candidates 에서 본다.
    LLM_REVIEW_ENABLED = os.environ.get("LLM_REVIEW_ENABLED", "true") in ("1", "true", "yes")
    # 심사 모델. 비우면 생성 모델과 같다. 생성보다 센 모델(opus)을 쓰고 싶을 때 바꾼다.
    LLM_REVIEW_MODEL = os.environ.get("LLM_REVIEW_MODEL") or ""


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
