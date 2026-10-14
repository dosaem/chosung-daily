"""운영자 책 검색 페이지(`/admin/books`) — Google Books 검색 → en 단어 추가.

구글 호출은 가짜 `requests.get` 으로 대체한다(tests/test_google_books.py 와 같은
방식) — 실제 API 를 때리면 테스트가 쿼터·색인 변화에 묶인다.
"""

import json
import re

import pytest
import requests

from app.clients import google_books
from app.models import PuzzleLanguage, Word, WordCategory

CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')

HOBBIT = {
    "volumeInfo": {
        "title": "The Hobbit",
        "authors": ["J. R. R. Tolkien"],
        "publisher": "Houghton Mifflin",
        "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780395071229"}],
    }
}


class _FakeGet:
    def __init__(self, payload, raises=None):
        self.calls = []
        self._payload = payload
        self._raises = raises

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response._content = json.dumps(self._payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response


@pytest.fixture
def google_results(monkeypatch):
    def _install(items, raises=None):
        get = _FakeGet({"items": items}, raises=raises)
        monkeypatch.setattr(google_books.requests, "get", get)
        return get

    return _install


def _token(client, path="/admin/books"):
    html = client.get(path).get_data(as_text=True)
    match = CSRF_PATTERN.search(html)
    assert match, f"{path} 에 csrf_token hidden 이 없다"
    return match.group(1)


# --- 검색 ----------------------------------------------------------------


def test_the_books_page_opens_without_a_search(admin_session, google_results):
    get = google_results([HOBBIT])

    html = admin_session.get("/admin/books").get_data(as_text=True)

    assert "책 제목 검색" in html
    # 검색어가 없으면 구글을 부르지 않는다 — 빈 폼을 여는 것만으로 쿼터를 쓰지 않게.
    assert get.calls == []


def test_a_search_lists_the_results(admin_session, google_results):
    google_results([HOBBIT])

    html = admin_session.get("/admin/books?q=hobbit").get_data(as_text=True)

    assert "The Hobbit" in html
    assert "J. R. R. Tolkien" in html


def test_a_search_with_no_result_says_so(admin_session, google_results):
    google_results([])

    html = admin_session.get("/admin/books?q=zzzzz").get_data(as_text=True)

    assert "결과가 없" in html


def test_a_google_failure_is_shown_as_a_reason(admin_session, google_results):
    google_results([], raises=requests.ConnectionError("boom"))

    res = admin_session.get("/admin/books?q=hobbit")

    assert res.status_code == 200
    assert "검색에 실패" in res.get_data(as_text=True)


def test_the_books_page_needs_an_admin_session(client):
    assert client.get("/admin/books").status_code == 302


# --- 추가 ----------------------------------------------------------------


def test_choosing_a_result_adds_an_english_book_title_word(admin_session, google_results):
    google_results([HOBBIT])

    res = admin_session.post(
        "/admin/books",
        data={
            "csrf_token": _token(admin_session, "/admin/books?q=hobbit"),
            "title": "The Hobbit",
            "author": "J. R. R. Tolkien",
            "publisher": "Houghton Mifflin",
        },
    )

    assert res.status_code == 302
    word = Word.query.one()
    assert word.answer == "The Hobbit"
    assert word.language is PuzzleLanguage.EN
    assert word.category is WordCategory.BOOK_TITLE
    assert word.hint == "J. R. R. Tolkien, Houghton Mifflin"


def test_the_mask_is_computed_when_the_word_is_added(admin_session, google_results):
    google_results([HOBBIT])

    admin_session.post(
        "/admin/books",
        data={
            "csrf_token": _token(admin_session, "/admin/books?q=hobbit"),
            "title": "Dune",
            "author": "Frank Herbert",
        },
    )

    word = Word.query.one()
    # en 은 모음을 가린다 — D u n e → 보임/빈칸/보임/빈칸.
    assert [tile["t"] for tile in word.mask] == ["r", "h", "r", "h"]


def test_adding_the_same_book_twice_does_not_duplicate_it(admin_session, google_results):
    google_results([HOBBIT])
    for _ in range(2):
        admin_session.post(
            "/admin/books",
            data={
                "csrf_token": _token(admin_session, "/admin/books?q=hobbit"),
                "title": "The Hobbit",
                "author": "J. R. R. Tolkien",
            },
        )

    assert Word.query.count() == 1


def test_a_title_longer_than_the_answer_column_is_refused(admin_session, google_results):
    google_results([HOBBIT])

    res = admin_session.post(
        "/admin/books",
        data={
            "csrf_token": _token(admin_session, "/admin/books?q=hobbit"),
            "title": "T" * 51,
            "author": "누군가",
        },
        follow_redirects=True,
    )

    assert "정답이 너무 깁니다" in res.get_data(as_text=True)
    assert Word.query.count() == 0


def test_a_book_without_an_author_gets_a_fallback_hint(admin_session, google_results):
    google_results([HOBBIT])

    admin_session.post(
        "/admin/books",
        data={
            "csrf_token": _token(admin_session, "/admin/books?q=hobbit"),
            "title": "Beowulf",
        },
    )

    assert Word.query.one().hint == "책 제목"


def test_adding_without_a_csrf_token_is_forbidden(admin_session, google_results):
    google_results([HOBBIT])

    res = admin_session.post("/admin/books", data={"title": "The Hobbit"})

    assert res.status_code == 403
    assert Word.query.count() == 0
