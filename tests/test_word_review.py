"""LLM 심사관 — 판정대로 승인(=단어 생성)·거절, 고친 힌트는 규칙 통과 시만,
판정 없는 후보는 보류."""

import json

import pytest
import requests

from app.extensions import db
from app.models import CandidateStatus, LlmCall, PuzzleLanguage, Word, WordCandidate, WordCategory
from app.services import operator_alert_service, task_dispatch
from app.services import word_generation_service as gen
from app.services import word_review_service as svc
from tests.test_word_generation import FakeResponse, messages_payload


def verdict_payload(verdicts, model="claude-sonnet-5-5", in_tok=900, out_tok=400):
    return {
        "model": model,
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": json.dumps({"verdicts": verdicts})}],
        "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
    }


def _candidate(answer, hint, language=PuzzleLanguage.KO, batch="batch-1"):
    c = WordCandidate(
        language=language,
        category=WordCategory.GENERAL,
        answer=answer,
        hint=hint,
        status=CandidateStatus.PROPOSED,
        batch_id=batch,
    )
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def llm_app(app):
    app.config["ANTHROPIC_API_KEY"] = "test-key"
    app.config["LLM_MODEL"] = "claude-sonnet-5-5"
    app.config["LLM_REVIEW_MODEL"] = ""
    app.config["LLM_REVIEW_ENABLED"] = True
    return app


@pytest.fixture
def post_calls(monkeypatch):
    calls = []
    responses = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    return {"calls": calls, "responses": responses}


@pytest.fixture
def alerts(monkeypatch):
    messages = []
    monkeypatch.setattr(
        operator_alert_service,
        "post_channel_message",
        lambda channel, text: messages.append(text) or True,
    )
    return messages


def test_review_approves_rejects_and_leaves_unjudged_for_the_operator(llm_app, post_calls, alerts):
    good = _candidate("책상", "공부할 때 앞에 두는 가구")
    fixable = _candidate("의자", "앉는 가구")
    bad = _candidate("ㅁㄴㅇ", "말이 안 됨")
    unjudged = _candidate("창문", "벽에 난 유리")
    post_calls["responses"].append(
        FakeResponse(
            200,
            verdict_payload(
                [
                    {"id": good.id, "verdict": "approve", "reason": "일상어"},
                    {
                        "id": fixable.id,
                        "verdict": "approve",
                        "reason": "힌트 보강",
                        "hint": "등받이가 있는 앉는 가구",
                    },
                    {"id": bad.id, "verdict": "reject", "reason": "사전에 없는 말"},
                    {"id": 999999, "verdict": "approve", "reason": "없는 id"},
                ]
            ),
        )
    )

    outcome = svc.run_review("batch-1")

    assert (outcome.approved, outcome.rejected, outcome.left_for_operator) == (2, 1, 1)
    sent = post_calls["calls"][0]["json"]
    assert "책상" in sent["messages"][0]["content"]
    assert sent["output_config"]["format"]["type"] == "json_schema"
    words = {w.answer: w for w in Word.query.all()}
    assert set(words) == {"책상", "의자"}
    assert words["의자"].hint == "등받이가 있는 앉는 가구"
    for c in (good, fixable, bad, unjudged):
        db.session.refresh(c)
    assert good.status is CandidateStatus.APPROVED
    assert good.reviewed_by == "llm:claude-sonnet-5-5"
    assert fixable.hint == "등받이가 있는 앉는 가구"
    assert bad.status is CandidateStatus.REJECTED
    assert bad.reject_reason == "LLM 심사 거절: 사전에 없는 말"
    assert unjudged.status is CandidateStatus.PROPOSED
    call = LlmCall.query.filter_by(purpose="word_review").one()
    assert call.batch_id == "batch-1"
    assert call.cost_usd > 0
    assert "승인 2 · 거절 1 · 보류 1" in alerts[0]


def test_fixed_hint_that_breaks_the_rules_falls_back_to_the_original(llm_app, post_calls, alerts):
    c = _candidate("책상", "공부할 때 앞에 두는 가구")
    post_calls["responses"].append(
        FakeResponse(
            200,
            verdict_payload(
                [{"id": c.id, "verdict": "approve", "reason": "ok", "hint": "책을 올려두는 상"}]
            ),  # 힌트에 정답 음절 '책'·'상'
        )
    )

    svc.run_review("batch-1")

    assert Word.query.one().hint == "공부할 때 앞에 두는 가구"


def test_approval_that_hits_a_duplicate_is_turned_into_a_rejection(llm_app, post_calls, alerts):
    db.session.add(
        Word(answer="책상", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="h")
    )
    db.session.commit()
    c = _candidate("책상", "가구")
    post_calls["responses"].append(
        FakeResponse(200, verdict_payload([{"id": c.id, "verdict": "approve", "reason": "ok"}]))
    )

    outcome = svc.run_review("batch-1")

    db.session.refresh(c)
    assert c.status is CandidateStatus.REJECTED
    assert "이미 등록된 단어" in c.reject_reason
    assert (outcome.approved, outcome.rejected) == (0, 1)


def test_review_is_idempotent_and_skips_when_nothing_is_pending(llm_app, post_calls, alerts):
    outcome = svc.run_review("no-such-batch")
    assert "없음" in outcome.skipped
    assert post_calls["calls"] == []
    assert alerts == []


def test_review_can_be_disabled(llm_app, post_calls, alerts):
    llm_app.config["LLM_REVIEW_ENABLED"] = False
    _candidate("책상", "가구")
    assert "꺼짐" in svc.run_review("batch-1").skipped
    assert post_calls["calls"] == []


def test_review_model_can_differ_from_generation_model(llm_app, post_calls, alerts):
    llm_app.config["LLM_REVIEW_MODEL"] = "claude-opus-5-5"
    c = _candidate("책상", "가구")
    post_calls["responses"].append(
        FakeResponse(
            200,
            verdict_payload(
                [{"id": c.id, "verdict": "approve", "reason": "ok"}], model="claude-opus-5-5"
            ),
        )
    )
    svc.run_review("batch-1")
    assert post_calls["calls"][0]["json"]["model"] == "claude-opus-5-5"
    db.session.refresh(c)
    assert c.reviewed_by == "llm:claude-opus-5-5"


def test_generation_enqueues_the_review_for_its_batch(llm_app, post_calls, alerts, monkeypatch):
    llm_app.config["LLM_WORD_GENERATION_ENABLED"] = True
    enqueued = []
    monkeypatch.setattr(
        task_dispatch, "enqueue_task", lambda name, *args: enqueued.append((name, args))
    )
    post_calls["responses"].append(
        FakeResponse(200, messages_payload([{"answer": "책상", "hint": "가구"}]))
    )

    outcome = gen.run_generation(PuzzleLanguage.KO)

    assert enqueued == [("tasks.review_word_candidates", (outcome.result.batch_id,))]
    assert "LLM 심사 대기열" in alerts[0]

    llm_app.config["LLM_REVIEW_ENABLED"] = False
    enqueued.clear()
    post_calls["responses"].append(
        FakeResponse(200, messages_payload([{"answer": "창문", "hint": "유리"}]))
    )
    gen.run_generation(PuzzleLanguage.KO)
    assert enqueued == []
