"""구독 권한 판정표와 재조회 TTL — 순수 함수만 (티켓 13, 스펙 §A.8, ADR 0003).

DB·스토어·Flask 가 없다. 시계는 인자로 받으므로 "유예 3일째", "만료 1시간 뒤"
같은 상황을 실제 시간을 기다리지 않고 그대로 적는다 — 판정표가 틀리면 여기서
먼저 깨지고, 재조회·엔드포인트 테스트(`tests/test_subscription_recheck.py`)는
그 위에서 "언제 스토어를 다시 부르는가" 만 본다.
"""

from datetime import datetime, timedelta

import pytest

from app.models import Subscription, SubscriptionStatus
from app.services.entitlement import (
    NEAR_EXPIRY_RECHECK_INTERVAL,
    NEAR_EXPIRY_WINDOW,
    RECHECK_INTERVAL,
    RENEWAL_GRACE,
    is_entitled,
    is_recheck_due,
    recheck_interval,
)

NOW = datetime(2026, 10, 14, 12, 0, 0)


def test_an_active_subscription_keeps_the_entitlement_for_24h_after_expiry():
    """갱신은 됐는데 서버가 아직 모르는 구간을 흡수한다(스펙 §A.8 판정표)."""
    expires_at = NOW - timedelta(hours=23)

    assert is_entitled(SubscriptionStatus.ACTIVE, expires_at, None, NOW) is True


def test_an_active_subscription_loses_the_entitlement_after_the_24h_grace():
    expires_at = NOW - RENEWAL_GRACE - timedelta(seconds=1)

    assert is_entitled(SubscriptionStatus.ACTIVE, expires_at, None, NOW) is False


def test_a_canceled_but_unexpired_subscription_still_has_the_entitlement():
    """해지해도 만료일까지는 광고가 없다(US 30) — 스토어가 active 로 준다."""
    expires_at = NOW + timedelta(days=20)

    assert is_entitled(SubscriptionStatus.ACTIVE, expires_at, None, NOW) is True


def test_a_grace_subscription_has_the_entitlement_on_the_third_day():
    """결제 실패 유예(스토어 기본 3일)의 마지막 날에도 권한이 있다."""
    expires_at = NOW - timedelta(days=3)
    grace_expires_at = NOW + timedelta(hours=1)

    assert is_entitled(SubscriptionStatus.GRACE, expires_at, grace_expires_at, NOW) is True


def test_a_grace_subscription_loses_the_entitlement_when_the_grace_ends():
    grace_expires_at = NOW - timedelta(seconds=1)

    assert is_entitled(SubscriptionStatus.GRACE, NOW, grace_expires_at, NOW) is False


def test_a_grace_subscription_does_not_get_the_renewal_grace():
    """24h 유예는 "갱신됐는데 서버가 모름" 전용이다. 유예는 스토어가 준 종료
    시각이 전부라서, 그 시각이 지나면 24h 를 더 주지 않는다."""
    grace_expires_at = NOW - timedelta(hours=1)

    assert is_entitled(SubscriptionStatus.GRACE, NOW, grace_expires_at, NOW) is False


def test_a_hold_subscription_has_no_entitlement_even_before_expiry():
    """결제 보류(Apple Billing Retry / Google ON_HOLD)는 만료일이 미래여도 없음.
    확인된 보류에는 24h 유예를 적용하지 않는다."""
    expires_at = NOW + timedelta(days=20)

    assert is_entitled(SubscriptionStatus.HOLD, expires_at, None, NOW) is False


def test_a_revoked_subscription_loses_the_entitlement_immediately():
    """환불·철회는 만료일이 한참 남았어도 그 응답부터 권한이 없다."""
    expires_at = NOW + timedelta(days=20)

    assert is_entitled(SubscriptionStatus.REVOKED, expires_at, None, NOW) is False


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.EXPIRED, SubscriptionStatus.REVOKED, SubscriptionStatus.REPLACED],
)
def test_statuses_in_the_no_entitlement_column_never_grant_it(status):
    assert is_entitled(status, NOW + timedelta(days=20), NOW + timedelta(days=20), NOW) is False


