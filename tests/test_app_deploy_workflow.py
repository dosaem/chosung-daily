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
import subprocess
import tempfile
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
    assert "not stripped" in run, "libapp.so 스트립 검증이 없다"


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
    "GAMEPLAY_CONTENT": "시도 기록",
    "PURCHASE_HISTORY": "구독 식별자",
    "DEVICE_ID": "광고 ID",
    "ADVERTISING_DATA": "광고 ID(광고 요청·측정)",
    "PRODUCT_INTERACTION": "앱 사용 이벤트(Firebase Analytics)",
    "CRASH_DATA": "접속·오류 기록(Sentry)",
    "PERFORMANCE_DATA": "접속·오류 기록(Sentry)",
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

    for category in ("DEVICE_ID", "ADVERTISING_DATA"):
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
