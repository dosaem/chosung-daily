from datetime import datetime
from typing import NamedTuple

from app.config import KST
from app.extensions import db
from app.models import (
    Account,
    Attempt,
    Guest,
    GuestStats,
    HintUnlock,
    OAuthProvider,
    PuzzleLanguage,
    Subscription,
)
from app.repositories.account_repository import find_by_guest
from app.services.apple_revocation_service import (
    complete_scheduled_revocation,
    schedule_revocation,
)
from app.services.puzzle_metrics import remove_from_leaderboard

# 지우는 테이블. 자식(게스트를 참조하는 행)이 먼저, 마지막이 Guest 다 — 순서를
# 바꾸면 외래 키 때문에 삭제 자체가 막힌다.
_GUEST_OWNED_MODELS = (Attempt, HintUnlock, Subscription, Account, GuestStats)


class _AppleConnection(NamedTuple):
    """애플 철회에 필요한 짝. 계정 행을 지우기 전에 떠 둔다."""

    refresh_token_enc: str
    client_id: str


def delete_guest_account(guest: Guest) -> None:
    """게스트의 계정과 모든 기록을 지운다(스펙 §A.7, US 21). 함수 하나 = 커밋 하나.

    `DELETE /me`(앱)와 웹 `POST /account/delete` 가 같은 이 함수를 쓴다 — 삭제
    범위가 들어온 문으로 갈리면 한쪽만 고쳐진 삭제가 생긴다.

    순서가 설계다. **DB 삭제를 한 트랜잭션으로 커밋한 뒤** 바깥 정리(오늘 리더보드
    `ZREM`, 애플 연결 철회)를 한다. 바깥 둘은 트랜잭션에 들어올 수 없고(Redis·애플)
    되돌릴 수도 없어서, 커밋 전에 하면 "커밋이 실패했는데 순위만 사라진" 상태가
    된다. 반대로 커밋 뒤에 하면 Redis·애플 장애는 플레이어의 삭제를 막지 못한다 —
    "지워졌다" 는 약속을 DB 가 지키고, 나머지는 복구 경로가 따로 있는 정리 작업이다
    (리더보드는 그날 키뿐, 철회는 `AppleRevocationRetry` 가 다시 시도한다).

    그래서 애플 철회 **의무** 는 삭제와 같은 커밋에 들어간다(`schedule_revocation`).
    애플 호출이 실패한 뒤에 그 행을 저장하면, 커밋과 저장 사이에서 DB·프로세스가
    죽은 요청이 계정만 지우고 철회 자격증명을 영구히 버린다 — 게스트 행이 없어서
    아무도 다시 만들어낼 수 없는 유실이다. 커밋 뒤의 호출이 성공하면 그 행을 지운다
    (즉 커밋 둘: 삭제 하나, 의무 해제 하나).
    """
    apple_connection = _apple_connection(guest)
    guest_id = guest.id

    revocation = (
        schedule_revocation(apple_connection.refresh_token_enc, apple_connection.client_id)
        if apple_connection is not None
        else None
    )
    for model in _GUEST_OWNED_MODELS:
        db.session.query(model).filter_by(guest_id=guest_id).delete(synchronize_session=False)
    db.session.query(Guest).filter_by(id=guest_id).delete(synchronize_session=False)
    db.session.commit()

    _remove_from_todays_leaderboards(guest_id)
    if revocation is not None:
        complete_scheduled_revocation(revocation)


def _apple_connection(guest: Guest) -> _AppleConnection | None:
    """애플로 연결된 계정이면 철회에 쓸 (암호문 토큰, 발급 client) 을 돌려준다.

    둘 중 하나라도 없으면 None 이다. 특히 `provider_client_id` 가 없으면 어느
    자격증명으로 철회할지 알 수 없는데, 아무 client 로 찍어 보내면 애플이
    `invalid_client` 로 거절할 뿐이라 재시도 행을 만들 이유도 없다(티켓 10·11
    이후의 애플 연결은 항상 둘을 같이 저장한다).
    """
    account = find_by_guest(guest.id)
    if account is None or account.provider is not OAuthProvider.APPLE:
        return None
    if not account.provider_refresh_token or not account.provider_client_id:
        return None
    return _AppleConnection(account.provider_refresh_token, account.provider_client_id)


def _remove_from_todays_leaderboards(guest_id: int) -> None:
    """오늘(KST) 리더보드에서 이 게스트를 뺀다 — ko·en 키가 따로라 언어마다 한 번.

    어제 이전 키는 어떤 엔드포인트도 읽지 않아서(랭킹은 오늘만 보여준다) 스펙이
    오늘만 지우라고 정했다.
    """
    today = datetime.now(KST).date()
    for language in PuzzleLanguage:
        remove_from_leaderboard(today, language, guest_id)
