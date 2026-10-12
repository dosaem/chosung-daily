"""Celery 앱 "배선"만 확인한다 (등록된 태스크 이름, Beat 스케줄, 타임존).

실제 태스크 실행은 여기서 안 한다 — celery_app.py가 자기 자신의 create_app()으로
만든 Flask 앱을 캡처해서 쓰기 때문에, 그 태스크를 직접 호출하면 pytest의 `app`
fixture(testing 설정)가 아니라 celery_app.py의 development 설정 앱/DB를 건드리게
된다. 그래서 실제 동작 검증은 tests/test_puzzle_maintenance.py에서 서비스 함수
(ensure_today_puzzle_and_warm_cache, flush_daily_stats_for_yesterday)를 직접
불러서 한다 — 이 모듈을 import하는 것만으로는 DB/Redis에 아무 영향이 없다.
"""

from celery_app import celery


def test_tasks_are_registered():
    assert "tasks.ensure_today_puzzle" in celery.tasks
    assert "tasks.flush_daily_stats" in celery.tasks


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


def test_timezone_is_kst():
    assert celery.conf.timezone == "Asia/Seoul"
