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
