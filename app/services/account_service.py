from typing import NamedTuple

from app.errors import AccountAlreadyLinkedError
from app.extensions import db
from app.models import Account, Guest, OAuthProvider
from app.repositories.account_repository import find_by_guest, find_by_identity
from app.utils.crypto import encrypt_secret


class ProviderTokens(NamedTuple):
    """애플이 돌려준 refresh token 과 그걸 발급한 client.

    둘은 항상 같이 움직인다 — 애플 revoke 는 "이 토큰" 을 "그 토큰을 발급한
    client 의 자격증명" 으로 호출해야 받아주기 때문에, 하나만 저장되면 쓸 수 없다.
    client_id 는 웹 로그인이면 Services ID, 앱 로그인이면 앱 번들 ID 다.
    """

    refresh_token: str
    client_id: str


def link_or_switch_account(
    current_guest: Guest,
    provider: OAuthProvider,
    provider_user_id: str,
    email: str | None,
    provider_tokens: ProviderTokens | None = None,
) -> Guest:
    """OAuth 콜백(웹)과 id_token 교환(앱)에서 호출. 함수 하나 = 커밋 하나.

    이 provider+provider_user_id로 이미 연결된 계정이 있으면, 그 계정의 게스트로
    "전환"한다 — 다른 기기에서 처음 로그인해도 항상 같은 기록으로 돌아가는 방식.
    없으면 지금 쓰고 있는 게스트(current_guest)에 새로 연결한다.

    `provider_tokens` 는 애플 로그인에서만 들어온다(§A.6) — 새로 연결하든 전환하든
    매번 최신 값으로 덮어쓴다. 애플이 refresh token 을 로그인마다 새로 주고, 오래된
    토큰으로는 revoke 가 실패할 수 있어서다.
    """
    existing = find_by_identity(provider, provider_user_id)
    if existing is not None:
        _store_provider_tokens(existing, provider_tokens)
        db.session.commit()
        return existing.guest

    already_linked = find_by_guest(current_guest.id)
    if already_linked is not None:
        raise AccountAlreadyLinkedError()

    account = Account(
        guest_id=current_guest.id,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
    )
    _store_provider_tokens(account, provider_tokens)
    db.session.add(account)
    db.session.commit()
    return current_guest


def _store_provider_tokens(account: Account, tokens: ProviderTokens | None) -> None:
    """애플 refresh token 을 암호화해 발급 client 와 함께 보관한다.

    구글 로그인은 보관할 게 없어서 None 으로 들어온다 — 그때는 컬럼을 건드리지
    않는다(한 게스트에 provider 는 하나뿐이라 실제로 섞일 일은 없지만, "없음" 이
    기존 값을 지우는 동작이 되면 나중에 쉽게 사고가 난다).
    """
    if tokens is None:
        return
    account.provider_refresh_token = encrypt_secret(tokens.refresh_token)
    account.provider_client_id = tokens.client_id
