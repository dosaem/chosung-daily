"""퍼즐 고정(`puzzle_id`)·제출 일관성·시도 이력 복원.

스펙 §A.2 "퍼즐 고정 / 시도 이력 복원 / 힌트 표시 규칙".
"""

from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import Attempt, DailyPuzzle, Guest, GuestStats, PuzzleLanguage, Word, WordCategory
from app.services.guest_service import issue_guest


def _headers(guest):
    return {"Authorization": f"Bearer {guest.token}"}


def _guest_of(headers):
    token = headers["Authorization"].removeprefix("Bearer ")
    return Guest.query.filter_by(token=token).one()


def _today(client, headers):
    return client.get("/api/v1/puzzles/today", headers=headers).get_json()


def _guess(client, headers, puzzle_id, text):
    return client.post(
        "/api/v1/puzzles/today/guesses",
        headers=headers,
        json={"puzzle_id": puzzle_id, "guess": text},
    )


def _make_puzzle(puzzle_date, language=PuzzleLanguage.KO, answer="사과", hint="빨간 과일"):
    word = Word(answer=answer, language=language, category=WordCategory.GENERAL, hint=hint)
    db.session.add(word)
    db.session.flush()
    puzzle = DailyPuzzle(puzzle_date=puzzle_date, language=language, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


# --- 퍼즐 고정: puzzle_id 불일치 ---------------------------------------------


def test_guess_without_puzzle_id_is_rejected_as_puzzle_changed(
    client, guest_headers, today_puzzle
):
    res = client.post(
        "/api/v1/puzzles/today/guesses", headers=guest_headers, json={"guess": "사과"}
    )

    assert res.status_code == 409
    assert res.get_json()["code"] == "PUZZLE_CHANGED"
    assert Attempt.query.count() == 0


def test_guess_for_yesterdays_puzzle_is_rejected_without_consuming_an_attempt(
    client, guest_headers, today_puzzle
):
    """자정 경과 시나리오 — 어제 퍼즐을 보던 클라이언트가 그대로 제출한다."""
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    stale = _make_puzzle(yesterday, answer="수박", hint="여름 과일")
    guest = _guest_of(guest_headers)

    res = _guess(client, guest_headers, stale.id, "사과")

    assert res.status_code == 409
    assert res.get_json()["code"] == "PUZZLE_CHANGED"
    assert Attempt.query.count() == 0
    stats = db.session.get(GuestStats, guest.id)
    assert (stats.current_streak, stats.solved_count, stats.last_solved_date) == (0, 0, None)


def test_guess_for_other_language_puzzle_is_rejected(client, make_today_puzzle):
    """다른 기기에서 언어를 바꾼 시나리오 — 화면은 ko 인데 선호 언어는 en 이다."""
    ko_puzzle = make_today_puzzle(PuzzleLanguage.KO)
    make_today_puzzle(PuzzleLanguage.EN, answer="apple", hint="red fruit")
    guest = issue_guest()
    headers = _headers(guest)

    client.patch("/api/v1/me", headers=headers, json={"puzzle_language": "en"})

    res = _guess(client, headers, ko_puzzle.id, "사과")

    assert res.status_code == 409
    assert res.get_json()["code"] == "PUZZLE_CHANGED"
    assert Attempt.query.count() == 0


def test_matching_puzzle_id_is_accepted(client, guest_headers, today_puzzle):
    res = _guess(client, guest_headers, today_puzzle.id, "사과")

    assert res.status_code == 200
    assert res.get_json()["is_correct"] is True


# --- 제출 일관성: 구분자·대소문자 --------------------------------------------


def test_english_guess_ignores_separators_and_case(client, make_today_puzzle):
    puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="harry potter", hint="wizard")
    spaced = issue_guest(PuzzleLanguage.EN)
    hyphened = issue_guest(PuzzleLanguage.EN)

    spaced_res = _guess(client, _headers(spaced), puzzle.id, "Harry Potter")
    hyphened_res = _guess(client, _headers(hyphened), puzzle.id, "harry-potter")

    assert spaced_res.get_json() == hyphened_res.get_json()
    assert spaced_res.get_json()["is_correct"] is True
    assert spaced_res.get_json()["answer"] == "harry potter"


