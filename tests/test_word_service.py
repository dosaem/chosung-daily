from app.models import PuzzleLanguage, Word, WordCategory
from app.schemas.book import BookSearchResult
from app.services.word_service import (
    WORD_CSV_COLUMNS,
    RowStatus,
    add_word_from_book,
    import_word_rows,
    missing_csv_columns,
    seed_words_from_csv,
)


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

# --- CSV 행 리스트 적재 (운영자 업로드와 CLI 시드가 같이 쓰는 경로) -------------


def _row(language="ko", category="general", answer="사과", hint="과일"):
    return {"language": language, "category": category, "answer": answer, "hint": hint}


def test_import_word_rows_reports_one_outcome_per_row(app):
    outcomes = import_word_rows([_row(answer="사과"), _row(answer="학교", hint="배우는 곳")])

    assert [outcome.status for outcome in outcomes] == [RowStatus.ADDED, RowStatus.ADDED]
    assert [outcome.line for outcome in outcomes] == [2, 3]  # 헤더가 1행
    assert Word.query.count() == 2


def test_import_word_rows_marks_an_already_registered_word_as_duplicate(app):
    import_word_rows([_row()])

    outcomes = import_word_rows([_row(hint="다른 힌트")])

    assert [outcome.status for outcome in outcomes] == [RowStatus.DUPLICATE]
    assert Word.query.count() == 1


def test_import_word_rows_marks_a_row_repeated_inside_the_list_as_duplicate(app):
    outcomes = import_word_rows([_row(), _row()])

    assert [outcome.status for outcome in outcomes] == [RowStatus.ADDED, RowStatus.DUPLICATE]
    assert Word.query.count() == 1


def test_import_word_rows_keeps_good_rows_when_one_row_is_broken(app):
    outcomes = import_word_rows(
        [_row(answer="사과"), _row(language="fr", answer="pomme"), _row(answer="학교")]
    )

    assert [outcome.status for outcome in outcomes] == [
        RowStatus.ADDED,
        RowStatus.ERROR,
        RowStatus.ADDED,
    ]
    assert "language" in outcomes[1].reason
    assert Word.query.count() == 2


def test_import_word_rows_reports_a_blank_answer_as_an_error(app):
    outcomes = import_word_rows([_row(answer="  ")])

    assert outcomes[0].status is RowStatus.ERROR
    assert "정답" in outcomes[0].reason
    assert Word.query.count() == 0


def test_import_word_rows_reports_a_missing_hint_as_an_error(app):
    outcomes = import_word_rows([{"language": "ko", "category": "general", "answer": "사과"}])

    assert outcomes[0].status is RowStatus.ERROR
    assert "힌트" in outcomes[0].reason


def test_import_word_rows_defaults_a_missing_language_to_korean(app):
    """language 열이 없던 시절의 CSV 가 그대로 돌아간다 (CLI `seed-words`)."""
    outcomes = import_word_rows([{"category": "general", "answer": "사과", "hint": "과일"}])

    assert outcomes[0].status is RowStatus.ADDED
    assert Word.query.one().language == PuzzleLanguage.KO


def test_import_word_rows_trims_surrounding_spaces(app):
    import_word_rows([_row(answer=" 사과 ", hint=" 과일 ")])

    word = Word.query.one()
    assert word.answer == "사과"
    assert word.hint == "과일"


def test_missing_csv_columns_lists_what_the_header_lacks(app):
    assert missing_csv_columns(["answer", "hint"]) == ["language", "category"]
    assert missing_csv_columns(None) == list(WORD_CSV_COLUMNS)
    assert missing_csv_columns(["language", "category", "answer", "hint"]) == []
    # 열 순서와 앞뒤 공백은 따지지 않는다 — 사람이 만든 CSV 다.
    assert missing_csv_columns([" answer", "hint ", "category", "language"]) == []
