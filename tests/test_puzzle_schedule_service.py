from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import DailyPuzzle, Word, WordCategory
from app.services.puzzle_schedule_service import schedule_puzzles


def _make_words(n):
    words = [
        Word(answer=f"단어{i}", category=WordCategory.GENERAL, hint="테스트용")
        for i in range(n)
    ]
    db.session.add_all(words)
    db.session.commit()
    return words


def test_schedule_creates_one_puzzle_per_day(app):
    _make_words(5)

    created = schedule_puzzles(days=5, avoid_days=2)

    assert created == 5
    assert DailyPuzzle.query.count() == 5

    today = datetime.now(KST).date()
    expected_dates = {today + timedelta(days=i) for i in range(5)}
    actual_dates = {p.puzzle_date for p in DailyPuzzle.query.all()}
    assert actual_dates == expected_dates


def test_schedule_skips_existing_dates(app):
    _make_words(3)
    schedule_puzzles(days=2, avoid_days=1)

    created_again = schedule_puzzles(days=3, avoid_days=1)

    # 0, 1일차는 이미 있으니 2일차 하루만 새로 생겨야 함
    assert created_again == 1
    assert DailyPuzzle.query.count() == 3


def test_schedule_avoids_recently_used_words(app):
    _make_words(3)

    schedule_puzzles(days=3, avoid_days=2)

    puzzles = DailyPuzzle.query.order_by(DailyPuzzle.puzzle_date).all()
    word_ids = [p.word_id for p in puzzles]
    # 단어가 3개, avoid_days=2라 연속 3일은 전부 다른 단어여야 함
    assert len(set(word_ids)) == 3


def test_schedule_falls_back_when_pool_exhausted(app):
    _make_words(1)

    created = schedule_puzzles(days=3, avoid_days=14)

    assert created == 3
    assert DailyPuzzle.query.count() == 3
