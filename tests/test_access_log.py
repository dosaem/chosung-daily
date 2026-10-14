"""개인정보 처리 행위 감사 로그(`access_log`) — 기록·해시 체인·보관·점검.

근거는 **개인정보의 안전성 확보조치 기준**(개인정보보호위원회 고시 제2023-6호)
제8조(접속기록의 보관 및 점검)다. ① 1년 이상 보관 ② 월 1회 이상 점검 ③ 위·변조·
도난·분실 방지. 이 파일은 그 세 가지가 코드에 있는지를 본다 —
"어떤 행위가 기록되는가"(README 설계 판단 "36." 의 표), "행이 바뀌면 검출되는가",
"기간이 지난 행만 지워지는가".

웹 요청 접근 로그(Gunicorn 파일)는 `tests/test_access_log_file.py` 쪽이다. 이
파일은 DB 감사 로그만 본다.
"""

import importlib
import re
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app import access_log as access_log_wiring
from app import config
from app.extensions import db
from app.models import AccessLog, PuzzleLanguage, Word, WordCategory
from app.repositories import access_log_repository
from app.services import access_log_service
from app.utils.time import utcnow
from tests.conftest import ADMIN_EMAIL

REPO_ROOT = Path(__file__).resolve().parent.parent


def _rows():
    return db.session.query(AccessLog).order_by(AccessLog.id).all()


def _actions():
    return [row.action for row in _rows()]


def _row_at(monkeypatch, days_ago: int, *, minutes: int = 0) -> AccessLog:
    """`days_ago` 일 전(+`minutes` 분) 시각의 행 하나. 보관 기간 경계를 밀어 본다.

    행을 만든 뒤에 `occurred_at` 을 고치면 그 행의 해시가 내용과 안 맞게 된다
    (해시에 시각이 들어간다) — 그러면 보관 기간 테스트가 verify 를 같이 못 본다.
    그래서 **기록 시점의 시계를 과거로 바꿔** 해시까지 그 시각으로 만든다.
    패치는 이 행을 쌓는 동안만 걸려 있어서, 뒤따라오는 만료 삭제는 진짜 `utcnow`
    로 기준 시각을 잡는다.
    """
    when = utcnow() - timedelta(days=days_ago, minutes=minutes)
    with monkeypatch.context() as patched:
        patched.setattr(access_log_service, "utcnow", lambda: when)
        return access_log_service.record_access(
            action="me.history.read",
            actor=f"guest.{days_ago}.{minutes}",
            remote_ip="127.0.0.1",
            target=None,
            status_code=200,
        )


# ------------------------------------------------- 행위자 마스킹 · 기록 내용


def test_the_operator_email_is_masked_in_the_actor_column(admin_session):
    """로그에 전체 이메일을 남기지 않는다(기존 "로그 최소화" 원칙).

    그래도 "누가" 를 가려낼 수 있어야 접속기록이다 — 첫 글자와 도메인은 남긴다.
    """
    admin_session.get("/admin/")

    actors = {row.actor for row in _rows()}
    assert ADMIN_EMAIL not in actors
    assert actors == {f"{ADMIN_EMAIL[0]}***@{ADMIN_EMAIL.split('@')[1]}"}


def test_a_guest_actor_is_recorded_by_guest_id(client, guest_headers, today_puzzle):
    client.get("/api/v1/me/history", headers=guest_headers)

    rows = _rows()
    assert len(rows) == 1
    assert re.fullmatch(r"guest\.\d+", rows[0].actor), rows[0].actor


def test_each_row_records_who_when_where_and_what(admin_session):
    admin_session.get("/admin/settings")

    row = _rows()[-1]
    assert row.action == "admin.settings.read"
    assert row.actor.endswith("@example.com")
    assert row.remote_ip  # 테스트 클라이언트는 127.0.0.1
    assert row.result == "success"
    assert row.status_code == 200
    assert utcnow() - row.occurred_at < timedelta(seconds=30)


def test_the_target_identifier_is_recorded_for_a_single_object(admin_session, app):
    word = Word(
        answer="사과", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="과일"
    )
    db.session.add(word)
    db.session.commit()

    admin_session.get(f"/admin/words/{word.id}/edit")

    assert _rows()[-1].target == str(word.id)


# ------------------------------------------------------- 기록되는 행위 목록


