import pytest

from app.utils.ui_language import resolve_ui_language


@pytest.mark.parametrize(
    ("lang_param", "accept_language", "expected"),
    [
        # ?lang= 가 가장 세다
        ("en", "ko-KR,ko;q=0.9", "en"),
        ("ko", "en-US,en;q=0.9", "ko"),
        # 지역 꼬리표는 떼고 본다
        ("en-US", None, "en"),
        ("KO-kr", None, "ko"),
        # ?lang= 가 없거나 지원하지 않는 값이면 Accept-Language 로 내려간다
        (None, "en-US,en;q=0.9", "en"),
        ("", "en-US,en;q=0.9", "en"),
        ("fr", "en-US,en;q=0.9", "en"),
        ("kor", "en-US,en;q=0.9", "en"),
        # 둘 다 없거나 못 고르면 ko
        (None, None, "ko"),
        (None, "", "ko"),
        (None, "fr-FR,de;q=0.8", "ko"),
        # q 값이 높은 쪽을 고른다
        (None, "fr;q=1.0,en;q=0.8,ko;q=0.2", "en"),
        # 지역 꼬리표가 붙은 선호 언어가 q 값이 낮은 완전 일치보다 세다 (D-09-2).
        # werkzeug 의 best_match 는 완전 일치를 먼저 찾아서 여기서 뒤집혔다.
        (None, "en-US,ko;q=0.1", "en"),
        (None, "ko-KR,en;q=0.1", "ko"),
        (None, "en-GB,ko;q=0.5", "en"),
        (None, "ko_KR,en;q=0.5", "ko"),
        # q=0 은 "받지 않겠다" 는 뜻이라 고르지 않는다
        (None, "en;q=0,ko;q=0.5", "ko"),
        (None, "ko;q=0,en;q=0.3", "en"),
        (None, "ko;q=0", "ko"),  # 남는 후보가 없으면 기본값
        # 와일드카드만 오면 기본값
        (None, "*", "ko"),
    ],
)
def test_resolve_ui_language(lang_param, accept_language, expected):
    assert resolve_ui_language(lang_param, accept_language) == expected
