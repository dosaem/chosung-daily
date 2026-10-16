"""Celery 앱 "배선"만 확인한다 (등록된 태스크 이름, Beat 스케줄, 타임존).

실제 태스크 실행은 여기서 안 한다 — celery_app.py가 자기 자신의 create_app()으로
만든 Flask 앱을 캡처해서 쓰기 때문에, 그 태스크를 직접 호출하면 pytest의 `app`
fixture(testing 설정)가 아니라 celery_app.py의 development 설정 앱/DB를 건드리게
된다. 그래서 실제 동작 검증은 tests/test_puzzle_maintenance.py·
tests/test_word_pool_service.py에서 서비스 함수를 직접 불러서 한다 — 이 모듈을
import하는 것만으로는 DB/Redis에 아무 영향이 없다.
"""

from app.tasks import scheduled
from celery_app import celery


def test_tasks_are_registered():
    assert "tasks.ensure_today_puzzle" in celery.tasks
    assert "tasks.flush_daily_stats" in celery.tasks
    assert "tasks.notify_low_word_pool" in celery.tasks
    assert "tasks.notify_apple_secret_expiry" in celery.tasks
    assert "tasks.retry_apple_revocations" in celery.tasks
    assert "tasks.recheck_expiring_subscriptions" in celery.tasks
    assert "tasks.purge_access_logs" in celery.tasks
    assert "tasks.generate_word_candidates" in celery.tasks
    assert "tasks.review_word_candidates" in celery.tasks


def test_beat_schedule_matches_spec_times():
    schedule = celery.conf.beat_schedule

    ensure_schedule = schedule["ensure-today-puzzle"]["schedule"]
    assert ensure_schedule.hour == {0}
    assert ensure_schedule.minute == {0}
    assert schedule["ensure-today-puzzle"]["task"] == "tasks.ensure_today_puzzle"

    flush_schedule = schedule["flush-daily-stats"]["schedule"]
    assert flush_schedule.hour == {0}
    assert flush_schedule.minute == {5}
    assert schedule["flush-daily-stats"]["task"] == "tasks.flush_daily_stats"

    word_pool_schedule = schedule["notify-low-word-pool"]["schedule"]
    assert word_pool_schedule.hour == {9}
    assert word_pool_schedule.minute == {0}
    assert schedule["notify-low-word-pool"]["task"] == "tasks.notify_low_word_pool"

    # 애플 secret 만료 알림은 주 1회다(스펙 §A.13) — 매일 돌면 갱신이 멈춘 걸
    # 알리는 안전망이 아니라 잡음이 된다.
    apple_secret_schedule = schedule["notify-apple-secret-expiry"]["schedule"]
    assert apple_secret_schedule.day_of_week == {1}
    assert apple_secret_schedule.hour == {9}
    assert apple_secret_schedule.minute == {10}
    assert schedule["notify-apple-secret-expiry"]["task"] == "tasks.notify_apple_secret_expiry"

    # 애플 철회 재시도는 매일이다(스펙 §A.7) — 다른 아침 알림과 10분씩 떨어뜨렸다.
    revocation_schedule = schedule["retry-apple-revocations"]["schedule"]
    assert revocation_schedule.hour == {9}
    assert revocation_schedule.minute == {20}
    assert schedule["retry-apple-revocations"]["task"] == "tasks.retry_apple_revocations"


def test_subscription_recheck_runs_daily_away_from_the_midnight_batch():
    """구독 재조회는 매일 1회다(스펙 §A.8 (c)). 자정 배치·잔량 알림과 시각을
    떼어놨다 — 스토어 조회가 느려도 퍼즐 배정을 밀지 않게."""
    recheck_schedule = celery.conf.beat_schedule["recheck-expiring-subscriptions"]

    assert recheck_schedule["task"] == "tasks.recheck_expiring_subscriptions"
    assert recheck_schedule["schedule"].hour == {3}
    assert recheck_schedule["schedule"].minute == {30}


def test_access_log_purge_runs_daily_right_after_the_backup(app):
    """접속기록 만료 삭제는 매일 04:10 — 04:00 백업보다 **뒤**다(티켓 36).

    반대 순서면 그 날 지워진 행이 당일 덤프에만 남아, 보관 기간을 넘긴 개인정보가
    백업 보존 기간(14일)만큼 더 살아 있게 된다.
    """
    purge = celery.conf.beat_schedule["purge-access-logs"]

    assert purge["task"] == "tasks.purge_access_logs"
    assert purge["schedule"].hour == {4}
    assert purge["schedule"].minute == {10}


def test_beat_schedule_is_merged_from_task_modules():
    """태스크 모듈이 자기 몫을 들고 있고 celery_app.py가 합친다 — 태스크를 추가하는
    티켓이 celery_app.py의 한 딕셔너리를 같이 고치지 않게 한 구조다."""
    assert scheduled.BEAT_SCHEDULE.keys() <= celery.conf.beat_schedule.keys()


def test_tasks_delegate_to_the_service_functions(monkeypatch):
    """태스크 본문이 어떤 서비스 함수를 부르는지까지 확인한다.

    `.run()`은 ContextTask를 거치지 않는 원래 함수라 celery_app.py의 Flask 앱을
    열지 않는다 — 서비스 함수를 가로채 두면 DB/Redis를 전혀 안 건드린다.
    """
    called = []
    monkeypatch.setattr(
        scheduled,
        "ensure_today_puzzles_for_all_languages",
        lambda: called.append("ensure") or [],
    )
    monkeypatch.setattr(scheduled, "notify_low_word_pool", lambda: called.append("word-pool") or [])
    monkeypatch.setattr(
        scheduled,
        "notify_apple_secret_expiry",
        lambda: called.append("apple-secret") or False,
    )
    monkeypatch.setattr(
        scheduled,
        "retry_pending_revocations",
        lambda: called.append("apple-revocations") or None,
    )
    monkeypatch.setattr(
        scheduled,
        "recheck_expiring_subscriptions",
        lambda: called.append("subscription-recheck") or 0,
    )
    monkeypatch.setattr(
        scheduled, "purge_expired_access_logs", lambda: called.append("access-log-purge") or 0
    )

    scheduled.ensure_today_puzzle_task.run()
    scheduled.notify_low_word_pool_task.run()
    scheduled.notify_apple_secret_expiry_task.run()
    scheduled.retry_apple_revocations_task.run()
    scheduled.recheck_expiring_subscriptions_task.run()
    scheduled.purge_access_logs_task.run()

    assert called == [
        "ensure",
        "word-pool",
        "apple-secret",
        "apple-revocations",
        "subscription-recheck",
        "access-log-purge",
    ]


def test_timezone_is_kst():
    assert celery.conf.timezone == "Asia/Seoul"
