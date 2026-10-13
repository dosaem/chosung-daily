from app.models import PuzzleLanguage
from app.services.guest_service import issue_guest


def test_eleventh_guess_within_a_minute_is_rate_limited(client, guest_headers, today_puzzle):
    for _ in range(10):
        res = client.post(
            "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "바바"}
        )
        assert res.status_code != 429

    eleventh = client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "바바"}
    )

    assert eleventh.status_code == 429
    assert eleventh.get_json()["code"] == "RATE_LIMITED"


def test_rate_limit_is_per_guest(client, today_puzzle):
    guest_a = issue_guest()
    guest_b = issue_guest()

    headers_a = {"Authorization": f"Bearer {guest_a.token}"}
    headers_b = {"Authorization": f"Bearer {guest_b.token}"}

    for _ in range(10):
        client.post("/api/v1/puzzles/today/guesses", headers=headers_a, json={"guess": "바바"})

    blocked = client.post(
        "/api/v1/puzzles/today/guesses", headers=headers_a, json={"guess": "바바"}
    )
    assert blocked.status_code == 429

    still_ok = client.post(
        "/api/v1/puzzles/today/guesses", headers=headers_b, json={"guess": "바바"}
    )
    assert still_ok.status_code != 429


def test_rate_limit_counter_survives_a_language_change(client, guest_headers, make_today_puzzle):
    """rate limit 키에는 언어가 없다 — 언어를 바꿔 제출을 이어가도 같은 카운터다."""
    make_today_puzzle(PuzzleLanguage.KO)
    make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")

    for _ in range(10):
        res = client.post(
            "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "바바"}
        )
        assert res.status_code != 429

    client.patch("/api/v1/me", headers=guest_headers, json={"puzzle_language": "en"})

    eleventh = client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "banan"}
    )

    assert eleventh.status_code == 429
    assert eleventh.get_json()["code"] == "RATE_LIMITED"
