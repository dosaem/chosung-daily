"""앱 배포 워크플로(`.github/workflows/flutter.yml`)와 서명 설정의 계약 테스트.

`tests/test_deploy_workflow.py`(서버 배포)와 같은 이유다 — 워크플로는 푸시해야
돌아가고, 서명·스토어 업로드는 사람 산출물(keystore·match·Firebase 파일, 스펙 D0·D2)
없이는 로컬에서 끝까지 돌릴 수 없다. 그래서 돌려서 확인할 수 없는 부분(트리거·브랜치별
대상·경로·식별자·dart-define·쓰는 secret 이름·개인정보 라벨)을 파일에서 읽어 검증한다.

BASELINE(BuildUrPalace / Habitopia)에서 복사한 구조라, 치환을 빼먹어 다른 앱의
식별자가 남는 것이 가장 흔한 사고다. 그 검사를 제일 먼저 둔다.
"""

import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
MOBILE = ROOT / "mobile"
FLUTTER_CI = ROOT / ".github" / "workflows" / "flutter-ci.yml"
DISTRIBUTE = ROOT / ".github" / "workflows" / "flutter.yml"
RELEASE_DOC = ROOT / "docs" / "RELEASE.md"

APP_GRADLE = MOBILE / "android" / "app" / "build.gradle.kts"
KEY_PROPERTIES_EXAMPLE = MOBILE / "android" / "key.properties.example"
ANDROID_GITIGNORE = MOBILE / "android" / ".gitignore"
ANDROID_APPFILE = MOBILE / "android" / "fastlane" / "Appfile"
ANDROID_FASTFILE = MOBILE / "android" / "fastlane" / "Fastfile"
IOS_APPFILE = MOBILE / "ios" / "fastlane" / "Appfile"
IOS_FASTFILE = MOBILE / "ios" / "fastlane" / "Fastfile"
IOS_MATCHFILE = MOBILE / "ios" / "fastlane" / "Matchfile"
IOS_GITIGNORE = MOBILE / "ios" / ".gitignore"
PRIVACY_DETAILS = MOBILE / "ios" / "fastlane" / "app_privacy_details.json"
EXPORT_OPTIONS = MOBILE / "ios" / "ExportOptions.plist"
APP_ENV = MOBILE / "lib" / "config" / "app_env.dart"

BUNDLE_ID = "com.dosaem.chosung"
APPLE_TEAM_ID = "J8QUD7B666"

# YAML 1.1 에서 `on` 은 불린이라 PyYAML 이 트리거 키를 True 로 읽는다.
ON = True


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def distribute():
    return _load(DISTRIBUTE)


@pytest.fixture(scope="module")
def flutter_ci():
    return _load(FLUTTER_CI)


def _steps(workflow, job):
    return workflow["jobs"][job]["steps"]


def _flat(value):
    return yaml.safe_dump(value, allow_unicode=True)


def _runs(workflow, job):
    return [step.get("run", "") for step in _steps(workflow, job)]


def _build_steps(workflow, job):
    """`flutter build ...` 를 실행하는 스텝들."""
    return [step for step in _steps(workflow, job) if "flutter build" in step.get("run", "")]


# --- 복사·치환 -------------------------------------------------------------


OTHER_APPS = ["palace", "buildurpalace", "habitopia", "BuildUrPalace", "Habitopia"]

COPIED_FILES = [
    DISTRIBUTE,
    APP_GRADLE,
    KEY_PROPERTIES_EXAMPLE,
    ANDROID_APPFILE,
    ANDROID_FASTFILE,
    IOS_APPFILE,
    IOS_FASTFILE,
    IOS_MATCHFILE,
    PRIVACY_DETAILS,
    EXPORT_OPTIONS,
]


def _without_comments(path):
    """주석을 뺀 본문. BASELINE 출처를 적은 주석은 치환 누락이 아니다."""
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith(("#", "//", "<!--"))
    ]
    return "\n".join(lines)


@pytest.mark.parametrize("path", COPIED_FILES, ids=lambda p: p.name)
def test_copied_files_have_no_other_app_identifiers(path):
    """BASELINE 복사물에 다른 앱의 번들 ID·이름이 남아 있으면 남의 앱에 업로드된다."""
    text = _without_comments(path)

    for name in OTHER_APPS:
        assert name not in text, f"{path.name} 에 '{name}' 이 남아 있다"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (ANDROID_APPFILE, BUNDLE_ID),
        (IOS_APPFILE, BUNDLE_ID),
        (IOS_APPFILE, APPLE_TEAM_ID),
        (IOS_FASTFILE, BUNDLE_ID),
        (IOS_MATCHFILE, APPLE_TEAM_ID),
        (EXPORT_OPTIONS, BUNDLE_ID),
        (EXPORT_OPTIONS, APPLE_TEAM_ID),
        (APP_GRADLE, BUNDLE_ID),
    ],
    ids=lambda value: str(value)[-28:],
)
def test_identifiers_are_substituted(path, expected):
    assert expected in path.read_text(encoding="utf-8")


def test_export_options_points_at_the_match_profile_of_this_bundle():
    """프로파일 이름이 틀리면 아카이브는 되고 export 에서 죽는다(`match AppStore <id>`)."""
    options = plistlib.loads(EXPORT_OPTIONS.read_bytes())

    assert options["teamID"] == APPLE_TEAM_ID
    assert options["signingStyle"] == "manual"
    assert options["provisioningProfiles"] == {BUNDLE_ID: f"match AppStore {BUNDLE_ID}"}


def test_match_uses_the_shared_certificate_repository():
    text = IOS_MATCHFILE.read_text(encoding="utf-8")

    assert "dosaem/match-certs" in text
    assert 'type("appstore")' in text


