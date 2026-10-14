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


# --- D-17-1 REPEAT · D-17-3: 폐기 이전 세대의 응답 -----------------------------


@pytest.fixture(scope="module")
def stale_generation() -> dict:
    return run_scenario("stale_state_generation.mjs", "ko")


def test_a_submit_response_from_before_a_round_trip_is_discarded(stale_generation):
    """ko→en→ko 로 돌아오면 퍼즐 ID 는 같아진다 — 그래도 전환 전 제출 응답은 버린다.

    돌아온 보드는 서버 `attempts` 로 이미 그 시도를 복원해뒀다. 늦게 온 응답을
    다시 반영하면 같은 행이 두 번 보이고 공유 그리드도 중복된다.
    """
    after = stale_generation["round_trip_submit"]

    assert after["puzzleId"] == 1
    assert after["attempts"] == [{"guess": "사자", "feedback": [True, False]}]
    assert after["boardRows"] == 1
    assert after["attemptsLeft"] == 4


def test_a_stats_response_from_before_a_switch_does_not_revert_the_language(stale_generation):
    """늦게 온 `/me/stats` 의 `puzzle_language` 가 지금 고른 언어를 되돌리면 안 된다."""
    after = stale_generation["stale_stats"]

    assert after["puzzleId"] == 2
    assert after["puzzleLanguage"] == "en"
    assert after["chips"] == {"ko": "false", "en": "true"}
    # 선택이 되돌아가면 normalizeGuess 가 en 대문자 처리를 잃는다.
    assert after["normalizedLatin"] == "AB"
    # 되돌아간 선택은 다음 한국어 클릭을 "이미 그 언어"로 보고 무시해 전환을 막는다.
    assert after["koClickRequests"] > 0


def test_a_stale_stats_response_still_updates_the_guest_scoped_summary(stale_generation):
    """연속 기록은 퍼즐이 아니라 게스트의 것이다 — 전환했다고 비워두지 않는다."""
    expected = UI_STRINGS["ko"]["streak_summary"].format(current=3, max=7, solved=12)

    assert stale_generation["stale_stats"]["streak"] == expected


def test_a_stats_response_without_a_switch_still_selects_the_chip(stale_generation):
    """대조군 — 전환이 없으면 stats 의 선호 언어가 평소처럼 칩에 반영된다."""
    after = stale_generation["fresh_stats"]

    assert after["puzzleLanguage"] == "ko"
    assert after["chips"] == {"ko": "true", "en": "false"}


def test_leaderboard_and_today_stats_from_before_a_switch_are_discarded(stale_generation):
    """전환 전에 보낸 순위·오늘 통계 조회는 다른 언어 퍼즐의 것이다."""
    after = stale_generation["stale_leaderboard"]

    assert after["entryRows"] == 0
    assert after["myRank"] == UI_STRINGS["ko"]["my_rank_unsolved"]
    assert after["statsText"] == UI_STRINGS["ko"]["stats_empty"]


def test_a_today_response_from_an_earlier_switch_does_not_replace_the_newer_puzzle(
    stale_generation,
):
    """칩을 연달아 누르면 재조회가 겹친다 — 먼저 보낸 응답이 늦게 와도 덮어쓰지 않는다."""
    after = stale_generation["late_today"]

    assert after["puzzleId"] == 1
    assert after["puzzleLanguage"] == "ko"
    assert after["chips"] == {"ko": "true", "en": "false"}


def test_a_language_patch_that_resolves_after_a_refetch_is_dropped(stale_generation):
    """PATCH /me 가 도는 사이 409 재조회가 화면을 갈아끼웠으면 그 전환은 접는다."""
    after = stale_generation["late_patch"]

    assert after["puzzleLanguage"] == "ko"
    assert after["chips"] == {"ko": "true", "en": "false"}
    # 접지 않으면 재조회가 한 번 더 돌아 사용자가 보던 퍼즐이 또 바뀐다.
    assert after["refetchesAfterReload"] == 0


# --- D-17-4: 본문 수신 대기 중의 상태 폐기 -------------------------------------


@pytest.fixture(scope="module")
def stale_body() -> dict:
    return run_scenario("stale_response_body.mjs", "ko")


def test_a_today_body_that_arrives_after_a_switch_does_not_replace_the_new_puzzle(stale_body):
    """`await fetch()` 는 헤더까지다 — 본문을 읽는 사이에 전환됐으면 그 본문은 버린다."""
    after = stale_body["late_today_body"]

    assert after["puzzleId"] == 2
    assert after["puzzleLanguage"] == "en"
    assert after["chips"] == {"ko": "false", "en": "true"}


def test_the_same_holds_in_the_other_direction(stale_body):
    """en→ko 로 돌아오는 순서에서도 늦게 온 en 본문이 ko 화면을 덮지 않는다."""
    after = stale_body["late_today_body_reverse"]

    assert after["puzzleId"] == 1
    assert after["puzzleLanguage"] == "ko"
    assert after["chips"] == {"ko": "true", "en": "false"}


def test_a_leaderboard_body_that_arrives_after_a_switch_is_discarded(stale_body):
    """전 언어 순위가 새 언어 화면에 다시 뜨면 안 된다."""
    after = stale_body["late_leaderboard_body"]

    assert after["entryRows"] == 0
    assert after["myRank"] == UI_STRINGS["ko"]["my_rank_unsolved"]


