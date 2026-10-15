"""E2E 에서 "하루가 지났다" 를 만든다 — 앱 코드에 테스트용 시계를 넣지 않고.

코디네이터 결정(2026-10-15): 서버는 KST 벽시계를 그대로 쓰고, 날짜를 넘기는 건
**저장된 날짜를 하루 되돌리는** 쪽으로 한다. `datetime.now(KST)` 가 서비스 8곳에
흩어져 있어서 주입형 시계를 넣으려면 프로덕션 코드에 테스트 전용 경로를 만들어야
하는데, E2E 티켓이 그걸 들이는 건 비용이 더 크다고 봤다.

되돌리는 것들(= "오늘" 이 하루 전진한 것과 같은 상태):

- `daily_puzzle.puzzle_date` : 어제 푼 퍼즐이 어제가 되고, 내일 퍼즐이 오늘이 된다.
  시도 이력(`/me/history`)·배정표가 전부 이 컬럼에서 날짜를 읽으므로 이 한 번으로
  같이 움직인다(`attempt` 에는 날짜가 없다 — 퍼즐을 조인해서 읽는다).
- `guest_stats.last_solved_date` : 연속 기록 판정이 `today - 1` 과 비교하는 값이다.
  이게 안 움직이면 어제 푼 사람이 "오늘 이미 풀었다" 로 읽힌다.
- `daily_stats.puzzle_date` : Beat 가 만든 하루치 분포 스냅샷.
- Redis `lb:<날짜>:<언어>` · `stats:<날짜>:<언어>` : 키 이름에 날짜가 박혀 있어서
  이름을 하루 내려 rename 한다(순위표는 Redis 에만 있다 — 지우면 어제 기록이 사라진다).
- Redis `puzzle:<날짜>:<언어>` : 캐시다. 옮기지 않고 지운다 — DB 에서 다시 읽힌다.
- Redis `ratelimit:guess:*` : 분당 10회 고정 윈도우. 하루를 넘긴 직후의 제출이
  앞 시나리오의 카운터에 걸리지 않게 비운다.

마지막으로 시드 manifest(`e2e-artifacts/seed-manifest.json`)의 날짜도 같이 내린다 —
manifest 는 "어느 날짜에 어느 정답이 배정됐나" 의 기록이고, DB 를 옮겼으면 그 기록도
옮겨야 테스트가 지금 퍼즐의 정답을 찾을 수 있다.

**달력 날짜는 움직이지 않는다.** 서버는 벽시계로 "오늘" 을 계산하므로, 하루를 넘겨도
화면의 날짜(`#date`)는 그대로 실제 오늘이고 **배정된 단어만** 다음 것으로 바뀐다.
연속 기록 판정은 `puzzle_date` 와 `last_solved_date` 의 **차이**만 보기 때문에
(`guess_service._record_solve`) 이 방식으로도 진짜 코드 경로가 그대로 돈다.

`--days N` 으로 여러 날을 넘길 수 있다. 티켓 43·44 도 `advance(days)` 를 그대로
부른다(`scripts/e2e_stack.sh advance-day`).
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db, get_redis  # noqa: E402

# 날짜가 키 이름에 박힌 Redis 키. 접두사 뒤가 `<ISO 날짜>:<언어>` 형식이다.
DATE_KEYED_PREFIXES = ("lb:", "stats:")
# 옮기지 않고 버리는 키.
DROPPED_PREFIXES = ("puzzle:", "ratelimit:")


def _shift_sql(days: int) -> list[str]:
    # `ORDER BY` 를 붙인다: (puzzle_date, language) 유니크 키가 있어서, 날짜가
    # 겹치는 순서로 갱신되면 중간 상태에서 중복 키 오류가 난다. 오래된 날짜부터
    # 내리면 비는 자리로만 움직인다.
    return [
        f"UPDATE daily_puzzle SET puzzle_date = puzzle_date - INTERVAL {days} DAY "
        "ORDER BY puzzle_date ASC",
        f"UPDATE daily_stats SET puzzle_date = puzzle_date - INTERVAL {days} DAY "
        "ORDER BY puzzle_date ASC",
        "UPDATE guest_stats SET last_solved_date = "
        f"last_solved_date - INTERVAL {days} DAY WHERE last_solved_date IS NOT NULL",
    ]


def _shift_redis(redis, days: int) -> tuple[int, int]:
    renamed = 0
    for prefix in DATE_KEYED_PREFIXES:
        moves = []
        for raw_key in redis.scan_iter(match=f"{prefix}*"):
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            iso, _, suffix = key[len(prefix) :].partition(":")
            try:
                parsed = date.fromisoformat(iso)
            except ValueError:
                # 날짜가 아닌 키는 건드리지 않는다 — 접두사만 같은 다른 키일 수 있다.
                continue
            moves.append((parsed, key, suffix))

        # **오래된 날짜부터** 옮긴다. `RENAME` 은 대상 키가 있으면 조용히 덮어쓰므로,
        # 두 번 넘긴 뒤(어제·오늘 둘 다 기록이 있는 상태)에 새 날짜부터 옮기면
        # 어제 순위표가 사라진다. SQL 쪽에 `ORDER BY` 를 붙인 것과 같은 이유다.
        for parsed, key, suffix in sorted(moves):
            shifted = parsed - timedelta(days=days)
            redis.rename(key, f"{prefix}{shifted.isoformat()}:{suffix}")
            renamed += 1

    dropped = 0
    for prefix in DROPPED_PREFIXES:
        for key in redis.scan_iter(match=f"{prefix}*"):
            redis.delete(key)
            dropped += 1
    return renamed, dropped


def _shift_manifest(days: int) -> int:
    """시드 manifest 의 퍼즐 날짜를 같이 내린다. 파일이 없으면 아무것도 안 한다."""
    path = os.environ.get("E2E_MANIFEST")
    if not path or not Path(path).exists():
        return 0

    manifest = json.loads(Path(path).read_text())
    today = date.fromisoformat(manifest["today"])
    for puzzle in manifest["puzzles"]:
        shifted = date.fromisoformat(puzzle["date"]) - timedelta(days=days)
        puzzle["date"] = shifted.isoformat()
        # `today` 는 벽시계라 그대로다 — 그래서 오프셋이 내려간다(0 → -1).
        puzzle["offset"] = (shifted - today).days
    Path(path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return len(manifest["puzzles"])


def advance(days: int = 1) -> dict[str, int]:
    """저장된 날짜를 `days` 일 되돌린다 = 그만큼 하루가 지난 상태가 된다."""
    if days < 1:
        raise ValueError("days 는 1 이상이어야 한다")

    app = create_app("development")
    with app.app_context():
        rows = 0
        for statement in _shift_sql(days):
            rows += db.session.execute(text(statement)).rowcount
        db.session.commit()
        renamed, dropped = _shift_redis(get_redis(), days)
    pinned = _shift_manifest(days)
    return {"rows": rows, "renamed": renamed, "dropped": dropped, "manifest": pinned}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="E2E: 저장된 날짜를 되돌려 하루를 넘긴다")
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()
    result = advance(args.days)
    print(
        f"{args.days}일 전진: DB {result['rows']}행 시프트, "
        f"Redis {result['renamed']}키 rename · {result['dropped']}키 삭제, "
        f"manifest {result['manifest']}건 시프트"
    )
