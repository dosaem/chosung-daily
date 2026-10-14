"""메인 페이지(`/`)의 디자인 계약 — 토큰 CSS · 상태 화면 · 섹션 토글 · 앱 CTA · 푸터.

`tests/test_web.py` 는 문구 사전·기기 언어·번들 계약을 본다. 이 파일은 티켓 18 이
바꾼 **화면의 생김새 계약**만 모았다: 어떤 요소가 렌더되는지, 색·폭을 토큰에서
가져오는지, 설정값이 비었을 때 무엇을 안 그리는지.

브라우저는 안 띄운다(스펙 "미정 항목" 5). 실제 상태 전환 동작(스켈레톤 → 퍼즐,
오프라인 배너, 카운트다운)은 번들을 node 로 돌리는 `tests/test_web_js.py` 가 보고,
라이트/다크 실제 렌더는 워커가 헤드리스 스크린샷으로 남겼다
(`.scratch/store-launch/design/web-shots/`, `review/impl-evidence-18.md`).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = REPO_ROOT / "web" / "static" / "style.css"
TEMPLATE = REPO_ROOT / "web" / "templates" / "index.html"


@pytest.fixture(scope="module")
def style() -> str:
    return STYLE_CSS.read_text(encoding="utf-8")


@pytest.fixture
def html(client) -> str:
    return client.get("/").data.decode()


# --- 토큰 CSS 교체 (OVERRIDES §2·§4·§9·§10) ----------------------------------


def test_style_sheet_has_no_hex_colors_left(style: str):
    """색은 전부 tokens.css 변수에서 온다 — 이 파일에 hex 가 남아 있으면 토큰을 안 쓴 것이다.

    (티켓 17 이 남긴 `test_new_elements_use_token_variables_not_new_hex` 는 "17 이 새로
    만든 선택자에는 hex 가 없다" 였다. 18 이 기존 규칙까지 옮겼으니 파일 전체를 본다.)
    """
    assert re.findall(r"#[0-9a-fA-F]{3,8}\b", style) == []


def test_style_sheet_has_no_shadows(style: str):
    # OVERRIDES §4: 그림자 없음. 17 까지 `.card` 에 남아 있었다.
    assert "box-shadow" not in style
    assert "text-shadow" not in style


def test_style_sheet_does_not_pin_its_own_color_scheme(style: str):
    """`color-scheme: light` 를 다시 선언하면 tokens.css 의 `light dark` 를 덮어
    다크모드가 안 따라온다(OVERRIDES §9)."""
    assert "color-scheme: light;" not in style


def test_card_width_comes_from_the_shared_token(style: str):
    """OVERRIDES §10: 중앙 정렬 카드 하나, 481+ 에서 480px. 420px 하드코딩을 걷어낸다."""
    widths = [
        block
        for selector, block in re.findall(r"([^{}]*)\{([^}]*)\}", style)
        if ".card" in selector and "max-width" in block
    ]

    assert widths, "`.card` 의 최대 폭을 정하는 규칙이 없다"
    assert all("var(--content-max-width)" in block for block in widths)
    assert "420px" not in style


@pytest.mark.parametrize(
    ("selector", "token"),
    [
        (".primary-button", "var(--color-primary-button)"),
        (".tile-empty", "var(--color-tile-empty)"),
        (".tile-correct", "var(--color-tile-correct)"),
        (".tile-wrong", "var(--color-tile-wrong)"),
    ],
)
def test_token_named_classes_use_the_token_of_the_same_name(style: str, selector: str, token: str):
    """클래스 이름을 토큰 이름 그대로 쓴다(티켓 18 완료 조건).

    이름이 같으면 "이 면은 어느 토큰인가" 를 CSS 를 열지 않고도 마크업에서 읽는다.
    """
    block = style.split(selector + " {")[1].split("}", maxsplit=1)[0]

    assert token in block


def test_feedback_tiles_are_not_distinguished_by_color_alone(style: str):
    """US 3 · OVERRIDES §2: correct 는 체크 아이콘/굵은 글자, wrong 은 취소선."""
    correct = style.split(".tile-correct {")[1].split("}", maxsplit=1)[0]
    wrong = style.split(".tile-wrong {")[1].split("}", maxsplit=1)[0]

    assert "font-weight" in correct
    assert ".tile-correct::after" in style, "correct 타일에 체크 표시가 없다"
    assert "line-through" in wrong


def test_page_loads_the_pretendard_web_font(html: str):
    # OVERRIDES §3: 웹은 Pretendard CDN (법적 문서 페이지와 같은 고정 버전).
    assert "pretendard" in html.lower()


# --- 상태 4종 (OVERRIDES §7) --------------------------------------------------


def test_skeleton_is_rendered_before_the_puzzle_arrives(html: str):
    """로딩은 스켈레톤이다 — 스피너 금지(OVERRIDES §7). 서버가 미리 그려 내려보낸다."""
    assert 'id="puzzle-skeleton"' in html
    skeleton = html.split('id="puzzle-skeleton"')[1].split("</div>", maxsplit=1)[0]

    assert "hidden" not in skeleton, "처음 상태가 스켈레톤이어야 한다"
    assert 'id="puzzle"' in html
    assert re.search(r'id="puzzle" class="[^"]*hidden', html), "퍼즐 영역은 숨은 채 시작한다"


def test_offline_banner_sits_above_the_card(html: str):
    """오프라인은 상단 배너다(OVERRIDES §7) — 카드 안이 아니라 카드 위."""
    assert 'id="offline-banner"' in html
    assert html.index('id="offline-banner"') < html.index('<main class="card"')


def test_inline_state_card_carries_a_retry_button_and_a_countdown_slot(html: str):
    """네트워크 오류와 "퍼즐 없음" 이 같은 인라인 카드를 쓴다 — 토스트로 숨기지 않는다."""
    assert 'id="puzzle-state"' in html
    assert 'id="puzzle-state-text"' in html
    assert 'id="puzzle-state-countdown"' in html
    assert 'id="puzzle-state-retry"' in html


# --- 섹션 토글 (SCREENS "웹" 절) ----------------------------------------------


def test_section_nav_toggles_three_sections_on_one_page(html: str):
    """탭 대신 상단 텍스트 링크 → 같은 페이지 섹션 토글(SCREENS 웹 절)."""
    for section in ["today", "leaderboard", "records"]:
        assert f'data-section="{section}"' in html, section
        assert f'data-section-panel="{section}"' in html, section


def test_only_the_today_section_is_visible_at_first(html: str):
    panels = {
        name: classes
        for classes, name in re.findall(r'class="([^"]*)" data-section-panel="(\w+)"', html)
    }

    assert panels, "섹션 패널을 찾지 못했다"
    assert "hidden" not in panels["today"]
    assert "hidden" in panels["leaderboard"]
    assert "hidden" in panels["records"]


def test_active_section_link_is_marked_for_assistive_tech(html: str):
    nav = html.split('class="section-nav"')[1].split("</nav>", maxsplit=1)[0]

    assert nav.count("aria-pressed") == 3
    assert 'aria-pressed="true"' in nav


def test_backup_and_restore_panels_moved_into_the_records_section(html: str):
    """백업/불러오기 패널은 유지한다(디자인만 토큰). 자리는 "내 기록" 섹션."""
    records = html.split('data-section-panel="records"')[1].split("</section>", maxsplit=1)[0]

    assert 'id="backup-panel"' in records
    assert 'id="restore-panel"' in records
    assert 'id="token-input"' in records
    assert 'id="google-login-button"' in records


# --- 앱 CTA · Smart App Banner (US 42·43, 08 의 설정값) ----------------------


def _with_store_config(app, **overrides):
    app.config["STORE_URL_IOS"] = overrides.get("ios", "")
    app.config["STORE_URL_ANDROID"] = overrides.get("android", "")
    app.config["APP_STORE_ID"] = overrides.get("app_store_id", "")


def test_store_badges_and_smart_app_banner_render_when_configured(app, client):
    _with_store_config(
        app,
        ios="https://apps.apple.com/app/id1234567890",
        android="https://play.google.com/store/apps/details?id=com.chosungdaily.app",
        app_store_id="1234567890",
    )
    html = client.get("/").data.decode()

    assert '<meta name="apple-itunes-app" content="app-id=1234567890"' in html
    assert "https://apps.apple.com/app/id1234567890" in html
    assert "https://play.google.com/store/apps/details?id=com.chosungdaily.app" in html


def test_nothing_store_shaped_renders_while_the_app_is_not_on_the_stores(app, client):
    """스토어 등록 전에는 설정값이 비어 있다 — 배지도 메타 태그도 그리지 않는다."""
    _with_store_config(app)
    html = client.get("/").data.decode()

    assert "apple-itunes-app" not in html
    assert 'class="store-badge"' not in html
    assert 'class="app-cta"' not in html


def test_each_badge_is_independent_of_the_other_platform(app, client):
    """한쪽 스토어만 먼저 열리는 경우가 있다 — 있는 쪽만 그린다."""
    _with_store_config(app, ios="https://apps.apple.com/app/id999")
    html = client.get("/").data.decode()

    assert html.count('class="store-badge"') == 1
    assert "apps.apple.com" in html
    assert "play.google.com" not in html


def test_the_app_cta_lives_in_the_result_section(app, client):
    """ "앱에서 연속 기록·알림" 안내는 결과 화면이다(US 42 · SCREENS 웹 절)."""
    _with_store_config(app, ios="https://apps.apple.com/app/id999")
    html = client.get("/").data.decode()
    result = html.split('id="result"')[1].split("</section>")[0]

    assert 'class="app-cta"' in result


# --- 푸터 (US 45 · 티켓 16 의 사업자 정보 조각) ------------------------------


@pytest.mark.parametrize("path", ["/privacy", "/terms", "/account/delete"])
def test_footer_links_the_three_legal_urls(html: str, path: str):
    footer = html.split('class="site-footer"')[1]

    assert f'href="{path}' in footer, path


def test_footer_includes_the_shared_business_info_fragment(html: str):
    """티켓 16 이 소유한 조각을 include 한다 — 항목을 여기서 더하거나 빼지 않는다."""
    footer = html.split('class="site-footer"')[1]

    assert 'class="doc-operator"' in footer
    assert 'id="business-info"' in footer
    # 조각의 고정 항목(서비스·연락처·호스팅)은 사업자 정보가 비어도 렌더된다.
    assert "chosung.dosaem.com" in footer


def test_footer_business_info_follows_the_same_config_as_the_legal_pages(app, client):
    """조각이 쓰는 컨텍스트를 메인 페이지도 같은 설정에서 넘긴다."""
    app.config["LEGAL_BUSINESS_NAME"] = "테스트 상호"
    footer = client.get("/").data.decode().split('class="site-footer"')[1]

    assert "테스트 상호" in footer
