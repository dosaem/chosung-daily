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


def test_book_title_only_appears_on_sunday(app):
    general_words = [
        Word(answer=f"일반{i}", category=WordCategory.GENERAL, hint="테스트용") for i in range(5)
    ]
    book_words = [
        Word(answer=f"책{i}", category=WordCategory.BOOK_TITLE, hint="테스트용") for i in range(5)
    ]
    db.session.add_all(general_words + book_words)
    db.session.commit()

    # 14일(2주)이면 일요일이 항상 정확히 2번 들어있다 — 시작 요일에 상관없이.
    schedule_puzzles(days=14, avoid_days=2)

    puzzles = DailyPuzzle.query.all()
    assert len(puzzles) == 14

    for puzzle in puzzles:
        if puzzle.puzzle_date.weekday() != 6:  # 월=0 ... 일=6
            assert puzzle.word.category == WordCategory.GENERAL

    sunday_categories = {p.word.category for p in puzzles if p.puzzle_date.weekday() == 6}
    assert WordCategory.BOOK_TITLE in sunday_categories


def test_sunday_falls_back_to_general_when_no_book_title_words_exist(app):
    _make_words(3)  # 전부 일반 단어, book_title 없음

    created = schedule_puzzles(days=14, avoid_days=2)

    assert created == 14
    assert DailyPuzzle.query.count() == 14
