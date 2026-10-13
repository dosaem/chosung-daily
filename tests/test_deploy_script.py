"""`deploy/deploy.sh` 의 계약 테스트.

배포 스크립트는 NAS 에서만 실제로 돌지만, "어느 브랜치·디렉터리·env 파일·compose
프로젝트명을 고르는지" 와 "어떤 순서로 무엇을 실행하고 어디서 멈추는지" 는 로컬에서
확인할 수 있어야 한다. 두 가지로 검증한다.

1. `--dry-run`: 아무것도 실행하지 않고 실행할 명령만 찍는다 → 대상별 설정 확인.
2. 가짜 `git`/`docker`/`curl`/`sleep`(`tests/fake_nas_bin/`)을 PATH 앞에 두고 실제
   실행 → 단계 순서, 마이그레이션 실패 시 중단, `/health` 재시도까지 실제 분기를 지난다.

가짜 명령은 골라서 쓴다(`FakeNas(..., fakes=...)`). 커밋 고정은 **진짜 git** 과 임시
origin 으로, `/health` 판정은 **진짜 curl** 과 루프백 HTTP 서버로 확인한다 — 그 두
결함(D-20-1·D-20-2)은 가짜 명령으로는 재현되지 않는다.

도커를 띄우지 않는다. 실제 기동 검증은 `docs/RELEASE.md` 의 로컬/NAS 절차.
"""

import http.server
import os
import subprocess
import threading
from contextlib import contextmanager
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
        check=False,
    )


ALL_FAKES = ("git", "docker", "curl", "sleep")


class FakeNas:
    """가짜 NAS: 체크아웃 디렉터리와 PATH 앞에 둘 가짜 명령을 준비한다.

    `fakes` 에 적은 명령만 가짜로 바꾼다 — 빠진 명령은 진짜가 돈다.
    """

    def __init__(self, tmp_path, target_dir, fakes=ALL_FAKES, **overrides):
        self.base = tmp_path / "docker"
        self.checkout = self.base / target_dir
        self.checkout.mkdir(parents=True)
        self.log = tmp_path / "calls.log"
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        for name in fakes:
            (bin_dir / name).symlink_to(FAKE_BIN / name)
        self.env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "DEPLOY_BASE_DIR": str(self.base),
            "FAKE_LOG": str(self.log),
            "FAKE_CURL_COUNTER": str(tmp_path / "curl.count"),
            **overrides,
        }

    def deploy(self, *args):
        return subprocess.run(
            ["bash", str(DEPLOY_SH), *args],
            capture_output=True,
            text=True,
            env=self.env,
            check=False,
        )

    def calls(self):
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


def git(cwd, *args):
    """테스트용 진짜 git 호출."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def make_origin(tmp_path):
    """빈 임시 origin 저장소. `commit()` 으로 커밋을 쌓고 `clone()` 으로 가져간다."""
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "-c", "init.defaultBranch=main", "init", "-q")
    git(origin, "config", "user.email", "test@example.com")
    git(origin, "config", "user.name", "test")
    return origin


def clone(origin, checkout):
    git(checkout.parent, "clone", "-q", str(origin), str(checkout))


def commit(origin, text):
    (origin / "version").write_text(text, encoding="utf-8")
    git(origin, "add", "version")
    git(origin, "commit", "-qm", text)
    return git(origin, "rev-parse", "HEAD")


@contextmanager
def health_server(status, body=b'{"status":"ok"}', location=None):
    """`/health` 흉내를 내는 루프백 서버 — 진짜 curl 로 상태 코드 판정을 확인한다."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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
    assert f"git fetch --quiet origin {branch}" in out
    assert f"git merge --ff-only origin/{branch}" in out
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
        check=False,
    )

    assert res.returncode == 0, res.stderr
    assert nas.calls() == []


