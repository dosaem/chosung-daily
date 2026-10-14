"""구독 행 → 권한(`entitlement`) 판정. 순수 함수만 둔다(스펙 §A.8, ADR 0003).

판정표가 이 모듈의 전부다. 시계는 **인자로 받는다** — 스토어 호출도 DB 도
없으니 "유예 3일째", "만료 1시간 뒤" 같은 상황을 테스트가 그대로 적을 수 있다
(`tests/test_entitlement.py`). 스토어를 다시 부르는 쪽은
`app/services/subscription_recheck.py` 이고, 이 모듈은 "언제 다시 물어볼
때가 됐나" 까지만 계산한다.
"""

from datetime import UTC, datetime, timedelta

from app.models import Subscription, SubscriptionStatus
from app.schemas.subscription import EntitlementResponse

# 갱신 유예. "갱신은 됐는데 서버가 아직 모름" 만 흡수한다 — 확인된 철회·보류에는
# 적용하지 않는다(그래서 아래 판정표에서 active 에만 더한다).
RENEWAL_GRACE = timedelta(hours=24)

# 재조회 간격. 앱은 `next_check_at` 뒤에 `/me/stats` 를 다시 부른다(스펙 §A.8).
RECHECK_INTERVAL = timedelta(hours=1)

# 만료 ±24h 는 갱신이 실제로 들어오는 구간이라 더 자주 본다. 스펙 본문은 이
# 구간을 "상한 없이 매 호출 재조회" 로 뒀는데, 그러면 앱이 포그라운드에서
# `/me/stats` 를 부르는 만큼 스토어 API 를 때린다 — 5분 상한을 둔다
# (미정 항목 18 확정). 갱신 반영이 최대 5분 늦지만, 그 구간은 24h 유예가
# 이미 권한을 유지해 주는 구간이라 사용자가 광고를 보지는 않는다.
NEAR_EXPIRY_WINDOW = timedelta(hours=24)
NEAR_EXPIRY_RECHECK_INTERVAL = timedelta(minutes=5)

# 재조회 대상 상태. 나머지(expired·revoked·replaced)는 스토어가 "끝났다" 고
# 말해준 상태라 다시 물어볼 이유가 없다 — 되살아나면 앱이 영수증을 다시 올린다.
RECHECKABLE_STATUSES = frozenset(
    {SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE, SubscriptionStatus.HOLD}
)

NO_ENTITLEMENT = EntitlementResponse(
    active=False, until=None, status=None, source=None, next_check_at=None
)


def is_entitled(
    status: SubscriptionStatus,
    expires_at: datetime | None,
    grace_expires_at: datetime | None,
    now: datetime,
) -> bool:
    """이 구독 하나가 지금 광고를 끌 자격이 있나 — 스펙 §A.8 판정표 그대로다.

    - `revoked|hold|expired|replaced` → 없음 (확인된 상태에는 유예를 안 준다)
    - `grace` → `grace_expires_at > now` (스토어가 준 유예 종료까지)
    - `active` → `expires_at + 24h > now`

    시각이 비어 있으면 없음이다. `grace` 인데 `grace_expires_at` 이 없는 건
    데이터 이상이고(스토어 둘 다 유예 종료 시각을 준다), 그때는 "미래까지
    유효" 를 증명할 수 없으니 권한을 주지 않는다 — 다음 재조회가 값을 채운다.
    """
    if status is SubscriptionStatus.ACTIVE:
        return expires_at is not None and expires_at + RENEWAL_GRACE > now
    if status is SubscriptionStatus.GRACE:
        return grace_expires_at is not None and grace_expires_at > now
    return False


def recheck_interval(expires_at: datetime | None, now: datetime) -> timedelta:
    """이 구독을 다시 물어보기까지 기다릴 시간. 만료 ±24h 안이면 5분이다."""
    if expires_at is not None and abs(now - expires_at) <= NEAR_EXPIRY_WINDOW:
        return NEAR_EXPIRY_RECHECK_INTERVAL
    return RECHECK_INTERVAL


def is_recheck_due(subscription: Subscription, now: datetime) -> bool:
    """재조회할 때가 됐나. 경계(`now == last_verified_at + 간격`)는 포함이다 —
    앱이 `next_check_at` 정각에 `/me/stats` 를 부르면 그 호출이 재조회여야
    한다(미정 항목 19)."""
    if subscription.status not in RECHECKABLE_STATUSES:
        return False
    due_at = subscription.last_verified_at + recheck_interval(subscription.expires_at, now)
    return now >= due_at


def build_entitlement(subscriptions: list[Subscription], now: datetime) -> EntitlementResponse:
    """게스트가 가진 구독들에서 권한 하나를 만든다.

    목록을 받는 이유: 한 게스트가 애플에서 사고 안드로이드로 옮기면 행이 둘이
    된다. 권한을 주는 행이 있으면 그 중 가장 늦게까지 가는 것을 쓰고, 없으면
    가장 늦은 행의 상태를 그대로 알려준다(앱이 "결제 실패" 같은 걸 보여줄 수
    있게) — 다만 `active` 는 False 다.
    """
    if not subscriptions:
        return NO_ENTITLEMENT

    best = max(subscriptions, key=lambda row: _entitlement_priority(row, now))
    return EntitlementResponse(
        active=_is_entitled(best, now),
        until=_as_utc(_until_of(best)),
        status=best.status,
        source=best.store,
        next_check_at=_as_utc(best.last_verified_at + RECHECK_INTERVAL),
    )


def _is_entitled(subscription: Subscription, now: datetime) -> bool:
    return is_entitled(
        subscription.status, subscription.expires_at, subscription.grace_expires_at, now
    )


def _entitlement_priority(subscription: Subscription, now: datetime) -> tuple[bool, datetime]:
    """권한을 주는 행이 먼저, 그 안에서는 더 늦게까지 가는 행이 먼저."""
    return (_is_entitled(subscription, now), _until_of(subscription) or datetime.min)


def _until_of(subscription: Subscription) -> datetime | None:
    """유예 중이면 유예 종료 시각이 "언제까지" 다 — 그 시점까지 광고가 없다."""
    if subscription.status is SubscriptionStatus.GRACE and subscription.grace_expires_at:
        return subscription.grace_expires_at
    return subscription.expires_at


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC)
