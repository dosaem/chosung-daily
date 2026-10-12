import random
from datetime import date, datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import DailyPuzzle, Word, WordCategory

# 월=0 ... 일=6 (datetime.date.weekday() 기준). 책 제목은 매일 섞으면 체감 난이도가
# 들쭉날쭉해서(안 읽어본 사람한텐 그냥 모르는 단어 + 여러 단어짜리면 초성도 김)
# 일주일에 한 번, 일요일에만 후보로 넣는 "특별 라운드"로 뺐다(사용자 피드백 반영).
BOOK_TITLE_WEEKDAY = 6


def schedule_puzzles(days: int = 30, avoid_days: int = 14) -> int:
    """오늘(KST)부터 days일치 DailyPuzzle을 배정한다. 이미 있는 날짜는 건너뛴다.

    트랜잭션 경계: 전체를 하나의 커밋 단위로 묶는다 — 중간에 실패하면 이번 실행에서
    새로 만든 배정은 전부 롤백된다 (하루치만 반영되는 반쪼가리 상태를 피하려고).
    """
    today = datetime.now(KST).date()
    created = 0

    for offset in range(days):
        target_date = today + timedelta(days=offset)
        if db.session.query(DailyPuzzle.id).filter_by(puzzle_date=target_date).first():
            continue

        word = _pick_word(target_date, avoid_days)
        db.session.add(DailyPuzzle(puzzle_date=target_date, word_id=word.id))
        created += 1

    db.session.commit()
    return created


def _pick_word(target_date: date, avoid_days: int) -> Word:
    cutoff = target_date - timedelta(days=avoid_days)
    recently_used_ids = (
        db.session.query(DailyPuzzle.word_id)
        .filter(DailyPuzzle.puzzle_date >= cutoff, DailyPuzzle.puzzle_date < target_date)
        .distinct()
    )

    preferred_category = (
        WordCategory.BOOK_TITLE
        if target_date.weekday() == BOOK_TITLE_WEEKDAY
        else WordCategory.GENERAL
    )
    candidates = Word.query.filter(
        Word.category == preferred_category, ~Word.id.in_(recently_used_ids)
    ).all()

    if not candidates:
        # 원하는 카테고리에 후보가 없으면(예: 일요일인데 최근에 안 쓴 책 제목이
        # 없음) 카테고리 제한을 풀고 다시 찾는다 — 빈 날짜를 만들진 않는다.
        candidates = Word.query.filter(~Word.id.in_(recently_used_ids)).all()

    if candidates:
        return random.choice(candidates)

    # 최근 avoid_days일 안 쓴 단어가 하나도 없음 (단어 풀이 작아서 생기는 상황).
    # 그럴 땐 그냥 가장 오래전에 쓰인(혹은 한 번도 안 쓰인) 단어로 폴백한다.
    return _least_recently_used_word()


def _least_recently_used_word() -> Word:
    last_used_subq = (
        db.session.query(
            DailyPuzzle.word_id,
            db.func.max(DailyPuzzle.puzzle_date).label("last_used"),
        )
        .group_by(DailyPuzzle.word_id)
        .subquery()
    )
    # MySQL은 NULLS FIRST 문법이 없지만, ASC 정렬에서 NULL을 기본으로 맨 앞에
    # 두기 때문에(한 번도 안 쓰인 단어 우선) 그냥 .asc()만 쓰면 원하는 순서가 된다.
    word = (
        db.session.query(Word)
        .outerjoin(last_used_subq, Word.id == last_used_subq.c.word_id)
        .order_by(last_used_subq.c.last_used.asc())
        .first()
    )
    if word is None:
        raise ValueError("등록된 단어가 없습니다. flask seed-words로 먼저 시드하세요.")
    return word
