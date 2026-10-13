import json
from datetime import datetime, timedelta

import pytest
from redis.exceptions import RedisError

from app.config import KST
from app.extensions import db, get_redis
from app.models import DailyPuzzle, DailyStats, PuzzleLanguage, Word, WordCategory
from app.services import operator_alert_service
from app.services.puzzle_maintenance_service import (
    ensure_today_puzzle_and_warm_cache,
    ensure_today_puzzles_for_all_languages,
    flush_daily_stats_for_yesterday,
)


@pytest.fixture
def operator_alerts(monkeypatch):
    """Slack 래퍼를 가로채서 운영자에게 나간 메시지를 모은다(네트워크 없음)."""
    messages = []
    monkeypatch.setattr(
        operator_alert_service,
        "post_webhook_message",
        lambda text: messages.append(text) or True,
    )
    return messages


def _add_word(answer, language=PuzzleLanguage.KO):
    db.session.add(
        Word(answer=answer, language=language, category=WordCategory.GENERAL, hint="테스트용")
    )
    db.session.commit()


def test_ensure_today_puzzle_creates_when_missing(app):
    _add_word("사과")

    today = datetime.now(KST).date()
    assert DailyPuzzle.query.filter_by(puzzle_date=today).first() is None

    ensure_today_puzzle_and_warm_cache(PuzzleLanguage.KO)

    assert DailyPuzzle.query.filter_by(puzzle_date=today).first() is not None
    cached = get_redis().get(f"puzzle:{today.isoformat()}:ko")
    assert json.loads(cached)["answer"] == "사과"


def test_ensure_today_puzzle_is_idempotent_when_already_exists(app, today_puzzle):
    ensure_today_puzzle_and_warm_cache(PuzzleLanguage.KO)
    ensure_today_puzzle_and_warm_cache(PuzzleLanguage.KO)

    assert DailyPuzzle.query.count() == 1


def test_ensure_today_puzzle_warms_the_cache_of_its_own_language(app):
    _add_word("apple", PuzzleLanguage.EN)

    ensure_today_puzzle_and_warm_cache(PuzzleLanguage.EN)

    today = datetime.now(KST).date()
    assert json.loads(get_redis().get(f"puzzle:{today.isoformat()}:en"))["answer"] == "apple"
    # ko 키는 ko 배정이 돌 때만 생긴다.
    assert get_redis().get(f"puzzle:{today.isoformat()}:ko") is None


def test_ensure_today_puzzle_still_commits_when_redis_is_down(app, broken_redis):
    """캐시 워밍은 safe_redis_call 뒤에 있어서 배정 자체를 막지 않는다(DB 폴백)."""
    _add_word("사과")

    ensure_today_puzzle_and_warm_cache(PuzzleLanguage.KO)

    today = datetime.now(KST).date()
    assert DailyPuzzle.query.filter_by(
        puzzle_date=today, language=PuzzleLanguage.KO
    ).first() is not None


def test_all_languages_get_their_own_puzzle_and_cache(app, operator_alerts):
    _add_word("사과", PuzzleLanguage.KO)
    _add_word("apple", PuzzleLanguage.EN)

    failed = ensure_today_puzzles_for_all_languages()

    assert failed == []
    today = datetime.now(KST).date()
    languages = {p.language for p in DailyPuzzle.query.filter_by(puzzle_date=today).all()}
    assert languages == {PuzzleLanguage.KO, PuzzleLanguage.EN}
    assert get_redis().get(f"puzzle:{today.isoformat()}:ko") is not None
    assert get_redis().get(f"puzzle:{today.isoformat()}:en") is not None
    assert operator_alerts == []


def test_one_language_failing_does_not_block_the_others(app, operator_alerts):
    """en 단어가 0개여도 ko 는 배정되고, 운영자는 en 실패 한 건만 받는다."""
    _add_word("사과", PuzzleLanguage.KO)

    failed = ensure_today_puzzles_for_all_languages()

    assert failed == [PuzzleLanguage.EN]
    today = datetime.now(KST).date()
    assert DailyPuzzle.query.filter_by(
        puzzle_date=today, language=PuzzleLanguage.KO
    ).first() is not None
    assert DailyPuzzle.query.filter_by(
        puzzle_date=today, language=PuzzleLanguage.EN
    ).first() is None

    assert len(operator_alerts) == 1
    assert "퍼즐 배정 실패" in operator_alerts[0]
    assert "en" in operator_alerts[0]


def test_flush_daily_stats_writes_distribution_from_redis(app):
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    redis_client = get_redis()
    redis_client.hincrby(f"stats:{yesterday.isoformat()}:ko", "1", 3)
    redis_client.hincrby(f"stats:{yesterday.isoformat()}:ko", "2", 1)
    redis_client.hincrby(f"stats:{yesterday.isoformat()}:ko", "fail", 2)

    flush_daily_stats_for_yesterday()

    stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    assert stats is not None
    assert stats.solver_count == 4
    assert stats.distribution == {"1": 3, "2": 1, "3": 0, "4": 0, "5": 0, "fail": 2}


def test_flush_daily_stats_reads_one_key_per_language(app):
    yesterday = datetime.now(KST).date() - timedelta(days=1)
    redis_client = get_redis()
    redis_client.hincrby(f"stats:{yesterday.isoformat()}:ko", "1", 3)
    redis_client.hincrby(f"stats:{yesterday.isoformat()}:en", "2", 5)

    flush_daily_stats_for_yesterday()

    ko_stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    en_stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.EN))
    assert ko_stats.solver_count == 3
    assert en_stats.solver_count == 5
    assert en_stats.distribution["2"] == 5


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

    get_redis().hincrby(f"stats:{yesterday.isoformat()}:ko", "1", 5)

    flush_daily_stats_for_yesterday()

    stats = db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO))
    assert stats.solver_count == 5


def test_flush_daily_stats_with_no_activity_records_all_zero(app):
    flush_daily_stats_for_yesterday()

    yesterday = datetime.now(KST).date() - timedelta(days=1)
    for language in PuzzleLanguage:
        stats = db.session.get(DailyStats, (yesterday, language))
        assert stats.solver_count == 0


def test_flush_daily_stats_raises_instead_of_recording_zeros_when_redis_is_down(
    app, broken_redis
):
    with pytest.raises(RedisError):
        flush_daily_stats_for_yesterday()

    yesterday = datetime.now(KST).date() - timedelta(days=1)
    assert db.session.get(DailyStats, (yesterday, PuzzleLanguage.KO)) is None