def test_distribute_workflow_runs_on_the_self_hosted_runner(distribute):
    """서명·아카이브는 사용자 맥(러너)에서만 된다 — ubuntu 러너로 바뀌면 전부 실패한다."""
    runners = {job["runs-on"] for job in distribute["jobs"].values()}

    assert runners == {"self-hosted"}


def test_distribute_workflow_triggers_on_the_two_branches(distribute):
    trigger = distribute[ON]["push"]

    assert trigger["branches"] == ["main", "develop"]
    assert "mobile/**" in trigger["paths"]
    assert ".github/workflows/flutter.yml" in trigger["paths"]


def test_flutter_version_matches_the_ci_workflow(distribute, flutter_ci):
    """두 워크플로가 다른 Flutter 로 돌면 "CI 는 통과하는데 배포만 깨지는" 상태가 된다."""
    ci_version = next(
        step["with"]["flutter-version"]
        for step in _steps(flutter_ci, "analyze-and-test")
        if "flutter-action" in step.get("uses", "")
    )

    assert distribute["env"]["FLUTTER_VERSION"] == ci_version


@pytest.mark.parametrize("job", ["android", "ios"])
def test_flutter_commands_run_inside_the_mobile_directory(distribute, job):
    """Flutter 루트는 `mobile/` 이다 — 레포 루트에서 돌리면 pubspec 을 못 찾는다."""
    assert distribute["jobs"][job]["defaults"]["run"]["working-directory"] == "mobile"

    for step in _steps(distribute, job):
        directory = step.get("working-directory")
        if directory is not None:
            assert directory.startswith("mobile"), f"{step.get('name')} 의 작업 디렉터리"


@pytest.mark.parametrize("job", ["android", "ios"])
def test_action_inputs_use_workspace_relative_mobile_paths(distribute, job):
    """`uses:` 스텝의 경로는 `defaults.run.working-directory` 를 따르지 않는다.

    `build/...` 로 두면 artifact·Play 업로드가 레포 루트에서 파일을 찾아 빈손으로
    끝난다(`if-no-files-found: ignore` 라 조용히 성공한다).
    """
    for step in _steps(distribute, job):
        if "uses" not in step:
            continue
        for value in _flat(step.get("with", {})).splitlines():
            for match in re.finditer(r"\bbuild/app|\bbuild/ios", value):
                assert "mobile/" + match.group(0) in value, f"{step.get('name')}: {value}"


def test_dev_branch_ships_an_apk_to_firebase_app_distribution(distribute):
    steps = _steps(distribute, "android")
    apk = next(step for step in steps if "flutter build apk" in step.get("run", ""))
    firebase = next(step for step in steps if "appdistribution:distribute" in step.get("run", ""))

    assert apk["if"] == firebase["if"] == "needs.setup.outputs.is_prod == 'false'"
    assert "app-release.apk" in firebase["run"]
    assert "--groups" in firebase["run"]


def test_main_branch_ships_an_aab_to_the_play_internal_track(distribute):
    steps = _steps(distribute, "android")
    aab = next(step for step in steps if "flutter build appbundle" in step.get("run", ""))
    play = next(step for step in steps if "upload-google-play" in step.get("uses", ""))

    assert aab["if"] == play["if"] == "needs.setup.outputs.is_prod == 'true'"
    assert play["with"]["packageName"] == BUNDLE_ID
    assert play["with"]["track"] == "internal"
    assert play["with"]["releaseFiles"].startswith("mobile/build/app/outputs/bundle/release/")


def test_aab_step_keeps_the_strip_false_positive_handling(distribute):
    """`debugSymbolLevel=FULL` 이면 flutter tool 이 정상 AAB 를 만들고도 exit 1 을 준다.

    그 처리를 되돌리면 main 푸시가 항상 빨갛게 끝난다. 대신 AAB 가 진짜 생겼는지와
    배포 lib 이 스트립됐는지를 직접 확인한다(오탐을 무조건 삼키지 않는다).
    """
    aab = next(
        step
        for step in _steps(distribute, "android")
        if "flutter build appbundle" in step.get("run", "")
    )
    run = aab["run"]

    assert "|| echo" in run, "오탐 처리(|| echo ...)가 없다"
    assert "test -f" in run, "AAB 존재 확인이 없다"
    assert "verify_appbundle.py" in run, "AAB 내용 검증(스트립 포함)이 없다"


def test_both_platforms_upload_to_testflight_regardless_of_branch(distribute):
    """iOS 는 develop·main 모두 TestFlight 다(스토어 승격은 사람)."""
    steps = _steps(distribute, "ios")
    upload = next(step for step in steps if "altool --upload-app" in step.get("run", ""))

    assert "if" not in upload
    assert "--apiKey" in upload["run"]


def test_ios_signing_uses_match_in_an_isolated_keychain(distribute):
    steps = _steps(distribute, "ios")
    match = next(step for step in steps if "fastlane match" in step.get("run", ""))
    cleanup = next(step for step in steps if "delete-keychain" in step.get("run", ""))

    assert "--readonly" in match["run"], "CI 가 인증서를 새로 만들면 안 된다"
    assert "create-keychain" in match["run"]
    assert cleanup["if"] == "always()", "실패해도 임시 keychain 은 지운다"


def test_every_run_step_is_valid_shell(distribute):
    """YAML 블록 안의 셸은 푸시해야 돌아간다 — heredoc 들여쓰기 하나로 죽는다."""
    for job in distribute["jobs"]:
        for step in _steps(distribute, job):
            script = step.get("run")
            if not script:
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
                handle.write(script)
                path = handle.name
            try:
                result = subprocess.run(
                    ["bash", "-n", path], check=False, capture_output=True, text=True
                )
            finally:
                os.unlink(path)
            assert result.returncode == 0, f"{job}/{step.get('name')}: {result.stderr}"


def test_artifact_names_belong_to_this_app(distribute):
    names = [
        step["with"]["name"]
        for job in ("android", "ios")
        for step in _steps(distribute, job)
        if "upload-artifact" in step.get("uses", "")
    ]

    assert len(names) == 2
    assert all(name.startswith("chosung-") for name in names)


