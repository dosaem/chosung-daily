"""compose/배포 설정 파일의 계약 테스트.

prod 와 develop 을 같은 NAS 에서 동시에 돌리려면 compose 파일에 환경별로
달라지는 값(프로젝트명·포트·env 파일)이 하드코딩돼 있으면 안 된다. 그런데
이 조건은 파일을 눈으로 봐야만 알 수 있어서 쉽게 되돌아간다 — 그래서 설정
파일 자체를 읽어서 검증한다(도커를 띄우지 않는다. 실제 기동 검증은
docs/RELEASE.md 의 로컬 검증 절차).
"""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"


@pytest.fixture(scope="module")
def prod_compose():
    return yaml.safe_load(PROD_COMPOSE.read_text(encoding="utf-8"))


def _env_example(name):
    """예시 env 파일을 KEY=VALUE 딕트로 읽는다."""
    lines = (ROOT / name).read_text(encoding="utf-8").splitlines()
    return dict(
        line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#")
    )


def test_prod_compose_has_no_fixed_project_name(prod_compose):
    """프로젝트명은 `-p`/COMPOSE_PROJECT_NAME 으로 준다 — 고정이면 develop 을 못 띄운다."""
    assert "name" not in prod_compose


def test_prod_compose_has_no_fixed_container_names(prod_compose):
    """container_name 은 전역 유일해서 두 인스턴스 중 하나가 기동에 실패한다."""
    named = [name for name, svc in prod_compose["services"].items() if "container_name" in svc]
    assert named == []


def test_app_host_port_is_parametrized(prod_compose):
    assert prod_compose["services"]["app"]["ports"] == ["127.0.0.1:${APP_PORT}:5000"]


def test_env_file_is_parametrized(prod_compose):
    """env_file 이 .env 고정이면 develop 컨테이너가 prod 시크릿을 읽는다."""
    with_env_file = {
        name: svc["env_file"]
        for name, svc in prod_compose["services"].items()
        if "env_file" in svc
    }
    assert with_env_file == {
        "app": "${ENV_FILE:-.env}",
        "worker": "${ENV_FILE:-.env}",
        "beat": "${ENV_FILE:-.env}",
    }


def test_volumes_use_compose_project_naming(prod_compose):
    """볼륨 키 이름이 바뀌거나 `name:` 이 붙으면 기존 prod 볼륨이 안 붙는다."""
    volumes = prod_compose["volumes"]
    assert sorted(volumes) == ["mysql-data", "redis-data"]
    for spec in volumes.values():
        assert spec is None or "name" not in spec


@pytest.mark.parametrize(
    ("filename", "project", "port"),
    [
        (".env.prod.example", "chosung-daily-prod", "8089"),
        (".env.develop.example", "chosung-daily-develop", "8090"),
    ],
)
def test_env_examples_pin_project_and_port(filename, project, port):
    """`-p` 를 빼고 up 해도 같은 프로젝트에 붙도록 예시가 두 값을 갖고 있어야 한다."""
    env = _env_example(filename)
    assert env["COMPOSE_PROJECT_NAME"] == project
    assert env["APP_PORT"] == port


def test_dockerignore_excludes_non_backend_paths():
    """백엔드 이미지에 Flutter 앱·계획 문서·가상환경이 들어가면 안 된다."""
    entries = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert {"mobile/", ".scratch/", "review/", ".venv/", "tests/"} <= entries
