from datetime import date, datetime

from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.schemas.stats import TodayStatsResponse
from app.services.game_rules import MAX_ATTEMPTS
from app.utils.redis_safe import safe_redis_call

# 리더보드 점수 = attempt_no * SECONDS_PER_DAY + 그날 자정부터 걸린 초.
# "적은 시도 우선, 같으면 빨리 푼 순"을 하나의 숫자로 인코딩한다 — 시도 횟수가
# 하루 안에 걸릴 수 있는 어떤 초 값보다도 압도적으로 커서, 시도 횟수가 항상
# 먼저 비교되고 그 안에서만 걸린 시간으로 갈린다.
SECONDS_PER_DAY = 86400


def _stats_key(puzzle_date: date) -> str:
    return f"stats:{puzzle_date.isoformat()}"


def _leaderboard_key(puzzle_date: date) -> str:
    return f"lb:{puzzle_date.isoformat()}"


def record_finish(puzzle_date: date, is_correct: bool, attempt_no: int) -> None:
    """퍼즐이 끝난 순간(정답 또는 5회 소진) 통계 카운터를 올린다.

    Redis Hash(stats:{date})에 HINCRBY로 누적한다. DB(DailyStats)에는 Celery
    Beat 배치가 반영한다(Phase 5) — 여기서는 Redis만 건드린다.
    """
    field = str(attempt_no) if is_correct else "fail"
    safe_redis_call("hincrby", _stats_key(puzzle_date), field, 1)


def record_leaderboard(
    puzzle_date: date, guest_id: int, attempt_no: int, solved_at: datetime
) -> None:
    """정답을 맞춘 게스트를 오늘의 리더보드(Sorted Set)에 올린다."""
    midnight = solved_at.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed_seconds = max(0, int((solved_at - midnight).total_seconds()))
    score = attempt_no * SECONDS_PER_DAY + elapsed_seconds
    safe_redis_call("zadd", _leaderboard_key(puzzle_date), {str(guest_id): score})


def get_today_stats(puzzle_date: date) -> TodayStatsResponse:
    counts = safe_redis_call("hgetall", _stats_key(puzzle_date)) or {}

    by_attempt_count = {str(n): int(counts.get(str(n), 0)) for n in range(1, MAX_ATTEMPTS + 1)}
    total_solved = sum(by_attempt_count.values())

    by_attempt_ratio = {
        n: (count / total_solved if total_solved else 0.0) for n, count in by_attempt_count.items()
    }

    return TodayStatsResponse(
        date=puzzle_date,
        total_solved=total_solved,
        by_attempt=by_attempt_ratio,
    )


def get_today_leaderboard(
    puzzle_date: date, limit: int, requesting_guest_id: int
) -> LeaderboardResponse:
    raw_entries = (
        safe_redis_call(
            "zrange", _leaderboard_key(puzzle_date), 0, limit - 1, withscores=True
        )
        or []
    )

    entries = []
    for rank, (member, score) in enumerate(raw_entries, start=1):
        guest_id = int(member)
        attempts, elapsed_seconds = divmod(int(score), SECONDS_PER_DAY)
        entries.append(
            LeaderboardEntry(
                rank=rank,
                guest_id=guest_id,
                attempts=attempts,
                solved_in_seconds=elapsed_seconds,
                is_me=(guest_id == requesting_guest_id),
            )
        )

    return LeaderboardResponse(date=puzzle_date, entries=entries)
