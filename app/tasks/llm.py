"""LLM 단어 후보 생성 태스크(LLM 출제 파이프라인).

트리거 두 곳 — 잔량 알림(`notify_low_word_pool`)과 어드민 "후보 생성" 버튼 — 이 같은
태스크를 큐에 넣는다. 안전장치(플래그·락·대기열 상한·월 예산)는 서비스
`run_generation` 이 들고 있고, 이 모듈은 **재시도 정책**만 안다:

- 429·5xx·타임아웃(`AnthropicTransientError`): 백오프 재시도 최대 3회.
- 설정 오류(4xx, `AnthropicConfigError`): 다시 보내도 같은 답이라 재시도 없이 바로
  Slack 으로 알린다.
"""

from app.clients.anthropic import AnthropicConfigError, AnthropicTransientError
from app.models import PuzzleLanguage
from app.services.operator_alert_service import notify_operator
from app.services.word_generation_service import TASK_NAME, run_generation
from celery_app import celery

MAX_RETRIES = 3


@celery.task(
    name=TASK_NAME,
    bind=True,
    autoretry_for=(AnthropicTransientError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def generate_word_candidates_task(self, language: str, trigger: str = "schedule"):
    try:
        outcome = run_generation(PuzzleLanguage(language), trigger)
    except AnthropicTransientError as err:
        if self.request.retries >= MAX_RETRIES:
            notify_operator(
                "LLM 단어 후보 생성 실패",
                f"{language} — {MAX_RETRIES}회 재시도 후 포기: {err}",
            )
        raise
    except AnthropicConfigError as err:
        notify_operator("LLM 단어 후보 생성 실패 (설정)", f"{language} — 재시도 안 함: {err}")
        return {"language": language, "skipped": f"config error: {err}"}
    return {
        "language": language,
        "skipped": outcome.skipped,
        "proposed": outcome.result.proposed if outcome.result else 0,
        "rejected": outcome.result.rejected if outcome.result else 0,
    }
