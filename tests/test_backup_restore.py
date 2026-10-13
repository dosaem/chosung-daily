"""매일 백업 컨테이너와 복구 스크립트의 동작 테스트.

백업은 셸 스크립트 3개(`scripts/backup.sh`, `scripts/backup-cron.sh`,
`scripts/restore.sh`)와 compose 의 `backup` 서비스로 돼 있다. 스크립트를 실제로
실행해서 검증한다 — `mysqldump`·`curl`·`docker` 는 PATH 앞에 끼운 스텁으로
바꿔치기하고(인자와 stdin 을 파일로 기록), gzip·find·date 는 진짜를 쓴다.
그래서 "덤프가 gzip 으로 떨어지는지", "14일 지난 파일이 지워지는지",
"실패하면 Slack 으로 쏘는지" 는 흉내가 아니라 스크립트가 한 일을 본다.

MySQL 컨테이너를 띄우는 실제 복구 리허설은 `docs/RELEASE.md` "복구 리허설" 절.
"""

import gzip
import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"

DAY = 86400


# ---------------------------------------------------------------- 스텁 환경


def _write_stub(bin_dir, name, body):
    path = bin_dir / name
    path.write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def stub(tmp_path):
    """PATH 스텁 + 호출 기록 디렉터리를 가진 셸 실행 환경."""

    class Stub:
        def __init__(self):
            self.bin = tmp_path / "bin"
            self.log = tmp_path / "log"
            self.dumps = tmp_path / "dumps"
            self.tmp = tmp_path / "tmp"
            for d in (self.bin, self.log, self.dumps, self.tmp):
                d.mkdir()
            self.env = {
                "PATH": f"{self.bin}:{os.environ['PATH']}",
                "STUB_LOG": str(self.log),
                "HOME": str(tmp_path),
                "TMPDIR": str(self.tmp),
                # 이 값이 스텁 인자 기록에 남으면 안 된다(아래 테스트가 확인한다).
                "MYSQL_ROOT_PASSWORD": "s3cret-root-pw",
                "MYSQL_DATABASE": "chosung_daily",
                "MYSQL_HOST": "mysql",
                "DUMP_DIR": str(self.dumps),
            }

        def write(self, name, body):
            _write_stub(self.bin, name, body)

        def run(self, script, *args, **env):
            return subprocess.run(
                [str(SCRIPTS / script), *args],
                capture_output=True,
                text=True,
                env={**self.env, **env},
                cwd=str(ROOT),
            )

        def args(self, name):
            path = self.log / f"{name}.args"
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8").splitlines()

        def calls(self, name):
            return len(list(self.log.glob(f"{name}.*.args")))

    s = Stub()
    # mysqldump: 인자를 기록하고 가짜 덤프를 stdout 으로 흘린다.
    s.write(
        "mysqldump",
        'printf "%s\\n" "$@" > "$STUB_LOG/mysqldump.args"\n'
        'echo "-- fake dump of $*"\n'
        "echo \"INSERT INTO word VALUES (1,'사과');\"",
    )
    # curl: 인자를 호출마다 새 파일에 기록한다(몇 번 불렸는지도 세려고).
    s.write(
        "curl",
        'n=$(ls "$STUB_LOG" | grep -c "^curl\\." || true)\n'
        'printf "%s\\n" "$@" > "$STUB_LOG/curl.$n.args"\n'
        'printf "%s\\n" "$@" >> "$STUB_LOG/curl.args"',
    )
    return s


# ---------------------------------------------------------------- backup.sh


def test_backup_writes_gzipped_dump(stub):
    result = stub.run("backup.sh")
    assert result.returncode == 0, result.stderr

    dumps = sorted(stub.dumps.glob("*.sql.gz"))
    assert len(dumps) == 1
    assert dumps[0].name.startswith("chosung_daily-")
    body = gzip.decompress(dumps[0].read_bytes()).decode("utf-8")
    assert "INSERT INTO word" in body


def test_backup_dump_is_consistent_and_restorable_whole_database(stub):
    """--single-transaction(잠금 없는 일관된 스냅샷) + --databases/--add-drop-database
    (복구 때 DB 를 지우고 다시 만들어 덤프 이후 생긴 행이 남지 않음)."""
    stub.run("backup.sh")
    args = stub.args("mysqldump")
    assert "--single-transaction" in args
    assert "--add-drop-database" in args
    assert "--databases" in args
    assert "chosung_daily" in args
    assert "-hmysql" in args or "mysql" in args


def test_backup_never_puts_password_on_the_command_line(stub):
    """`ps` 에 비밀번호가 보이면 안 된다 — defaults-extra-file 로 넘긴다."""
    stub.run("backup.sh")
    args = stub.args("mysqldump")
    assert all("s3cret-root-pw" not in a for a in args)
    assert any(a.startswith("--defaults-extra-file=") for a in args)
    # 비밀번호를 담은 임시 파일은 실행이 끝나면 남지 않는다.
    assert list(Path(stub.env["TMPDIR"]).iterdir()) == []


