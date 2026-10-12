from app.extensions import db
from app.models import Guest, GuestStats
from app.schemas.stats import MyStatsResponse


def get_my_stats(guest: Guest) -> MyStatsResponse:
    # guest_service.issue_guest()가 Guest와 GuestStats를 항상 같이 만들기 때문에
    # 여기선 "없을 수도 있음"을 방어하지 않는다.
    stats = db.session.get(GuestStats, guest.id)
    return MyStatsResponse(
        current_streak=stats.current_streak,
        max_streak=stats.max_streak,
        solved_count=stats.solved_count,
    )
