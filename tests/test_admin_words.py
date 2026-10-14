"""운영자 단어 CRUD 페이지 — 목록·필터·페이지네이션·추가·수정·삭제.

폼 토큰은 세션을 직접 건드리지 않고 **실제로 렌더된 폼에서 뽑아** 쓴다. 토큰이
1회용이라(app/csrf.py) 페이지를 다시 그리면 토큰도 새로 받아야 하는데, 그 왕복까지
테스트가 그대로 밟는다.
"""

import re

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word, WordCategory
from app.services.puzzle_service import get_today_puzzle_or_404
from app.services.word_service import ADMIN_WORDS_PER_PAGE

CSRF_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


def _token(client, path="/admin/words/new"):
    html = client.get(path).get_data(as_text=True)
    match = CSRF_PATTERN.search(html)
    assert match, f"{path} 에 csrf_token hidden 이 없다"
    return match.group(1)


def _add_words(*answers, language=PuzzleLanguage.KO, category=WordCategory.GENERAL):
    for answer in answers:
        db.session.add(
            Word(answer=answer, language=language, category=category, hint=f"{answer} 힌트")
        )
    db.session.commit()


# --- 목록 ----------------------------------------------------------------


def test_words_page_lists_registered_words(admin_session):
    _add_words("사과", "학교")

    html = admin_session.get("/admin/").get_data(as_text=True)

    assert "사과" in html
    assert "학교" in html


def test_words_page_filters_by_language(admin_session):
    _add_words("사과")
    _add_words("apple", language=PuzzleLanguage.EN)

    html = admin_session.get("/admin/?language=en").get_data(as_text=True)

    assert "APPLE" in html or "apple" in html
    assert "사과" not in html


def test_words_page_filters_by_category(admin_session):
    _add_words("사과")
    _add_words("데미안", category=WordCategory.BOOK_TITLE)

    html = admin_session.get("/admin/?category=book_title").get_data(as_text=True)

    assert "데미안" in html
    assert "사과" not in html


def test_words_page_filters_by_keyword_over_answer_and_hint(admin_session):
    _add_words("사과", "학교")

    by_answer = admin_session.get("/admin/?q=사과").get_data(as_text=True)
    assert "사과" in by_answer
    assert "학교" not in by_answer

    by_hint = admin_session.get("/admin/?q=학교 힌트").get_data(as_text=True)
    assert "학교" in by_hint
    assert "사과" not in by_hint


def test_keyword_wildcards_are_matched_literally(admin_session):
    """LIKE 와일드카드를 그대로 흘리면 `%` 한 글자가 전체 검색이 된다."""
    _add_words("사과", "100%")

    html = admin_session.get("/admin/?q=%").get_data(as_text=True)

    assert "100%" in html
    assert "사과" not in html


def test_words_page_paginates(admin_session):
    _add_words(*[f"단어{index:03d}" for index in range(ADMIN_WORDS_PER_PAGE + 3)])

    first = admin_session.get("/admin/").get_data(as_text=True)
    second = admin_session.get("/admin/?page=2").get_data(as_text=True)

    assert first.count("<tr") == ADMIN_WORDS_PER_PAGE + 1  # 헤더 행 포함
    assert second.count("<tr") == 4
    assert "2 / 2" in second


def test_pagination_keeps_the_current_filter(admin_session):
    _add_words(*[f"단어{index:03d}" for index in range(ADMIN_WORDS_PER_PAGE + 1)])
    _add_words("apple", language=PuzzleLanguage.EN)

    html = admin_session.get("/admin/?language=ko").get_data(as_text=True)

    assert "page=2&amp;language=ko" in html or "language=ko&amp;page=2" in html


# --- 추가 ----------------------------------------------------------------


