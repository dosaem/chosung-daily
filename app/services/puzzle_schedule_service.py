import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.config import KST
from app.errors import ValidationError
from app.extensions import db
from app.models import DailyPuzzle, PuzzleLanguage, Word, WordCategory
from app.repositories import attempt_repository, puzzle_repository
from app.services.puzzle_cache import invalidate_cached_puzzle

# 운영자 배정표가 보는 날 수 = 자정 배정이 미리 채워두는 날 수. 두 수가 갈리면
# 배정표 끝 며칠이 영영 "자정에 배정" 으로 남는다(티켓 23).
SCHEDULE_DAYS = 30

# 월=0 ... 일=6 (datetime.date.weekday() 기준). 책 제목은 매일 섞으면 체감 난이도가
# 들쭉날쭉해서(안 읽어본 사람한텐 그냥 모르는 단어 + 여러 단어짜리면 초성도 김)
# 일주일에 한 번, 일요일에만 후보로 넣는 "특별 라운드"로 뺐다(사용자 피드백 반영).
BOOK_TITLE_WEEKDAY = 6


def schedule_puzzles(
    language: PuzzleLanguage, days: int = SCHEDULE_DAYS, avoid_days: int = 14
) -> int:
    """오늘(KST)부터 days일치, 주어진 언어의 DailyPuzzle을 배정한다.

    퍼즐은 (날짜, 언어)당 하나라서 언어가 첫 인자다 — 같은 날짜에 다른 언어
    퍼즐이 있어도 "이미 있는 날짜"로 치지 않는다. 이미 그 언어 퍼즐이 있는
    날짜만 건너뛴다.

    트랜잭션 경계: 한 언어의 이번 실행 전체를 하나의 커밋 단위로 묶는다 — 중간에
    실패하면 이번 실행에서 새로 만든 배정은 전부 롤백된다 (하루치만 반영되는
    반쪼가리 상태를 피하려고). 언어 사이에는 경계를 두지 않는다 — 자정 배정이
    언어마다 이 함수를 따로 불러서 각각 커밋한다(README "설계 판단" 05).
    """
    today = datetime.now(KST).date()
    created = 0

    for offset in range(days):
        target_date = today + timedelta(days=offset)
        if (
            db.session.query(DailyPuzzle.id)
            .filter_by(puzzle_date=target_date, language=language)
            .first()
        ):
            continue

        word = _pick_word(language, target_date, avoid_days)
        db.session.add(
            DailyPuzzle(puzzle_date=target_date, language=language, word_id=word.id)
        )
        created += 1

    db.session.commit()
    return created


def _pick_word(language: PuzzleLanguage, target_date: date, avoid_days: int) -> Word:
    cutoff = target_date - timedelta(days=avoid_days)
    recently_used_ids = (
        db.session.query(DailyPuzzle.word_id)
        .filter(
            DailyPuzzle.language == language,
            DailyPuzzle.puzzle_date >= cutoff,
            DailyPuzzle.puzzle_date < target_date,
        )
        .distinct()
    )

    preferred_category = (
        WordCategory.BOOK_TITLE
        if target_date.weekday() == BOOK_TITLE_WEEKDAY
        else WordCategory.GENERAL
    )
    candidates = Word.query.filter(
        Word.language == language,
        Word.category == preferred_category,
        ~Word.id.in_(recently_used_ids),
    ).all()

    if not candidates:
        # 원하는 카테고리에 후보가 없으면(예: 일요일인데 최근에 안 쓴 책 제목이
        # 없음) 카테고리 제한을 풀고 다시 찾는다 — 빈 날짜를 만들진 않는다.
        candidates = Word.query.filter(
            Word.language == language, ~Word.id.in_(recently_used_ids)
        ).all()

    if candidates:
        return random.choice(candidates)

    # 최근 avoid_days일 안 쓴 단어가 하나도 없음 (단어 풀이 작아서 생기는 상황).
    # 그럴 땐 그냥 가장 오래전에 쓰인(혹은 한 번도 안 쓰인) 단어로 폴백한다.
    return _least_recently_used_word(language)


def _least_recently_used_word(language: PuzzleLanguage) -> Word:
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
        .filter(Word.language == language)
        .order_by(last_used_subq.c.last_used.asc())
        .first()
    )
    if word is None:
        # 자정 배정은 이 예외를 잡아 운영자에게 알리고 다음 언어로 넘어간다
        # (app/services/puzzle_maintenance_service.py).
        raise ValueError(
            f"{language.value} 단어가 하나도 없습니다. flask seed-words로 먼저 시드하세요."
        )
    return word


@dataclass(frozen=True)
class ScheduledDay:
    """배정표 한 줄. 아직 배정이 없는 날짜도 `word=None` 으로 한 줄을 차지한다 —
    운영자가 비어 있는 날짜를 봐야 "자정에 배정" 인지 알 수 있다."""

    puzzle_date: date
    puzzle_id: int | None
    word: Word | None
    attempt_count: int

    @property
    def is_locked(self) -> bool:
        """시도가 한 건이라도 있으면 그 날짜의 단어는 못 바꾼다 — 이미 푼 사람의
        시도 이력이 다른 정답을 가리키게 된다."""
        return self.attempt_count > 0


