"""웹 메인 페이지 렌더 + 번들 계약.

브라우저는 안 띄운다(스펙 "미정 항목" 5: Playwright 보류). 그래서 서버가 책임지는
부분(문구 사전, 기기 언어, 섹션 마크업)은 실제 요청으로 검증하고, JS 쪽 계약은 번들
내용으로 회귀만 막는다. 번들을 **실행**해서 보는 동작은 `tests/test_web_js.py` 가
맡는다 — 문자열 어서션만으로는 응답 도착 순서나 오류 문구 같은 실행 결과를 못 잡는다
(review/impl-review-17.md D-17-1 · D-17-2). 레이아웃과 실제 왕복은 README "웹 수동
체크리스트".

티켓 14 의 삭제 신호 처리는 그보다 먼저 같은 이유로 실행 테스트를 붙였다(D-14-1) —
`tests/fixtures/js/deleted_state_harness.mjs` 를 쓰는 아래 절이 그것이다.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.utils.ui_strings import UI_STRINGS

BUNDLE = Path(__file__).resolve().parent.parent / "web" / "static" / "app.js"


def _bundle() -> str:
    return BUNDLE.read_text(encoding="utf-8")


def _embedded_strings(html: str) -> dict:
    """페이지에 인라인으로 심긴 UI 문자열 사전을 꺼낸다 (JS 가 읽는 그 JSON)."""
    match = re.search(
        r'<script id="ui-strings" type="application/json">(.*?)</script>', html, re.S
    )
    assert match, "페이지에 ui-strings JSON 이 없다"
    return json.loads(match.group(1))


def test_index_page_renders(client):
    res = client.get("/")

    assert res.status_code == 200
    assert "오늘의 초성".encode() in res.data


def test_static_js_is_served(client):
    res = client.get("/static/app.js")

    assert res.status_code == 200
    assert b"API_BASE" in res.data


# --- UI 문자열 ko/en + 기기 언어 감지 -----------------------------------------


def test_korean_device_gets_korean_ui(client):
    res = client.get("/", headers={"Accept-Language": "ko-KR,ko;q=0.9"})
    html = res.data.decode()

    assert 'lang="ko"' in html
    assert UI_STRINGS["ko"]["app_title"] in html
    assert UI_STRINGS["ko"]["submit"] in html


def test_english_device_gets_english_ui(client):
    res = client.get("/", headers={"Accept-Language": "en-US,en;q=0.9"})
    html = res.data.decode()

    assert 'lang="en"' in html
    assert UI_STRINGS["en"]["app_title"] in html
    assert UI_STRINGS["en"]["submit"] in html
    # 한글 문구가 한 줄이라도 남아 있으면 사전으로 안 옮긴 하드코딩이다.
    assert not re.search(r"[가-힣]", html), re.findall(r"[가-힣 ]+", html)[:5]


def test_ui_language_is_independent_of_puzzle_language(client, guest_headers):
    """기기 언어가 en 이어도 퍼즐 언어 기본값(ko)은 그대로다 (CONTEXT.md "UI 언어")."""
    res = client.get("/", headers={"Accept-Language": "en-US"})

    assert 'lang="en"' in res.data.decode()
    assert client.get("/api/v1/me/stats", headers=guest_headers).json["puzzle_language"] == "ko"


def test_page_varies_on_accept_language(client):
    """프록시·CDN 이 ko 페이지를 en 방문자에게 주지 않게 한다."""
    res = client.get("/")

    assert "Accept-Language" in res.headers.get("Vary", "")
    assert res.headers.get("Content-Language") == "ko"


def test_lang_query_param_overrides_the_device_language(client):
    """법적 문서 페이지와 같은 규칙(`?lang=` > Accept-Language) 을 쓴다."""
    res = client.get("/?lang=en", headers={"Accept-Language": "ko-KR,ko;q=0.9"})

    assert 'lang="en"' in res.data.decode()
    assert res.headers.get("Content-Language") == "en"


def test_js_reads_strings_from_the_embedded_dictionary(client):
    res = client.get("/", headers={"Accept-Language": "en"})
    strings = _embedded_strings(res.data.decode())

    assert strings == UI_STRINGS["en"]
    assert 'getElementById("ui-strings")' in _bundle()


# --- 09 의 공용 토큰 재사용 ---


def test_page_links_the_shared_token_stylesheet(client):
    html = client.get("/").data.decode()

    assert "tokens.css" in html
    assert html.index("tokens.css") < html.index("style.css"), "토큰이 먼저 와야 변수가 잡힌다"


# (티켓 17 의 `test_new_elements_use_token_variables_not_new_hex` 는 "17 이 새로 만든
# 선택자에는 hex 가 없다" 였다. 18 이 기존 규칙까지 토큰으로 옮겼으니 파일 전체를 보는
# `tests/test_web_design.py::test_style_sheet_has_no_hex_colors_left` 가 그 자리를
# 대신한다 — 디자인 계약은 그 파일에 모았다.)


# --- 퍼즐 언어 칩 --------------------------------------------------------------


def test_language_chips_are_rendered_for_both_puzzle_languages(client):
    html = client.get("/").data.decode()

    assert 'data-puzzle-language="ko"' in html
    assert 'data-puzzle-language="en"' in html


def test_js_changes_puzzle_language_with_patch_me_and_refetches(client):
    bundle = _bundle()

    assert '`${API_BASE}/me`' in bundle
    assert '"PATCH"' in bundle
    assert "puzzle_language" in bundle


# --- mask 기반 타일 렌더 (chosung 의존 제거) ----------------------------------


def test_js_renders_tiles_from_mask_not_chosung(client):
    bundle = _bundle()

    assert "puzzle.mask" in bundle
    # `chosung` 은 ko 호환 필드라 en 퍼즐에선 쓸 수 없다 — 응답에서 읽지 않아야 한다
    # (localStorage 키 이름의 "chosung" 은 제품 이름이라 별개다).
    assert "puzzle.chosung" not in bundle
    assert "state.chosung" not in bundle


def test_js_reinserts_separator_gaps_from_the_mask(client):
    """서버 `attempts[].guess` 는 구분자를 뺀 글자열이라 간격은 클라이언트가 끼운다
    (스펙 "미정 항목" 13)."""
    bundle = _bundle()

    assert "withSeparatorSlots" in bundle
    assert "SEPARATOR" in bundle


# --- 보드 복원은 서버 attempts, 로컬 history 키는 제거 -------------------------


def test_js_restores_the_board_from_server_attempts(client):
    bundle = _bundle()

    assert "puzzle.attempts" in bundle
    assert "localStorage" in bundle  # 토큰 저장은 남아 있어야 한다
    assert "chosung_history_" in bundle  # 옛 키를 지우는 코드로만 등장한다
    assert "saveHistory" not in bundle
    assert "loadHistory" not in bundle


def test_backup_and_restore_panel_is_kept(client):
    html = client.get("/").data.decode()
    bundle = _bundle()

    assert 'id="backup-panel"' in html
    assert 'id="restore-panel"' in html
    assert 'id="token-input"' in html
    assert 'const TOKEN_KEY = "chosung_token"' in bundle


# --- puzzle_id 동봉 · 409 PUZZLE_CHANGED --------------------------------------


def test_js_sends_puzzle_id_with_a_guess(client):
    """제출은 "그릴 때 받은" 퍼즐 ID 를 들고 간다 — 응답이 늦게 와도 그 ID 로 판단한다
    (응답 도착 순서까지 보는 건 tests/test_web_js.py)."""
    bundle = _bundle()

    assert "const requestedPuzzleId = state.puzzleId;" in bundle
    assert "puzzle_id: requestedPuzzleId" in bundle
    assert "state.puzzleId = puzzle.puzzle_id" in bundle


def test_js_handles_puzzle_changed_with_an_inline_message_and_refetch(client):
    bundle = _bundle()

    assert "PUZZLE_CHANGED" in bundle
    assert 't("puzzle_changed")' in bundle
    assert "reloadPuzzle" in bundle


def test_js_shows_the_puzzle_changed_notice_after_the_refetch(client):
    """재조회가 화면을 비우면서 #message 도 지우니, 안내는 그 뒤에 띄워야 남는다."""
    branch = _bundle().split('data.code === "PUZZLE_CHANGED"')[1].split("return;")[0]

    assert branch.index("await reloadPuzzle()") < branch.index('showMessage(t("puzzle_changed"))')


