"""웹 폼 CSRF 토큰. 쓰는 라우트는 아직 없어서 테스트 전용 라우트를 붙여 검증한다.

실제 쿠키 세션을 타고 발급 → 제출까지 돌려본다 (session 을 직접 조작하지 않는다).
"""

import pytest

from app.csrf import CSRF_FORM_FIELD, csrf_protected, issue_csrf_token

ISSUE_PATH = "/_test/csrf/issue"
SUBMIT_PATH = "/_test/csrf/submit"


@pytest.fixture
def csrf_client(app):
    """토큰을 발급하는 GET 과 토큰을 요구하는 POST 를 임시로 붙인 테스트 클라이언트."""

    def issue_view():
        return {"token": issue_csrf_token()}

    @csrf_protected
    def submit_view():
        return {"ok": True}

    app.add_url_rule(ISSUE_PATH, "test_csrf_issue", issue_view, methods=["GET"])
    app.add_url_rule(SUBMIT_PATH, "test_csrf_submit", submit_view, methods=["POST"])
    return app.test_client()


def _issue(csrf_client):
    return csrf_client.get(ISSUE_PATH).get_json()["token"]


def test_issued_token_passes_verification(csrf_client):
    token = _issue(csrf_client)

    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 200
    assert res.get_json() == {"ok": True}


def test_each_issue_returns_a_fresh_token(csrf_client):
    first = _issue(csrf_client)
    second = _issue(csrf_client)

    assert first != second
    assert len(first) >= 32


def test_wrong_token_is_forbidden(csrf_client):
    _issue(csrf_client)

    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: "같지-않은-값"})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_missing_token_is_forbidden(csrf_client):
    _issue(csrf_client)

    res = csrf_client.post(SUBMIT_PATH, data={})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_request_without_any_issued_token_is_forbidden(csrf_client):
    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: "아무-값"})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_token_is_one_time_only(csrf_client):
    """같은 토큰으로 두 번 제출하면 두 번째는 막힌다 — 폼 재전송으로 삭제가 두 번
    일어나는 걸 막는 게 1회용의 목적이다."""
    token = _issue(csrf_client)

    assert csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token}).status_code == 200
    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_failed_attempt_does_not_burn_a_valid_token(csrf_client):
    """틀린 토큰을 던진 요청이 사용자가 열어둔 폼의 토큰까지 무효화하면 안 된다."""
    token = _issue(csrf_client)

    csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: "틀린-값"})

    assert csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token}).status_code == 200
