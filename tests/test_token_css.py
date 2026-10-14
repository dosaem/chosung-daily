"""공용 디자인 토큰 스타일시트(web/static/tokens.css) 검증.

OVERRIDES.md(디자인 시스템 정본)의 토큰 표를 CSS 변수로 옮긴 파일이라,
"변수가 있는지"와 "OVERRIDES 가 금지한 것이 없는지"를 파일 내용으로 확인한다.
"""

import re
from pathlib import Path

import pytest

TOKENS_CSS = Path(__file__).resolve().parent.parent / "web" / "static" / "tokens.css"

# OVERRIDES.md §2 색 토큰 표: (변수 이름, 라이트 값, 다크 값)
COLOR_TOKENS = [
    ("--color-brand", "#ea580c", "#f97316"),
    ("--color-primary-button", "#0f172a", "#f1f5f9"),
    ("--color-on-primary-button", "#ffffff", "#141a26"),
    ("--color-brand-subtle", "#fff7ed", "#431407"),
    ("--color-background", "#fafaf9", "#141a26"),
    ("--color-foreground", "#0f172a", "#f1f5f9"),
    ("--color-card", "#ffffff", "#1c2433"),
    ("--color-muted", "#f5f5f4", "#253044"),
    ("--color-muted-foreground", "#57534e", "#94a3b8"),
    ("--color-border", "#e7e5e4", "#2a3447"),
    ("--color-destructive", "#dc2626", "#ef4444"),
    ("--color-tile-correct", "#16a34a", "#22c55e"),
    ("--color-tile-wrong", "#d6d3d1", "#475569"),
    ("--color-tile-text-on-correct", "#ffffff", "#052e16"),
]


@pytest.fixture(scope="module")
def css() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8").lower()


@pytest.fixture(scope="module")
def dark_block(css: str) -> str:
    """`prefers-color-scheme: dark` 미디어 쿼리 안쪽만 떼어낸다."""
    start = css.index("prefers-color-scheme: dark")
    return css[start:]


@pytest.mark.parametrize(("name", "light", "_dark"), COLOR_TOKENS)
def test_light_color_token_matches_overrides(css: str, name: str, light: str, _dark: str):
    assert f"{name}: {light};" in css


@pytest.mark.parametrize(("name", "_light", "dark"), COLOR_TOKENS)
def test_dark_color_token_matches_overrides(dark_block: str, name: str, _light: str, dark: str):
    assert f"{name}: {dark};" in dark_block


def test_tile_empty_reuses_muted(css: str):
    # OVERRIDES §2: tile-empty 은 muted 와 같은 면. 값을 복제하지 않고 참조한다.
    assert "--color-tile-empty: var(--color-muted);" in css


@pytest.mark.parametrize("space", ["4px", "8px", "12px", "16px", "24px", "32px", "48px"])
def test_spacing_scale(css: str, space: str):
    # OVERRIDES §4 간격 스케일 4/8/12/16/24/32/48
    assert f": {space};" in css


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("--radius-tile", "8px"),
        ("--radius-button", "10px"),
        ("--radius-card", "16px"),
        ("--radius-sheet", "20px"),
    ],
)
def test_radius_scale(css: str, name: str, value: str):
    assert f"{name}: {value};" in css


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("--font-size-xs", "12px"),
        ("--font-size-sm", "14px"),
        ("--font-size-base", "16px"),
        ("--font-size-lg", "20px"),
        ("--font-size-xl", "24px"),
        ("--font-size-2xl", "32px"),
        ("--line-height-body", "1.5"),
        ("--letter-spacing-ko", "-0.01em"),
    ],
)
def test_typography_tokens(css: str, name: str, value: str):
    assert f"{name}: {value};" in css


def test_pretendard_is_the_primary_font(css: str):
    # OVERRIDES §3: Pretendard Variable → Inter → system-ui
    match = re.search(r"--font-sans:([^;]+);", css)
    assert match, "--font-sans 토큰이 없다"
    stack = [part.strip().strip("\"'") for part in match.group(1).split(",")]
    assert stack[0] == "pretendard variable"
    assert "inter" in stack
    assert "system-ui" in stack


def test_no_shadows(css: str):
    # OVERRIDES §4: 그림자 없음.
    assert "box-shadow" not in css
    assert "text-shadow" not in css


def test_declares_both_color_schemes(css: str):
    # OVERRIDES §9: 시스템 추종. 브라우저 기본 UI(스크롤바·폼)도 같이 따라오게.
    assert "color-scheme: light dark;" in css


def test_token_css_is_served(client):
    res = client.get("/static/tokens.css")

    assert res.status_code == 200
    assert b"--color-background" in res.data


def test_tokens_css_declares_variables_only(css: str):
    """이 파일은 변수만 둔다 — 요소 규칙을 넣으면 이걸 같이 쓰는 페이지마다 되돌리는
    코드가 생긴다(파일 머리말).

    (티켓 09 의 `test_main_page_style_is_untouched` 를 대체한다. 그 테스트는 "09 가
    메인 페이지를 안 건드렸다"는 뜻이었는데, 17 이 자기가 새로 만든 요소(타일·칩·
    순위 행)에 이 변수를 쓰기로 해서 더 이상 성립하지 않는다. 17 의 새 요소가 색을
    직접 정하지 않는지는 `tests/test_web.py` 가 본다. 기존 규칙의 토큰 전환·다크모드
    는 티켓 18 범위다.)
    """
    outside_blocks = re.sub(r":root[^{]*\{[^}]*\}", "", css)
    outside_blocks = re.sub(r"@media[^{]*\{.*?\n\}", "", outside_blocks, flags=re.S)
    selectors = re.findall(r"^\s*([.#a-z][^{\n]*)\{", outside_blocks, re.M)

    assert selectors == []
