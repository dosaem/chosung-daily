"""구독 행 → 권한(`entitlement`) 조립. 순수 함수만 둔다.

**이 티켓(12)에서는 임시 판정이다**: `status` 가 `active|grace` 면 권한 있음.
스펙 §A.8 의 판정표(active 는 만료 + 24h 까지, grace 는 `grace_expires_at` 까지,
확인된 revoked/hold 에는 유예를 주지 않음)와 재조회 TTL 은 티켓 13 이 이 함수를
바꿔 끼우며 완성한다. 지금은 "검증 엔드포인트가 뭘 돌려주나" 를 고정하는 게
목적이라 시계를 아예 보지 않는다 — 그래서 이 함수는 만료 비교를 하지 않는다.
"""

from datetime import UTC, datetime, timedelta

from app.models import Subscription, SubscriptionStatus
from app.schemas.subscription import EntitlementResponse

# 재조회 간격. 앱은 `next_check_at` 뒤에 `/me/stats` 를 다시 부른다(스펙 §A.8).
RECHECK_INTERVAL = timedelta(hours=1)

_ENTITLING_STATUSES = frozenset({SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE})

NO_ENTITLEMENT = EntitlementResponse(
    active=False, until=None, status=None, source=None, next_check_at=None
)


def build_entitlement(subscriptions: list[Subscription]) -> EntitlementResponse:
    """게스트가 가진 구독들에서 권한 하나를 만든다.

    목록을 받는 이유: 한 게스트가 애플에서 사고 안드로이드로 옮기면 행이 둘이
    된다. 권한을 주는 행이 있으면 그 중 가장 늦게까지 가는 것을 쓰고, 없으면
    가장 늦은 행의 상태를 그대로 알려준다(앱이 "결제 실패" 같은 걸 보여줄 수
    있게) — 다만 `active` 는 False 다.
    """
    if not subscriptions:
        return NO_ENTITLEMENT

    best = max(subscriptions, key=_entitlement_priority)
    return EntitlementResponse(
        active=best.status in _ENTITLING_STATUSES,
        until=_as_utc(_until_of(best)),
        status=best.status,
        source=best.store,
        next_check_at=_as_utc(best.last_verified_at + RECHECK_INTERVAL),
    )


def _entitlement_priority(subscription: Subscription) -> tuple[bool, datetime]:
    """권한을 주는 행이 먼저, 그 안에서는 더 늦게까지 가는 행이 먼저."""
    return (
        subscription.status in _ENTITLING_STATUSES,
        _until_of(subscription) or datetime.min,
    )


def _until_of(subscription: Subscription) -> datetime | None:
    """유예 중이면 유예 종료 시각이 "언제까지" 다 — 그 시점까지 광고가 없다."""
    if subscription.status is SubscriptionStatus.GRACE and subscription.grace_expires_at:
        return subscription.grace_expires_at
    return subscription.expires_at


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC)
