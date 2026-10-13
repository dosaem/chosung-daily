def _guess(client, headers, puzzle, text):
    return client.post(
        "/api/v1/puzzles/today/guesses",
        headers=headers,
        json={"puzzle_id": puzzle.id, "guess": text},
    )


def test_correct_guess_reveals_answer_and_no_feedback(client, guest_headers, today_puzzle):
    res = _guess(client, guest_headers, today_puzzle, "사과")
    body = res.get_json()

    assert res.status_code == 200
    assert body["is_correct"] is True
    assert body["feedback"] is None
    assert body["attempts_left"] == 4
    assert body["answer"] == "사과"


def test_wrong_guess_returns_per_position_feedback(client, guest_headers, today_puzzle):
    res = _guess(client, guest_headers, today_puzzle, "바과")
    body = res.get_json()

    assert res.status_code == 200
    assert body["is_correct"] is False
    assert body["feedback"] == [False, True]
    assert body["attempts_left"] == 4
    assert body["answer"] is None


def test_length_mismatch_is_rejected_without_consuming_attempt(client, guest_headers, today_puzzle):
    res = _guess(client, guest_headers, today_puzzle, "사과사과")

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"

    today_res = client.get("/api/v1/puzzles/today", headers=guest_headers)
    assert today_res.get_json()["attempts_left"] == 5


def test_hint_revealed_after_third_wrong_guess(client, guest_headers, today_puzzle):
    for _ in range(2):
        res = _guess(client, guest_headers, today_puzzle, "바바")
        assert res.get_json()["hint"] is None

    third = _guess(client, guest_headers, today_puzzle, "바바")
    assert third.get_json()["hint"] == "빨간 과일"


def test_exhausting_attempts_reveals_answer_and_then_blocks(client, guest_headers, today_puzzle):
    for _ in range(5):
        res = _guess(client, guest_headers, today_puzzle, "바바")

    assert res.get_json()["answer"] == "사과"
    assert res.get_json()["attempts_left"] == 0

    blocked = _guess(client, guest_headers, today_puzzle, "바바")
    assert blocked.status_code == 409
    assert blocked.get_json()["code"] == "ALREADY_FINISHED"


def test_guessing_again_after_solved_is_blocked(client, guest_headers, today_puzzle):
    _guess(client, guest_headers, today_puzzle, "사과")

    res = _guess(client, guest_headers, today_puzzle, "사과")

    assert res.status_code == 409
    assert res.get_json()["code"] == "ALREADY_FINISHED"
