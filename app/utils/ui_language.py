"""UI 언어(화면 문구의 언어) 판정. 퍼즐 언어와는 다른 개념이다 (CONTEXT.md).

웹 문서 페이지(`/privacy`, `/terms`)가 쓰고, 이후 웹 프론트도 같은 규칙을 쓴다.
"""

from werkzeug.datastructures import LanguageAccept
from werkzeug.http import parse_accept_header

SUPPORTED_UI_LANGUAGES = ("ko", "en")
DEFAULT_UI_LANGUAGE = "ko"


def resolve_ui_language(lang_param: str | None, accept_language: str | None) -> str:
    """`?lang=` > Accept-Language > ko 순으로 UI 언어를 고른다.

    `?lang=` 를 먼저 보는 이유: 스토어 심사자나 앱이 특정 언어 문서를 링크로
    가리켜야 하는데, 브라우저 언어 설정에 따라 다른 문서가 나오면 안 된다.
    반환값은 항상 SUPPORTED_UI_LANGUAGES 안의 값이라 템플릿 이름에 바로 쓸 수 있다.
    """
    if lang_param:
        # "en-US", "ko_KR" 처럼 지역 꼬리표가 붙어 와도 받아준다.
        requested = lang_param.strip().lower().replace("_", "-").split("-")[0]
        if requested in SUPPORTED_UI_LANGUAGES:
            return requested

    if accept_language:
        for tag in _accepted_languages(accept_language):
            if tag in SUPPORTED_UI_LANGUAGES:
                return tag

    return DEFAULT_UI_LANGUAGE


def _accepted_languages(accept_language: str) -> list[str]:
    """Accept-Language 를 선호 순서의 주 언어 목록으로 바꾼다 (지역 꼬리표 제거).

    `LanguageAccept.best_match` 를 쓰지 않는 이유: werkzeug 는 완전 일치를 먼저 찾고
    완전 일치가 없을 때만 주 언어로 내려간다. 그래서 `en-US,ko;q=0.1` 처럼 선호 언어에
    지역 꼬리표가 붙으면, 완전 일치하는 q=0.1 의 ko 가 q=1 의 en-US 를 이겨 버린다.
    우리는 본문이 ko/en 둘뿐이라 지역 꼬리표를 구분할 일이 없으니, 꼬리표를 먼저 떼고
    q 값 순서대로 보는 게 맞다.

    파싱(q 값 해석·정렬)은 그대로 werkzeug 에 맡긴다 — 순회 순서가 q 내림차순이고,
    q 가 같으면 헤더에 적힌 순서다. q=0 은 "받지 않겠다" 는 뜻이라 버린다.
    """
    parsed = parse_accept_header(accept_language, LanguageAccept)
    return [
        tag.strip().lower().replace("_", "-").split("-")[0]
        for tag, quality in parsed
        if quality > 0
    ]
