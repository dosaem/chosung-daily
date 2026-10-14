"""운영자 설정 페이지(`/admin/settings`) — 점검 모드·최소 앱 버전 토글.

핵심은 "저장 직후 `GET /api/v1/config` 에 반영되는가" 다 — /config 는 60초 캐시라
저장이 캐시를 지우지 않으면 앱은 최대 1분 동안 옛 설정을 본다.
"""

import re

from app.models import AppSetting
from app.services.app_config_service import (
    MAINTENANCE_ENABLED_KEY,
    MAINTENANCE_MESSAGE_KEY,
    MIN_APP_VERSION_ANDROID_KEY,
    MIN_APP_VERSION_IOS_KEY,
)

CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')

MAINTENANCE_MESSAGE = "00:00~01:00 서버 점검 중입니다"


def _token(client, path="/admin/settings"):
    html = client.get(path).get_data(as_text=True)
    match = CSRF_PATTERN.search(html)
    assert match, f"{path} 에 csrf_token hidden 이 없다"
    return match.group(1)


def _form(client, **overrides):
    data = {
        "csrf_token": _token(client),
        "min_app_version_ios": "1.0.0",
        "min_app_version_android": "1.0.0",
    }
    data.update(overrides)
    return data


def _settings_rows():
    return {row.key: row.value for row in AppSetting.query.all()}


def test_the_settings_page_shows_the_current_values(admin_session):
    html = admin_session.get("/admin/settings").get_data(as_text=True)

    assert "점검 모드" in html
    assert "최소 앱 버전" in html
    assert 'value="1.0.0"' in html


def test_the_settings_page_needs_an_admin_session(client):
    assert client.get("/admin/settings").status_code == 302


def test_turning_maintenance_on_shows_up_in_config_right_away(admin_session):
    admin_session.get("/api/v1/config")  # 캐시를 채운다 (TTL 60초)

    res = admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session,
            maintenance_enabled="on",
            maintenance_message=MAINTENANCE_MESSAGE,
        ),
    )

    assert res.status_code == 302
    body = admin_session.get("/api/v1/config").get_json()
    assert body["maintenance"] == {"enabled": True, "message": MAINTENANCE_MESSAGE}


def test_raising_the_minimum_app_version_shows_up_in_config_right_away(admin_session):
    admin_session.get("/api/v1/config")

    admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session, min_app_version_ios="1.4.0", min_app_version_android="1.3.2"
        ),
    )

    body = admin_session.get("/api/v1/config").get_json()
    assert body["min_app_version"] == {"ios": "1.4.0", "android": "1.3.2"}


def test_turning_maintenance_off_again_is_stored(admin_session):
    admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session,
            maintenance_enabled="on",
            maintenance_message=MAINTENANCE_MESSAGE,
        ),
    )

    admin_session.post(
        "/admin/settings",
        data=_form(admin_session, maintenance_message=MAINTENANCE_MESSAGE),
    )

    assert _settings_rows()[MAINTENANCE_ENABLED_KEY] == "false"
    # 메시지는 지우지 않는다 — 다음에 켤 때 같은 문구를 다시 적지 않게.
    assert _settings_rows()[MAINTENANCE_MESSAGE_KEY] == MAINTENANCE_MESSAGE
    assert admin_session.get("/api/v1/config").get_json()["maintenance"]["enabled"] is False


def test_the_saved_values_come_back_in_the_form(admin_session):
    admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session,
            maintenance_enabled="on",
            maintenance_message=MAINTENANCE_MESSAGE,
            min_app_version_ios="1.4.0",
        ),
    )

    html = admin_session.get("/admin/settings").get_data(as_text=True)

    assert MAINTENANCE_MESSAGE in html
    assert 'value="1.4.0"' in html
    assert "checked" in html


def test_a_broken_version_is_refused_and_nothing_is_saved(admin_session):
    res = admin_session.post(
        "/admin/settings", data=_form(admin_session, min_app_version_ios="v1.4")
    )

    assert res.status_code == 200
    assert "버전" in res.get_data(as_text=True)
    assert AppSetting.query.count() == 0


def test_maintenance_without_a_message_is_refused(admin_session):
    res = admin_session.post(
        "/admin/settings",
        data=_form(admin_session, maintenance_enabled="on", maintenance_message=" "),
    )

    assert res.status_code == 200
    assert "메시지" in res.get_data(as_text=True)
    assert AppSetting.query.count() == 0


def test_a_refused_save_keeps_what_the_operator_typed(admin_session):
    """고치던 값을 그대로 다시 그린다 — 폼이 비면 운영자가 처음부터 다시 적는다."""
    res = admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session,
            maintenance_enabled="on",
            maintenance_message=MAINTENANCE_MESSAGE,
            min_app_version_android="1.3",
        ),
    )

    html = res.get_data(as_text=True)
    assert MAINTENANCE_MESSAGE in html
    assert 'value="1.3"' in html


def test_saving_without_a_csrf_token_is_forbidden(admin_session):
    res = admin_session.post(
        "/admin/settings",
        data={
            "maintenance_enabled": "on",
            "maintenance_message": MAINTENANCE_MESSAGE,
            "min_app_version_ios": "1.4.0",
            "min_app_version_android": "1.4.0",
        },
    )

    assert res.status_code == 403
    assert AppSetting.query.count() == 0


def test_the_four_keys_are_the_ones_config_reads(admin_session):
    admin_session.post(
        "/admin/settings",
        data=_form(
            admin_session,
            maintenance_enabled="on",
            maintenance_message=MAINTENANCE_MESSAGE,
            min_app_version_ios="1.4.0",
            min_app_version_android="1.3.2",
        ),
    )

    assert set(_settings_rows()) == {
        MAINTENANCE_ENABLED_KEY,
        MAINTENANCE_MESSAGE_KEY,
        MIN_APP_VERSION_IOS_KEY,
        MIN_APP_VERSION_ANDROID_KEY,
    }
