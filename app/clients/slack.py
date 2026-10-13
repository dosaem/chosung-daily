import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# 운영자 알림은 부가 기능이라 오래 기다릴 가치가 없다. 자정 배정 태스크가
# Slack 때문에 3초 넘게 멈추지 않도록 짧게 끊는다.
TIMEOUT_SECONDS = 3


def post_webhook_message(text: str) -> bool:
    """Slack Incoming Webhook 으로 메시지 한 건을 보내고 성공 여부를 돌려준다.

    `SLACK_WEBHOOK_URL` 이 비어 있으면 아무 것도 하지 않는다(개발·테스트 기본값).
    실패해도 예외를 호출자에게 던지지 않고 경고 로그만 남긴다 — 호출자는 퍼즐
    배정·백업 같은 본 작업이고, 알림이 안 갔다고 그 작업이 깨지면 안 된다.
    """
    url = current_app.config["SLACK_WEBHOOK_URL"]
    if not url:
        logger.info("SLACK_WEBHOOK_URL 이 없어 운영자 알림을 건너뜀")
        return False

    try:
        response = requests.post(url, json={"text": text}, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("Slack webhook 전송 실패", exc_info=True)
        return False

    return True