def test_create_word_saves_the_word_and_its_mask(admin_session):
    res = admin_session.post(
        "/admin/words",
        data={
            "csrf_token": _token(admin_session),
            "language": "ko",
            "category": "general",
            "answer": "지하철역",
            "hint": "타는 곳",
        },
    )

    assert res.status_code == 302
    word = Word.query.one()
    assert word.answer == "지하철역"
    assert [tile["c"] for tile in word.mask] == ["ㅈ", "ㅎ", "ㅊ", "ㅇ"]
    assert word.chosung == "ㅈㅎㅊㅇ"


def test_create_word_rejects_a_duplicate(admin_session):
    _add_words("사과")

    res = admin_session.post(
        "/admin/words",
        data={
            "csrf_token": _token(admin_session),
            "language": "ko",
            "category": "general",
            "answer": "사과",
            "hint": "다른 힌트",
        },
    )

    assert res.status_code == 200  # 폼을 다시 그린다
    assert "이미 등록된 단어" in res.get_data(as_text=True)
    assert Word.query.count() == 1


def test_create_word_rejects_a_blank_answer(admin_session):
    res = admin_session.post(
        "/admin/words",
        data={
            "csrf_token": _token(admin_session),
            "language": "ko",
            "category": "general",
            "answer": "   ",
            "hint": "힌트",
        },
    )

    assert res.status_code == 200
    assert "정답" in res.get_data(as_text=True)
    assert Word.query.count() == 0


def test_create_word_without_a_csrf_token_is_forbidden(admin_session):
    res = admin_session.post(
        "/admin/words",
        data={"language": "ko", "category": "general", "answer": "사과", "hint": "과일"},
    )

    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"
    assert Word.query.count() == 0


# --- 수정 ----------------------------------------------------------------


def test_edit_form_shows_the_current_values(admin_session):
    _add_words("사과")
    word_id = Word.query.one().id

    html = admin_session.get(f"/admin/words/{word_id}/edit").get_data(as_text=True)

    assert 'value="사과"' in html
    assert "사과 힌트" in html


def test_update_word_recalculates_the_mask(admin_session):
    _add_words("사과")
    word_id = Word.query.one().id

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{word_id}/edit"),
            "language": "en",
            "category": "general",
            "answer": "apple",
            "hint": "red fruit",
        },
    )

    assert res.status_code == 302
    word = db.session.get(Word, word_id)
    assert word.language == PuzzleLanguage.EN
    assert [tile["t"] for tile in word.mask] == ["h", "r", "r", "r", "h"]


def test_update_word_rejects_a_duplicate_of_another_word(admin_session):
    _add_words("사과", "학교")
    target = Word.query.filter_by(answer="학교").one()

    res = admin_session.post(
        f"/admin/words/{target.id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{target.id}/edit"),
            "language": "ko",
            "category": "general",
            "answer": "사과",
            "hint": "과일",
        },
    )

    assert res.status_code == 200
    assert "이미 등록된 단어" in res.get_data(as_text=True)
    assert db.session.get(Word, target.id).answer == "학교"


def test_update_word_can_keep_its_own_answer(admin_session):
    """자기 자신은 중복이 아니다 — 힌트만 고치는 게 가장 흔한 수정이다."""
    _add_words("사과")
    word_id = Word.query.one().id

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{word_id}/edit"),
            "language": "ko",
            "category": "general",
            "answer": "사과",
            "hint": "고친 힌트",
        },
    )

    assert res.status_code == 302
    assert db.session.get(Word, word_id).hint == "고친 힌트"


def test_update_word_without_a_csrf_token_is_forbidden(admin_session):
    _add_words("사과")
    word_id = Word.query.one().id

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={"language": "ko", "category": "general", "answer": "바뀜", "hint": "힌트"},
    )

    assert res.status_code == 403
    assert db.session.get(Word, word_id).answer == "사과"


def test_edit_form_404_for_an_unknown_word(admin_session):
    assert admin_session.get("/admin/words/9999/edit").status_code == 404


# --- 삭제 ----------------------------------------------------------------


