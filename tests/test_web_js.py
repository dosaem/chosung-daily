"""번들(`web/static/app.js`)을 node 로 실제 실행해서 보는 동작 테스트.

같은 파일을 보는 `tests/test_web.py` 는 번들 **문자열** 계약만 본다 — "함수가
있다"까지다. 최종 리뷰가 잡은 두 결함은 둘 다 *실행* 결과라서 그 방식으로는 안
잡혔다(review/impl-review-17.md D-17-1 · D-17-2):

- 제출 응답이 언어 전환 뒤에 도착하면 새 퍼즐 상태를 덮어쓴다
- 서버 오류의 한국어 `message` 가 영어 UI 에 그대로 나온다

Playwright 는 아직 안 들이기로 했으니(스펙 "미정 항목" 5) 브라우저 없이 번들만
`node --vm` 대역에서 돌린다. 대역은 `tests/js/harness.mjs`, 시나리오는
`tests/js/*.mjs`.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app.utils.ui_strings import UI_STRINGS

REPO_ROOT = Path(__file__).resolve().parent.parent
JS_DIR = REPO_ROOT / "tests" / "js"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node 가 없는 환경에서는 건너뛴다")


def run_scenario(script: str, language: str) -> dict:
    """시나리오 하나를 돌리고 stdout 의 JSON 을 돌려준다."""
    completed = subprocess.run(
        [NODE, str(JS_DIR / script), json.dumps(UI_STRINGS[language]), language],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        cwd=REPO_ROOT,
    )

    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


# --- D-17-1: 전환 이전 요청의 응답 -------------------------------------------


@pytest.fixture(scope="module")
def stale_submit() -> dict:
    return run_scenario("stale_submit_response.mjs", "ko")


def test_stale_wrong_guess_response_does_not_touch_the_new_puzzle(stale_submit):
    """폐기한 ko 제출의 오답 응답이 새 en 보드·남은 기회를 건드리지 않는다."""
    after = stale_submit["stale_wrong"]

    assert after["puzzleId"] == 2
    assert after["attempts"] == []
    assert after["boardRows"] == 0
    assert after["attemptsLeft"] == 5


def test_stale_correct_guess_response_does_not_finish_the_new_puzzle(stale_submit):
    """ko 정답 응답이 새 en 퍼즐을 끝내고 ko 정답을 결과로 띄우지 않는다."""
    after = stale_submit["stale_correct"]

    assert after["finalStatus"] is None
    assert after["guessFormHidden"] is False
    assert after["resultHidden"] is True
    assert after["attempts"] == []


def test_a_submit_without_a_switch_still_updates_the_board(stale_submit):
    """대조군 — 퍼즐이 그대로면 제출 응답은 평소처럼 반영된다."""
    after = stale_submit["fresh_wrong"]

    assert after["attempts"] == [{"guess": "사과", "feedback": [True, False]}]
    assert after["boardRows"] == 1
    assert after["attemptsLeft"] == 4


# --- D-17-2: 오류 문구의 언어 -------------------------------------------------


@pytest.fixture(scope="module")
def english_errors() -> dict:
    return run_scenario("error_message_language.mjs", "en")


def test_server_error_messages_are_shown_in_the_ui_language(english_errors):
    """서버 message 는 한국어 한 벌뿐이다 — 영어 UI 에는 영어 사전 문구가 나와야 한다."""
    en = UI_STRINGS["en"]

    assert english_errors["guess_validation"] == en["error_guess_length"].format(length=5)
    assert english_errors["guess_already_finished"] == en["error_already_finished"]
    assert english_errors["guess_rate_limited"] == en["error_rate_limited"]
    assert english_errors["guess_unauthorized"] == en["error_unauthorized"]
    assert english_errors["today_no_puzzle"] == en["error_no_puzzle_today"]


def test_an_unmapped_error_code_falls_back_to_the_generic_ui_string(english_errors):
    assert english_errors["guess_unknown"] == UI_STRINGS["en"]["generic_error"]


def test_no_error_message_leaks_korean_into_the_english_ui(english_errors):
    leaked = {
        name: text
        for name, text in english_errors.items()
        if any("가" <= char <= "힣" or "ㄱ" <= char <= "ㅎ" for char in text)
    }

    assert leaked == {}
