"""E2E 스택 스크립트(`scripts/e2e_stack.sh`·`e2e_web.sh`·`scripts/e2e/*`)의 계약 테스트.

왜 pytest 가 이걸 보는가: 티켓 43·44 의 앱 E2E 가 **같은 스택**을 쓴다. 전용 DB 이름이나
Redis 번호가 조용히 바뀌면 다른 워커의 pytest 를 지우고, `PINNED` 와 시드 CSV 가 어긋나면
브라우저를 다 띄운 뒤에야 알게 된다. 둘 다 여기서 1초에 보인다.

브라우저 시나리오 자체는 pytest 가 돌리지 않는다 — 실제 스택이 떠 있어야 하고
(`scripts/e2e_web.sh`), 그걸 pytest 에 넣으면 단위 테스트 한 판이 몇 분이 된다.
"""

import csv
import re
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


def _source_env(ticket: str) -> subprocess.CompletedProcess:
    """`env.sh` 를 source 하는 것 자체의 성패. 배정표에 없는 티켓은 실패해야 한다."""
    return subprocess.run(
        ["bash", "-c", f'E2E_TICKET={ticket} source "{E2E_DIR / "env.sh"}"'],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )


# 같은 머신에서 동시에 뜨는 E2E 스택들. `env.sh` 의 배정표와 같은 티켓 집합이다.
E2E_TICKETS = ("42", "43", "44")
# E2E 가 건드리면 안 되는 Redis DB 번호: 0 로컬 개발, 1 pytest 기본(`TestingConfig`),
# 5 티켓 42 의 pytest(코디네이터가 `TEST_REDIS_URL` 로 배정). `down` 의 flushdb 가
# 이 중 하나를 잡으면 돌고 있는 남의 판을 지운다.
RESERVED_REDIS_DBS = {"0", "1", "5"}


def test_resources_carry_the_ticket_number():
    """티켓 번호 하나만 바꾸면 DB·포트·**Redis 번호**가 전부 갈린다 — 43·44 가 42 와
    같은 자원을 쓰면 서로의 DB 를 drop 하고 Redis 를 flush 한다."""
    t42 = _env_values("42")
    t43 = _env_values("43")

    assert t42["db"] == "chosung_daily_e2e_t42"
    assert t43["db"] == "chosung_daily_e2e_t43"
    assert t42["port"] != t43["port"]
    assert t42["port_nostore"] != t43["port_nostore"]
    assert t42["redis_db"] != t43["redis_db"]
    # 같은 티켓 안에서도 두 앱 인스턴스가 포트를 공유하면 둘째가 못 뜬다.
    assert t42["port"] != t42["port_nostore"]


def test_every_ticket_gets_its_own_redis_db():
    """D-42-5: Redis 키에는 스키마 구분이 없다. 두 스택이 한 번호를 쓰면 `puzzle:`
    캐시가 남의 퍼즐 id 를 내보내고 `lb:`·`stats:` 가 섞이며, 한쪽의 `down`(flushdb)이
    상대의 실행 중 상태를 지운다. DB 이름·포트처럼 번호도 티켓별로 달라야 한다."""
    assigned = {ticket: _env_values(ticket)["redis_db"] for ticket in E2E_TICKETS}
    assert len(set(assigned.values())) == len(assigned), f"Redis 번호가 겹친다: {assigned}"
    for ticket, number in assigned.items():
        assert number, f"티켓 {ticket} 에 Redis 번호가 없다"
        assert number not in RESERVED_REDIS_DBS, f"티켓 {ticket} 이 예약 번호 {number} 를 쓴다"
        # Redis 기본 설정의 databases 16 을 넘으면 접속 자체가 안 된다.
        assert 0 <= int(number) < 16, f"티켓 {ticket} 의 번호 {number} 가 범위를 벗어났다"


