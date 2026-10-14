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
    assert (
        schedule["notify-apple-secret-expiry"]["task"] == "tasks.notify_apple_secret_expiry"
    )

    # 애플 철회 재시도는 매일이다(스펙 §A.7) — 다른 아침 알림과 10분씩 떨어뜨렸다.
    revocation_schedule = schedule["retry-apple-revocations"]["schedule"]
    assert revocation_schedule.hour == {9}
    assert revocation_schedule.minute == {20}
    assert schedule["retry-apple-revocations"]["task"] == "tasks.retry_apple_revocations"


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
    monkeypatch.setattr(
        scheduled, "notify_low_word_pool", lambda: called.append("word-pool") or []
    )
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

    scheduled.ensure_today_puzzle_task.run()
    scheduled.notify_low_word_pool_task.run()
    scheduled.notify_apple_secret_expiry_task.run()
    scheduled.retry_apple_revocations_task.run()

    assert called == ["ensure", "word-pool", "apple-secret", "apple-revocations"]


def test_timezone_is_kst():
    assert celery.conf.timezone == "Asia/Seoul"
