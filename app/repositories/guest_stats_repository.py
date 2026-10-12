from app.extensions import db
from app.models import GuestStats


def lock_for_guest(guest_id: int) -> GuestStats:
    """GuestStats 행을 SELECT ... FOR UPDATE로 잠근다.

    같은 게스트의 동시 제출을 여기서 직렬화한다 (동시성 설계는
    app/services/guess_service.py의 submit_guess 독스트링 참고).
    """
    return db.session.query(GuestStats).filter_by(guest_id=guest_id).with_for_update().one()
