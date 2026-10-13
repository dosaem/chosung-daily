"""id_token 검증 순수 함수. 네트워크 없이 입력(토큰 + JWKS) → 출력(클레임)."""

import base64
import hashlib
import hmac
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization

from app.errors import InvalidIdTokenError
from app.services.id_token_service import APPLE_ISSUER, GOOGLE_ISSUERS, verify_id_token
from tests.id_token_helpers import TEST_KID, generate_rsa_key, jwks_for, sign_id_token

IOS_CLIENT_ID = "ios-client-id.apps.googleusercontent.com"
WEB_CLIENT_ID = "web-client-id.apps.googleusercontent.com"


@pytest.fixture(scope="module")
def key():
    return generate_rsa_key()


@pytest.fixture(scope="module")
def jwks(key):
    return jwks_for(key)


def test_valid_google_token_returns_claims(key, jwks):
    token = sign_id_token(key, issuer="https://accounts.google.com", audience=IOS_CLIENT_ID)

    claims = verify_id_token(
        token, jwks, issuers=GOOGLE_ISSUERS, audiences=(IOS_CLIENT_ID, WEB_CLIENT_ID)
    )

    assert claims["sub"] == "provider-uid-1"
    assert claims["email"] == "player@example.com"


def test_google_accepts_issuer_without_scheme(key, jwks):
    # 구글은 iss 를 "accounts.google.com" 으로 주는 토큰도 발급한다(둘 다 유효).
    token = sign_id_token(key, issuer="accounts.google.com", audience=WEB_CLIENT_ID)

    claims = verify_id_token(
        token, jwks, issuers=GOOGLE_ISSUERS, audiences=(IOS_CLIENT_ID, WEB_CLIENT_ID)
    )

    assert claims["aud"] == WEB_CLIENT_ID


def test_audience_outside_matrix_is_rejected(key, jwks):
    # Android 클라이언트 ID 로 발급된 토큰(= 앱 설정이 잘못된 경우)은 받지 않는다.
    token = sign_id_token(
        key, issuer="https://accounts.google.com", audience="android-client-id"
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(
            token, jwks, issuers=GOOGLE_ISSUERS, audiences=(IOS_CLIENT_ID, WEB_CLIENT_ID)
        )


def test_wrong_issuer_is_rejected(key, jwks):
    token = sign_id_token(key, issuer=APPLE_ISSUER, audience=IOS_CLIENT_ID)

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=GOOGLE_ISSUERS, audiences=(IOS_CLIENT_ID,))


def test_expired_token_is_rejected(key, jwks):
    token = sign_id_token(
        key, issuer=APPLE_ISSUER, audience="com.dosaem.chosung", exp=int(time.time()) - 60
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=("com.dosaem.chosung",))


def test_signature_from_another_key_is_rejected(jwks):
    # kid 는 맞지만 다른 개인키로 서명한 토큰 — 서명을 실제로 검증하는지 확인한다.
    attacker_key = generate_rsa_key()
    token = sign_id_token(
        attacker_key, issuer=APPLE_ISSUER, audience="com.dosaem.chosung"
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=("com.dosaem.chosung",))


def test_unknown_kid_is_rejected(key, jwks):
    token = sign_id_token(
        key, issuer=APPLE_ISSUER, audience="com.dosaem.chosung", kid="rotated-kid"
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=("com.dosaem.chosung",))


def test_symmetric_algorithm_is_rejected(key, jwks):
    """공개키를 HMAC 비밀로 써서 서명한 토큰(알고리즘 혼동 공격)은 거부해야 한다.

    jwt.decode 에 algorithms=["RS256"] 를 넘기지 않으면, 서버가 "토큰 헤더가
    말하는 알고리즘" 을 믿고 JWKS 의 공개키(= 누구나 읽는 값)를 HMAC 비밀로 써서
    검증해버리는 고전적인 구멍이 생긴다. PyJWT 는 encode 쪽에서 이런 키를 막기
    때문에, 공격자가 실제로 하는 것처럼 토큰을 직접 만들어서 넣는다.
    """
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    token = _hmac_signed_token(
        {"alg": "HS256", "kid": TEST_KID},
        {"iss": APPLE_ISSUER, "aud": "com.dosaem.chosung", "sub": "x", "exp": 9999999999},
        secret=public_pem,
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=("com.dosaem.chosung",))


def test_unsigned_token_is_rejected(key, jwks):
    """alg=none(서명 없음) 토큰도 같은 이유로 거부해야 한다."""
    header = _b64(json.dumps({"alg": "none", "kid": TEST_KID}).encode())
    claims = _b64(
        json.dumps(
            {"iss": APPLE_ISSUER, "aud": "com.dosaem.chosung", "sub": "x", "exp": 9999999999}
        ).encode()
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(
            f"{header}.{claims}.",
            jwks,
            issuers=(APPLE_ISSUER,),
            audiences=("com.dosaem.chosung",),
        )


def test_token_without_subject_is_rejected(key, jwks):
    token = jwt.encode(
        {"iss": APPLE_ISSUER, "aud": "com.dosaem.chosung", "exp": 9999999999},
        key,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=("com.dosaem.chosung",))


def test_garbage_token_is_rejected(jwks):
    with pytest.raises(InvalidIdTokenError):
        verify_id_token("not-a-jwt", jwks, issuers=(APPLE_ISSUER,), audiences=("x",))


def test_empty_audience_matrix_is_rejected(key, jwks):
    """설정값(클라이언트 ID)이 비어 있으면 "aud 검증 없이 통과" 가 아니라 거부다."""
    token = sign_id_token(key, issuer=APPLE_ISSUER, audience="com.dosaem.chosung")

    with pytest.raises(InvalidIdTokenError):
        verify_id_token(token, jwks, issuers=(APPLE_ISSUER,), audiences=())


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _hmac_signed_token(header: dict, claims: dict, *, secret: bytes) -> str:
    signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(claims).encode())}"
    signature = hmac.new(secret, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"
