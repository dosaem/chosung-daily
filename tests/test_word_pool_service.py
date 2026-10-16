"""언어별 단어 풀 잔량과 운영자 알림. Slack 래퍼만 가로채고 나머지는 실제 DB다."""

import pytest

from app.extensions import db
from app.models import PuzzleLanguage, Word, WordCategory
from app.services import operator_alert_service, task_dispatch
from app.services.puzzle_schedule_service import schedule_puzzles
from app.services.word_pool_service import (
    LOW_WORD_POOL_THRESHOLD_DAYS,
    notify_low_word_pool,
    remaining_days_by_language,
)


@pytest.fixture
def operator_alerts(monkeypatch):
    messages = []
    monkeypatch.setattr(
        operator_alert_service,
        "post_webhook_message",
        lambda text: messages.append(text) or True,
    )
    return messages


def _add_words(n, language=PuzzleLanguage.KO):
    db.session.add_all(
        Word(
            answer=f"{language.value}단어{i}",
            language=language,
            category=WordCategory.GENERAL,
            hint="테스트용",
        )
        for i in range(n)
    )
    db.session.commit()


def test_remaining_days_counts_unused_words_per_language(app):
    _add_words(3, PuzzleLanguage.KO)
    _add_words(5, PuzzleLanguage.EN)

    remaining = remaining_days_by_language()

    # 퍼즐이 날짜·언어당 하나라 미사용 단어 하나가 곧 하루치다.
    assert remaining == {PuzzleLanguage.KO: 3, PuzzleLanguage.EN: 5}


def test_remaining_days_drops_as_words_get_scheduled(app):
    _add_words(5, PuzzleLanguage.KO)

    schedule_puzzles(PuzzleLanguage.KO, days=2, avoid_days=14)

    assert remaining_days_by_language()[PuzzleLanguage.KO] == 3


def test_remaining_days_is_zero_for_a_language_with_no_words(app):
    _add_words(2, PuzzleLanguage.KO)

    assert remaining_days_by_language()[PuzzleLanguage.EN] == 0


def test_notifies_only_the_languages_below_the_threshold(app, operator_alerts):
    _add_words(LOW_WORD_POOL_THRESHOLD_DAYS, PuzzleLanguage.KO)  # 딱 임계치 = 알림 없음
    _add_words(LOW_WORD_POOL_THRESHOLD_DAYS - 2, PuzzleLanguage.EN)

    alerted = notify_low_word_pool()

    assert alerted == [PuzzleLanguage.EN]
    assert len(operator_alerts) == 1
    assert "단어 잔량 부족" in operator_alerts[0]
    assert "en" in operator_alerts[0]
    assert f"{LOW_WORD_POOL_THRESHOLD_DAYS - 2}일치" in operator_alerts[0]


def test_stays_quiet_when_every_language_has_enough_words(app, operator_alerts):
    _add_words(LOW_WORD_POOL_THRESHOLD_DAYS + 1, PuzzleLanguage.KO)
    _add_words(LOW_WORD_POOL_THRESHOLD_DAYS + 1, PuzzleLanguage.EN)

    assert notify_low_word_pool() == []
    assert operator_alerts == []


def test_low_pool_enqueues_llm_generation_only_when_the_flag_is_on(
    app, operator_alerts, monkeypatch
):
    enqueued = []
    monkeypatch.setattr(
        task_dispatch, "enqueue_task", lambda name, *args: enqueued.append((name, args))
    )
    _add_words(2, PuzzleLanguage.KO)
    _add_words(LOW_WORD_POOL_THRESHOLD_DAYS, PuzzleLanguage.EN)

    app.config["LLM_WORD_GENERATION_ENABLED"] = False
    notify_low_word_pool()
    assert enqueued == []

    app.config["LLM_WORD_GENERATION_ENABLED"] = True
    notify_low_word_pool()
    assert enqueued == [("tasks.generate_word_candidates", ("ko",))]
