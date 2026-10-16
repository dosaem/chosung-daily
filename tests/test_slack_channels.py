"""운영자 알림의 채널 분리 — 봇 토큰이 있으면 용도별 채널로, 없으면 웹훅 하나로."""

import pytest
import requests

from app.clients import slack
from app.services.operator_alert_service import notify_operator


@pytest.fixture
def posts(monkeypatch):
    calls = []

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    def fake_post(url, json=None, timeout=None, headers=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return R()

    monkeypatch.setattr(slack.requests, "post", fake_post)
    return calls


def test_with_a_bot_token_alerts_and_ops_go_to_their_own_channels(app, posts):
    app.config["SLACK_BOT_TOKEN"] = "xoxb-test"
    app.config["SLACK_CHANNEL_ALERTS"] = "#chosung-alerts"
    app.config["SLACK_CHANNEL_OPS"] = "#chosung-ops"

    assert notify_operator("퍼즐 배정 실패", "ko", channel="alerts")
    assert notify_operator("단어 잔량 부족", "en")

    assert [c["url"] for c in posts] == [slack.POST_MESSAGE_URL] * 2
    assert posts[0]["json"]["channel"] == "#chosung-alerts"
    assert posts[1]["json"]["channel"] == "#chosung-ops"
    assert posts[0]["headers"]["Authorization"] == "Bearer xoxb-test"
    assert posts[0]["json"]["text"].startswith("[오늘의 초성] 퍼즐 배정 실패")


def test_without_a_bot_token_everything_falls_back_to_the_webhook(app, posts):
    app.config["SLACK_BOT_TOKEN"] = ""
    app.config["SLACK_WEBHOOK_URL"] = "https://hooks.slack.test/one"

    assert notify_operator("퍼즐 배정 실패", "ko", channel="alerts")
    assert posts[0]["url"] == "https://hooks.slack.test/one"
    assert "channel" not in posts[0]["json"]


def test_a_rejected_post_is_reported_as_failure_not_raised(app, monkeypatch):
    app.config["SLACK_BOT_TOKEN"] = "xoxb-test"

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": False, "error": "not_in_channel"}

    monkeypatch.setattr(slack.requests, "post", lambda *a, **k: R())
    assert notify_operator("x", "y") is False


def test_network_errors_do_not_raise(app, monkeypatch):
    app.config["SLACK_BOT_TOKEN"] = "xoxb-test"

    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(slack.requests, "post", boom)
    assert notify_operator("x", "y") is False
