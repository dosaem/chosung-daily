"""E2E 스택 스크립트(`scripts/e2e_stack.sh`·`e2e_web.sh`·`scripts/e2e/*`)의 계약 테스트.

왜 pytest 가 이걸 보는가: 티켓 43·44 의 앱 E2E 가 **같은 스택**을 쓴다. 전용 DB 이름이나
Redis 번호가 조용히 바뀌면 다른 워커의 pytest 를 지우고, `PINNED` 와 시드 CSV 가 어긋나면
브라우저를 다 띄운 뒤에야 알게 된다. 둘 다 여기서 1초에 보인다.

브라우저 시나리오 자체는 pytest 가 돌리지 않는다 — 실제 스택이 떠 있어야 하고
(`scripts/e2e_web.sh`), 그걸 pytest 에 넣으면 단위 테스트 한 판이 몇 분이 된다.
"""

import csv
import subprocess
from pathlib import Path

import pytest

from app.services.word_service import WORD_CSV_COLUMNS, parse_word_input
from scripts.e2e.advance_day import DATE_KEYED_PREFIXES, DROPPED_PREFIXES, _shift_sql
from scripts.e2e.seed import EN_CSV, KO_CSV, PINNED

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
E2E_DIR = SCRIPTS / "e2e"
WEB_E2E_DIR = REPO_ROOT / "tests" / "e2e" / "web"


@pytest.mark.parametrize(
    "script",
    [SCRIPTS / "e2e_stack.sh", SCRIPTS / "e2e_web.sh", E2E_DIR / "env.sh"],
)
def test_scripts_exist_and_parse(script):
    """파일이 있고, bash 가 문법을 받아들인다."""
    assert script.exists(), script
    parsed = subprocess.run(
        ["bash", "-n", str(script)], capture_output=True, text=True, check=False
    )
    assert parsed.returncode == 0, parsed.stderr


@pytest.mark.parametrize("script", [SCRIPTS / "e2e_stack.sh", SCRIPTS / "e2e_web.sh"])
def test_scripts_are_executable(script):
    assert script.stat().st_mode & 0o111, f"{script.name} 에 실행 권한이 없다"


def _env_values(ticket: str) -> dict[str, str]:
    """`env.sh` 를 주어진 티켓 번호로 source 해서 결정된 값들을 읽는다."""
    body = (
        f'E2E_TICKET={ticket} source "{E2E_DIR / "env.sh"}"\n'
        'printf "%s\\n" "$E2E_DB" "$E2E_REDIS_DB" "$E2E_PORT" "$E2E_PORT_NOSTORE" '
        '"$(e2e_redis_url)" "$E2E_ADMIN_EMAIL"\n'
    )
    done = subprocess.run(
        ["bash", "-c", body], capture_output=True, text=True, cwd=REPO_ROOT, check=False
    )
    assert done.returncode == 0, done.stderr
    db, redis_db, port, port_nostore, redis_url, admin_email = done.stdout.split("\n")[:6]
    return {
        "db": db,
        "redis_db": redis_db,
        "port": port,
        "port_nostore": port_nostore,
        "redis_url": redis_url,
        "admin_email": admin_email,
    }


def test_resources_carry_the_ticket_number():
    """티켓 번호 하나만 바꾸면 DB·포트가 전부 갈린다 — 43·44 가 42 와 같은 자원을 쓰면
    서로의 DB 를 drop 하고 Redis 를 flush 한다."""
    t42 = _env_values("42")
    t43 = _env_values("43")

    assert t42["db"] == "chosung_daily_e2e_t42"
    assert t43["db"] == "chosung_daily_e2e_t43"
    assert t42["port"] != t43["port"]
    assert t42["port_nostore"] != t43["port_nostore"]
    # 같은 티켓 안에서도 두 앱 인스턴스가 포트를 공유하면 둘째가 못 뜬다.
    assert t42["port"] != t42["port_nostore"]


def test_redis_db_is_not_the_dev_or_pytest_one():
    """개발은 0, pytest(`TestingConfig`)는 1 이다. E2E 가 그 번호를 쓰면
    `down` 의 flushdb 가 남의 상태를 지운다."""
    assert _env_values("42")["redis_db"] not in {"0", "1"}


def test_admin_email_is_not_a_real_account():
    """시드가 만드는 운영자 계정은 실제 운영자 이메일이 아니어야 한다
    (CONTEXT.md 의 운영자 계정이 테스트 DB 에 들어가지 않게)."""
    assert _env_values("42")["admin_email"].endswith("@example.com")


