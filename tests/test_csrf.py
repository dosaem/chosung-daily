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


def _session_cookie(csrf_client):
    return csrf_client.get_cookie("session").value


def test_replayed_original_cookie_cannot_reuse_a_consumed_token(csrf_client):
    """소비된 토큰은 **그 토큰을 담고 있던 원래 쿠키를 되돌려도** 다시 안 통해야 한다.

    서명 쿠키 세션에서 `session.pop` 은 응답 쿠키만 바꾼다. 브라우저·중간 프록시가
    들고 있던 옛 쿠키를 그대로 다시 보내면 세션 안의 토큰이 되살아나므로, 소비
    사실은 서버가 기억해야 한다.
    """
    token = _issue(csrf_client)
    original = _session_cookie(csrf_client)

    assert csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token}).status_code == 200

    csrf_client.set_cookie("session", original)
    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"


def test_only_one_of_several_same_cookie_submits_passes(app, csrf_client):
    """같은 쿠키를 들고 동시에 들어온 중복 제출 중 하나만 통과한다(소비는 원자적).

    새로고침 연타·더블 클릭이 만드는 실제 모양이다. 쿠키 왕복이 끝나기 전에 보낸
    요청들은 전부 **같은** 세션 쿠키를 들고 오므로, 응답 쿠키로는 구분할 수 없다.
    """
    token = _issue(csrf_client)
    original = _session_cookie(csrf_client)

    statuses = []
    for _ in range(3):
        parallel = app.test_client()
        parallel.set_cookie("session", original)
        statuses.append(parallel.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token}).status_code)

    assert sorted(statuses) == [200, 403, 403]


def test_submit_is_forbidden_while_redis_is_down(csrf_client, broken_redis):
    """소비 기록을 남길 수 없으면 통과시키지 않는다(fail-closed).

    Redis 장애 때 통과시키면 1회용 보장이 조용히 사라진다. 이 데코레이터를 쓰는
    화면은 계정 삭제·운영자 폼이라 "두 번 실행" 이 "실행 못 함" 보다 비싸서,
    랭킹·통계처럼 폴백해서 넘기지 않고 막는 쪽을 택했다.
    """
    token = _issue(csrf_client)

    res = csrf_client.post(SUBMIT_PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"
