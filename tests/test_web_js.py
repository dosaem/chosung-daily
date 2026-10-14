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
    # 퍼즐이 없는 날은 오류가 아니라 "기다리면 된다" 라서, 티켓 18 부터 인라인 상태
    # 카드가 카운트다운과 같이 `no_puzzle_heading` 을 띄운다(OVERRIDES §7). 어느
    # 문구든 서버의 한국어 `message` 가 아니라 사전에서 와야 한다는 점은 같다.
    assert english_errors["today_no_puzzle"] == en["no_puzzle_heading"]


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


# --- 티켓 18: 상태 4종 전환 · 섹션 토글 · 공유 링크 --------------------------


@pytest.fixture(scope="module")
def web_states() -> dict:
    return run_scenario("web_states_and_sections.mjs", "ko")


def test_the_skeleton_gives_way_to_the_puzzle(web_states):
    """로딩은 스켈레톤이고(OVERRIDES §7) 퍼즐이 오면 걷힌다 — 둘이 같이 보이지 않는다."""
    before, after = web_states["before_load"], web_states["after_load"]

    assert (before["skeletonHidden"], before["puzzleHidden"], before["formHidden"]) == (
        False,
        True,
        True,
    )
    assert (after["skeletonHidden"], after["puzzleHidden"], after["formHidden"]) == (
        True,
        False,
        False,
    )


def test_a_request_that_cannot_leave_shows_the_banner_and_locks_the_input(web_states):
    """오프라인은 상단 배너 + 입력 비활성이다(OVERRIDES §7) — 보낼 수 없는 제출로
    기회를 잃지 않게 한다."""
    offline = web_states["unreachable"]

    assert offline["bannerHidden"] is False
    assert offline["inputDisabled"] is True
    assert offline["submitDisabled"] is True
    assert offline["stateHidden"] is False
    assert offline["stateText"] == UI_STRINGS["ko"]["network_error"]
    # 스켈레톤이 남아 있으면 "아직 불러오는 중" 으로 보인다.
    assert offline["skeletonHidden"] is True


def test_the_inline_retry_button_recovers_the_puzzle(web_states):
    """오류는 인라인 카드 + 재시도다 — 토스트로 숨기지 않는다(OVERRIDES §7)."""
    after = web_states["after_retry"]

    assert after["stateHidden"] is True
    assert after["puzzleHidden"] is False
    assert after["bannerHidden"] is True
    assert after["inputDisabled"] is False


def test_coming_back_online_reloads_without_asking(web_states):
    """`online` 이벤트가 오면 버튼을 누르게 만들지 않고 알아서 다시 받는다."""
    recovery = web_states["online_recovery"]

    assert recovery["offline"]["bannerHidden"] is False
    assert recovery["after"]["bannerHidden"] is True
    assert recovery["after"]["puzzleHidden"] is False
    assert recovery["after"]["inputDisabled"] is False


def test_navigator_online_alone_raises_the_banner_before_any_request(web_states):
    """비행기 모드로 들어온 방문자는 첫 요청이 실패하기 전에 이유를 안다."""
    at_load = web_states["offline_before_first_request"]

    assert at_load["bannerHidden"] is False
    assert at_load["inputDisabled"] is True
    # 아직 조회를 하지도 않았으니 오류 카드는 뜨지 않는다.
    assert at_load["stateHidden"] is True


def test_a_day_without_a_puzzle_counts_down_to_kst_midnight(web_states):
    """퍼즐 없음은 오류가 아니다 — "곧 새 퍼즐" + 카운트다운 + 재시도(US 7)."""
    state = web_states["no_puzzle"]

    assert state["stateText"] == UI_STRINGS["ko"]["no_puzzle_heading"]
    assert state["countdownHidden"] is False
    countdown = UI_STRINGS["ko"]["no_puzzle_countdown"]
    assert state["countdownText"] == countdown.format(time="23:30:00")
    # 풀 퍼즐이 없으니 제출 폼은 안 보인다.
    assert state["formHidden"] is True
    assert state["bannerHidden"] is True, "퍼즐이 없는 것과 오프라인은 다른 상태다"


def test_the_countdown_follows_the_clock(web_states):
    countdown = UI_STRINGS["ko"]["no_puzzle_countdown"]
    assert web_states["no_puzzle_next_tick"] == countdown.format(time="00:00:01")


def test_the_countdown_stops_when_the_puzzle_finally_arrives(web_states):
    """자정이 지나 퍼즐이 생기면 카운트다운이 멈추고 자리를 비켜야 한다."""
    after = web_states["no_puzzle_then_ready"]

    assert after["stateHidden"] is True
    assert after["countdownHidden"] is True
    assert after["puzzleHidden"] is False