def test_delete_word_removes_it(admin_session):
    _add_words("사과")
    word_id = Word.query.one().id

    res = admin_session.post(
        f"/admin/words/{word_id}/delete",
        data={"csrf_token": _token(admin_session, "/admin/")},
    )

    assert res.status_code == 302
    assert Word.query.count() == 0


def test_delete_is_blocked_for_a_word_already_assigned_to_a_puzzle(admin_session, today_puzzle):
    """퍼즐에 배정된 단어를 지우면 그 날짜의 퍼즐이 깨진다 — 배정을 먼저 바꿔야 한다."""
    word_id = today_puzzle.word_id

    res = admin_session.post(
        f"/admin/words/{word_id}/delete",
        data={"csrf_token": _token(admin_session, "/admin/")},
        follow_redirects=True,
    )

    assert res.status_code == 200
    assert "배정" in res.get_data(as_text=True)
    assert db.session.get(Word, word_id) is not None
    assert db.session.get(DailyPuzzle, today_puzzle.id) is not None


def test_delete_without_a_csrf_token_is_forbidden(admin_session):
    _add_words("사과")
    word_id = Word.query.one().id

    res = admin_session.post(f"/admin/words/{word_id}/delete", data={})

    assert res.status_code == 403
    assert Word.query.count() == 1


# --- 배정된 단어 수정 (수정 라운드 1: D-15-1, D-15-2) -----------------------


def test_update_word_makes_the_change_visible_in_todays_puzzle(admin_session, today_puzzle):
    """D-15-1 재현: 캐시가 먼저 채워져 있으면 수정이 플레이어에게 안 보였다.

    오늘 퍼즐 읽기는 Redis cache-aside 라서(app/services/puzzle_service.py), 수정이
    DB 만 고치고 캐시를 그대로 두면 TTL 26시간 동안 옛 힌트가 계속 나간다.
    """
    word_id = today_puzzle.word_id
    before = get_today_puzzle_or_404(PuzzleLanguage.KO)  # 캐시 채우기
    assert before.word.hint == "빨간 과일"

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{word_id}/edit"),
            "language": "ko",
            "category": "general",
            "answer": "사과",
            "hint": "고친 힌트",
        },
    )

    assert res.status_code == 302
    assert db.session.get(Word, word_id).hint == "고친 힌트"
    assert get_today_puzzle_or_404(PuzzleLanguage.KO).word.hint == "고친 힌트"


def test_update_word_rejects_a_language_change_for_an_assigned_word(admin_session, today_puzzle):
    """D-15-2 재현: ko 퍼즐이 참조하는 단어를 en 으로 바꾸면 퍼즐 언어가 거짓이 된다."""
    word_id = today_puzzle.word_id

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{word_id}/edit"),
            "language": "en",
            "category": "general",
            "answer": "apple",
            "hint": "red fruit",
        },
    )

    assert res.status_code == 200
    assert "배정" in res.get_data(as_text=True)
    word = db.session.get(Word, word_id)
    assert word.language == PuzzleLanguage.KO
    assert word.answer == "사과"
    assert get_today_puzzle_or_404(PuzzleLanguage.KO).word.answer == "사과"


def test_update_word_can_change_language_when_it_is_not_assigned(admin_session, today_puzzle):
    """배정되지 않은 단어는 그대로 언어를 바꿀 수 있다 — 막는 범위를 좁게 둔다."""
    _add_words("학교")
    word_id = Word.query.filter_by(answer="학교").one().id

    res = admin_session.post(
        f"/admin/words/{word_id}",
        data={
            "csrf_token": _token(admin_session, f"/admin/words/{word_id}/edit"),
            "language": "en",
            "category": "general",
            "answer": "school",
            "hint": "learning place",
        },
    )

    assert res.status_code == 302
    assert db.session.get(Word, word_id).language == PuzzleLanguage.EN
