"""퍼즐 조회·통계·리더보드의 언어 인지화 — 같은 날 ko/en 공존, 캐시·집계 분리."""

import json

from app.extensions import get_redis
from app.models import PuzzleLanguage
from app.services.guest_service import issue_guest
from app.services.puzzle_metrics import display_name


def _headers(guest):
    return {"Authorization": f"Bearer {guest.token}"}


def _switch_to(client, headers, language: str):
    res = client.patch("/api/v1/me", headers=headers, json={"puzzle_language": language})
    assert res.status_code == 200


def test_korean_guest_gets_korean_puzzle_with_language_fields(client, guest_headers, today_puzzle):
    res = client.get("/api/v1/puzzles/today", headers=guest_headers)
    body = res.get_json()

    assert res.status_code == 200
    assert body["puzzle_id"] == today_puzzle.id
    assert body["language"] == "ko"
    assert body["length"] == 2
    assert body["mask"] == [{"t": "r", "c": "ㅅ"}, {"t": "r", "c": "ㄱ"}]
    # ko 의 `chosung` 은 현행 값 그대로 — 기존 클라이언트가 그대로 돈다.
    assert body["chosung"] == "ㅅㄱ"
    assert body["answer"] is None


def test_english_guest_gets_english_puzzle(client, make_today_puzzle):
    en_puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")
    guest = issue_guest(PuzzleLanguage.EN)

    res = client.get("/api/v1/puzzles/today", headers=_headers(guest))
    body = res.get_json()

    assert res.status_code == 200
    assert body["puzzle_id"] == en_puzzle.id
    assert body["language"] == "en"
    assert body["length"] == 5
    assert body["mask"] == [
        {"t": "h", "c": ""},
        {"t": "r", "c": "P"},
        {"t": "r", "c": "P"},
        {"t": "r", "c": "L"},
        {"t": "h", "c": ""},
    ]
    # en 의 `chosung` 은 mask 의 `r` 글자 기반 문자열 — 빈 타일은 자리표시자다.
    assert body["chosung"] == "_PPL_"
    assert body["answer"] is None


def test_english_length_excludes_separators(client, make_today_puzzle):
    make_today_puzzle(PuzzleLanguage.EN, answer="harry potter", hint="wizard")
    guest = issue_guest(PuzzleLanguage.EN)

    body = client.get("/api/v1/puzzles/today", headers=_headers(guest)).get_json()

    assert body["length"] == 11  # 공백은 타일이 아니다
    assert body["chosung"] == "H_RRY P_TT_R"


def test_both_languages_coexist_on_the_same_day(client, make_today_puzzle):
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    en_puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")
    assert ko_puzzle.id != en_puzzle.id
    assert ko_puzzle.puzzle_date == en_puzzle.puzzle_date

    guest = issue_guest()
    headers = _headers(guest)

    assert client.get("/api/v1/puzzles/today", headers=headers).get_json()["puzzle_id"] == (
        ko_puzzle.id
    )

    _switch_to(client, headers, "en")

    assert client.get("/api/v1/puzzles/today", headers=headers).get_json()["puzzle_id"] == (
        en_puzzle.id
    )


def test_missing_puzzle_in_preferred_language_is_404(client, today_puzzle):
    guest = issue_guest(PuzzleLanguage.EN)

    res = client.get("/api/v1/puzzles/today", headers=_headers(guest))

    assert res.status_code == 404
    assert res.get_json()["code"] == "NO_PUZZLE_TODAY"


def test_puzzle_cache_keys_are_split_by_language(client, make_today_puzzle):
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")
    today = ko_puzzle.puzzle_date.isoformat()

    guest = issue_guest()
    headers = _headers(guest)
    client.get("/api/v1/puzzles/today", headers=headers)

    assert json.loads(get_redis().get(f"puzzle:{today}:ko"))["answer"] == "사과"
    assert get_redis().get(f"puzzle:{today}:en") is None

    _switch_to(client, headers, "en")
    client.get("/api/v1/puzzles/today", headers=headers)

    assert json.loads(get_redis().get(f"puzzle:{today}:en"))["answer"] == "apple"


def test_stats_are_counted_per_language(client, make_today_puzzle):
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")

    ko_guest = issue_guest()
    client.post(
        "/api/v1/puzzles/today/guesses",
        headers=_headers(ko_guest),
        json={"puzzle_id": ko_puzzle.id, "guess": "사과"},
    )

    ko_body = client.get("/api/v1/puzzles/today/stats", headers=_headers(ko_guest)).get_json()
    assert ko_body["language"] == "ko"
    assert ko_body["total_solved"] == 1

    en_body = client.get(
        "/api/v1/puzzles/today/stats?language=en", headers=_headers(ko_guest)
    ).get_json()
    assert en_body["language"] == "en"
    assert en_body["total_solved"] == 0


def test_stats_keys_are_split_by_language(client, make_today_puzzle):
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    today = ko_puzzle.puzzle_date.isoformat()

    guest = issue_guest()
    client.post(
        "/api/v1/puzzles/today/guesses",
        headers=_headers(guest),
        json={"puzzle_id": ko_puzzle.id, "guess": "사과"},
    )

    assert get_redis().hgetall(f"stats:{today}:ko") == {"1": "1"}
    assert get_redis().hgetall(f"stats:{today}:en") == {}
    assert get_redis().zrange(f"lb:{today}:ko", 0, -1) == [str(guest.id)]
    assert get_redis().zrange(f"lb:{today}:en", 0, -1) == []


def test_leaderboard_is_separated_per_language(client, make_today_puzzle):
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    en_puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")

    ko_guest = issue_guest()
    client.post(
        "/api/v1/puzzles/today/guesses",
        headers=_headers(ko_guest),
        json={"puzzle_id": ko_puzzle.id, "guess": "사과"},
    )

    en_guest = issue_guest(PuzzleLanguage.EN)
    client.post(
        "/api/v1/puzzles/today/guesses",
        headers=_headers(en_guest),
        json={"puzzle_id": en_puzzle.id, "guess": "apple"},
    )

    ko_board = client.get(
        "/api/v1/puzzles/today/leaderboard", headers=_headers(ko_guest)
    ).get_json()
    assert ko_board["language"] == "ko"
    assert [e["display"] for e in ko_board["entries"]] == [display_name(ko_guest.id)]

    en_board = client.get(
        "/api/v1/puzzles/today/leaderboard?language=en", headers=_headers(ko_guest)
    ).get_json()
    assert en_board["language"] == "en"
    assert [e["display"] for e in en_board["entries"]] == [display_name(en_guest.id)]


def test_unsupported_language_query_param_is_a_validation_error(
    client, guest_headers, today_puzzle
):
    for path in ("stats", "leaderboard"):
        res = client.get(f"/api/v1/puzzles/today/{path}?language=jp", headers=guest_headers)

        assert res.status_code == 400
        assert res.get_json()["code"] == "VALIDATION_ERROR"
