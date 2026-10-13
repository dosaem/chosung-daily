from app.clients.slack import post_webhook_message

SERVICE_TAG = "[오늘의 초성]"


def notify_operator(kind: str, message: str) -> bool:
    """운영자에게 알림 한 건을 보낸다. 성공 여부를 돌려주되 예외는 내지 않는다.

    `kind` 는 알림 종류(= 제목), `message` 는 본문이다. 스펙 §A.12 가 정한
    종류: 단어 잔량 부족(언어별), 퍼즐 배정 실패, 백업 실패, 구독 재조회 실패
    누적, 애플 client_secret 만료 임박, Apple revoke 재시도 폐기.

    채널은 Slack Incoming Webhook 하나뿐이라 분기가 없다. 그래도 호출부가
    `app.clients.slack` 을 직접 쓰지 않는 이유는, 문구 조립(서비스 태그·제목·본문)
    이 도메인 결정이고 전송은 외부 호출이어서다 — 호출부 테스트는 이 함수를,
    전송 실패 처리 테스트는 래퍼를 본다.
    """
    return post_webhook_message(f"{SERVICE_TAG} {kind}\n{message}")
