from app.services.guest_service import issue_guest


def _guess(client, token, text):
    return client.post(
        "/api/v1/puzzles/today/guesses",
        headers={"Authorization": f"Bearer {token}"},
        json={"guess": text},
    )


def test_leaderboard_ranks_fewer_attempts_first(client, today_puzzle):
    fast = issue_guest()
    _guess(client, fast.token, "사과")  # 1번째 시도에 정답

    slow = issue_guest()
    _guess(client, slow.token, "바바")
    _guess(client, slow.token, "사과")  # 2번째 시도에 정답

    res = client.get(
        "/api/v1/puzzles/today/leaderboard",
        headers={"Authorization": f"Bearer {fast.token}"},
    )
    body = res.get_json()

    assert res.status_code == 200
    ranked_guest_ids = [e["guest_id"] for e in body["entries"]]
    assert ranked_guest_ids == [fast.id, slow.id]
    assert body["entries"][0]["attempts"] == 1
    assert body["entries"][0]["is_me"] is True
    assert body["entries"][1]["attempts"] == 2
    assert body["entries"][1]["is_me"] is False


def test_leaderboard_respects_limit(client, today_puzzle):
    for _ in range(3):
        guest = issue_guest()
        _guess(client, guest.token, "사과")

    res = client.get(
        "/api/v1/puzzles/today/leaderboard?limit=2",
        headers={"Authorization": f"Bearer {guest.token}"},
    )
    body = res.get_json()

    assert len(body["entries"]) == 2
    assert [e["rank"] for e in body["entries"]] == [1, 2]