# --- dart-define -----------------------------------------------------------


REQUIRED_DART_DEFINES = [
    "API_BASE_URL",
    "GOOGLE_SERVER_CLIENT_ID",
    "ADMOB_BANNER_AD_UNIT_ID",
    "ADMOB_INTERSTITIAL_AD_UNIT_ID",
    "ADMOB_REWARDED_AD_UNIT_ID",
]


def _dart_defines(workflow, job):
    """잡의 `DART_DEFINES` 환경변수에 적힌 `--dart-define=NAME=값` 의 NAME 들."""
    return re.findall(r"--dart-define=([A-Z0-9_]+)=", workflow["jobs"][job]["env"]["DART_DEFINES"])


@pytest.mark.parametrize("job", ["android", "ios"])
def test_every_build_passes_the_dart_defines(distribute, job):
    """하나라도 빠지면 그 빌드만 로컬 기본값(에뮬레이터 주소)으로 서버를 찾는다."""
    builds = _build_steps(distribute, job)

    assert builds, f"{job} 잡에 flutter build 스텝이 없다"
    for step in builds:
        assert "$DART_DEFINES" in step["run"], step.get("name")


@pytest.mark.parametrize("job", ["android", "ios"])
@pytest.mark.parametrize("name", REQUIRED_DART_DEFINES)
def test_dart_defines_cover_api_ads_and_login(distribute, job, name):
    assert name in _dart_defines(distribute, job)


@pytest.mark.parametrize("job", ["android", "ios"])
def test_ad_unit_ids_are_platform_specific(distribute, job):
    """AdMob 유닛은 앱(플랫폼)마다 다르다 — 같은 값을 두 잡에 주면 노출이 안 붙는다."""
    defines = distribute["jobs"][job]["env"]["DART_DEFINES"]
    platform = "ANDROID" if job == "android" else "IOS"
    other = "IOS" if job == "android" else "ANDROID"

    assert f"ADMOB_BANNER_AD_UNIT_ID_{platform}" in defines
    assert f"_{other}" not in defines


def test_api_base_url_comes_from_the_branch_target(distribute):
    """main → prod, develop → develop 인스턴스(8090). 한 잡이 두 주소를 고른다."""
    resolve = next(step for step in _steps(distribute, "setup") if step.get("id") == "env")
    run = resolve["run"]

    assert "API_BASE_URL_PROD" in run
    assert "API_BASE_URL_DEV" in run
    assert "refs/heads/main" in run
    assert distribute["jobs"]["setup"]["outputs"]["api_base_url"]

    for job in ("android", "ios"):
        assert "needs.setup.outputs.api_base_url" in distribute["jobs"][job]["env"]["DART_DEFINES"]


def test_build_stops_when_the_api_base_url_is_not_configured(distribute):
    """빈 값을 그대로 넘기면 앱이 빈 주소로 빌드돼 테스터 손에서만 깨진다."""
    resolve = next(step for step in _steps(distribute, "setup") if step.get("id") == "env")

    assert re.search(r"exit 1", resolve["run"])
    assert re.search(r'-z "\$API_BASE_URL', resolve["run"])


def test_api_base_url_define_matches_the_app_constant():
    """워크플로가 넘기는 이름과 앱이 읽는 이름이 갈라지면 아무 말 없이 기본값이 쓰인다."""
    assert "String.fromEnvironment(\n    'API_BASE_URL'" in APP_ENV.read_text(encoding="utf-8")


def test_dart_define_names_are_documented(distribute):
    """31(광고)·29(로그인) 이 같은 이름을 쓰도록 RELEASE.md 에 적어 둔다."""
    doc = RELEASE_DOC.read_text(encoding="utf-8")

    for job in ("android", "ios"):
        for name in _dart_defines(distribute, job):
            assert f"`{name}`" in doc, f"{name} 이 RELEASE.md 에 없다"


# --- flutter-ci.yml 과의 분리 ---------------------------------------------


def test_analyze_and_test_stay_in_the_ci_workflow(flutter_ci):
    """이 티켓은 flutter-ci.yml 을 건드리지 않는다 — 린트·테스트는 무료 러너에 둔다."""
    job = flutter_ci["jobs"]["analyze-and-test"]
    commands = [step.get("run", "") for step in job["steps"]]

    assert job["runs-on"] == "ubuntu-latest"
    assert any("flutter analyze" in cmd for cmd in commands)
    assert any("flutter test" in cmd for cmd in commands)


def test_distribute_workflow_does_not_duplicate_analyze_or_test(distribute, flutter_ci):
    runs = " ".join(
        _runs(distribute, "setup") + _runs(distribute, "android") + _runs(distribute, "ios")
    )

    assert "flutter analyze" not in runs
    assert "flutter test" not in runs
    assert distribute["name"] != flutter_ci["name"]


# --- secrets·variables 문서화 ---------------------------------------------


SECTION_34 = "### 34."


def _section_34():
    text = RELEASE_DOC.read_text(encoding="utf-8")
    assert SECTION_34 in text, "RELEASE.md 에 '### 34.' 절이 없다"
    body = text.split(SECTION_34, 1)[1]
    # 다음 티켓 절이 붙으면 거기서 끊는다.
    return re.split(r"\n### \d", body)[0]


def _table_names(markdown):
    """표의 첫 칸에 `` `NAME` `` 으로 적힌 것들."""
    names = set()
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        match = re.fullmatch(r"`([A-Z0-9_]+)`", cell)
        if match:
            names.add(match.group(1))
    return names


def test_workflow_secrets_and_variables_are_documented(distribute):
    """사람이 등록해야 하는 값이다 — 문서에 없으면 빨간 빌드만 보고 이유를 모른다."""
    flat = _flat(distribute)
    used = set(re.findall(r"secrets\.([A-Z0-9_]+)", flat)) | set(
        re.findall(r"vars\.([A-Z0-9_]+)", flat)
    )

    assert used, "secret·variable 을 하나도 안 쓰는 배포 워크플로는 없다"
    assert used <= _table_names(_section_34())


