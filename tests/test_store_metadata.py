"""스토어 메타데이터·업로드 워크플로 (티켓 35).

fastlane 이 올리는 것은 **레포의 파일 그대로**다 — 글자 수 하나가 한도를 넘으면
업로드가 거기서 멈추고, URL 한 줄이 틀리면 심사에서 돌아온다. analyze·위젯
테스트는 `.txt` 를 보지 않으므로 여기서 직접 읽어서 지킨다
(티켓 34 의 `tests/test_app_deploy_workflow.py` 와 같은 자리).
"""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MOBILE = REPO_ROOT / "mobile"
IOS_METADATA = MOBILE / "ios" / "fastlane" / "metadata"
PLAY_METADATA = MOBILE / "android" / "fastlane" / "metadata" / "android"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

BUNDLE_ID = "com.dosaem.chosung"
PRIVACY_URL = "https://chosung.dosaem.com/privacy"
TERMS_URL = "https://chosung.dosaem.com/terms"

# YAML 1.1 에서 `on` 은 불린이라 PyYAML 이 트리거 키를 True 로 읽는다.
ON = True

# 스토어가 자르는 한도. 넘으면 업로드가 실패한다.
IOS_LIMITS = {
    "name.txt": 30,
    "subtitle.txt": 30,
    "keywords.txt": 100,
    "promotional_text.txt": 170,
    "description.txt": 4000,
    "release_notes.txt": 4000,
}
PLAY_LIMITS = {
    "title.txt": 30,
    "short_description.txt": 80,
    "full_description.txt": 4000,
}

IOS_LOCALES = ("ko", "en-US")
PLAY_LOCALES = ("ko-KR", "en-US")