def upcoming_schedule(
    language: PuzzleLanguage, days: int = SCHEDULE_DAYS
) -> list[ScheduledDay]:
    """오늘(KST)부터 days일치 배정 현황. 운영자 배정표가 그대로 그린다.

    날짜 창은 `schedule_puzzles` 와 같다(오늘 + days일) — 배정표에 보이는 날짜가
    자정 배정이 채우는 날짜여야 "미배정 = 자정에 배정" 이 참이 된다. 쓰기는 하지
    않는다: GET 으로 들어온 조회가 배정을 만들면 운영자가 보기만 해도 단어 풀이
    줄어든다(배정은 Beat 와 교체 폼만 한다).
    """
    today = datetime.now(KST).date()
    last_date = today + timedelta(days=days - 1)

    puzzles = {
        puzzle.puzzle_date: puzzle
        for puzzle in puzzle_repository.list_in_range(language, today, last_date)
    }
    attempt_counts = attempt_repository.count_by_puzzle(
        [puzzle.id for puzzle in puzzles.values()]
    )

    schedule = []
    for offset in range(days):
        target_date = today + timedelta(days=offset)
        puzzle = puzzles.get(target_date)
        schedule.append(
            ScheduledDay(
                puzzle_date=target_date,
                puzzle_id=puzzle.id if puzzle else None,
                word=puzzle.word if puzzle else None,
                attempt_count=attempt_counts.get(puzzle.id, 0) if puzzle else 0,
            )
        )
    return schedule


def replace_assignment(
    puzzle_date: date, language: PuzzleLanguage, word_id: int
) -> DailyPuzzle:
    """그 날짜·언어의 퍼즐 단어를 바꾼다(배정이 없으면 새로 만든다).

    막는 두 경우:

    - **지난 날짜.** 이미 지난 퍼즐은 기록이다 — 통계·리더보드·시도 이력이 그
      단어를 가리키고 있다.
    - **시도가 있는 날짜(보통 오늘).** 누군가 이미 제출했으면 그 사람의 시도는
      다른 정답과 비교된 결과다. 오늘이어도 시도가 없으면 바꿀 수 있다 —
      운영자가 자정 직후에 기념일 문제로 갈아끼우는 게 US 54 의 주 용도다.

    "시도 없음" 검사는 퍼즐 행을 `FOR UPDATE` 로 잠근 뒤에 한다 — 검사와 UPDATE
    사이에 첫 제출이 커밋되면 그 시도는 옛 정답으로 판정됐는데 보드는 새 정답을
    가리키게 된다(리뷰 D-23-1). 제출 쪽도 같은 행을 공유 잠금으로 잡으므로
    (`guess_service.submit_guess`) 어느 쪽이 먼저 오든 뒤에 온 쪽이 멈춘다: 제출이
    먼저면 여기서 "시도 1건" 을 보고 거부하고, 교체가 먼저면 제출이 바뀐 정답을 보고
    PUZZLE_CHANGED 로 끊긴다.

    커밋이 끝난 뒤 `puzzle:{date}:{lang}` 캐시를 지운다 — 오늘 퍼즐 읽기가
    cache-aside 라(`puzzle_service.get_today_puzzle_or_404`) 안 지우면 TTL 26시간
    동안 옛 단어가 계속 나간다. 롤백된 교체가 캐시를 날리지 않게 순서를 그렇게 뒀다.
    """
    today = datetime.now(KST).date()
    if puzzle_date < today:
        raise ValidationError(f"지난 날짜({puzzle_date.isoformat()})의 퍼즐은 바꿀 수 없습니다.")

    word = db.session.get(Word, word_id)
    if word is None:
        raise ValidationError("단어를 찾을 수 없습니다 (목록에서 다시 골라주세요).")
    if word.language is not language:
        raise ValidationError(
            f"퍼즐과 단어의 언어가 다릅니다 — {language.value} 퍼즐에는 "
            f"{language.value} 단어만 배정할 수 있어요 (고른 단어는 {word.language.value})."
        )

    puzzle = puzzle_repository.lock_by_date(puzzle_date, language)
    if puzzle is not None:
        attempts = attempt_repository.count_by_puzzle([puzzle.id]).get(puzzle.id, 0)
        if attempts:
            raise ValidationError(
                f"이미 시도가 {attempts}건 있는 날짜({puzzle_date.isoformat()})는 "
                "단어를 바꿀 수 없습니다."
            )
        puzzle.word_id = word.id
    else:
        puzzle = DailyPuzzle(
            puzzle_date=puzzle_date, language=language, word_id=word.id
        )
        db.session.add(puzzle)

    db.session.commit()
    invalidate_cached_puzzle(puzzle_date, language)
    return puzzle