def test_documented_secrets_cover_signing_stores_and_firebase(distribute):
    used = set(re.findall(r"secrets\.([A-Z0-9_]+)", _flat(distribute)))

    assert {"KEYSTORE_BASE64", "KEYSTORE_PASSWORD", "KEY_ALIAS", "KEY_PASSWORD"} <= used
    assert {"MATCH_PASSWORD", "MATCH_GIT_BASIC_AUTHORIZATION"} <= used
    assert {"APP_STORE_CONNECT_API_KEY", "GOOGLE_PLAY_KEY_JSON"} <= used
    assert {"FIREBASE_APP_ID", "FIREBASE_SERVICE_ACCOUNT"} <= used


def test_release_doc_names_the_match_repository_and_tester_group(distribute):
    section = _section_34()
    group = re.search(r'--groups "([^"]+)"', DISTRIBUTE.read_text(encoding="utf-8")).group(1)

    assert "dosaem/match-certs" in section
    assert group in section


def test_release_doc_separates_what_only_a_human_can_do():
    """릴리스 빌드는 D0(Firebase 파일)·D2(keystore·match) 가 있어야 돈다 — 워커 조건이 아니다."""
    section = _section_34()

    assert "D0" in section
    assert "D2" in section
    assert "flutter build apk --debug" in section
    assert "build ipa" in section


# --- 서명·심볼 (Gradle) ----------------------------------------------------


def test_release_signing_reads_key_properties():
    text = APP_GRADLE.read_text(encoding="utf-8")

    assert "key.properties" in text
    assert 'create("release")' in text
    assert all(
        key in text for key in ("storeFile", "storePassword", "keyAlias", "keyPassword")
    )


def test_release_falls_back_to_debug_signing_without_key_properties():
    """keystore 가 없는 로컬·새 클론에서도 release 빌드가 돌아야 한다(D2 전)."""
    text = APP_GRADLE.read_text(encoding="utf-8")

    assert 'findByName("release")' in text
    assert 'getByName("debug")' in text


def test_release_keeps_full_native_debug_symbols():
    """심볼이 없으면 Play 콘솔의 네이티브 크래시가 주소로만 찍힌다."""
    text = APP_GRADLE.read_text(encoding="utf-8")

    assert 'debugSymbolLevel = "FULL"' in text


def test_key_properties_example_lists_the_keys_without_values():
    text = KEY_PROPERTIES_EXAMPLE.read_text(encoding="utf-8")

    assert "storeFile=upload-keystore.jks" in text
    assert "keyAlias=" in text
    for key in ("storePassword", "keyPassword"):
        value = re.search(rf"^{key}=(.*)$", text, re.MULTILINE).group(1)
        assert value.startswith("<"), f"{key} 에 실제 비밀번호처럼 보이는 것이 있다"


@pytest.mark.parametrize(
    ("gitignore", "pattern"),
    [
        (ANDROID_GITIGNORE, "key.properties"),
        (ANDROID_GITIGNORE, "*.jks"),
        (ANDROID_GITIGNORE, "fastlane/google-play-key.json"),
        (IOS_GITIGNORE, "fastlane/api_key.json"),
    ],
    ids=lambda value: str(value)[-28:],
)
def test_secret_files_are_not_committable(gitignore, pattern):
    """BASELINE 레포는 Play 서비스 계정 키·ASC 키를 커밋해 뒀다 — 따라가지 않는다."""
    assert pattern in gitignore.read_text(encoding="utf-8")


# --- 개인정보 라벨 ---------------------------------------------------------


@pytest.fixture(scope="module")
def privacy():
    return json.loads(PRIVACY_DETAILS.read_text(encoding="utf-8"))


# ASC 개인정보 라벨 ↔ `/privacy` 1절 "수집하는 정보". 왼쪽이 ASC 카테고리.
COLLECTED = {
    "USER_ID": "게스트 토큰",
    "EMAIL_ADDRESS": "계정 이메일",
    # 아래 세 줄은 티켓 35 의 1:1 대조에서 더해졌다(docs/legal-checklist.md
    # "9. 스토어 라벨"): refresh token 은 ASC 에 "기타 데이터" 자리가 있고,
    # 접속기록은 티켓 36 이 만든 수집이라 34 당시에는 없었다. 대략적인 위치는
    # 위치 권한 없이도 AdMob SDK 가 광고 요청의 IP 로 추정해 기기 밖으로 보낸다 —
    # 우리 서버에 저장하지 않는다는 것은 신고 제외 근거가 아니다(최종 리뷰 D-35-4).
    "OTHER_DATA_TYPES": "애플 refresh token",
    "GAMEPLAY_CONTENT": "시도 기록",
    "PURCHASE_HISTORY": "구독 식별자",
    "DEVICE_ID": "광고 ID",
    "ADVERTISING_DATA": "광고 ID(광고 요청·측정)",
    "COARSE_LOCATION": "광고 요청 정보(대략적 위치 — AdMob 이 IP 로 추정)",
    "PRODUCT_INTERACTION": "앱 사용 이벤트(Firebase Analytics)",
    "CRASH_DATA": "접속·오류 기록(Sentry)",
    "PERFORMANCE_DATA": "접속·오류 기록(Sentry)",
    "OTHER_DIAGNOSTIC_DATA": "접속·오류 기록(접속기록·접근 로그)",
}

PURPOSES = {
    "THIRD_PARTY_ADVERTISING",
    "DEVELOPERS_ADVERTISING",
    "ANALYTICS",
    "PRODUCT_PERSONALIZATION",
    "APP_FUNCTIONALITY",
    "OTHER_PURPOSES",
}
PROTECTIONS = {"DATA_LINKED_TO_YOU", "DATA_NOT_LINKED_TO_YOU", "DATA_USED_TO_TRACK_YOU"}


