from app.extensions import db
from app.models import Guest, GuestStats
from app.repositories.account_repository import find_by_guest
from app.schemas.stats import LinkedAccount, MyStatsResponse


def get_my_stats(guest: Guest) -> MyStatsResponse:
    # guest_service.issue_guest()가 Guest와 GuestStats를 항상 같이 만들기 때문에
    # 여기선 "없을 수도 있음"을 방어하지 않는다.
    stats = db.session.get(GuestStats, guest.id)
    account = find_by_guest(guest.id)
    linked_account = (
        LinkedAccount(provider=account.provider.value, email=account.email)
        if account is not None
        else None
    )
    return MyStatsResponse(
        puzzle_language=guest.puzzle_language,
        current_streak=stats.current_streak,
        max_streak=stats.max_streak,
        solved_count=stats.solved_count,
        linked_account=linked_account,
    )
