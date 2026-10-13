"""법적 문서 레이아웃 스타일시트(web/static/legal.css) 검증.

폭·패딩은 OVERRIDES §4·§10 이 숫자로 정한 값이라, 실제 브라우저에서 몇 px 로 나오는지가
완료 조건이다. 레포에 브라우저 드라이버 의존성이 없어서(프로덕션 의존성을 테스트
때문에 늘리지 않는다) 여기서는 그 px 를 만드는 CSS 선언을 고정하고, 헤드리스 Chrome
실측은 `review/impl-evidence-09.md` §수정 라운드 1 에 재현 스크립트와 함께 둔다.
"""

import re
from pathlib import Path

LEGAL_CSS = Path(__file__).resolve().parent.parent / "web" / "static" / "legal.css"

# OVERRIDES §10 의 "≤480 폭 100% / 481+ 카드 max-width: 480px" 경계.
TABLET_MIN_WIDTH = "481px"


def _rules(css: str, selector: str) -> list[str]:
    """선택자의 선언 블록들을 등장 순서대로 돌려준다."""
    pattern = re.compile(rf"(?:^|\}}|\{{|\n)\s*{re.escape(selector)}\s*\{{([^}}]*)\}}")
    return [match.group(1) for match in pattern.finditer(css)]


def _css() -> str:
    return LEGAL_CSS.read_text(encoding="utf-8")


def test_doc_card_width_counts_padding():
    """480px 는 카드 '외곽' 폭이다 (OVERRIDES §10).

    content-box 로 두면 좌우 패딩이 더해져서 실제 외곽 폭이 480 을 넘는다 (D-09-3).
    """
    rule = _rules(_css(), ".doc")[0]

    assert "max-width: var(--content-max-width);" in rule
    assert "box-sizing: border-box;" in rule


def test_doc_mobile_padding_is_16px():
    # OVERRIDES §4: 카드 패딩 16(모바일). 기본값이 모바일이고 태블릿+ 가 덮어쓴다.
    rule = _rules(_css(), ".doc")[0]
    padding = re.search(r"padding:([^;]*);", rule)

    assert padding, ".doc 에 padding 선언이 없다"
    assert "var(--space-6)" not in padding.group(1)
    assert "var(--space-4)" in padding.group(1)


def test_doc_tablet_padding_is_24px():
    # OVERRIDES §4: 24(태블릿+). 경계는 §10 과 같은 481px.
    css = _css()
    start = css.find(f"min-width: {TABLET_MIN_WIDTH}")

    assert start != -1, f"min-width: {TABLET_MIN_WIDTH} 미디어 쿼리가 없다"
    rule = _rules(css[start:], ".doc")[0]
    assert "var(--space-6)" in rule


def test_legal_css_defines_no_new_colors_or_shadows():
    # tokens.css 변수만 쓴다는 파일 머리 주석을 테스트로도 고정한다.
    css = _css()

    assert "box-shadow" not in css
    assert "text-shadow" not in css
    # 2px/3px 는 밑줄 두께·오프셋이라 토큰 대상이 아니다. 색 리터럴은 하나도 없어야 한다.
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css)
    assert not re.search(r"\brgba?\(", css)