def test_privacy_details_lists_exactly_what_the_app_collects(privacy):
    """스펙 §B.25 의 재작성 대상. 빠지면 심사 반려, 남으면 거짓 신고다."""
    assert {entry["category"] for entry in privacy} == set(COLLECTED)


def test_privacy_details_entries_use_valid_asc_values(privacy):
    for entry in privacy:
        assert set(entry["purposes"]) <= PURPOSES, entry["category"]
        assert set(entry["data_protections"]) <= PROTECTIONS, entry["category"]
        assert entry["purposes"], entry["category"]
        assert entry["data_protections"], entry["category"]


def test_account_bound_data_is_declared_as_linked_to_the_user(privacy):
    """게스트 토큰·이메일·시도 기록·구독은 한 사람의 기록으로 이어져 있다."""
    by_category = {entry["category"]: entry for entry in privacy}

    for category in ("USER_ID", "EMAIL_ADDRESS", "GAMEPLAY_CONTENT", "PURCHASE_HISTORY"):
        assert "DATA_LINKED_TO_YOU" in by_category[category]["data_protections"], category
        assert "APP_FUNCTIONALITY" in by_category[category]["purposes"], category


def test_advertising_identifiers_are_declared_as_tracking(privacy):
    """ATT 프롬프트를 띄우고 AdMob 에 광고 ID 를 넘긴다 — 추적으로 신고해야 한다."""
    by_category = {entry["category"]: entry for entry in privacy}

    for category in ("DEVICE_ID", "ADVERTISING_DATA", "COARSE_LOCATION"):
        entry = by_category[category]
        assert "DATA_USED_TO_TRACK_YOU" in entry["data_protections"], category
        assert "THIRD_PARTY_ADVERTISING" in entry["purposes"], category
        assert "DATA_LINKED_TO_YOU" not in entry["data_protections"], category


def test_diagnostics_are_declared_as_not_linked(privacy):
    """Sentry 로 가는 오류 기록은 식별 정보를 마스킹해서 보낸다(`/privacy` 1절)."""
    by_category = {entry["category"]: entry for entry in privacy}

    for category in ("CRASH_DATA", "PERFORMANCE_DATA"):
        entry = by_category[category]
        assert entry["purposes"] == ["APP_FUNCTIONALITY"], category
        assert entry["data_protections"] == ["DATA_NOT_LINKED_TO_YOU"], category


# --- iOS 아카이브 서명 (D-34-1) --------------------------------------------


PBXPROJ = MOBILE / "ios" / "Runner.xcodeproj" / "project.pbxproj"
MATCH_PROFILE = f"match AppStore {BUNDLE_ID}"


def _build_settings(config_id):
    """pbxproj 의 XCBuildConfiguration 한 블록의 `키 = 값` 들."""
    text = PBXPROJ.read_text(encoding="utf-8")
    block = re.search(
        rf"\t\t{config_id} /\* \w+ \*/ = \{{.*?\n\t\t\}};", text, re.DOTALL
    )
    assert block, f"{config_id} 블록이 없다"
    settings = {}
    for line in block.group(0).splitlines():
        # `"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "..."` 처럼 키가 인용될 수 있다.
        pair = re.match(r'\s*(?:"([^"]+)"|([A-Za-z_0-9]+))\s*=\s*(.+);\s*$', line)
        if pair:
            settings[pair.group(1) or pair.group(2)] = pair.group(3).strip('"')
    return settings


# 프로젝트 레벨 Release, Runner 타깃 Release. `flutter build ipa` 는 이 둘로 아카이브한다.
RELEASE_CONFIG_IDS = ["97C147041CF9000F007C117D", "97C147071CF9000F007C117D"]


@pytest.mark.parametrize("config_id", RELEASE_CONFIG_IDS)
def test_release_archive_signs_with_a_distribution_identity(config_id):
    """개발용 identity 로는 App Store 아카이브가 안 된다 — D2 는 배포 인증서만 만든다."""
    settings = _build_settings(config_id)
    identities = {
        value
        for key, value in settings.items()
        if key.startswith("CODE_SIGN_IDENTITY")
    }

    assert identities, f"{config_id}: Release 에 CODE_SIGN_IDENTITY 가 없다"
    assert identities == {"Apple Distribution"}, identities


def test_release_archive_uses_the_match_app_store_profile():
    """match 가 만드는 프로파일 이름 그대로여야 manual 서명이 그걸 집는다."""
    settings = _build_settings("97C147071CF9000F007C117D")

    assert settings.get("CODE_SIGN_STYLE") == "Manual", (
        "Automatic 이면 Xcode 가 개발 프로파일을 알아서 집는다"
    )
    assert settings.get("PROVISIONING_PROFILE_SPECIFIER") == MATCH_PROFILE
    assert settings.get("DEVELOPMENT_TEAM") == APPLE_TEAM_ID


def test_archive_and_export_name_the_same_profile():
    """export plist 는 이미 만든 아카이브에만 적용된다 — 아카이브 쪽이 갈라지면 죽는다."""
    export = plistlib.loads(EXPORT_OPTIONS.read_bytes())
    settings = _build_settings("97C147071CF9000F007C117D")

    assert export["provisioningProfiles"][BUNDLE_ID] == settings[
        "PROVISIONING_PROFILE_SPECIFIER"
    ]


# --- 수동 fastlane lane 의 dart-define (D-34-2) -----------------------------


# 사람이 맥에서 손으로 올릴 때도 Actions 와 같은 값으로 빌드해야 한다.
FASTLANE_BUILD_FUNCTIONS = [
    (ANDROID_FASTFILE, "build_appbundle"),
    (IOS_FASTFILE, "build_flutter_ios"),
]

