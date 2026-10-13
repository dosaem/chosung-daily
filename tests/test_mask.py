"""가림(mask) 순수 함수 테스트.

가림은 "단어를 문제로 보여주는 방식"이다(CONTEXT.md) — 한국어는 초성, 영어는
모음 빈칸. 입력(언어, 정답)만으로 결과가 정해지는 순수 함수라, DB·Redis 없이
여기서 전부 검증한다.
"""

import pytest

from app.models.enums import PuzzleLanguage
from app.utils.chosung import extract_chosung
from app.utils.mask import (
    HIDDEN,
    REVEALED,
    SEPARATOR,
    build_mask,
    mask_length,
    mask_to_text,
)


def render(mask: list[dict[str, str]]) -> str:
    """빈 타일을 `_`로 찍어 사람이 읽을 수 있는 한 줄로 만든다 (테스트 가독성용)."""
    return "".join(tile["c"] if tile["c"] else "_" for tile in mask)


def kinds(mask: list[dict[str, str]]) -> str:
    return "".join(tile["t"] for tile in mask)


# --- 영어: 모음 빈칸 ---------------------------------------------------------


def test_english_hides_vowels():
    mask = build_mask(PuzzleLanguage.EN, "apple")

    assert render(mask) == "_PPL_"
    assert kinds(mask) == "hrrrh"
    assert mask_length(mask) == 5


def test_english_uppercase_input_gives_same_mask_as_lowercase():
    assert build_mask(PuzzleLanguage.EN, "APPLE") == build_mask(PuzzleLanguage.EN, "apple")


def test_english_space_is_separator_and_not_counted_in_length():
    mask = build_mask(PuzzleLanguage.EN, "harry potter")

    assert kinds(mask) == "rhrrrsrhrrhr"
    assert mask[5] == {"t": SEPARATOR, "c": " "}
    assert mask_length(mask) == 11  # 공백 1개 제외


def test_english_hyphen_is_separator():
    mask = build_mask(PuzzleLanguage.EN, "spider-man")

    assert mask[6] == {"t": SEPARATOR, "c": "-"}
    assert kinds(mask) == "rrhrhrsrhr"
    assert mask_length(mask) == 9


def test_english_hidden_tile_never_carries_the_answer_letter():
    """빈 타일에 정답 글자를 담으면 클라이언트가 그대로 읽어버린다."""
    mask = build_mask(PuzzleLanguage.EN, "apple")

    assert [tile["c"] for tile in mask if tile["t"] == HIDDEN] == ["", ""]


def test_english_digit_is_revealed():
    mask = build_mask(PuzzleLanguage.EN, "catch22")

    assert render(mask) == "C_TCH22"
    assert kinds(mask) == "rhrrrrr"


# --- 한국어: 초성 -----------------------------------------------------------


def test_korean_reveals_chosung_of_each_syllable():
    mask = build_mask(PuzzleLanguage.KO, "사과")

    assert mask == [{"t": REVEALED, "c": "ㅅ"}, {"t": REVEALED, "c": "ㄱ"}]
    assert mask_length(mask) == 2


def test_korean_space_is_separator():
    mask = build_mask(PuzzleLanguage.KO, "해리 포터")

    assert kinds(mask) == "rrsrr"
    assert render(mask) == "ㅎㄹ ㅍㅌ"
    assert mask_length(mask) == 4


def test_korean_standalone_jamo_stays_as_is():
    assert render(build_mask(PuzzleLanguage.KO, "ㄱ자형")) == "ㄱㅈㅎ"


def test_korean_non_hangul_letter_becomes_hidden_tile():
    mask = build_mask(PuzzleLanguage.KO, "해리potter2")

    assert kinds(mask) == "rr" + HIDDEN * 7
    assert render(mask) == "ㅎㄹ_______"


@pytest.mark.parametrize("text", ["사과", "해리 포터", "ㄱ자형", "해리potter2", "남-북"])
def test_korean_mask_matches_the_existing_chosung_column_logic(text):
    """`chosung` 컬럼(응답 호환용)과 ko 가림이 같은 초성을 쓴다는 회귀 보호."""
    rendered = "".join(
        tile["c"] if tile["t"] == REVEALED else "_" for tile in build_mask(PuzzleLanguage.KO, text)
    )

    assert rendered == extract_chosung(text)


# --- 공통 -------------------------------------------------------------------


@pytest.mark.parametrize("language", list(PuzzleLanguage))
def test_empty_answer_gives_empty_mask(language):
    assert build_mask(language, "") == []
    assert mask_length([]) == 0


def test_mask_to_text_spells_revealed_letters_and_placeholders():
    mask = build_mask(PuzzleLanguage.EN, "harry potter")

    assert mask_to_text(mask) == "H_RRY P_TT_R"


def test_mask_to_text_never_leaks_hidden_letters():
    mask = build_mask(PuzzleLanguage.EN, "apple")

    assert mask_to_text(mask) == "_PPL_"
    assert "A" not in mask_to_text(mask)
    assert "E" not in mask_to_text(mask)


def test_mask_to_text_matches_extract_chosung_for_korean_without_separators():
    answer = "사과"

    assert mask_to_text(build_mask(PuzzleLanguage.KO, answer)) == extract_chosung(answer)
