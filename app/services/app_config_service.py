from flask import current_app

from app.models import PuzzleLanguage
from app.repositories.app_setting_repository import find_all_settings
from app.schemas.config import AppConfigResponse, Maintenance, MinAppVersion, StoreUrls
from app.utils.redis_safe import safe_redis_call

# app_setting 테이블에서 운영자가 바꾸는 키들(토글 UI 는 티켓 16). 행이 없으면
# 아래 기본값으로 응답한다 — 설정 테이블이 비어 있어도 앱은 떠야 한다.
MIN_APP_VERSION_IOS_KEY = "min_app_version_ios"
MIN_APP_VERSION_ANDROID_KEY = "min_app_version_android"
MAINTENANCE_ENABLED_KEY = "maintenance_enabled"
MAINTENANCE_MESSAGE_KEY = "maintenance_message"

# 첫 스토어 릴리스 버전. "이 버전 미만이면 강제 업데이트" 규칙에서 기본값이
# 첫 릴리스면 아무도 막히지 않는다.
DEFAULT_MIN_APP_VERSION = "1.0.0"

CACHE_KEY = "app_config"
# 앱이 시작할 때마다 부르는 엔드포인트라 DB 를 매번 때릴 이유가 없고, 반대로
# 점검 모드를 켠 뒤 1분 넘게 안 퍼지면 운영자가 답답하다 — 스펙대로 60초.
CACHE_TTL_SECONDS = 60


def get_app_config() -> AppConfigResponse:
    cached = safe_redis_call("get", CACHE_KEY)
    if cached is not None:
        return AppConfigResponse.model_validate_json(cached)

    config = _load_app_config()
    safe_redis_call("set", CACHE_KEY, config.model_dump_json(), ex=CACHE_TTL_SECONDS)
    return config


def _load_app_config() -> AppConfigResponse:
    settings = find_all_settings()

    return AppConfigResponse(
        min_app_version=MinAppVersion(
            ios=settings.get(MIN_APP_VERSION_IOS_KEY, DEFAULT_MIN_APP_VERSION),
            android=settings.get(MIN_APP_VERSION_ANDROID_KEY, DEFAULT_MIN_APP_VERSION),
        ),
        maintenance=Maintenance(
            enabled=_to_bool(settings.get(MAINTENANCE_ENABLED_KEY)),
            message=settings.get(MAINTENANCE_MESSAGE_KEY),
        ),
        languages=[language.value for language in PuzzleLanguage],
        store_urls=StoreUrls(
            ios=current_app.config["STORE_URL_IOS"] or None,
            android=current_app.config["STORE_URL_ANDROID"] or None,
        ),
    )


def _to_bool(value: str | None) -> bool:
    """설정 값은 문자열 한 칸이라, 참으로 읽을 표현을 좁게 정해둔다 — 운영자가
    DB 에 "True"/"1" 을 넣어도 켜지고, 그 밖의 값(빈 문자열·오타)은 꺼진 쪽으로
    기운다. 점검 모드는 실수로 켜지는 쪽이 더 위험하다."""
    return value is not None and value.strip().lower() in {"true", "1"}
