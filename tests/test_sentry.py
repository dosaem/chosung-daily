"""Sentry 초기화와, 실제로 떠나는 이벤트에 무엇이 담기는지.

두 층으로 본다. 앞쪽은 `sentry_sdk.init` 을 가로채서 "무엇을 들고 초기화하는지"만
확인한다("DSN 이 없으면 아예 안 켠다 / 켤 땐 릴리스·환경 태그를 같이 넣는다").
뒤쪽(`captured_events` 아래)은 진짜 SDK 를 켜고 Transport 만 메모리로 바꿔서 완성된
이벤트 payload 를 들여다본다 — 초기화 인자만 보던 때 요청 본문에 OAuth 인증 코드가
실려 나가는 걸 놓쳤기 때문이다. 둘 다 네트워크는 타지 않는다.
"""

import json

import pytest
import sentry_sdk
from celery import Celery
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.transport import Transport

from app import create_app
from app.extensions import db
from app.models import AccessLog
from app.observability import init_sentry

FAKE_DSN = "https://examplepublickey@o0.ingest.sentry.io/0"


@pytest.fixture
def init_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    return calls


def test_sentry_stays_off_without_a_dsn(init_calls):
    app = create_app("testing")

    assert app.config["SENTRY_DSN"] == ""
    assert init_sentry(app) is False
    assert init_calls == []


def test_sentry_init_carries_release_and_environment_tags(init_calls):
    app = create_app("testing")
    app.config["SENTRY_DSN"] = FAKE_DSN
    app.config["SENTRY_RELEASE"] = "abc1234"

    assert init_sentry(app) is True

    (kwargs,) = init_calls
    assert kwargs["dsn"] == FAKE_DSN
    assert kwargs["release"] == "abc1234"
    assert kwargs["environment"] == "testing"


def test_sentry_init_registers_both_flask_and_celery_integrations(init_calls):
    app = create_app("testing")
    app.config["SENTRY_DSN"] = FAKE_DSN

    init_sentry(app)

    (kwargs,) = init_calls
    integrations = {type(integration) for integration in kwargs["integrations"]}
    assert integrations == {FlaskIntegration, CeleryIntegration}


def test_release_is_omitted_when_not_set(init_calls):
    app = create_app("testing")
    app.config["SENTRY_DSN"] = FAKE_DSN

    init_sentry(app)

    (kwargs,) = init_calls
    assert kwargs["release"] is None


def test_create_app_initializes_sentry(monkeypatch):
    """워커도 celery_app.py 가 create_app() 을 거치니, 초기화 지점은 여기 하나다."""
    initialized = []
    monkeypatch.setattr("app.init_sentry", initialized.append)

    app = create_app("testing")

    assert initialized == [app]


@pytest.fixture
def captured_events(monkeypatch):
    """실제 SDK 를 켜고 전송만 메모리로 돌린다.

    위 테스트들은 `sentry_sdk.init` 을 가로채서 "무엇을 들고 초기화하는지"만 본다.
    그 검증은 "실제로 떠나는 이벤트에 무엇이 담기나" 를 못 본다 — 최종 리뷰에서
    `send_default_pii=False` 만으로는 요청 본문이 그대로 실려 나가는 걸 그래서
    놓쳤다. 여기서는 진짜 `sentry_sdk.init` 을 호출하고 Transport 만 메모리로
    바꿔서 완성된 이벤트 payload 를 그대로 들여다본다(네트워크는 타지 않는다).
    """
    events = []

    class _MemoryTransport(Transport):
        def capture_envelope(self, envelope):
            for item in envelope.items:
                if item.headers.get("type") == "event":
                    events.append(item.payload.json)

        def flush(self, *_args, **_kwargs):
            pass

        def kill(self):
            pass

    real_init = sentry_sdk.init
    monkeypatch.setattr(
        sentry_sdk, "init", lambda **kwargs: real_init(transport=_MemoryTransport(), **kwargs)
    )
    yield events
    # 전역 클라이언트가 다음 테스트로 새지 않게 비활성 클라이언트로 되돌린다.
    sentry_sdk.get_client().close()
    real_init(dsn=None)


@pytest.fixture
def sentry_app(captured_events):
    app = create_app("testing")
    app.config["SENTRY_DSN"] = FAKE_DSN
    app.config["SENTRY_RELEASE"] = "regression"
    # TESTING=True 면 Flask 가 예외를 테스트로 다시 던져서 500 핸들러·Sentry 캡처
    # 경로를 안 탄다. 실제 운영과 같은 경로를 보려고 끈다.
    app.config["TESTING"] = False
    assert init_sentry(app) is True
    # 이 fixture 는 conftest 의 `app` 과 달리 자기 앱을 만들어서 스키마가 없다.
    # 콜백은 접속기록 대상이라(티켓 36, `account.link`) 응답 훅이 행을 남기는데,
    # 테이블이 없으면 그 실패가 ERROR 로그 → Sentry 이벤트 하나를 **더** 만들어서
    # 아래 "이벤트 1건" 단언이 2건으로 깨진다. 운영에서는 테이블이 있으니, 여기서도
    # 그 테이블만 만들어 같은 경로를 보게 한다(다른 테이블은 건드리지 않는다).
    with app.app_context():
        AccessLog.__table__.create(db.engine, checkfirst=True)
    yield app
    with app.app_context():
        db.session.remove()
        AccessLog.__table__.drop(db.engine, checkfirst=True)


