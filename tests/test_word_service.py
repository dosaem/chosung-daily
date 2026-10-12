from app.models import Word
from app.services.word_service import seed_words_from_csv


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
