from app.extensions import db
from app.models import Account, OAuthProvider


def find_by_identity(provider: OAuthProvider, provider_user_id: str) -> Account | None:
    return (
        db.session.query(Account)
        .filter_by(provider=provider, provider_user_id=provider_user_id)
        .first()
    )


def find_by_guest(guest_id: int) -> Account | None:
    return db.session.query(Account).filter_by(guest_id=guest_id).first()
