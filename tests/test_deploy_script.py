"""`deploy/deploy.sh` 의 계약 테스트.

배포 스크립트는 NAS 에서만 실제로 돌지만, "어느 브랜치·디렉터리·env 파일·compose
프로젝트명을 고르는지" 와 "어떤 순서로 무엇을 실행하고 어디서 멈추는지" 는 로컬에서
확인할 수 있어야 한다. 두 가지로 검증한다.

1. `--dry-run`: 아무것도 실행하지 않고 실행할 명령만 찍는다 → 대상별 설정 확인.
2. 가짜 `git`/`docker`/`curl`/`sleep`(`tests/fake_nas_bin/`)을 PATH 앞에 두고 실제
   실행 → 단계 순서, 마이그레이션 실패 시 중단, `/health` 재시도까지 실제 분기를 지난다.

도커를 띄우지 않는다. 실제 기동 검증은 `docs/RELEASE.md` 의 로컬/NAS 절차.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SH = ROOT / "deploy" / "deploy.sh"
FAKE_BIN = Path(__file__).resolve().parent / "fake_nas_bin"


def run_dry(*args):
    return subprocess.run(
        ["bash", str(DEPLOY_SH), *args],
        capture_output=True,
        text=True,
    )


class FakeNas:
    """가짜 NAS: 체크아웃 디렉터리와 PATH 앞에 둘 가짜 명령을 준비한다."""

    def __init__(self, tmp_path, target_dir, **overrides):
        self.base = tmp_path / "docker"
        (self.base / target_dir).mkdir(parents=True)
        self.log = tmp_path / "calls.log"
        self.env = {
            **os.environ,
            "PATH": f"{FAKE_BIN}{os.pathsep}{os.environ['PATH']}",
            "DEPLOY_BASE_DIR": str(self.base),
            "FAKE_LOG": str(self.log),
            "FAKE_CURL_COUNTER": str(tmp_path / "curl.count"),
            **overrides,
        }

    def deploy(self, target):
        return subprocess.run(
            ["bash", str(DEPLOY_SH), target],
            capture_output=True,
            text=True,
            env=self.env,
        )

    def calls(self):
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


def test_deploy_script_is_executable():
    assert DEPLOY_SH.exists()
    assert os.access(DEPLOY_SH, os.X_OK), "NAS 에서 `deploy.sh prod` 로 바로 실행한다"


def test_missing_target_fails_with_usage():
    res = run_dry()

    assert res.returncode != 0
    assert "prod|develop" in res.stderr


def test_unknown_target_fails_with_usage():
    res = run_dry("staging", "--dry-run")

    assert res.returncode != 0
    assert "prod|develop" in res.stderr


@pytest.mark.parametrize(
    ("target", "branch", "directory", "project", "env_file"),
    [
        ("prod", "main", "/volume1/docker/chosung-daily", "chosung-daily-prod", ".env"),
        (
            "develop",
            "develop",
            "/volume1/docker/chosung-daily-develop",
            "chosung-daily-develop",
            ".env.develop",
        ),
    ],
)
def test_dry_run_picks_target_settings(target, branch, directory, project, env_file):
    """대상 인자 하나가 브랜치·디렉터리·프로젝트명·env 파일을 전부 결정한다."""
    res = run_dry(target, "--dry-run")

    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert f"git pull --ff-only origin {branch}" in out
    assert directory in out
    assert f"-p {project}" in out
    assert f"--env-file {env_file}" in out
    assert "-f docker-compose.prod.yml" in out


def test_dry_run_does_not_touch_the_other_instance():
    res = run_dry("develop", "--dry-run")

    assert "chosung-daily-prod" not in res.stdout
    assert ".env.develop" in res.stdout


def test_dry_run_runs_nothing(tmp_path):
    """dry-run 은 가짜 명령조차 부르지 않는다 — 출력만 보고 검토할 수 있다."""
    nas = FakeNas(tmp_path, "chosung-daily")
    res = subprocess.run(
        ["bash", str(DEPLOY_SH), "prod", "--dry-run"],
        capture_output=True,
        text=True,
        env=nas.env,
    )

    assert res.returncode == 0, res.stderr
    assert nas.calls() == []


def test_deploy_runs_steps_in_order(tmp_path):
    nas = FakeNas(tmp_path, "chosung-daily", FAKE_GIT_BRANCH="main")
    res = nas.deploy("prod")

    assert res.returncode == 0, res.stdout + res.stderr
    steps = [
        line
        for line in nas.calls()
        if not line.startswith("sleep") and "rev-parse" not in line
    ]
    assert steps == [
        "git pull --ff-only origin main",
        "docker compose -f docker-compose.prod.yml -p chosung-daily-prod "
        "--env-file .env up -d --build",
        "docker compose -f docker-compose.prod.yml -p chosung-daily-prod "
        "--env-file .env exec -T app uv run flask db upgrade",
        "docker compose -f docker-compose.prod.yml -p chosung-daily-prod "
        "--env-file .env config --services",
        "docker compose -f docker-compose.prod.yml -p chosung-daily-prod "
        "--env-file .env ps --services --filter status=running",
        "docker compose -f docker-compose.prod.yml -p chosung-daily-prod "
        "--env-file .env port app 5000",
        "curl -fsS --max-time 5 http://127.0.0.1:8089/health",
    ]


def test_deploy_uses_the_port_compose_actually_published(tmp_path):
    """포트는 env 파일의 APP_PORT 가 진실 — 스크립트에 또 적지 않고 compose 에 물어본다."""
    nas = FakeNas(
        tmp_path,
        "chosung-daily-develop",
        FAKE_GIT_BRANCH="develop",
        FAKE_DOCKER_PORT="127.0.0.1:8090",
    )
    res = nas.deploy("develop")

    assert res.returncode == 0, res.stdout + res.stderr
    assert "curl -fsS --max-time 5 http://127.0.0.1:8090/health" in nas.calls()


def test_deploy_aborts_when_checkout_is_missing(tmp_path):
    nas = FakeNas(tmp_path, "chosung-daily")
    res = nas.deploy("develop")

    assert res.returncode != 0
    assert "chosung-daily-develop" in res.stderr
    assert nas.calls() == []


def test_deploy_aborts_when_checkout_is_on_another_branch(tmp_path):
    """prod 디렉터리가 develop 에 가 있으면 pull 전에 멈춘다 — 엉뚱한 코드를 올리지 않는다."""
    nas = FakeNas(tmp_path, "chosung-daily", FAKE_GIT_BRANCH="develop")
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert "main" in res.stderr
    assert not any(line.startswith("docker") for line in nas.calls())


def test_deploy_fails_when_pull_fails(tmp_path):
    nas = FakeNas(tmp_path, "chosung-daily", FAKE_GIT_BRANCH="main", FAKE_GIT_FAIL="pull")
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert not any(line.startswith("docker") for line in nas.calls())


def test_deploy_fails_when_migration_fails(tmp_path):
    """마이그레이션이 깨지면 `/health` 를 보러 가지 않고 거기서 멈춘다."""
    nas = FakeNas(
        tmp_path,
        "chosung-daily",
        FAKE_GIT_BRANCH="main",
        FAKE_DOCKER_FAIL="db upgrade",
    )
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert "up -d --build" in " ".join(nas.calls())
    assert not any(line.startswith("curl") for line in nas.calls())


def test_deploy_fails_when_a_service_is_not_running(tmp_path):
    """worker 가 안 떴는데 /health 는 200 일 수 있다 — 5개 서비스를 다 확인한다."""
    nas = FakeNas(
        tmp_path,
        "chosung-daily",
        FAKE_GIT_BRANCH="main",
        FAKE_DOCKER_RUNNING="mysql redis app beat",
    )
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert "worker" in res.stderr
    assert not any(line.startswith("curl") for line in nas.calls())


def test_deploy_retries_health_until_it_answers(tmp_path):
    """재기동 직후 gunicorn 이 뜨는 데 몇 초 걸린다 — 바로 실패로 치지 않는다."""
    nas = FakeNas(
        tmp_path,
        "chosung-daily",
        FAKE_GIT_BRANCH="main",
        FAKE_CURL_FAILS="2",
    )
    res = nas.deploy("prod")

    assert res.returncode == 0, res.stdout + res.stderr
    assert len([line for line in nas.calls() if line.startswith("curl")]) == 3


def test_deploy_fails_when_health_never_answers(tmp_path):
    nas = FakeNas(
        tmp_path,
        "chosung-daily",
        FAKE_GIT_BRANCH="main",
        FAKE_CURL_FAILS="999",
    )
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert "/health" in res.stderr
    curls = [line for line in nas.calls() if line.startswith("curl")]
    assert len(curls) == 10, "무한 재시도 금지 — 워크플로가 빨갛게 멈춰야 한다"
