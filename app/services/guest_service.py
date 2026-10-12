from app.extensions import db
from app.models import Guest, GuestStats
from app.repositories.guest_repository import find_by_token


def issue_guest() -> Guest:
    """게스트 토큰을 발급한다. GuestStats를 같은 트랜잭션에서 같이 만들어서,
    이후 코드가 "게스트가 있으면 stats도 항상 있다"는 전제를 믿고 쓸 수 있게 한다.
    """
    guest = Guest()
    db.session.add(guest)
    db.session.flush()  # GuestStats.guest_id FK를 쓰려면 guest.id가 먼저 필요

    db.session.add(GuestStats(guest_id=guest.id))
    db.session.commit()
    return guest


def get_guest_by_token(token: str) -> Guest | None:
    return find_by_token(token)
