"""OAuth 로그인은 실제 구글/애플 콘솔에 앱을 등록하기 전까진 끝까지
테스트할 수 없다(authorize_access_token이 실제 provider와 통신함). 여기선
그 전 단계 — 라우팅/가드 로직과 세션 동기화(로그인 CSRF 방어)만 검증한다.
실제 로그인 왕복은 콘솔 등록 후 수동으로 확인해야 한다.
"""


from flask import redirect

from app.api import oauth as oauth_api
from app.models import Account
from app.utils.crypto import decrypt_secret


def test_login_rejects_unsupported_provider(client):
    res = client.get("/api/v1/auth/naver/login")

    assert res.status_code == 404
    assert res.get_json()["code"] == "NOT_FOUND"


def test_login_without_synced_session_is_unauthorized(client, guest_headers):
    # session/sync를 안 부르고 바로 로그인 시도 — 세션 쿠키가 없으니 막혀야 한다.
    res = client.get("/api/v1/auth/google/login")

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_login_csrf_cannot_be_forged_via_query_param(client, guest_headers):
    """예전엔 /login?token=<아무 게스트 토큰>으로 어느 게스트에 연결할지 정할 수
    있었다 — 공격자가 자기 토큰을 넣은 링크를 피해자에게 보내서 피해자가 로그인을
    완료하면 피해자 계정이 공격자 게스트에 묶이는 로그인 CSRF가 가능했다(보안
    리뷰로 발견, 수정함). 지금은 그 쿼리파라미터를 아예 안 읽으니, 넣어도 무시돼야
    (= 세션 동기화 없이는 여전히 401) 한다.
    """
    res = client.get(f"/api/v1/auth/google/login?token={guest_headers['Authorization']}")

    assert res.status_code == 401


def test_sync_then_login_redirects_to_provider(client, guest_headers):
    sync_res = client.post("/api/v1/session/sync", headers=guest_headers)
    assert sync_res.status_code == 200

    res = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert res.status_code == 302
    assert "accounts.google.com" in res.headers["Location"]


def test_sync_then_apple_login_redirects_to_provider(client, guest_headers):
    """애플은 client_secret이 ES256 JWT라(app/extensions.py의 apple_client_secret)
    등록 단계에서부터 서명이 깨지면 여기서 바로 드러난다 — 리다이렉트까지 가는지로
    그 서명 로직 자체가 안 깨졌는지 확인한다. 실제 애플 서버가 이 JWT를 받아주는지는
    콘솔 등록 후에만 확인 가능.
    """
    client.post("/api/v1/session/sync", headers=guest_headers)

    res = client.get("/api/v1/auth/apple/login", follow_redirects=False)

    assert res.status_code == 302
    assert "appleid.apple.com" in res.headers["Location"]


def test_sync_requires_auth(client):
    res = client.post("/api/v1/session/sync")

    assert res.status_code == 401


def test_callback_without_pending_session_is_unauthorized(client):
    res = client.get("/api/v1/auth/google/callback")

    assert res.status_code == 401


def test_apple_callback_accepts_post(client):
    # 애플은 콜백을 GET이 아니라 POST(response_mode=form_post)로 보낸다 —
    # 라우트가 POST를 아예 안 받으면 405가 떠야 하는데, 그게 아니라 (세션이
    # 없어서) 401이 떠야 라우트 자체는 POST를 받고 있다는 뜻이다.
    res = client.post("/api/v1/auth/apple/callback")

    assert res.status_code == 401


class _FakeOAuthClient:
    """Authlib 클라이언트 대역 — 로그인 시작/콜백에서 쓰는 메서드만 흉내 낸다."""

    def __init__(self, token, user_info):
        self._token = token
        self._user_info = user_info

    def authorize_redirect(self, redirect_uri, **kwargs):
        return redirect("https://provider.test/authorize")

    def authorize_access_token(self):
        return self._token

    def parse_id_token(self, token, nonce=None):
        return self._user_info


def test_apple_callback_stores_refresh_token_and_services_id(
    app, client, guest_headers, monkeypatch
):
    """웹 애플 로그인도 앱과 같은 컬럼에 refresh token 을 보관한다(§A.6).

    계정 삭제 때 애플 revoke 를 호출하려면 refresh token 이 필요하고, 그 호출엔
    "어느 client 로 발급했는지"(웹=Services ID / 앱=번들 ID)도 같이 있어야 한다.
    """
    monkeypatch.setattr(
        oauth_api,
        "_get_client",
        lambda provider: _FakeOAuthClient(
            {"refresh_token": "web-apple-refresh", "id_token": "unused"},
            {"sub": "apple-web-uid", "email": "web@example.com"},
        ),
    )
    client.post("/api/v1/session/sync", headers=guest_headers)
    client.get("/api/v1/auth/apple/login", follow_redirects=False)

    res = client.post("/api/v1/auth/apple/callback", follow_redirects=False)

    assert res.status_code == 302
    account = Account.query.one()
    assert account.provider_client_id == app.config["APPLE_CLIENT_ID"]
    assert decrypt_secret(account.provider_refresh_token) == "web-apple-refresh"


def test_google_callback_stores_no_provider_token(app, client, guest_headers, monkeypatch):
    monkeypatch.setattr(
        oauth_api,
        "_get_client",
        lambda provider: _FakeOAuthClient(
            {"access_token": "google-access"},
            {"sub": "google-web-uid", "email": "web@example.com"},
        ),
    )
    client.post("/api/v1/session/sync", headers=guest_headers)
    client.get("/api/v1/auth/google/login", follow_redirects=False)

    res = client.get("/api/v1/auth/google/callback", follow_redirects=False)

    assert res.status_code == 302
    account = Account.query.one()
    assert account.provider_refresh_token is None
    assert account.provider_client_id is None
