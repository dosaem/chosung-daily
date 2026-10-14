"""저장된 구독을 스토어에 다시 물어본다 — 두 경로(스펙 §A.8 재조회).

1. `/me/stats` 가 부를 때: 그 게스트의 구독 중 TTL 이 지난 것만(1시간, 만료
   ±24h 는 5분). 앱이 포그라운드에서 `next_check_at` 에 맞춰 다시 부르므로
   철회 반영 지연이 최대 1시간이 된다.
2. Celery Beat 매일 1회: 만료 3일 이내의 살아 있는 구독 전부. `/me/stats` 를
   아예 안 부르는 사용자(앱을 안 켠 구독자)를 위한 경로다.

웹훅(App Store Server Notifications / Play RTDN)을 안 쓰는 대가가 이 폴링이고,
그 판단 근거는 ADR 0003 과 README "13." 에 적어 뒀다.

"언제 다시 물어볼 때가 됐나" 와 "권한이 있나" 는 순수 함수
(`app/services/entitlement.py`)가 판정한다. 이 모듈은 그 판정에 따라 스토어를
부르고 결과를 행에 적는 쪽이다.
"""

import logging
from datetime import timedelta

from app.clients import app_store, play
from app.errors import ReceiptInvalidError, StoreUnavailableError
from app.extensions import db
from app.models import Guest, Subscription, SubscriptionStore
from app.repositories.subscription_repository import (
    find_by_guest,
    find_expiring,
    find_with_repeated_failures,
)
from app.schemas.subscription import EntitlementResponse
from app.services.entitlement import (
    RECHECKABLE_STATUSES,
    build_entitlement,
    is_recheck_due,
)
from app.services.operator_alert_service import notify_operator
from app.services.subscription_status import (
    NormalizedSubscription,
    apple_subscription_status,
    google_subscription_status,
)
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# Beat 가 보는 구간. 스토어가 만료·갱신을 처리하는 시점 주변만 보면 되고,
# 만료가 한 달 뒤인 구독을 매일 물어볼 이유는 없다(스펙 §A.8 (c)).
BEAT_RECHECK_WINDOW = timedelta(days=3)

# 연속 실패가 이만큼 쌓인 구독이 있으면 운영자에게 알린다(스펙 §A.12). 한 번·두
# 번은 스토어 일시 장애로 흔하고, 세 번이면 설정이 틀어졌을 가능성이 높다.
FAILURE_ALERT_THRESHOLD = 3


def entitlement_for(guest: Guest) -> EntitlementResponse:
    """`GET /me/stats` 가 쓰는 권한. 필요하면 스토어를 먼저 다시 물어본다.

    이 게스트의 구독만 본다 — 전체를 훑으면 한 사람의 호출이 구독 수만큼
    스토어 API 를 때린다.
    """
    subscriptions = find_by_guest(guest.id)
    now = utcnow()
    for subscription in subscriptions:
        if is_recheck_due(subscription, now):
            recheck(subscription)
    return build_entitlement(subscriptions, now)


