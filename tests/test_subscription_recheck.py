"""1시간 TTL 재조회(`/me/stats`)와 Beat 재검증 (티켓 13, 스펙 §A.8).

바꿔 끼우는 건 스토어 래퍼(`app/clients/*.py`)의 조회 함수 하나뿐이다 — TTL
판정, 저장, 실패 카운터, 권한 조립, 엔드포인트 응답까지 전부 실제 코드로
지나간다. 래퍼가 돌려주는 값은 실제 응답 모양 fixture(`tests/fixtures/store/`)다.

시계는 실제 `utcnow()` 를 쓰고, 대신 `last_verified_at`·`expires_at` 을 "정확히
1시간 전" 처럼 상대 시각으로 심는다. 판정표·간격 자체의 경계값 테스트는 순수
함수 쪽(`tests/test_entitlement.py`)에 있다.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from app.clients import app_store, play
from app.errors import ReceiptInvalidError, StoreUnavailableError
from app.extensions import db
from app.models import (
    Guest,
    Subscription,
    SubscriptionEnvironment,
    SubscriptionStatus,
    SubscriptionStore,
)
from app.services import subscription_recheck
from app.services.guest_service import issue_guest
from app.services.subscription_recheck import (
    BEAT_RECHECK_WINDOW,
    FAILURE_ALERT_THRESHOLD,
    recheck_expiring_subscriptions,
)
from app.services.subscription_service import verify_receipt
from app.utils.time import utcnow

FIXTURES = Path(__file__).parent / "fixtures" / "store"

BUNDLE_ID = "com.chosungdaily.app"
APPLE_STORE_KEY = "2000000111111111"
PLAY_STORE_KEY = "purchase-token-1"
STATS_URL = "/api/v1/me/stats"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def store_config(app):
    app.config.update(APP_STORE_BUNDLE_ID=BUNDLE_ID, SUBSCRIPTION_PRODUCT_ID="adfree_monthly")
    return app


@pytest.fixture
def guest(app):
    return issue_guest()


@pytest.fixture
def headers(guest):
    return {"Authorization": f"Bearer {guest.token}"}


@pytest.fixture
def make_subscription(app, guest):
    """구독 행 하나를 직접 심는다 — 영수증 검증 경로를 거치지 않는다.

    재조회 테스트가 보고 싶은 건 "이미 저장된 구독을 언제 다시 물어보나" 라서,
    `last_verified_at` 과 `expires_at` 을 원하는 시각으로 두는 게 핵심이다.
    """

    def _make(
        *,
        store: SubscriptionStore = SubscriptionStore.APPLE,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        expires_in: timedelta = timedelta(days=20),
        verified_ago: timedelta = timedelta(0),
        recheck_failures: int = 0,
    ) -> Subscription:
        # 초 아래를 버린다. MySQL DATETIME 은 소수점 초를 반올림해서 저장하기
        # 때문에, "정확히 1시간 전" 을 마이크로초까지 심으면 저장값이 0.5초
        # 흔들려서 경계 테스트가 그 반올림에 좌우된다.
        now = utcnow().replace(microsecond=0)
        subscription = Subscription(
            guest_id=guest.id,
            store=store,
            store_key=APPLE_STORE_KEY if store is SubscriptionStore.APPLE else PLAY_STORE_KEY,
            product_id="adfree_monthly",
            environment=SubscriptionEnvironment.PRODUCTION,
            status=status,
            expires_at=now + expires_in,
            last_verified_at=now - verified_ago,
            recheck_failures=recheck_failures,
        )
        db.session.add(subscription)
        db.session.commit()
        return subscription

    return _make


def apple_response(fixture: str, store_key: str, environment) -> app_store.AppleSubscription:
    """응답 모양 fixture 하나를 래퍼가 돌려주는 값으로 옮긴다."""
    item = load(fixture)
    transaction = item["signedTransactionInfo"]
    return app_store.AppleSubscription(
        store_key=store_key,
        product_id=transaction["productId"],
        bundle_id=transaction["bundleId"],
        environment=environment,
        raw_status=item["status"],
        transaction=transaction,
        renewal_info=item["signedRenewalInfo"],
    )


@pytest.fixture
def apple_store(monkeypatch, store_config):
    """Apple 상태 조회를 fixture 로 바꿔 끼우고 호출 횟수를 기록한다."""
    calls = []

    def use(fixture: str = "apple_active.json", *, error: Exception | None = None):
        def fetch(store_key, environment):
            calls.append((store_key, environment))
            if error is not None:
                raise error
            return apple_response(fixture, store_key, environment)

        monkeypatch.setattr(app_store, "fetch_subscription_status", fetch)
        return calls

    use.calls = calls
    return use


@pytest.fixture
def play_store(monkeypatch, store_config):
    """Play 상태 조회를 fixture 로 바꿔 끼우고 호출 횟수를 기록한다."""
    calls = []

    def use(fixture: str = "play_active.json", *, error: Exception | None = None, **overrides):
        purchase = load(fixture) | overrides

        def fetch(token):
            calls.append(token)
            if error is not None:
                raise error
            return purchase

        monkeypatch.setattr(play, "fetch_subscription", fetch)
        return calls

    use.calls = calls
    return use


def get_stats(client, headers):
    response = client.get(STATS_URL, headers=headers)
    assert response.status_code == 200
    return response.json


def reload(subscription: Subscription) -> Subscription:
    db.session.expire_all()
    return db.session.get(Subscription, subscription.id)


# --- /me/stats 응답 모양 -------------------------------------------------


def test_stats_without_a_subscription_reports_no_entitlement(client, headers):
    body = get_stats(client, headers)

    assert body["entitlement"] == {
        "active": False,
        "until": None,
        "status": None,
        "source": None,
        "next_check_at": None,
    }


def test_stats_reports_the_entitlement_and_the_next_check_time(
    client, headers, make_subscription, apple_store
):
    apple_store()
    subscription = make_subscription(verified_ago=timedelta(minutes=10))

    body = get_stats(client, headers)

    assert body["entitlement"]["active"] is True
    assert body["entitlement"]["status"] == "active"
    assert body["entitlement"]["source"] == "apple"
    # 앱이 이 시각에 맞춰 타이머를 걸고 다시 부른다 — 항상 마지막 조회 + 1h 다.
    expected = (subscription.last_verified_at + timedelta(hours=1)).isoformat() + "Z"
    assert body["entitlement"]["next_check_at"] == expected
    assert body["current_streak"] == 0  # 기존 필드도 그대로 온다


# --- 1시간 TTL ----------------------------------------------------------


def test_a_subscription_revoked_at_the_store_loses_the_entitlement_after_an_hour(
    client, headers, make_subscription, apple_store
):
    """티켓 13 필수 케이스. 만료 20일 전(= ±24h 밖) 구독의 스토어 상태만
    revoked 로 바꾸고 `last_verified_at` 을 정확히 1시간 전으로 둔다."""
    apple_store("apple_revoked.json")
    subscription = make_subscription(
        expires_in=timedelta(days=20), verified_ago=timedelta(hours=1)
    )

    body = get_stats(client, headers)

    assert len(apple_store.calls) == 1
    assert body["entitlement"]["active"] is False
    assert body["entitlement"]["status"] == "revoked"
    assert reload(subscription).status is SubscriptionStatus.REVOKED


def test_a_subscription_verified_59_minutes_ago_is_not_rechecked(
    client, headers, make_subscription, apple_store
):
    apple_store("apple_revoked.json")
    make_subscription(expires_in=timedelta(days=20), verified_ago=timedelta(minutes=59))

    body = get_stats(client, headers)

    assert apple_store.calls == []
    assert body["entitlement"]["active"] is True  # 저장된 값 그대로


def test_the_hourly_interval_caps_the_store_calls(
    client, headers, make_subscription, apple_store
):
    """상한이 없으면 포그라운드 앱이 `/me/stats` 를 부르는 만큼 스토어를 때린다.
    한 번 재조회한 뒤 1시간 동안은 더 묻지 않는다."""
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(days=20), verified_ago=timedelta(minutes=90))

    get_stats(client, headers)
    get_stats(client, headers)
    get_stats(client, headers)

    assert len(apple_store.calls) == 1


def test_near_the_expiry_the_interval_drops_to_five_minutes(
    client, headers, make_subscription, apple_store
):
    """만료 ±24h 안에서는 5분 상한이다(미정 항목 18 확정)."""
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(hours=1), verified_ago=timedelta(minutes=6))

    get_stats(client, headers)

    assert len(apple_store.calls) == 1


def test_near_the_expiry_a_call_within_five_minutes_is_not_rechecked(
    client, headers, make_subscription, apple_store
):
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(hours=1), verified_ago=timedelta(minutes=4))

    get_stats(client, headers)

    assert apple_store.calls == []


def test_outside_the_expiry_window_six_minutes_is_not_enough(
    client, headers, make_subscription, apple_store
):
    """같은 6분이라도 만료가 멀면 재조회하지 않는다 — 5분 상한은 ±24h 전용이다."""
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(days=20), verified_ago=timedelta(minutes=6))

    get_stats(client, headers)

    assert apple_store.calls == []


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.EXPIRED, SubscriptionStatus.REVOKED, SubscriptionStatus.REPLACED],
)
def test_finished_subscriptions_are_not_rechecked(
    client, headers, make_subscription, apple_store, status
):
    """스토어가 "끝났다" 고 말해준 행은 다시 묻지 않는다. 되살아나면 앱이
    구매 동기화로 영수증을 다시 올린다(스펙 §A.8 (b))."""
    apple_store("apple_active.json")
    make_subscription(status=status, verified_ago=timedelta(days=30))

    body = get_stats(client, headers)

    assert apple_store.calls == []
    assert body["entitlement"]["active"] is False


def test_a_hold_subscription_is_rechecked_so_a_recovered_payment_shows_up(
    client, headers, make_subscription, apple_store
):
    """보류는 권한이 없지만 재조회 대상이다 — 결제가 복구되면 active 로 돌아온다."""
    apple_store("apple_active.json")
    subscription = make_subscription(
        status=SubscriptionStatus.HOLD, verified_ago=timedelta(hours=2)
    )

    body = get_stats(client, headers)

    assert len(apple_store.calls) == 1
    assert body["entitlement"]["active"] is True
    assert reload(subscription).status is SubscriptionStatus.ACTIVE


def test_a_google_subscription_is_rechecked_with_its_purchase_token(
    client, headers, make_subscription, play_store
):
    play_store("play_expired.json")
    make_subscription(store=SubscriptionStore.GOOGLE, verified_ago=timedelta(hours=2))

    body = get_stats(client, headers)

    assert play_store.calls == [PLAY_STORE_KEY]
    assert body["entitlement"]["active"] is False
    assert body["entitlement"]["status"] == "expired"


def test_the_recheck_only_touches_the_calling_guests_subscriptions(
    app, client, headers, make_subscription, apple_store
):
    """`/me/stats` 는 부른 게스트의 구독만 다시 물어본다 — 남의 구독을 함께
    재조회하면 한 사람의 호출이 전체 구독 수만큼 스토어 API 를 때린다."""
    apple_store("apple_active.json")
    other = issue_guest()
    subscription = make_subscription(verified_ago=timedelta(hours=2))
    subscription.guest_id = other.id
    db.session.commit()

    get_stats(client, headers)

    assert apple_store.calls == []


# --- 재조회 실패 ---------------------------------------------------------


@pytest.mark.parametrize("error", [StoreUnavailableError(), ReceiptInvalidError()])
def test_a_failed_recheck_keeps_the_stored_values_and_counts_the_failure(
    client, headers, make_subscription, apple_store, error
):
    """스토어가 답을 못 주면 저장값을 유지한다 — 장애로 돈 낸 구독자의 광고를
    켜지 않는다. 영수증 거절(400)도 같다: 권한을 뺏는 판단은 스토어가 분명히
    말해준 상태로만 한다."""
    apple_store("apple_active.json", error=error)
    subscription = make_subscription(
        expires_in=timedelta(days=20), verified_ago=timedelta(hours=2)
    )
    verified_at = subscription.last_verified_at

    body = get_stats(client, headers)

    assert len(apple_store.calls) == 1
    assert body["entitlement"]["active"] is True
    row = reload(subscription)
    assert row.status is SubscriptionStatus.ACTIVE
    assert row.recheck_failures == 1
    # 실패했으니 "마지막으로 물어본 시각" 을 올리지 않는다 — 다음 호출이 또 시도한다.
    assert row.last_verified_at == verified_at


def test_a_successful_recheck_resets_the_failure_counter(
    client, headers, make_subscription, apple_store
):
    apple_store("apple_active.json")
    subscription = make_subscription(verified_ago=timedelta(hours=2), recheck_failures=2)

    get_stats(client, headers)

    assert reload(subscription).recheck_failures == 0


# --- Beat 매일 재검증 ----------------------------------------------------


def test_the_beat_rechecks_subscriptions_expiring_within_three_days(
    app, make_subscription, apple_store
):
    apple_store("apple_revoked.json")
    subscription = make_subscription(expires_in=BEAT_RECHECK_WINDOW - timedelta(hours=1))

    rechecked = recheck_expiring_subscriptions()

    assert rechecked == 1
    assert len(apple_store.calls) == 1
    assert reload(subscription).status is SubscriptionStatus.REVOKED


def test_the_beat_ignores_subscriptions_that_expire_later(app, make_subscription, apple_store):
    apple_store("apple_revoked.json")
    make_subscription(expires_in=BEAT_RECHECK_WINDOW + timedelta(hours=1))

    assert recheck_expiring_subscriptions() == 0
    assert apple_store.calls == []


def test_the_beat_ignores_the_ttl_and_rechecks_anyway(app, make_subscription, apple_store):
    """Beat 는 만료 임박 구독을 하루 한 번 꼭 본다 — 방금 조회한 행이어도
    돈다(`/me/stats` 를 아예 안 부르는 사용자를 위한 경로다)."""
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(days=1), verified_ago=timedelta(0))

    assert recheck_expiring_subscriptions() == 1


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.EXPIRED, SubscriptionStatus.REVOKED, SubscriptionStatus.REPLACED],
)
def test_the_beat_only_rechecks_live_statuses(app, make_subscription, apple_store, status):
    apple_store("apple_active.json")
    make_subscription(status=status, expires_in=timedelta(days=1))

    assert recheck_expiring_subscriptions() == 0
    assert apple_store.calls == []


def test_the_beat_alerts_the_operator_after_three_consecutive_failures(
    app, monkeypatch, make_subscription, apple_store
):
    alerts = []
    monkeypatch.setattr(
        subscription_recheck,
        "notify_operator",
        lambda kind, message: alerts.append((kind, message)) or True,
    )
    apple_store("apple_active.json", error=StoreUnavailableError())
    subscription = make_subscription(
        expires_in=timedelta(days=1), recheck_failures=FAILURE_ALERT_THRESHOLD - 1
    )

    recheck_expiring_subscriptions()

    assert reload(subscription).recheck_failures == FAILURE_ALERT_THRESHOLD
    assert len(alerts) == 1
    kind, message = alerts[0]
    assert kind == "구독 재조회 실패 누적"
    assert str(subscription.id) in message
    # 스토어 키는 결제 식별자라 알림에 싣지 않는다 — 운영자는 행 ID 로 찾는다.
    assert APPLE_STORE_KEY not in message


def test_the_beat_does_not_alert_before_the_threshold(
    app, monkeypatch, make_subscription, apple_store
):
    alerts = []
    monkeypatch.setattr(
        subscription_recheck, "notify_operator", lambda kind, message: alerts.append(kind)
    )
    apple_store("apple_active.json", error=StoreUnavailableError())
    make_subscription(expires_in=timedelta(days=1), recheck_failures=0)

    recheck_expiring_subscriptions()

    assert alerts == []


def test_the_beat_does_not_alert_when_every_recheck_succeeds(
    app, monkeypatch, make_subscription, apple_store
):
    """실패 카운터가 쌓여 있던 행도 성공하면 0으로 돌아가고 알림이 없다."""
    alerts = []
    monkeypatch.setattr(
        subscription_recheck, "notify_operator", lambda kind, message: alerts.append(kind)
    )
    apple_store("apple_active.json")
    subscription = make_subscription(
        expires_in=timedelta(days=1), recheck_failures=FAILURE_ALERT_THRESHOLD
    )

    recheck_expiring_subscriptions()

    assert reload(subscription).recheck_failures == 0
    assert alerts == []


def test_one_failing_subscription_does_not_stop_the_others(
    monkeypatch, make_subscription, apple_store, play_store
):
    """한 구독 조회가 실패해도 나머지는 계속 돈다 — 하루 한 번뿐인 배치라서
    중간에 멈추면 그날 나머지 구독을 아무도 다시 안 본다."""
    monkeypatch.setattr(subscription_recheck, "notify_operator", lambda kind, message: True)
    apple_store("apple_active.json", error=StoreUnavailableError())
    play_store("play_expired.json")
    apple_row = make_subscription(store=SubscriptionStore.APPLE, expires_in=timedelta(days=1))
    play_row = make_subscription(store=SubscriptionStore.GOOGLE, expires_in=timedelta(days=1))

    assert recheck_expiring_subscriptions() == 2
    assert reload(apple_row).recheck_failures == 1
    assert reload(play_row).status is SubscriptionStatus.EXPIRED


# --- 스펙 §A.8 (b): 영수증 재전송은 TTL 과 무관하게 즉시 반영 ------------


def test_resending_the_receipt_two_days_after_expiry_takes_effect_at_once(
    client, headers, make_subscription, apple_store, monkeypatch
):
    """티켓 13 필수 케이스. 만료 2일 뒤면 24h 유예가 끝나 권한이 없고(±24h
    밖이라 재조회도 TTL 을 따른다), 앱이 구매 동기화로 영수증을 다시 올리면
    그 응답부터 권한이 돌아온다."""
    apple_store("apple_active.json")
    make_subscription(expires_in=timedelta(days=-2), verified_ago=timedelta(minutes=1))

    before = get_stats(client, headers)
    assert before["entitlement"]["active"] is False
    assert apple_store.calls == []  # TTL 안이라 스토어를 부르지도 않는다

    item = load("apple_active.json")
    transaction = item["signedTransactionInfo"]
    monkeypatch.setattr(
        app_store,
        "fetch_subscription",
        lambda _receipt: app_store.AppleSubscription(
            store_key=APPLE_STORE_KEY,
            product_id=transaction["productId"],
            bundle_id=transaction["bundleId"],
            environment=SubscriptionEnvironment.PRODUCTION,
            raw_status=item["status"],
            transaction=transaction,
            renewal_info=item["signedRenewalInfo"],
        ),
    )
    guest = db.session.query(Guest).filter_by(
        token=headers["Authorization"].removeprefix("Bearer ")
    ).one()

    entitlement = verify_receipt(guest, SubscriptionStore.APPLE, "renewed-receipt-jws")

    assert entitlement.active is True
    assert len(db.session.query(Subscription).all()) == 1


# --- 겹친 재조회 (수정 라운드 1, D-13-1) ---------------------------------


def _recheck_in_another_session(app, subscription_id: int) -> SubscriptionStatus:
    """독립 app context(= 독립 DB 세션)로 같은 구독의 재조회를 끝까지 돌린다.

    Flask-SQLAlchemy 의 세션은 app context 에 묶여 있어서, context 를 새로 열면
    실제 두 번째 요청처럼 별도 커넥션·트랜잭션이 된다 — 같은 세션으로 흉내 내면
    identity map 이 행을 공유해서 겹침 자체가 사라진다.
    """
    with app.app_context():
        row = db.session.get(Subscription, subscription_id)
        assert subscription_recheck.recheck(row) is True
        status = row.status
        db.session.remove()
    return status


def test_a_delayed_store_response_does_not_revive_a_confirmed_revocation(
    app, guest, make_subscription, monkeypatch, store_config
):
    """두 재조회가 겹칠 때, 먼저 출발했지만 늦게 도착한 응답으로 이미 확인된
    철회를 덮으면 안 된다 — 스펙 §A.8 "철회가 확인되면 그 응답부터 권한 없음".

    겹치는 조합은 `/me/stats` 두 개, `/me/stats` 와 Beat, Beat 안의 두 행 모두다
    (셋 다 `recheck` 하나를 지난다). A 가 스토어에 묻는 동안 B 가 철회를
    확인·저장했으면 A 의 오래된 active 응답은 버린다. 안 그러면 환불한 구독의
    광고 제거 권한이 되살아나고, A 가 `last_verified_at` 까지 올려서 다음
    TTL(1시간)까지 그 상태로 남는다.
    """
    subscription = make_subscription(
        status=SubscriptionStatus.HOLD,
        expires_in=timedelta(days=2),
        verified_ago=timedelta(hours=2),
    )
    asked = []

    def fetch(store_key, environment):
        if asked:  # B 의 조회 — 철회를 보고 저장한다.
            return apple_response("apple_revoked.json", store_key, environment)
        # A 의 스토어 경계 안 = 아직 응답을 못 받은 구간. 여기서 B 가 끝난다.
        asked.append(True)
        assert _recheck_in_another_session(app, subscription.id) is SubscriptionStatus.REVOKED
        return apple_response("apple_active.json", store_key, environment)

    monkeypatch.setattr(app_store, "fetch_subscription_status", fetch)

    entitlement = subscription_recheck.entitlement_for(guest)

    assert entitlement.active is False
    assert entitlement.status is SubscriptionStatus.REVOKED
    assert reload(subscription).status is SubscriptionStatus.REVOKED


def test_a_delayed_failure_does_not_count_against_a_fresh_success(
    app, guest, make_subscription, monkeypatch, store_config
):
    """실패 쪽도 같다. A 의 조회가 실패로 돌아왔을 때 B 가 그 사이에 성공해
    카운터를 0으로 돌려놨으면, A 의 실패는 그 행에 적지 않는다 — 이미 지나간
    조회의 실패로 운영자 알림 임계를 채우게 된다."""
    subscription = make_subscription(
        status=SubscriptionStatus.HOLD,
        expires_in=timedelta(days=2),
        verified_ago=timedelta(hours=2),
        recheck_failures=FAILURE_ALERT_THRESHOLD - 1,
    )
    asked = []

    def fetch(store_key, environment):
        if asked:  # B 의 조회 — 성공해서 카운터를 0 으로 돌린다.
            return apple_response("apple_revoked.json", store_key, environment)
        asked.append(True)
        assert _recheck_in_another_session(app, subscription.id) is SubscriptionStatus.REVOKED
        raise StoreUnavailableError

    monkeypatch.setattr(app_store, "fetch_subscription_status", fetch)

    subscription_recheck.entitlement_for(guest)

    row = reload(subscription)
    assert row.recheck_failures == 0
    assert row.status is SubscriptionStatus.REVOKED


# --- 겹친 재조회 (수정 라운드 2, D-13-3) ---------------------------------


def test_a_confirmed_revocation_is_not_discarded_by_an_earlier_active_write(
    app, guest, make_subscription, monkeypatch, store_config
):
    """반대 순서. A 가 스토어에서 **철회를 실제로 받아 왔으면**, 그 사이 B 가
    active 를 먼저 커밋했더라도 A 의 응답부터 권한이 없어야 한다 — 스펙 §A.8
    "철회가 확인되면 그 응답부터 권한 없음".

    겹침 때문에 저장값이 바뀌었다는 사실은 "우리 응답이 오래됐다" 의 증거가
    못 된다. 그 사실로 버릴 수 있는 건 **권한을 되살리는** 응답뿐이고(D-13-1),
    성공으로 받은 철회를 버리면 1시간 TTL 동안 환불된 구독의 광고 제거 권한이
    유지된다.
    """
    subscription = make_subscription(
        status=SubscriptionStatus.ACTIVE,
        expires_in=timedelta(days=20),
        verified_ago=timedelta(hours=2),
    )
    asked = []

    def fetch(store_key, environment):
        if asked:  # B 의 조회 — active 를 먼저 저장한다.
            return apple_response("apple_active.json", store_key, environment)
        # A 의 스토어 경계 안. 여기서 B 가 끝나고, 그 뒤 A 가 철회를 받는다.
        asked.append(True)
        assert _recheck_in_another_session(app, subscription.id) is SubscriptionStatus.ACTIVE
        return apple_response("apple_revoked.json", store_key, environment)

    monkeypatch.setattr(app_store, "fetch_subscription_status", fetch)

    entitlement = subscription_recheck.entitlement_for(guest)

    assert entitlement.active is False
    assert entitlement.status is SubscriptionStatus.REVOKED
    assert reload(subscription).status is SubscriptionStatus.REVOKED