def _readme_action_table() -> dict[str, str]:
    """README 설계 판단 "### 36." 의 "기록되는 행위" 표를 행위 → 경로로 읽는다.

    표가 코드와 갈라지면 문서가 거짓이 된다 — 아래 테스트가 둘을 맞춘다.
    """
    text_ = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    after = text_.split("### 36. 개인정보 안전성 확보조치")[1]
    # 다음 절(## 또는 ###)에서 끊는다.
    section = re.split(r"\n#{2,3} ", after)[0]
    rows = {}
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        rows[cells[0]] = cells[1]
    return rows


def test_the_recorded_actions_match_the_readme_table():
    table = _readme_action_table()
    assert table, "README 설계 판단 36. 에 기록되는 행위 표가 없다"
    assert set(table) == set(access_log_wiring.ACTION_BY_ENDPOINT.values())


# (행위, 요청을 만드는 함수). 표의 모든 행위를 실제 요청으로 한 번씩 발생시킨다 —
# "기록 지점을 배선했다" 가 아니라 "그 요청이 행을 남긴다" 를 본다.
def _admin_word(client):
    word = Word(
        answer="포도", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="과일"
    )
    db.session.add(word)
    db.session.commit()
    return word


ADMIN_REQUESTS = {
    "admin.word.list": lambda c: c.get("/admin/"),
    "admin.word.form": lambda c: c.get("/admin/words/new"),
    "admin.word.create": lambda c: c.post("/admin/words", data={}),
    "admin.word.update": lambda c: c.post(f"/admin/words/{_admin_word(c).id}", data={}),
    "admin.word.delete": lambda c: c.post(f"/admin/words/{_admin_word(c).id}/delete", data={}),
    "admin.csv.form": lambda c: c.get("/admin/words/import"),
    "admin.csv.import": lambda c: c.post("/admin/words/import", data={}),
    "admin.schedule.read": lambda c: c.get("/admin/schedule"),
    "admin.schedule.form": lambda c: c.get("/admin/schedule/2026-10-20/replace"),
    "admin.schedule.replace": lambda c: c.post("/admin/schedule/2026-10-20/replace", data={}),
    "admin.settings.read": lambda c: c.get("/admin/settings"),
    "admin.settings.save": lambda c: c.post("/admin/settings", data={}),
    "admin.book.search": lambda c: c.get("/admin/books"),
    "admin.book.create": lambda c: c.post("/admin/books", data={}),
}


@pytest.mark.parametrize("action", sorted(ADMIN_REQUESTS))
def test_every_admin_route_leaves_a_row_even_when_the_request_fails(
    admin_session, action, monkeypatch
):
    """조회(GET)도 남는다 — 운영자 화면 열람 자체가 개인정보처리시스템 접속이다.

    POST 들은 CSRF 토큰이 없어서 403 으로 떨어진다. 그래도 행은 남아야 한다:
    "실패한 접근 시도" 가 점검에서 가장 보고 싶은 기록이다.
    """
    monkeypatch.setattr(
        "app.services.book_lookup_service.search_google_books", lambda *a, **k: []
    )

    ADMIN_REQUESTS[action](admin_session)

    assert action in _actions()


def test_a_forbidden_operator_attempt_is_recorded_as_denied(app, client, web_login):
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    web_login("not-an-admin@example.com")

    assert client.get("/admin/").status_code == 403

    row = _rows()[-1]
    assert row.action == "admin.word.list"
    assert row.result == "denied"
    assert row.status_code == 403


def test_deleting_an_account_through_the_api_is_recorded(client, guest_headers):
    assert client.delete("/api/v1/me", headers=guest_headers).status_code == 204

    assert _actions() == ["account.delete"]


def test_deleting_an_account_through_the_web_page_is_recorded(client, web_login):
    web_login()
    page = client.get("/account/delete")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert token, page.get_data(as_text=True)

    res = client.post("/account/delete", data={"csrf_token": token.group(1)})

    assert res.status_code == 302
    assert "account.delete" in _actions()


def test_reading_my_own_history_is_recorded(client, guest_headers):
    client.get("/api/v1/me/history", headers=guest_headers)

    assert _actions() == ["me.history.read"]


def test_changing_my_puzzle_language_is_recorded(client, guest_headers):
    client.patch("/api/v1/me", json={"puzzle_language": "en"}, headers=guest_headers)

    assert _actions() == ["me.profile.update"]


