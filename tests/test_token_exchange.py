"""앱 로그인: POST /auth/token-exchange (ADR 0002).

가짜로 두는 건 네트워크 경계 둘 — provider JWKS 조회와 애플 토큰 교환 — 뿐이고,
id_token 자체는 테스트 키 쌍으로 진짜 서명해서 서버가 진짜로 검증하게 한다.
"""

import jwt
import pytest
import requests

from app.models import Account, OAuthProvider
from app.services import app_login_service
from app.services.account_service import link_or_switch_account
from app.services.guest_service import get_guest_by_token, issue_guest
from app.services.id_token_service import APPLE_ISSUER
from app.utils.crypto import decrypt_secret
from tests.id_token_helpers import generate_rsa_key, jwks_for, sign_id_token

GOOGLE_ISSUER = "https://accounts.google.com"
PATH = "/api/v1/auth/token-exchange"


@pytest.fixture(scope="module")
def key():
    return generate_rsa_key()


@pytest.fixture(autouse=True)
def jwks(app, key, monkeypatch):
    """provider 공개키 조회만 가짜로 대체한다(프로세스 캐시는 테스트마다 비운다)."""
    keys = jwks_for(key)
    calls = []

    def fake_fetch():
        calls.append(1)
        return keys

    app_login_service._JWKS_CACHE.clear()
    monkeypatch.setattr(app_login_service, "fetch_google_jwks", fake_fetch)
    monkeypatch.setattr(app_login_service, "fetch_apple_jwks", fake_fetch)
    return calls


class _RecordingExchange:
    """애플 토큰 교환 래퍼 대역. 호출 인자를 기록한다."""

    def __init__(self, response=None, raises=None):
        self.calls = []
        self._response = response or {}
        self._raises = raises

    def __call__(self, code, *, client_id, client_secret):
        self.calls.append({"code": code, "client_id": client_id, "client_secret": client_secret})
        if self._raises is not None:
            raise self._raises
        return self._response


def _google_token(key, app, *, audience=None, subject="google-uid-1", email="p@example.com"):
    return sign_id_token(
        key,
        issuer=GOOGLE_ISSUER,
        audience=audience or app.config["GOOGLE_IOS_CLIENT_ID"],
        sub=subject,
        email=email,
    )


def _apple_token(key, app, *, subject="apple-uid-1", email=None):
    return sign_id_token(
        key,
        issuer=APPLE_ISSUER,
        audience=app.config["APPLE_APP_BUNDLE_ID"],
        sub=subject,
        email=email,
    )


def _apple_exchange(key, app, *, subject="apple-uid-1", refresh_token="apple-refresh-1"):
    return _RecordingExchange(
        {"refresh_token": refresh_token, "id_token": _apple_token(key, app, subject=subject)}
    )


def test_google_ios_token_links_current_guest(client, app, key, guest_headers):
    res = client.post(
        PATH,
        headers=guest_headers,
        json={"provider": "google", "id_token": _google_token(key, app)},
    )

    assert res.status_code == 200
    account = Account.query.one()
    assert account.provider == OAuthProvider.GOOGLE
    assert account.provider_user_id == "google-uid-1"
    assert account.email == "p@example.com"
    assert res.get_json()["token"] == account.guest.token


def test_google_android_token_uses_web_client_id(client, app, key, guest_headers):
    token = _google_token(key, app, audience=app.config["GOOGLE_WEB_CLIENT_ID"])

    res = client.post(PATH, headers=guest_headers, json={"provider": "google", "id_token": token})

    assert res.status_code == 200
    assert Account.query.count() == 1


def test_audience_outside_matrix_is_unauthorized(client, app, key, guest_headers):
    token = _google_token(key, app, audience="android-client-id")

    res = client.post(PATH, headers=guest_headers, json={"provider": "google", "id_token": token})

    assert res.status_code == 401
    assert res.get_json()["code"] == "INVALID_ID_TOKEN"
    assert Account.query.count() == 0


def test_already_linked_provider_account_switches_guest(client, app, key, guest_headers):
    original = issue_guest()
    link_or_switch_account(original, OAuthProvider.GOOGLE, "google-uid-1", "p@example.com")

    res = client.post(
        PATH,
        headers=guest_headers,
        json={"provider": "google", "id_token": _google_token(key, app)},
    )

    assert res.status_code == 200
    assert res.get_json()["token"] == original.token
    assert Account.query.count() == 1


def test_guest_with_another_account_is_rejected(client, app, key, guest_headers):
    guest = get_guest_by_token(guest_headers["Authorization"].removeprefix("Bearer "))
    link_or_switch_account(guest, OAuthProvider.APPLE, "apple-uid-9", None)

    res = client.post(
        PATH,
        headers=guest_headers,
        json={"provider": "google", "id_token": _google_token(key, app)},
    )

    assert res.status_code == 409
    assert res.get_json()["code"] == "ACCOUNT_ALREADY_LINKED"


