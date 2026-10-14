from datetime import datetime

from app.extensions import db
from app.models import Subscription, SubscriptionStatus, SubscriptionStore


def find_by_store_key(store: SubscriptionStore, store_key: str) -> Subscription | None:
    """멱등의 열쇠. 같은 영수증이 몇 번 오든 이 조회가 같은 행을 가리킨다."""
    return db.session.query(Subscription).filter_by(store=store, store_key=store_key).first()


def find_by_guest(guest_id: int) -> list[Subscription]:
    return db.session.query(Subscription).filter_by(guest_id=guest_id).all()


def find_expiring(
    statuses: list[SubscriptionStatus], before: datetime
) -> list[Subscription]:
    """만료가 `before` 이전인(또는 모르는) 구독 중 주어진 상태인 것들. Beat 몫.

    만료 시각을 모르는 행(`expires_at IS NULL`)도 넣는다 — 그 행은 "언제까지"
    를 증명할 수 없어서 권한 판정이 이미 없음으로 떨어지고, 다시 물어봐야
    고쳐진다.

    유예 중인 행은 `grace_expires_at` 이 더 늦지만 `expires_at`(원래 만료일)이
    이미 지나 있어서 이 조건에 자연히 걸린다.
    """
    return (
        db.session.query(Subscription)
        .filter(
            Subscription.status.in_(statuses),
            db.or_(Subscription.expires_at.is_(None), Subscription.expires_at <= before),
        )
        .all()
    )


def lock_and_refresh(subscription: Subscription) -> Subscription:
    """구독 행을 SELECT ... FOR UPDATE 로 다시 읽어 최신 커밋 값으로 채운다.

    스토어 조회처럼 **잠금을 들고 있을 수 없는 구간**(최대 3초 외부 호출) 뒤에
    쓰기 직전에 부른다: 잠금을 받은 뒤 읽으므로 그 사이에 다른 요청·Beat 가
    커밋한 값이 보이고(InnoDB 의 잠금 읽기는 REPEATABLE READ 스냅샷이 아니라
    최신 커밋을 본다), 그 값과 비교해서 오래된 응답을 버릴 수 있다. 잠금은
    호출한 쪽이 커밋할 때 풀린다(`guest_stats_repository.lock_for_guest` 와 같은
    규칙).
    """
    db.session.refresh(subscription, with_for_update=True)
    return subscription


def find_with_repeated_failures(at_least: int) -> list[Subscription]:
    return (
        db.session.query(Subscription)
        .filter(Subscription.recheck_failures >= at_least)
        .all()
    )
