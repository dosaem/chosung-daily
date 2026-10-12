import os

import requests

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


def search_books(query: str, size: int = 5) -> list[BookSearchResult]:
    """설정된 소스(카카오/알라딘)를 모두 조회해서 합친다. 키가 없는 소스는 조용히 건너뛴다."""
    return search_kakao_books(query, size) + search_aladin_books(query, size)
