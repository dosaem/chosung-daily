"""LLM 후보 검수 화면 — 목록, 힌트 고쳐 승인, 거절, 중복 승인 실패, 후보 생성 버튼."""

import re

import pytest

from app.extensions import db
from app.models import CandidateStatus, PuzzleLanguage, Word, WordCandidate, WordCategory
from app.services import task_dispatch
from tests.conftest import ADMIN_EMAIL

CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


def _token(client):
    return CSRF_PATTERN.search(client.get("/admin/candidates").get_data(as_text=True)).group(1)


def _candidate(answer, language=PuzzleLanguage.KO, hint="힌트", batch="batch-1"):
    candidate = WordCandidate(
        language=language,
        category=WordCategory.GENERAL,
        answer=answer,
        hint=hint,
        status=CandidateStatus.PROPOSED,
        batch_id=batch,
    )
    db.session.add(candidate)
    db.session.commit()
    return candidate


@pytest.fixture
def enqueued(monkeypatch):
    calls = []
    monkeypatch.setattr(
        task_dispatch, "enqueue_task", lambda name, *args: calls.append((name, args))
    )
    return calls


def test_requires_admin(client, web_login, app):
    assert client.get("/admin/candidates").status_code == 302  # 로그인 안내
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    web_login("someone-else@example.com")
    assert client.get("/admin/candidates").status_code == 403


def test_lists_pending_candidates_with_language_filter(admin_session):
    _candidate("책상")
    _candidate("apple", language=PuzzleLanguage.EN)
    rejected = _candidate("의자")
    rejected.status = CandidateStatus.REJECTED
    db.session.commit()

    html = admin_session.get("/admin/candidates").get_data(as_text=True)
    pending_part, recent_part = html.split("최근 처리", 1)
    assert "책상" in pending_part
    assert "apple" in pending_part
    assert "의자" not in pending_part  # 거절된 후보는 대기 목록이 아니라 최근 처리에만
    assert "의자" in recent_part
    assert "1개 대기" in html

    html = admin_session.get("/admin/candidates?language=en").get_data(as_text=True)
    assert "apple" in html
    assert "책상" not in html


def test_approve_creates_words_with_the_edited_hint(admin_session):
    first = _candidate("책상", hint="LLM 힌트")
    second = _candidate("의자")
    untouched = _candidate("창문")

    res = admin_session.post(
        "/admin/candidates/review",
        data={
            "csrf_token": _token(admin_session),
            "action": "approve",
            "candidate_id": [str(first.id), str(second.id)],
            f"hint-{first.id}": "운영자가 고친 힌트",
            f"hint-{second.id}": "",
        },
    )
    assert res.status_code == 302

    words = {w.answer: w for w in Word.query.all()}
    assert set(words) == {"책상", "의자"}
    assert words["책상"].hint == "운영자가 고친 힌트"
    assert words["의자"].hint == "힌트"
    db.session.refresh(first)
    assert first.status is CandidateStatus.APPROVED
    assert first.word_id == words["책상"].id
    assert first.reviewed_by == ADMIN_EMAIL
    assert first.hint == "운영자가 고친 힌트"
    assert first.reviewed_at is not None
    db.session.refresh(untouched)
    assert untouched.status is CandidateStatus.PROPOSED

    html = admin_session.get("/admin/candidates").get_data(as_text=True)
    assert "후보 2개를 단어로 추가했어요" in html


def test_approving_a_duplicate_rejects_it_and_keeps_the_rest(admin_session):
    db.session.add(
        Word(answer="책상", language=PuzzleLanguage.KO, category=WordCategory.GENERAL, hint="h")
    )
    db.session.commit()
    dup = _candidate("책상")
    ok = _candidate("의자")

    admin_session.post(
        "/admin/candidates/review",
        data={
            "csrf_token": _token(admin_session),
            "action": "approve",
            "candidate_id": [str(dup.id), str(ok.id)],
        },
    )

    assert Word.query.count() == 2
    db.session.refresh(dup)
    db.session.refresh(ok)
    assert dup.status is CandidateStatus.REJECTED
    assert "이미 등록된 단어" in dup.reject_reason
    assert ok.status is CandidateStatus.APPROVED
    html = admin_session.get("/admin/candidates").get_data(as_text=True)
    assert "추가하지 못해 거절로 돌렸어요" in html


def test_reject_records_reason_and_reviewer(admin_session):
    candidate = _candidate("책상")

    admin_session.post(
        "/admin/candidates/review",
        data={
            "csrf_token": _token(admin_session),
            "action": "reject",
            "candidate_id": [str(candidate.id)],
            "reason": "너무 쉬움",
        },
    )

    db.session.refresh(candidate)
    assert candidate.status is CandidateStatus.REJECTED
    assert candidate.reject_reason == "너무 쉬움"
    assert candidate.reviewed_by == ADMIN_EMAIL
    assert Word.query.count() == 0


def test_review_without_selection_only_flashes(admin_session):
    _candidate("책상")
    admin_session.post(
        "/admin/candidates/review",
        data={"csrf_token": _token(admin_session), "action": "approve"},
    )
    assert WordCandidate.query.filter_by(status=CandidateStatus.PROPOSED).count() == 1


def test_generate_button_enqueues_the_task_only_when_enabled(admin_session, app, enqueued):
    app.config["LLM_WORD_GENERATION_ENABLED"] = False
    admin_session.post(
        "/admin/candidates/generate",
        data={"csrf_token": _token(admin_session), "language": "en"},
    )
    assert enqueued == []

    app.config["LLM_WORD_GENERATION_ENABLED"] = True
    res = admin_session.post(
        "/admin/candidates/generate",
        data={"csrf_token": _token(admin_session), "language": "en"},
    )
    assert res.status_code == 302
    assert enqueued == [("tasks.generate_word_candidates", ("en", "admin"))]


def test_review_requires_csrf(admin_session):
    candidate = _candidate("책상")
    res = admin_session.post(
        "/admin/candidates/review",
        data={"action": "approve", "candidate_id": [str(candidate.id)]},
    )
    assert res.status_code in (400, 403)
    db.session.refresh(candidate)
    assert candidate.status is CandidateStatus.PROPOSED


def test_review_llm_button_enqueues_each_pending_batch(admin_session, app, enqueued):
    _candidate("책상", batch="b1")
    _candidate("의자", batch="b1")
    _candidate("apple", language=PuzzleLanguage.EN, batch="b2")

    res = admin_session.post(
        "/admin/candidates/review-llm", data={"csrf_token": _token(admin_session)}
    )

    assert res.status_code == 302
    assert sorted(enqueued) == [
        ("tasks.review_word_candidates", ("b1",)),
        ("tasks.review_word_candidates", ("b2",)),
    ]


def test_recent_reviewed_section_shows_llm_decisions(admin_session):
    done = _candidate("책상")
    done.status = CandidateStatus.REJECTED
    done.reject_reason = "LLM 심사 거절: 사전에 없는 말"
    done.reviewed_by = "llm:claude-sonnet-5-5"
    db.session.commit()

    html = admin_session.get("/admin/candidates").get_data(as_text=True)
    assert "최근 처리" in html
    assert "LLM 심사 거절: 사전에 없는 말" in html
    assert "llm:claude-sonnet-5-5" in html
