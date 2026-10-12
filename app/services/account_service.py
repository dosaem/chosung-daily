from app.errors import AccountAlreadyLinkedError
from app.extensions import db
from app.models import Account, Guest, OAuthProvider
from app.repositories.account_repository import find_by_guest, find_by_identity


def link_or_switch_account(
    current_guest: Guest,
    provider: OAuthProvider,
    provider_user_id: str,
    email: str | None,
) -> Guest:
    """OAuth 콜백에서 호출. 함수 하나 = 커밋 하나(이 레포 트랜잭션 규칙).

    이 provider+provider_user_id로 이미 연결된 계정이 있으면, 그 계정의 게스트로
    "전환"한다 — 다른 기기에서 처음 로그인해도 항상 같은 기록으로 돌아가는 방식.
    없으면 지금 쓰고 있는 게스트(current_guest)에 새로 연결한다.
    """
    existing = find_by_identity(provider, provider_user_id)
    if existing is not None:
        return existing.guest

    already_linked = find_by_guest(current_guest.id)
    if already_linked is not None:
        raise AccountAlreadyLinkedError()

    db.session.add(
        Account(
            guest_id=current_guest.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
        )
    )
    db.session.commit()
    return current_guest
