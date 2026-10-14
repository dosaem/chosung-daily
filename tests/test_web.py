"""웹 프론트(Jinja 1장 + vanilla JS)의 계약.

JS 테스트 러너가 없어서 번들 내용으로 확인하는 테스트와, 실제 `app.js` 를 Node
`vm` 에서 실행해 동작으로 확인하는 테스트가 같이 있다.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_index_page_renders(client):
    res = client.get("/")

    assert res.status_code == 200
    assert "오늘의 초성".encode() in res.data


def test_static_js_is_served(client):
    res = client.get("/static/app.js")

    assert res.status_code == 200
    assert b"API_BASE" in res.data


def test_static_js_sends_puzzle_id_with_a_guess(client):
    """현행 웹도 퍼즐 고정 규칙을 지켜야 제출이 409 로 막히지 않는다.

    JS 테스트 러너가 없어서 번들 내용으로 확인한다 — 웹 개편(티켓 17·18)에서
    제출 코드를 다시 쓸 때 이 한 줄이 빠지면 바로 걸린다.
    """
    res = client.get("/static/app.js")

    assert b"puzzle_id: state.puzzleId" in res.data
    assert b"state.puzzleId = puzzle.puzzle_id" in res.data


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


def _run_deleted_signal(scenario: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 가 없어서 app.js 동작 테스트를 건너뛴다")

    result = subprocess.run(
        [node, str(JS_HARNESS), scenario],
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
    assert out["messages"], "삭제 안내 메시지가 없다"
    # 주소창에 신호가 남으면 새로고침마다 같은 분기를 다시 탄다.
    assert out["finalSearch"] == ""


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