def test_a_today_stats_body_that_arrives_after_a_switch_is_discarded(stale_body):
    """전 언어의 시도 분포도 마찬가지다."""
    assert stale_body["late_today_stats_body"]["statsText"] == UI_STRINGS["ko"]["stats_empty"]


def test_a_language_patch_body_that_arrives_after_a_refetch_is_dropped(stale_body):
    """PATCH 본문을 읽는 사이 409 재조회가 화면을 갈아끼웠으면 그 전환은 접는다."""
    after = stale_body["late_patch_body"]

    assert after["puzzleLanguage"] == "ko"
    assert after["chips"] == {"ko": "true", "en": "false"}
    # 접지 않으면 재조회가 한 번 더 돌아 사용자가 보던 퍼즐이 또 바뀐다.
    assert after["refetchesAfterReload"] == 0


def test_a_stats_body_that_arrives_after_a_switch_keeps_the_guest_scoped_summary(stale_body):
    """칩은 지난 선호를 따라가지 않지만, 게스트의 연속 기록은 그대로 갱신한다."""
    after = stale_body["late_stats_body"]
    expected = UI_STRINGS["ko"]["streak_summary"].format(current=3, max=7, solved=12)

    assert after["chips"] == {"ko": "false", "en": "true"}
    assert after["streak"] == expected


def test_a_late_body_without_a_switch_is_still_applied(stale_body):
    """대조군 — 전환이 없으면 늦게 온 본문도 평소처럼 반영된다."""
    after = stale_body["fresh_leaderboard_body"]

    assert after["entryRows"] == 1
    assert after["myRank"] != UI_STRINGS["ko"]["my_rank_unsolved"]


def test_a_submit_body_that_arrives_after_a_switch_does_not_touch_the_new_board(stale_body):
    """제출까지 여섯 요청 전부 같은 경계를 쓴다 — 늦게 온 제출 본문도 버린다."""
    after = stale_body["late_submit_body"]

    assert after["puzzleId"] == 2
    assert after["attempts"] == []
    assert after["boardRows"] == 0
    assert after["attemptsLeft"] == 5


def test_a_200_with_an_unparsable_body_falls_back_to_the_load_failure_message(stale_body):
    """본문을 한 곳에서 읽으니 파싱 실패도 던지지 않고 안내로 눕는다."""
    assert stale_body["unparsable_body"]["message"] == UI_STRINGS["ko"]["puzzle_load_failed"]


# --- D-17-5: 겹친 언어 쓰기의 적용 순서 ---------------------------------------


@pytest.fixture(scope="module")
def concurrent_language_writes() -> dict:
    return run_scenario("concurrent_language_writes.mjs", "ko")


def test_the_last_language_choice_wins_on_the_server_even_if_an_earlier_write_commits_last(
    concurrent_language_writes,
):
    """겹친 PATCH 가 B→C→A 순으로 적용돼도 마지막 선택이 서버 선호로 남는다.

    응답을 버리는 것(세대)은 화면만 지킨다 — 이미 보낸 쓰기는 서버에 커밋되므로,
    쓰기 자체를 한 번에 하나로 줄여 "클릭 순서 = 커밋 순서"를 만들어야 한다.
    """
    after = concurrent_language_writes["duplicate_clicks_then_switch"]

    assert after["puzzleLanguage"] == "ko"
    assert after["puzzleId"] == 1
    assert after["chips"] == {"ko": "true", "en": "false"}
    # 화면과 서버가 갈리지 않는다 — 새 탭·새로고침도 같은 언어를 연다.
    assert after["serverPreference"] == "ko"
    assert after["commits"][-1] == "ko"


def test_the_next_submit_after_concurrent_language_writes_is_not_rejected(
    concurrent_language_writes,
):
    """갈라져 있으면 다음 제출이 409 로 마지막 선택을 취소한다."""
    submit = concurrent_language_writes["duplicate_clicks_then_switch"]["submit"]

    assert submit["puzzleLanguage"] == "ko"
    assert submit["puzzleId"] == 1
    assert submit["message"] != UI_STRINGS["ko"]["puzzle_changed"]


def test_a_click_while_a_language_write_is_in_flight_is_not_swallowed(
    concurrent_language_writes,
):
    """칩은 응답이 와야 바뀐다 — 쓰기 중의 클릭을 "이미 그 언어"로 보면 입력이 사라진다."""
    after = concurrent_language_writes["switch_during_write"]

    assert after["puzzleLanguage"] == "ko"
    assert after["serverPreference"] == "ko"
    assert after["commits"] == ["en", "ko"]


def test_repeated_clicks_on_the_same_chip_write_once(concurrent_language_writes):
    after = concurrent_language_writes["duplicate_clicks_only"]

    assert after["commits"] == ["en"]
    assert after["puzzleLanguage"] == "en"
    assert after["serverPreference"] == "en"


def test_a_plain_language_switch_still_writes_and_renders_once(concurrent_language_writes):
    """대조군 — 겹치지 않는 전환은 평소대로 한 번 쓰고 새 퍼즐을 연다."""
    after = concurrent_language_writes["plain_switch"]

    assert after["commits"] == ["en"]
    assert after["puzzleId"] == 2
    assert after["chips"] == {"ko": "false", "en": "true"}
    assert after["submit"]["message"] != UI_STRINGS["en"]["puzzle_changed"]
