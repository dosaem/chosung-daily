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
    # 애플 refresh token. 계정 삭제 때 애플 쪽 연결을 실제로 철회하려면 id_token 이
    # 아니라 이 토큰이 필요하다(ADR 0002). DB 유출 하나로 애플 연결까지 넘어가지
    # 않게 Fernet 으로 암호화해서 넣는다(app/utils/crypto.py) — 그래서 길이가
    # 평문보다 늘어나 String 대신 Text 다. 구글 로그인은 비어 있다.
    provider_refresh_token: str | None = db.Column(db.Text, nullable=True)
    # 그 refresh token 을 발급한 client — 웹 로그인은 Services ID, 앱 로그인은 앱
    # 번들 ID. 애플 revoke 는 발급 client 의 자격증명으로만 받아주기 때문에 어느
    # 쪽으로 연결됐는지를 같이 들고 있어야 한다.
    provider_client_id: str | None = db.Column(db.String(191), nullable=True)
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)

    guest = db.relationship("Guest")