def test_seconds_until_kst_midnight_is_computed_from_the_kst_day(web_states):
    """KST 는 서머타임이 없어서 고정 오프셋으로 계산해도 서버 자정과 어긋나지 않는다."""
    seconds = web_states["countdown_seconds"]

    assert seconds["just_after_midnight"] == 86399
    assert seconds["half_hour_in"] == 84600
    assert seconds["one_second_before_midnight"] == 1


def test_the_top_links_show_exactly_one_section(web_states):
    """탭 바 대신 상단 텍스트 링크로 같은 페이지 섹션을 바꾼다(SCREENS "웹" 절)."""
    assert web_states["sections_at_first"] == {
        "panels": {"today": True, "leaderboard": False, "records": False},
        "pressed": {"today": "true", "leaderboard": "false", "records": "false"},
    }
    assert web_states["sections_after_leaderboard"]["panels"] == {
        "today": False,
        "leaderboard": True,
        "records": False,
    }
    assert web_states["sections_after_records"]["panels"] == {
        "today": False,
        "leaderboard": False,
        "records": True,
    }
    assert web_states["sections_back_to_today"] == web_states["sections_at_first"]


def test_the_selected_section_is_announced_to_assistive_tech(web_states):
    """퍼즐 언어 칩과 같은 `aria-pressed` 로 선택을 알린다 — 색·굵기만으로 두지 않는다."""
    pressed = web_states["sections_after_records"]["pressed"]

    assert pressed == {"today": "false", "leaderboard": "false", "records": "true"}


def test_the_share_text_ends_with_the_web_link(web_states):
    """받은 사람이 바로 플레이할 수 있게 웹 링크가 붙는다(US 11)."""
    lines = web_states["share_text"].split("\n")

    assert lines[-1] == "https://chosung.dosaem.com/?utm_source=share"
    # 그리드와 링크가 한 줄에 붙지 않게 빈 줄을 둔다.
    assert lines[-2] == ""
    assert web_states["share_result"]["resultHidden"] is False


# --- 수정 라운드 1: 최종 리뷰 D-18-1 · D-18-2 --------------------------------


def test_a_first_visit_whose_guest_issue_cannot_leave_does_not_stay_on_the_skeleton(web_states):
    """D-18-1: 첫 방문의 게스트 발급이 못 나가도 오류 카드·배너·재시도가 떠야 한다.

    예전에는 `ensureToken()` 이 던져서 `init()` 이 거기서 끊겼다 — 뒤에 있던
    `bindEvents()`·`renderOffline()` 이 아예 안 돌아, 배너도 재시도 버튼도
    `online` 이벤트도 없는 스켈레톤이 영구 상태였다. 이 시나리오는 핸들러를
    손으로 붙이지 않고 `init()` 을 그대로 돌린다.
    """
    first = web_states["first_visit_offline"]

    assert first["threw"] is None, "init() 이 예외로 끊기면 안 된다"
    assert first["skeletonHidden"] is True
    assert first["stateHidden"] is False
    assert first["stateText"] == UI_STRINGS["ko"]["network_error"]
    assert first["bannerHidden"] is False
    assert first["retryHandlers"] == 1


def test_the_retry_button_issues_the_guest_token_the_first_visit_never_got(web_states):
    """D-18-1: 같은 재시도 버튼 하나로 **발급부터** 다시 시작한다."""
    after = web_states["first_visit_offline_after_retry"]

    assert after["token"] == "issued-token"
    assert after["stored"] == "issued-token"
    assert (after["puzzleHidden"], after["formHidden"], after["stateHidden"]) == (
        False,
        False,
        True,
    )
    assert after["bannerHidden"] is True
    assert after["inputDisabled"] is False
    # 발급이 실패해 못 받았던 통계도 같이 따라온다.
    assert after["streak"] == UI_STRINGS["ko"]["streak_summary"].format(
        current=0, max=0, solved=0
    )


def test_coming_back_online_also_retries_the_guest_issue(web_states):
    """D-18-1: 재시도 버튼을 누르게 만들지 않는다 — `online` 이벤트도 발급부터 잇는다."""
    after = web_states["first_visit_online_recovery"]

    assert after["token"] == "issued-token"
    assert after["puzzleHidden"] is False
    assert after["bannerHidden"] is True


def test_a_guest_issue_that_fails_with_5xx_also_offers_a_retry(web_states):
    """D-18-1: 요청이 나갔지만 서버가 실패한 경우도 같은 인라인 카드다(배너는 없다)."""
    after = web_states["first_visit_server_error"]

    assert after["stateHidden"] is False
    assert after["stateText"] == UI_STRINGS["ko"]["guest_issue_failed"]
    assert after["bannerHidden"] is True
    assert after["retryHandlers"] == 1