def test_linking_an_account_by_token_exchange_is_recorded(client, guest_headers):
    """계정 연결은 개인정보(이메일) 수집 지점이다 — 실패해도 기록한다."""
    client.post(
        "/api/v1/auth/token-exchange",
        json={"provider": "google", "id_token": "not-a-real-token"},
        headers=guest_headers,
    )

    assert _actions() == ["account.link"]


def test_the_web_oauth_callback_is_recorded(client):
    res = client.get("/api/v1/auth/google/callback")

    assert res.status_code >= 400
    assert _actions() == ["account.link"]


def test_routes_that_do_not_process_personal_data_leave_no_rows(client, guest_headers):
    """전부 다 남기면 접속기록이 아니라 접근 로그다 — 점검이 불가능해진다.

    퍼즐 조회는 개인정보 처리 행위가 아니라서 DB 감사 로그에 안 남는다(요청 자체는
    Gunicorn 접근 로그 파일에 남는다).
    """
    client.get("/api/v1/config")
    client.get("/health")

    assert _rows() == []


# ------------------------------------------------------------- 해시 체인


def test_rows_are_chained_by_sha256_of_the_previous_hash(client, guest_headers):
    client.get("/api/v1/me/history", headers=guest_headers)
    client.patch("/api/v1/me", json={"puzzle_language": "en"}, headers=guest_headers)

    first, second = _rows()
    assert first.prev_hash == access_log_service.GENESIS_HASH
    assert second.prev_hash == first.hash
    for row in (first, second):
        assert row.hash == access_log_service.row_hash(row)


def test_verify_accepts_an_untouched_chain(client, guest_headers):
    client.get("/api/v1/me/history", headers=guest_headers)

    result = access_log_service.verify_chain()

    assert result.broken_at is None
    assert result.checked == 1


def test_verify_reports_the_row_where_the_chain_breaks(client, guest_headers):
    """행 내용을 SQL 로 바꿔치면(앱을 거치지 않은 위·변조) 그 지점이 잡힌다.
    고시 제8조 제3항의 "위·변조 방지" 를 사람이 확인할 수 있는 수단이다."""
    for _ in range(3):
        client.get("/api/v1/me/history", headers=guest_headers)
    tampered = _rows()[1]

    db.session.execute(
        text("UPDATE access_log SET action = :action WHERE id = :id"),
        {"action": "admin.word.list", "id": tampered.id},
    )
    db.session.commit()

    result = access_log_service.verify_chain()

    assert result.broken_at == tampered.id
    # 끊긴 지점까지만 세고 멈춘다 — 그 뒤는 어차피 전부 안 맞는다.
    assert result.checked == 2


def test_verify_detects_a_deleted_row_in_the_middle(client, guest_headers):
    for _ in range(3):
        client.get("/api/v1/me/history", headers=guest_headers)
    removed = _rows()[1]

    db.session.execute(text("DELETE FROM access_log WHERE id = :id"), {"id": removed.id})
    db.session.commit()

    assert access_log_service.verify_chain().broken_at == _rows()[-1].id


def test_verify_still_passes_after_the_retention_purge(app, monkeypatch):
    """만료 삭제는 체인의 맨 앞을 잘라낸다 — 그걸 "끊겼다" 로 보면 첫 삭제 이후
    verify 가 영원히 실패해서 점검 도구가 쓸모없어진다."""
    app.config["ACCESS_LOG_RETENTION_DAYS"] = 365
    _row_at(monkeypatch, 400)
    _row_at(monkeypatch, 366)
    kept = _row_at(monkeypatch, 1).id

    assert access_log_service.purge_expired_access_logs() == 2

    result = access_log_service.verify_chain()
    assert result.broken_at is None
    assert result.checked == 1
    assert {row.id for row in _rows()} == {kept}


def test_verify_still_catches_tampering_in_the_rows_that_remain(app, monkeypatch):
    """앞을 잘라낸 뒤에도 남은 행의 내용이 바뀌면 잡아야 한다."""
    app.config["ACCESS_LOG_RETENTION_DAYS"] = 365
    _row_at(monkeypatch, 400)
    _row_at(monkeypatch, 2)
    tampered = _row_at(monkeypatch, 1)
    access_log_service.purge_expired_access_logs()

    db.session.execute(
        text("UPDATE access_log SET remote_ip = '10.0.0.1' WHERE id = :id"),
        {"id": tampered.id},
    )
    db.session.commit()

    assert access_log_service.verify_chain().broken_at == tampered.id


