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


def find_with_repeated_failures(at_least: int) -> list[Subscription]:
    return (
        db.session.query(Subscription)
        .filter(Subscription.recheck_failures >= at_least)
        .all()
    )
