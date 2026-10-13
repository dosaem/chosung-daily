import requests

# 구글의 OIDC 공개키 목록. discovery 문서(server_metadata_url)를 한 번 더 받아서
# jwks_uri 를 읽는 대신 고정 URL 을 쓴다 — 이 URL 은 구글 문서가 보장하는 값이고,
# 로그인 한 번에 네트워크 왕복을 둘로 늘릴 이유가 없다.
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
TIMEOUT_SECONDS = 3


def fetch_google_jwks() -> list[dict]:
    """구글 id_token 서명 검증용 공개키(JWKS)를 받아온다.

    외부 호출만 하는 래퍼다(§A.17) — 캐시는 호출자
    (`app/services/app_login_service.py`), 검증은 순수 함수
    (`app/services/id_token_service.py`) 쪽에 있다.
    """
    response = requests.get(GOOGLE_JWKS_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()["keys"]