@pytest.mark.parametrize(
    ("now", "refused"),
    [
        ("2026-10-15T23:55:00+09:00", True),  # 자정 5분 전
        ("2026-10-16T00:05:00+09:00", True),  # 자정 5분 뒤
        ("2026-10-15T23:45:00+09:00", False),  # 15분 전 — 한 판(~2분)이 들어간다
        ("2026-10-15T12:00:00+09:00", False),
    ],
)
def test_midnight_guard_refuses_only_near_kst_midnight(now, refused):
    """서버가 KST 벽시계를 쓰므로 자정을 넘기며 돌면 "오늘" 이 실행 중에 바뀐다.

    판정 **그 자체**를 돌린다(사본을 테스트에 적지 않는다 — 사본은 스크립트가 바뀌면
    낡는다). 그래서 가드가 `--now` 를 받는 파일로 따로 있다.
    """
    done = subprocess.run(
        ["python3", str(E2E_DIR / "guard_midnight.py"), "--now", now],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert (done.returncode != 0) is refused, done.stdout + done.stderr


def test_stack_actually_calls_the_midnight_guard():
    """가드가 있어도 안 부르면 아무것도 막지 못한다 — `up` 과 `seed` 양쪽에서 부른다."""
    stack = (SCRIPTS / "e2e_stack.sh").read_text()
    assert "guard_midnight()" in stack
    # 정의 1 + 호출 2(up, seed)
    assert stack.count("guard_midnight") >= 3


def test_e2e_web_resets_the_database_before_running():
    """시나리오 10(운영자 CSV 업로드)은 "추가 2개 · 중복 1개" 처럼 **빈 DB** 를 전제한
    수를 단정하고, 시나리오 4 는 저장된 날짜를 되돌린다. 한 판마다 새로 만들지 않으면
    둘 다 다른 것을 본다."""
    script = (SCRIPTS / "e2e_web.sh").read_text()
    order = [
        script.index('e2e_stack.sh" down'),
        script.index('e2e_stack.sh" up'),
        script.index('e2e_stack.sh" seed'),
        script.index("npx playwright test"),
    ]
    assert order == sorted(order), "down → up → seed → test 순서가 아니다"


def test_seed_pins_words_that_exist_in_the_csvs():
    """`seed.py` 의 `PINNED` 와 시드 CSV 가 어긋나면 시드가 중간에 멈춘다.
    브라우저를 다 띄운 뒤가 아니라 여기서 알아야 한다."""
    available = {}
    for path in (KO_CSV, EN_CSV):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                language = (row.get("language") or "ko").strip()
                available.setdefault(language, set()).add(row["answer"].strip())

    for language, answers in PINNED.items():
        missing = [a for a in answers if a not in available.get(language.value, set())]
        assert not missing, f"{language.value} 시드 CSV 에 없는 단어: {missing}"
        # 오늘·내일이 같은 단어면 "하루 넘기니 새 문제" 를 검증할 수 없다.
        assert len(set(answers)) == len(answers), f"{language.value} PINNED 에 중복: {answers}"


def test_en_seed_csv_is_loadable():
    """en 전용 CSV 가 운영자 업로드와 같은 규칙(`parse_word_input`)을 통과한다."""
    with open(EN_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        assert set(WORD_CSV_COLUMNS) <= {name.strip() for name in reader.fieldnames}
        rows = list(reader)

    assert rows, "en 시드 CSV 가 비어 있다"
    for row in rows:
        parsed = parse_word_input(
            row["language"], row["category"], row["answer"], row["hint"]
        )
        assert parsed.language.value == "en", f"{parsed.answer} 가 en 이 아니다"


def test_advance_day_shifts_every_date_holder():
    """하루를 되돌릴 때 빠뜨리면 안 되는 자리들. 하나라도 빠지면 연속 기록이
    "오늘 이미 풀었다" 나 "끊겼다" 로 읽힌다."""
    statements = " ".join(_shift_sql(1))
    for table_column in (
        "daily_puzzle SET puzzle_date",
        "daily_stats SET puzzle_date",
        "guest_stats SET last_solved_date",
    ):
        assert table_column in statements, f"{table_column} 를 안 옮긴다"
    # (puzzle_date, language) 유니크 키가 있어서 순서 없이 갱신하면 중복 키로 깨진다.
    assert statements.count("ORDER BY puzzle_date ASC") == 2
    # 순위는 Redis 에만 있다 — 지우면 어제 기록이 사라진다(옮겨야 한다).
    assert "lb:" in DATE_KEYED_PREFIXES
    assert "stats:" in DATE_KEYED_PREFIXES
    assert "lb:" not in DROPPED_PREFIXES
    # `RENAME` 은 대상 키를 조용히 덮어쓴다 — 오래된 날짜부터 옮겨야 두 번 넘겼을 때
    # 어제 순위표가 사라지지 않는다(SQL 의 `ORDER BY` 와 같은 이유).
    source = (E2E_DIR / "advance_day.py").read_text()
    assert "for parsed, key, suffix in sorted(moves)" in source
    # 캐시와 분당 카운터는 옮기지 않고 버린다.
    assert "puzzle:" in DROPPED_PREFIXES
    assert "ratelimit:" in DROPPED_PREFIXES


def test_e2e_artifacts_are_not_committed():
    """스크린샷에 게스트 토큰·백업 코드가 찍히고 접근 로그에 원격 IP 가 남는다."""
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert "e2e-artifacts/" in gitignore
    assert "tests/e2e/web/node_modules/" in gitignore


def test_readme_documents_how_to_run_e2e():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "## E2E (웹 브라우저)" in readme
    for mention in ("scripts/e2e_web.sh", "scripts/e2e_stack.sh", "chosung_daily_e2e_t42"):
        assert mention in readme, mention


def test_playwright_project_covers_both_viewports_serially():
    """두 뷰포트(1280·390)를 같은 시나리오로 돌리고, **직렬**이어야 한다 —
    시나리오들이 한 DB·한 Redis·한 서버를 공유하고 하나는 날짜를 되돌린다."""
    config = (WEB_E2E_DIR / "playwright.config.mjs").read_text()
    assert "desktop-1280" in config
    assert "mobile-390" in config
    assert "width: 1280" in config
    assert "width: 390" in config
    assert "workers: 1" in config
    assert "fullyParallel: false" in config
    # 재시도는 결함을 가린다 — 실제 스택 E2E 에서는 0 이다.
    assert "retries: 0" in config
