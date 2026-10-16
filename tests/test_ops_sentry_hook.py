"""Sentry 웹훅 → Slack + GitHub 이슈 (티켓 51). HTTP 경계(requests)만 가짜, Redis 는 진짜."""

import hashlib
import hmac
import json

import pytest
import requests

from app.api.ops import TASK_NAME
from app.clients import slack
from app.extensions import get_redis
from app.services import ops_alert_service as svc
from app.services import task_dispatch
from celery_app import celery

SECRET = "sentry-client-secret"


def issue_payload(action="created", issue_id="1234567890", short_id="CHOSUNG-WEB-7", count="3"):
    return {
        "action": action,
        "installation": {"uuid": "inst"},
        "data": {
            "issue": {
                "id": issue_id,
                "shortId": short_id,
                "title": "OperationalError: (1050, \"Table 'app_setting' already exists\")",
                "culprit": "alembic.operations.base in create_table",
                "level": "error",
                "status": "unresolved",
                "permalink": f"https://dosaem.sentry.io/issues/{issue_id}/",
                "project": {"id": "1", "name": "chosung-web", "slug": "chosung-web"},
                "count": count,
                "firstSeen": "2026-10-16T04:04:34Z",
            }
        },
        "actor": {"type": "application", "id": "sentry", "name": "Sentry"},
    }


def signed_post(client, payload, secret=SECRET, resource="issue"):
    body = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return client.post(
        "/api/v1/ops/sentry",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Sentry-Hook-Resource": resource,
            "Sentry-Hook-Signature": sig,
        },
    )


@pytest.fixture
def ops_app(app):
    app.config["SENTRY_WEBHOOK_SECRET"] = SECRET
    app.config["GITHUB_ISSUES_TOKEN"] = "gh-token"
    app.config["GITHUB_ISSUES_REPO"] = "dosaem/chosung-daily"
    app.config["SLACK_WEBHOOK_URL"] = "https://hooks.slack.test/x"
    return app


@pytest.fixture
def enqueued(monkeypatch):
    calls = []
    monkeypatch.setattr(
        task_dispatch, "enqueue_task", lambda name, *args: calls.append((name, args))
    )
    return calls


@pytest.fixture
def http(monkeypatch):
    """requests.request(GitHub)·requests.post(Slack) 를 가로챈다."""
    log = {"github": [], "slack": [], "issues": []}

    class R:
        def __init__(self, status, payload):
            self.status_code = status
            self._payload = payload
            self.text = json.dumps(payload)
            self.content = self.text.encode()

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)

    def fake_request(method, url, headers=None, timeout=None, **kw):
        log["github"].append((method, url, kw.get("json"), kw.get("params")))
        assert headers["Authorization"] == "Bearer gh-token"
        if method == "GET":
            return R(200, log["issues"])
        if method == "POST" and url.endswith("/issues"):
            number = 100 + len(
                [g for g in log["github"] if g[0] == "POST" and g[1].endswith("/issues")]
            )
            log["issues"].append({"number": number, "title": kw["json"]["title"]})
            return R(201, {"number": number})
        return R(200, {})

    def fake_post(url, json=None, timeout=None):
        log["slack"].append(json["text"])
        return R(200, {})

    monkeypatch.setattr(requests, "request", fake_request)
    monkeypatch.setattr(slack.requests, "post", fake_post)
    return log


# --- 입구: 서명·큐 -------------------------------------------------------------


def test_valid_signature_is_accepted_and_queued(ops_app, client, enqueued):
    res = signed_post(client, issue_payload())
    assert res.status_code == 202
    assert enqueued == [(TASK_NAME, ("issue", issue_payload()))]


def test_bad_signature_is_rejected_without_queueing(ops_app, client, enqueued):
    res = signed_post(client, issue_payload(), secret="wrong")
    assert res.status_code == 403
    assert enqueued == []


def test_hook_is_closed_when_no_secret_is_configured(app, client, enqueued):
    app.config["SENTRY_WEBHOOK_SECRET"] = ""
    res = signed_post(client, issue_payload())
    assert res.status_code == 503
    assert enqueued == []


