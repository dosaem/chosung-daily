import requests

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
TIMEOUT_SECONDS = 3


def fetch_apple_jwks() -> list[dict]:
    """애플 id_token 서명 검증용 공개키(JWKS)를 받아온다."""
    response = requests.get(APPLE_JWKS_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()["keys"]


def exchange_authorization_code(code: str, *, client_id: str, client_secret: str) -> dict:
    """애플 authorization_code 를 토큰(refresh_token·id_token)으로 교환한다.

    client_id 는 로그인한 쪽의 발급 client 다 — 웹은 Services ID, 앱은 번들 ID.
    client_secret 은 그 client_id 로 서명한 JWT(`app/extensions.py` 의
    `apple_client_secret`). 애플 토큰 엔드포인트는 자격증명을 HTTP Basic 이 아니라
    POST 바디로만 받는다(`init_oauth` 주석의 실측).

    애플이 코드를 거절하면(이미 쓴 코드 등) `requests.HTTPError` 가 올라간다 —
    호출자가 로그인 실패로 번역한다.
    """
    response = requests.post(
        APPLE_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()
