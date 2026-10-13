"""Slack Incoming Webhook 래퍼. 네트워크 호출은 전부 가짜 requests.post 로 대체한다."""

import logging
import traceback

import pytest
import requests

from app.clients import slack


class _RecordingPost:
    """requests.post 대역. 호출 인자를 기록하고 정해둔 응답/예외를 돌려준다."""

    def __init__(self, status_code=200, raises=None, url=None):
        self.calls = []
        self._status_code = status_code
        self._raises = raises
        self._url = url

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = self._status_code
        # 실제 응답은 요청 URL 을 들고 있다 — raise_for_status 의 에러 메시지에
        # 그 URL 이 들어가는 걸 재현해야 비밀 노출 회귀를 잡을 수 있다.
        response.url = self._url if self._url is not None else url
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


def test_failure_log_does_not_leak_webhook_url(webhook_app, monkeypatch, caplog):
    """Incoming Webhook URL 경로 자체가 인증 비밀이다 — 실패 로그로 새면 안 된다.

    실제 `Response.raise_for_status()` 가 만드는 HTTPError 는 메시지에 요청 URL 을
    담고, traceback 에도 URL 이 들어간다. 그래서 가짜 응답에도 URL 을 붙여 둔다.
    """
    url = webhook_app.config["SLACK_WEBHOOK_URL"]
    post = _RecordingPost(status_code=500, url=url)
    monkeypatch.setattr(slack.requests, "post", post)

    with caplog.at_level(logging.WARNING, logger=slack.logger.name):
        assert slack.post_webhook_message("배정 실패") is False

    assert caplog.records, "실패를 알리는 경고 로그는 남아야 한다"
    for record in caplog.records:
        rendered = record.getMessage()
        if record.exc_info is not None:
            rendered += "".join(traceback.format_exception(*record.exc_info))
        assert url not in rendered
        assert "T000" not in rendered


def test_failure_log_does_not_leak_url_from_exception_message(webhook_app, monkeypatch, caplog):
    """requests 가 던지는 예외 메시지에도 URL 이 들어온다 — 그 경로도 막아야 한다."""
    url = webhook_app.config["SLACK_WEBHOOK_URL"]
    post = _RecordingPost(raises=requests.Timeout(f"timed out for url: {url}"))
    monkeypatch.setattr(slack.requests, "post", post)

    with caplog.at_level(logging.WARNING, logger=slack.logger.name):
        assert slack.post_webhook_message("배정 실패") is False

    assert caplog.records
    for record in caplog.records:
        rendered = record.getMessage()
        if record.exc_info is not None:
            rendered += "".join(traceback.format_exception(*record.exc_info))
        assert url not in rendered