# --- 처리: Slack + GitHub -----------------------------------------------------------


def test_new_issue_creates_a_labeled_github_issue_and_slack_message(ops_app, http):
    outcome = svc.handle_hook("issue", issue_payload())

    assert outcome.handled
    assert outcome.github_issue == 101
    created = [g for g in http["github"] if g[0] == "POST" and g[1].endswith("/issues")]
    assert len(created) == 1
    body = created[0][2]
    assert body["labels"] == ["sentry"]
    assert body["title"].startswith("[Sentry CHOSUNG-WEB-7] OperationalError")
    assert "외부 시스템이 보낸 데이터" in body["body"]
    assert "https://dosaem.sentry.io/issues/1234567890/" in body["body"]
    assert len(http["slack"]) == 1
    assert "새 에러 [error] CHOSUNG-WEB-7" in http["slack"][0]
    assert "github.com/dosaem/chosung-daily/issues/101" in http["slack"][0]
    assert get_redis().get("ops:sentry:1234567890") == "101"


def test_same_issue_again_comments_instead_of_creating(ops_app, http):
    svc.handle_hook("issue", issue_payload())
    outcome = svc.handle_hook("issue", issue_payload(action="unresolved", count="12"))

    assert outcome.github_issue == 101
    created = [g for g in http["github"] if g[0] == "POST" and g[1].endswith("/issues")]
    comments = [g for g in http["github"] if g[1].endswith("/issues/101/comments")]
    assert (len(created), len(comments)) == (1, 1)
    assert "누적 12건" in comments[0][2]["body"]
    assert "에러 다시 열림" in http["slack"][1]


def test_dedupe_survives_a_redis_wipe_by_searching_issue_titles(ops_app, http):
    svc.handle_hook("issue", issue_payload())
    get_redis().flushdb()

    outcome = svc.handle_hook("issue", issue_payload())

    assert outcome.note == "기존 GitHub 이슈에 덧글"
    assert any(
        g[0] == "GET" and g[3] == {"labels": "sentry", "state": "all", "per_page": 100}
        for g in http["github"]
    )


def test_resolved_closes_the_github_issue(ops_app, http):
    svc.handle_hook("issue", issue_payload())
    outcome = svc.handle_hook("issue", issue_payload(action="resolved"))

    patched = [g for g in http["github"] if g[0] == "PATCH"]
    assert patched[0][1].endswith("/issues/101")
    assert patched[0][2] == {"state": "closed", "state_reason": "completed"}
    assert outcome.note == "해결 처리"
    assert "에러 해결됨" in http["slack"][-1]


def test_event_alert_from_an_alert_rule_is_treated_as_a_new_issue(ops_app, http):
    payload = {
        "action": "triggered",
        "data": {
            "event": {
                "issue_id": "555",
                "title": "ProgrammingError: table hint_unlock doesn't exist",
                "culprit": "puzzles.today",
                "level": "error",
                "web_url": "https://dosaem.sentry.io/issues/555/events/abc/",
                "issue_url": "https://dosaem.sentry.io/api/0/issues/555/",
                "project": 1,
            }
        },
    }
    outcome = svc.handle_hook("event_alert", payload)
    assert outcome.handled
    assert outcome.github_issue == 101
    assert "[Sentry 555]" in http["issues"][0]["title"]


@pytest.mark.parametrize(
    ("resource", "payload"),
    [
        ("installation", {"action": "created", "data": {}}),
        ("issue", {"action": "assigned", "data": {"issue": {"id": "1", "title": "x"}}}),
        ("comment", {"action": "created", "data": {"comment": "hi"}}),
        ("issue", {"action": "created", "data": {}}),
    ],
)
def test_other_resources_and_actions_are_ignored(ops_app, http, resource, payload):
    outcome = svc.handle_hook(resource, payload)
    assert not outcome.handled
    assert http["github"] == []
    assert http["slack"] == []


def test_task_is_registered():
    assert TASK_NAME in celery.tasks