def test_js_submits_the_same_letters_it_draws_on_the_board(client):
    """보드 한 줄은 서버가 저장한 글자열(구분자 제거·en 대문자)과 같아야 한다."""
    bundle = _bundle()

    assert "function normalizeGuess(" in bundle
    assert "const guess = normalizeGuess(raw);" in bundle
    # 입력창 제한이 타일 수면 `harry-potter`(구분자 포함)를 칠 수가 없다.
    assert "maxLength = puzzle.mask.length" in bundle


def test_js_discards_local_play_state_on_language_and_account_switch(client):
    bundle = _bundle()

    assert "discardLocalPlayState" in bundle
    assert "clearStoredHistory" in bundle


# --- 리더보드 섹션 -------------------------------------------------------------


def test_leaderboard_section_is_rendered(client):
    html = client.get("/").data.decode()

    assert 'id="leaderboard-section"' in html
    assert 'id="my-rank"' in html
    assert 'id="leaderboard-entries"' in html
    assert 'id="today-stats"' in html


def test_js_renders_leaderboard_name_is_me_and_my_rank(client):
    bundle = _bundle()

    # 서버는 언어 중립 태그만 준다 — 이름은 번들이 UI 사전으로 만든다(티켓 38).
    assert "entry.anon_tag" in bundle
    assert "entry.display" not in bundle
    assert "entry.is_me" in bundle
    assert "data.me" in bundle


