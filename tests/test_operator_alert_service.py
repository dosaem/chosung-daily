"""운영자 알림 서비스. Slack 래퍼를 monkeypatch 해서 제목·본문 조립만 검증한다."""

import pytest

from app.services import operator_alert_service
from app.services.operator_alert_service import notify_operator


@pytest.fixture
def sent(monkeypatch):
    messages = []
    monkeypatch.setattr(
        operator_alert_service, "post_webhook_message", lambda text: messages.append(text) or True
    )
    return messages


def test_sends_kind_and_message_in_one_slack_message(app, sent):
    assert notify_operator("단어 잔량 부족", "ko 12일치 남음 (임계 14일)") is True

    assert len(sent) == 1
    assert "단어 잔량 부족" in sent[0]
    assert "ko 12일치 남음 (임계 14일)" in sent[0]
    # 운영자가 Slack 채널에서 어느 서비스 알림인지 바로 알아야 한다.
    assert sent[0].startswith("[오늘의 초성]")
    # 제목과 본문이 한 줄로 붙으면 읽기 어렵다.
    assert "단어 잔량 부족\n" in sent[0]


def test_reports_wrapper_failure_without_raising(app, monkeypatch):
    monkeypatch.setattr(operator_alert_service, "post_webhook_message", lambda text: False)

    assert notify_operator("백업 실패", "mysqldump exit 1") is False
