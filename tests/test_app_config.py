from app.extensions import db, get_redis
from app.models import AppSetting
from app.services.app_config_service import (
    CACHE_KEY,
    CACHE_TTL_SECONDS,
    MAINTENANCE_ENABLED_KEY,
    MAINTENANCE_MESSAGE_KEY,
    MIN_APP_VERSION_ANDROID_KEY,
    MIN_APP_VERSION_IOS_KEY,
)

PLAY_URL = "https://play.google.com/store/apps/details?id=com.dosaem.chosung"
APP_STORE_URL = "https://apps.apple.com/app/id1234567890"


def _set_setting(key: str, value: str) -> None:
    db.session.add(AppSetting(key=key, value=value))
    db.session.commit()


def test_config_needs_no_auth_and_returns_defaults(client):
    res = client.get("/api/v1/config")

    assert res.status_code == 200
    assert res.get_json() == {
        "min_app_version": {"ios": "1.0.0", "android": "1.0.0"},
        "maintenance": {"enabled": False, "message": None},
        "languages": ["ko", "en"],
        "store_urls": {"ios": None, "android": None},
    }


def test_config_reflects_setting_rows(client):
    _set_setting(MIN_APP_VERSION_IOS_KEY, "1.4.0")
    _set_setting(MIN_APP_VERSION_ANDROID_KEY, "1.3.2")
    _set_setting(MAINTENANCE_ENABLED_KEY, "true")
    _set_setting(MAINTENANCE_MESSAGE_KEY, "서버 점검 중입니다 (00:00~01:00)")

    body = client.get("/api/v1/config").get_json()

    assert body["min_app_version"] == {"ios": "1.4.0", "android": "1.3.2"}
    assert body["maintenance"] == {
        "enabled": True,
        "message": "서버 점검 중입니다 (00:00~01:00)",
    }


def test_maintenance_is_off_unless_the_row_says_true(client):
    _set_setting(MAINTENANCE_ENABLED_KEY, "false")

    assert client.get("/api/v1/config").get_json()["maintenance"]["enabled"] is False


def test_store_urls_come_from_the_environment(client, app):
    app.config["STORE_URL_IOS"] = APP_STORE_URL
    app.config["STORE_URL_ANDROID"] = PLAY_URL

    body = client.get("/api/v1/config").get_json()

    assert body["store_urls"] == {"ios": APP_STORE_URL, "android": PLAY_URL}


def test_config_is_cached_so_a_changed_row_is_not_seen_right_away(client):
    first = client.get("/api/v1/config").get_json()
    _set_setting(MAINTENANCE_ENABLED_KEY, "true")

    assert client.get("/api/v1/config").get_json() == first


def test_config_cache_expires_within_a_minute(client):
    client.get("/api/v1/config")

    ttl = get_redis().ttl(CACHE_KEY)

    assert 0 < ttl <= CACHE_TTL_SECONDS


def test_config_still_answers_when_redis_is_down(client, broken_redis):
    _set_setting(MAINTENANCE_ENABLED_KEY, "true")

    res = client.get("/api/v1/config")

    assert res.status_code == 200
    assert res.get_json()["maintenance"]["enabled"] is True
