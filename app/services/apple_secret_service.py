from datetime import UTC, datetime, timedelta

from flask import current_app

from app.extensions import apple_client_secret_expiries
from app.services.operator_alert_service import notify_operator

# 스펙 §A.13: 만료 7일 전이면 운영자에게 알린다. 접근자의 갱신 창(APPLE_SECRET_
# RENEW_WITHIN)과 같은 7일인 게 중요하다 — 요청 경로 갱신이 제대로 도는 프로세스는
# secret 이 이 구간에 머무르지 않아서 이 알림이 아예 안 울린다. 울렸다면 "갱신이
# 안 돌고 있다"는 신호다.
APPLE_SECRET_ALERT_WITHIN = timedelta(days=7)


def notify_apple_secret_expiry() -> bool:
    """Celery Beat 주 1회. 애플 client_secret 만료가 7일 안이면 운영자에게 알린다.

    알렸는지 여부를 돌려준다 — 태스크 로그와 테스트가 Slack 호출을 들여다보지 않고
    확인할 수 있게(`word_pool_service.notify_low_word_pool` 과 같은 규칙).

    왜 알림이 따로 필요한가: 갱신은 요청 경로에서 각 프로세스가 스스로 한다
    (`app/extensions.py` 의 `apple_client_secret`). 그 경로를 안 지나는 프로세스 —
    예를 들어 Beat 자신, 또는 애플 로그인이 한 건도 없던 워커 — 는 시작 시점에
    서명한 secret 을 그대로 들고 늙는다. 이 알림은 그 상태를 운영자에게 보여주는
    안전망이다. 그래서 `apple_client_secret_expiries` 는 관측만 하고 갱신하지 않는다
    (그쪽 독스트링 참고).

    메시지에 secret 자체(JWT)는 넣지 않는다 — Slack 채널로 서명된 자격증명을
    복제하는 셈이 된다. 운영자가 알아야 할 건 "어느 client 가 언제까지" 뿐이다.
    """
    now = datetime.now(UTC)
    expiring = {
        client_id: expires_at
        for client_id, expires_at in apple_client_secret_expiries(current_app).items()
        if expires_at - now < APPLE_SECRET_ALERT_WITHIN
    }
    if not expiring:
        return False

    notify_operator(
        "애플 client_secret 만료 임박",
        "\n".join(
            f"{client_id}: {_days_until(expires_at, now)}일 뒤 만료 ({expires_at.isoformat()})"
            for client_id, expires_at in sorted(expiring.items(), key=lambda item: item[1])
        ),
        channel="alerts",
    )
    return True


def _days_until(expires_at: datetime, now: datetime) -> int:
    """남은 일수. `timedelta.days` 로 자르면 "6일 뒤 만료"가 5일로 보인다(6일에서
    몇 마이크로초 모자란 값이라) — 운영자가 읽는 숫자라 버리지 않고 반올림한다."""
    return round((expires_at - now) / timedelta(days=1))
