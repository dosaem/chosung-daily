"""구독 영수증 검증과 저장. 함수 하나 = 커밋 하나(이 레포 트랜잭션 규칙).

흐름은 스펙 §A.8 의 "검증·완료 순서" 그대로다: 앱이 영수증을 올리면 상품·
번들을 먼저 보고, 공식 라이브러리로 스토어에 확인하고, `(store, store_key)`
기준으로 행을 만들거나 갱신한 뒤 권한을 돌려준다. 앱은 이 응답을 받은 뒤에야
`completePurchase` 를 한다 — 그래서 중간에 실패하면 앱이 다음 시작에 같은
영수증을 다시 올리고, 그 재전송이 행을 늘리지 않는 게 이 모듈의 핵심이다.
"""

import logging
from dataclasses import dataclass

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.clients import app_store, play
from app.errors import ReceiptInvalidError
from app.extensions import db
from app.models import (
    Guest,
    Subscription,
    SubscriptionEnvironment,
    SubscriptionStatus,
    SubscriptionStore,
)
from app.repositories.subscription_repository import find_by_guest, find_by_store_key
from app.schemas.subscription import EntitlementResponse
from app.services.entitlement import build_entitlement
from app.services.subscription_status import (
    NormalizedSubscription,
    apple_subscription_status,
    google_subscription_status,
)
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def verify_receipt(guest: Guest, store: SubscriptionStore, receipt: str) -> EntitlementResponse:
    """영수증을 검증해 구독 행을 만들거나 갱신하고, 현재 권한을 돌려준다."""
    if store is SubscriptionStore.APPLE:
        verified = _verify_apple(receipt)
    else:
        verified = _verify_google(receipt)

    if verified is not None:
        _save(guest, store, verified)

    # 방금 올린 영수증이 권한을 주지 못해도(유예 종료·보류) 게스트가 다른
    # 스토어에 살아 있는 구독을 들고 있을 수 있으니 전체를 보고 판정한다.
    return build_entitlement(find_by_guest(guest.id), utcnow())


@dataclass(frozen=True)
class _VerifiedSubscription:
    """스토어 확인이 끝난 구독 하나 — 저장에 필요한 값만 모아 둔 것."""

    store_key: str
    product_id: str
    environment: SubscriptionEnvironment
    normalized: NormalizedSubscription
    # Google 구매 교체에서만 채워진다(옛 purchaseToken).
    replaces_store_key: str | None = None


def _verify_apple(receipt: str) -> _VerifiedSubscription | None:
    subscription = app_store.fetch_subscription(receipt)

    # 번들 ID 는 영수증(JWS)에 서명돼 들어오므로 여기서 대조한다. 다른 앱의
    # 영수증을 우리 구독으로 쓰는 걸 막는 지점이다(Google 은 패키지명이 요청
    # 경로에 들어가서 조회 자체가 실패한다 — app/clients/play.py).
    _reject_unless(
        subscription.bundle_id == current_app.config["APP_STORE_BUNDLE_ID"],
        f"다른 앱의 영수증이다: bundle_id={subscription.bundle_id!r}",
    )
    _reject_unless_our_product(subscription.product_id)

    return _VerifiedSubscription(
        store_key=subscription.store_key,
        product_id=subscription.product_id,
        environment=subscription.environment,
        normalized=apple_subscription_status(
            subscription.raw_status, subscription.transaction, subscription.renewal_info
        ),
    )


