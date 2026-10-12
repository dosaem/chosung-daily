def test_today_requires_auth(client, today_puzzle):
    res = client.get("/api/v1/puzzles/today")

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_today_without_puzzle_returns_404(client, guest_headers):
    res = client.get("/api/v1/puzzles/today", headers=guest_headers)

    assert res.status_code == 404
    assert res.get_json()["code"] == "NO_PUZZLE_TODAY"


def test_today_does_not_leak_answer(client, guest_headers, today_puzzle):
    res = client.get("/api/v1/puzzles/today", headers=guest_headers)
    body = res.get_json()

    assert res.status_code == 200
    assert body["status"] == "in_progress"
    assert body["chosung"] == "ㅅㄱ"
    assert body["length"] == 2
    assert body["attempts_left"] == 5
    assert body["answer"] is None
    assert body["hint"] is None
