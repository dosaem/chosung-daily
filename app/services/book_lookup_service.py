import os

import requests

from app.clients.google_books import search_volumes
from app.schemas.book import BookSearchResult

KAKAO_BOOK_SEARCH_URL = "https://dapi.kakao.com/v3/search/book"
ALADIN_ITEM_SEARCH_URL = "http://www.aladin.co.kr/ttb/api/ItemSearch.aspx"


def search_kakao_books(query: str, size: int = 5) -> list[BookSearchResult]:
    api_key = os.environ.get("KAKAO_REST_API_KEY")
    if not api_key:
        return []

    res = requests.get(
        KAKAO_BOOK_SEARCH_URL,
        headers={"Authorization": f"KakaoAK {api_key}"},
        params={"query": query, "size": size, "target": "title"},
        timeout=5,
    )
    res.raise_for_status()
    documents = res.json().get("documents", [])
    return [
        BookSearchResult(
            title=doc["title"],
            author=", ".join(doc.get("authors", [])) or None,
            publisher=doc.get("publisher") or None,
            isbn=doc.get("isbn") or None,
            source="kakao",
        )
        for doc in documents
    ]


def search_aladin_books(query: str, size: int = 5) -> list[BookSearchResult]:
    """알라딘 Open API 검색. 공식 문서에 output=js 응답의 전체 JSON 스키마가
    명시돼 있지 않아서(2007년 작성 문서, 예시 파일 링크만 제공), 커뮤니티에
    널리 알려진 필드명(title/author/publisher/isbn13)을 기준으로 구현했다.
    실제 TTBKey로 처음 호출해보고 필드명이 다르면 여기를 고치면 된다.
    """
    ttb_key = os.environ.get("ALADIN_TTB_KEY")
    if not ttb_key:
        return []

    res = requests.get(
        ALADIN_ITEM_SEARCH_URL,
        params={
            "ttbkey": ttb_key,
            "Query": query,
            "QueryType": "Title",
            "SearchTarget": "Book",
            "MaxResults": size,
            "output": "js",
            "Version": "20131101",
        },
        timeout=5,
    )
    res.raise_for_status()
    items = res.json().get("item", [])
    return [
        BookSearchResult(
            title=item["title"],
            author=item.get("author"),
            publisher=item.get("publisher"),
            isbn=item.get("isbn13") or item.get("isbn"),
            source="aladin",
        )
        for item in items
    ]


def search_google_books(query: str, size: int = 5) -> list[BookSearchResult]:
    """Google Books 로 영어 책 제목을 찾는다. 카카오 검색과 같은 시그니처다
    (스펙 §A.14) — 운영자 화면이 소스마다 다른 호출 방식을 알 필요가 없다.

    제목이 없는 volume 은 버린다 — 정답이 될 글자가 없으면 단어로 쓸 수 없다.
    """
    books = []
    for item in search_volumes(query, size):
        info = item.get("volumeInfo", {})
        title = (info.get("title") or "").strip()
        if not title:
            continue
        books.append(
            BookSearchResult(
                title=title,
                author=", ".join(info.get("authors", [])) or None,
                publisher=info.get("publisher") or None,
                isbn=_pick_isbn(info.get("industryIdentifiers", [])),
                source="google_books",
            )
        )
    return books


def _pick_isbn(identifiers: list[dict]) -> str | None:
    """ISBN_13 우선, 없으면 ISBN_10. 둘 다 없으면 None(구글은 자체 식별자만 주는
    volume 도 있다)."""
    by_type = {entry.get("type"): entry.get("identifier") for entry in identifiers}
    return by_type.get("ISBN_13") or by_type.get("ISBN_10")


def search_books(query: str, size: int = 5) -> list[BookSearchResult]:
    """설정된 ko 소스(카카오/알라딘)를 모두 조회해서 합친다. 키가 없는 소스는 조용히
    건너뛴다. Google Books 는 영어 전용이라 여기 섞지 않는다 — `flask search-books`
    는 ko 단어 풀을 채우는 명령이고, 운영자 화면의 영어 검색은
    `search_google_books` 를 따로 부른다."""
    return search_kakao_books(query, size) + search_aladin_books(query, size)
