"""스토어 응답 → 정규화된 구독 상태. 순수 함수만 둔다(스펙 §A.8, §A.17).

네트워크를 타는 쪽은 `app/clients/app_store.py`·`app/clients/play.py` 이고, 이
모듈은 그 응답을 받아 "우리 말" 로 옮기기만 한다. Apple 의 숫자 status 와
Google 의 `SUBSCRIPTION_STATE_*` 문자열을 서비스 코드 전체에 퍼뜨리지 않으려고
자른 경계다 — 스토어 규칙이 바뀌면 여기와 fixture 만 고친다.

입력은 라이브러리 객체가 아니라 평범한 dict 다. 그래야 fixture 를 스토어 응답
모양 그대로 둘 수 있고(`tests/fixtures/store/`), SDK 버전에 매핑 규칙이 묶이지
않는다. 래퍼가 디코딩 결과를 dict 로 넘겨준다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.models import SubscriptionStatus

# Apple: App Store Server API 의 구독 status 코드.
# https://developer.apple.com/documentation/appstoreserverapi/status
_APPLE_STATUS = {
    1: SubscriptionStatus.ACTIVE,
    2: SubscriptionStatus.EXPIRED,
    3: SubscriptionStatus.HOLD,  # Billing Retry — 결제 재시도 중, 권한 없음
    4: SubscriptionStatus.GRACE,  # Billing Grace Period — 유예 종료까지 권한 있음
    5: SubscriptionStatus.REVOKED,
}

# Google: purchases.subscriptionsv2 의 subscriptionState.
# PENDING 계열은 "아직 결제가 안 끝난 구매" 라 행을 만들지 않는다 → None.
# PAUSED 를 hold 와 같은 칸에 두는 건 "지금은 권한 없음, 돌아올 수 있음" 이
# 둘에게 같은 뜻이기 때문이다(스펙 미정 항목 14 확정).
_GOOGLE_STATE = {
    "SUBSCRIPTION_STATE_ACTIVE": SubscriptionStatus.ACTIVE,
    # 해지했지만 아직 만료 전. Google 이 만료되면 EXPIRED 로 바꿔 주므로 이
    # 상태는 그 자체로 "미만료" 다(US 30 — 낸 돈만큼은 광고 없이 쓴다).
    "SUBSCRIPTION_STATE_CANCELED": SubscriptionStatus.ACTIVE,
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": SubscriptionStatus.GRACE,
    "SUBSCRIPTION_STATE_ON_HOLD": SubscriptionStatus.HOLD,
    "SUBSCRIPTION_STATE_PAUSED": SubscriptionStatus.HOLD,
    "SUBSCRIPTION_STATE_EXPIRED": SubscriptionStatus.EXPIRED,
    "SUBSCRIPTION_STATE_PENDING": None,
    "SUBSCRIPTION_STATE_PENDING_PURCHASE_CANCELED": None,
}


@dataclass(frozen=True)
class NormalizedSubscription:
    """스토어가 말한 상태를 우리 컬럼 모양으로 옮긴 결과.

    `status is None` 은 "행을 만들지 않는다" 는 뜻이다 — Google 의 결제 대기
    구매가 그렇다(권한도 없음).
    """

    status: SubscriptionStatus | None
    expires_at: datetime | None
    grace_expires_at: datetime | None


def apple_subscription_status(
    raw_status: int, transaction: dict, renewal_info: dict
) -> NormalizedSubscription:
    """Apple 구독 하나(`lastTransactions[]` 항목)를 정규화한다.

    세 입력은 `status` 코드와, JWS 검증 후 디코딩한 거래 정보·갱신 정보다.
    만료 시각은 거래 정보에, 유예 종료 시각은 갱신 정보에 들어 있다.
    """
    status = _APPLE_STATUS.get(raw_status)
    if status is None:
        # 모르는 코드를 active 로 떨어뜨리면 "권한을 공짜로 주는" 쪽으로 틀린다.
        raise ValueError(f"Apple 구독 status 코드를 모른다: {raw_status}")

    grace_expires_at = None
    if status is SubscriptionStatus.GRACE:
        grace_expires_at = _from_epoch_millis(renewal_info.get("gracePeriodExpiresDate"))

    return NormalizedSubscription(
        status=status,
        expires_at=_from_epoch_millis(transaction.get("expiresDate")),
        grace_expires_at=grace_expires_at,
    )


def google_subscription_status(
    purchase: dict, *, revoked: bool = False
) -> NormalizedSubscription:
    """Google 구독 하나(`SubscriptionPurchaseV2` 응답)를 정규화한다.

    `revoked` 는 호출자가 "이 구매는 철회·환불됐다" 를 따로 알고 있을 때만
    켠다. v2 응답에는 철회 전용 필드가 없다 — 그 신호는 Voided Purchases API 나
    RTDN `SUBSCRIPTION_REVOKED` 에만 있고 둘 다 아직 도입 전이다(스펙 미정 항목
    1·14). 그래서 응답만 보고 revoked 를 추측하지 않는다. 환불이 실제로
    관측되는 모양은 "만료일 전에 EXPIRED 로 바뀌어 있음" 이고, expired 와
    revoked 는 권한 판정표에서 같은 칸(권한 없음)이라 결과가 달라지지 않는다.
    """
    state = purchase.get("subscriptionState")
    if state not in _GOOGLE_STATE:
        raise ValueError(f"Google subscriptionState 를 모른다: {state}")

    status = SubscriptionStatus.REVOKED if revoked else _GOOGLE_STATE[state]
    if status is None:
        return NormalizedSubscription(status=None, expires_at=None, grace_expires_at=None)

    expires_at = _google_expiry(purchase)
    # Google 은 유예 종료 시각을 따로 주지 않는다. 유예 중에는 `expiryTime` 자체가
    # 유예 종료 시각까지 연장돼 오므로 두 컬럼에 같은 값이 들어간다(미정 항목 14).
    grace_expires_at = expires_at if status is SubscriptionStatus.GRACE else None

    return NormalizedSubscription(
        status=status, expires_at=expires_at, grace_expires_at=grace_expires_at
    )


def _google_expiry(purchase: dict) -> datetime | None:
    """구독 상품은 `lineItems` 가 하나뿐이지만(한 상품 = 한 구독), Google 이
    배열로 주므로 가장 늦은 만료를 쓴다."""
    expiries = [
        _from_rfc3339(item.get("expiryTime"))
        for item in purchase.get("lineItems") or []
        if item.get("expiryTime")
    ]
    return max(expiries) if expiries else None


def _from_epoch_millis(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC).replace(tzinfo=None)


def _from_rfc3339(value: str | None) -> datetime | None:
    """Google 의 `google-datetime`(RFC 3339, 항상 UTC)을 naive UTC 로 바꾼다."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).replace(
        tzinfo=None
    )
