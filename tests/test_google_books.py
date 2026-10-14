"""Google Books 래퍼(app/clients/google_books.py)와 그 위의 서비스 함수.

네트워크 호출은 전부 가짜 `requests.get` 으로 대체한다 — 실제 API 를 때리면
테스트가 쿼터·네트워크에 묶이고, 응답 내용도 그날 구글 색인에 따라 달라진다
(tests/test_slack_client.py 와 같은 방식).
"""

import json

import pytest
import requests

from app.clients import google_books
from app.services.book_lookup_service import search_books, search_google_books

ONE_VOLUME = {
    "items": [
        {
            "volumeInfo": {
                "title": "The Hobbit",
                "authors": ["J. R. R. Tolkien"],
                "publisher": "Houghton Mifflin",
                "industryIdentifiers": [
                    {"type": "ISBN_10", "identifier": "0395071224"},
                    {"type": "ISBN_13", "identifier": "9780395071229"},
                ],
            }
        }
    ]
}


class _RecordingGet:
    """requests.get 대역. 호출 인자를 기록하고 정해둔 JSON/예외를 돌려준다."""

    def __init__(self, payload=None, status_code=200, raises=None):
        self.calls = []
        self._payload = payload if payload is not None else {}
        self._status_code = status_code
        self._raises = raises

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = self._status_code
        response.url = url
        response._content = json.dumps(self._payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response


@pytest.fixture
def fake_get(monkeypatch):
    def _install(payload=None, status_code=200, raises=None):
        get = _RecordingGet(payload=payload, status_code=status_code, raises=raises)
        monkeypatch.setattr(google_books.requests, "get", get)
        return get

    return _install


# --- 래퍼 ----------------------------------------------------------------


def test_the_wrapper_searches_titles_only_and_asks_for_english_books(app, fake_get):
    get = fake_get(ONE_VOLUME)

    google_books.search_volumes("hobbit", size=3)

    (url, kwargs) = get.calls[0]
    assert url == google_books.VOLUMES_URL
    # 제목 검색이다 — `intitle:` 없이 보내면 본문·저자까지 걸려서 "책 제목 단어"
    # 와 상관없는 결과가 섞인다.
    assert kwargs["params"]["q"] == "intitle:hobbit"
    assert kwargs["params"]["maxResults"] == 3
    assert kwargs["params"]["langRestrict"] == "en"
    assert kwargs["timeout"] == google_books.TIMEOUT_SECONDS


def test_the_api_key_is_sent_only_when_it_is_configured(app, fake_get):
    get = fake_get(ONE_VOLUME)

    app.config["GOOGLE_BOOKS_API_KEY"] = ""
    google_books.search_volumes("hobbit")
    assert "key" not in get.calls[-1][1]["params"]

    app.config["GOOGLE_BOOKS_API_KEY"] = "test-books-key"
    google_books.search_volumes("hobbit")
    assert get.calls[-1][1]["params"]["key"] == "test-books-key"


def test_an_empty_result_set_comes_back_as_an_empty_list(app, fake_get):
    fake_get({"kind": "books#volumes", "totalItems": 0})

    assert google_books.search_volumes("zzzz") == []


def test_an_http_error_is_raised_to_the_caller(app, fake_get):
    fake_get(ONE_VOLUME, status_code=503)

    with pytest.raises(requests.HTTPError):
        google_books.search_volumes("hobbit")


# --- 서비스 함수 ----------------------------------------------------------


def test_results_are_mapped_to_the_same_shape_as_the_kakao_search(app, fake_get):
    fake_get(ONE_VOLUME)

    [book] = search_google_books("hobbit")

    assert book.title == "The Hobbit"
    assert book.author == "J. R. R. Tolkien"
    assert book.publisher == "Houghton Mifflin"
    # ISBN_13 이 있으면 그걸 쓴다 — 두 길이가 섞여 들어오면 긴 쪽이 표준이다.
    assert book.isbn == "9780395071229"
    assert book.source == "google_books"


def test_a_volume_without_a_title_is_skipped(app, fake_get):
    fake_get({"items": [{"volumeInfo": {"authors": ["무제"]}}, ONE_VOLUME["items"][0]]})

    titles = [book.title for book in search_google_books("hobbit")]

    assert titles == ["The Hobbit"]


def test_missing_fields_become_none(app, fake_get):
    fake_get({"items": [{"volumeInfo": {"title": "Untitled Sequel"}}]})

    [book] = search_google_books("untitled")

    assert (book.author, book.publisher, book.isbn) == (None, None, None)


def test_an_isbn_10_is_used_when_there_is_no_isbn_13(app, fake_get):
    fake_get(
        {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Old Print",
                        "industryIdentifiers": [
                            {"type": "ISBN_10", "identifier": "0123456789"}
                        ],
                    }
                }
            ]
        }
    )

    [book] = search_google_books("old print")

    assert book.isbn == "0123456789"


def test_the_kakao_and_aladin_search_is_left_alone(app, fake_get, monkeypatch):
    """`search_books` 는 ko 소스(카카오·알라딘) 합성이다 — 영어 전용 소스를 섞으면
    `flask search-books` 가 ko 단어 풀에 영어 책을 넣는다."""
    get = fake_get(ONE_VOLUME)
    # 키가 없으면 두 ko 소스는 호출 없이 빈 결과다 — 이 테스트가 보는 건
    # "구글이 그 합성에 끼어들지 않는다" 뿐이라, 머신 환경과 무관하게 비워둔다.
    monkeypatch.setenv("KAKAO_REST_API_KEY", "")
    monkeypatch.setenv("ALADIN_TTB_KEY", "")

    assert search_books("hobbit") == []
    assert get.calls == []
