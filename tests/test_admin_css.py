"""운영자 페이지 스타일시트(web/static/admin.css) — 토큰만 쓰는지 고정한다.

디자인 시스템(OVERRIDES)과 어긋나기 가장 쉬운 두 가지를 기계로 막는다: 색을 직접
적는 것과, brand 를 면으로 칠하는 것. 둘 다 `impeccable detect` 가 잡아주지만
(review/impl-evidence-15.md), 그건 수동 실행이라 레포에 남는 가드가 따로 필요하다.
"""

import re
from pathlib import Path

WEB_STATIC = Path(__file__).resolve().parent.parent / "web" / "static"
ADMIN_CSS = WEB_STATIC / "admin.css"


def _css() -> str:
    return ADMIN_CSS.read_text(encoding="utf-8")


def test_admin_css_defines_no_colors_of_its_own():
    css = _css()

    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert not re.search(r"\brgba?\(", css)
    # 그림자 없음 (OVERRIDES §4).
    assert "box-shadow" not in css
    assert "text-shadow" not in css


def test_admin_css_never_fills_a_surface_with_brand():
    """brand 오렌지는 아이콘·밑줄·테두리·포커스 링에만 쓴다 (OVERRIDES §2).

    `brand-subtle` 은 brand 배경 칩용으로 따로 있는 토큰이라 면에 쓸 수 있다.
    """
    for declaration in re.findall(r"\bbackground:([^;]*);", _css()):
        assert "--color-brand)" not in declaration, declaration


def test_admin_pages_link_the_shared_token_stylesheet():
    layout = (
        Path(__file__).resolve().parent.parent
        / "web"
        / "templates"
        / "admin"
        / "_layout.html"
    ).read_text(encoding="utf-8")

    assert "filename='tokens.css'" in layout
    assert "filename='admin.css'" in layout


def test_admin_css_keeps_touch_targets_at_44px():
    # OVERRIDES §4: 터치 타깃 최소 44x44. 토큰으로만 적는다.
    css = _css()

    assert css.count("min-height: var(--touch-target-min);") >= 3
