from sqlalchemy import text

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word
from app.services import access_log_service, operator_alert_service
from app.utils.time import utcnow


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


# ------------------------------------------- 접속기록 점검 CLI (티켓 36)


def _append_access_log_row(action="me.history.read", status_code=200):
    return access_log_service.record_access(
        action=action, actor="guest.1", remote_ip="127.0.0.1", target=None, status_code=status_code
    )


def test_access_log_verify_passes_on_an_untouched_chain(app):
    _append_access_log_row()
    _append_access_log_row()

    result = app.test_cli_runner().invoke(args=["access-log", "verify"])

    assert result.exit_code == 0
    assert "2행" in result.output
    assert "이상 없음" in result.output


def test_access_log_verify_exits_nonzero_and_names_the_broken_row(app):
    """위·변조 검출이 종료 코드로도 나와야 사람이 아니라 점검 스크립트도 쓸 수 있다."""
    _append_access_log_row()
    tampered = _append_access_log_row()
    _append_access_log_row()
    db.session.execute(
        text("UPDATE access_log SET actor = 'guest.999' WHERE id = :id"), {"id": tampered.id}
    )
    db.session.commit()

    result = app.test_cli_runner().invoke(args=["access-log", "verify"])

    assert result.exit_code != 0
    assert f"id={tampered.id}" in result.output


def test_access_log_report_prints_counts_denials_and_the_chain_result(app):
    _append_access_log_row()
    _append_access_log_row(action="admin.word.list")
    _append_access_log_row(action="admin.word.list", status_code=403)

    result = app.test_cli_runner().invoke(
        args=["access-log", "report", "--month", utcnow().strftime("%Y-%m")]
    )

    assert result.exit_code == 0
    assert "총 3건" in result.output
    assert "admin.word.list 2" in result.output
    assert "me.history.read 1" in result.output
    assert "거부 1건" in result.output
    assert "이상 없음" in result.output


def test_access_log_report_rejects_a_month_it_cannot_parse(app):
    result = app.test_cli_runner().invoke(args=["access-log", "report", "--month", "2026-13"])

    assert result.exit_code != 0