def test_deploy_runs_steps_in_order(tmp_path):
    nas = FakeNas(tmp_path, "chosung-daily", FAKE_GIT_BRANCH="main")
    res = nas.deploy("prod")

    assert res.returncode == 0, res.stdout + res.stderr
    steps = [
        line for line in nas.calls() if not line.startswith("sleep") and "rev-parse" not in line
    ]
    assert steps == [
        "git fetch --quiet origin main",
        "git merge --ff-only origin/main",
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
        r"curl -sS --max-time 5 -w \n%{http_code} http://127.0.0.1:8089/health",
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
    assert r"curl -sS --max-time 5 -w \n%{http_code} http://127.0.0.1:8090/health" in nas.calls()


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


@pytest.mark.parametrize("failing", ["fetch", "merge"])
def test_deploy_fails_when_pull_fails(tmp_path, failing):
    nas = FakeNas(tmp_path, "chosung-daily", FAKE_GIT_BRANCH="main", FAKE_GIT_FAIL=failing)
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


# --- D-20-1: CI 를 통과한 커밋만 빌드한다 (진짜 git + 임시 origin) ---------------
#
# 러너 checkout 의 head_sha 는 "러너가 읽는 deploy.sh" 만 정한다. NAS 는 자기 git 으로
# 브랜치를 가져오기 때문에, 커밋을 넘기지 않으면 그 사이 올라온(아직 CI 중이거나 실패한)
# 커밋을 빌드할 수 있다. 가짜 git 은 커밋 이동을 모델링하지 않아서 진짜 git 으로 본다.


def _real_git_nas(tmp_path, **overrides):
    """진짜 git + 가짜 docker/curl/sleep 으로 선 가짜 NAS."""
    return FakeNas(
        tmp_path,
        "chosung-daily",
        fakes=("docker", "curl", "sleep"),
        **overrides,
    )


def test_deploy_builds_exactly_the_commit_that_passed_ci(tmp_path):
    """넘긴 sha 가 브랜치 끝이면 체크아웃이 정확히 그 커밋으로 간다."""
    nas = _real_git_nas(tmp_path)
    origin = make_origin(tmp_path)
    commit(origin, "A")
    clone(origin, nas.checkout)
    sha_b = commit(origin, "B")

    res = nas.deploy("prod", sha_b)

    assert res.returncode == 0, res.stdout + res.stderr
    assert git(nas.checkout, "rev-parse", "HEAD") == sha_b
    assert (nas.checkout / "version").read_text(encoding="utf-8") == "B"


def test_deploy_refuses_a_commit_that_is_no_longer_the_branch_tip(tmp_path):
    """A 의 CI 로 시작한 배포가 그 뒤에 올라온 B 를 빌드하면 CI 선행 조건이 무의미하다."""
    nas = _real_git_nas(tmp_path)
    origin = make_origin(tmp_path)
    sha_a = commit(origin, "A")
    clone(origin, nas.checkout)
    sha_b = commit(origin, "B")

    res = nas.deploy("prod", sha_a)

    assert res.returncode != 0, res.stdout
    assert sha_b in res.stderr
    assert not any(line.startswith("docker") for line in nas.calls()), "빌드까지 가면 안 된다"
    assert (nas.checkout / "version").read_text(encoding="utf-8") == "A", "작업 트리도 그대로"


def test_deploy_refuses_a_commit_from_another_branch(tmp_path):
    """develop 의 커밋을 prod 로 넘기면 멈춘다 — main 끝이 아니기 때문."""
    nas = _real_git_nas(tmp_path)
    origin = make_origin(tmp_path)
    commit(origin, "A")
    clone(origin, nas.checkout)
    git(origin, "checkout", "-q", "-b", "develop")
    sha_dev = commit(origin, "develop 전용")

    res = nas.deploy("prod", sha_dev)

    assert res.returncode != 0
    assert not any(line.startswith("docker") for line in nas.calls())


def test_deploy_without_a_commit_takes_the_branch_tip(tmp_path):
    """NAS 에서 사람이 손으로 돌릴 때(sha 없음)는 그대로 브랜치 끝을 올린다."""
    nas = _real_git_nas(tmp_path)
    origin = make_origin(tmp_path)
    commit(origin, "A")
    clone(origin, nas.checkout)
    sha_b = commit(origin, "B")

    res = nas.deploy("prod")

    assert res.returncode == 0, res.stdout + res.stderr
    assert git(nas.checkout, "rev-parse", "HEAD") == sha_b


def test_unknown_third_argument_fails_with_usage(tmp_path):
    """sha 자리에 오타가 오면 조용히 무시하지 않는다."""
    res = run_dry("prod", "--dryrun")

    assert res.returncode == 2
    assert "prod|develop" in res.stderr


def test_dry_run_with_a_commit_runs_nothing(tmp_path):
    nas = FakeNas(tmp_path, "chosung-daily")
    res = nas.deploy("prod", "a" * 40, "--dry-run")

    assert res.returncode == 0, res.stderr
    assert nas.calls() == []


# --- D-20-2: /health 는 200 일 때만 성공이다 (진짜 curl + 루프백 서버) ------------


def test_deploy_fails_when_health_redirects_instead_of_200(tmp_path):
    """`curl -f` 는 302 에도 0 으로 끝난다 — 상태 코드를 봐야 로그인 리다이렉트를 잡는다."""
    with health_server(302, body=b"", location="/login") as port:
        nas = FakeNas(
            tmp_path,
            "chosung-daily",
            fakes=("git", "docker", "sleep"),
            FAKE_GIT_BRANCH="main",
            FAKE_DOCKER_PORT=f"127.0.0.1:{port}",
        )
        res = nas.deploy("prod")

    assert res.returncode != 0, res.stdout
    assert "HTTP 302" in res.stdout
    assert "배포 완료" not in res.stdout
    assert "200" in res.stderr


def test_deploy_succeeds_when_health_returns_200(tmp_path):
    """같은 경로로 200 이 오면 통과한다 — 항상 실패하는 검사가 아니다."""
    with health_server(200) as port:
        nas = FakeNas(
            tmp_path,
            "chosung-daily",
            fakes=("git", "docker", "sleep"),
            FAKE_GIT_BRANCH="main",
            FAKE_DOCKER_PORT=f"127.0.0.1:{port}",
        )
        res = nas.deploy("prod")

    assert res.returncode == 0, res.stdout + res.stderr
    assert '{"status":"ok"}' in res.stdout
    assert "== prod 배포 완료" in res.stdout


@pytest.mark.parametrize("status", ["301", "302", "404", "500"])
def test_deploy_fails_when_health_status_is_not_200(tmp_path, status):
    nas = FakeNas(
        tmp_path,
        "chosung-daily",
        FAKE_GIT_BRANCH="main",
        FAKE_CURL_STATUS=status,
    )
    res = nas.deploy("prod")

    assert res.returncode != 0
    assert f"HTTP {status}" in res.stdout
    curls = [line for line in nas.calls() if line.startswith("curl")]
    assert len(curls) == 10, "200 이 아니면 재시도하고 그 뒤 실패한다"
