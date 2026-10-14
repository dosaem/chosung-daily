"""Google Books API 래퍼 — 외부 호출 한 곳(README "01. 외부 호출 래퍼와 도메인
판정 함수의 분리").

이 모듈이 아는 건 "HTTP 로 어떻게 묻나" 뿐이고, 응답을 `BookSearchResult` 로
바꾸는 건 `app/services/book_lookup_service.py` 가 한다 — 카카오·알라딘과 같은
층에서 같은 모양으로 쓰이게.
"""

import requests
from flask import current_app

VOLUMES_URL = "https://www.googleapis.com/books/v1/volumes"

# 운영자가 폼 앞에서 기다리는 호출이다. 구글이 느릴 때 운영자 화면이 통째로
# 멈추지 않게 짧게 끊는다(카카오·알라딘 검색과 같은 5초).
TIMEOUT_SECONDS = 5


def search_volumes(query: str, size: int = 5) -> list[dict]:
    """제목으로 영어 책을 찾아 volume 목록(원본 JSON)을 돌려준다.

    `GOOGLE_BOOKS_API_KEY` 는 **선택**이다(스펙 미정 3). 공개 volume 검색은 키
    없이도 되고 키는 쿼터를 IP 가 아니라 프로젝트에 붙이는 역할이라, 키가 없으면
    그냥 안 보낸다 — 카카오·알라딘처럼 "키 없으면 빈 결과" 로 막지 않는다.

    HTTP 오류는 그대로 올린다(`raise_for_status`) — 운영자 화면이 "검색 실패" 를
    보여줄 수 있어야 하고, 빈 결과로 둥글리면 "그 책이 없다" 와 구분이 안 된다.
    """
    params = {
        # intitle: 없이 보내면 본문·저자까지 걸려서 제목 단어 풀에 쓸 수 없는
        # 결과가 섞인다.
        "q": f"intitle:{query}",
        "maxResults": size,
        "printType": "books",
        "langRestrict": "en",
    }
    api_key = current_app.config["GOOGLE_BOOKS_API_KEY"]
    if api_key:
        params["key"] = api_key

    response = requests.get(VOLUMES_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json().get("items", [])