def _verify_google(receipt: str) -> _VerifiedSubscription | None:
    purchase = play.fetch_subscription(receipt)
    normalized = google_subscription_status(purchase)
    if normalized.status is None:
        # 결제 대기 구매. 행을 만들지 않고 권한도 주지 않는다(미정 항목 14).
        # 결제가 끝나면 앱이 구매 스트림에서 다시 받아 올린다.
        logger.info("결제가 끝나지 않은 Play 구매라 행을 만들지 않음")
        return None

    _reject_unless_our_product(_google_product_id(purchase))

    return _VerifiedSubscription(
        store_key=receipt,
        product_id=_google_product_id(purchase),
        # Google 은 환경 필드 대신 테스트 구매에만 `testPurchase` 를 붙여 준다.
        environment=(
            SubscriptionEnvironment.SANDBOX
            if "testPurchase" in purchase
            else SubscriptionEnvironment.PRODUCTION
        ),
        normalized=normalized,
        # 업그레이드·재가입이면 옛 purchaseToken 이 같이 온다. 그 행은 이
        # 구독이 이어받았다는 뜻으로 replaced 로 닫는다(스펙 §A.8).
        replaces_store_key=purchase.get("linkedPurchaseToken"),
    )


def _google_product_id(purchase: dict) -> str:
    line_items = purchase.get("lineItems") or [{}]
    return line_items[0].get("productId") or ""


def _reject_unless_our_product(product_id: str) -> None:
    _reject_unless(
        product_id == current_app.config["SUBSCRIPTION_PRODUCT_ID"],
        f"우리 구독 상품이 아니다: product_id={product_id!r}",
    )


def _reject_unless(condition: bool, reason: str) -> None:
    if not condition:
        # 사용자에게는 이유를 알려주지 않는다(남의 영수증을 떠보는 데 쓰일 수
        # 있다). 운영자는 로그에서 본다.
        logger.warning("영수증 거절: %s", reason)
        raise ReceiptInvalidError()


def _save(guest: Guest, store: SubscriptionStore, verified: _VerifiedSubscription) -> None:
    if verified.replaces_store_key:
        _mark_replaced(store, verified.replaces_store_key, verified.store_key)

    existing = find_by_store_key(store, verified.store_key)
    if existing is None:
        db.session.add(_new_row(guest, store, verified))
    else:
        _update(existing, guest, verified)

    try:
        db.session.commit()
    except IntegrityError:
        # 앱이 같은 영수증을 동시에 두 번 올리면 둘 다 "없다" 를 보고 둘 다
        # INSERT 를 시도한다. unique(store, store_key) 가 한쪽을 막아주니,
        # 막힌 쪽은 이긴 행을 다시 읽어 갱신으로 돌린다.
        db.session.rollback()
        winner = find_by_store_key(store, verified.store_key)
        if winner is None:
            raise
        _update(winner, guest, verified)
        db.session.commit()


def _new_row(
    guest: Guest, store: SubscriptionStore, verified: _VerifiedSubscription
) -> Subscription:
    return Subscription(
        guest_id=guest.id,
        store=store,
        store_key=verified.store_key,
        product_id=verified.product_id,
        environment=verified.environment,
        status=verified.normalized.status,
        expires_at=verified.normalized.expires_at,
        grace_expires_at=verified.normalized.grace_expires_at,
        last_verified_at=utcnow(),
    )


def _update(
    subscription: Subscription, guest: Guest, verified: _VerifiedSubscription
) -> None:
    # 복원·기기 전환이면 같은 구독이 다른 게스트로 넘어온다 — 행을 새로 만들지
    # 않고 주인만 바꾼다(US 19·28).
    subscription.guest_id = guest.id
    subscription.product_id = verified.product_id
    subscription.environment = verified.environment
    subscription.status = verified.normalized.status
    subscription.expires_at = verified.normalized.expires_at
    subscription.grace_expires_at = verified.normalized.grace_expires_at
    subscription.last_verified_at = utcnow()


def _mark_replaced(store: SubscriptionStore, old_store_key: str, new_store_key: str) -> None:
    """교체된 옛 구독을 닫는다. 지우지 않는 이유: 어느 구독이 어느 구독으로
    이어졌는지가 환불·문의 때 필요한 기록이다."""
    old = find_by_store_key(store, old_store_key)
    if old is None or old.store_key == new_store_key:
        return

    old.status = SubscriptionStatus.REPLACED
    old.last_verified_at = utcnow()
