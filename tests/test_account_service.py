import pytest

from app.errors import AccountAlreadyLinkedError
from app.models import Account, OAuthProvider
from app.services.account_service import link_or_switch_account
from app.services.guest_service import issue_guest


def test_first_login_links_current_guest(app):
    guest = issue_guest()

    result = link_or_switch_account(guest, OAuthProvider.GOOGLE, "google-uid-1", "a@example.com")

    assert result.id == guest.id
    account = Account.query.filter_by(guest_id=guest.id).one()
    assert account.provider == OAuthProvider.GOOGLE
    assert account.provider_user_id == "google-uid-1"
    assert account.email == "a@example.com"


def test_second_login_from_different_device_switches_to_original_guest(app):
    original_guest = issue_guest()
    link_or_switch_account(original_guest, OAuthProvider.KAKAO, "kakao-uid-1", None)

    new_device_guest = issue_guest()  # 다른 기기에서 처음 접속해서 새로 발급된 게스트

    result = link_or_switch_account(new_device_guest, OAuthProvider.KAKAO, "kakao-uid-1", None)

    assert result.id == original_guest.id
    assert result.id != new_device_guest.id
    # 새 기기의 게스트엔 계정이 안 생겼어야 한다 — 원래 계정으로 "전환"만 됐다.
    assert Account.query.filter_by(guest_id=new_device_guest.id).first() is None


def test_linking_second_provider_to_already_linked_guest_is_rejected(app):
    guest = issue_guest()
    link_or_switch_account(guest, OAuthProvider.GOOGLE, "google-uid-2", None)

    with pytest.raises(AccountAlreadyLinkedError):
        link_or_switch_account(guest, OAuthProvider.KAKAO, "kakao-uid-2", None)
