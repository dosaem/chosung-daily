"""배포 워크플로(`.github/workflows/deploy.yml`)의 계약 테스트.

GitHub Actions 워크플로는 푸시해 봐야 돌아가서 로컬에서 "틀렸다" 를 알기 어렵다.
그래서 돌려서 확인할 수 없는 부분(트리거·선행 조건·대상 매핑·쓰는 secret 이름)을
YAML 을 읽어서 검증한다. 같이 `ci.yml` 이 develop 을 포함하는지, 배포 티켓이
CI 를 건드리지 않았는지도 본다.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"
DEPLOY = ROOT / ".github" / "workflows" / "deploy.yml"
RELEASE_DOC = ROOT / "docs" / "RELEASE.md"


# YAML 1.1 에서 `on` 은 불린이라 PyYAML 이 트리거 키를 True 로 읽는다.
ON = True


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ci():
    return _load(CI)


@pytest.fixture(scope="module")
def deploy():
    return _load(DEPLOY)


def _steps(workflow, job):
    return workflow["jobs"][job]["steps"]


def _flat(value):
    """워크플로 전체를 한 문자열로 — secret 참조 같은 걸 찾기 위해."""
    return yaml.safe_dump(value, allow_unicode=True)


def test_ci_runs_on_both_deploy_branches(ci):
    """develop 푸시에도 CI 가 돌아야 deploy 의 선행 조건이 성립한다."""
    assert ci[ON]["push"]["branches"] == ["main", "develop"]


def test_ci_still_lints_and_tests_with_service_containers(ci):
    """이 티켓은 ci.yml 에 develop 추가 외에는 손대지 않는다."""
    commands = [step.get("run", "") for step in _steps(ci, "test")]

    assert any("ruff check" in cmd for cmd in commands)
    assert any("pytest" in cmd for cmd in commands)
    assert sorted(ci["jobs"]["test"]["services"]) == ["mysql", "redis"]


def test_deploy_waits_for_ci_on_the_two_branches(deploy):
    trigger = deploy[ON]["workflow_run"]

    assert trigger["workflows"] == ["CI"]
    assert trigger["types"] == ["completed"]
    assert trigger["branches"] == ["main", "develop"]


def test_deploy_only_runs_when_ci_succeeded(deploy):
    """`completed` 는 실패도 포함한다 — conclusion 을 보지 않으면 깨진 코드가 올라간다."""
    condition = deploy["jobs"]["deploy"]["if"]

    assert "workflow_run.conclusion" in condition
    assert "success" in condition


REPO = "dosaem/chosung-daily"


def _resolve(token, context):
    token = token.strip()
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    value = context
    for part in token.split("."):
        value = value[part]
    return value


def _allows(condition, context):
    """`if:` 의 `a == b && ...` 를 컨텍스트에 대입해 평가한다.

    GitHub 식을 전부 해석하진 않는다 — 배포 게이트가 쓰는 `&&` 와 `==` 만 다룬다.
    그 밖의 연산자가 들어오면 조용히 통과시키지 않고 실패한다.
    """
    for term in condition.split("&&"):
        left, operator, right = term.partition("==")
        assert operator, f"지원하지 않는 식: {term.strip()}"
        if _resolve(left, context) != _resolve(right, context):
            return False
    return True


def _workflow_run(event, *, conclusion="success", head_repo=REPO, branch="main"):
    """선행 CI 의 workflow_run 이벤트 페이로드."""
    return {
        "github": {
            "repository": REPO,
            "event": {
                "workflow_run": {
                    "event": event,
                    "conclusion": conclusion,
                    "head_branch": branch,
                    "head_repository": {"full_name": head_repo},
                }
            },
        }
    }


@pytest.mark.parametrize("branch", ["main", "develop"])
def test_deploy_runs_for_push_ci_on_deploy_branches(deploy, branch):
    condition = deploy["jobs"]["deploy"]["if"]

    assert _allows(condition, _workflow_run("push", branch=branch))


def test_deploy_blocks_pull_request_ci(deploy):
    """ci.yml 은 `pull_request` 에서도 돈다 — PR 브랜치 이름이 main 이면 배포가 열린다.

    열리면 러너가 PR 의 커밋을 checkout 해서 그 `deploy/deploy.sh` 를 배포 secret 으로
    연 NAS 로 흘려보낸다. 병합 전 코드가 NAS 에서 실행되는 것이라 스크립트 안의
    SHA 검사로는 막을 수 없다(그 검사도 PR 이 바꿀 수 있는 코드다).
    """
    condition = deploy["jobs"]["deploy"]["if"]

    assert not _allows(condition, _workflow_run("pull_request"))
    assert not _allows(condition, _workflow_run("pull_request", branch="develop"))


def test_deploy_blocks_ci_from_a_forked_head_repository(deploy):
    """fork 의 PR CI 도 같은 이름의 브랜치를 쓸 수 있다 — 저장소 출처까지 봐야 한다."""
    condition = deploy["jobs"]["deploy"]["if"]

    assert not _allows(condition, _workflow_run("push", head_repo="attacker/chosung-daily"))


def test_deploy_blocks_failed_push_ci(deploy):
    condition = deploy["jobs"]["deploy"]["if"]

    assert not _allows(condition, _workflow_run("push", conclusion="failure"))


def test_deploy_maps_branch_to_target(deploy):
    """main → prod, develop → develop. 푸시된 브랜치는 workflow_run 이벤트에서 읽는다."""
    flat = _flat(deploy["jobs"]["deploy"])

    assert "workflow_run.head_branch" in flat
    assert "prod" in flat
    assert "develop" in flat


def test_deploy_checks_out_the_commit_that_passed_ci(deploy):
    """workflow_run 은 기본 브랜치를 체크아웃한다 — 통과한 커밋을 명시해야 한다."""
    checkout = next(
        step
        for step in _steps(deploy, "deploy")
        if step.get("uses", "").startswith("actions/checkout")
    )

    assert "workflow_run.head_sha" in _flat(checkout["with"])


def test_deploy_pins_the_nas_build_to_the_ci_commit(deploy):
    """러너 checkout 은 러너가 읽는 스크립트만 정한다 — NAS 가 빌드할 커밋도 넘겨야 한다.

    안 넘기면 NAS 의 git 이 "지금의 브랜치 끝" 을 가져오기 때문에, A 의 CI 로 시작한
    배포가 그 사이 올라온(CI 를 안 거친) B 를 빌드할 수 있다.
    """
    job = deploy["jobs"]["deploy"]
    sha_vars = [name for name, value in job["env"].items() if "head_sha" in str(value)]
    assert sha_vars, "job env 에 workflow_run.head_sha 가 없다"

    run = " ".join(step.get("run", "") for step in _steps(deploy, "deploy"))
    assert f"bash -s -- $TARGET ${sha_vars[0]}" in run, "deploy.sh <대상> <sha> 순서로 넘긴다"


def test_deploy_joins_tailnet_before_ssh(deploy):
    """NAS 는 인터넷에 ssh 를 안 열어서 Tailscale 로 들어가야 한다 — 순서가 뒤집히면 못 붙는다."""
    steps = _steps(deploy, "deploy")
    tailscale = next(
        i for i, step in enumerate(steps) if "tailscale/github-action" in step.get("uses", "")
    )
    ssh = next(i for i, step in enumerate(steps) if "ssh " in step.get("run", ""))

    assert tailscale < ssh


def test_deploy_pipes_the_script_over_ssh(deploy):
    """NAS 체크아웃의 스크립트를 실행하면 git pull 이 실행 중인 자기 자신을 갈아치운다."""
    run = " ".join(step.get("run", "") for step in _steps(deploy, "deploy"))

    assert "bash -s --" in run
    assert "deploy/deploy.sh" in run


def _secret_names(text):
    return set(re.findall(r"secrets\.([A-Z0-9_]+)", text))


def _release_doc_secret_table_names():
    """RELEASE.md 의 secrets 표 첫 칸에 적힌 `` `NAME` `` 들."""
    rows = []
    in_table = False
    for line in RELEASE_DOC.read_text(encoding="utf-8").splitlines():
        if "secrets" in line.lower() and line.startswith("#"):
            in_table = True
            continue
        if in_table and line.startswith("#"):
            break
        if in_table and line.startswith("|"):
            cell = line.split("|")[1].strip()
            match = re.fullmatch(r"`([A-Z0-9_]+)`", cell)
            if match:
                rows.append(match.group(1))
    return set(rows)


def test_deploy_secrets_are_documented(deploy):
    """워크플로가 쓰는 secret 이 RELEASE.md 표에 전부 있어야 사람이 등록할 수 있다."""
    used = _secret_names(_flat(deploy))

    assert used, "secrets 를 안 쓰는 배포 워크플로는 없다"
    assert used <= _release_doc_secret_table_names()


def test_deploy_secrets_cover_tailscale_ssh_and_host(deploy):
    used = _secret_names(_flat(deploy))

    assert any("TAILSCALE" in name or name.startswith("TS_") for name in used)
    assert any("SSH" in name and "KEY" in name for name in used)
    assert any("HOST" in name for name in used)


def test_release_doc_has_human_checklist_for_nas_access():
    """ssh 키 등록·Tailscale 설치는 사람이 NAS 에서 하는 일 — D3 체크리스트로 분리."""
    text = RELEASE_DOC.read_text(encoding="utf-8")
    section = text.split("D3", 1)

    assert len(section) == 2, "RELEASE.md 에 D3 체크리스트가 없다"
    body = section[1]
    assert "Tailscale" in body
    assert "ssh" in body
