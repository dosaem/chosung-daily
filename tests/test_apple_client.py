"""애플 외부 호출 래퍼(토큰 교환)와 client_secret 생성. 네트워크는 가짜 requests.post."""

import json

import jwt
import pytest
import requests

from app.clients import apple
from app.extensions import apple_client_secret

BUNDLE_ID = "com.dosaem.chosung"


class _RecordingPost:
    """requests.post 대역. 호출 인자를 기록하고 정해둔 응답/예외를 돌려준다."""

    def __init__(self, payload=None, status_code=200, raises=None):
        self.calls = []
        self._payload = payload or {}
        self._status_code = status_code
        self._raises = raises

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = self._status_code
        response.url = url
        response._content = json.dumps(self._payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response


def test_exchange_posts_code_to_apple_token_endpoint(app, monkeypatch):
    post = _RecordingPost({"refresh_token": "apple-refresh", "id_token": "signed"})
    monkeypatch.setattr(apple.requests, "post", post)

    result = apple.exchange_authorization_code(
        "auth-code-1", client_id=BUNDLE_ID, client_secret="secret-jwt"
    )

    assert result["refresh_token"] == "apple-refresh"
    url, kwargs = post.calls[0]
    assert url == apple.APPLE_TOKEN_URL
    # 애플은 자격증명을 POST 바디로만 받는다(app/extensions.py 주석 참고).
    assert kwargs["data"] == {
        "grant_type": "authorization_code",
        "code": "auth-code-1",
        "client_id": BUNDLE_ID,
        "client_secret": "secret-jwt",
    }
    assert kwargs["timeout"] == apple.TIMEOUT_SECONDS


def test_exchange_raises_on_rejected_code(app, monkeypatch):
    post = _RecordingPost({"error": "invalid_grant"}, status_code=400)
    monkeypatch.setattr(apple.requests, "post", post)

    with pytest.raises(requests.HTTPError):
        apple.exchange_authorization_code(
            "used-code", client_id=BUNDLE_ID, client_secret="secret-jwt"
        )


def test_jwks_fetch_returns_keys_array(app, monkeypatch):
    def fake_get(url, **kwargs):
        assert url == apple.APPLE_JWKS_URL
        assert kwargs["timeout"] == apple.TIMEOUT_SECONDS
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"keys": [{"kid": "a"}]}).encode()
        return response

    monkeypatch.setattr(apple.requests, "get", fake_get)

    assert apple.fetch_apple_jwks() == [{"kid": "a"}]


def test_client_secret_can_be_signed_for_bundle_id(app):
    """웹은 Services ID, 앱은 번들 ID 로 같은 키로 서명한다 — sub 만 달라진다."""
    web_secret = apple_client_secret(app, app.config["APPLE_CLIENT_ID"])
    app_secret = apple_client_secret(app, BUNDLE_ID)

    web_claims = jwt.decode(web_secret, options={"verify_signature": False})
    app_claims = jwt.decode(app_secret, options={"verify_signature": False})

    assert web_claims["sub"] == app.config["APPLE_CLIENT_ID"]
    assert app_claims["sub"] == BUNDLE_ID
    assert app_claims["iss"] == app.config["APPLE_TEAM_ID"]
    assert app_claims["aud"] == "https://appleid.apple.com"
    assert jwt.get_unverified_header(app_secret)["kid"] == app.config["APPLE_KEY_ID"]
