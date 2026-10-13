HANGUL_BASE = 0xAC00
HANGUL_LAST = 0xD7A3
JUNGSUNG_COUNT = 21
JONGSUNG_COUNT = 28

CHOSUNG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]

PLACEHOLDER = "_"


def syllable_chosung(ch: str) -> str | None:
    """글자 하나의 초성을 돌려준다. 초성을 뽑을 수 없는 글자면 None.

    완성형 한글 음절은 첫 자음으로, 독립 자음(호환 자모, 예: "ㄱ")은 이미 초성이라
    그대로 둔다. 공백·영문·숫자·기호는 None — 부르는 쪽이 그걸 어떻게 보여줄지
    정한다(`extract_chosung`은 자리표시자, `app/utils/mask.py`는 빈 타일/구분자).
    """
    code = ord(ch)
    if HANGUL_BASE <= code <= HANGUL_LAST:
        return CHOSUNG_LIST[(code - HANGUL_BASE) // (JUNGSUNG_COUNT * JONGSUNG_COUNT)]
    if ch in CHOSUNG_LIST:
        return ch
    return None


def extract_chosung(text: str, placeholder: str = PLACEHOLDER) -> str:
    """완성형 한글 음절 각각을 초성 하나로 바꾼다.

    한글 음절이 아닌 문자(공백, 영문, 숫자, 기타 기호)는 자리표시자로 치환해서
    결과 문자열 길이가 입력 글자 수와 항상 같게 유지한다.

    `Word.chosung` 컬럼(ko 응답 호환용)을 채우는 데만 쓴다. 언어가 들어간 뒤의
    가림은 `app/utils/mask.py`의 `build_mask`가 담당한다.
    """
    return "".join(syllable_chosung(ch) or placeholder for ch in text)
