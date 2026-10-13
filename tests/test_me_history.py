from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import Attempt, DailyPuzzle, PuzzleLanguage, Word, WordCategory
from app.services.game_rules import MAX_ATTEMPTS
from app.services.guest_service import issue_guest


def _headers(guest):
    return {"Authorization": f"Bearer {guest.token}"}


def _make_puzzle(puzzle_date, language=PuzzleLanguage.KO):
    word = Word(answer="사과", language=language, category=WordCategory.GENERAL, hint="과일")
    db.session.add(word)
    db.session.flush()
    puzzle = DailyPuzzle(puzzle_date=puzzle_date, language=language, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


def _record_attempts(guest_id, puzzle, wrong_count, solved):
    for attempt_no in range(1, wrong_count + 1):
        db.session.add(
            Attempt(
                guest_id=guest_id,
                puzzle_id=puzzle.id,
                guess="바바",
                is_correct=False,
                attempt_no=attempt_no,
            )
        )
    if solved:
        db.session.add(
            Attempt(
                guest_id=guest_id,
                puzzle_id=puzzle.id,
                guess="사과",
                is_correct=True,
                attempt_no=wrong_count + 1,
            )
        )
    db.session.commit()


def test_history_returns_seven_kst_days_oldest_first(client, app):
    guest = issue_guest()
    today = datetime.now(KST).date()

    body = client.get("/api/v1/me/history", headers=_headers(guest)).get_json()

    assert [row["date"] for row in body] == [
        (today - timedelta(days=offset)).isoformat() for offset in range(6, -1, -1)
    ]


def test_history_marks_each_language_separately(client, app):
    guest = issue_guest()
    today = datetime.now(KST).date()

    solved_ko = _make_puzzle(today - timedelta(days=1), PuzzleLanguage.KO)
    _record_attempts(guest.id, solved_ko, wrong_count=1, solved=True)

    failed_en = _make_puzzle(today - timedelta(days=1), PuzzleLanguage.EN)
    _record_attempts(guest.id, failed_en, wrong_count=MAX_ATTEMPTS, solved=False)

    in_progress_ko = _make_puzzle(today, PuzzleLanguage.KO)
    _record_attempts(guest.id, in_progress_ko, wrong_count=1, solved=False)

    body = client.get("/api/v1/me/history", headers=_headers(guest)).get_json()
    by_date = {row["date"]: row["results"] for row in body}

    yesterday = (today - timedelta(days=1)).isoformat()
    assert by_date[yesterday] == {"ko": "success", "en": "fail"}
    assert by_date[today.isoformat()] == {"ko": "in_progress", "en": "none"}


def test_history_shows_none_for_a_day_someone_else_played(client, app):
    mine = issue_guest()
    other = issue_guest()
    today = datetime.now(KST).date()

    puzzle = _make_puzzle(today, PuzzleLanguage.KO)
    _record_attempts(other.id, puzzle, wrong_count=0, solved=True)

    body = client.get("/api/v1/me/history", headers=_headers(mine)).get_json()
    by_date = {row["date"]: row["results"] for row in body}

    assert by_date[today.isoformat()] == {"ko": "none", "en": "none"}


def test_history_days_can_be_widened_up_to_31(client, app):
    guest = issue_guest()

    res = client.get("/api/v1/me/history?days=31", headers=_headers(guest))

    assert res.status_code == 200
    assert len(res.get_json()) == 31


def test_history_rejects_days_outside_the_allowed_range(client, app):
    guest = issue_guest()

    for days in ("32", "0", "-1", "abc"):
        res = client.get(f"/api/v1/me/history?days={days}", headers=_headers(guest))

        assert res.status_code == 400, days
        assert res.get_json()["code"] == "VALIDATION_ERROR"


def test_history_requires_a_guest_token(client, app):
    res = client.get("/api/v1/me/history")

    assert res.status_code == 401
