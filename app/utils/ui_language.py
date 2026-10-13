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
        # q 값 정렬·지역 꼬리표 매칭은 werkzeug 가 이미 한다.
        best = parse_accept_header(accept_language, LanguageAccept).best_match(
            SUPPORTED_UI_LANGUAGES
        )
        if best:
            return best

    return DEFAULT_UI_LANGUAGE