def test_requires_bearer_token(client, app, key):
    res = client.post(PATH, json={"provider": "google", "id_token": _google_token(key, app)})

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_unknown_provider_is_validation_error(client, app, key, guest_headers):
    res = client.post(
        PATH,
        headers=guest_headers,
        json={"provider": "naver", "id_token": _google_token(key, app)},
    )

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"


def test_jwks_is_fetched_once_for_two_logins(client, app, key, guest_headers, jwks):
    for subject in ("google-uid-1", "google-uid-2"):
        headers = {"Authorization": f"Bearer {issue_guest().token}"}
        client.post(
            PATH,
            headers=headers,
            json={"provider": "google", "id_token": _google_token(key, app, subject=subject)},
        )

    assert len(jwks) == 1


def test_google_ignores_authorization_code(client, app, key, guest_headers, monkeypatch):
    exchange = _apple_exchange(key, app)
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", exchange)

    res = client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "google",
            "id_token": _google_token(key, app),
            "authorization_code": "code-1",
        },
    )

    assert res.status_code == 200
    assert exchange.calls == []
    account = Account.query.one()
    assert account.provider_refresh_token is None
    assert account.provider_client_id is None


def test_apple_stores_encrypted_refresh_token_and_bundle_id(
    client, app, key, guest_headers, monkeypatch
):
    exchange = _apple_exchange(key, app)
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", exchange)

    res = client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "apple-code-1",
        },
    )

    assert res.status_code == 200
    account = Account.query.one()
    assert account.provider_client_id == app.config["APPLE_APP_BUNDLE_ID"]
    # 평문이 그대로 들어가면 DB 유출 한 번으로 애플 연결까지 넘어간다.
    assert account.provider_refresh_token != "apple-refresh-1"
    assert decrypt_secret(account.provider_refresh_token) == "apple-refresh-1"


def test_apple_exchange_uses_bundle_id_credentials(client, app, key, guest_headers, monkeypatch):
    exchange = _apple_exchange(key, app)
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", exchange)

    client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "apple-code-1",
        },
    )

    call = exchange.calls[0]
    assert call["code"] == "apple-code-1"
    assert call["client_id"] == app.config["APPLE_APP_BUNDLE_ID"]
    # client_secret 은 번들 ID 로 서명한 JWT 여야 한다(웹 Services ID 가 아니라).
    secret_claims = jwt.decode(call["client_secret"], options={"verify_signature": False})
    assert secret_claims["sub"] == app.config["APPLE_APP_BUNDLE_ID"]


def test_apple_requires_authorization_code(client, app, key, guest_headers):
    res = client.post(
        PATH, headers=guest_headers, json={"provider": "apple", "id_token": _apple_token(key, app)}
    )

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert Account.query.count() == 0


def test_apple_subject_mismatch_is_unauthorized(client, app, key, guest_headers, monkeypatch):
    exchange = _apple_exchange(key, app, subject="someone-else")
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", exchange)

    res = client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "apple-code-1",
        },
    )

    assert res.status_code == 401
    assert res.get_json()["code"] == "INVALID_ID_TOKEN"
    assert Account.query.count() == 0


def test_apple_rejected_code_is_unauthorized(client, app, key, guest_headers, monkeypatch):
    exchange = _RecordingExchange(raises=requests.HTTPError("400 invalid_grant"))
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", exchange)

    res = client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "used-code",
        },
    )

    assert res.status_code == 401
    assert res.get_json()["code"] == "INVALID_ID_TOKEN"
    assert Account.query.count() == 0


def test_apple_relogin_overwrites_stored_tokens(client, app, key, guest_headers, monkeypatch):
    first = _apple_exchange(key, app, refresh_token="apple-refresh-1")
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", first)
    client.post(
        PATH,
        headers=guest_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "apple-code-1",
        },
    )

    # 다른 기기에서 같은 애플 계정으로 다시 로그인 → 전환 경로에서도 덮어쓴다.
    second = _apple_exchange(key, app, refresh_token="apple-refresh-2")
    monkeypatch.setattr(app_login_service, "exchange_authorization_code", second)
    other_headers = {"Authorization": f"Bearer {issue_guest().token}"}
    res = client.post(
        PATH,
        headers=other_headers,
        json={
            "provider": "apple",
            "id_token": _apple_token(key, app),
            "authorization_code": "apple-code-2",
        },
    )

    assert res.status_code == 200
    account = Account.query.one()
    assert decrypt_secret(account.provider_refresh_token) == "apple-refresh-2"
    assert account.provider_client_id == app.config["APPLE_APP_BUNDLE_ID"]
