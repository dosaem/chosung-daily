from app.models import DailyPuzzle, Word


def test_seed_words_command(app, tmp_path):
    csv_path = tmp_path / "words.csv"
    csv_path.write_text("answer,category,hint\n사과,general,과일\n", encoding="utf-8")

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-words", str(csv_path)])

    assert result.exit_code == 0
    assert "1개 단어 시드 완료" in result.output
    assert Word.query.count() == 1


def test_schedule_puzzles_command(app, tmp_path):
    csv_path = tmp_path / "words.csv"
    csv_path.write_text(
        "answer,category,hint\n사과,general,과일\n학교,general,배우는 곳\n", encoding="utf-8"
    )
    app.test_cli_runner().invoke(args=["seed-words", str(csv_path)])

    result = app.test_cli_runner().invoke(args=["schedule-puzzles", "--days", "3"])

    assert result.exit_code == 0
    assert "3일치 퍼즐 배정 완료" in result.output
    assert DailyPuzzle.query.count() == 3


def test_search_books_command_without_api_keys(app, monkeypatch):
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    monkeypatch.delenv("ALADIN_TTB_KEY", raising=False)

    result = app.test_cli_runner().invoke(args=["search-books", "데미안"])

    assert result.exit_code == 0
    assert "검색 결과 없음" in result.output
