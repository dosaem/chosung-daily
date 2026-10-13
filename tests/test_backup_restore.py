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
import json
import os
import subprocess
import time
from datetime import date
from pathlib import Path

import pytest
import yaml

from app import create_app
from app.extensions import get_redis
from app.models import PuzzleLanguage
from app.services.puzzle_cache import _cache_key, get_cached_puzzle

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
            # 종료 코드는 테스트가 직접 본다(실패 경로를 검증하는 테스트가 있다).
            return subprocess.run(
                [str(SCRIPTS / script), *args],
                capture_output=True,
                text=True,
                env={**self.env, **env},
                cwd=str(ROOT),
                check=False,
            )

        def args(self, name):
            path = self.log / f"{name}.args"
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8").splitlines()

        def call_args(self, name, n):
            """n번째(0부터) 호출의 인자. 한 스크립트가 같은 명령을 여러 번 부를 때."""
            path = self.log / f"{name}.{n}.args"
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8").splitlines()

        def call_stdin(self, name, n):
            path = self.log / f"{name}.{n}.stdin"
            if not path.exists():
                return None
            return path.read_text(encoding="utf-8")

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


def test_backup_notifies_slack_when_the_dump_dir_cannot_be_created(stub):
    """D-21-1. 저장 경로·권한 문제로 디렉터리를 못 만들어도 백업은 실패한 것이다 —
    `set -e` 가 조용히 죽어버리면 운영자는 그 날 백업이 없는 걸 모른다."""
    broken = stub.dumps / "a-regular-file" / "dumps"
    (stub.dumps / "a-regular-file").write_text("x", encoding="utf-8")

    result = stub.run(
        "backup.sh",
        DUMP_DIR=str(broken),
        SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ",
    )

    assert result.returncode != 0
    args = stub.args("curl")
    assert args is not None, "디렉터리 준비 실패가 알림 없이 끝났다"
    assert "https://hooks.example.test/T/B/XYZ" in args
    assert "chosung_daily" in "\n".join(args)


