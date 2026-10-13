from celery.schedules import crontab
from redis.exceptions import RedisError

from app.services.puzzle_maintenance_service import (
    ensure_today_puzzles_for_all_languages,
    flush_daily_stats_for_yesterday,
)
from app.services.word_pool_service import notify_low_word_pool
from celery_app import celery


@celery.task(name="tasks.ensure_today_puzzle")
def ensure_today_puzzle_task():
    ensure_today_puzzles_for_all_languages()


@celery.task(
    name="tasks.flush_daily_stats",
    autoretry_for=(RedisError,),
    retry_backoff=True,
    max_retries=5,
)
def flush_daily_stats_task():
    flush_daily_stats_for_yesterday()


@celery.task(name="tasks.notify_low_word_pool")
def notify_low_word_pool_task():
    notify_low_word_pool()


# 시각은 전부 KST다(celery.conf.timezone = "Asia/Seoul").
# 잔량 알림을 09:00에 둔 이유: 자정 배정 직후가 아니라 운영자가 깨어 있는
# 시간에 와야 그날 안에 CSV를 채울 수 있다.
BEAT_SCHEDULE = {
    "ensure-today-puzzle": {
        "task": "tasks.ensure_today_puzzle",
        "schedule": crontab(hour=0, minute=0),
    },
    "flush-daily-stats": {
        "task": "tasks.flush_daily_stats",
        "schedule": crontab(hour=0, minute=5),
    },
    "notify-low-word-pool": {
        "task": "tasks.notify_low_word_pool",
        "schedule": crontab(hour=9, minute=0),
    },
}

# 이 모듈이 자기 몫의 Beat 스케줄을 직접 등록한다. celery_app.py 의 딕셔너리 하나에
# 모든 태스크가 모이면 태스크를 추가하는 작업마다 그 파일을 같이 고쳐야 한다 —
# 태스크 모듈을 새로 만드는 쪽은 여기처럼 자기 BEAT_SCHEDULE 을 합치고,
# celery_app.py 는 그 모듈을 import 만 한다.
celery.conf.beat_schedule = {**celery.conf.beat_schedule, **BEAT_SCHEDULE}
