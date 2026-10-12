HANGUL_BASE = 0xAC00
HANGUL_LAST = 0xD7A3
JUNGSUNG_COUNT = 21
JONGSUNG_COUNT = 28

CHOSUNG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]

PLACEHOLDER = "_"


def extract_chosung(text: str, placeholder: str = PLACEHOLDER) -> str:
    """완성형 한글 음절 각각을 초성 하나로 바꾼다.

    한글 음절이 아닌 문자(공백, 영문, 숫자, 기타 기호)는 자리표시자로 치환해서
    결과 문자열 길이가 입력 글자 수와 항상 같게 유지한다. 독립 자음(호환 자모,
    예: "ㄱ")은 이미 초성이므로 그대로 둔다.
    """
    result = []
    for ch in text:
        code = ord(ch)
        if HANGUL_BASE <= code <= HANGUL_LAST:
            chosung_index = (code - HANGUL_BASE) // (JUNGSUNG_COUNT * JONGSUNG_COUNT)
            result.append(CHOSUNG_LIST[chosung_index])
        elif ch in CHOSUNG_LIST:
            result.append(ch)
        else:
            result.append(placeholder)
    return "".join(result)
