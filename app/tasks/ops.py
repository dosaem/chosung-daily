"""Sentry 웹훅 처리 태스크 — Slack·GitHub 의 일시 오류만 재시도한다(티켓 51)."""

from app.api.ops import TASK_NAME
from app.clients.github import GitHubError
from app.services import ops_alert_service
from app.services.operator_alert_service import notify_operator
from celery_app import celery

MAX_RETRIES = 3


@celery.task(
    name=TASK_NAME,
    bind=True,
    autoretry_for=(GitHubError,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def handle_sentry_hook_task(self, resource: str, payload: dict):
    try:
        outcome = ops_alert_service.handle_hook(resource, payload)
    except GitHubError as err:
        if not err.retryable or self.request.retries >= MAX_RETRIES:
            # GitHub 쪽이 끝내 안 되면 최소한 Slack 에는 남긴다 — 사람이 직접 이슈를 연다.
            notify_operator(
                "Sentry 에러 (GitHub 이슈 생성 실패)",
                f"{resource}: {err} · Sentry 에서 직접 확인하세요",
            )
            if not err.retryable:
                return {"handled": False, "error": str(err)}
        raise
    return {
        "handled": outcome.handled,
        "slack_sent": outcome.slack_sent,
        "github_issue": outcome.github_issue,
        "note": outcome.note,
    }