def test_unassigned_ticket_refuses_instead_of_sharing_a_redis_db():
    """배정표에 없는 티켓이 기본값으로 떨어지면 조용히 남의 번호를 쓴다 — 거부해야
    사람이 표에 한 줄을 더한다."""
    done = _source_env("99")
    assert done.returncode != 0, done.stdout + done.stderr
    assert "99" in (done.stdout + done.stderr)
    # 직접 지정하면 돌아간다 — 표에 없는 티켓도 손으로 번호를 주면 쓸 수 있다.
    # bash 는 `VAR=x source ...` 의 값을 source 가 끝나면 버린다(POSIX 모드가 아니다) —
    # 그래서 뒤에서 읽으려면 미리 export 해야 한다.
    body = (
        "export E2E_TICKET=99 E2E_REDIS_DB=9\n"
        f'source "{E2E_DIR / "env.sh"}"\n'
        'echo "$E2E_REDIS_DB"\n'
    )
    explicit = subprocess.run(
        ["bash", "-c", body],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert explicit.returncode == 0, explicit.stderr
    assert explicit.stdout.strip() == "9"


def test_redis_url_carries_the_assigned_db():
    """`e2e_redis_url` 과 `E2E_REDIS_DB` 가 어긋나면 앱은 한 번호를, `down` 의
    flushdb(`redis-cli -n`)는 다른 번호를 본다."""
    for ticket in E2E_TICKETS:
        values = _env_values(ticket)
        assert values["redis_url"].endswith(f"/{values['redis_db']}"), values


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


# 브리프 "시나리오 (ko·en 각각)" 의 예외. **목록이 아니라 예외만** 적는다 — 새 스펙이
# 생기면 묻지 않고 ko·en 둘 다 요구하게 두는 쪽이 안전하다.
SINGLE_LANGUAGE_SPECS = {
    # 한 테스트가 ko↔en 전환 자체를 본다 — 언어로 나누면 검증할 것이 없어진다.
    "05-language-switch.spec.mjs",
    # 운영자 화면은 ko 전용이다(README "설계 판단 15.").
    "09-admin.spec.mjs",
}
BILINGUAL_SPECS = tuple(
    sorted(
        spec.name
        for spec in (WEB_E2E_DIR / "specs").glob("*.spec.mjs")
        if spec.name not in SINGLE_LANGUAGE_SPECS
    )
)


def _lang_loop(spec_name: str) -> list[str]:
    """스펙 파일이 도는 언어 목록. `for (const lang of ["ko", "en"])` 를 읽는다."""
    source = (WEB_E2E_DIR / "specs" / spec_name).read_text()
    found = re.search(r"for \(const lang of \[([^\]]*)\]\)", source)
    return re.findall(r'"(\w+)"', found.group(1)) if found else []


@pytest.mark.parametrize("spec_name", BILINGUAL_SPECS)
def test_scenario_runs_in_both_languages(spec_name):
    """D-42-6: ko 만 돌면 en 사전의 문구와 en 퍼즐의 경로를 아무도 보지 않는다
    (시나리오 4 는 en streak, 8 은 en 오프라인·오류 문구)."""
    assert _lang_loop(spec_name) == ["ko", "en"], spec_name


def test_pinned_words_cover_every_day_the_streak_scenario_advances():
    """시나리오 4 는 한 판마다 `advance-day` 를 부른다 — (언어 수 * 뷰포트 수)번 돈다.
    k 번째 판은 `PINNED[k-1]`(1일차)과 `PINNED[k]`(2일차)를 쓰므로, 언어마다
    (판 수 + 1)개를 못박아야 마지막 판이 "manifest 에 오늘 퍼즐이 없다" 로 안 깨진다.
    날짜 시프트는 언어를 가리지 않으므로 ko·en 둘 다 같은 수가 필요하다."""
    runs = len(_lang_loop("10-streak.spec.mjs"))
    config = (WEB_E2E_DIR / "playwright.config.mjs").read_text()
    viewports = len(re.findall(r'name: "[a-z]+-\d+"', config))
    assert runs, "시나리오 4 가 언어를 돌지 않는다"
    assert viewports, "playwright.config.mjs 에서 뷰포트를 못 읽었다"
    needed = runs * viewports + 1
    for language, answers in PINNED.items():
        assert len(answers) >= needed, (
            f"{language.value} PINNED 가 {len(answers)}개 — 하루 넘기기 "
            f"{runs * viewports}번에는 {needed}개가 필요하다"
        )


@pytest.mark.parametrize(
    "spec", sorted((WEB_E2E_DIR / "specs").glob("*.spec.mjs")), ids=lambda p: p.name
)
def test_no_spec_types_a_hardcoded_answer(spec):
    """D-42-7: 제출할 문자열을 적어두면 시드가 못박은 단어의 **길이**에 묶인다 —
    4글자 단어가 오늘이 되는 순간 서버가 길이 검증으로 막아 시도가 아예 안 생기고,
    그 뒤의 단정("교체 불가" 등)은 무엇도 검증하지 못한다. 정답에서 만들어야 한다
    (`nearMiss`/`wrongGuesses`)."""
    literals = re.findall(r"guess\([^,]+,\s*[\"']", spec.read_text())
    assert not literals, f"{spec.name} 가 제출 문자열을 하드코딩했다: {literals}"


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