# 미정 4: ASC 이름이 겹치면 "Hidden Vowels: Daily Word" 로 간다(docs/RELEASE.md "35.").
APP_NAMES = {"ko": "오늘의 초성", "en-US": "Hidden Vowels"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("locale", IOS_LOCALES)
@pytest.mark.parametrize("name", sorted(IOS_LIMITS))
def test_ios_metadata_files_exist_and_fit_the_store_limit(locale, name):
    path = IOS_METADATA / locale / name
    assert path.is_file(), f"{path} 가 없다 — deliver 가 그 칸을 비운 채 올린다"

    text = _read(path)
    assert text, f"{path} 가 비었다"
    assert len(text) <= IOS_LIMITS[name], f"{path}: {len(text)}자 > {IOS_LIMITS[name]}자"


@pytest.mark.parametrize("locale", PLAY_LOCALES)
@pytest.mark.parametrize("name", sorted(PLAY_LIMITS))
def test_play_metadata_files_exist_and_fit_the_store_limit(locale, name):
    path = PLAY_METADATA / locale / name
    assert path.is_file(), f"{path} 가 없다 — supply 가 올릴 게 없다"

    text = _read(path)
    assert text
    assert len(text) <= PLAY_LIMITS[name], f"{path}: {len(text)}자 > {PLAY_LIMITS[name]}자"


@pytest.mark.parametrize(
    ("ios_locale", "play_locale"), list(zip(IOS_LOCALES, PLAY_LOCALES, strict=True))
)
def test_the_app_name_is_the_same_on_both_stores(ios_locale, play_locale):
    assert _read(IOS_METADATA / ios_locale / "name.txt") == APP_NAMES[ios_locale]
    assert _read(PLAY_METADATA / play_locale / "title.txt") == APP_NAMES[ios_locale]


@pytest.mark.parametrize("locale", IOS_LOCALES)
def test_privacy_and_support_urls_point_at_the_legal_pages(locale):
    """티켓 35: privacy/support URL 은 `/privacy`·`/terms` 다."""
    assert _read(IOS_METADATA / locale / "privacy_url.txt") == PRIVACY_URL
    assert _read(IOS_METADATA / locale / "support_url.txt") == TERMS_URL


@pytest.mark.parametrize("locale", IOS_LOCALES + PLAY_LOCALES)
def test_descriptions_link_the_legal_pages(locale):
    """스토어 설명에서도 방침·약관에 닿아야 한다(Apple 3.1.2(a))."""
    directory = IOS_METADATA / locale if locale in IOS_LOCALES else PLAY_METADATA / locale
    name = "description.txt" if locale in IOS_LOCALES else "full_description.txt"

    text = _read(directory / name)
    assert PRIVACY_URL in text
    assert TERMS_URL in text


# 영문 설명이 보드 예시로 쓰는 문장. 칸 수와 단어 길이를 여기서만 쓴다.
ENGLISH_BOARD_EXAMPLE = "P _ R P L _"

_WORD_LENGTH_WORDS = {5: "five", 6: "six", 7: "seven"}


def test_the_english_description_counts_the_example_board_correctly():
    """D-35-9: `P _ R P L _` 는 6칸인데 본문이 "five-letter word" 라고 적었다.

    칸 수를 손으로 센 숫자가 아니라 **예시 문자열에서** 뽑아 대조한다 — 예시가
    바뀌면 숫자도 같이 바뀌어야 한다. 실제 장면의 가림 타일 수와도 맞춘다
    (`store_screenshot_scenes.dart` 의 `_enMask`).
    """
    slots = len(ENGLISH_BOARD_EXAMPLE.split())
    expected = f"({ENGLISH_BOARD_EXAMPLE} for a {_WORD_LENGTH_WORDS[slots]}-letter word)"

    for directory, name in (
        (IOS_METADATA / "en-US", "description.txt"),
        (PLAY_METADATA / "en-US", "full_description.txt"),
    ):
        text = _read(directory / name)
        assert ENGLISH_BOARD_EXAMPLE in text, f"{name}: 예시 보드가 없다"
        assert expected in text, f"{name}: {slots}칸을 다른 글자 수로 설명한다"

    scenes = (
        MOBILE / "integration_test" / "store_screenshot_scenes.dart"
    ).read_text(encoding="utf-8")
    mask = scenes.split("const _enMask = [", 1)[1].split("];", 1)[0]
    assert mask.count("MaskTile(") == slots, "장면의 가림 타일 수와 설명의 칸 수가 갈렸다"


def test_the_category_is_a_word_puzzle_game():
    assert _read(IOS_METADATA / "primary_category.txt") == "GAMES"
    assert _read(IOS_METADATA / "primary_first_sub_category.txt") == "GAMES_WORD"
    assert _read(IOS_METADATA / "primary_second_sub_category.txt") == "GAMES_PUZZLE"


# --- 심사 노트 -------------------------------------------------------------

REVIEW_INFORMATION = IOS_METADATA / "review_information"
# `notes.txt` 가 아니라 `notes.template.txt` 다 — fastlane deliver 는
# `review_information/` 의 예약 이름(`notes.txt` 등)을 보면 심사 상세를 PATCH 해서
# 사람이 콘솔에 넣은 Sandbox 계정을 덮는다(최종 리뷰 D-35-7,
# `tests/test_asc_submit_workflow.py`). 올리는 쪽은 `asc-submit.yml` 의 Python
# 스텝 하나로 모으고, 그 스텝이 콘솔 값과 플레이스홀더를 구분한다.
NOTES = REVIEW_INFORMATION / "notes.template.txt"

# ASC `appStoreReviewDetails.notes` 한도.
NOTES_LIMIT = 4000


def test_review_notes_fit_the_asc_limit():
    assert len(_read(NOTES)) <= NOTES_LIMIT


@pytest.mark.parametrize(
    "requirement",
    [
        "No account registration or login is required",  # 심사자가 바로 들어온다
        "SUBSCRIPTION TEST",  # 구독 테스트 방법
        "Sandbox tester",  # Sandbox 테스터 안내
        "ACCOUNT DELETION PATH",  # 계정 삭제 경로 (5.1.1(v))
        "https://chosung.dosaem.com/account/delete",
        "EXTERNAL SERVICES",
        "REGIONAL DIFFERENCES",
    ],
)
def test_review_notes_cover_what_review_asks_for(requirement):
    assert requirement in NOTES.read_text(encoding="utf-8")


def test_review_credentials_are_placeholders_not_real_values():
    """계정 정보는 사람이 ASC 콘솔에 넣는다 — 레포에는 자리만 둔다."""
    notes = NOTES.read_text(encoding="utf-8")

    assert "<SANDBOX_TESTER_EMAIL>" in notes
    assert "<SANDBOX_TESTER_PASSWORD>" in notes
    # 자격 증명 파일을 두면 deliver 가 그 값으로 ASC 를 덮어쓴다.
    assert not (REVIEW_INFORMATION / "demo_user.txt").exists()
    assert not (REVIEW_INFORMATION / "demo_password.txt").exists()
    # 계정 없이 플레이할 수 있는 앱이다.
    assert _read(REVIEW_INFORMATION / "demo_required.txt") == "false"


# --- 업로드 워크플로 -------------------------------------------------------


def _workflow(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["appstore-metadata.yml", "asc-submit.yml"])
def test_upload_workflows_are_manual_only(name):
    """자동 푸시로 스토어 메타데이터·심사 제출이 나가면 안 된다 — 수동 디스패치뿐이다."""
    workflow = _workflow(name)

    assert set(workflow[ON]) == {"workflow_dispatch"}


@pytest.mark.parametrize("name", ["appstore-metadata.yml", "asc-submit.yml"])
def test_upload_workflows_run_in_the_flutter_ios_directory(name):
    """Flutter 루트가 `mobile/` 이라 fastlane 경로도 그 아래다."""
    workflow = _workflow(name)
    job = next(iter(workflow["jobs"].values()))

    assert job["defaults"]["run"]["working-directory"] == "mobile/ios"
    assert job["runs-on"] == "self-hosted"


@pytest.mark.parametrize("name", ["appstore-metadata.yml", "asc-submit.yml"])
def test_upload_workflows_use_this_apps_bundle_id(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")

    assert BUNDLE_ID in text
    assert "buildurpalace" not in text, "BASELINE 식별자가 남아 있다"


@pytest.mark.parametrize("name", ["appstore-metadata.yml", "asc-submit.yml"])
def test_upload_workflows_delete_the_api_key_afterwards(name):
    """키 파일을 러너(사용자 맥)에 남기지 않는다 — 실패해도 지운다."""
    workflow = _workflow(name)
    steps = next(iter(workflow["jobs"].values()))["steps"]

    cleanup = [step for step in steps if "rm -f fastlane/api_key.json" in step.get("run", "")]
    assert cleanup, f"{name}: 키 삭제 스텝이 없다"
    assert all(step.get("if") == "always()" for step in cleanup)


VERIFIER = MOBILE / "tool" / "verify_store_screenshots.py"

IOS_SETS = {("ko", "iphone69"), ("ko", "ipad13"), ("en-US", "iphone69"), ("en-US", "ipad13")}


def _step_script(workflow: str, step_name: str) -> str:
    steps = next(iter(_workflow(workflow)["jobs"].values()))["steps"]
    matching = [step for step in steps if step.get("name") == step_name]
    assert matching, f"{workflow}: '{step_name}' 스텝이 없다"
    return matching[0]["run"]


# 실제 파일 이름의 장면 조각(`StoreScene.slug`). 마지막 장이 플랫폼으로 갈리는
# 온보딩이라 검사가 그 이름을 본다.
SCENE_SLUGS = ("01_home", "02_result", "03_leaderboard", "04_records", "06_language")


def _write_set(directory: Path, prefix: str, count: int, body: str = "x") -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for index in range(count):
        slug = SCENE_SLUGS[index] if index < len(SCENE_SLUGS) else f"{index:02d}_extra"
        path = directory / f"{prefix}_ko_{slug}.png"
        path.write_text(f"{body}{slug}")
        written.append(path)
    return written


def _fake_mobile(tmp_path: Path, *, ios=None, play_phone=None, play_tablet=None) -> Path:
    """`verify_store_screenshots.py` 가 보는 폴더 모양만 만든다."""
    root = tmp_path / "mobile"
    for locale, prefix in IOS_SETS:
        count = EXPECTED_SHOTS if ios is None else ios.get((locale, prefix), EXPECTED_SHOTS)
        _write_set(
            root / "ios" / "fastlane" / "screenshots" / locale,
            prefix,
            count,
            body=f"{locale}-{prefix}-",
        )
    for locale in PLAY_LOCALES:
        images = root / "android" / "fastlane" / "metadata" / "android" / locale / "images"
        _write_set(
            images / "phoneScreenshots",
            "android",
            EXPECTED_SHOTS if play_phone is None else play_phone.get(locale, EXPECTED_SHOTS),
            body=f"play-phone-{locale}-",
        )
        _write_set(
            images / "tenInchScreenshots",
            "androidtablet",
            EXPECTED_SHOTS if play_tablet is None else play_tablet.get(locale, EXPECTED_SHOTS),
            body=f"play-tablet-{locale}-",
        )
    return root


def _verify(root: Path, target: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(VERIFIER), target, str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


# 한 세트 = OVERRIDES §8 의 5장.
EXPECTED_SHOTS = 5


def test_the_upload_steps_verify_the_screenshot_sets_before_uploading():
    """글자 수·경로만 보던 검사는 "1장만 찍히고 drive 가 죽은" 상태를 통과시켰다
    (최종 리뷰 D-35-1). 두 업로드 경로가 모두 검사를 **먼저** 돌리는지 본다.
    """
    assert "verify_store_screenshots.py ios" in _step_script(
        "appstore-metadata.yml", "Check screenshots exist"
    )

    fastfile = (MOBILE / "android" / "fastlane" / "Fastfile").read_text(encoding="utf-8")
    release = fastfile.split("lane :release", 1)[1].split("upload_to_play_store", 1)[0]
    assert "verify_store_screenshots.py play" in release, "Play 업로드 전 검사가 없다"


def test_the_verifier_passes_on_complete_sets(tmp_path):
    for target in ("ios", "play", "both"):
        result = _verify(_fake_mobile(tmp_path / target), target)
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("label", "kwargs", "target"),
    [
        ("iPad 세트가 중간에 깨졌다", {"ios": {("ko", "ipad13"): 1}}, "ios"),
        ("6.9\" 세트가 없다", {"ios": {("en-US", "iphone69"): 0}}, "ios"),
        ("세트가 누적됐다", {"ios": {("ko", "iphone69"): 10}}, "ios"),
        ("Play 폰 세트가 비었다", {"play_phone": {"ko-KR": 0}}, "play"),
        ("Play 폰 세트가 누적됐다", {"play_phone": {"en-US": 10}}, "play"),
        ("Play 태블릿 세트가 반쪽이다", {"play_tablet": {"ko-KR": 3}}, "play"),
    ],
)
def test_the_verifier_refuses_a_broken_set(label, kwargs, target, tmp_path):
    result = _verify(_fake_mobile(tmp_path, **kwargs), target)

    assert result.returncode == 1, f"{label}: 그대로 올리려 했다\n{result.stdout}"
    assert "::error::" in result.stdout


def _ios_phone_scenes(root: Path, locale: str = "ko") -> list[Path]:
    directory = root / "ios" / "fastlane" / "screenshots" / locale
    return sorted(directory.glob("iphone69_*.png"))


def _play_phone_dir(root: Path, locale: str = "ko-KR") -> Path:
    images = root / "android" / "fastlane" / "metadata" / "android" / locale / "images"
    phone_dir = images / "phoneScreenshots"
    for path in phone_dir.glob("*.png"):
        path.unlink()
    return phone_dir


def test_the_verifier_refuses_a_play_phone_set_copied_from_the_iphone_captures(tmp_path):
    """D-35-5: Android 에뮬레이터가 없던 날 iPhone 캡처를 Play 폰 세트로 복사하면
    iOS 에만 있는 ATT 안내 장이 들어간 그림이 Play 에 올라간다 — 올리기 전에 막는다.
    """
    root = _fake_mobile(tmp_path)
    phone_dir = _play_phone_dir(root)
    for source in _ios_phone_scenes(root):
        (phone_dir / source.name).write_bytes(source.read_bytes())

    result = _verify(root, "play")

    assert result.returncode == 1, result.stdout
    assert "iOS 온보딩 캡처" in result.stdout


def test_the_verifier_allows_the_fallback_set_shot_in_the_android_layout(tmp_path):
    """AVD 없이 iPhone 시뮬레이터에서 **Android 구성**으로 찍은 세트는 통과한다.

    온보딩 말고 네 장면(홈·결과·순위·내 기록)은 두 플랫폼이 같은 그림이라 iOS 세트와
    바이트가 같다 — 그걸 복사본으로 보면 정상 경로가 막힌다. 갈리는 장면은 온보딩
    하나다.
    """
    root = _fake_mobile(tmp_path)
    phone_dir = _play_phone_dir(root)
    for source in _ios_phone_scenes(root):
        body = source.read_bytes()
        if "06_language" in source.name:
            body = body + b"-android-onboarding"
        (phone_dir / source.name.replace("iphone69_", "androidui_")).write_bytes(body)

    result = _verify(root, "play")

    assert result.returncode == 0, result.stdout + result.stderr


def _ios_tablet_scenes(root: Path, locale: str = "ko") -> list[Path]:
    directory = root / "ios" / "fastlane" / "screenshots" / locale
    return sorted(directory.glob("ipad13_*.png"))


def _play_tablet_dir(root: Path, locale: str = "ko-KR") -> Path:
    images = root / "android" / "fastlane" / "metadata" / "android" / locale / "images"
    tablet_dir = images / "tenInchScreenshots"
    for path in tablet_dir.glob("*.png"):
        path.unlink()
    return tablet_dir


def test_the_verifier_refuses_a_play_tablet_set_copied_from_the_ipad_captures(tmp_path):
    """D-35-8: 태블릿도 온보딩 장이 플랫폼으로 갈린다 — `onboardingPages` 는 화면
    폭을 보지 않고 iOS 에만 ATT 안내 장을 붙인다. iPad 캡처를 그대로 Play
    `tenInchScreenshots` 로 복사하면 폰과 똑같이 iOS 전용 장이 올라간다.
    """
    root = _fake_mobile(tmp_path)
    tablet_dir = _play_tablet_dir(root)
    for source in _ios_tablet_scenes(root):
        (tablet_dir / source.name).write_bytes(source.read_bytes())

    result = _verify(root, "play")

    assert result.returncode == 1, result.stdout
    assert "iOS 온보딩 캡처" in result.stdout


def test_the_verifier_allows_a_tablet_set_shot_in_the_android_layout(tmp_path):
    """iPad 시뮬레이터에서 **Android 구성**으로 찍은 태블릿 세트는 통과한다.

    폰 대체 세트와 같은 선이다 — 갈리는 장면은 온보딩 하나고, 나머지 네 장면은
    iPad 캡처와 바이트가 같은 것이 정상이다.
    """
    root = _fake_mobile(tmp_path)
    tablet_dir = _play_tablet_dir(root)
    for source in _ios_tablet_scenes(root):
        body = source.read_bytes()
        if "06_language" in source.name:
            body = body + b"-android-onboarding"
        (tablet_dir / source.name.replace("ipad13_", "androidtablet_")).write_bytes(body)

    result = _verify(root, "play")

    assert result.returncode == 0, result.stdout + result.stderr


def test_the_submit_workflow_keeps_the_review_contact_out_of_the_repo():
    """BASELINE 은 이름·전화번호를 워크플로에 적어 뒀다 — secret 으로 옮겼다."""
    text = (WORKFLOWS / "asc-submit.yml").read_text(encoding="utf-8")

    for secret in (
        "ASC_REVIEW_CONTACT_FIRST_NAME",
        "ASC_REVIEW_CONTACT_LAST_NAME",
        "ASC_REVIEW_CONTACT_PHONE",
        "ASC_REVIEW_CONTACT_EMAIL",
    ):
        assert f"secrets.{secret}" in text

    assert not re.search(r"\+\d{1,3}-\d", text), "전화번호가 워크플로에 박혀 있다"
    assert "@gmail.com" not in text


def test_the_submit_workflow_reads_the_review_notes_from_the_repo():
    text = (WORKFLOWS / "asc-submit.yml").read_text(encoding="utf-8")

    assert "fastlane/metadata/review_information/notes.template.txt" in text
    assert "fastlane/app_privacy_details.json" in text
