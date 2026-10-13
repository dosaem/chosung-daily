import time

import requests
from flask import current_app

from app.clients.apple import exchange_authorization_code, fetch_apple_jwks
from app.clients.google_jwks import fetch_google_jwks
from app.errors import InvalidIdTokenError, ValidationError
from app.extensions import apple_client_secret
from app.models import Guest, OAuthProvider
from app.services.account_service import ProviderTokens, link_or_switch_account
from app.services.id_token_service import APPLE_ISSUER, GOOGLE_ISSUERS, verify_id_token

# JWKS 는 provider 가 키를 교체할 때만 바뀌는 공개 정보다. 로그인마다 구글·애플에
# 공개키를 받으러 가지 않도록 프로세스 안에 1시간 캐시한다(ADR 0002).
JWKS_CACHE_TTL_SECONDS = 60 * 60

# redis 클라이언트·Authlib 레지스트리와 달리 앱 설정과 무관한 값이라(어느 Flask 앱이
# 물어도 같은 공개키) app.extensions 가 아니라 모듈 전역에 둬도 오염되지 않는다.
_JWKS_CACHE: dict[OAuthProvider, tuple[float, list[dict]]] = {}


def exchange_id_token(
    current_guest: Guest,
    provider: OAuthProvider,
    id_token: str,
    authorization_code: str | None = None,
) -> Guest:
    """앱이 네이티브 로그인으로 받은 id_token 을 검증해 계정을 연결하거나 전환한다.

    웹(리다이렉트 + 세션 쿠키)과 진입 경로만 다르고, 연결·전환 규칙은 웹과 같은
    `link_or_switch_account` 하나를 쓴다(ADR 0002). 돌려주는 건 연결된 게스트 —
    전환이면 원래 기록의 게스트다.
    """
    claims = _verify(provider, id_token)
    provider_user_id = str(claims["sub"])

    provider_tokens = None
    if provider is OAuthProvider.APPLE:
        provider_tokens = _exchange_apple_code(authorization_code, provider_user_id)

    return link_or_switch_account(
        current_guest,
        provider,
        provider_user_id,
        claims.get("email"),
        provider_tokens=provider_tokens,
    )


def allowed_audiences(provider: OAuthProvider) -> tuple[str, ...]:
    """provider·플랫폼 조합별 aud 매트릭스(ADR 0002, 스펙 §A.6).

    구글은 iOS 가 iOS 클라이언트 ID, Android 가 `serverClientId` 로 넘긴 **웹**
    클라이언트 ID 를 aud 에 넣는다(Android 클라이언트 ID 는 SHA-1 검증용이라 aud
    에 안 나온다). 요청만 보고 플랫폼을 알 방법이 없으니 둘 다 받아들인다 — 둘
    모두 우리 프로젝트의 클라이언트라 받아들이는 범위가 넓어지지 않는다.
    애플은 앱 번들 ID 하나(웹 Services ID 로 발급된 토큰은 이 경로로 못 들어온다).

    설정이 비어 있으면 빈 튜플이고, `verify_id_token` 이 그걸 거부로 처리한다.
    """
    config = current_app.config
    names = (
        ("GOOGLE_IOS_CLIENT_ID", "GOOGLE_WEB_CLIENT_ID")
        if provider is OAuthProvider.GOOGLE
        else ("APPLE_APP_BUNDLE_ID",)
    )
    return tuple(config[name] for name in names if config[name])


def _verify(provider: OAuthProvider, id_token: str) -> dict:
    issuers = GOOGLE_ISSUERS if provider is OAuthProvider.GOOGLE else (APPLE_ISSUER,)
    return verify_id_token(
        id_token,
        _load_jwks(provider),
        issuers=issuers,
        audiences=allowed_audiences(provider),
    )


def _load_jwks(provider: OAuthProvider) -> list[dict]:
    cached = _JWKS_CACHE.get(provider)
    if cached is not None and time.monotonic() < cached[0]:
        return cached[1]

    fetch = fetch_google_jwks if provider is OAuthProvider.GOOGLE else fetch_apple_jwks
    keys = fetch()
    _JWKS_CACHE[provider] = (time.monotonic() + JWKS_CACHE_TTL_SECONDS, keys)
    return keys


def _exchange_apple_code(
    authorization_code: str | None, expected_provider_user_id: str
) -> ProviderTokens:
    """애플 authorization_code 를 교환해 refresh token 과 발급 client 를 돌려준다.

    애플 계정 삭제 때 연결을 실제로 철회하려면 id_token 이 아니라 refresh token 이
    필요해서(ADR 0002), 앱은 로그인마다 code 도 함께 보낸다. 그래서 애플인데 code
    가 없으면 연결을 거절한다 — 연결은 됐는데 철회할 수단이 없는 계정을 만들지
    않는다(스펙 §A' 요청 스키마의 `?` 는 구글이 안 보낸다는 뜻이다).

    교환으로 받은 id_token 도 앱이 보낸 것과 같은 방식으로 검증하고, `sub` 가
    같은지 확인한다 — 다른 사람의 code 를 끼워 넣어 그 사람의 refresh token 을
    내 계정에 붙이는 걸 막는다.
    """
    if not authorization_code:
        raise ValidationError("애플 로그인은 authorization_code 가 필요합니다.")

    client_id = current_app.config["APPLE_APP_BUNDLE_ID"]
    try:
        token = exchange_authorization_code(
            authorization_code,
            client_id=client_id,
            client_secret=apple_client_secret(current_app, client_id),
        )
    except requests.RequestException as exc:
        # 애플이 코드를 거절했거나 토큰 엔드포인트에 못 닿았다. 둘 다 사용자가 할 일은
        # "다시 로그인" 이라, 같은 로그인 실패로 번역한다.
        raise InvalidIdTokenError() from exc

    exchanged = verify_id_token(
        token.get("id_token", ""),
        _load_jwks(OAuthProvider.APPLE),
        issuers=(APPLE_ISSUER,),
        audiences=(client_id,),
    )
    if str(exchanged["sub"]) != expected_provider_user_id:
        raise InvalidIdTokenError()

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise InvalidIdTokenError()

    return ProviderTokens(refresh_token, client_id)
