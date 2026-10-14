"""스토어 메타데이터·업로드 워크플로 (티켓 35).

fastlane 이 올리는 것은 **레포의 파일 그대로**다 — 글자 수 하나가 한도를 넘으면
업로드가 거기서 멈추고, URL 한 줄이 틀리면 심사에서 돌아온다. analyze·위젯
테스트는 `.txt` 를 보지 않으므로 여기서 직접 읽어서 지킨다
(티켓 34 의 `tests/test_app_deploy_workflow.py` 와 같은 자리).
"""

import re
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


def test_the_category_is_a_word_puzzle_game():
    assert _read(IOS_METADATA / "primary_category.txt") == "GAMES"
    assert _read(IOS_METADATA / "primary_first_sub_category.txt") == "GAMES_WORD"
    assert _read(IOS_METADATA / "primary_second_sub_category.txt") == "GAMES_PUZZLE"


# --- 심사 노트 -------------------------------------------------------------

REVIEW_INFORMATION = IOS_METADATA / "review_information"
NOTES = REVIEW_INFORMATION / "notes.txt"

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


def test_the_metadata_workflow_refuses_to_upload_without_screenshots():
    """iPad 스크린샷 없이 제출하면 심사가 막힌다 — 비어 있으면 먼저 멈춘다."""
    text = (WORKFLOWS / "appstore-metadata.yml").read_text(encoding="utf-8")

    assert "fastlane/screenshots" in text
    assert "scripts/store_screenshots.sh" in text


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

    assert "fastlane/metadata/review_information/notes.txt" in text
    assert "fastlane/app_privacy_details.json" in text
