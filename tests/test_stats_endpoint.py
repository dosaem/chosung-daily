from app.services.guest_service import issue_guest


def _solve(client, token, guesses):
    headers = {"Authorization": f"Bearer {token}"}
    for g in guesses:
        res = client.post("/api/v1/puzzles/today/guesses", headers=headers, json={"guess": g})
    return res


def test_stats_with_no_solvers_is_all_zero(client, guest_headers, today_puzzle):
    res = client.get("/api/v1/puzzles/today/stats", headers=guest_headers)
    body = res.get_json()

    assert res.status_code == 200
    assert body["total_solved"] == 0
    assert body["by_attempt"] == {"1": 0.0, "2": 0.0, "3": 0.0, "4": 0.0, "5": 0.0}


def test_stats_reflects_attempt_distribution(client, today_puzzle):
    guest1 = issue_guest()
    _solve(client, guest1.token, ["사과"])  # 1번째 시도에 정답

    guest2 = issue_guest()
    _solve(client, guest2.token, ["바바", "사과"])  # 2번째 시도에 정답

    res = client.get(
        "/api/v1/puzzles/today/stats",
        headers={"Authorization": f"Bearer {guest1.token}"},
    )
    body = res.get_json()

    assert body["total_solved"] == 2
    assert body["by_attempt"]["1"] == 0.5
    assert body["by_attempt"]["2"] == 0.5
    assert body["by_attempt"]["3"] == 0.0
