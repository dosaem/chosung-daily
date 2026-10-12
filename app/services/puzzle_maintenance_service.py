import logging
from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db, get_redis
from app.models import DailyStats
from app.repositories.puzzle_repository import find_by_date
from app.services.game_rules import MAX_ATTEMPTS
from app.services.puzzle_cache import cache_puzzle
from app.services.puzzle_metrics import stats_key
from app.services.puzzle_schedule_service import schedule_puzzles

logger = logging.getLogger(__name__)


def ensure_today_puzzle_and_warm_cache() -> None:
    """Celery Beat 00:00 KST. 오늘 퍼즐이 없으면 만들고, 캐시를 채운다.

    `schedule_puzzles(days=1, ...)`가 이미 "그 날짜에 퍼즐이 있으면 건너뛴다"는
    로직을 갖고 있어서(app/services/puzzle_schedule_service.py), 여기서 따로
    존재 확인을 하지 않아도 매번 돌려도 안전하다(멱등).
    """
    schedule_puzzles(days=1, avoid_days=14)

    today = datetime.now(KST).date()
    puzzle = find_by_date(today)
    cache_puzzle(puzzle)


def flush_daily_stats_for_yesterday() -> None:
    """Celery Beat 00:05 KST. 전날 Redis 통계(stats:{date})를 DailyStats로 반영.

    실시간 API(puzzle_metrics.get_today_stats)와 다르게 safe_redis_call을 안
    쓴다 — 거기선 Redis 장애 시 "일단 0으로 보여주고 다음 요청에서 다시 시도"가
    괜찮지만, 여긴 그 0을 DB에 영구 기록해버리면 그날 통계가 "0명이 풀었다"로
    거짓 기록되고 복구할 방법이 없다. 그래서 Redis가 없거나 장애면 예외를 그대로
    올려서 Celery가 재시도하게 한다(app/tasks/scheduled.py의 autoretry_for).
    """
    redis_client = get_redis()
    if redis_client is None:
        raise RuntimeError("Redis가 설정되지 않아 통계를 반영할 수 없습니다.")

    target_date = datetime.now(KST).date() - timedelta(days=1)
    raw = redis_client.hgetall(stats_key(target_date))

    distribution = {str(n): int(raw.get(str(n), 0)) for n in range(1, MAX_ATTEMPTS + 1)}
    distribution["fail"] = int(raw.get("fail", 0))
    solver_count = sum(distribution[str(n)] for n in range(1, MAX_ATTEMPTS + 1))

    existing = db.session.get(DailyStats, target_date)
    if existing is not None:
        existing.distribution = distribution
        existing.solver_count = solver_count
    else:
        db.session.add(
            DailyStats(
                puzzle_date=target_date,
                distribution=distribution,
                solver_count=solver_count,
            )
        )
    db.session.commit()
