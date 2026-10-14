"""계정 삭제 서비스와 `DELETE /me`.

삭제는 되돌릴 수 없는 유일한 기능이라 "뭐가 지워졌나" 를 테이블마다 직접 확인한다
(스펙 §A.7: Attempt, GuestStats, Account, HintUnlock, Subscription, 오늘 리더보드,
Guest). 애플 연결 철회는 tests/test_apple_revocation.py 가 본다.
"""

from datetime import datetime

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
    SubscriptionEnvironment,
    SubscriptionStatus,
    SubscriptionStore,
)
from app.services.account_deletion_service import delete_guest_account
from app.services.guest_service import issue_guest
from app.services.puzzle_metrics import record_leaderboard
from app.utils.redis_safe import safe_redis_call


def _fill_every_table(guest: Guest, puzzle) -> None:
    """이 게스트가 남길 수 있는 모든 행을 한 번씩 만든다."""
    db.session.add(
        Attempt(guest_id=guest.id, puzzle_id=puzzle.id, guess="사과", is_correct=True, attempt_no=1)
    )
    db.session.add(HintUnlock(guest_id=guest.id, puzzle_id=puzzle.id))
    db.session.add(
        Account(
            guest_id=guest.id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-uid-delete",
            email="delete-me@example.com",
        )
    )
    db.session.add(
        Subscription(
            guest_id=guest.id,
            store=SubscriptionStore.APPLE,
            store_key="original-transaction-delete",
            product_id="adfree_monthly",
            environment=SubscriptionEnvironment.PRODUCTION,
            status=SubscriptionStatus.ACTIVE,
        )
    )
    db.session.commit()


def test_deletion_removes_every_row_of_that_guest(app, today_puzzle):
    guest = issue_guest()
    _fill_every_table(guest, today_puzzle)
    guest_id = guest.id

    delete_guest_account(guest)

    assert db.session.get(Guest, guest_id) is None
    assert db.session.get(GuestStats, guest_id) is None
    assert Attempt.query.filter_by(guest_id=guest_id).count() == 0
    assert HintUnlock.query.filter_by(guest_id=guest_id).count() == 0
    assert Account.query.filter_by(guest_id=guest_id).count() == 0
    assert Subscription.query.filter_by(guest_id=guest_id).count() == 0


def test_deletion_is_committed(app, today_puzzle):
    """함수 하나 = 커밋 하나(스펙 §A.17) — 호출자가 커밋하지 않아도 지워져 있다."""
    guest = issue_guest()
    _fill_every_table(guest, today_puzzle)
    guest_id = guest.id

    delete_guest_account(guest)
    db.session.rollback()  # 커밋이 없었다면 여기서 전부 되살아난다

    assert db.session.get(Guest, guest_id) is None
    assert Attempt.query.filter_by(guest_id=guest_id).count() == 0


def test_other_guests_records_are_untouched(app, today_puzzle):
    victim = issue_guest()
    bystander = issue_guest()
    _fill_every_table(victim, today_puzzle)
    db.session.add(
        Attempt(
            guest_id=bystander.id,
            puzzle_id=today_puzzle.id,
            guess="바나나",
            is_correct=False,
            attempt_no=1,
        )
    )
    db.session.commit()
    bystander_id = bystander.id

    delete_guest_account(victim)

    assert db.session.get(Guest, bystander_id) is not None
    assert db.session.get(GuestStats, bystander_id) is not None
    assert Attempt.query.filter_by(guest_id=bystander_id).count() == 1


def _leaderboard_score(language: PuzzleLanguage, guest_id: int):
    key = f"lb:{datetime.now(KST).date().isoformat()}:{language.value}"
    return safe_redis_call("zscore", key, str(guest_id))


def test_todays_leaderboard_entry_is_removed_for_every_language(app, make_today_puzzle):
    """ko·en 은 키가 따로라 언어마다 ZREM 해야 한다(스펙 §A.7 "언어별")."""
    guest = issue_guest()
    now = datetime.now(KST)
    for language in PuzzleLanguage:
        puzzle = make_today_puzzle(language)
        record_leaderboard(puzzle.puzzle_date, language, guest.id, 1, now)
    guest_id = guest.id

    assert _leaderboard_score(PuzzleLanguage.KO, guest_id) is not None
    assert _leaderboard_score(PuzzleLanguage.EN, guest_id) is not None

    delete_guest_account(guest)

    assert _leaderboard_score(PuzzleLanguage.KO, guest_id) is None
    assert _leaderboard_score(PuzzleLanguage.EN, guest_id) is None


def test_other_guests_keep_their_leaderboard_entry(app, today_puzzle):
    victim = issue_guest()
    bystander = issue_guest()
    now = datetime.now(KST)
    record_leaderboard(today_puzzle.puzzle_date, PuzzleLanguage.KO, victim.id, 1, now)
    record_leaderboard(today_puzzle.puzzle_date, PuzzleLanguage.KO, bystander.id, 2, now)
    bystander_id = bystander.id

    delete_guest_account(victim)

    assert _leaderboard_score(PuzzleLanguage.KO, bystander_id) is not None


def test_deletion_survives_a_redis_outage(app, today_puzzle, broken_redis):
    """Redis 가 죽어 있어도 DB 삭제는 끝까지 간다 — 삭제가 캐시 장애로 막히면 안 된다."""
    guest = issue_guest()
    _fill_every_table(guest, today_puzzle)
    guest_id = guest.id

    delete_guest_account(guest)

    assert db.session.get(Guest, guest_id) is None


# --- DELETE /me ------------------------------------------------------------


def test_delete_me_returns_no_content_and_invalidates_the_token(client, today_puzzle):
    guest = issue_guest()
    headers = {"Authorization": f"Bearer {guest.token}"}

    res = client.delete("/api/v1/me", headers=headers)

    assert res.status_code == 204
    assert res.data == b""
    # 옛 토큰으로 오는 모든 요청은 401 이다(스펙 §A.7).
    after = client.get("/api/v1/puzzles/today", headers=headers)
    assert after.status_code == 401
    assert after.get_json()["code"] == "UNAUTHORIZED"


def test_delete_me_requires_a_bearer_token(client):
    res = client.delete("/api/v1/me")

    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"


def test_delete_me_twice_is_unauthorized_the_second_time(client):
    guest = issue_guest()
    headers = {"Authorization": f"Bearer {guest.token}"}

    assert client.delete("/api/v1/me", headers=headers).status_code == 204
    assert client.delete("/api/v1/me", headers=headers).status_code == 401
