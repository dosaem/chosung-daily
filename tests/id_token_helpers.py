"""테스트용 RSA 키 쌍으로 실제 id_token 을 서명한다.

구글·애플의 id_token 검증은 "서명이 맞는가" 가 핵심이라, 클레임만 들어있는
가짜 객체를 돌려주는 식으로 monkeypatch 하면 검증 코드가 실제로 서명을 보는지
알 수 없다. 그래서 네트워크 경계(JWKS 조회·토큰 교환)만 가짜로 두고, 토큰 자체는
여기서 만든 키 쌍으로 진짜 서명해서 진짜로 검증하게 한다.
"""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

TEST_KID = "test-kid"


def generate_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks_for(private_key, kid: str = TEST_KID) -> list[dict]:
    """provider 의 JWKS 응답에서 우리가 쓰는 부분(keys 배열)과 같은 모양."""
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    return [{**public_jwk, "kid": kid, "alg": "RS256", "use": "sig"}]


def sign_id_token(
    private_key,
    *,
    issuer: str,
    audience: str,
    kid: str = TEST_KID,
    **claims,
) -> str:
    """기본 클레임(sub·iat·exp·email)으로 토큰을 서명한다. 개별 클레임은 키워드로 덮어쓴다."""
    now = int(time.time())
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": "provider-uid-1",
        "iat": now,
        "exp": now + 3600,
        "email": "player@example.com",
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": kid})
