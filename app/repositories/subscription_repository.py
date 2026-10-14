from app.extensions import db
from app.models import Subscription, SubscriptionStore


def find_by_store_key(store: SubscriptionStore, store_key: str) -> Subscription | None:
    """멱등의 열쇠. 같은 영수증이 몇 번 오든 이 조회가 같은 행을 가리킨다."""
    return db.session.query(Subscription).filter_by(store=store, store_key=store_key).first()


def find_by_guest(guest_id: int) -> list[Subscription]:
    return db.session.query(Subscription).filter_by(guest_id=guest_id).all()
