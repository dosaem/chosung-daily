"""운영자 배정표(`/admin/schedule`) — 30일 표·언어 탭·잔량 카드·단어 교체.

폼 토큰은 세션을 직접 건드리지 않고 **실제로 렌더된 폼에서 뽑아** 쓴다(티켓 15
테스트와 같은 요령) — 토큰이 1회용이라 그 왕복까지 테스트가 밟는다.
"""

import re
from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import Attempt, DailyPuzzle, PuzzleLanguage, Word, WordCategory
from app.services.guest_service import issue_guest
from app.services.puzzle_schedule_service import SCHEDULE_DAYS
from app.services.puzzle_service import get_today_puzzle_or_404
from app.services.word_pool_service import LOW_WORD_POOL_THRESHOLD_DAYS

CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


def _token(client, path):
    html = client.get(path).get_data(as_text=True)
    match = CSRF_PATTERN.search(html)
    assert match, f"{path} 에 csrf_token hidden 이 없다"
    return match.group(1)


def _today():
    return datetime.now(KST).date()


def _add_word(answer, language=PuzzleLanguage.KO, category=WordCategory.GENERAL):
    word = Word(
        answer=answer, language=language, category=category, hint=f"{answer} 힌트"
    )
    db.session.add(word)
    db.session.commit()
    return word


def _assign(puzzle_date, word, language=PuzzleLanguage.KO):
    puzzle = DailyPuzzle(puzzle_date=puzzle_date, language=language, word_id=word.id)
    db.session.add(puzzle)
    db.session.commit()
    return puzzle


def _attempt(puzzle):
    guest = issue_guest()
    db.session.add(
        Attempt(
            guest_id=guest.id,
            puzzle_id=puzzle.id,
            guess="오답",
            is_correct=False,
            attempt_no=1,
        )
    )
    db.session.commit()


# --- 배정표 --------------------------------------------------------------


def test_the_schedule_page_shows_thirty_days(admin_session):
    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    today = _today()
    assert today.isoformat() in html
    assert (today + timedelta(days=SCHEDULE_DAYS - 1)).isoformat() in html
    assert (today + timedelta(days=SCHEDULE_DAYS)).isoformat() not in html


def test_the_schedule_page_shows_the_assigned_word(admin_session):
    _assign(_today(), _add_word("사과"))

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "사과" in html


def test_a_day_without_an_assignment_says_it_is_filled_at_midnight(admin_session):
    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "자정에 배정" in html


def test_the_language_tab_switches_the_table(admin_session):
    _assign(_today(), _add_word("사과"))
    _assign(_today(), _add_word("apple", language=PuzzleLanguage.EN), PuzzleLanguage.EN)

    ko = admin_session.get("/admin/schedule?language=ko").get_data(as_text=True)
    en = admin_session.get("/admin/schedule?language=en").get_data(as_text=True)

    assert "사과" in ko
    assert "apple" not in ko
    assert "apple" in en
    assert "사과" not in en


def test_an_unknown_language_falls_back_to_korean(admin_session):
    """손으로 URL 을 고친 요청 때문에 배정표가 에러 페이지가 되면 안 된다."""
    _assign(_today(), _add_word("사과"))

    html = admin_session.get("/admin/schedule?language=fr").get_data(as_text=True)

    assert "사과" in html


def test_the_schedule_page_needs_an_admin_session(client):
    assert client.get("/admin/schedule").status_code == 302


# --- 잔량 카드 -----------------------------------------------------------


def test_the_stock_card_counts_unused_words_per_language(admin_session):
    _add_word("사과")
    _add_word("학교")
    _add_word("apple", language=PuzzleLanguage.EN)

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "2일치" in html
    assert "1일치" in html


def test_an_assigned_word_leaves_the_stock(admin_session):
    _assign(_today(), _add_word("사과"))

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "0일치" in html


def test_a_stock_under_two_weeks_is_marked_low(admin_session):
    _add_word("사과")

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "admin-stock-low" in html
    assert str(LOW_WORD_POOL_THRESHOLD_DAYS) in html


def test_a_healthy_stock_is_not_marked_low(admin_session):
    for i in range(LOW_WORD_POOL_THRESHOLD_DAYS):
        _add_word(f"단어{i}")
    for i in range(LOW_WORD_POOL_THRESHOLD_DAYS):
        _add_word(f"word{i}", language=PuzzleLanguage.EN)

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert "admin-stock-low" not in html


# --- 교체 ----------------------------------------------------------------


def test_the_replace_page_lists_candidate_words_of_that_language(admin_session):
    _add_word("사과")
    _add_word("apple", language=PuzzleLanguage.EN)
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    html = admin_session.get(f"/admin/schedule/{tomorrow}/replace?language=ko").get_data(
        as_text=True
    )

    assert "사과" in html
    assert "apple" not in html


