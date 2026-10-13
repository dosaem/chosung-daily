import logging
from datetime import date, datetime, timedelta

from app.config import KST
from app.extensions import db, get_redis
from app.models import DailyStats, PuzzleLanguage
from app.repositories.puzzle_repository import find_by_date
from app.services.game_rules import MAX_ATTEMPTS
from app.services.operator_alert_service import notify_operator
from app.services.puzzle_cache import cache_puzzle
from app.services.puzzle_metrics import stats_key
from app.services.puzzle_schedule_service import schedule_puzzles

logger = logging.getLogger(__name__)


def ensure_today_puzzle_and_warm_cache(language: PuzzleLanguage) -> None:
    """한 언어의 오늘 퍼즐을 배정하고(커밋까지) 캐시를 채운다.

    `schedule_puzzles(language, days=1, ...)`가 이미 "그 날짜·언어에 퍼즐이 있으면
    건너뛴다"는 로직을 갖고 있어서(app/services/puzzle_schedule_service.py),
    여기서 따로 존재 확인을 하지 않아도 매번 돌려도 안전하다(멱등).

    캐시 워밍은 safe_redis_call 뒤에 있어서(app/services/puzzle_cache.py) Redis가
    죽어 있어도 배정 자체는 끝난다 — 플레이어는 DB 경로로 같은 퍼즐을 받는다.
    단어 풀이 비었을 때처럼 배정이 아예 안 되는 경우엔 예외를 그대로 올린다;
    언어별 실패 처리는 ensure_today_puzzles_for_all_languages가 한다.
    """
    schedule_puzzles(language, days=1, avoid_days=14)

    today = datetime.now(KST).date()
    puzzle = find_by_date(today, language)
    cache_puzzle(puzzle)


def ensure_today_puzzles_for_all_languages() -> list[PuzzleLanguage]:
    """Celery Beat 00:00 KST. 지원 언어를 하나씩 돌며 각각 배정·커밋한다.

    한 언어가 실패해도(예: en 단어 풀 고갈) 멈추지 않고 다음 언어로 간다 —
    커밋이 언어마다 따로라 앞 언어의 배정은 그대로 남는다. 실패한 언어는
    운영자에게 Slack 으로 알리고 목록으로 돌려준다(README "설계 판단" 05).

    순회를 Celery 태스크가 아니라 여기서 하는 이유: 태스크는 자기만의 Flask
    앱(celery_app.py)을 쓰기 때문에 pytest가 직접 부를 수 없다. 부분 실패
    처리처럼 검증이 필요한 로직은 서비스 함수에 두고 태스크는 호출만 한다
    (README "Celery Beat" 절의 기존 규칙).
    """
    failed: list[PuzzleLanguage] = []

    for language in PuzzleLanguage:
        try:
            ensure_today_puzzle_and_warm_cache(language)
        except Exception as exc:
            # 어떤 예외든 다음 언어를 막으면 안 된다 — 한 언어의 사고로 다른
            # 언어까지 퍼즐이 비는 게 이 태스크의 최악 시나리오다.
            db.session.rollback()
            logger.exception("%s 오늘 퍼즐 배정 실패", language.value)
            notify_operator(
                "퍼즐 배정 실패",
                f"{language.value} 오늘 퍼즐을 배정하지 못했습니다: {exc}",
            )
            failed.append(language)

    return failed


def flush_daily_stats_for_yesterday() -> None:
    """Celery Beat 00:05 KST. 전날 Redis 통계(stats:{date}:{lang})를 DailyStats로 반영.

    퍼즐이 (날짜, 언어)당 하나라 통계 키도 언어마다 갈린다 — 언어를 순회하며
    각각 읽어 각각의 행에 쓰고, 마지막에 한 번만 커밋한다(하루치 통계는 언어가
    전부 같이 반영되거나 전부 안 되거나다).

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
    for language in PuzzleLanguage:
        raw = redis_client.hgetall(stats_key(target_date, language))
        _upsert_daily_stats(target_date, language, raw)

    db.session.commit()


def _upsert_daily_stats(
    target_date: date, language: PuzzleLanguage, raw: dict[str, str]
) -> None:
    distribution = {str(n): int(raw.get(str(n), 0)) for n in range(1, MAX_ATTEMPTS + 1)}
    distribution["fail"] = int(raw.get("fail", 0))
    solver_count = sum(distribution[str(n)] for n in range(1, MAX_ATTEMPTS + 1))

    existing = db.session.get(DailyStats, (target_date, language))
    if existing is not None:
        existing.distribution = distribution
        existing.solver_count = solver_count
        return

    db.session.add(
        DailyStats(
            puzzle_date=target_date,
            language=language,
            distribution=distribution,
            solver_count=solver_count,
        )
    )