def test_backup_keeps_14_days_and_deletes_older(stub):
    old = stub.dumps / "chosung_daily-20260101-040000.sql.gz"
    borderline = stub.dumps / "chosung_daily-20260108-040000.sql.gz"
    recent = stub.dumps / "chosung_daily-20260112-040000.sql.gz"
    keep_me = stub.dumps / "README.txt"
    for path in (old, borderline, recent, keep_me):
        path.write_bytes(b"x")
    now = time.time()
    os.utime(old, (now - 30 * DAY, now - 30 * DAY))
    os.utime(borderline, (now - 14 * DAY - 60, now - 14 * DAY - 60))
    os.utime(recent, (now - 2 * DAY, now - 2 * DAY))
    os.utime(keep_me, (now - 99 * DAY, now - 99 * DAY))

    assert stub.run("backup.sh").returncode == 0

    assert not old.exists()
    assert not borderline.exists()
    assert recent.exists()
    assert keep_me.exists(), "덤프가 아닌 파일은 건드리지 않는다"


def test_backup_retention_days_is_configurable(stub):
    old = stub.dumps / "chosung_daily-20260101-040000.sql.gz"
    old.write_bytes(b"x")
    now = time.time()
    os.utime(old, (now - 5 * DAY, now - 5 * DAY))

    assert stub.run("backup.sh", BACKUP_RETENTION_DAYS="30").returncode == 0
    assert old.exists()

    assert stub.run("backup.sh", BACKUP_RETENTION_DAYS="3").returncode == 0
    assert not old.exists()


