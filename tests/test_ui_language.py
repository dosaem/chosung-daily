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
    ],
)
def test_resolve_ui_language(lang_param, accept_language, expected):
    assert resolve_ui_language(lang_param, accept_language) == expected