def test_english_wrong_guess_feedback_maps_to_separator_free_positions(
    client, make_today_puzzle
):
    puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="harry potter", hint="wizard")
    guest = issue_guest(PuzzleLanguage.EN)

    body = _guess(client, _headers(guest), puzzle.id, "harry-rotter").get_json()

    # "harryrotter" vs "harrypotter" — 구분자를 뺀 11자리에 1:1 로 돌아온다.
    assert body["is_correct"] is False
    assert len(body["feedback"]) == 11
    assert body["feedback"] == [True] * 5 + [False] + [True] * 5


def test_english_length_is_checked_after_removing_separators(client, make_today_puzzle):
    puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="harry potter", hint="wizard")
    guest = issue_guest(PuzzleLanguage.EN)
    headers = _headers(guest)

    res = _guess(client, headers, puzzle.id, "harry potte")

    assert res.status_code == 400
    assert res.get_json()["code"] == "VALIDATION_ERROR"
    assert Attempt.query.count() == 0
    assert _today(client, headers)["attempts_left"] == 5


def test_korean_guess_ignores_separators(client, make_today_puzzle):
    puzzle = make_today_puzzle(PuzzleLanguage.KO, answer="해리 포터", hint="마법사")
    guest = issue_guest()

    body = _guess(client, _headers(guest), puzzle.id, "해리포터").get_json()

    assert body["is_correct"] is True


# --- 시도 이력 복원 -----------------------------------------------------------


def test_today_restores_attempts_for_a_fresh_client(app, client, guest_headers, today_puzzle):
    _guess(client, guest_headers, today_puzzle.id, "바과")
    _guess(client, guest_headers, today_puzzle.id, "사자")

    fresh = app.test_client()
    body = _today(fresh, guest_headers)

    assert body["attempts"] == [
        {"guess": "바과", "feedback": [False, True]},
        {"guess": "사자", "feedback": [True, False]},
    ]
    assert body["attempts_left"] == 3


def test_solved_attempt_row_feedback_is_all_true(client, guest_headers, today_puzzle):
    """미정 12 확정 — 정답 행도 `feedback` 을 채워 보낸다(웹이 "항상 채워짐" 전제)."""
    _guess(client, guest_headers, today_puzzle.id, "바과")
    _guess(client, guest_headers, today_puzzle.id, "사과")

    body = _today(client, guest_headers)

    assert body["attempts"][-1] == {"guess": "사과", "feedback": [True, True]}
    assert body["status"] == "success"


def test_attempts_are_empty_before_any_guess(client, guest_headers, today_puzzle):
    body = _today(client, guest_headers)

    assert body["attempts"] == []
    assert body["hint_unlocked"] is False


def test_english_attempt_history_stores_separator_free_guesses(client, make_today_puzzle):
    puzzle = make_today_puzzle(PuzzleLanguage.EN, answer="harry potter", hint="wizard")
    guest = issue_guest(PuzzleLanguage.EN)
    headers = _headers(guest)

    _guess(client, headers, puzzle.id, "Harry-Rotter")

    body = _today(client, headers)
    assert body["attempts"] == [
        {"guess": "HARRYROTTER", "feedback": [True] * 5 + [False] + [True] * 5}
    ]


# --- 힌트 표시 규칙 -----------------------------------------------------------


def test_hint_is_filled_in_both_responses_after_third_wrong_guess(
    client, guest_headers, today_puzzle
):
    for _ in range(2):
        assert _guess(client, guest_headers, today_puzzle.id, "바바").get_json()["hint"] is None
        assert _today(client, guest_headers)["hint"] is None

    third = _guess(client, guest_headers, today_puzzle.id, "바바")

    assert third.get_json()["hint"] == "빨간 과일"
    assert _today(client, guest_headers)["hint"] == "빨간 과일"
