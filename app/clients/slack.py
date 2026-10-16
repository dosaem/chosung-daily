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
    except requests.RequestException as exc:
        # Incoming Webhook 은 URL 경로 자체가 인증 비밀이다. requests 예외는
        # 메시지("... for url: <URL>")와 traceback 양쪽에 요청 URL 을 담으므로
        # `exc_info`·`str(exc)` 를 남기면 비밀이 로그 수집기로 복제된다. 디버깅에
        # 필요한 건 "어떤 실패였나" 뿐이라 예외 타입과 HTTP 상태 코드만 남긴다.
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        logger.warning("Slack webhook 전송 실패 (%s, status=%s)", type(exc).__name__, status)
        return False

    return True


# 봇 토큰 전송 — 채널을 호출부가 고른다(알림 채널 분리, 2026-10-16 사용자 결정: 프로젝트당
# `#<프로젝트>-alerts`(사람이 봐야 하는 것) / `#<프로젝트>-ops`(운영 알림)). Incoming Webhook 은
# URL 하나가 채널 하나에 묶여서 채널이 늘 때마다 OAuth 승인을 다시 받아야 하지만, 봇 토큰
# (`chat:write`)은 하나로 채널명을 지정해 보낸다. 토큰이 비면 예전 웹훅으로 떨어진다.
POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


def post_channel_message(channel: str, text: str) -> bool:
    token = current_app.config["SLACK_BOT_TOKEN"]
    if not token or not channel:
        return post_webhook_message(text)
    try:
        response = requests.post(
            POST_MESSAGE_URL,
            json={"channel": channel, "text": text},
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Slack chat.postMessage 전송 실패 (%s)", type(exc).__name__)
        return False
    if not body.get("ok"):
        # 토큰·채널 설정 문제(not_in_channel, channel_not_found 등)는 200 으로 온다.
        logger.warning("Slack chat.postMessage 거부: %s (channel=%s)", body.get("error"), channel)
        return False
    return True