def test_a_submit_that_cannot_leave_shows_a_retry_not_just_a_locked_input(web_states):
    """D-18-2: 제출이 못 나가면 입력이 잠기는데, 재시도 경로가 없으면 갇힌다.

    `navigator.onLine` 이 계속 true 인 일시적 실패에서는 `online` 이벤트가 영영
    안 온다 — 숨어 있는 `#puzzle-state` 안의 재시도 버튼이 유일한 탈출구였다.
    """
    after = web_states["submit_unreachable"]

    assert after["online"] is True
    assert after["inputDisabled"] is True
    assert after["bannerHidden"] is False
    # 안내만 `#message` 에 남기지 않고, 재시도 버튼이 있는 카드를 띄운다.
    assert after["stateHidden"] is False
    assert after["stateText"] == UI_STRINGS["ko"]["network_error"]
    assert after["message"] == "", "같은 문장을 두 군데 띄우지 않는다"


def test_the_retry_after_a_failed_submit_resyncs_with_the_server(web_states):
    """D-18-2: fetch 가 죽은 사이에 제출이 닿았을 수도 있다 — 서버 이력으로 다시 맞춘다."""
    after = web_states["submit_unreachable_after_retry"]

    assert after["attempts"] == [{"guess": "사과", "feedback": [True, False]}]
    assert after["boardRows"] == 1
    assert after["attemptsLeft"] == 4
    assert (after["puzzleHidden"], after["formHidden"], after["stateHidden"]) == (
        False,
        False,
        True,
    )
    assert after["inputDisabled"] is False


# --- D-18-4: 토큰이 바뀌는 모든 경로에서 세션 게스트가 화면과 같다 -----------
#
# 세션 게스트는 OAuth 연결과 계정 삭제의 **대상**이다(app/api/oauth.py `sync_session`,
# app/web.py `account_delete`). 화면이 쓰는 토큰과 세션 게스트가 어긋나면 삭제 폼이
# 화면에 없는 계정을 지운다 — 그래서 경로마다 `/session/sync` 가 1회 나갔는지와 그
# Authorization 이 화면의 토큰(`/me/stats` 와 같은 값)인지를 함께 본다.


def test_a_first_visit_syncs_the_session_with_the_issued_guest(web_states):
    """경로 1 — 첫 발급. 대조군이다(이 경로는 D-18-1 수정에서도 동기화했다)."""
    sync = web_states["sync_on_first_visit"]

    assert sync["guestIssues"] == 1
    assert sync["count"] == 1
    assert sync["authorization"] == "Bearer issued-token"
    assert sync["matchesUi"] is True
    assert sync["beforePuzzleLoad"] is True


def test_starting_from_a_stored_token_also_syncs_the_session(web_states):
    """경로 2 — 저장된 토큰으로 시작(복원 후 새로고침·쿠키만 없는 재방문).

    이 경로가 동기화를 건너뛰면 API 는 저장된 게스트로 가는데 세션은 옛 게스트로
    남는다. 삭제 페이지는 세션의 옛 게스트로 폼을 발급하므로 CSRF 와 폼 대상 검사를
    둘 다 통과시킨 뒤 **화면에 없는 계정**을 지운다.
    """
    sync = web_states["sync_on_stored_token"]

    assert sync["guestIssues"] == 0, "저장된 토큰이 있으면 발급하지 않는다"
    assert sync["count"] == 1
    assert sync["authorization"] == "Bearer restored-guest-token"
    assert sync["matchesUi"] is True
    assert sync["beforePuzzleLoad"] is True


def test_a_backup_restore_syncs_the_session_with_the_restored_guest(web_states):
    """경로 3 — 백업 코드 복원. 저장소를 B 로 바꾸고 새로고침한 뒤의 로드가 B 로 맞춘다."""
    after = web_states["sync_after_backup_restore"]

    # 복원 전에는 A 로 맞춰져 있었다.
    assert after["beforeRestore"]["authorization"] == "Bearer guest-a-token"
    assert after["reloads"] == 1
    assert after["storedAfterRestore"] == "guest-b-token"
    # 새로고침 뒤의 로드는 B 로 동기화한다 — A 가 세션에 남지 않는다.
    assert after["count"] == 1
    assert after["authorization"] == "Bearer guest-b-token"
    assert after["matchesUi"] is True


def test_the_oauth_callback_syncs_the_session_with_the_new_token(web_states):
    """경로 4 — 로그인 복귀. 콜백이 준 계정 토큰으로 맞춘다(옛 게스트 세션이 남지 않는다)."""
    sync = web_states["sync_after_oauth_callback"]

    assert sync["count"] == 1
    assert sync["authorization"] == "Bearer linked-account-token"
    assert sync["matchesUi"] is True


