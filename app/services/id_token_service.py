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

    try:
        kid = jwt.get_unverified_header(id_token).get("kid")
    except jwt.PyJWTError as exc:
        raise InvalidIdTokenError() from exc

    key = _find_key(jwks, kid)
    if key is None:
        # provider 가 키를 교체했는데 캐시가 옛 키만 들고 있을 수도 있다 —
        # 캐시 TTL(1시간) 이 지나면 다음 로그인에서 새 키를 받는다.
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


def _find_key(jwks: Sequence[dict], kid: str | None):
    for entry in jwks:
        if kid is not None and entry.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))
    return None
