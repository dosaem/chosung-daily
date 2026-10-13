import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration


def init_sentry(app) -> bool:
    """`SENTRY_DSN` 이 있을 때만 Sentry 를 켠다. 켰으면 True.

    초기화 지점이 create_app() 하나인 이유: Celery worker/beat 도 celery_app.py
    에서 create_app() 으로 Flask 앱을 만들어 쓰기 때문에, 여기서 Flask·Celery
    통합을 같이 등록하면 웹·워커가 같은 설정을 탄다. 웹 프로세스에 걸린 Celery
    통합은 할 일이 없을 뿐 해롭지 않다.

    `send_default_pii=False` 는 기본값이지만 명시한다 — 개인정보처리방침
    (스펙 §A.15)에 Sentry 를 수탁자로 적어둔 만큼, 요청 쿠키·바디가 자동으로
    따라가지 않는다는 걸 코드에서 바로 읽히게 두려는 의도다.
    """
    dsn = app.config["SENTRY_DSN"]
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration(), CeleryIntegration()],
        environment=app.config["ENV_NAME"],
        release=app.config["SENTRY_RELEASE"] or None,
        send_default_pii=False,
    )
    return True
