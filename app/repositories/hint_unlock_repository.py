from app.extensions import db
from app.models import HintUnlock


def is_unlocked(guest_id: int, puzzle_id: int) -> bool:
    """이 게스트가 이 퍼즐의 힌트를 이미 열었는가.

    조회 경로(`GET /puzzles/today`, 제출 응답)가 요청마다 부르므로 행 전체가
    아니라 존재 여부만 읽는다.
    """
    return (
        db.session.query(HintUnlock.guest_id)
        .filter_by(guest_id=guest_id, puzzle_id=puzzle_id)
        .first()
        is not None
    )