def test_backup_notifies_slack_when_the_dump_cannot_be_moved_into_place(stub):
    """D-21-1. 덤프는 떴는데 제 이름으로 못 옮기면 그 날 백업은 없는 것과 같다."""
    stub.write("mv", 'echo "mv: Read-only file system" >&2\nexit 1')

    result = stub.run("backup.sh", SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")

    assert result.returncode != 0
    assert stub.args("curl") is not None, "mv 실패가 알림 없이 끝났다"
    assert list(stub.dumps.glob("*.sql.gz")) == [], "제 이름으로 못 옮긴 덤프가 남았다"


def test_backup_notifies_slack_when_retention_prune_fails(stub):
    """D-21-1. 정리가 안 되면 디스크가 차서 다음 백업부터 통째로 실패한다."""
    stub.write(
        "find",
        'case "$*" in *-delete*) echo "find: cannot delete" >&2; exit 1;; esac\n'
        'exec /usr/bin/find "$@"',
    )

    result = stub.run("backup.sh", SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")

    assert result.returncode != 0
    assert stub.args("curl") is not None, "보존 정리 실패가 알림 없이 끝났다"


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
    # restore.sh 는 docker 를 두 번 부른다(mysql 복원 → redis 파생 키 정리).
    # 호출마다 따로 기록해야 뒤 호출이 앞 호출 기록을 덮어쓰지 않는다.
    stub.write(
        "docker",
        'n=$(ls "$STUB_LOG" | grep -c "^docker\\..*\\.args" || true)\n'
        'printf "%s\\n" "$@" > "$STUB_LOG/docker.$n.args"\n'
        'cat > "$STUB_LOG/docker.$n.stdin"\n'
        'printf "%s\\n" "$@" >> "$STUB_LOG/docker.args"',
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
    assert "-p" in args
    assert args[args.index("-p") + 1] == "chosung-daily-develop"
    assert args[args.index("-f") + 1] == "docker-compose.prod.yml"
    assert "exec" in args
    assert "-T" in args
    assert "mysql" in args
    # 압축을 푼 SQL 이 컨테이너 stdin 으로 들어간다.
    assert docker_stub.call_stdin("docker", 0).startswith("DROP DATABASE IF EXISTS")


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


def test_restore_rejects_a_truncated_dump_before_touching_mysql(docker_stub, tmp_path):
    """D-21-2. `gzip -dc | mysql` 은 스트리밍이라 끝이 잘린 덤프여도 앞쪽의
    DROP/CREATE DATABASE 가 먼저 실행된다 — 복구 실패가 멀쩡하던 DB 를 날린다."""
    whole = gzip.compress(
        b"DROP DATABASE IF EXISTS chosung_daily;\nCREATE DATABASE chosung_daily;\n"
    )
    truncated = tmp_path / "chosung_daily-20261013-040000.sql.gz"
    truncated.write_bytes(whole[:-8])

    result = docker_stub.run("restore.sh", "-y", str(truncated), "chosung-daily-prod")

    assert result.returncode != 0
    assert docker_stub.args("docker") is None, "깨진 덤프의 SQL 이 이미 DB 로 흘러갔다"


def test_restore_rejects_a_file_that_is_not_a_dump(docker_stub, tmp_path):
    """D-21-2. 엉뚱한 파일을 줬을 때도 DB 를 건드리기 전에 멈춘다."""
    not_a_dump = tmp_path / "chosung_daily-notes.sql.gz"
    not_a_dump.write_text("이건 gzip 이 아니다", encoding="utf-8")

    result = docker_stub.run("restore.sh", "-y", str(not_a_dump), "chosung-daily-prod")

    assert result.returncode != 0
    assert docker_stub.args("docker") is None


def test_restore_invalidates_derived_redis_keys_after_the_database(docker_stub, dump_file):
    """D-21-3. Redis 는 MySQL 과 같이 되감기지 않는다 — 복구 전 퍼즐 캐시가
    남으면 앱이 복원된 DB 대신 그 값을 읽는다(26시간 TTL)."""
    result = docker_stub.run("restore.sh", "-y", str(dump_file), "chosung-daily-prod")
    assert result.returncode == 0, result.stderr

    redis_call = docker_stub.call_args("docker", 1)
    assert redis_call is not None, "MySQL 만 되감고 Redis 파생 키는 그대로 뒀다"
    assert "redis" in redis_call, redis_call
    assert redis_call[redis_call.index("-p") + 1] == "chosung-daily-prod"
    command = "\n".join(redis_call)
    for pattern in ("puzzle:*", "stats:*", "lb:*"):
        assert pattern in command, f"{pattern} 가 정리 대상에 없다"


def test_restore_does_not_wipe_the_celery_broker(docker_stub, dump_file):
    """D-21-3 의 수정이 과하면 안 된다 — 같은 Redis DB 에 celery 브로커가 산다."""
    docker_stub.run("restore.sh", "-y", str(dump_file), "chosung-daily-prod")
    command = "\n".join(docker_stub.call_args("docker", 1)).lower()
    assert "flushdb" not in command
    assert "flushall" not in command


def test_restore_leaves_redis_alone_when_the_database_restore_fails(docker_stub, dump_file):
    """DB 복원이 깨졌는데 캐시만 비우면, 앱이 반쪽 DB 를 다시 캐싱한다."""
    docker_stub.write("docker", 'echo "Error: No such service: mysql" >&2\nexit 1')
    result = docker_stub.run("restore.sh", "-y", str(dump_file), "chosung-daily-prod")
    assert result.returncode != 0


@pytest.fixture
def redis_exec_stub(stub):
    """docker 스텁이 redis 쪽 `sh -c` 를 진짜로 실행한다.

    `docker_stub` 은 인자와 stdin 만 기록하므로 restore.sh 안쪽 Redis 정리 셸이
    한 줄도 돌지 않는다 — 그래서 그 셸의 오류 전파(D-21-4)를 못 본다. 여기서는
    mysql 호출은 stdin 을 삼키고, redis 호출은 `sh -c '<본문>'` 을 그대로
    exec 해서 redis-cli 스텁과 함께 실제로 돌린다.
    """
    stub.write(
        "docker",
        'printf "%s\\n" "$@" >> "$STUB_LOG/docker.args"\n'
        'case " $* " in\n'
        '*" exec -T mysql "*)\n'
        '  cat > "$STUB_LOG/mysql.stdin"\n'
        "  ;;\n"
        '*" exec -T redis "*)\n'
        '  while [ $# -gt 0 ] && [ "$1" != sh ]; do shift; done\n'
        "  [ $# -gt 0 ] || exit 1\n"
        '  exec "$@"\n'
        "  ;;\n"
        "esac",
    )
    # redis-cli: REDIS_CLI_MODE 로 성공/SCAN 실패/DEL 실패를 고른다.
    stub.write(
        "redis-cli",
        'printf "%s\\n" "$@" >> "$STUB_LOG/redis-cli.args"\n'
        'case "${REDIS_CLI_MODE:-ok}" in\n'
        "scan-fails)\n"
        '  echo "Could not connect to Redis: Connection refused" >&2\n'
        "  exit 1\n"
        "  ;;\n"
        "del-fails)\n"
        '  case "$1" in\n'
        '  --scan) [ "$3" = "puzzle:*" ] && echo "puzzle:2026-10-13" ;;\n'
        "  del)\n"
        '    echo "Could not connect to Redis: Connection refused" >&2\n'
        "    exit 1\n"
        "    ;;\n"
        "  esac\n"
        "  ;;\n"
        "*)\n"
        '  case "$1" in\n'
        "  --scan)\n"
        '    [ "$3" = "puzzle:*" ] && printf "puzzle:2026-10-13\\npuzzle:2026-10-12\\n"\n'
        "    ;;\n"
        "  del) echo 1 ;;\n"
        "  esac\n"
        "  ;;\n"
        "esac\n"
        "exit 0",
    )
    return stub


def test_restore_deletes_every_derived_key_the_scan_found(redis_exec_stub, dump_file):
    """정리 셸을 실제로 돌려본다 — 찾은 키마다 DEL 이 나가고 수가 맞는다."""
    result = redis_exec_stub.run("restore.sh", "-y", str(dump_file), "chosung-daily-prod")
    assert result.returncode == 0, result.stderr

    calls = redis_exec_stub.args("redis-cli")
    assert "puzzle:2026-10-13" in calls
    assert "puzzle:2026-10-12" in calls
    assert "deleted 2 derived keys" in result.stdout, result.stdout


def test_restore_fails_when_the_redis_scan_cannot_run(redis_exec_stub, dump_file):
    """D-21-4. `for key in $(redis-cli --scan ...)` 는 치환이 죽어도 빈 목록을
    돌고 끝난다 — Redis 가 안 떠 있어도 "0개 지웠다" 로 성공해 보인다."""
    result = redis_exec_stub.run(
        "restore.sh", "-y", str(dump_file), "chosung-daily-prod", REDIS_CLI_MODE="scan-fails"
    )

    assert result.returncode != 0, result.stdout
    assert "완료" not in result.stdout, "캐시가 남았는데 복구 성공을 선언했다"
    assert "직접 확인하고 지워야 한다" in result.stderr


def test_restore_fails_when_deleting_a_derived_key_fails(redis_exec_stub, dump_file):
    """D-21-4. DEL 이 깨지면 그 키는 복구 전 값으로 남는다 — 세지 말고 멈춘다."""
    result = redis_exec_stub.run(
        "restore.sh", "-y", str(dump_file), "chosung-daily-prod", REDIS_CLI_MODE="del-fails"
    )

    assert result.returncode != 0, result.stdout
    assert "완료" not in result.stdout
    assert "deleted 1 derived keys" not in result.stdout, "못 지운 키를 지웠다고 셌다"


@pytest.mark.parametrize("doc", ["README.md", "docs/RELEASE.md"])
def test_restore_docs_do_not_sell_an_app_restart_as_cache_cleanup(doc):
    """D-21-3. `restart app worker beat` 는 Redis 를 비우지 않는다 — Redis 는
    별도 컨테이너고 퍼즐 캐시는 그 안에 있다."""
    text = (ROOT / doc).read_text(encoding="utf-8")
    # 돌려 쓰라고 내놓은 명령줄에 남아 있으면 안 된다(설명문에서 "이건 안 된다"
    # 고 언급하는 건 괜찮다).
    recipes = [line for line in text.splitlines() if "docker compose" in line and "restart" in line]
    assert recipes == [], f"앱 재시작은 캐시 정리가 아니다: {recipes}"
    assert "puzzle:" in text, "복구가 무효화하는 Redis 키를 문서가 밝혀야 한다"


def test_restarting_the_app_does_not_clear_the_puzzle_cache(app):
    """D-21-3 의 뿌리. 앱을 새로 띄워도(= `restart app worker beat`) Redis 의
    퍼즐 캐시는 그대로 살아 있다 — 그래서 restore.sh 가 직접 지운다."""
    stale_date = date(2099, 12, 21)
    get_redis().set(
        _cache_key(stale_date, PuzzleLanguage.KO),
        json.dumps(
            {
                "id": 212121,
                "chosung": "ㅍㄷ",
                "answer": "포도",
                "hint": "h",
                "category": "general",
                "mask": [{"t": "r", "c": "ㅍ"}, {"t": "r", "c": "ㄷ"}],
            }
        ),
        ex=60 * 60 * 26,
    )

    restarted = create_app("testing")
    with restarted.app_context():
        cached = get_cached_puzzle(stale_date, PuzzleLanguage.KO)
        assert cached is not None, "재시작만으로 캐시가 지워졌다"
        assert cached.id == 212121
        # restore.sh 가 하는 일: 파생 키를 직접 지운다.
        for key in get_redis().scan_iter(match="puzzle:*"):
            get_redis().delete(key)
        assert get_cached_puzzle(stale_date, PuzzleLanguage.KO) is None


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