def test_the_replace_page_can_be_searched(admin_session):
    _add_word("사과")
    _add_word("학교")
    tomorrow = (_today() + timedelta(days=1)).isoformat()

    html = admin_session.get(
        f"/admin/schedule/{tomorrow}/replace?language=ko&q=학교"
    ).get_data(as_text=True)

    assert "학교" in html
    assert "사과" not in html


def test_replacing_a_future_day_swaps_the_word(admin_session):
    tomorrow = _today() + timedelta(days=1)
    puzzle = _assign(tomorrow, _add_word("사과"))
    replacement = _add_word("학교")
    path = f"/admin/schedule/{tomorrow.isoformat()}/replace"

    res = admin_session.post(
        path,
        data={
            "csrf_token": _token(admin_session, f"{path}?language=ko"),
            "language": "ko",
            "word_id": replacement.id,
        },
    )

    assert res.status_code == 302
    assert db.session.get(DailyPuzzle, puzzle.id).word_id == replacement.id
    assert "학교" in admin_session.get("/admin/schedule").get_data(as_text=True)


def test_replacing_today_drops_the_puzzle_cache(admin_session):
    """읽기 경로가 cache-aside 라, 캐시를 안 지우면 TTL 26시간 동안 옛 단어가 나간다."""
    today = _today()
    _assign(today, _add_word("사과"))
    get_today_puzzle_or_404(PuzzleLanguage.KO)  # 캐시를 채운다
    replacement = _add_word("학교")
    path = f"/admin/schedule/{today.isoformat()}/replace"

    admin_session.post(
        path,
        data={
            "csrf_token": _token(admin_session, f"{path}?language=ko"),
            "language": "ko",
            "word_id": replacement.id,
        },
    )

    assert get_today_puzzle_or_404(PuzzleLanguage.KO).word.answer == "학교"


def test_replacing_a_day_that_has_attempts_is_refused(admin_session):
    today = _today()
    puzzle = _assign(today, _add_word("사과"))
    _attempt(puzzle)
    replacement = _add_word("학교")
    path = f"/admin/schedule/{today.isoformat()}/replace"

    res = admin_session.post(
        path,
        data={
            "csrf_token": _token(admin_session, f"{path}?language=ko"),
            "language": "ko",
            "word_id": replacement.id,
        },
        follow_redirects=True,
    )

    assert "시도" in res.get_data(as_text=True)
    assert db.session.get(DailyPuzzle, puzzle.id).word_id != replacement.id


def test_a_day_with_attempts_offers_no_replace_link(admin_session):
    today = _today()
    _attempt(_assign(today, _add_word("사과")))

    html = admin_session.get("/admin/schedule").get_data(as_text=True)

    assert f"/admin/schedule/{today.isoformat()}/replace" not in html
    assert "교체 불가" in html


def test_replacing_an_unassigned_day_assigns_the_word(admin_session):
    target = _today() + timedelta(days=5)
    word = _add_word("사과")
    path = f"/admin/schedule/{target.isoformat()}/replace"

    admin_session.post(
        path,
        data={
            "csrf_token": _token(admin_session, f"{path}?language=ko"),
            "language": "ko",
            "word_id": word.id,
        },
    )

    puzzle = DailyPuzzle.query.filter_by(
        puzzle_date=target, language=PuzzleLanguage.KO
    ).one()
    assert puzzle.word_id == word.id


def test_a_replacement_without_a_csrf_token_is_forbidden(admin_session):
    tomorrow = _today() + timedelta(days=1)
    puzzle = _assign(tomorrow, _add_word("사과"))
    replacement = _add_word("학교")

    res = admin_session.post(
        f"/admin/schedule/{tomorrow.isoformat()}/replace",
        data={"language": "ko", "word_id": replacement.id},
    )

    assert res.status_code == 403
    assert db.session.get(DailyPuzzle, puzzle.id).word_id != replacement.id


def test_a_word_of_the_other_language_is_refused(admin_session):
    """ko 교체 화면은 ko 단어만 보여주지만, 손으로 고친 요청·옛 화면은 다른 언어의
    id 를 보낼 수 있다 — 서버가 막는다(퍼즐 언어 불변식)."""
    tomorrow = _today() + timedelta(days=1)
    _add_word("사과")  # 후보가 하나라도 있어야 폼(=토큰)이 그려진다
    english = _add_word("apple", language=PuzzleLanguage.EN)
    path = f"/admin/schedule/{tomorrow.isoformat()}/replace"

    res = admin_session.post(
        path,
        data={
            "csrf_token": _token(admin_session, f"{path}?language=ko"),
            "language": "ko",
            "word_id": english.id,
        },
        follow_redirects=True,
    )

    assert "언어" in res.get_data(as_text=True)
    assert DailyPuzzle.query.count() == 0


def test_a_date_outside_the_window_is_not_found(admin_session):
    far = (_today() + timedelta(days=SCHEDULE_DAYS + 1)).isoformat()

    assert admin_session.get(f"/admin/schedule/{far}/replace?language=ko").status_code == 404


def test_a_malformed_date_is_not_found(admin_session):
    assert admin_session.get("/admin/schedule/2026-13-99/replace").status_code == 404
