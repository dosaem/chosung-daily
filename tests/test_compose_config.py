"""compose/배포 설정 파일의 계약 테스트.

prod 와 develop 을 같은 NAS 에서 동시에 돌리려면 compose 파일에 환경별로
달라지는 값(프로젝트명·포트·env 파일)이 하드코딩돼 있으면 안 된다. 그런데
이 조건은 파일을 눈으로 봐야만 알 수 있어서 쉽게 되돌아간다 — 그래서 설정
파일 자체를 읽어서 검증한다(도커를 띄우지 않는다. 실제 기동 검증은
docs/RELEASE.md 의 로컬 검증 절차).
"""

import re
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


# ------------------------------------------------- 컨테이너가 실제로 받는 env
#
# `environment:` 와 `env_file:` 을 따로 보면 "선언돼 있다" 까지만 알 수 있다.
# 컨테이너 안에서 실제로 보이는 값은 둘을 합친 것이고(`environment` 가 이긴다),
# `${VAR}`·`${VAR:-기본값}` 은 **`--env-file` 쪽에서만** 치환된다 — env 파일에
# 적어둔 값이 자동으로 컨테이너까지 흘러가지 않는다. 이 차이에서 티켓 36 의
# 두 결함이 나왔다(backup 에 인증서 경로가 안 들어가고, app 의 LOG_DIR 이
# 호스트 경로인 채로 들어갔다). 그래서 **합친 결과**를 본다.

_PLACEHOLDER = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:?-)?([^}]*)\}")


def _interpolate(value, env):
    """compose 의 `${VAR}`·`${VAR-기본값}`·`${VAR:-기본값}` 치환.

    `:-` 는 "없거나 비었으면 기본값", `-` 는 "없으면 기본값" 이다.
    """

    def replace(match):
        name, separator, default = match.groups()
        if separator == ":-":
            return env.get(name) or default
        if separator == "-":
            return env.get(name, default)
        return env.get(name, "")

    return _PLACEHOLDER.sub(replace, value)


def _container_env(compose, service, env_filename):
    """`docker compose --env-file <파일> config` 가 그 서비스에 넣는 환경변수."""
    env_file_values = _env_example(env_filename)
    merged = dict(env_file_values) if "env_file" in compose["services"][service] else {}
    for key, value in compose["services"][service].get("environment", {}).items():
        merged[key] = _interpolate(str(value), env_file_values)
    return merged


ENV_EXAMPLES = [".env.prod.example", ".env.develop.example"]


@pytest.mark.parametrize("env_filename", ENV_EXAMPLES)
def test_the_backup_container_receives_the_encryption_certificate(prod_compose, env_filename):
    """36: 인증서 경로가 backup 까지 안 가면 매일 백업이 통째로 실패한다.

    `scripts/backup.sh` 는 이 값이 비면 덤프를 만들지 않고 끝낸다 — 평문 백업을
    남기지 않기 위한 설계라, 전달이 빠지면 "암호화 보관" 이 아니라 "백업 없음" 이
    된다. env 파일에 적어두는 것만으로는 전달되지 않는다.
    """
    env = _container_env(prod_compose, "backup", env_filename)

    assert env.get("BACKUP_ENCRYPTION_CERT_FILE") == "/backups/backup-cert.pem"


@pytest.mark.parametrize("env_filename", ENV_EXAMPLES)
@pytest.mark.parametrize("service", ["app", "backup"])
def test_the_log_dir_the_container_sees_is_the_mount_target(prod_compose, service, env_filename):
    """36: 컨테이너 안의 `LOG_DIR` 은 bind mount 의 **컨테이너 쪽** 경로여야 한다.

    env 파일의 `LOG_DIR` 은 호스트 폴더(`./logs`)다. 그대로 app 에 흘러가면
    Gunicorn 이 WORKDIR(`/srv`) 기준의 `/srv/logs/access.log` 에 쓰고, backup 은
    `/logs` 만 회전한다 — 접속기록이 컨테이너와 함께 사라지고 1년 보관·만료
    삭제가 하나도 안 걸린다.
    """
    mount_target = next(
        spec.rsplit(":", 1)[1]
        for spec in prod_compose["services"][service]["volumes"]
        if spec.endswith(":/logs")
    )
    env = _container_env(prod_compose, service, env_filename)

    assert env.get("LOG_DIR") == mount_target
