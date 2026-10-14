from datetime import date

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word, WordCategory

# LIKE 안에서 특수한 뜻을 갖는 글자와, 이스케이프에 쓸 글자.
_LIKE_WILDCARDS = ("\\", "%", "_")
_LIKE_ESCAPE = "\\"


def existing_keys() -> set[tuple[str, str, str]]:
    """등록된 모든 단어의 (language, answer, category). CSV 적재의 중복 판정용.

    행마다 쿼리를 날리지 않으려고 한 번에 다 읽는다 — 단어 풀은 수천 개 규모라
    (며칠치 = 개수, `word_pool_service`) 메모리에 들고 있어도 된다.
    """
    return {
        (language, answer, category)
        for language, answer, category in db.session.query(
            Word.language, Word.answer, Word.category
        ).all()
    }


def find_duplicate(
    language: PuzzleLanguage,
    answer: str,
    category: WordCategory,
    exclude_id: int | None = None,
) -> Word | None:
    """같은 (언어, 정답, 카테고리) 단어. 수정할 때는 자기 자신을 제외한다."""
    query = Word.query.filter_by(language=language, answer=answer, category=category)
    if exclude_id is not None:
        query = query.filter(Word.id != exclude_id)
    return query.first()


def search(
    *,
    language: PuzzleLanguage | None,
    category: WordCategory | None,
    keyword: str,
    page: int,
    per_page: int,
):
    """운영자 목록용 조회. 최근에 넣은 단어가 위로 온다.

    검색어는 정답과 힌트를 같이 본다 — 운영자가 "과일" 같은 힌트 조각으로 찾는
    경우가 많다. `Pagination` 을 그대로 돌려줘서 템플릿이 쪽수를 직접 계산하지 않는다.
    """
    stmt = db.select(Word).order_by(Word.id.desc())
    if language is not None:
        stmt = stmt.where(Word.language == language)
    if category is not None:
        stmt = stmt.where(Word.category == category)
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        stmt = stmt.where(
            db.or_(
                Word.answer.like(pattern, escape=_LIKE_ESCAPE),
                Word.hint.like(pattern, escape=_LIKE_ESCAPE),
            )
        )
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def assigned_puzzle_slots(word_id: int) -> list[tuple[date, PuzzleLanguage]]:
    """이 단어가 배정된 퍼즐의 (날짜, 언어). 날짜만으로는 캐시 키를 못 만든다 —
    캐시가 `puzzle:{date}:{lang}` 로 갈려 있어서(app/services/puzzle_cache.py)
    수정 후 무효화할 키를 고르려면 언어가 같이 필요하다."""
    return [
        (puzzle_date, language)
        for puzzle_date, language in db.session.query(
            DailyPuzzle.puzzle_date, DailyPuzzle.language
        )
        .filter_by(word_id=word_id)
        .order_by(DailyPuzzle.puzzle_date)
        .all()
    ]


def assigned_puzzle_dates(word_id: int) -> list[date]:
    """이 단어가 배정된 퍼즐 날짜들. 삭제를 막을지 판단하는 데 쓴다."""
    return [puzzle_date for puzzle_date, _ in assigned_puzzle_slots(word_id)]


def _escape_like(keyword: str) -> str:
    """검색어 안의 LIKE 와일드카드를 글자 그대로 찾게 바꾼다.

    이걸 빼면 검색어 `%` 한 글자가 전체 조회가 되고, 운영자는 필터가 걸린 줄
    알면서 전체 목록을 보게 된다.
    """
    for char in _LIKE_WILDCARDS:
        keyword = keyword.replace(char, _LIKE_ESCAPE + char)
    return keyword
