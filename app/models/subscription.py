from datetime import datetime

from app.extensions import db
from app.models.enums import (
    SubscriptionEnvironment,
    SubscriptionStatus,
    SubscriptionStore,
)
from app.utils.time import utcnow


def _store_enum(enum_cls):
    return db.Enum(enum_cls, values_callable=lambda cls: [e.value for e in cls])


class Subscription(db.Model):
    """광고 제거 구독 하나. "스토어가 마지막으로 말해준 상태" 를 그대로 적어두는
    자리이고, 광고를 끌지 말지는 이 행을 보고 순수 함수가 판정한다(ADR 0003).

    `unique(store, store_key)` 가 멱등의 전부다. 앱은 같은 영수증을 여러 번
    올린다 — 구매 직후, 재설치 후 복원, 앱 시작마다 하는 구매 동기화(스펙 §A.8).
    그래서 "이 구독이 이미 있나" 를 게스트가 아니라 **스토어가 준 구독 식별자**로
    묻는다: Apple `originalTransactionId`, Google `purchaseToken`. 같은 구독을
    다른 게스트가 복원하면 행을 새로 만들지 않고 `guest_id` 를 옮긴다(US 19·28).

    `guest_id` 에 unique 를 걸지 않는 이유: 한 게스트가 애플에서 사고 안드로이드로
    옮기면 스토어가 다른 두 구독을 들고 있는 상태가 실제로 가능하다. 권한 판정은
    그 중 "권한을 주는 행이 하나라도 있나" 를 본다.
    """

    __tablename__ = "subscription"
    __table_args__ = (
        db.UniqueConstraint("store", "store_key", name="uq_subscription_store_key"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    # 별도 index=True 를 안 붙인다 — MySQL 은 외래 키에 인덱스를 자동으로
    # 만들어 주고, 같은 컬럼에 또 선언하면 중복 인덱스가 생긴다.
    guest_id: int = db.Column(db.Integer, db.ForeignKey("guest.id"), nullable=False)
    store: SubscriptionStore = db.Column(_store_enum(SubscriptionStore), nullable=False)
    # 스토어가 주는 구독 식별자. Apple originalTransactionId(숫자 문자열) /
    # Google purchaseToken(base64 수백 자). 다른 컬럼들이 쓰는 191 로는 Google 이
    # 안 들어가서 512 로 뒀다 — utf8mb4 로도 2048 바이트라 InnoDB 유니크 인덱스
    # 한계(3072) 안이다.
    store_key: str = db.Column(db.String(512), nullable=False)
    product_id: str = db.Column(db.String(191), nullable=False)
    environment: SubscriptionEnvironment = db.Column(
        _store_enum(SubscriptionEnvironment), nullable=False
    )
    status: SubscriptionStatus = db.Column(_store_enum(SubscriptionStatus), nullable=False)
    # 스토어가 말한 만료 시각. grace 중에는 유예 종료 시각이 따로 올 수 있어서
    # (Apple `gracePeriodExpiresDate`) 컬럼을 나눠 뒀다.
    expires_at: datetime | None = db.Column(db.DateTime, nullable=True)
    grace_expires_at: datetime | None = db.Column(db.DateTime, nullable=True)
    # 마지막으로 스토어에 물어본 시각. 재조회 TTL(1시간)의 기준이다 — 티켓 13.
    last_verified_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)

    guest = db.relationship("Guest")
