"""웹 `/account/delete` — 확인 폼, 세션·CSRF 가드, 안 되돌릴 수 있는 삭제.

Play Data safety 의 "계정 삭제 URL" 로 제출하는 페이지라, 심사자가 로그인 없이
열어도 뭘 해야 하는지 보여야 하고(안내 + 운영자 메일), 로그인된 세션에서는 한
번의 확인으로 실제로 지워져야 한다.

세션은 실제 흐름(`POST /api/v1/session/sync`)으로 심는다 — `session` 을 직접
조작하면 "토큰 없이 쿠키만 만들어도 지워지는지" 를 못 본다.
"""

import pytest

from app.csrf import CSRF_FORM_FIELD
from app.extensions import db
from app.models import Guest

PATH = "/account/delete"
EN_HEADERS = {"Accept-Language": "en-US,en;q=0.9"}
KO_HEADERS = {"Accept-Language": "ko-KR,ko;q=0.9"}

# 개인정보처리방침 "수집하는 정보" 절(`legal/privacy.*.html` `id="collection"`)의 항목 이름.
# 삭제 확인 페이지가 지우는 데이터를 **같은 이름** 으로 보여줘야 한다(티켓 14) —
# 방침과 다른 말로 적으면 두 문서가 서로 다른 약속을 하는 셈이 된다.
COLLECTED_NAMES = {
    "ko": ["게스트 토큰", "계정 이메일", "애플 refresh token", "시도 기록", "구독 식별자"],
    "en": [
        "Guest token",
        "Account email",
        "Apple refresh token",
        "Attempt history",
        "Subscription identifier",
    ],
}


@pytest.fixture
def logged_in_client(client, web_login):
    """세션 쿠키에 게스트가 심어진 브라우저와 그 게스트.

    세션은 공용 `web_login` 픽스처(conftest)가 실제 흐름
    (`POST /api/v1/session/sync`)으로 심는다 — 운영자 페이지 테스트와 같은 길이다.
    """
    return client, web_login()


def _html(client, path=PATH, **kwargs):
    res = client.get(path, **kwargs)
    assert res.status_code == 200
    return res.data.decode()


def _form_token(html: str) -> str:
    marker = f'name="{CSRF_FORM_FIELD}" value="'
    start = html.index(marker) + len(marker)
    return html[start : html.index('"', start)]


# --- 로그인 안 된 브라우저 -------------------------------------------------


def test_page_without_a_session_explains_how_to_delete(client, app):
    html = _html(client)

    assert f"mailto:{app.config['LEGAL_CONTACT_EMAIL']}" in html
    # 폼이 없어야 한다 — 누를 수 있는 삭제 버튼이 보이면 안내가 아니라 고장이다.
    assert f'name="{CSRF_FORM_FIELD}"' not in html
    assert "<form" not in html


def test_page_without_a_session_still_renders_in_english(client):
    html = _html(client, headers=EN_HEADERS)

    assert '<html lang="en">' in html
    assert "log in" in html.lower()


# --- 확인 폼 ---------------------------------------------------------------


def test_confirm_form_warns_that_deletion_is_permanent(logged_in_client):
    client, _ = logged_in_client

    html = _html(client)

    assert "되돌릴 수 없" in html
    # 구독은 서버가 해지할 수 없다 — 스토어에서 따로 해지해야 결제가 멈춘다.
    assert "App Store" in html
    assert "Google Play" in html
    assert "해지" in html


def test_confirm_form_warns_in_english_too(logged_in_client):
    client, _ = logged_in_client

    html = _html(client, headers=EN_HEADERS)

    assert '<html lang="en">' in html
    assert "cannot be undone" in html
    assert "App Store" in html
    assert "Google Play" in html
    assert "cancel" in html.lower()


@pytest.mark.parametrize("language", ["ko", "en"])
def test_confirm_form_lists_the_data_with_the_privacy_policy_names(logged_in_client, language):
    client, _ = logged_in_client

    html = _html(client, f"{PATH}?lang={language}")

    for name in COLLECTED_NAMES[language]:
        assert name in html, f"{language} 목록에 '{name}' 이 없다"


@pytest.mark.parametrize("language", ["ko", "en"])
def test_confirm_form_links_the_policy_retention_and_rights_sections(logged_in_client, language):
    """방침의 "수집하는 정보·보유 기간" 절과 "정보주체의 권리" 절로 바로 갈 수 있어야 한다."""
    client, _ = logged_in_client

    html = _html(client, f"{PATH}?lang={language}")

    assert f"/privacy?lang={language}#collection" in html
    assert f"/privacy?lang={language}#rights" in html


@pytest.mark.parametrize("language", ["ko", "en"])
def test_policy_has_the_anchors_the_delete_page_links_to(client, language):
    """링크만 있고 앵커가 없으면 문서 맨 위로 떨어진다 — 양쪽을 같이 고정한다."""
    html = _html(client, f"/privacy?lang={language}")

    assert 'id="collection"' in html
    assert 'id="rights"' in html


def test_confirm_form_posts_to_the_same_url_with_a_csrf_token(logged_in_client):
    client, _ = logged_in_client

    html = _html(client)

    assert f'action="{PATH}"' in html
    assert 'method="post"' in html
    assert len(_form_token(html)) >= 32


def test_each_render_issues_a_fresh_token(logged_in_client):
    client, _ = logged_in_client

    assert _form_token(_html(client)) != _form_token(_html(client))


def test_get_never_deletes_anything(logged_in_client):
    """GET 은 상태를 바꾸지 않는다(스펙 §A.7) — 크롤러·프리페치가 계정을 지우면 안 된다."""
    client, guest = logged_in_client
    guest_id = guest.id

    _html(client)
    _html(client, f"{PATH}?lang=en")

    assert db.session.get(Guest, guest_id) is not None


