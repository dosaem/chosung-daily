import pytest

from app.errors import ValidationError
from app.extensions import db, get_redis
from app.models import AppSetting
from app.services.app_config_service import (
    CACHE_KEY,
    CACHE_TTL_SECONDS,
    DEFAULT_MIN_APP_VERSION,
    MAINTENANCE_ENABLED_KEY,
    MAINTENANCE_MESSAGE_KEY,
    MAINTENANCE_MESSAGE_MAX_LENGTH,
    MIN_APP_VERSION_ANDROID_KEY,
    MIN_APP_VERSION_IOS_KEY,
    get_operator_settings,
    save_operator_settings,
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


# --- 운영자 토글 (티켓 23) ------------------------------------------------


def test_operator_settings_start_from_the_defaults(app):
    settings = get_operator_settings()

    assert settings.maintenance_enabled is False
    assert settings.maintenance_message == ""
    assert settings.min_app_version_ios == DEFAULT_MIN_APP_VERSION
    assert settings.min_app_version_android == DEFAULT_MIN_APP_VERSION


def test_saving_operator_settings_writes_the_rows(app):
    save_operator_settings(
        maintenance_enabled=True,
        maintenance_message="00:00~01:00 점검 중입니다",
        min_app_version_ios="1.4.0",
        min_app_version_android="1.3.2",
    )

    rows = {row.key: row.value for row in AppSetting.query.all()}
    assert rows[MAINTENANCE_ENABLED_KEY] == "true"
    assert rows[MAINTENANCE_MESSAGE_KEY] == "00:00~01:00 점검 중입니다"
    assert rows[MIN_APP_VERSION_IOS_KEY] == "1.4.0"
    assert rows[MIN_APP_VERSION_ANDROID_KEY] == "1.3.2"


def test_saving_twice_updates_the_same_rows(app):
    save_operator_settings(
        maintenance_enabled=True,
        maintenance_message="점검 중",
        min_app_version_ios="1.4.0",
        min_app_version_android="1.4.0",
    )
    save_operator_settings(
        maintenance_enabled=False,
        maintenance_message="점검 중",
        min_app_version_ios="1.5.0",
        min_app_version_android="1.5.0",
    )

    assert AppSetting.query.count() == 4
    assert get_operator_settings().maintenance_enabled is False
    assert get_operator_settings().min_app_version_ios == "1.5.0"


def test_saving_drops_the_config_cache_so_apps_see_it_now(client):
    client.get("/api/v1/config")  # 캐시를 채운다 (TTL 60초)

    save_operator_settings(
        maintenance_enabled=True,
        maintenance_message="점검 중입니다",
        min_app_version_ios="2.0.0",
        min_app_version_android="2.0.0",
    )

    body = client.get("/api/v1/config").get_json()
    assert body["maintenance"] == {"enabled": True, "message": "점검 중입니다"}
    assert body["min_app_version"] == {"ios": "2.0.0", "android": "2.0.0"}


def test_a_version_that_is_not_three_numbers_is_rejected(app):
    with pytest.raises(ValidationError, match="버전"):
        save_operator_settings(
            maintenance_enabled=False,
            maintenance_message="",
            min_app_version_ios="v1.4",
            min_app_version_android="1.4.0",
        )

    assert AppSetting.query.count() == 0


def test_maintenance_cannot_be_turned_on_without_a_message(app):
    with pytest.raises(ValidationError, match="메시지"):
        save_operator_settings(
            maintenance_enabled=True,
            maintenance_message="   ",
            min_app_version_ios="1.0.0",
            min_app_version_android="1.0.0",
        )

    assert AppSetting.query.count() == 0


def test_a_message_longer_than_the_column_is_rejected(app):
    with pytest.raises(ValidationError, match="메시지"):
        save_operator_settings(
            maintenance_enabled=True,
            maintenance_message="점" * (MAINTENANCE_MESSAGE_MAX_LENGTH + 1),
            min_app_version_ios="1.0.0",
            min_app_version_android="1.0.0",
        )

    assert AppSetting.query.count() == 0


def test_an_empty_maintenance_message_is_sent_as_null(client):
    save_operator_settings(
        maintenance_enabled=False,
        maintenance_message="",
        min_app_version_ios="1.0.0",
        min_app_version_android="1.0.0",
    )

    assert client.get("/api/v1/config").get_json()["maintenance"] == {
        "enabled": False,
        "message": None,
    }
