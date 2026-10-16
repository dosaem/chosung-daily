from flask import current_app

from app.clients.slack import post_channel_message

SERVICE_TAG = "[오늘의 초성]"


def notify_operator(kind: str, message: str, *, channel: str = "ops") -> bool:
    """운영자에게 알림 한 건을 보낸다. 성공 여부를 돌려주되 예외는 내지 않는다.

    `kind` 는 알림 종류(= 제목), `message` 는 본문이다. 스펙 §A.12 가 정한
    종류: 단어 잔량 부족(언어별), 퍼즐 배정 실패, 백업 실패, 구독 재조회 실패
    누적, 애플 client_secret 만료 임박, Apple revoke 재시도 폐기.

    `channel` 은 용도 키다 — `"alerts"`(사람이 봐야 하는 것: 실패·만료·에러) 또는
    `"ops"`(잔량·생성·심사 요약 같은 운영 알림). 실제 채널명은 설정
    `SLACK_CHANNEL_ALERTS`/`SLACK_CHANNEL_OPS` 가 들고 있어 호출부는 채널명을 모른다.
    호출부가 `app.clients.slack` 을 직접 쓰지 않는 이유는, 문구 조립(서비스 태그·제목·
    본문)과 용도 분류가 도메인 결정이고 전송은 외부 호출이어서다 — 호출부 테스트는 이
    함수를, 전송 실패 처리 테스트는 래퍼를 본다.
    """
    return post_channel_message(channel_name(channel), f"{SERVICE_TAG} {kind}\n{message}")


def channel_name(channel: str) -> str:
    key = "SLACK_CHANNEL_ALERTS" if channel == "alerts" else "SLACK_CHANNEL_OPS"
    return current_app.config.get(key) or ""
