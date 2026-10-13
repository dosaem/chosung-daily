"""Slack Incoming Webhook 래퍼. 네트워크 호출은 전부 가짜 requests.post 로 대체한다."""

import pytest
import requests

from app.clients import slack


class _RecordingPost:
    """requests.post 대역. 호출 인자를 기록하고 정해둔 응답/예외를 돌려준다."""

    def __init__(self, status_code=200, raises=None):
        self.calls = []
        self._status_code = status_code
        self._raises = raises

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = self._status_code
        return response


@pytest.fixture
def webhook_app(app):
    app.config["SLACK_WEBHOOK_URL"] = "https://hooks.slack.test/services/T000/B000/xxx"
    return app


def test_posts_text_with_three_second_timeout(webhook_app, monkeypatch):
    post = _RecordingPost()
    monkeypatch.setattr(slack.requests, "post", post)

    assert slack.post_webhook_message("단어 잔량 부족") is True

    (url, kwargs) = post.calls[0]
    assert url == webhook_app.config["SLACK_WEBHOOK_URL"]
    assert kwargs["json"] == {"text": "단어 잔량 부족"}
    assert kwargs["timeout"] == slack.TIMEOUT_SECONDS == 3


def test_is_no_op_when_webhook_url_is_empty(app, monkeypatch):
    app.config["SLACK_WEBHOOK_URL"] = ""
    post = _RecordingPost()
    monkeypatch.setattr(slack.requests, "post", post)

    assert slack.post_webhook_message("아무도 안 받는 알림") is False
    assert post.calls == []


def test_swallows_network_failure(webhook_app, monkeypatch):
    """알림 실패가 호출자(퍼즐 배정·백업)의 작업을 깨뜨리면 안 된다."""
    post = _RecordingPost(raises=requests.Timeout("too slow"))
    monkeypatch.setattr(slack.requests, "post", post)

    assert slack.post_webhook_message("배정 실패") is False


def test_swallows_error_status(webhook_app, monkeypatch):
    post = _RecordingPost(status_code=500)
    monkeypatch.setattr(slack.requests, "post", post)

    assert slack.post_webhook_message("배정 실패") is False
