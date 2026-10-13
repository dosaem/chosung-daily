"""Sentry 초기화. 실제 DSN 으로 네트워크를 타지 않게 `sentry_sdk.init` 을
가로채서 "무엇을 들고 초기화하는지"만 본다 — 여기서 검증할 건 전송이 아니라
"DSN 이 없으면 아예 안 켠다 / 켤 땐 릴리스·환경 태그를 같이 넣는다" 라는 규칙이다.
"""

import pytest
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from app import create_app
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
