"""도메인 문서가 docs/agents/domain.md 가 가리키는 자리에 있는지 확인한다.

용어집·ADR 은 계획 단계에서 `.scratch/store-launch/` 에 있었다(Planner 가 그 밖을
못 썼다). 에이전트 스킬과 사람이 읽는 자리는 레포 루트 `CONTEXT.md` + `docs/adr/`
라서 구현 첫 티켓에서 옮겼고, 이 테스트가 그 자리를 지킨다.
"""

from pathlib import Path

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
