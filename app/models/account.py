from datetime import datetime

from app.extensions import db
from app.models.enums import OAuthProvider
from app.utils.time import utcnow


class Account(db.Model):
    """게스트에 연결된 OAuth 계정. 1 게스트 : 1 계정만 허용한다(복잡도를 낮추려고 —
    이미 다른 provider로 연결된 게스트는 또 연결 못 한다, app/services/account_service.py).

    guest_id가 PK가 아니라 별도 id를 쓰는 이유: GuestStats처럼 guest_id를 그대로 PK로
    써도 되지만, 나중에 "한 게스트에 여러 provider 연결 허용"으로 바뀔 가능성을 완전히
    배제하진 않아서 평범한 자동증가 PK로 뒀다. 지금은 unique(guest_id)로 1:1을 강제한다.
    """

    __tablename__ = "account"
    __table_args__ = (
        db.UniqueConstraint(
            "provider", "provider_user_id", name="uq_account_provider_identity"
        ),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    guest_id: int = db.Column(
        db.Integer, db.ForeignKey("guest.id"), nullable=False, unique=True
    )
    provider: OAuthProvider = db.Column(
        db.Enum(OAuthProvider, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    provider_user_id: str = db.Column(db.String(191), nullable=False)
    email: str | None = db.Column(db.String(255), nullable=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)

    guest = db.relationship("Guest")