def test_a_fresh_guest_after_account_deletion_syncs_the_emptied_session(web_states):
    """경로 5 — 삭제 후 `/?deleted=1`. 비워진 세션을 새로 발급한 게스트로 다시 채운다."""
    sync = web_states["sync_after_account_deletion"]

    assert sync["storedToken"] == "issued-token", "지워진 토큰을 버리고 새로 발급받는다"
    assert sync["count"] == 1
    assert sync["authorization"] == "Bearer issued-token"
    assert sync["matchesUi"] is True


def test_a_sync_that_cannot_leave_is_retried_when_the_connection_returns(web_states):
    """경로 2b — 저장된 토큰으로 오프라인 재방문. 동기화 요청이 못 나가는 경우다.

    저장된 토큰이 있으면 발급 요청 없이 곧장 동기화로 온다. 부르는 쪽은 응답을
    기다리지 않으니 거부를 그대로 두면 받아줄 사람 없는 rejection 이 되고(node 는
    거기서 죽는다), 세션은 옛 게스트로 남는다. 연결이 돌아오면 다시 보내야 한다.
    """
    after = web_states["sync_on_stored_token_offline"]

    assert after["offline"]["threw"] is None, "동기화 실패가 init() 을 깨지 않는다"
    assert after["offline"]["syncedToken"] is None, "못 심었으면 심었다고 기억하지 않는다"
    assert after["offline"]["bannerHidden"] is False

    # `online` 이벤트가 같은 토큰으로 동기화를 다시 보낸다 — 발급은 하지 않는다.
    assert after["guestIssues"] == 0
    assert after["count"] == 1
    assert after["authorization"] == "Bearer offline-revisit-token"
    assert after["matchesUi"] is True
    assert after["syncedToken"] == "offline-revisit-token"


# --- 티켓 38: 리더보드 이름·en 복수형 ----------------------------------------


@pytest.fixture(scope="module")
def names_ko() -> dict:
    return run_scenario("leaderboard_names.mjs", "ko")


@pytest.fixture(scope="module")
def names_en() -> dict:
    return run_scenario("leaderboard_names.mjs", "en")


def test_korean_ui_prefixes_the_anon_tag_with_the_korean_word(names_ko):
    """서버가 주는 건 `anon_tag: "a3f1"` 뿐이고 "게스트 #" 는 웹이 붙인다."""
    rows = names_ko["two_entries"]["rowTexts"]

    assert rows[0] == "#1게스트 #a3f1 · 1회 · 00:00:41"
    assert rows[1] == "#2게스트 #7b20 · 2회 · 00:03:41"
    assert names_ko["two_entries"]["myRank"] == "#2 · 2회 · 00:03:41"


def test_english_ui_prefixes_the_same_tag_with_guest(names_en):
    """같은 응답이 영어 UI 에서는 "Guest #a3f1" 이다 — 한글이 섞이지 않는다."""
    rows = names_en["two_entries"]["rowTexts"]

    assert rows[0] == "#1Guest #a3f1 · 1 try · 00:00:41"
    assert rows[1] == "#2Guest #7b20 · 2 tries · 00:03:41"
    assert "게스트" not in "".join(rows)


def test_english_attempts_are_singular_at_one_and_plural_above(names_en):
    """`1 tries` 가 보이던 자리. 행·내 순위 카드·분포 줄이 모두 같은 규칙이다."""
    assert " 1 try · " in names_en["two_entries"]["rowTexts"][0]
    assert " 2 tries · " in names_en["two_entries"]["rowTexts"][1]
    assert names_en["solo_entry"]["myRank"] == "#1 · 1 try · 00:00:41"
    assert names_en["two_entries"]["myRank"] == "#2 · 2 tries · 00:03:41"

    # 오늘의 시도 분포: 1회 칸만 단수.
    assert names_en["stats_rows"][:2] == ["1 try 50%", "2 tries 25%"]


def test_korean_attempts_read_the_same_at_one_and_above(names_ko):
    """ko 는 단수·복수가 같다 — en 복수형을 넣으면서 한국어가 바뀌지 않았는지 본다."""
    assert names_ko["stats_rows"][:2] == ["1회 50%", "2회 25%"]
    assert names_ko["solo_entry"]["myRank"] == "#1 · 1회 · 00:00:41"


def test_my_row_is_still_marked_by_a_class_not_by_a_different_name(names_ko):
    """is_me 표기는 기존대로 CSS 클래스다 — 이름 규칙은 남의 행과 같다."""
    assert names_ko["two_entries"]["isMeClasses"] == [
        "leaderboard-entry",
        "leaderboard-entry is-me",
    ]