def test_js_asks_leaderboard_and_stats_for_an_explicit_language(client):
    """통계·리더보드는 "내가 안 고른 언어"도 볼 수 있는 엔드포인트라 언어를 명시한다."""
    bundle = _bundle()

    assert "/puzzles/today/leaderboard?language=" in bundle
    assert "/puzzles/today/stats?language=" in bundle


# --- 수동 체크리스트 -----------------------------------------------------------


def test_manual_checklist_is_documented():
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")

    assert "## 웹 수동 체크리스트" in readme
    items = [
        "퍼즐 언어 전환",
        "새 탭",
        "자정 경과",
        "계정 전환",
        "백업 코드",
        # 티켓 18 이 더한 줄. 브라우저 없이 못 보는 것들이라 표에 남는다.
        "섹션 토글",
        "로딩 스켈레톤",
        "오프라인",
        "퍼즐 없음 카운트다운",
        "앱 CTA",
        "삭제 후 새 게스트 발급",
        "다크모드",
        "공유 텍스트",
        "푸터",
    ]
    for item in items:
        assert item in readme, item


# --- 계정 삭제 신호(티켓 14) ------------------------------------------------


def test_static_js_discards_the_token_after_account_deletion(client):
    """삭제 후 /?deleted=1 로 돌아온 브라우저는 옛 토큰을 버리고 새 게스트를 받아야
    한다(티켓 14). JS 테스트 러너가 없어서 번들 내용으로 확인한다 — 웹 개편
    (티켓 17·18)에서 이 호출이 빠지면 삭제 직후 화면이 전부 401 로 죽는다.

    수동 확인 항목은 `docs/RELEASE.md` "### 14." 에 있다.
    """
    js = client.get("/static/app.js").data

    assert b'params.has("deleted")' in js
    assert b"safeStorageRemove(TOKEN_KEY)" in js
    assert b"discardDeletedAccountState();" in js


# --- 삭제 신호 처리(실제 app.js 를 Node 로 실행) -----------------------------
#
# 위 두 테스트처럼 번들 문자열만 보면 "있는 코드가 맞게 동작하는가" 를 못 본다.
# 삭제 신호는 외부 사이트가 보낸 링크로도 붙을 수 있어서(D-14-1) 동작으로 고정한다.
# Node 가 없는 환경에서는 건너뛴다 — 이 레포는 런타임에 Node 를 쓰지 않는다.

JS_HARNESS = Path(__file__).resolve().parent / "fixtures" / "js" / "deleted_state_harness.mjs"


