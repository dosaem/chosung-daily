"""게임 화면의 UI 문자열 사전(`app/utils/ui_strings.py`).

웹 문구는 전부 이 사전에서 나온다 — 템플릿도 JS 도 하드코딩하지 않는다. 사전 자체를
파이썬에서 검증하고, 템플릿·번들이 참조하는 키가 사전에 다 있는지도 여기서 본다.
번역 누락은 이 사전에서 생기는 가장 흔한 버그다. 실제로 그 문구가 화면에 나오는지는
`tests/test_web_js.py` 가 번들을 돌려서 본다.

언어 판정(`resolve_ui_language`)은 티켓 09 가 만든 공용 유틸이라 `tests/test_ui_language.py`
가 본다 — 여기선 "사전이 그 유틸이 돌려줄 수 있는 언어를 모두 덮는가"만 확인한다.
"""

import re
from pathlib import Path

import pytest

from app.utils.ui_language import SUPPORTED_UI_LANGUAGES, resolve_ui_language
from app.utils.ui_strings import UI_STRINGS, strings_for

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "web" / "templates" / "index.html"
BUNDLE = REPO_ROOT / "web" / "static" / "app.js"
TEMPLATE_DIR = REPO_ROOT / "web" / "templates"

# 템플릿이 사전을 읽는 두 가지 모양: `t.key` 와 `t["key"]`.
ATTRIBUTE_USE = re.compile(r"\bt\.(\w+)")
SUBSCRIPT_USE = re.compile(r"""\bt\[\s*["'](\w+)["']\s*\]""")


def test_dictionary_covers_every_supported_ui_language():
    assert set(UI_STRINGS) == set(SUPPORTED_UI_LANGUAGES)


def test_both_languages_have_the_same_keys():
    assert set(UI_STRINGS["ko"]) == set(UI_STRINGS["en"])


def test_strings_for_returns_that_language_and_rejects_others():
    assert strings_for("en") is UI_STRINGS["en"]
    with pytest.raises(KeyError):
        strings_for("fr")


def test_every_language_resolve_can_return_has_strings():
    """`resolve_ui_language` 가 돌려줄 수 있는 값이면 `strings_for` 가 터지지 않는다."""
    for header in ["ko-KR,ko;q=0.9", "en-US,en;q=0.9", "fr-FR", None]:
        assert strings_for(resolve_ui_language(None, header))


def test_no_string_is_empty():
    empty = [
        f"{language}.{key}"
        for language, strings in UI_STRINGS.items()
        for key, value in strings.items()
        if not value.strip()
    ]

    assert empty == []


def test_english_strings_have_no_korean_letters():
    """en 사전에 한글이 남아 있으면 번역을 빼먹은 것이다."""
    untranslated = [
        key for key, value in UI_STRINGS["en"].items() if re.search(r"[가-힣]", value)
    ]

    assert untranslated == []


def _placeholders(value: str) -> list[str]:
    return sorted(re.findall(r"\{(\w+)\}", value))


def test_placeholders_match_between_languages():
    """`{n}` 같은 자리표시자가 양쪽에 같아야 한다 — 하나만 빠지면 그 언어에서 숫자가 사라진다."""
    mismatched = {
        key: (_placeholders(value), _placeholders(UI_STRINGS["en"][key]))
        for key, value in UI_STRINGS["ko"].items()
        if _placeholders(value) != _placeholders(UI_STRINGS["en"][key])
    }

    assert mismatched == {}


def test_template_only_uses_keys_that_exist():
    text = TEMPLATE.read_text(encoding="utf-8")
    used = set(ATTRIBUTE_USE.findall(text)) | set(SUBSCRIPT_USE.findall(text))

    assert used, "템플릿이 사전을 전혀 안 쓰고 있다"
    assert used <= set(UI_STRINGS["ko"]), used - set(UI_STRINGS["ko"])