def recheck(subscription: Subscription) -> bool:
    """구독 하나를 스토어에 다시 물어보고 그 행에 적는다. 성공 여부를 돌려준다.

    행마다 커밋한다(이 레포의 "함수 하나 = 커밋 하나" 를 구독 하나 단위로 적용).
    Beat 가 수십 건을 돌 때 중간에 스토어가 죽어도 그 앞의 결과는 남아야 하고,
    한 구독의 재조회는 다른 구독과 같이 되돌릴 이유가 없는 독립된 사실이다.

    실패하면 저장값을 그대로 두고 `recheck_failures` 만 올린다 —
    `last_verified_at` 을 올리지 않으므로 다음 호출이 바로 다시 시도한다.
    스토어 장애로 돈 낸 구독자의 광고를 켜지 않는 쪽을 택한 것이다.
    """
    try:
        normalized = _ask_store(subscription)
    except (StoreUnavailableError, ReceiptInvalidError, ValueError) as exc:
        # ReceiptInvalidError: Apple 이 "어느 환경에도 없는 거래" 라고 답한 경우.
        # 권한을 뺏는 판단은 스토어가 분명히 말해준 상태로만 한다.
        # ValueError: 스토어가 우리가 모르는 상태 코드를 새로 쓰기 시작한 경우
        # (`subscription_status`). `/me/stats` 가 그걸로 500 이 되면 안 된다.
        logger.warning(
            "구독 %s 재조회 실패 (%s) — 저장값 유지", subscription.id, type(exc).__name__
        )
        subscription.recheck_failures += 1
        db.session.commit()
        return False

    if normalized.status is None:
        # Google 이 "결제가 아직 안 끝난 구매" 라고 답한 경우. 이미 행이 있는
        # 구독에는 나올 일이 없는 답이라 상태를 덮지 않고 실패로 센다.
        logger.warning("구독 %s 재조회가 결제 대기로 돌아옴 — 저장값 유지", subscription.id)
        subscription.recheck_failures += 1
        db.session.commit()
        return False

    subscription.status = normalized.status
    subscription.expires_at = normalized.expires_at
    subscription.grace_expires_at = normalized.grace_expires_at
    subscription.last_verified_at = utcnow()
    subscription.recheck_failures = 0
    db.session.commit()
    return True


def recheck_expiring_subscriptions() -> int:
    """Celery Beat 매일 1회. 만료 3일 이내의 살아 있는 구독을 전부 재조회한다.

    재조회한 구독 수를 돌려준다 — 태스크 로그와 테스트가 스토어 호출을
    들여다보지 않고 확인할 수 있게(`word_pool_service.notify_low_word_pool` 과
    같은 규칙).

    TTL 은 보지 않는다. 이 경로의 목적이 "앱을 안 켜는 구독자의 구독도 하루
    한 번은 확인한다" 라서, 방금 조회한 행이어도 한 번 더 도는 비용을 받는다.
    """
    subscriptions = find_expiring(
        sorted(RECHECKABLE_STATUSES), utcnow() + BEAT_RECHECK_WINDOW
    )
    for subscription in subscriptions:
        recheck(subscription)

    _alert_on_repeated_failures()
    return len(subscriptions)


def _ask_store(subscription: Subscription) -> NormalizedSubscription:
    """저장된 스토어 식별자로 현재 상태를 읽어 우리 상태로 옮긴다.

    상품·번들 대조는 하지 않는다 — 그건 구매 경로(`subscription_service`)가
    영수증을 받을 때 하는 일이고, 여기서 보는 건 이미 우리가 받아들인 구독이다.
    """
    if subscription.store is SubscriptionStore.APPLE:
        apple = app_store.fetch_subscription_status(
            subscription.store_key, subscription.environment
        )
        return apple_subscription_status(
            apple.raw_status, apple.transaction, apple.renewal_info
        )
    return google_subscription_status(play.fetch_subscription(subscription.store_key))


def _alert_on_repeated_failures() -> bool:
    """연속 실패가 쌓인 구독을 한 건의 알림으로 묶어 운영자에게 보낸다.

    구독마다 보내지 않는 이유: 스토어 설정이 틀어지면 모든 구독이 같이 실패해서
    Slack 이 같은 메시지로 덮인다. 운영자가 알아야 할 건 "몇 건이 며칠째
    실패인가" 다.

    `store_key` 는 넣지 않는다 — 결제 식별자를 Slack 채널에 복제하는 셈이다
    (`apple_secret_service` 가 secret 을 안 싣는 것과 같은 이유). 운영자는 행
    ID 로 DB 에서 찾는다.
    """
    failing = find_with_repeated_failures(FAILURE_ALERT_THRESHOLD)
    if not failing:
        return False

    notify_operator(
        "구독 재조회 실패 누적",
        "\n".join(
            f"구독 {subscription.id}({subscription.store.value}): "
            f"연속 {subscription.recheck_failures}회 실패, "
            f"마지막 확인 {subscription.last_verified_at.isoformat()}"
            for subscription in failing
        ),
    )
    return True
