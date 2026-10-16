"""애플 client_secret(JWT) 의 요청 경로 갱신·만료 관측·만료 임박 알림 (스펙 §A.13).

외부 호출은 없다 — 서명·만료 판정이 전부 프로세스 안에서 일어나서, 시간만
"만료 N일 남은 secret 을 캐시에 심는" 식으로 조작하면 실제 동작을 그대로 볼 수
있다. `_AppleClientSecret` 를 직접 심는 것도 그래서다(시계를 monkeypatch 하는
것보다 "지금 프로세스가 들고 있는 상태"를 그대로 표현한다).
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.extensions import (
    APPLE_SECRET_LIFETIME,
    APPLE_SECRET_RENEW_WITHIN,
    _apple_secrets,
    _AppleClientSecret,
    apple_client_ids,
    apple_client_secret,
    apple_client_secret_expiries,
    apple_secret_expires_at,
    get_oauth,
)
from app.services import apple_secret_service
from app.services.apple_secret_service import notify_apple_secret_expiry

STALE_JWT = "stale-but-not-yet-expired-jwt"


def _seed(app, client_id: str, *, days_left: float) -> _AppleClientSecret:
    """`client_id` 의 캐시된 secret 을 "만료 days_left 일 남은" 상태로 바꾼다."""
    seeded = _AppleClientSecret(STALE_JWT, datetime.now(UTC) + timedelta(days=days_left))
    _apple_secrets(app)[client_id] = seeded
    return seeded


def _exp(token: str) -> datetime:
    claims = jwt.decode(token, options={"verify_signature": False})
    return datetime.fromtimestamp(claims["exp"], UTC)


@pytest.fixture
def apple_oauth_client(app):
    """등록된 Authlib 애플 클라이언트. 교체를 눈으로 보려고 stale 값으로 맞춰둔다."""
    client = get_oauth().create_client("apple")
    client.client_secret = STALE_JWT
    return client


@pytest.fixture
def synced_client(client, guest_headers):
    """세션 동기화까지 끝낸 테스트 클라이언트 — /auth/apple/login 이 401 로 안 막힌다."""
    client.post("/api/v1/session/sync", headers=guest_headers)
    return client


# --- 접근자: 7일 미만 남으면 재서명 -------------------------------------------------


def test_accessor_keeps_a_secret_that_is_not_near_expiry(app):
    seeded = _seed(app, app.config["APPLE_CLIENT_ID"], days_left=30)

    assert apple_client_secret(app, app.config["APPLE_CLIENT_ID"]) == STALE_JWT
    assert _apple_secrets(app)[app.config["APPLE_CLIENT_ID"]] == seeded


def test_accessor_resigns_when_less_than_seven_days_remain(app):
    client_id = app.config["APPLE_CLIENT_ID"]
    _seed(app, client_id, days_left=6)

    renewed = apple_client_secret(app, client_id)

    assert renewed != STALE_JWT
    assert jwt.decode(renewed, options={"verify_signature": False})["sub"] == client_id
    # 새로 서명한 secret 은 다시 150일치다.
    remaining = _exp(renewed) - datetime.now(UTC)
    assert timedelta(days=149) < remaining <= APPLE_SECRET_LIFETIME
    # 교체는 캐시에도 반영돼야 한다 — 다음 요청이 또 서명하면 갱신이 아니라 매번 서명이다.
    assert _apple_secrets(app)[client_id].jwt == renewed


def test_accessor_resigns_for_the_bundle_id_by_the_same_rule(app):
    """앱(iOS) 로그인용 번들 ID secret 도 같은 접근자·같은 7일 규칙을 쓴다."""
    bundle_id = app.config["APPLE_APP_BUNDLE_ID"]
    _seed(app, bundle_id, days_left=6)

    renewed = apple_client_secret(app, bundle_id)

    assert renewed != STALE_JWT
    assert jwt.decode(renewed, options={"verify_signature": False})["sub"] == bundle_id
    assert _apple_secrets(app)[bundle_id].jwt == renewed


def test_accessor_signs_a_secret_that_was_never_cached(app):
    _apple_secrets(app).clear()

    signed = apple_client_secret(app, app.config["APPLE_CLIENT_ID"])

    assert _apple_secrets(app)[app.config["APPLE_CLIENT_ID"]].jwt == signed


def test_renew_window_is_seven_days():
    """스펙 §A.13 이 정한 창. Beat 만료 알림도 같은 7일을 쓴다."""
    assert APPLE_SECRET_RENEW_WITHIN.days == 7
    assert APPLE_SECRET_LIFETIME.days == 150


# --- 요청 경로: login·callback 진입 -----------------------------------------------


def test_apple_login_swaps_the_authlib_client_secret(
    synced_client, app, apple_oauth_client, offline_provider_metadata
):
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=6)

    res = synced_client.get("/api/v1/auth/apple/login", follow_redirects=False)

    assert res.status_code == 302
    assert apple_oauth_client.client_secret != STALE_JWT
    assert _exp(apple_oauth_client.client_secret) - datetime.now(UTC) > timedelta(days=149)


def test_apple_callback_swaps_the_authlib_client_secret(client, app, apple_oauth_client):
    """콜백은 `authorize_access_token()` 에서 애플에 실제 요청을 보내기 때문에 끝까지
    돌릴 수 없다. 대신 진입 지점(`_get_client`)이 세션 검사보다 **먼저** 교체한다는
    사실을 쓴다 — 보류 세션이 없어 401 로 끝나는 호출에서도 교체는 일어나야 한다.
    교체가 토큰 교환 직전이 아니라 진입에서 일어나는 게 §A.13 이 요구하는 것이다.
    """
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=6)

    res = client.post("/api/v1/auth/apple/callback")

    assert res.status_code == 401
    assert apple_oauth_client.client_secret != STALE_JWT
    assert _exp(apple_oauth_client.client_secret) - datetime.now(UTC) > timedelta(days=149)


def test_apple_login_leaves_a_healthy_secret_alone(
    synced_client, app, apple_oauth_client, offline_provider_metadata
):
    """갱신은 만료가 임박했을 때만이다 — 로그인마다 새 JWT 를 서명하지 않는다."""
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=30)

    synced_client.get("/api/v1/auth/apple/login", follow_redirects=False)

    assert apple_oauth_client.client_secret == STALE_JWT


def test_google_login_does_not_touch_its_client_secret(
    synced_client, app, offline_provider_metadata
):
    """구글 client_secret 은 고정값이라 갱신 대상이 아니다."""
    google_client = get_oauth().create_client("google")

    synced_client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert google_client.client_secret == app.config["GOOGLE_CLIENT_SECRET"]


# --- 관측: /health 와 Beat 가 보는 만료 시각 ----------------------------------------


def test_expiry_is_the_earlier_of_the_two_clients(app):
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=120)
    bundle_expiry = _seed(app, app.config["APPLE_APP_BUNDLE_ID"], days_left=40)

    assert apple_secret_expires_at(app) == bundle_expiry.expires_at


def test_expiry_does_not_renew_a_near_expiry_secret(app):
    """관측이 갱신까지 하면 "만료 임박" 이 보이는 순간 사라져서 Beat 알림이 영원히
    안 울린다. 그래서 `apple_secret_expires_at` 은 접근자와 달리 재서명하지 않는다."""
    seeded = _seed(app, app.config["APPLE_CLIENT_ID"], days_left=3)
    _seed(app, app.config["APPLE_APP_BUNDLE_ID"], days_left=100)

    assert apple_secret_expires_at(app) == seeded.expires_at
    assert _apple_secrets(app)[app.config["APPLE_CLIENT_ID"]].jwt == STALE_JWT


def test_expiry_signs_clients_that_were_never_used(app):
    """첫 앱 로그인 전에도 번들 ID 쪽 만료 시각이 /health 에 나와야 한다."""
    _apple_secrets(app).clear()

    expiries = apple_client_secret_expiries(app)

    both = {app.config["APPLE_CLIENT_ID"], app.config["APPLE_APP_BUNDLE_ID"]}
    assert set(expiries) == both
    assert set(apple_client_ids(app)) == both
    assert apple_secret_expires_at(app) == min(expiries.values())


def test_expiry_is_none_without_apple_signing_keys(app):
    app.config["APPLE_PRIVATE_KEY"] = ""
    _apple_secrets(app).clear()

    assert apple_client_ids(app) == ()
    assert apple_client_secret_expiries(app) == {}
    assert apple_secret_expires_at(app) is None


def test_health_reports_the_earlier_expiry(client, app):
    bundle_expiry = _seed(app, app.config["APPLE_APP_BUNDLE_ID"], days_left=9)
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=100)

    body = client.get("/health").get_json()

    assert body["apple_secret_expires_at"] == bundle_expiry.expires_at.isoformat()


def test_health_reports_null_without_apple_signing_keys(client, app):
    app.config["APPLE_PRIVATE_KEY"] = ""
    _apple_secrets(app).clear()

    assert client.get("/health").get_json()["apple_secret_expires_at"] is None


# --- Beat 주 1회: 만료 임박 알림 ----------------------------------------------------


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(
        apple_secret_service,
        "notify_operator",
        lambda kind, message, **_kw: sent.append((kind, message)),
    )
    return sent


def test_notifies_the_operator_when_expiry_is_within_seven_days(app, alerts):
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=6)
    _seed(app, app.config["APPLE_APP_BUNDLE_ID"], days_left=100)

    assert notify_apple_secret_expiry() is True

    assert len(alerts) == 1
    kind, message = alerts[0]
    assert kind == "애플 client_secret 만료 임박"
    # 운영자가 Slack 만 보고 "언제까지" 를 알 수 있어야 한다.
    assert app.config["APPLE_CLIENT_ID"] in message
    assert "6일" in message


def test_does_not_notify_while_both_secrets_are_healthy(app, alerts):
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=100)
    _seed(app, app.config["APPLE_APP_BUNDLE_ID"], days_left=100)

    assert notify_apple_secret_expiry() is False
    assert alerts == []


def test_does_not_notify_without_apple_signing_keys(app, alerts):
    app.config["APPLE_PRIVATE_KEY"] = ""
    _apple_secrets(app).clear()

    assert notify_apple_secret_expiry() is False
    assert alerts == []


def test_alert_does_not_leak_the_secret_itself(app, alerts):
    _seed(app, app.config["APPLE_CLIENT_ID"], days_left=1)

    notify_apple_secret_expiry()

    assert STALE_JWT not in alerts[0][1]
