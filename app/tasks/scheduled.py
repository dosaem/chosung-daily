from celery.schedules import crontab
from redis.exceptions import RedisError

from app.services.apple_revocation_service import retry_pending_revocations
from app.services.apple_secret_service import notify_apple_secret_expiry
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


@celery.task(name="tasks.notify_apple_secret_expiry")
def notify_apple_secret_expiry_task():
    notify_apple_secret_expiry()


@celery.task(name="tasks.retry_apple_revocations")
def retry_apple_revocations_task():
    retry_pending_revocations()


# 시각은 전부 KST다(celery.conf.timezone = "Asia/Seoul").
# 잔량 알림을 09:00에 둔 이유: 자정 배정 직후가 아니라 운영자가 깨어 있는
# 시간에 와야 그날 안에 CSV를 채울 수 있다.
# 애플 secret 만료 알림은 주 1회(월 09:10)다 — 갱신 자체는 요청 경로가 하고
# (스펙 §A.13) 이건 "갱신이 안 돌고 있다"를 잡는 안전망이라 매일 볼 일이 아니다.
# 잔량 알림과 10분 떼어놔서 두 Slack 메시지가 한 번에 겹치지 않게 했다.
# 애플 철회 재시도는 매일 09:20 이다(스펙 §A.7 "Beat 가 매일 재시도"). 폐기 알림이
# 울릴 수 있어서 다른 두 알림과 같은 아침 시간대에 두고 10분씩 떼어놨다 — 운영자가
# 깨어 있고, 세 Slack 메시지가 한꺼번에 오지 않는다.
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
    "notify-apple-secret-expiry": {
        "task": "tasks.notify_apple_secret_expiry",
        "schedule": crontab(day_of_week="mon", hour=9, minute=10),
    },
    "retry-apple-revocations": {
        "task": "tasks.retry_apple_revocations",
        "schedule": crontab(hour=9, minute=20),
    },
}

# 이 모듈이 자기 몫의 Beat 스케줄을 직접 등록한다. celery_app.py 의 딕셔너리 하나에
# 모든 태스크가 모이면 태스크를 추가하는 작업마다 그 파일을 같이 고쳐야 한다 —
# 태스크 모듈을 새로 만드는 쪽은 여기처럼 자기 BEAT_SCHEDULE 을 합치고,
# celery_app.py 는 그 모듈을 import 만 한다.
celery.conf.beat_schedule = {**celery.conf.beat_schedule, **BEAT_SCHEDULE}
