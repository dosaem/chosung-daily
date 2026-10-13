"""퍼즐 언어가 들어간 모델 제약·기본값 테스트.

같은 날짜에 ko/en 퍼즐이 각각 하나씩 공존해야 하고(유니크 키에 언어 포함),
언어를 안 적은 기존 코드 경로는 전부 ko로 남아야 한다.
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import DailyPuzzle, DailyStats, Guest, PuzzleLanguage, Word, WordCategory
from app.services.guest_service import issue_guest
from app.utils.mask import HIDDEN, REVEALED, SEPARATOR

TEST_DATE = date(2026, 10, 14)


def _word(answer="사과", language=None, category=WordCategory.GENERAL):
    kwargs = {"answer": answer, "category": category, "hint": "힌트"}
    if language is not None:
        kwargs["language"] = language
    word = Word(**kwargs)
    db.session.add(word)
    db.session.flush()
    return word


# --- Word.language / Word.mask ---------------------------------------------


def test_word_language_defaults_to_korean(app):
    word = _word()
    db.session.commit()

    assert word.language == PuzzleLanguage.KO


def test_word_mask_is_computed_on_insert(app):
    word = _word("사과")
    db.session.commit()

    assert word.mask == [{"t": REVEALED, "c": "ㅅ"}, {"t": REVEALED, "c": "ㄱ"}]


def test_word_mask_is_recomputed_when_answer_changes(app):
    word = _word("사과")
    db.session.commit()

    word.answer = "학교"
    db.session.commit()

    assert word.mask == [{"t": REVEALED, "c": "ㅎ"}, {"t": REVEALED, "c": "ㄱ"}]


def test_word_mask_is_recomputed_when_language_changes(app):
    word = _word("apple")
    db.session.commit()

    word.language = PuzzleLanguage.EN
    db.session.commit()

    assert [tile["t"] for tile in word.mask] == [HIDDEN, REVEALED, REVEALED, REVEALED, HIDDEN]


def test_english_word_mask_hides_vowels_and_marks_space(app):
    word = _word("harry potter", language=PuzzleLanguage.EN)
    db.session.commit()

    assert word.language == PuzzleLanguage.EN
    assert word.mask[0] == {"t": REVEALED, "c": "H"}
    assert word.mask[5] == {"t": SEPARATOR, "c": " "}


def test_english_word_keeps_chosung_column_filled(app):
    """`chosung`은 ko 응답 호환용으로 남겨둔 NOT NULL 컬럼이라, en 단어에서도
    값이 있어야 한다(초성이 없으니 자리표시자로 채워진다)."""
    word = _word("apple", language=PuzzleLanguage.EN)
    db.session.commit()

    assert word.chosung == "_____"


# --- DailyPuzzle (puzzle_date, language) 유니크 ------------------------------


def test_same_date_holds_one_puzzle_per_language(app):
    ko_word = _word("사과")
    en_word = _word("apple", language=PuzzleLanguage.EN)
    db.session.add_all(
        [
            DailyPuzzle(puzzle_date=TEST_DATE, word_id=ko_word.id, language=PuzzleLanguage.KO),
            DailyPuzzle(puzzle_date=TEST_DATE, word_id=en_word.id, language=PuzzleLanguage.EN),
        ]
    )
    db.session.commit()

    languages = {
        puzzle.language for puzzle in DailyPuzzle.query.filter_by(puzzle_date=TEST_DATE).all()
    }
    assert languages == {PuzzleLanguage.KO, PuzzleLanguage.EN}


def test_same_date_and_language_cannot_be_assigned_twice(app):
    word = _word("사과")
    db.session.add(DailyPuzzle(puzzle_date=TEST_DATE, word_id=word.id))
    db.session.commit()

    db.session.add(DailyPuzzle(puzzle_date=TEST_DATE, word_id=word.id))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_daily_puzzle_language_defaults_to_korean(app):
    word = _word("사과")
    puzzle = DailyPuzzle(puzzle_date=TEST_DATE, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()

    assert puzzle.language == PuzzleLanguage.KO


# --- Guest.puzzle_language --------------------------------------------------


def test_new_guest_prefers_korean(app):
    guest = issue_guest()

    assert guest.puzzle_language == PuzzleLanguage.KO
    assert db.session.get(Guest, guest.id).puzzle_language == PuzzleLanguage.KO


# --- DailyStats 키에 언어 ---------------------------------------------------


def test_daily_stats_is_keyed_by_date_and_language(app):
    db.session.add_all(
        [
            DailyStats(
                puzzle_date=TEST_DATE,
                language=PuzzleLanguage.KO,
                distribution={"1": 3},
                solver_count=3,
            ),
            DailyStats(
                puzzle_date=TEST_DATE,
                language=PuzzleLanguage.EN,
                distribution={"1": 1},
                solver_count=1,
            ),
        ]
    )
    db.session.commit()

    ko = db.session.get(DailyStats, (TEST_DATE, PuzzleLanguage.KO))
    en = db.session.get(DailyStats, (TEST_DATE, PuzzleLanguage.EN))
    assert (ko.solver_count, en.solver_count) == (3, 1)
