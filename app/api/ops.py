"""운영 웹훅 — Sentry 가 에러 이슈를 보내는 입구(티켓 51).

`Sentry-Hook-Signature`(= HMAC-SHA256(client secret, 원문 본문)) 가 맞아야 받는다.
Sentry 는 1초 안에 응답을 원하므로 여기서는 검증·큐 넣기만 하고 202 로 끝낸다 —
Slack·GitHub 호출은 Celery 태스크(`tasks.handle_sentry_hook`)가 한다.
"""

import hashlib
import hmac

from flask import Blueprint, current_app, jsonify, request

from app.errors import ForbiddenError
from app.services import task_dispatch

bp = Blueprint("ops", __name__)

TASK_NAME = "tasks.handle_sentry_hook"


@bp.post("/ops/sentry")
def sentry_hook():
    secret = current_app.config["SENTRY_WEBHOOK_SECRET"]
    if not secret:
        return jsonify(
            {"code": "OPS_WEBHOOK_UNAVAILABLE", "message": "웹훅 비밀키가 없습니다."}
        ), 503

    raw = request.get_data()
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    given = request.headers.get("Sentry-Hook-Signature", "")
    if not hmac.compare_digest(expected, given):
        raise ForbiddenError("서명이 맞지 않습니다.")

    resource = request.headers.get("Sentry-Hook-Resource", "")
    payload = request.get_json(silent=True) or {}
    task_dispatch.enqueue_task(TASK_NAME, resource, payload)
    return jsonify({"accepted": True, "resource": resource}), 202
