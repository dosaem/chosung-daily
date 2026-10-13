import json
from datetime import datetime, timedelta

import pytest
from redis.exceptions import RedisError

from app.config import KST
from app.extensions import db, get_redis
from app.models import DailyPuzzle, DailyStats, PuzzleLanguage, Word, WordCategory
from app.services.puzzle_maintenance_service import (
    ensure_today_puzzle_and_warm_cache,
    flush_daily_stats_for_yesterday,
)


def test_ensure_today_puzzle_creates_when_missing(app):
    db.session.add(Word(answer="사과", category=WordCategory.GENERAL, hint="과일"))
    db.session.commit()

    today = datetime.now(KST).date()
    assert DailyPuzzle.query.filter_by(puzzle_date=today).first() is None

    ensure_today_puzzle_and_warm_cache()

    assert DailyPuzzle.query.filter_by(puzzle_date=today).first() is not None
    cached = get_redis().get(f"puzzle:{today.isoformat()}")
    assert json.loads(cached)["answer"] == "사과"


def test_ensure_today_puzzle_is_idempotent_when_already_exists(app, today_puzzle):
    ensure_today_puzzle_and_warm_cache()
    ensure_today_puzzle_and_warm_cache()

    assert DailyPuzzle.query.count() == 1


def test_flush_daily_stats_writes_distribution_from_redis(app):
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    redis_client = get_redis()
    redis_client.hincrby(f"stats:{yesterday.isoformat()}", "1", 3)
    redis_client.hincrby(f"stats:{yesterday.isoformat()}", "2", 1)
    redis_client.hincrby(f"stats:{yesterday.isoformat()}", "fail", 2)

    flush_daily_stats_for_yesterday()

    stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    assert stats is not None
    assert stats.solver_count == 4
    assert stats.distribution == {"1": 3, "2": 1, "3": 0, "4": 0, "5": 0, "fail": 2}


def test_flush_daily_stats_upserts_existing_row(app):
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    db.session.add(
        DailyStats(
            puzzle_date=yesterday,
            language=PuzzleLanguage.KO,
            distribution={},
            solver_count=0,
        )
    )
    db.session.commit()

    get_redis().hincrby(f"stats:{yesterday.isoformat()}", "1", 5)

    flush_daily_stats_for_yesterday()

    stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    assert stats.solver_count == 5


def test_flush_daily_stats_with_no_activity_records_all_zero(app):
    flush_daily_stats_for_yesterday()

    yesterday = datetime.now(KST).date() - timedelta(days=1)
    stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    assert stats.solver_count == 0


def test_flush_daily_stats_raises_instead_of_recording_zeros_when_redis_is_down(
    app, broken_redis
):
    with pytest.raises(RedisError):
        flush_daily_stats_for_yesterday()

    yesterday = datetime.now(KST).date() - timedelta(days=1)
    assert db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO)) is None
