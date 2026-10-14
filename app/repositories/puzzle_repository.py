from datetime import date

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word


def find_by_date(puzzle_date: date, language: PuzzleLanguage) -> DailyPuzzle | None:
    """퍼즐은 (날짜, 언어)당 하나다 — 언어를 생략할 수 없게 인자로 받는다."""
    return (
        db.session.query(DailyPuzzle)
        .filter_by(puzzle_date=puzzle_date, language=language)
        .first()
    )


def lock_by_date(puzzle_date: date, language: PuzzleLanguage) -> DailyPuzzle | None:
    """그 날짜·언어 퍼즐 행을 `SELECT ... FOR UPDATE` 로 잠그고 읽는다.

    운영자 교체(`puzzle_schedule_service.replace_assignment`)가 "시도 0건" 을 확인한
    뒤 단어를 바꾸기까지를 한 줄로 세우는 잠금이다. 이 잠금이 없으면 검사와 UPDATE
    사이에 첫 제출이 커밋돼서, 옛 정답으로 판정된 시도 행이 새 정답을 가리키게 된다
    (티켓 23 리뷰 D-23-1). 제출 쪽은 `lock_shared_answer` 로 같은 행을 공유 잠금으로
    잡아서, 둘 중 어느 쪽이 먼저 와도 뒤에 온 쪽이 앞의 결과를 보고 멈춘다.

    배정이 없는 날짜는 잠글 행이 없다(None). 그 경우의 중복 INSERT 는
    `uq_daily_puzzle_date_language` 가 막는다 — READ COMMITTED 에선 gap lock 이 없어서
    잠금으로는 못 막는다. 시도는 퍼즐이 있어야 생기므로 D-23-1 경합과는 무관하다.
    """
    return (
        db.session.query(DailyPuzzle)
        .filter_by(puzzle_date=puzzle_date, language=language)
        .with_for_update()
        .first()
    )


def lock_shared_answer(puzzle_id: int) -> str | None:
    """퍼즐 행과 그 단어 행을 공유 잠금(`LOCK IN SHARE MODE`)으로 잡고 현재 정답을 읽는다.

    제출(`guess_service.submit_guess`)이 커밋까지 이 잠금을 쥐고 있으면 운영자 교체의
    `FOR UPDATE` 가 제출을 지나치지 못한다. 공유 잠금이라 제출끼리는 서로를 막지
    않는다 — 같은 퍼즐을 푸는 사람들이 한 줄로 서지 않게 하려고 배타 잠금을 쓰지
    않았다. 퍼즐이 사라졌으면 None.
    """
    row = (
        db.session.query(Word.answer)
        .join(DailyPuzzle, DailyPuzzle.word_id == Word.id)
        .filter(DailyPuzzle.id == puzzle_id)
        .with_for_update(read=True)
        .first()
    )
    return row[0] if row else None


def list_in_range(
    language: PuzzleLanguage, start_date: date, end_date: date
) -> list[DailyPuzzle]:
    """기간 안의 그 언어 퍼즐. 운영자 배정표가 30일을 한 번에 읽는다 —
    날짜마다 `find_by_date` 를 부르면 쿼리가 30개가 된다.

    단어까지 같이 읽는다(`joinedload`) — 배정표는 행마다 정답·카테고리·가림을
    그려서, 지연 로딩이면 쿼리가 다시 30개로 돌아간다.
    """
    return (
        db.session.query(DailyPuzzle)
        .options(joinedload(DailyPuzzle.word))
        .filter(
            DailyPuzzle.language == language,
            DailyPuzzle.puzzle_date >= start_date,
            DailyPuzzle.puzzle_date <= end_date,
        )
        .order_by(DailyPuzzle.puzzle_date)
        .all()
    )
