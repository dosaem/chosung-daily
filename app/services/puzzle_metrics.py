from datetime import date, datetime

from app.models import PuzzleLanguage
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse, MyRank
from app.schemas.stats import TodayStatsResponse
from app.services.game_rules import MAX_ATTEMPTS
from app.utils.redis_safe import safe_redis_call

# 리더보드 점수 = attempt_no * SECONDS_PER_DAY + 그날 자정부터 걸린 초.
# "적은 시도 우선, 같으면 빨리 푼 순"을 하나의 숫자로 인코딩한다 — 시도 횟수가
# 하루 안에 걸릴 수 있는 어떤 초 값보다도 압도적으로 커서, 시도 횟수가 항상
# 먼저 비교되고 그 안에서만 걸린 시간으로 갈린다.
SECONDS_PER_DAY = 86400

# 리더보드 표시 이름의 자리수. guest.id 를 이 값으로 나눈 나머지를 16진 4자리로
# 쓴다 — 게스트가 65536명을 넘으면 표시가 겹치지만, 이 문자열은 식별용이 아니라
# "남"과 "나"를 구분해 보여주기 위한 라벨이라 충돌을 허용한다(스펙 US 13).
DISPLAY_ID_MODULUS = 0x10000


def display_name(guest_id: int) -> str:
    """리더보드에 보여줄 익명 이름. 이메일·게스트 ID 원본은 응답에 넣지 않는다."""
    return f"게스트 #{guest_id % DISPLAY_ID_MODULUS:04x}"


def _split_score(score: float) -> tuple[int, int]:
    """리더보드 점수를 (시도 횟수, 걸린 초)로 되돌린다."""
    attempts, elapsed_seconds = divmod(int(score), SECONDS_PER_DAY)
    return attempts, elapsed_seconds


def stats_key(puzzle_date: date, language: PuzzleLanguage) -> str:
    """app/services/puzzle_maintenance_service.py의 Celery Beat 배치도 같은 키 포맷을 쓴다.

    같은 날 ko/en 퍼즐이 따로 있으니 집계도 언어별로 갈린다 — 키에 언어가 들어간다.
    """
    return f"stats:{puzzle_date.isoformat()}:{language.value}"


def _leaderboard_key(puzzle_date: date, language: PuzzleLanguage) -> str:
    return f"lb:{puzzle_date.isoformat()}:{language.value}"


def record_finish(
    puzzle_date: date, language: PuzzleLanguage, is_correct: bool, attempt_no: int
) -> None:
    """퍼즐이 끝난 순간(정답 또는 5회 소진) 통계 카운터를 올린다.

    Redis Hash(stats:{date}:{lang})에 HINCRBY로 누적한다. DB(DailyStats)에는 Celery
    Beat 배치가 반영한다(Phase 5) — 여기서는 Redis만 건드린다.
    """
    field = str(attempt_no) if is_correct else "fail"
    safe_redis_call("hincrby", stats_key(puzzle_date, language), field, 1)


def record_leaderboard(
    puzzle_date: date,
    language: PuzzleLanguage,
    guest_id: int,
    attempt_no: int,
    solved_at: datetime,
) -> None:
    """정답을 맞춘 게스트를 오늘의 리더보드(Sorted Set)에 올린다."""
    midnight = solved_at.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed_seconds = max(0, int((solved_at - midnight).total_seconds()))
    score = attempt_no * SECONDS_PER_DAY + elapsed_seconds
    safe_redis_call(
        "zadd", _leaderboard_key(puzzle_date, language), {str(guest_id): score}
    )


def remove_from_leaderboard(puzzle_date: date, language: PuzzleLanguage, guest_id: int) -> None:
    """리더보드에서 한 게스트를 뺀다. 계정 삭제가 쓴다(스펙 §A.7).

    없는 멤버를 지워도 Redis 는 0 을 돌려주고 끝이라, 그 게스트가 오늘 풀었는지
    먼저 묻지 않는다 — 왕복 한 번으로 끝낸다.
    """
    safe_redis_call("zrem", _leaderboard_key(puzzle_date, language), str(guest_id))


def get_today_stats(puzzle_date: date, language: PuzzleLanguage) -> TodayStatsResponse:
    counts = safe_redis_call("hgetall", stats_key(puzzle_date, language)) or {}

    by_attempt_count = {str(n): int(counts.get(str(n), 0)) for n in range(1, MAX_ATTEMPTS + 1)}
    total_solved = sum(by_attempt_count.values())

    by_attempt_ratio = {
        n: (count / total_solved if total_solved else 0.0) for n, count in by_attempt_count.items()
    }

    return TodayStatsResponse(
        date=puzzle_date,
        language=language,
        total_solved=total_solved,
        by_attempt=by_attempt_ratio,
    )


def get_today_leaderboard(
    puzzle_date: date, language: PuzzleLanguage, limit: int, requesting_guest_id: int
) -> LeaderboardResponse:
    key = _leaderboard_key(puzzle_date, language)
    raw_entries = safe_redis_call("zrange", key, 0, limit - 1, withscores=True) or []

    entries = []
    for rank, (member, score) in enumerate(raw_entries, start=1):
        guest_id = int(member)
        attempts, elapsed_seconds = _split_score(score)
        entries.append(
            LeaderboardEntry(
                rank=rank,
                display=display_name(guest_id),
                attempts=attempts,
                seconds=elapsed_seconds,
                is_me=(guest_id == requesting_guest_id),
            )
        )

    return LeaderboardResponse(
        date=puzzle_date,
        language=language,
        entries=entries,
        me=_my_rank(key, requesting_guest_id),
    )


def _my_rank(key: str, guest_id: int) -> MyRank | None:
    """내 순위를 ZRANK 로 따로 읽는다 — limit 밖(예: 23위)이어도 내려줘야 한다.

    아직 못 풀었으면 Sorted Set 에 멤버가 없어서 ZRANK 가 None 이고, 그때는 me 도
    null 이다. Redis 장애 때도 safe_redis_call 이 None 을 주니 같은 길로 떨어진다.
    """
    rank = safe_redis_call("zrank", key, str(guest_id))
    if rank is None:
        return None

    score = safe_redis_call("zscore", key, str(guest_id))
    if score is None:
        return None

    attempts, elapsed_seconds = _split_score(score)
    return MyRank(rank=rank + 1, attempts=attempts, seconds=elapsed_seconds)