def test_template_never_reaches_a_dict_method_by_attribute():
    """D-42-1: Jinja 의 `{{ t.copy }}` 는 사전 키 "copy" 가 아니라 **`dict.copy`
    메서드**를 집는다 — 속성 접근(`getattr`)이 첨자보다 먼저라서다. 그 버튼 라벨이
    `<built-in method copy of dict object at 0x…>` 로 출시될 뻔했다.

    사전에 `copy`·`items`·`get` 같은 키가 있는 것 자체는 문제가 아니다. 문제는 그
    키를 **속성으로** 읽는 것이라, 템플릿 전체에서 그 모양을 막는다.
    """
    dict_members = set(dir(dict))
    offenders = {
        f"{path.relative_to(REPO_ROOT)}: t.{name}"
        for path in sorted(TEMPLATE_DIR.rglob("*.html"))
        for name in ATTRIBUTE_USE.findall(path.read_text(encoding="utf-8"))
        if name in dict_members
    }

    assert offenders == set(), f'첨자(t["키"])로 읽어야 한다: {sorted(offenders)}'


def test_bundle_only_uses_keys_that_exist():
    used = set(re.findall(r"\bt\(\"(\w+)\"", BUNDLE.read_text(encoding="utf-8")))

    assert used, "번들이 사전을 전혀 안 쓰고 있다"
    assert used <= set(UI_STRINGS["ko"]), used - set(UI_STRINGS["ko"])


def test_api_error_codes_map_to_keys_that_exist():
    """`ERROR_STRING_KEYS` 는 `t(변수)` 로 쓰여서 위 정규식에 안 걸린다 — 따로 본다.

    API 오류 message 는 한국어 한 벌뿐이라(app/errors.py) 번들이 code 로 사전 문구를
    고른다. 키 이름을 잘못 적으면 그 오류에서만 `undefined` 가 뜬다.
    """
    table = re.search(
        r"const ERROR_STRING_KEYS = \{(.*?)\};", BUNDLE.read_text(encoding="utf-8"), re.S
    )
    assert table, "번들에서 ERROR_STRING_KEYS 를 찾지 못했다"
    mapping = dict(re.findall(r'(\w+): "(\w+)"', table.group(1)))

    assert mapping, "오류 code 매핑이 비어 있다"
    assert set(mapping.values()) <= set(UI_STRINGS["ko"])


def test_attempts_has_a_singular_and_a_plural_form_in_english():
    """티켓 38: en 에서 `1 tries` 가 나오던 자리. ko 는 두 형태가 같다.

    번들은 `attemptsText(count)` 로 둘 중 하나를 고른다 — 문구를 다시
    `{attempts} tries` 처럼 패턴에 박으면 이 테스트가 먼저 깨진다.
    """
    assert UI_STRINGS["en"]["attempts_one"] == "{count} try"
    assert UI_STRINGS["en"]["attempts_other"] == "{count} tries"
    assert UI_STRINGS["ko"]["attempts_one"] == UI_STRINGS["ko"]["attempts_other"]


def test_leaderboard_strings_take_a_prebuilt_name_and_attempts_phrase():
    """리더보드·분포 문구는 숫자가 아니라 **완성된 문구**를 받는다.

    `{attempts} tries` 처럼 단위를 패턴에 박으면 복수형을 고를 자리가 없어진다.
    이름도 같은 이유로 `{name}` 이다 — 접두사는 `leaderboard_guest` 가 만든다.
    """
    for language in UI_STRINGS:
        strings = UI_STRINGS[language]
        assert _placeholders(strings["leaderboard_entry"]) == ["attempts", "name", "time"]
        assert _placeholders(strings["my_rank"]) == ["attempts", "rank", "time"]
        assert _placeholders(strings["stats_row"]) == ["attempts", "percent"]
        assert _placeholders(strings["leaderboard_guest"]) == ["tag"]


def test_the_guest_prefix_is_translated():
    """서버가 보내는 태그는 언어 중립이라, 접두사가 양쪽 언어에 따로 있어야 한다."""
    assert UI_STRINGS["ko"]["leaderboard_guest"] == "게스트 #{tag}"
    assert UI_STRINGS["en"]["leaderboard_guest"] == "Guest #{tag}"
