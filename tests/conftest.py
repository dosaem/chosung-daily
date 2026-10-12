from datetime import datetime

import pytest

from app import create_app
from app.config import KST
from app.extensions import db
from app.models import DailyPuzzle, Word, WordCategory
from app.services.guest_service import issue_guest


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    return db.session


@pytest.fixture
def today_puzzle(app):
    """오늘(KST) 날짜로 Word + DailyPuzzle을 만든다."""
    word = Word(answer="사과", category=WordCategory.GENERAL, hint="빨간 과일")
    db.session.add(word)
    db.session.flush()

    today = datetime.now(KST).date()
    puzzle = DailyPuzzle(puzzle_date=today, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


@pytest.fixture
def guest_headers(app):
    guest = issue_guest()
    return {"Authorization": f"Bearer {guest.token}"}