# 원본 Fastfile 의 빌드 함수만 평가해 `sh` 가 받는 명령을 포착한다(외부 호출 없음).
CAPTURE_RB = r"""
CAPTURED = []
def sh(cmd); CAPTURED << cmd; end
def default_platform(_); end
module UI
  def self.user_error!(message)
    warn "USER_ERROR: #{message}"
    exit 2
  end
end
# 산출물 유무는 이 하네스의 관심사가 아니다(명령만 포착하고 빌드는 돌리지 않는다).
def File.exist?(_); true; end
source = File.read(ARGV[0]).sub(/^platform :\w+ do.*\z/m, "")
eval(source)
send(ARGV[1], clean: false)
puts CAPTURED
"""

ruby_only = pytest.mark.skipif(
    shutil.which("ruby") is None, reason="fastlane lane 평가에 ruby 가 필요하다"
)


def _capture_lane_build(fastfile, function, env):
    with tempfile.NamedTemporaryFile("w", suffix=".rb", delete=False) as handle:
        handle.write(CAPTURE_RB)
        script = handle.name
    # 빌드 함수는 `Dir.chdir("../..")` 로 Flutter 루트로 올라가고 거기서 이전 AAB 를
    # 지운다 — 레포 안에서 돌리면 레포 밖을 가리키므로 빈 임시 디렉터리에서 돌린다.
    sandbox = tempfile.mkdtemp()
    try:
        return subprocess.run(
            ["ruby", script, str(fastfile), function],
            check=False,
            capture_output=True,
            text=True,
            cwd=sandbox,
            env={**os.environ, **env},
        )
    finally:
        os.unlink(script)
        shutil.rmtree(sandbox, ignore_errors=True)


def _manual_lane_env():
    return {name: f"value-for-{name}" for name in REQUIRED_DART_DEFINES}


@ruby_only
@pytest.mark.parametrize(
    ("fastfile", "function"), FASTLANE_BUILD_FUNCTIONS, ids=lambda v: str(v)[-20:]
)
@pytest.mark.parametrize("name", REQUIRED_DART_DEFINES)
def test_manual_lane_build_passes_the_dart_defines(fastfile, function, name):
    """빠지면 앱이 에뮬레이터 기본 주소(app_env.dart)로 서버를 찾는다."""
    result = _capture_lane_build(fastfile, function, _manual_lane_env())

    assert result.returncode == 0, result.stderr
    assert f"--dart-define={name}=value-for-{name}" in result.stdout, result.stdout


@ruby_only
@pytest.mark.parametrize(
    ("fastfile", "function"), FASTLANE_BUILD_FUNCTIONS, ids=lambda v: str(v)[-20:]
)
@pytest.mark.parametrize("missing", REQUIRED_DART_DEFINES)
def test_manual_lane_stops_when_a_dart_define_is_missing(fastfile, function, missing):
    """값 없이 업로드하면 스토어에 잘못 설정된 바이너리가 올라간다 — 빌드 전에 멈춘다."""
    env = _manual_lane_env()
    env[missing] = ""
    result = _capture_lane_build(fastfile, function, env)

    assert result.returncode == 2, (result.returncode, result.stdout, result.stderr)
    assert missing in result.stderr
    assert "flutter build" not in result.stdout


@pytest.mark.parametrize(
    "fastfile", [ANDROID_FASTFILE, IOS_FASTFILE], ids=lambda v: str(v)[-20:]
)
def test_manual_lane_dart_define_names_are_documented(fastfile):
    """Actions 와 수동 lane 이 같은 이름을 쓰는지 RELEASE.md 에서 대조할 수 있어야 한다."""
    doc = RELEASE_DOC.read_text(encoding="utf-8")

    for name in REQUIRED_DART_DEFINES:
        assert name in fastfile.read_text(encoding="utf-8"), name
        assert f"`{name}`" in doc, name


# --- 실패 후 인증 자료 정리 (D-34-3) ---------------------------------------


def _step_with(workflow, job, needle):
    return next(step for step in _steps(workflow, job) if needle in step.get("run", ""))


def _cleanup_steps(workflow, job):
    return [step for step in _steps(workflow, job) if step.get("if") == "always()"]


def _run_block(script, env, cwd):
    """워크플로의 `run` 블록을 스텁과 함께 실제로 돌린다(Actions 는 `bash -e`)."""
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as handle:
        handle.write(script)
        path = handle.name
    try:
        return subprocess.run(
            ["bash", path],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            env=env,
        )
    finally:
        os.unlink(path)


def test_android_signing_material_is_deleted_after_the_job(distribute):
    """self-hosted 러너는 잡이 끝나도 호스트가 남는다 — keystore 를 두고 나가면 안 된다."""
    cleanups = "\n".join(step["run"] for step in _cleanup_steps(distribute, "android"))

    assert "upload-keystore.jks" in cleanups
    assert "key.properties" in cleanups


def test_firebase_key_is_removed_when_the_upload_fails(distribute, tmp_path):
    step = _step_with(distribute, "android", "appdistribution:distribute")
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_RUN_ID": "pytest",
        "GITHUB_SHA": "0" * 40,
        "FIREBASE_APP_ID": "1:0:android:0",
        "FIREBASE_SERVICE_ACCOUNT": '{"type":"service_account"}',
        "RELEASE_NOTES": "pytest",
    }
    result = _run_block(
        "npx() { echo 'stubbed upload failure' >&2; return 1; }\nset -e\n" + step["run"],
        env,
        tmp_path,
    )

    assert result.returncode != 0, "스텁이 실패를 못 만들었다"
    assert list(runner_temp.iterdir()) == [], "업로드 실패 후 서비스 계정 키가 남는다"


