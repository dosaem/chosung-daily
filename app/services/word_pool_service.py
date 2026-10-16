from flask import current_app

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word
from app.services import task_dispatch
from app.services.operator_alert_service import notify_operator
from app.services.word_generation_service import TASK_NAME as GENERATION_TASK

# 스펙 §A.12: 잔량이 14일치 미만이면 매일 운영자에게 알린다. 14일이면 CSV 를
# 만들어 올릴 시간이 충분하다는 판단(자정 배정이 매일 하루치씩 까먹는다).
LOW_WORD_POOL_THRESHOLD_DAYS = 14


def remaining_days_by_language() -> dict[PuzzleLanguage, int]:
    """언어별로 "아직 한 번도 배정된 적 없는 단어" 수를 센다.

    퍼즐이 (날짜, 언어)당 하나라서 미사용 단어 하나가 곧 하루치다 — 개수가 그대로
    "며칠치"다. 이미 쓴 단어도 avoid_days 가 지나면 폴백으로 다시 나올 수 있지만
    (puzzle_schedule_service._least_recently_used_word), 운영자가 알고 싶은 건
    "안 겹치는 새 단어로 며칠을 버티나"라서 재사용분은 잔량에 안 넣는다.

    단어가 하나도 없는 언어는 0으로 채워서 돌려준다 — 호출부(알림)가 "행이 없는
    언어"를 따로 신경 쓰지 않게.
    """
    used_word_ids = db.session.query(DailyPuzzle.word_id).distinct()
    counts = dict(
        db.session.query(Word.language, db.func.count(Word.id))
        .filter(~Word.id.in_(used_word_ids))
        .group_by(Word.language)
        .all()
    )
    return {language: counts.get(language, 0) for language in PuzzleLanguage}


def notify_low_word_pool() -> list[PuzzleLanguage]:
    """Celery Beat 매일 1회. 잔량이 임계 미만인 언어를 운영자에게 알린다.

    기능 플래그(`LLM_WORD_GENERATION_ENABLED`)가 켜져 있으면 그 언어의 LLM 후보
    생성 태스크도 큐에 넣는다 — 사람이 CSV 를 만드는 대신 승인만 하게(LLM 출제).
    나머지 안전장치(락·대기열 상한·월 예산)는 태스크 쪽이 본다.

    알린 언어 목록을 돌려준다 — 태스크 로그와 테스트가 "무엇을 알렸는지"를
    Slack 호출을 들여다보지 않고 확인할 수 있게.
    """
    alerted: list[PuzzleLanguage] = []

    for language, remaining_days in remaining_days_by_language().items():
        if remaining_days >= LOW_WORD_POOL_THRESHOLD_DAYS:
            continue
        notify_operator(
            "단어 잔량 부족",
            f"{language.value} {remaining_days}일치 남음 (임계 {LOW_WORD_POOL_THRESHOLD_DAYS}일)",
        )
        alerted.append(language)
        if current_app.config["LLM_WORD_GENERATION_ENABLED"]:
            task_dispatch.enqueue_task(GENERATION_TASK, language.value)

    return alerted
