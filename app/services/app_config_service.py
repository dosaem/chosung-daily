import re
from dataclasses import dataclass

from flask import current_app

from app.errors import ValidationError
from app.models import PuzzleLanguage
from app.repositories.app_setting_repository import find_all_settings, save_settings
from app.schemas.config import AppConfigResponse, Maintenance, MinAppVersion, StoreUrls
from app.utils.redis_safe import safe_redis_call

# app_setting 테이블에서 운영자가 바꾸는 키들(토글 UI 는 티켓 23). 행이 없으면
# 아래 기본값으로 응답한다 — 설정 테이블이 비어 있어도 앱은 떠야 한다.
MIN_APP_VERSION_IOS_KEY = "min_app_version_ios"
MIN_APP_VERSION_ANDROID_KEY = "min_app_version_android"
MAINTENANCE_ENABLED_KEY = "maintenance_enabled"
MAINTENANCE_MESSAGE_KEY = "maintenance_message"

# 첫 스토어 릴리스 버전. "이 버전 미만이면 강제 업데이트" 규칙에서 기본값이
# 첫 릴리스면 아무도 막히지 않는다.
DEFAULT_MIN_APP_VERSION = "1.0.0"

# 최소 앱 버전은 "1.4.0" 처럼 숫자 셋이다 — 앱이 자기 버전과 비교할 수 있는
# 형태여야 한다(`v1.4`·"1.4" 는 비교가 안 된다). 운영자 폼에서 먼저 거른다.
APP_VERSION_PATTERN = re.compile(r"^\d{1,3}\.\d{1,4}\.\d{1,4}$")

# `AppSetting.value` 컬럼 길이. 넘기면 MySQL 이 에러를 내므로 먼저 걸러서
# 운영자에게 사유를 보여준다.
MAINTENANCE_MESSAGE_MAX_LENGTH = 500

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


def invalidate_app_config_cache() -> None:
    """`/config` 캐시를 버린다. 다음 호출이 DB 에서 다시 읽는다.

    TTL(60초)만 믿으면 점검 모드를 켠 뒤 최대 1분 동안 앱이 모르는데, 운영자가
    점검을 켜는 순간은 보통 마이그레이션 직전이라 그 1분이 사고가 된다.
    """
    safe_redis_call("delete", CACHE_KEY)


@dataclass(frozen=True)
class OperatorSettings:
    """운영자 토글 화면이 그리고 저장하는 값 네 개."""

    maintenance_enabled: bool
    maintenance_message: str
    min_app_version_ios: str
    min_app_version_android: str


def get_operator_settings() -> OperatorSettings:
    """토글 폼에 그릴 현재 값. 캐시를 보지 않고 DB 를 읽는다 — 운영자에게는
    60초 전 스냅샷이 아니라 지금 저장된 값을 보여줘야 한다."""
    settings = find_all_settings()
    return OperatorSettings(
        maintenance_enabled=_to_bool(settings.get(MAINTENANCE_ENABLED_KEY)),
        maintenance_message=settings.get(MAINTENANCE_MESSAGE_KEY) or "",
        min_app_version_ios=settings.get(MIN_APP_VERSION_IOS_KEY, DEFAULT_MIN_APP_VERSION),
        min_app_version_android=settings.get(
            MIN_APP_VERSION_ANDROID_KEY, DEFAULT_MIN_APP_VERSION
        ),
    )


def save_operator_settings(
    *,
    maintenance_enabled: bool,
    maintenance_message: str,
    min_app_version_ios: str,
    min_app_version_android: str,
) -> OperatorSettings:
    """점검 모드·최소 앱 버전 네 값을 한 커밋으로 저장하고 `/config` 캐시를 버린다.

    검증을 먼저 전부 하고 나서 쓴다 — 버전 하나가 틀렸는데 점검 모드만 켜지면
    운영자가 의도하지 않은 상태가 남는다.

    점검을 켤 때 메시지를 요구하는 이유: 앱 점검 화면(S7)이 보여줄 문구가 그
    메시지다. 비어 있으면 사용자는 아무 설명 없이 막힌 화면을 본다.
    """
    _validate_version("iOS", min_app_version_ios)
    _validate_version("Android", min_app_version_android)

    message = maintenance_message.strip()
    if len(message) > MAINTENANCE_MESSAGE_MAX_LENGTH:
        raise ValidationError(
            f"점검 메시지가 너무 깁니다 (최대 {MAINTENANCE_MESSAGE_MAX_LENGTH}자)."
        )
    if maintenance_enabled and not message:
        raise ValidationError("점검 모드를 켤 때는 앱에 보여줄 메시지를 적어주세요.")

    save_settings(
        {
            MAINTENANCE_ENABLED_KEY: "true" if maintenance_enabled else "false",
            MAINTENANCE_MESSAGE_KEY: message,
            MIN_APP_VERSION_IOS_KEY: min_app_version_ios.strip(),
            MIN_APP_VERSION_ANDROID_KEY: min_app_version_android.strip(),
        }
    )
    invalidate_app_config_cache()
    return get_operator_settings()


def _validate_version(platform: str, raw: str) -> None:
    if not APP_VERSION_PATTERN.match((raw or "").strip()):
        raise ValidationError(
            f"{platform} 최소 앱 버전은 1.4.0 처럼 숫자 세 자리로 적어주세요 "
            f"(받은 값: {(raw or '').strip()!r})."
        )


def _load_app_config() -> AppConfigResponse:
    settings = find_all_settings()

    return AppConfigResponse(
        min_app_version=MinAppVersion(
            ios=settings.get(MIN_APP_VERSION_IOS_KEY, DEFAULT_MIN_APP_VERSION),
            android=settings.get(MIN_APP_VERSION_ANDROID_KEY, DEFAULT_MIN_APP_VERSION),
        ),
        maintenance=Maintenance(
            enabled=_to_bool(settings.get(MAINTENANCE_ENABLED_KEY)),
            # 빈 메시지 행은 null 로 내려보낸다 — 앱은 "메시지 없음" 을 null 로
            # 판단하고(스펙 §A' 응답 표), 빈 문자열이면 빈 말풍선을 그린다.
            message=settings.get(MAINTENANCE_MESSAGE_KEY) or None,
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