def test_backup_notifies_slack_on_failure(stub):
    stub.write("mysqldump", 'echo "mysqldump: Got error 2003" >&2\nexit 2')

    result = stub.run("backup.sh", SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")

    assert result.returncode != 0
    args = stub.args("curl")
    assert args is not None, "실패했는데 Slack 알림이 없다"
    assert "https://hooks.example.test/T/B/XYZ" in args
    payload = "\n".join(args)
    assert "backup" in payload.lower()
    assert "chosung_daily" in payload


def test_backup_failure_leaves_no_partial_dump(stub):
    stub.write("mysqldump", "exit 2")
    stub.run("backup.sh", SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")
    assert list(stub.dumps.iterdir()) == []


def test_backup_without_webhook_is_silent_but_still_fails(stub):
    """SLACK_WEBHOOK_URL 이 없으면 알림만 건너뛴다(스크립트가 멈추진 않는다)."""
    stub.write("mysqldump", "exit 2")
    result = stub.run("backup.sh", SLACK_WEBHOOK_URL="")
    assert result.returncode != 0
    assert stub.args("curl") is None


def test_backup_succeeds_quietly(stub):
    """성공했을 때 Slack 을 쏘지 않는다 — 매일 오는 알림은 아무도 안 본다."""
    result = stub.run("backup.sh", SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")
    assert result.returncode == 0
    assert stub.args("curl") is None


# ------------------------------------------------------------ backup-cron.sh


def test_cron_next_run_is_0400_kst(stub):
    """컨테이너가 TZ=Asia/Seoul 로 돌기 때문에 로컬 04:00 = 04:00 KST."""
    result = stub.run("backup-cron.sh", "--print-next", TZ="Asia/Seoul")
    assert result.returncode == 0, result.stderr

    # "04:00:00 +0900 (in 12345s)" 형태를 기대한다.
    out = result.stdout.strip()
    assert out.startswith("04:00:00"), out
    wait = int(out.split("in ")[1].rstrip("s)"))
    assert 0 < wait <= DAY


def test_cron_time_is_configurable(stub):
    result = stub.run("backup-cron.sh", "--print-next", BACKUP_AT="23:30", TZ="Asia/Seoul")
    assert result.stdout.strip().startswith("23:30:00"), result.stdout


# --------------------------------------------------------------- restore.sh


@pytest.fixture
def dump_file(tmp_path):
    path = tmp_path / "chosung_daily-20261013-040000.sql.gz"
    path.write_bytes(gzip.compress(b"DROP DATABASE IF EXISTS chosung_daily;\n"))
    return path


@pytest.fixture
def docker_stub(stub):
    stub.write(
        "docker",
        'printf "%s\\n" "$@" > "$STUB_LOG/docker.args"\ncat > "$STUB_LOG/docker.stdin"',
    )
    return stub


def test_restore_requires_a_dump_argument(docker_stub):
    result = docker_stub.run("restore.sh")
    assert result.returncode != 0
    assert "사용법" in result.stdout + result.stderr


def test_restore_rejects_missing_dump(docker_stub, tmp_path):
    result = docker_stub.run("restore.sh", "-y", str(tmp_path / "nope.sql.gz"))
    assert result.returncode != 0
    assert docker_stub.args("docker") is None


def test_restore_pipes_dump_into_the_project_mysql(docker_stub, dump_file):
    result = docker_stub.run(
        "restore.sh", "-y", str(dump_file), "chosung-daily-develop", TZ="Asia/Seoul"
    )
    assert result.returncode == 0, result.stderr

    args = docker_stub.args("docker")
    assert args[:1] == ["compose"]
    assert "-p" in args and args[args.index("-p") + 1] == "chosung-daily-develop"
    assert args[args.index("-f") + 1] == "docker-compose.prod.yml"
    assert "exec" in args and "-T" in args and "mysql" in args
    # 압축을 푼 SQL 이 컨테이너 stdin 으로 들어간다.
    assert (
        (docker_stub.log / "docker.stdin")
        .read_text(encoding="utf-8")
        .startswith("DROP DATABASE IF EXISTS")
    )


def test_restore_reads_password_inside_the_container(docker_stub, dump_file):
    """비밀번호를 스크립트가 알 필요가 없다 — mysql 컨테이너의 env 를 쓴다."""
    docker_stub.run("restore.sh", "-y", str(dump_file), "chosung-daily-prod")
    args = "\n".join(docker_stub.args("docker"))
    assert "$MYSQL_ROOT_PASSWORD" in args
    assert "s3cret-root-pw" not in args


def test_restore_defaults_project_to_compose_project_name(docker_stub, dump_file):
    docker_stub.run("restore.sh", "-y", str(dump_file), COMPOSE_PROJECT_NAME="chosung-daily-prod")
    args = docker_stub.args("docker")
    assert args[args.index("-p") + 1] == "chosung-daily-prod"


def test_restore_without_project_refuses(docker_stub, dump_file):
    result = docker_stub.run("restore.sh", "-y", str(dump_file), COMPOSE_PROJECT_NAME="")
    assert result.returncode != 0
    assert docker_stub.args("docker") is None


def test_restore_requires_confirmation_when_not_interactive(docker_stub, dump_file):
    """덮어쓰기는 되돌릴 수 없다 — 파이프/CI 에서는 -y 없이 안 돈다."""
    result = docker_stub.run("restore.sh", str(dump_file), "chosung-daily-prod")
    assert result.returncode != 0
    assert docker_stub.args("docker") is None


# --------------------------------------------------------- compose 의 backup 서비스


@pytest.fixture(scope="module")
def prod_compose():
    return yaml.safe_load(PROD_COMPOSE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def backup_service(prod_compose):
    return prod_compose["services"]["backup"]


def test_backup_service_reuses_the_mysql_image(prod_compose, backup_service):
    """mysqldump·gzip·curl·find 가 전부 들어 있는 이미지를 이미 당겨 뒀다."""
    assert backup_service["image"] == prod_compose["services"]["mysql"]["image"]
    assert backup_service["restart"] == "unless-stopped"


def test_backup_service_runs_the_cron_loop(backup_service):
    assert backup_service["entrypoint"] == ["/bin/bash", "/scripts/backup-cron.sh"]
    assert "./scripts:/scripts:ro" in backup_service["volumes"]


def test_backup_dumps_go_to_a_bind_mounted_host_directory(backup_service):
    """컨테이너가 죽어도 NAS 폴더에서 덤프를 꺼낼 수 있어야 한다."""
    assert "${BACKUP_DIR:-./backups}:/backups" in backup_service["volumes"]


def test_backup_service_env(backup_service):
    env = backup_service["environment"]
    assert env["TZ"] == "Asia/Seoul", "04:00 KST 로 돌려면 컨테이너 TZ 가 KST 여야 한다"
    assert env["BACKUP_AT"] == "04:00"
    assert env["BACKUP_RETENTION_DAYS"] == 14
    assert env["MYSQL_ROOT_PASSWORD"] == "${MYSQL_ROOT_PASSWORD}"
    assert env["SLACK_WEBHOOK_URL"] == "${SLACK_WEBHOOK_URL:-}"


def test_backup_service_waits_for_mysql(backup_service):
    assert backup_service["depends_on"] == {"mysql": {"condition": "service_healthy"}}


@pytest.mark.parametrize("filename", [".env.prod.example", ".env.develop.example"])
def test_env_examples_document_backup_dir_and_webhook(filename):
    lines = (ROOT / filename).read_text(encoding="utf-8").splitlines()
    env = dict(
        line.split("=", 1) for line in lines if "=" in line and not line.lstrip().startswith("#")
    )
    assert "BACKUP_DIR" in env
    assert "SLACK_WEBHOOK_URL" in env


def test_dumps_are_not_committed_or_baked_into_the_image():
    """BACKUP_DIR 기본값(./backups, develop 은 ./backups-develop)에 덤프가 쌓인다 —
    커밋되지도, Dockerfile 의 `COPY . .` 로 이미지에 들어가지도 않아야 한다."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert "backups*/" in ignored
    dockerignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert "backups*/" in dockerignored
