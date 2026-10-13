from app.models import DailyPuzzle, PuzzleLanguage, Word
from app.services import operator_alert_service


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


def test_schedule_puzzles_command_takes_a_language(app, tmp_path):
    csv_path = tmp_path / "words.csv"
    csv_path.write_text(
        "language,answer,category,hint\n"
        "ko,사과,general,과일\n"
        "en,apple,general,red fruit\n",
        encoding="utf-8",
    )
    app.test_cli_runner().invoke(args=["seed-words", str(csv_path)])

    result = app.test_cli_runner().invoke(
        args=["schedule-puzzles", "--language", "en", "--days", "2"]
    )

    assert result.exit_code == 0
    assert "en 2일치 퍼즐 배정 완료" in result.output
    puzzles = DailyPuzzle.query.all()
    assert len(puzzles) == 2
    assert all(p.language == PuzzleLanguage.EN for p in puzzles)


def test_schedule_puzzles_command_rejects_unknown_language(app):
    result = app.test_cli_runner().invoke(args=["schedule-puzzles", "--language", "jp"])

    assert result.exit_code != 0
    assert DailyPuzzle.query.count() == 0


def test_search_books_command_without_api_keys(app, monkeypatch):
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    monkeypatch.delenv("ALADIN_TTB_KEY", raising=False)

    result = app.test_cli_runner().invoke(args=["search-books", "데미안"])

    assert result.exit_code == 0
    assert "검색 결과 없음" in result.output


def test_notify_operator_test_command_reports_skip_without_webhook(app):
    """SLACK_WEBHOOK_URL 이 없으면 네트워크를 때리지 않고 그 사실을 알려준다."""
    app.config["SLACK_WEBHOOK_URL"] = ""

    result = app.test_cli_runner().invoke(args=["notify-operator-test"])

    assert result.exit_code == 0
    assert "SLACK_WEBHOOK_URL" in result.output


def test_notify_operator_test_command_sends_through_the_wrapper(app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        operator_alert_service, "post_webhook_message", lambda text: sent.append(text) or True
    )

    result = app.test_cli_runner().invoke(args=["notify-operator-test"])

    assert result.exit_code == 0
    assert "전송 완료" in result.output
    assert len(sent) == 1
    assert "연결 테스트" in sent[0]
