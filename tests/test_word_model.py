from app.extensions import db
from app.models import Word, WordCategory


def test_chosung_computed_on_insert(app):
    word = Word(answer="사과", category=WordCategory.GENERAL, hint="과일")
    db.session.add(word)
    db.session.commit()

    assert word.chosung == "ㅅㄱ"


def test_chosung_recomputed_on_update(app):
    word = Word(answer="사과", category=WordCategory.GENERAL, hint="과일")
    db.session.add(word)
    db.session.commit()

    word.answer = "학교"
    db.session.commit()

    assert word.chosung == "ㅎㄱ"
