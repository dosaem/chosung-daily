"""도메인 문서가 docs/agents/domain.md 가 가리키는 자리에 있는지 확인한다.

용어집·ADR 은 계획 단계에서 `.scratch/store-launch/` 에 있었다(Planner 가 그 밖을
못 썼다). 에이전트 스킬과 사람이 읽는 자리는 레포 루트 `CONTEXT.md` + `docs/adr/`
라서 구현 첫 티켓에서 옮겼고, 이 테스트가 그 자리를 지킨다.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = REPO_ROOT / "docs" / "adr"


def test_context_md_is_at_repo_root():
    context = REPO_ROOT / "CONTEXT.md"

    assert context.is_file()
    assert "## Language" in context.read_text(encoding="utf-8")


def test_adrs_are_under_docs_adr():
    slugs = sorted(path.name for path in ADR_DIR.glob("*.md"))

    assert slugs == [
        "0001-kst-fixed-day-boundary.md",
        "0002-app-login-via-id-token-exchange.md",
        "0003-subscription-entitlement-on-server.md",
    ]


def test_domain_doc_points_at_those_paths():
    """`docs/agents/domain.md` 가 가리키는 경로와 실제 위치가 같아야 한다."""
    layout = (REPO_ROOT / "docs" / "agents" / "domain.md").read_text(encoding="utf-8")

    assert "`CONTEXT.md`** at the repo root" in layout
    assert "`docs/adr/`" in layout


# --- 최종 코드와의 대조 (티켓 37) -------------------------------------------

CONTEXT = REPO_ROOT / "CONTEXT.md"
MOBILE_LIB = REPO_ROOT / "mobile" / "lib"

# 용어집에 term 이 있어야 하는 개념 → 그 개념이 실제로 코드에 있는지 보는 파일.
# 계획 당시 용어집에 없던 앱 개념들이다(티켓 28·31·32·33 이 코드로 만들었다).
GLOSSARY_TERMS = {
    "구독 안내(Paywall)": MOBILE_LIB / "subscription" / "paywall_sheet.dart",
    "광고 동의(Ad Consent)": MOBILE_LIB / "ads" / "google_ad_service.dart",
    "권한 재확인(Entitlement Recheck)": MOBILE_LIB / "subscription" / "entitlement_schedule.dart",
    "온보딩(Onboarding)": MOBILE_LIB / "screens" / "onboarding_screen.dart",
}


@pytest.mark.parametrize(("term", "source"), GLOSSARY_TERMS.items(), ids=list(GLOSSARY_TERMS))
def test_glossary_covers_the_concepts_the_app_code_has(term, source):
    """코드에 개념이 있으면 용어집에도 있어야 한다 — 티켓 37 이 추가분을 반영한다."""
    assert source.is_file(), f"{source} 가 없다 — 용어집의 term 과 코드가 어긋난다"
    assert f"**{term}**" in CONTEXT.read_text(encoding="utf-8"), term


def test_adr_0003_matches_the_app_side_recheck_floor():
    """ADR 은 정본이다. 티켓 33 이 앱 쪽에 더한 하한·관측 시각이 빠지면 거짓이 된다."""
    adr = (ADR_DIR / "0003-subscription-entitlement-on-server.md").read_text(encoding="utf-8")

    assert "하한" in adr
    assert "관측 시각" in adr
