from app.utils.chosung import extract_chosung


def test_simple_word():
    assert extract_chosung("사과") == "ㅅㄱ"


def test_word_with_jongseong_batchim():
    assert extract_chosung("학교") == "ㅎㄱ"


def test_word_with_space():
    assert extract_chosung("해리 포터") == "ㅎㄹ_ㅍㅌ"


def test_word_with_english_and_digit():
    assert extract_chosung("해리potter2") == "ㅎㄹ_______"


def test_mixed_hangul_and_number_preserves_length():
    text = "9번출구"
    result = extract_chosung(text)
    assert len(result) == len(text)
    assert result == "_ㅂㅊㄱ"


def test_standalone_jamo_passthrough():
    assert extract_chosung("ㄱ자형") == "ㄱㅈㅎ"


def test_empty_string():
    assert extract_chosung("") == ""


def test_custom_placeholder():
    assert extract_chosung("ab가", placeholder="*") == "**ㄱ"