def test_keychain_name_reaches_the_cleanup_step_even_if_match_fails(
    distribute, tmp_path
):
    """이름이 match 뒤에 export 되면 `always()` 정리가 keychain 을 못 찾는다."""
    step = _step_with(distribute, "ios", "fastlane match")
    github_env = tmp_path / "github_env"
    github_env.write_text("")
    stubs = (
        'security() { if [ "$1" = "list-keychains" ]; then echo \'"login.keychain"\'; fi; }\n'
        "openssl() { echo stub-password; }\n"
        "fastlane() { echo 'stubbed match failure' >&2; return 1; }\n"
    )
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "GITHUB_RUN_ID": "pytest",
        "GITHUB_ENV": str(github_env),
    }
    result = _run_block(stubs + "set -e\n" + step["run"], env, tmp_path)

    assert result.returncode != 0, "스텁이 실패를 못 만들었다"
    assert "KEYCHAIN_NAME=ci-pytest.keychain" in github_env.read_text(encoding="utf-8")


def test_extracted_p8_is_removed_when_the_testflight_upload_fails(
    distribute, tmp_path
):
    step = _step_with(distribute, "ios", "altool --upload-app")
    (tmp_path / "build" / "ios" / "ipa").mkdir(parents=True)
    (tmp_path / "build" / "ios" / "ipa" / "chosung.ipa").write_text("")
    workdir = tmp_path / "ios" / "fastlane"
    workdir.mkdir(parents=True)
    (workdir / "api_key.json").write_text('{"key_id":"PYTEST","issuer_id":"i","key":"k"}')
    stubs = (
        'jq() { case "$2" in .key_id) echo PYTEST ;; .issuer_id) echo ISSUER ;;'
        ' .key) echo STUB-KEY ;; esac; }\n'
        "xcrun() { echo 'stubbed altool failure' >&2; return 1; }\n"
    )
    env = {**os.environ, "HOME": str(tmp_path / "home")}
    (tmp_path / "home").mkdir()
    result = _run_block(stubs + "set -e\n" + step["run"], env, tmp_path / "ios")

    assert result.returncode != 0, "스텁이 실패를 못 만들었다"
    leftover = list((tmp_path / "home").rglob("*.p8"))
    assert leftover == [], f"업로드 실패 후 ASC 개인키가 남는다: {leftover}"


def test_asc_api_key_file_is_deleted_after_the_job(distribute):
    cleanups = "\n".join(step["run"] for step in _cleanup_steps(distribute, "ios"))

    assert "api_key.json" in cleanups
    assert "delete-keychain" in cleanups


# --- 이번 빌드가 만든 AAB 만 업로드한다 (D-34-4) ---------------------------

VERIFY_AAB = MOBILE / "tool" / "verify_appbundle.py"
AAB_IN_BUNDLE = "build/app/outputs/bundle/release/app-release.aab"


def _elf(*, stripped):
    """`file` 이 ELF 섹션 헤더에서 심볼 테이블을 찾아 "not stripped" 를 붙인다.

    테스트가 로컬 NDK 나 커밋한 바이너리에 기대지 않도록 최소 ELF 를 직접 만든다.
    같은 검사를 실제 NDK 의 aarch64 `.so`(스트립 전/후)로도 돌려봤다 —
    `review/impl-evidence-34.md` "수정 라운드 2".
    """
    names = b"\0.shstrtab\0.symtab\0"
    sections = [(0, 0), (1, 3)] + ([(11, 2)] if not stripped else [])
    ehsize = shentsize = 64
    header = b"\x7fELF\x02\x01\x01\x00" + b"\0" * 8
    header += struct.pack("<HHI", 3, 183, 1)  # ET_DYN, EM_AARCH64, EV_CURRENT
    header += struct.pack("<QQQ", 0, 0, ehsize + len(names))  # entry, phoff, shoff
    header += struct.pack("<IHHHHHH", 0, ehsize, 0, 0, shentsize, len(sections), 1)
    table = b"".join(
        struct.pack("<IIQQQQIIQQ", name, typ, 0, 0, ehsize if typ == 3 else 0, 0, 0, 0, 1, 0)
        for name, typ in sections
    )
    return header + names + table


def _make_aab(path, *, manifest=True, lib="base/lib/arm64-v8a/libapp.so", stripped=True):
    with zipfile.ZipFile(path, "w") as bundle:
        if manifest:
            bundle.writestr("base/manifest/AndroidManifest.xml", b"<manifest/>")
        if lib:
            bundle.writestr(lib, _elf(stripped=stripped))
    return path


def _verify(path):
    return subprocess.run(
        ["python3", str(VERIFY_AAB), str(path)], capture_output=True, text=True, check=False
    )


def test_verify_appbundle_accepts_a_bundle_with_stripped_delivered_libs(tmp_path):
    result = _verify(_make_aab(tmp_path / "ok.aab"))

    assert result.returncode == 0, (result.stdout, result.stderr)


def test_verify_appbundle_rejects_a_bundle_whose_libs_are_not_stripped(tmp_path):
    """`exit 1` 을 삼키는 유일한 근거가 "스트립 오탐" 이다 — 진짜 실패면 멈춘다."""
    result = _verify(_make_aab(tmp_path / "unstripped.aab", stripped=False))

    assert result.returncode == 1
    assert "스트립되지 않았다" in result.stderr


def test_verify_appbundle_rejects_a_bundle_without_the_dart_library(tmp_path):
    result = _verify(_make_aab(tmp_path / "nolib.aab", lib=None))

    assert result.returncode == 1
    assert "libapp.so" in result.stderr


def test_verify_appbundle_rejects_a_truncated_bundle(tmp_path):
    """빌드가 중간에 끊겨 쓰다 만 파일이 남으면 존재 검사만으로는 통과한다."""
    broken = tmp_path / "broken.aab"
    broken.write_bytes(_make_aab(tmp_path / "src.aab").read_bytes()[:40])

    result = _verify(broken)

    assert result.returncode == 1
    assert "zip" in result.stderr


