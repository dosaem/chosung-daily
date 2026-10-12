from redis.exceptions import RedisError

from app.services.puzzle_maintenance_service import (
    ensure_today_puzzle_and_warm_cache,
    flush_daily_stats_for_yesterday,
)
from celery_app import celery


@celery.task(name="tasks.ensure_today_puzzle")
def ensure_today_puzzle_task():
    ensure_today_puzzle_and_warm_cache()


@celery.task(
    name="tasks.flush_daily_stats",
    autoretry_for=(RedisError,),
    retry_backoff=True,
    max_retries=5,
)
def flush_daily_stats_task():
    flush_daily_stats_for_yesterday()
