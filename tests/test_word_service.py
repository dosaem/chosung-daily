from app.models import PuzzleLanguage, Word, WordCategory
from app.schemas.book import BookSearchResult
from app.services.word_service import add_word_from_book, seed_words_from_csv


def _write_csv(tmp_path, rows):
    path = tmp_path / "words.csv"
    lines = ["answer,category,hint"] + [",".join(row) for row in rows]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_seed_words_creates_rows(app, tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ("사과", "general", "과일"),
            ("데미안", "book_title", "헤르만 헤세"),
        ],
    )

    result = seed_words_from_csv(csv_path)

    assert result.created == 2
    assert Word.query.count() == 2


def test_seed_words_is_idempotent(app, tmp_path):
    csv_path = _write_csv(tmp_path, [("사과", "general", "과일")])

    seed_words_from_csv(csv_path)
    second_run = seed_words_from_csv(csv_path)

    assert second_run.created == 0
    assert Word.query.count() == 1


def test_seed_words_skips_unknown_category(app, tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            ("사과", "general", "과일"),
            ("이상한것", "no_such_category", "모름"),
        ],
    )

    result = seed_words_from_csv(csv_path)

    assert result.created == 1
    assert len(result.skipped) == 1
    assert Word.query.count() == 1


def _book(title="데미안", author="헤르만 헤세", publisher="민음사"):
    return BookSearchResult(title=title, author=author, publisher=publisher, source="kakao")


def test_add_word_from_book_creates_new_word(app):
    word, created = add_word_from_book(_book())

    assert created is True
    assert word.answer == "데미안"
    assert word.category == WordCategory.BOOK_TITLE
    assert word.hint == "헤르만 헤세, 민음사"
    assert Word.query.count() == 1


def test_add_word_from_book_is_idempotent(app):
    """flask search-books ... --add를 같은 책으로 두 번 돌려도 Word가 중복
    등록되면 안 된다 — 실제로 "데미안"을 두 번 추가해서 중복 row가 생기는 걸
    발견하고 고쳤다.
    """
    add_word_from_book(_book())

    _word, created = add_word_from_book(_book())

    assert created is False
    assert Word.query.count() == 1


# --- 언어·가림 ---------------------------------------------------------------


def test_seed_words_defaults_to_korean_and_fills_mask(app, tmp_path):
    csv_path = _write_csv(tmp_path, [("사과", "general", "과일")])

    seed_words_from_csv(csv_path)

    word = Word.query.one()
    assert word.language == PuzzleLanguage.KO
    assert [tile["c"] for tile in word.mask] == ["ㅅ", "ㄱ"]


def test_seed_words_reads_language_column(app, tmp_path):
    path = tmp_path / "words.csv"
    path.write_text(
        "language,category,answer,hint\nen,general,apple,red fruit\n",
        encoding="utf-8",
    )

    result = seed_words_from_csv(str(path))

    assert result.created == 1
    word = Word.query.one()
    assert word.language == PuzzleLanguage.EN
    assert [tile["t"] for tile in word.mask] == ["h", "r", "r", "r", "h"]


def test_seed_words_skips_unknown_language(app, tmp_path):
    path = tmp_path / "words.csv"
    path.write_text(
        "language,category,answer,hint\nfr,general,pomme,fruit\n",
        encoding="utf-8",
    )

    result = seed_words_from_csv(str(path))

    assert result.created == 0
    assert len(result.skipped) == 1
    assert Word.query.count() == 0


def test_seed_words_treats_same_answer_in_another_language_as_a_different_word(app, tmp_path):
    path = tmp_path / "words.csv"
    path.write_text(
        "language,category,answer,hint\n"
        "ko,general,plan,계획\n"
        "en,general,plan,a scheme\n",
        encoding="utf-8",
    )

    result = seed_words_from_csv(str(path))

    assert result.created == 2
    assert {word.language for word in Word.query.all()} == {
        PuzzleLanguage.KO,
        PuzzleLanguage.EN,
    }


def test_add_word_from_book_defaults_to_korean_and_fills_mask(app):
    word, _created = add_word_from_book(_book())

    assert word.language == PuzzleLanguage.KO
    assert [tile["c"] for tile in word.mask] == ["ㄷ", "ㅁ", "ㅇ"]


def test_add_word_from_book_can_register_an_english_title(app):
    word, created = add_word_from_book(
        _book(title="Dune", author="Frank Herbert", publisher="Ace"),
        language=PuzzleLanguage.EN,
    )

    assert created is True
    assert word.language == PuzzleLanguage.EN
    assert [tile["t"] for tile in word.mask] == ["r", "h", "r", "h"]