def test_verify_appbundle_rejects_a_missing_bundle(tmp_path):
    result = _verify(tmp_path / "absent.aab")

    assert result.returncode == 1
    assert "만들지 못했다" in result.stderr


# 원본 Fastfile 의 lane 을 끝까지(업로드 진입점까지) 평가한다. `sh` 는 실제 셸을
# 돌리고, 외부 호출인 `upload_to_play_store` 만 출력으로 바꾼다.
LANE_RB = r"""
LANES = {}
def default_platform(_); end
def platform(_name); yield; end
def desc(_text); end
def lane(name, &block); LANES[name] = block; end
def sh(command)
  system(command) or raise "sh failed: #{command}"
end
module UI
  def self.user_error!(message)
    warn "USER_ERROR: #{message}"
    exit 2
  end
end
def upload_to_play_store(**options)
  puts "UPLOAD_REACHED: #{options[:track]}"
end
eval(File.read(ARGV[0]))
LANES[ARGV[1].to_sym].call({})
"""

# PATH 앞에 끼워 flutter 를 대신한다. 종료 코드와 산출물을 따로 정한다.
FAKE_FLUTTER = f"""#!/bin/sh
echo "fake flutter $*"
if [ -n "$FAKE_AAB_SOURCE" ]; then
  mkdir -p "$(dirname "{AAB_IN_BUNDLE}")"
  cp "$FAKE_AAB_SOURCE" "{AAB_IN_BUNDLE}"
fi
exit "$FAKE_FLUTTER_EXIT"
"""


def _run_android_lane(tmp_path, *, exit_code, produces=None, stale=False, lane="beta"):
    """임시 mobile/ 트리에 원본 Fastfile 을 놓고 lane 을 돌린다."""
    mobile = tmp_path / "mobile"
    fastlane_dir = mobile / "android" / "fastlane"
    fastlane_dir.mkdir(parents=True)
    (mobile / "tool").mkdir()
    shutil.copy(ANDROID_FASTFILE, fastlane_dir / "Fastfile")
    shutil.copy(VERIFY_AAB, mobile / "tool" / "verify_appbundle.py")

    if stale:
        previous = mobile / AAB_IN_BUNDLE
        previous.parent.mkdir(parents=True)
        _make_aab(previous)

    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    flutter = stub_dir / "flutter"
    flutter.write_text(FAKE_FLUTTER)
    flutter.chmod(0o755)

    harness = tmp_path / "lane.rb"
    harness.write_text(LANE_RB)

    env = {
        **os.environ,
        **_manual_lane_env(),
        "PATH": f"{stub_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_FLUTTER_EXIT": str(exit_code),
        "FAKE_AAB_SOURCE": str(produces) if produces else "",
    }
    return subprocess.run(
        ["ruby", str(harness), "Fastfile", lane],
        cwd=fastlane_dir,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


@ruby_only
@pytest.mark.parametrize("lane", ["beta", "release"])
def test_manual_lane_does_not_upload_a_stale_aab_when_the_build_fails(tmp_path, lane):
    """D-34-4: 빌드 실패를 삼킨 뒤 지난 AAB 를 올리면 다른 소스·다른 API 환경이 나간다.

    `clean:` 은 선택이라 문서의 기본 명령으로는 이전 산출물이 그대로 남는다.
    """
    result = _run_android_lane(tmp_path, exit_code=1, produces=None, stale=True, lane=lane)

    assert result.returncode != 0, (result.stdout, result.stderr)
    assert "UPLOAD_REACHED" not in result.stdout, result.stdout
    assert "AAB was not produced" in result.stderr, result.stderr


@ruby_only
def test_manual_lane_uploads_the_aab_this_build_produced(tmp_path):
    """위 테스트가 늘 실패하는 게 아니라 산출물 출처를 본다는 대조군."""
    aab = _make_aab(tmp_path / "fresh.aab")
    result = _run_android_lane(tmp_path, exit_code=0, produces=aab)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "UPLOAD_REACHED: internal" in result.stdout


@ruby_only
def test_manual_lane_still_tolerates_the_strip_false_positive(tmp_path):
    """오탐(exit 1 + 정상 AAB)은 그대로 통과해야 한다 — 수동 배포가 막히면 안 된다."""
    aab = _make_aab(tmp_path / "fresh.aab")
    result = _run_android_lane(tmp_path, exit_code=1, produces=aab, stale=True)

    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "UPLOAD_REACHED: internal" in result.stdout


@ruby_only
def test_manual_lane_rejects_a_new_but_unstripped_aab(tmp_path):
    """이번 빌드가 만들었어도 스트립이 진짜 실패했으면 올리지 않는다."""
    aab = _make_aab(tmp_path / "unstripped.aab", stripped=False)
    result = _run_android_lane(tmp_path, exit_code=1, produces=aab)

    assert result.returncode != 0
    assert "UPLOAD_REACHED" not in result.stdout
    assert "스트립되지 않았다" in result.stderr


def test_aab_step_removes_the_previous_bundle_before_building(distribute):
    """self-hosted 러너는 작업 디렉터리가 남는다 — 같은 재사용 사고가 Actions 에도 있다."""
    aab = next(
        step
        for step in _steps(distribute, "android")
        if "flutter build appbundle" in step.get("run", "")
    )
    run = aab["run"]
    removal = run.index(f"rm -f {AAB_IN_BUNDLE}")

    assert removal < run.index("flutter build appbundle"), "빌드 뒤에 지우면 의미가 없다"


def test_workflow_and_manual_lane_share_the_aab_check(distribute):
    """두 경로가 다른 검사를 쓰면 한쪽만 조용히 느슨해진다."""
    aab = next(
        step
        for step in _steps(distribute, "android")
        if "flutter build appbundle" in step.get("run", "")
    )

    assert "tool/verify_appbundle.py" in aab["run"]
    assert "tool/verify_appbundle.py" in ANDROID_FASTFILE.read_text(encoding="utf-8")