def _run_deleted_signal(scenario: str, mode: str = "steps") -> dict:
    """`mode="steps"` 는 삭제 판단만, `mode="init"` 은 `init()` 한 바퀴를 통째로.

    순서가 틀린 결함(D-42-3)은 조각을 따로 부르면 안 보인다 — 안내를 적은 직후
    `restart()` 가 화면을 비우면서 지우기 때문이다.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 가 없어서 app.js 동작 테스트를 건너뛴다")

    result = subprocess.run(
        [node, str(JS_HARNESS), scenario, json.dumps(UI_STRINGS["ko"]), mode],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"하네스 실패:\n{result.stderr}"
    return json.loads(result.stdout)


def test_deleted_signal_discards_the_token_only_after_the_server_confirms_deletion():
    """정상 경로: 서버가 옛 토큰을 401 로 거절하면 토큰·보드 기록을 버리고 새 게스트."""
    out = _run_deleted_signal("token-is-dead")

    assert out["originalTokenRetained"] is False
    assert out["historyRetained"] is False
    assert out["issuedNewGuest"] is True
    assert any(r["method"] == "POST" and r["url"].endswith("/guests") for r in out["requests"])
    # 주소창에 신호가 남으면 새로고침마다 같은 분기를 다시 탄다.
    assert out["finalSearch"] == ""


def test_the_deletion_notice_is_still_on_screen_when_the_first_load_finishes():
    """D-42-3: 안내가 **남아야** 한다.

    `discardDeletedAccountState()` 안에서 띄우면 바로 뒤의 `restart()` →
    `discardLocalPlayState()` → `showMessage("")` 가 지워서, 되돌릴 수 없는 작업의
    유일한 확인을 사용자가 한 번도 못 본다. 그래서 조각이 아니라 `init()` 한 바퀴를
    돌려 **마지막에 화면에 남은** 문구를 본다.
    """
    out = _run_deleted_signal("token-is-dead", mode="init")

    assert out["finalMessage"] == UI_STRINGS["ko"]["account_deleted"]
    # 안내만 남고 끝나는 게 아니다 — 새 게스트도 실제로 받았다.
    assert out["issuedNewGuest"] is True


def test_the_deletion_notice_does_not_appear_for_a_fake_signal():
    """`?deleted=1` 만 붙은 링크로 들어왔고 토큰이 살아 있으면 안내도 없다."""
    out = _run_deleted_signal("token-is-alive", mode="init")

    assert out["finalMessage"] == ""
    assert out["originalTokenRetained"] is True


def test_deleted_signal_in_a_link_cannot_discard_a_living_guests_token():
    """D-14-1: `?deleted=1` 은 신호일 뿐 증거가 아니다.

    외부 사이트가 보낸 링크로 들어와도, 저장된 토큰이 아직 유효하면(200) 토큰과
    보드 기록은 그대로여야 한다 — 계정 연결·백업이 없는 플레이어에게 그 토큰이
    유일한 복구 수단이다.
    """
    out = _run_deleted_signal("token-is-alive")

    assert out["originalTokenRetained"] is True
    assert out["historyRetained"] is True
    assert not [r for r in out["requests"] if r["url"].endswith("/guests")]
    assert out["messages"] == []
    # 가짜 신호였으니 주소창에서는 지운다.
    assert out["finalSearch"] == ""


def test_deleted_signal_keeps_the_token_when_the_check_cannot_reach_the_server():
    """확인을 못 했으면 지우지 않는다. 신호는 주소창에 남겨 새로고침 때 다시 확인한다."""
    out = _run_deleted_signal("probe-unreachable")

    assert out["originalTokenRetained"] is True
    assert out["historyRetained"] is True
    assert out["finalSearch"] == "?deleted=1"


# --- 렌더된 HTML 에 파이썬 객체가 새지 않는다 (D-42-1) -------------------------
#
# `{{ t.copy }}` 는 Jinja 의 getattr 우선 규칙 때문에 사전 키가 아니라 `dict.copy`
# **메서드**를 집어, 버튼 라벨이 `<built-in method copy of dict object at 0x…>` 로
# 렌더됐다. 사전(`tests/test_ui_strings.py`)도 번들도 그 자리를 못 봤다 — 렌더된
# HTML 을 보는 테스트가 없었기 때문이다. 그래서 여기서 본다.

PAGES = ("/", "/privacy", "/terms", "/account/delete")
PYTHON_REPR_LEAKS = ("<built-in method", "<bound method", "<function ", " object at 0x")


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_no_page_renders_a_python_object_repr(client, path, lang):
    html = client.get(f"{path}?lang={lang}").data.decode()

    leaks = [needle for needle in PYTHON_REPR_LEAKS if needle in html]
    assert leaks == [], f"{path}?lang={lang} 에 파이썬 객체가 새어 나왔다: {leaks}"


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_the_copy_button_shows_the_dictionary_word(client, lang):
    """D-42-1 이 실제로 보이던 자리. 사전의 `copy` 가 그대로 라벨이어야 한다."""
    html = client.get(f"/?lang={lang}").data.decode()

    match = re.search(r'<button id="copy-token-button"[^>]*>(.*?)</button>', html, re.S)
    assert match, "복사 버튼이 없다"
    assert match.group(1).strip() == UI_STRINGS[lang]["copy"]


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_the_backup_code_box_has_an_accessible_name(client, lang):
    """D-42-2: 읽기 전용이라 placeholder 가 없고, 라벨이 없으면 스크린리더가 그
    칸이 무엇인지 못 읽는다(axe `label`, critical)."""
    html = client.get(f"/?lang={lang}").data.decode()

    match = re.search(r"<input id=\"token-display\"[^>]*>", html)
    assert match, "백업 코드 칸이 없다"
    assert f'aria-label="{UI_STRINGS[lang]["backup_code_label"]}"' in match.group(0)