def test_the_model_has_no_updated_at_column():
    """한 번 쓰면 안 고치는 테이블이다 — 수정 시각 자리를 두지 않는다."""
    assert "updated_at" not in AccessLog.__table__.columns


def test_the_repository_exposes_no_update_or_delete_path():
    """INSERT 전용 리포지토리. 만료 삭제는 서비스(Beat 작업)만 한다 —
    기록 경로 옆에 삭제 함수를 두면 "지울 수 있는 로그" 가 된다."""
    public = {name for name in vars(access_log_repository) if not name.startswith("_")}
    assert "append" in public
    assert not {name for name in public if re.search(r"update|delete|remove|save", name)}


# --------------------------------------------------------- 보관 기간 · 삭제


def test_rows_past_the_retention_period_are_deleted(app, monkeypatch):
    """경계를 1분씩 밀어서 본다 — "365일 보관" 은 365일이 지난 행부터 지운다."""
    app.config["ACCESS_LOG_RETENTION_DAYS"] = 365
    old = _row_at(monkeypatch, 400).id
    just_past = _row_at(monkeypatch, 365, minutes=1).id
    just_inside = _row_at(monkeypatch, 365, minutes=-1).id
    recent = _row_at(monkeypatch, 10).id

    deleted = access_log_service.purge_expired_access_logs()

    assert deleted == 2
    remaining = {row.id for row in _rows()}
    assert remaining == {just_inside, recent}
    assert old not in remaining
    assert just_past not in remaining


def test_the_retention_period_is_configurable(app, monkeypatch):
    app.config["ACCESS_LOG_RETENTION_DAYS"] = 730
    old = _row_at(monkeypatch, 366).id

    assert access_log_service.purge_expired_access_logs() == 0
    assert old in {row.id for row in _rows()}


def test_the_default_retention_is_the_legal_minimum_of_one_year(app):
    """고시 제8조 제1항: 1년 이상. 고유식별정보·민감정보를 처리하지 않고
    정보주체 5만명 미만이라 2년 상향 요건에 걸리지 않는다."""
    assert app.config["ACCESS_LOG_RETENTION_DAYS"] == 365


def test_an_empty_retention_env_falls_back_to_the_legal_minimum(monkeypatch):
    """`.env.example` 은 `ACCESS_LOG_RETENTION_DAYS=` 로 키만 둔다. 그대로 복사해 쓰면
    환경에는 빈 문자열이 들어오는데, `int("")` 면 앱이 기동조차 못 한다."""
    monkeypatch.setenv("ACCESS_LOG_RETENTION_DAYS", "")
    importlib.reload(config)

    try:
        assert config.Config.ACCESS_LOG_RETENTION_DAYS == 365
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_a_failed_purge_tells_the_operator(app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        access_log_service, "notify_operator", lambda kind, message: sent.append(kind)
    )

    def boom(*args, **kwargs):
        raise RuntimeError("deadlock found when trying to get lock")

    monkeypatch.setattr(access_log_service, "_delete_rows_before", boom)

    with pytest.raises(RuntimeError):
        access_log_service.purge_expired_access_logs()

    assert sent == ["접속기록 만료 삭제 실패"]


# ----------------------------------------------------------------- 점검


def test_the_monthly_report_counts_actions_denials_and_verifies_the_chain(
    app, client, guest_headers
):
    """고시 제8조 제2항의 "월 1회 이상 점검" 을 사람이 할 수 있게 하는 출력."""
    app.config["ADMIN_EMAILS"] = ()
    client.get("/api/v1/me/history", headers=guest_headers)
    client.get("/api/v1/me/history", headers=guest_headers)
    client.patch("/api/v1/me", json={"puzzle_language": "en"}, headers=guest_headers)

    report = access_log_service.monthly_report(utcnow().strftime("%Y-%m"))

    assert report.total == 3
    assert report.by_action == {"me.history.read": 2, "me.profile.update": 1}
    assert report.denied == 0
    assert report.chain.broken_at is None


def test_the_monthly_report_only_counts_that_month(app, client, guest_headers, monkeypatch):
    client.get("/api/v1/me/history", headers=guest_headers)
    _row_at(monkeypatch, 400)

    report = access_log_service.monthly_report(utcnow().strftime("%Y-%m"))

    assert report.total == 1


def test_the_monthly_report_rejects_a_bad_month():
    with pytest.raises(ValueError, match="month must be in"):
        access_log_service.monthly_report("2026-13")
