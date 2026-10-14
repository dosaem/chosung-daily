"""운영자 페이지 접근 판정 — 세션 → Guest → Account.email ∈ ADMIN_EMAILS.

세션에는 이메일이 없고 게스트 ID 만 있어서(app/api/oauth.py `sync_session`),
판정은 그 게스트에 연결된 Account 의 이메일로 한다. 운영자 페이지가 직접 구글
로그인을 시작하지는 않는다 — 현행 OAuth 진입(`/auth/google/login`)이 Bearer
토큰으로 심은 세션을 전제하므로, 로그인 안 된 브라우저는 `/` 로 돌려보낸다.
"""

from tests.conftest import ADMIN_EMAIL

ADMIN_PATHS = [
    "/admin/",
    "/admin/words/new",
    "/admin/words/import",
]


def test_admin_email_can_open_the_words_page(admin_session):
    res = admin_session.get("/admin/")

    assert res.status_code == 200
    assert "단어 목록".encode() in res.data


def test_other_email_is_forbidden(app, client, web_login):
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    web_login("someone-else@example.com")

    res = client.get("/admin/")

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_request_without_a_session_is_sent_to_the_home_page(client):
    res = client.get("/admin/")

    assert res.status_code == 302
    assert res.headers["Location"] == "/"

    followed = client.get("/admin/", follow_redirects=True)
    assert followed.status_code == 200
    assert "구글 로그인".encode() in followed.data
    assert b"/admin" in followed.data


def test_logged_in_guest_without_a_linked_account_is_sent_to_the_home_page(
    app, client, web_login
):
    """세션은 있지만 아직 구글 계정을 연결하지 않은 브라우저.

    이메일이 없으니 403 으로 막는 게 아니라, 로그인을 마치라고 안내한다 — 운영자가
    `/admin` 을 북마크해 두고 세션만 동기화된 상태로 들어오는 실제 경로다.
    """
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    web_login()

    res = client.get("/admin/")

    assert res.status_code == 302
    assert res.headers["Location"] == "/"


def test_nobody_is_an_admin_when_admin_emails_is_unset(app, client, web_login):
    """`ADMIN_EMAILS` 기본값은 없다 — 설정을 깜빡한 환경에서 운영자가 생기면 안 된다."""
    app.config["ADMIN_EMAILS"] = ()
    web_login(ADMIN_EMAIL)

    res = client.get("/admin/")

    assert res.status_code == 403


def test_email_match_ignores_case_and_surrounding_spaces(app, client, web_login):
    """구글이 돌려주는 이메일의 대소문자를 운영자가 맞춰 적게 만들지 않는다."""
    app.config["ADMIN_EMAILS"] = ("dosaem90@gmail.com",)
    web_login(" DoSaem90@Gmail.com ")

    assert client.get("/admin/").status_code == 200


def test_every_admin_page_is_guarded(client):
    for path in ADMIN_PATHS:
        assert client.get(path).status_code == 302, path