def test_page_declares_its_language(logged_in_client):
    client, _ = logged_in_client

    assert client.get(PATH).headers["Content-Language"] == "ko"
    assert client.get(f"{PATH}?lang=en").headers["Content-Language"] == "en"


def test_lang_query_beats_accept_language(logged_in_client):
    client, _ = logged_in_client

    assert '<html lang="en">' in _html(client, f"{PATH}?lang=en", headers=KO_HEADERS)
    assert '<html lang="ko">' in _html(client, f"{PATH}?lang=ko", headers=EN_HEADERS)


# --- 삭제 제출 -------------------------------------------------------------


def test_submitting_the_form_deletes_the_account_and_sends_the_browser_home(logged_in_client):
    client, guest = logged_in_client
    guest_id = guest.id
    token = _form_token(_html(client))

    res = client.post(PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 302
    # 프론트가 이 쿼리를 보고 localStorage 토큰을 버리고 새 게스트를 받는다.
    assert res.headers["Location"] == "/?deleted=1"
    assert db.session.get(Guest, guest_id) is None


def test_session_is_emptied_so_the_next_page_is_a_fresh_visitor(logged_in_client):
    client, _ = logged_in_client
    token = _form_token(_html(client))

    client.post(PATH, data={CSRF_FORM_FIELD: token})

    # 세션이 남아 있으면 지워진 게스트 id 를 들고 확인 폼이 또 뜬다.
    html = _html(client)
    assert f'name="{CSRF_FORM_FIELD}"' not in html


def test_post_without_a_session_is_unauthorized(client):
    """로그인 안 된 브라우저의 제출은 403(폼 위조)이 아니라 401 이다 — 세션 확인이
    CSRF 검증보다 먼저다(스펙 §A.7)."""
    res = client.post(PATH, data={CSRF_FORM_FIELD: "아무-값"})

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_post_from_a_second_tab_after_deletion_is_unauthorized(app, logged_in_client):
    """같은 세션을 들고 있는 두 번째 탭. 첫 탭이 지운 뒤의 제출은 401 이다.

    서명 쿠키 세션은 상태가 전부 클라이언트에 있어서 `session.clear()` 가 다른
    탭이 들고 있는 쿠키를 지우지 못한다 — 가드가 "세션에 적힌 게스트가 지금도
    있는가" 까지 봐야 한다.
    """
    client, guest = logged_in_client
    second_tab = app.test_client()
    second_tab.set_cookie("session", client.get_cookie("session").value)
    stale_token = _form_token(_html(second_tab))

    assert client.post(PATH, data={CSRF_FORM_FIELD: _form_token(_html(client))}).status_code == 302

    res = second_tab.post(PATH, data={CSRF_FORM_FIELD: stale_token})

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"
    _ = guest


def test_post_with_a_wrong_csrf_token_is_forbidden(logged_in_client):
    client, guest = logged_in_client
    _html(client)  # 토큰을 발급해 두고 다른 값을 제출한다
    guest_id = guest.id

    res = client.post(PATH, data={CSRF_FORM_FIELD: "같지-않은-값"})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"
    assert db.session.get(Guest, guest_id) is not None


def test_post_without_a_csrf_token_is_forbidden(logged_in_client):
    client, guest = logged_in_client
    _html(client)
    guest_id = guest.id

    res = client.post(PATH, data={})

    assert res.status_code == 403
    assert db.session.get(Guest, guest_id) is not None


def test_replaying_the_form_cannot_delete_a_second_time(logged_in_client):
    """브라우저·프록시가 들고 있던 옛 쿠키로 같은 제출을 되돌려도 다시 안 돈다.

    가드 둘이 각각 막는다: 세션이 가리키는 게스트가 이미 없고(401), 설령
    살아 있었어도 토큰은 1회용이라 소비돼 있다(티켓 01, `tests/test_csrf.py`).
    """
    client, _ = logged_in_client
    token = _form_token(_html(client))
    original_cookie = client.get_cookie("session").value

    assert client.post(PATH, data={CSRF_FORM_FIELD: token}).status_code == 302

    client.set_cookie("session", original_cookie)
    assert client.post(PATH, data={CSRF_FORM_FIELD: token}).status_code == 401


def test_a_form_rendered_for_another_guest_is_refused_after_a_session_switch(client, web_login):
    """D-14-2: 확인 폼은 **그릴 때 본 게스트** 만 지운다.

    한 탭에 A 의 삭제 확인 화면을 띄워 둔 채 다른 탭에서 백업 코드를 복원하거나
    계정을 전환하면(= 세션이 B 를 가리킨다) 옛 탭의 버튼은 B 를 지우게 된다.
    CSRF 토큰은 "이 폼을 우리가 그려줬다" 만 증명하고 "누구를 지우는 폼인가" 는
    증명하지 않기 때문이다. 그래서 둘 다 요구한다.
    """
    first_id = web_login().id
    token = _form_token(_html(client))

    second_id = web_login().id  # 같은 브라우저가 다른 게스트로 전환

    res = client.post(PATH, data={CSRF_FORM_FIELD: token})

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"
    assert db.session.get(Guest, first_id) is not None
    assert db.session.get(Guest, second_id) is not None


def test_the_switched_guest_can_delete_itself_from_a_freshly_rendered_form(client, web_login):
    """전환 뒤 화면을 다시 받으면 그 게스트는 정상적으로 지워진다(위 거부가 막는
    건 "옛 폼" 뿐이다)."""
    web_login()
    _html(client)

    switched_id = web_login().id
    token = _form_token(_html(client))

    assert client.post(PATH, data={CSRF_FORM_FIELD: token}).status_code == 302
    assert db.session.get(Guest, switched_id) is None