@pytest.fixture
def boom_oauth(monkeypatch):
    """OAuth 제공자 호출 지점에서 터뜨린다 — 외부 요청 없이 콜백 500 을 만든다."""

    class _BoomClient:
        def authorize_access_token(self):
            raise RuntimeError("provider unavailable (local test)")

    monkeypatch.setattr("app.api.oauth._get_client", lambda _provider: _BoomClient())


def _flush_and_get_one(events):
    sentry_sdk.flush()
    assert len(events) == 1, events
    return events[0]


def test_oauth_callback_error_is_reported_without_the_request_body(
    sentry_app, captured_events, boom_oauth
):
    """애플 콜백은 `code` 와 최초 로그인 `user` JSON 을 form POST 로 보낸다."""
    client = sentry_app.test_client()
    with client.session_transaction() as sess:
        sess["oauth_pending_guest_id"] = 1

    resp = client.post(
        "/api/v1/auth/apple/callback",
        data={
            "code": "sentinel-authorization-code",
            "user": json.dumps({"email": "sentinel@example.test"}),
            "id_token": "sentinel-id-token",
        },
    )

    assert resp.status_code == 500
    event = _flush_and_get_one(captured_events)
    assert "data" not in event.get("request", {})
    blob = json.dumps(event, ensure_ascii=False)
    for sentinel in ("sentinel-authorization-code", "sentinel@example.test", "sentinel-id-token"):
        assert sentinel not in blob, sentinel


def test_oauth_callback_error_is_reported_without_the_query_string(
    sentry_app, captured_events, boom_oauth
):
    """구글 콜백은 같은 인증 코드를 `?code=` 쿼리로 보낸다."""
    client = sentry_app.test_client()
    with client.session_transaction() as sess:
        sess["oauth_pending_guest_id"] = 1

    resp = client.get("/api/v1/auth/google/callback?code=sentinel-query-code&state=xyz")

    assert resp.status_code == 500
    event = _flush_and_get_one(captured_events)
    assert "query_string" not in event.get("request", {})
    assert "sentinel-query-code" not in json.dumps(event, ensure_ascii=False)


def test_error_report_still_carries_the_exception_environment_and_release(
    sentry_app, captured_events, boom_oauth
):
    """민감정보를 막는 설정이 "오류 보고 자체" 를 끄지는 않았다는 확인."""
    client = sentry_app.test_client()
    with client.session_transaction() as sess:
        sess["oauth_pending_guest_id"] = 1

    client.post("/api/v1/auth/apple/callback", data={"code": "sentinel-authorization-code"})

    event = _flush_and_get_one(captured_events)
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "RuntimeError"
    assert event["environment"] == "testing"
    assert event["release"] == "regression"
    assert event["request"]["url"].endswith("/api/v1/auth/apple/callback")
    assert event["request"]["method"] == "POST"
    # 쿠키·IP 는 여전히 안 따라간다. Cookie 헤더는 SDK 가 `[Filtered]` 로 바꾼다.
    assert "cookies" not in event["request"]
    assert event["request"]["headers"]["Cookie"] == "[Filtered]"
    assert "user" not in event


def test_celery_task_error_is_reported_without_the_task_arguments(sentry_app, captured_events):
    """워커 쪽도 같은 설정을 탄다 — 오류는 올라가고 task 인자는 안 올라간다.

    프로젝트 Celery 앱(`celery_app.py`)은 import 시점에 브로커 설정을 읽으니,
    통합이 걸렸는지만 보면 되는 여기서는 일회용 Celery 앱으로 확인한다.
    """
    celery = Celery("test", broker="memory://")

    @celery.task(name="tasks.boom")
    def boom(nickname):
        raise RuntimeError("task failed (local test)")

    result = boom.apply(args=["sentinel-nickname"], throw=False)

    assert result.failed()
    event = _flush_and_get_one(captured_events)
    (exception,) = event["exception"]["values"]
    assert exception["type"] == "RuntimeError"
    # task 이름만 남고 args/kwargs 는 아예 안 실린다.
    assert event["extra"]["celery-job"] == {"task_name": "tasks.boom"}
    assert "sentinel-nickname" not in json.dumps(event["extra"], ensure_ascii=False)