def test_a_missing_timestamp_does_not_grant_the_entitlement():
    """시각이 비어 있으면 "미래까지 유효" 를 증명할 수 없다 — 권한을 주지 않는다."""
    assert is_entitled(SubscriptionStatus.ACTIVE, None, None, NOW) is False
    assert is_entitled(SubscriptionStatus.GRACE, NOW + timedelta(days=1), None, NOW) is False


def test_the_recheck_interval_is_an_hour_outside_the_expiry_window():
    assert recheck_interval(NOW + timedelta(days=20), NOW) == timedelta(hours=1)
    assert recheck_interval(NOW + timedelta(days=20), NOW) == RECHECK_INTERVAL


@pytest.mark.parametrize("offset", [-NEAR_EXPIRY_WINDOW, timedelta(0), NEAR_EXPIRY_WINDOW])
def test_the_recheck_interval_drops_to_five_minutes_around_the_expiry(offset):
    """만료 ±24h 는 갱신이 들어오는 구간이라 더 자주 본다. 상한을 아예 없애면
    호출마다 스토어 API 를 때리므로 5분을 둔다(미정 항목 18 확정)."""
    assert recheck_interval(NOW + offset, NOW) == timedelta(minutes=5)
    assert recheck_interval(NOW + offset, NOW) == NEAR_EXPIRY_RECHECK_INTERVAL


def test_the_expiry_window_is_24h_wide_on_both_sides():
    just_outside = NEAR_EXPIRY_WINDOW + timedelta(seconds=1)

    assert recheck_interval(NOW + just_outside, NOW) == RECHECK_INTERVAL
    assert recheck_interval(NOW - just_outside, NOW) == RECHECK_INTERVAL


def test_a_subscription_without_an_expiry_uses_the_hourly_interval():
    assert recheck_interval(None, NOW) == RECHECK_INTERVAL


def _row(status: SubscriptionStatus, *, verified_ago: timedelta, expires_in: timedelta):
    """DB 에 넣지 않는 구독 행. 재조회 판정은 컬럼 네 개만 보므로 세션이 없어도 된다."""
    return Subscription(
        status=status,
        expires_at=NOW + expires_in,
        grace_expires_at=None,
        last_verified_at=NOW - verified_ago,
    )


def test_the_recheck_is_due_exactly_at_the_next_check_time():
    """경계는 포함이다(미정 항목 19). 앱이 `next_check_at` 정각에 `/me/stats` 를
    부르면 그 호출이 재조회여야 한다 — 1초 더 기다리게 하면 앱과 서버의 해석이
    갈린다."""
    row = _row(
        SubscriptionStatus.ACTIVE,
        verified_ago=RECHECK_INTERVAL,
        expires_in=timedelta(days=20),
    )

    assert is_recheck_due(row, NOW) is True


def test_the_recheck_is_not_due_a_second_early():
    row = _row(
        SubscriptionStatus.ACTIVE,
        verified_ago=RECHECK_INTERVAL - timedelta(seconds=1),
        expires_in=timedelta(days=20),
    )

    assert is_recheck_due(row, NOW) is False


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE, SubscriptionStatus.HOLD],
)
def test_live_statuses_are_rechecked(status):
    row = _row(status, verified_ago=timedelta(days=1), expires_in=timedelta(days=20))

    assert is_recheck_due(row, NOW) is True


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.EXPIRED, SubscriptionStatus.REVOKED, SubscriptionStatus.REPLACED],
)
def test_finished_statuses_are_never_rechecked(status):
    """스토어가 끝났다고 말해준 행은 아무리 오래됐어도 다시 묻지 않는다."""
    row = _row(status, verified_ago=timedelta(days=365), expires_in=timedelta(days=20))

    assert is_recheck_due(row, NOW) is False


def test_near_the_expiry_the_recheck_is_due_after_five_minutes():
    row = _row(
        SubscriptionStatus.ACTIVE,
        verified_ago=NEAR_EXPIRY_RECHECK_INTERVAL,
        expires_in=timedelta(hours=1),
    )

    assert is_recheck_due(row, NOW) is True
