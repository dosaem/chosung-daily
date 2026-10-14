from datetime import datetime, timedelta

from app.config import KST
from app.extensions import db
from app.models import Guest, GuestStats, PuzzleLanguage
from app.repositories.account_repository import find_by_guest
from app.repositories.attempt_repository import DaySummary, summarize_by_date_and_language
from app.schemas.history import HistoryDay
from app.schemas.stats import LinkedAccount, MyStatsResponse
from app.services.game_rules import day_result
from app.services.subscription_recheck import entitlement_for

# 기록 화면이 한 번에 요청할 수 있는 날짜 수의 상한(스펙 §A' `/me/history`).
# 한 달치까지는 미니 그리드로 볼 만하고, 그 이상은 쿼리 한 번에 담지 않는다.
MAX_HISTORY_DAYS = 31
DEFAULT_HISTORY_DAYS = 7


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
        # 구독이 있고 TTL(1시간, 만료 ±24h 는 5분)이 지났으면 여기서 스토어를
        # 다시 물어본다 — 앱이 이 엔드포인트만 보고 광고를 켜고 끄기 때문에,
        # 철회를 가장 빨리 반영할 수 있는 자리다(스펙 §A.8).
        entitlement=entitlement_for(guest),
    )


def get_my_history(guest: Guest, days: int) -> list[HistoryDay]:
    """오늘(KST)까지 최근 `days` 일의 퍼즐 언어별 결과.

    날짜는 KST 기준이다 — 퍼즐 자체가 KST 자정에 갈리기 때문에(`puzzle_service`)
    UTC 로 자르면 한국 사용자의 저녁 플레이가 전날 칸에 들어간다.

    오래된 날짜부터(오늘이 마지막) 돌려준다. 기록 화면의 미니 그리드가 왼쪽에서
    오른쪽으로 한 주를 읽는 순서라, 클라이언트가 뒤집지 않아도 그대로 그린다.
    시도가 없는 날·언어는 `none` 으로 채워서, 퍼즐이 없던 날도 빈칸이 생기지 않는다.
    """
    today = datetime.now(KST).date()
    start_date = today - timedelta(days=days - 1)
    summaries = summarize_by_date_and_language(guest.id, start_date, today)
    not_played = DaySummary(attempts=0, solved=False)

    history = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        results = {}
        for language in PuzzleLanguage:
            summary = summaries.get((day, language), not_played)
            results[language] = day_result(summary.attempts, summary.solved)
        history.append(HistoryDay(date=day, results=results))
    return history
