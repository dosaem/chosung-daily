from app.errors import AlreadyFinishedError, HintAlreadyUnlockedError, PuzzleChangedError
from app.extensions import db
from app.models import Guest, HintUnlock
from app.repositories.attempt_repository import list_for_guest_puzzle
from app.repositories.guest_stats_repository import lock_for_guest
from app.repositories.hint_unlock_repository import is_unlocked
from app.schemas.puzzle import HintUnlockResponse
from app.services.game_rules import compute_reveal, summarize_attempts
from app.services.puzzle_service import get_today_puzzle_or_404


def unlock_hint(guest: Guest, puzzle_id: int | None) -> HintUnlockResponse:
    """힌트 미리 보기 하나 = 트랜잭션 하나.

    제출(`app/services/guess_service.py`)과 같은 순서를 밟는다: 퍼즐 조회 →
    `puzzle_id` 확인 → GuestStats 잠금(`SELECT ... FOR UPDATE`) → 그 안에서
    시도 이력과 열림 여부를 다시 읽는다. 같은 게스트의 제출과 힌트 미리 보기가
    동시에 들어와도 한 줄로 세워지고(`tests/test_concurrency.py`), "끝난 퍼즐인가"
    판정이 제출이 방금 만든 5번째 시도까지 보고 내려진다.

    서버는 보상형 광고를 실제로 봤는지 알 수 없다(AdMob SSV 미사용, README
    "설계 판단"). 그래서 구독자·비구독자를 가르지 않고, 광고 시청 여부도 묻지
    않는다 — 이 엔드포인트가 지키는 건 "퍼즐당 한 번"과 "시도·순위에 영향 없음"
    두 가지뿐이다. 시도 행도 GuestStats 도 건드리지 않는 이유가 그것이다.
    """
    puzzle = get_today_puzzle_or_404(guest.puzzle_language)
    if puzzle_id != puzzle.id:
        raise PuzzleChangedError()

    lock_for_guest(guest.id)

    attempts = list_for_guest_puzzle(guest.id, puzzle.id)
    solved, wrong_count = summarize_attempts(attempts)
    finished, _ = compute_reveal(len(attempts), wrong_count, solved)
    if finished:
        # 끝난 퍼즐은 이미 정답을 보여준 상태다 — 광고를 보여주고 힌트를 파는 건
        # 플레이어를 속이는 쪽이라 막는다.
        raise AlreadyFinishedError()

    if is_unlocked(guest.id, puzzle.id):
        raise HintAlreadyUnlockedError()

    db.session.add(HintUnlock(guest_id=guest.id, puzzle_id=puzzle.id))
    db.session.commit()

    return HintUnlockResponse(hint=puzzle.word.hint)
