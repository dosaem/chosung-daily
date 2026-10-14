"""웹 요청 접근 로그 — Gunicorn 설정과 일 회전·보관 스크립트(티켓 36).

DB 감사 로그(`tests/test_access_log.py`)가 "누가 개인정보를 처리했나" 를 남기는
쪽이고, 이 파일은 그 밖의 **모든 요청**이 파일로 모이는 쪽이다. 고시(개인정보의
안전성 확보조치 기준) 제8조는 둘 다 접속기록으로 보고 보관 기간·점검을 요구한다.

회전 스크립트는 실제로 실행해서 본다 — `curl` 만 PATH 스텁으로 바꾸고 gzip·find·
date·cp 는 진짜를 쓴다(`tests/test_backup_restore.py` 와 같은 방식).
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
DAY = 86400


@pytest.fixture(scope="module")
def gunicorn_config():
    """`gunicorn.conf.py` 를 그대로 실행해 설정값을 읽는다.

    import 가 아니라 exec 로 읽는 이유: 이 파일은 패키지 밖(레포 루트)에 있고,
    Gunicorn 도 `-c` 로 받아 같은 방식으로 실행한다.
    """
    source = (ROOT / "gunicorn.conf.py").read_text(encoding="utf-8")
    namespace: dict[str, object] = {"__file__": str(ROOT / "gunicorn.conf.py")}
    exec(compile(source, "gunicorn.conf.py", "exec"), namespace)
    return namespace


def test_requests_are_logged_to_a_file_under_log_dir(gunicorn_config):
    """Gunicorn 기본값은 "접근 로그 없음" 이다 — 명시적으로 파일을 지정한다."""
    assert gunicorn_config["accesslog"] == f"{gunicorn_config['LOG_DIR']}/access.log"
    assert gunicorn_config["LOG_DIR"] == os.environ.get("LOG_DIR", "/logs")


def test_the_access_log_format_records_what_the_notice_says(gunicorn_config):
    fmt = gunicorn_config["access_log_format"]

    assert "%(h)s" in fmt, "원격 IP"
    assert "%(t)s" in fmt, "시각"
    assert "%(m)s" in fmt, "메서드"
    assert "%(U)s" in fmt, "경로(쿼리 제외)"
    assert "%(s)s" in fmt, "상태 코드"
    assert "%(b)s" in fmt, "응답 크기"
    assert "%({user-agent}i)s" in fmt, "User-Agent"
    assert "%(L)s" in fmt, "응답 시간"


def test_the_access_log_format_excludes_tokens_cookies_and_query_strings(gunicorn_config):
    """로그에 비밀값을 남기지 않는다. 토큰·백업 코드가 URL 에 오지는 않지만
    포맷에서 명시적으로 뺀다 — 나중에 쿼리로 뭔가를 받게 되면 조용히 새어 나간다."""
    fmt = gunicorn_config["access_log_format"].lower()

    assert "authorization" not in fmt
    assert "cookie" not in fmt
    assert "%(q)s" not in fmt
    # `%(r)s`(요청 줄)은 쿼리스트링을 통째로 담는다 — `%(m)s %(U)s` 로 쪼갰다.
    assert "%(r)s" not in fmt


@pytest.mark.parametrize("filename", ["Dockerfile", "docker-compose.prod.yml"])
def test_the_production_entrypoint_uses_the_gunicorn_config(filename):
    text = (ROOT / filename).read_text(encoding="utf-8")
    if filename == "Dockerfile":
        assert "gunicorn.conf.py" in text
    else:
        assert "LOG_DIR" in text


@pytest.fixture(scope="module")
def prod_compose():
    return yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("service", ["app", "backup"])
def test_the_log_directory_is_bind_mounted_like_the_backup_directory(prod_compose, service):
    """앱이 쓰고 backup 컨테이너의 cron 이 회전한다 — 같은 호스트 폴더를 둘 다 본다.
    컨테이너가 날아가도 보관 기간 동안 남아야 하니 named volume 이 아니다."""
    assert "${LOG_DIR:-./logs}:/logs" in prod_compose["services"][service]["volumes"]


def test_the_app_container_knows_the_retention_period(prod_compose):
    env = prod_compose["services"]["backup"]["environment"]
    assert env["ACCESS_LOG_RETENTION_DAYS"] == "${ACCESS_LOG_RETENTION_DAYS:-365}"


# --------------------------------------------------- rotate-access-log.sh


@pytest.fixture
def rotate(tmp_path):
    """회전 스크립트 실행 환경. `curl`(Slack)만 스텁으로 바꾼다."""

    class Rotate:
        def __init__(self):
            self.bin = tmp_path / "bin"
            self.log = tmp_path / "log"
            self.logs = tmp_path / "logs"
            for d in (self.bin, self.log, self.logs):
                d.mkdir()
            curl = self.bin / "curl"
            curl.write_text(
                '#!/bin/bash\nprintf "%s\\n" "$@" >> "$STUB_LOG/curl.args"\n', encoding="utf-8"
            )
            curl.chmod(0o755)
            self.env = {
                "PATH": f"{self.bin}:{os.environ['PATH']}",
                "STUB_LOG": str(self.log),
                "HOME": str(tmp_path),
                "LOG_DIR": str(self.logs),
            }

        def access_log(self, body="127.0.0.1 [14/Oct/2026] GET / 200\n"):
            path = self.logs / "access.log"
            path.write_text(body, encoding="utf-8")
            return path

        def run(self, **env):
            return subprocess.run(
                [str(SCRIPTS / "rotate-access-log.sh")],
                capture_output=True,
                text=True,
                env={**self.env, **env},
                check=False,
            )

        def curl_args(self):
            path = self.log / "curl.args"
            return path.read_text(encoding="utf-8").splitlines() if path.exists() else None

    return Rotate()


def test_rotation_moves_todays_requests_into_a_gzipped_file(rotate):
    live = rotate.access_log("127.0.0.1 [14/Oct/2026] GET /privacy 200\n")

    result = rotate.run()
    assert result.returncode == 0, result.stderr

    rotated = sorted(rotate.logs.glob("access.log-*.gz"))
    assert len(rotated) == 1
    assert "GET /privacy" in gzip.decompress(rotated[0].read_bytes()).decode("utf-8")
    # 원본은 지우지 않고 비운다 — 앱 컨테이너의 Gunicorn 이 그 파일을 열어둔
    # 채라서, 지우면 회전 이후 요청이 사라진 inode 로 흘러간다.
    assert live.exists()
    assert live.read_text(encoding="utf-8") == ""


def test_rotation_does_nothing_when_there_were_no_requests(rotate):
    rotate.access_log("")

    assert rotate.run().returncode == 0
    assert list(rotate.logs.glob("access.log-*.gz")) == []


def test_rotation_is_safe_to_run_twice_in_one_day(rotate):
    rotate.access_log("first\n")
    assert rotate.run().returncode == 0
    rotate.access_log("second\n")

    result = rotate.run()

    assert result.returncode == 0, result.stderr
    rotated = sorted(rotate.logs.glob("access.log-*.gz"))
    assert len(rotated) == 1
    body = gzip.decompress(rotated[0].read_bytes()).decode("utf-8")
    assert "first" in body, body
    assert "second" in body, body


def test_rotated_files_past_the_retention_period_are_deleted(rotate):
    old = rotate.logs / "access.log-20250101.gz"
    borderline = rotate.logs / "access.log-20251013.gz"
    recent = rotate.logs / "access.log-20261010.gz"
    for path in (old, borderline, recent):
        path.write_bytes(gzip.compress(b"x"))
    now = time.time()
    os.utime(old, (now - 800 * DAY, now - 800 * DAY))
    os.utime(borderline, (now - 366 * DAY, now - 366 * DAY))
    os.utime(recent, (now - 2 * DAY, now - 2 * DAY))
    rotate.access_log()

    assert rotate.run().returncode == 0

    assert not old.exists()
    assert not borderline.exists()
    assert recent.exists()


def test_the_file_retention_period_is_configurable(rotate):
    """기본값은 법정 최소 기간(1년)이고, 상향 요건이 생기면 설정값만 올린다."""
    old = rotate.logs / "access.log-20251013.gz"
    old.write_bytes(gzip.compress(b"x"))
    now = time.time()
    os.utime(old, (now - 400 * DAY, now - 400 * DAY))

    assert rotate.run(ACCESS_LOG_RETENTION_DAYS="730").returncode == 0
    assert old.exists()

    assert rotate.run(ACCESS_LOG_RETENTION_DAYS="365").returncode == 0
    assert not old.exists()


def test_a_failed_prune_tells_the_operator(rotate):
    """정리가 안 되면 보관 기간을 넘긴 접속기록이 계속 남는다 — 조용히 넘기지 않는다."""
    find = rotate.bin / "find"
    find.write_text(
        '#!/bin/bash\ncase "$*" in *-delete*) echo "find: cannot delete" >&2; exit 1;; esac\n'
        'exec /usr/bin/find "$@"\n',
        encoding="utf-8",
    )
    find.chmod(0o755)
    rotate.access_log()

    result = rotate.run(SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")

    assert result.returncode != 0
    args = rotate.curl_args()
    assert args is not None, "보관 기간 정리 실패가 알림 없이 끝났다"
    assert "https://hooks.example.test/T/B/XYZ" in args
    assert "access log" in "\n".join(args).lower()


def test_rotation_succeeds_quietly(rotate):
    rotate.access_log()

    result = rotate.run(SLACK_WEBHOOK_URL="https://hooks.example.test/T/B/XYZ")

    assert result.returncode == 0
    assert rotate.curl_args() is None


def test_the_backup_container_cron_also_rotates_the_access_log():
    """새 컨테이너를 만들지 않는다 — 이미 매일 도는 backup 컨테이너가 같이 한다."""
    cron = (SCRIPTS / "backup-cron.sh").read_text(encoding="utf-8")

    assert "rotate-access-log.sh" in cron
