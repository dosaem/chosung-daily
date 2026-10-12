"""OAuth 로그인은 실제 구글/카카오 콘솔에 앱을 등록하기 전까진 끝까지
테스트할 수 없다(authorize_access_token이 실제 provider와 통신함). 여기선
그 전 단계 — 라우팅/가드 로직과 세션 동기화(로그인 CSRF 방어)만 검증한다.
실제 로그인 왕복은 콘솔 등록 후 수동으로 확인해야 한다.
"""


def test_login_rejects_unsupported_provider(client):
    res = client.get("/api/v1/auth/naver/login")

    assert res.status_code == 404
    assert res.get_json()["code"] == "NOT_FOUND"


def test_login_without_synced_session_is_unauthorized(client, guest_headers):
    # session/sync를 안 부르고 바로 로그인 시도 — 세션 쿠키가 없으니 막혀야 한다.
    res = client.get("/api/v1/auth/google/login")

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_login_csrf_cannot_be_forged_via_query_param(client, guest_headers):
    """예전엔 /login?token=<아무 게스트 토큰>으로 어느 게스트에 연결할지 정할 수
    있었다 — 공격자가 자기 토큰을 넣은 링크를 피해자에게 보내서 피해자가 로그인을
    완료하면 피해자 계정이 공격자 게스트에 묶이는 로그인 CSRF가 가능했다(보안
    리뷰로 발견, 수정함). 지금은 그 쿼리파라미터를 아예 안 읽으니, 넣어도 무시돼야
    (= 세션 동기화 없이는 여전히 401) 한다.
    """
    res = client.get(f"/api/v1/auth/google/login?token={guest_headers['Authorization']}")

    assert res.status_code == 401


def test_sync_then_login_redirects_to_provider(client, guest_headers):
    sync_res = client.post("/api/v1/session/sync", headers=guest_headers)
    assert sync_res.status_code == 200

    res = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert res.status_code == 302
    assert "accounts.google.com" in res.headers["Location"]


def test_sync_requires_auth(client):
    res = client.post("/api/v1/session/sync")

    assert res.status_code == 401


def test_callback_without_pending_session_is_unauthorized(client):
    res = client.get("/api/v1/auth/google/callback")

    assert res.status_code == 401
