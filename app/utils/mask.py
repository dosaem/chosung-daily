"""가림(mask) 계산 — 단어를 문제로 보여주는 방식.

한국어는 초성, 영어는 모음 빈칸이다(CONTEXT.md "가림"). 둘을 하나의 포맷으로
묶어서 클라이언트가 언어마다 다른 렌더링 코드를 갖지 않게 한다:

    [{"t": "r", "c": "P"}, {"t": "h", "c": ""}, {"t": "s", "c": " "}]

- `r`(revealed) 보이는 타일 — `c`가 화면에 찍히는 글자
- `h`(hidden)   빈 타일 — `c`는 항상 빈 문자열이다. 정답 글자를 담으면
                클라이언트가 그대로 읽어버린다
- `s`(separator) 구분자(공백·하이픈) — 타일이 아니라 타일 사이 간격이고,
                길이(`length`)에 안 들어간다

입력(언어, 정답)만으로 결과가 정해지는 순수 함수다 — 단어를 저장할 때 한 번
계산해서 `Word.mask`에 넣는다(app/models/word.py).
"""

from app.models.enums import PuzzleLanguage
from app.utils.chosung import PLACEHOLDER, syllable_chosung

REVEALED = "r"
HIDDEN = "h"
SEPARATOR = "s"

ENGLISH_VOWELS = frozenset("aeiou")
SEPARATOR_CHARS = frozenset(" -")

MaskTile = dict[str, str]


def build_mask(language: PuzzleLanguage, answer: str) -> list[MaskTile]:
    """정답 하나를 언어에 맞는 가림 타일 목록으로 바꾼다."""
    if language == PuzzleLanguage.EN:
        return [_english_tile(ch) for ch in answer]
    return [_korean_tile(ch) for ch in answer]


def mask_length(mask: list[MaskTile]) -> int:
    """플레이어에게 알려주는 글자 수. 구분자는 세지 않는다."""
    return sum(1 for tile in mask if tile["t"] != SEPARATOR)


def _english_tile(ch: str) -> MaskTile:
    if ch in SEPARATOR_CHARS:
        return {"t": SEPARATOR, "c": ch}
    if ch.lower() in ENGLISH_VOWELS:
        return {"t": HIDDEN, "c": ""}
    # 영어 정답 비교는 대소문자를 무시하므로(spec §A.2), 보이는 글자도 대문자로
    # 통일한다 — 운영자가 CSV에 "Apple"로 넣든 "apple"로 넣든 같은 화면이 된다.
    return {"t": REVEALED, "c": ch.upper()}


def _korean_tile(ch: str) -> MaskTile:
    if ch in SEPARATOR_CHARS:
        return {"t": SEPARATOR, "c": ch}
    chosung = syllable_chosung(ch)
    if chosung is None:
        # 한글이 아닌 글자(영문·숫자·기호)는 초성이 없으니 단서 없는 빈 타일이다.
        return {"t": HIDDEN, "c": ""}
    return {"t": REVEALED, "c": chosung}


def mask_to_text(mask: list[MaskTile], placeholder: str = PLACEHOLDER) -> str:
    """가림을 한 줄 문자열로 펼친다 — 보이는 타일은 글자, 빈 타일은 자리표시자.

    `GET /puzzles/today` 의 ko 호환 필드(`chosung`)를 en 퍼즐에서도 채우는 데 쓴다.
    ko 는 `Word.chosung` 컬럼의 현행 값을 그대로 쓰기 때문에 여기 오지 않는다
    (README "03. 언어 인지 응답" 참고). 자리표시자는 `extract_chosung` 과 같은
    글자를 쓴다 — 두 문자열이 같은 응답 필드를 채우니 모양도 같아야 한다.
    """
    return "".join(placeholder if tile["t"] == HIDDEN else tile["c"] for tile in mask)
