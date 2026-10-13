import json
from collections.abc import Sequence

import jwt

from app.errors import InvalidIdTokenError

# 구글은 같은 토큰을 두 형태의 iss 로 발급한다(둘 다 유효하다고 문서에 명시).
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
APPLE_ISSUER = "https://appleid.apple.com"

# 구글·애플 id_token 은 둘 다 RS256 이다. 허용 알고리즘을 고정하지 않으면
# 공개키(JWKS 는 누구나 읽는다)를 HMAC 비밀로 써서 서명한 토큰이 통과한다.
ALLOWED_ALGORITHMS = ("RS256",)


def verify_id_token(
    id_token: str,
    jwks: Sequence[dict],
    *,
    issuers: Sequence[str],
    audiences: Sequence[str],
) -> dict:
    """id_token 의 서명·iss·aud·exp 를 검증하고 클레임을 돌려준다.

    네트워크를 타지 않는 순수 함수다 — 공개키(jwks)와 받아들일 iss·aud 를 인자로
    받는다(§A.17). 그래서 테스트가 테스트 키 쌍으로 서명한 진짜 토큰을 그대로
    검증할 수 있고, 가짜로 둘 건 JWKS 조회뿐이다.

    `audiences` 가 비어 있으면(= 클라이언트 ID 설정이 안 됨) 검증을 건너뛰지 않고
    거부한다. 설정 누락이 "아무 토큰이나 통과" 로 조용히 바뀌면 안 된다.
    """
    if not audiences:
        raise InvalidIdTokenError()

    key = _find_key(jwks, unverified_kid(id_token))
    if key is None:
        # 넘겨받은 공개키에 이 토큰의 kid 가 없다. 키 교체 중이면 호출자
        # (`app_login_service._jwks_for`)가 먼저 JWKS 를 다시 받아 넘긴다.
        raise InvalidIdTokenError()

    try:
        return jwt.decode(
            id_token,
            key,
            algorithms=list(ALLOWED_ALGORITHMS),
            audience=list(audiences),
            issuer=list(issuers),
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidIdTokenError() from exc


def unverified_kid(id_token: str) -> str | None:
    """서명 검증 전에 헤더의 `kid` 만 읽는다 — 어떤 공개키로 검증할지 고르는 용도.

    헤더가 깨져 있으면 `None` 이고, 그러면 맞는 공개키가 없으니 검증이 거부된다.
    헤더의 다른 값(특히 `alg`)은 믿지 않는다.
    """
    try:
        return jwt.get_unverified_header(id_token).get("kid")
    except jwt.PyJWTError:
        return None


def jwks_contains_kid(jwks: Sequence[dict], kid: str | None) -> bool:
    return kid is not None and any(entry.get("kid") == kid for entry in jwks)


def _find_key(jwks: Sequence[dict], kid: str | None):
    for entry in jwks:
        if kid is not None and entry.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))
    return None
