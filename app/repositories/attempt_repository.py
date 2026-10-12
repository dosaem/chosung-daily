from app.extensions import db
from app.models import Attempt


def list_for_guest_puzzle(guest_id: int, puzzle_id: int) -> list[Attempt]:
    return (
        db.session.query(Attempt)
        .filter_by(guest_id=guest_id, puzzle_id=puzzle_id)
        .order_by(Attempt.attempt_no)
        .all()
    )
