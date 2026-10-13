def test_today_still_works_when_redis_is_down(client, guest_headers, today_puzzle, broken_redis):
    res = client.get("/api/v1/puzzles/today", headers=guest_headers)

    assert res.status_code == 200
    assert res.get_json()["chosung"] == "ㅅㄱ"


def test_guess_submission_still_works_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.post(
        "/api/v1/puzzles/today/guesses",
        headers=guest_headers,
        json={"puzzle_id": today_puzzle.id, "guess": "사과"},
    )

    assert res.status_code == 200
    assert res.get_json()["is_correct"] is True


def test_stats_returns_empty_instead_of_erroring_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.get("/api/v1/puzzles/today/stats", headers=guest_headers)

    assert res.status_code == 200
    assert res.get_json()["total_solved"] == 0


def test_leaderboard_returns_empty_instead_of_erroring_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    res = client.get("/api/v1/puzzles/today/leaderboard", headers=guest_headers)

    assert res.status_code == 200
    body = res.get_json()
    assert body["entries"] == []
    # ZRANK 도 같은 safe_redis_call 을 타서 None 으로 떨어진다 — 내 순위 칸은 비고,
    # 응답 자체는 200 이다.
    assert body["me"] is None


def test_rate_limit_does_not_block_when_redis_is_down(
    client, guest_headers, today_puzzle, broken_redis
):
    for _ in range(12):
        res = client.post(
            "/api/v1/puzzles/today/guesses",
            headers=guest_headers,
            json={"puzzle_id": today_puzzle.id, "guess": "바바"},
        )
        assert res.status_code != 429
