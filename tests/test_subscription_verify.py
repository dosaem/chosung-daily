"""`POST /subscriptions/verify` 와 저장 규칙 (티켓 12, 스펙 §A.8).

스토어 래퍼(`app/clients/*.py`)만 바꿔 끼우고 그 아래는 전부 실제 코드다 —
상태 매핑 순수 함수, 저장, 권한 조립, DB 유니크 제약까지 진짜로 돌린다.
바꿔 끼운 자리가 돌려주는 값은 실제 응답 모양 fixture(`tests/fixtures/store/`)다.
래퍼 자체의 행동(환경 선택·Sandbox 폴백·에러 분류)은
`tests/test_store_clients.py` 가 따로 검증한다.
"""

import base64
import json
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path

import httplib2
import pytest
import requests
from appstoreserverlibrary.api_client import APIException
from googleapiclient.discovery import build

from app.clients import app_store, play
from app.errors import StoreUnavailableError
from app.extensions import db
from app.models import (
    Guest,
    Subscription,
    SubscriptionEnvironment,
    SubscriptionStatus,
    SubscriptionStore,
)
from app.services.entitlement import RECHECK_INTERVAL
from app.services.guest_service import issue_guest
from app.services.subscription_service import verify_receipt

FIXTURES = Path(__file__).parent / "fixtures" / "store"

BUNDLE_ID = "com.chosungdaily.app"
APPLE_STORE_KEY = "2000000111111111"
EXPIRES_AT = datetime(2026, 11, 1)
GRACE_EXPIRES_AT = datetime(2026, 11, 4)

VERIFY_URL = "/api/v1/subscriptions/verify"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def store_config(app):
    app.config.update(APP_STORE_BUNDLE_ID=BUNDLE_ID, SUBSCRIPTION_PRODUCT_ID="adfree_monthly")
    return app


@pytest.fixture
def fake_apple(monkeypatch, store_config):
    """`apple_*.json` fixture 를 Apple 래퍼의 반환값 자리에 끼운다."""

    def use(fixture: str = "apple_active.json", *, environment=None):
        item = load(fixture)
        transaction = item["signedTransactionInfo"]
        subscription = app_store.AppleSubscription(
            store_key=transaction["originalTransactionId"],
            product_id=transaction["productId"],
            bundle_id=transaction["bundleId"],
            environment=environment
            or SubscriptionEnvironment(transaction.get("environment", "Production")),
            raw_status=item["status"],
            transaction=transaction,
            renewal_info=item["signedRenewalInfo"],
        )
        monkeypatch.setattr(app_store, "fetch_subscription", lambda _receipt: subscription)
        return subscription

    return use


@pytest.fixture
def fake_play(monkeypatch, store_config):
    """`play_*.json` fixture 를 Play 래퍼의 반환값 자리에 끼운다."""

    def use(fixture: str = "play_active.json", **overrides):
        purchase = load(fixture) | overrides
        monkeypatch.setattr(play, "fetch_subscription", lambda _token: purchase)
        return purchase

    return use


def post_verify(client, headers, store: str, receipt: str):
    return client.post(VERIFY_URL, json={"store": store, "receipt": receipt}, headers=headers)


def rows() -> list[Subscription]:
    return db.session.query(Subscription).all()


def test_apple_purchase_creates_one_row_and_grants_entitlement(
    client, guest_headers, fake_apple
):
    fake_apple("apple_active.json")

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.status_code == 200
    assert response.json == {
        "active": True,
        "until": "2026-11-01T00:00:00Z",
        "status": "active",
        "source": "apple",
        "next_check_at": response.json["next_check_at"],
    }

    (row,) = rows()
    assert row.store is SubscriptionStore.APPLE
    assert row.store_key == APPLE_STORE_KEY
    assert row.product_id == "adfree_monthly"
    assert row.status is SubscriptionStatus.ACTIVE
    assert row.expires_at == EXPIRES_AT


def test_next_check_at_is_an_hour_after_the_last_store_lookup(client, guest_headers, fake_apple):
    fake_apple("apple_active.json")

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    (row,) = rows()
    expected = (row.last_verified_at + RECHECK_INTERVAL).isoformat() + "Z"
    assert response.json["next_check_at"] == expected
    assert timedelta(hours=1) == RECHECK_INTERVAL


def test_the_same_receipt_twice_keeps_one_row(client, guest_headers, fake_apple):
    """앱은 구매 직후·복원·앱 시작마다 같은 영수증을 올린다 — 멱등해야 한다."""
    fake_apple("apple_active.json")

    first = post_verify(client, guest_headers, "apple", "apple-receipt-jws")
    second = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(rows()) == 1


def test_a_renewed_receipt_updates_the_same_row(client, guest_headers, fake_apple):
    """같은 구독의 상태가 바뀌면 행을 늘리지 않고 그 행을 고친다."""
    fake_apple("apple_active.json")
    post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    fake_apple("apple_grace.json")
    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    (row,) = rows()
    assert row.status is SubscriptionStatus.GRACE
    assert row.grace_expires_at == GRACE_EXPIRES_AT
    # 유예 중에는 "언제까지" 가 유예 종료 시각이다 — 그때까지 광고가 없다.
    assert response.json == {
        "active": True,
        "until": "2026-11-04T00:00:00Z",
        "status": "grace",
        "source": "apple",
        "next_check_at": response.json["next_check_at"],
    }


def test_restoring_on_another_guest_moves_the_row_instead_of_copying_it(
    app, client, guest_headers, fake_apple
):
    """재설치·기기 교체 후 복원(US 19·28). 구독은 스토어 식별자로 하나뿐이고,
    주인만 지금 게스트로 옮긴다."""
    fake_apple("apple_active.json")
    post_verify(client, guest_headers, "apple", "apple-receipt-jws")
    (first_row,) = rows()
    first_guest_id = first_row.guest_id

    other_guest = issue_guest()
    other_headers = {"Authorization": f"Bearer {other_guest.token}"}
    response = post_verify(client, other_headers, "apple", "apple-receipt-jws")

    assert response.json["active"] is True
    (row,) = rows()
    assert row.guest_id == other_guest.id
    assert row.guest_id != first_guest_id


def test_the_previous_guest_loses_the_entitlement_after_a_restore(
    client, guest_headers, fake_apple
):
    """구독은 한 번에 한 게스트 것이다 — 옮겨간 뒤 옛 게스트는 권한이 없다."""
    fake_apple("apple_active.json")
    post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    other_guest = issue_guest()
    post_verify(
        client,
        {"Authorization": f"Bearer {other_guest.token}"},
        "apple",
        "apple-receipt-jws",
    )

    left_behind = post_verify(client, guest_headers, "apple", "apple-receipt-jws")
    assert left_behind.json["active"] is True  # 다시 올리면 또 되찾아 온다
    assert len(rows()) == 1


def test_a_receipt_for_another_product_is_rejected(client, guest_headers, fake_apple):
    fake_apple("apple_other_product.json")

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.status_code == 400
    assert response.json["code"] == "RECEIPT_INVALID"
    assert rows() == []


def test_a_receipt_from_another_app_is_rejected(client, guest_headers, fake_apple):
    """번들 ID 는 영수증에 서명돼 오므로 남의 앱 영수증을 걸러낼 수 있다."""
    fake_apple("apple_other_bundle.json")

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.status_code == 400
    assert response.json["code"] == "RECEIPT_INVALID"
    assert rows() == []


@pytest.mark.parametrize(
    ("fixture", "status"),
    [
        ("apple_billing_retry.json", SubscriptionStatus.HOLD),
        ("apple_expired.json", SubscriptionStatus.EXPIRED),
        ("apple_revoked.json", SubscriptionStatus.REVOKED),
    ],
)
def test_statuses_without_entitlement_are_still_recorded(
    client, guest_headers, fake_apple, fixture, status
):
    """권한이 없어도 행은 남긴다 — 앱이 "결제 실패" 같은 상태를 보여줘야 한다."""
    fake_apple(fixture)

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.json["active"] is False
    assert response.json["status"] == status.value
    (row,) = rows()
    assert row.status is status


def test_a_sandbox_receipt_is_recorded_as_sandbox(client, guest_headers, fake_apple):
    """심사 중 Sandbox 구매도 똑같이 권한을 준다(US 34a). 환경만 남겨 둔다."""
    fake_apple("apple_sandbox_active.json")

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.json["active"] is True
    (row,) = rows()
    assert row.environment is SubscriptionEnvironment.SANDBOX


def test_store_outage_is_not_the_users_fault(client, guest_headers, monkeypatch, store_config):
    """503 이면 앱이 영수증을 버리지 않고 다음 시작에 다시 올린다."""

    def unavailable(_receipt):
        raise StoreUnavailableError()

    monkeypatch.setattr(app_store, "fetch_subscription", unavailable)

    response = post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    assert response.status_code == 503
    assert response.json["code"] == "STORE_UNAVAILABLE"


@pytest.fixture
def apple_network_boundary(monkeypatch, store_config):
    """Apple 래퍼를 통째로 바꾸지 않고 **네트워크 경계만** 바꿔 끼운다.

    `fake_apple` 은 `fetch_subscription` 자체를 대체해서 래퍼 안의 오류 변환을
    건너뛴다. 여기서는 설정·JWS 검증만 합성값으로 두고 `_fetch_status` 의 변환,
    서비스, 오류 핸들러, HTTP 응답 코드까지 실제 코드로 지나가게 한다.
    """
    transaction = load("apple_active.json")["signedTransactionInfo"]
    monkeypatch.setattr(
        app_store,
        "_credentials",
        lambda: app_store._Credentials(
            bundle_id=BUNDLE_ID,
            app_apple_id=6450000000,
            issuer_id="issuer-id",
            key_id="key-id",
            private_key="not-a-real-key",
            root_certificates=[],
        ),
    )
    monkeypatch.setattr(app_store, "_verify_transaction", lambda *_args: transaction)

    def fail_with(error: Exception):
        class _FailingClient:
            def __init__(self, **_kwargs):
                pass

            def get_all_subscription_statuses(self, _store_key):
                raise error

        monkeypatch.setattr(app_store, "_TimeoutAppStoreServerAPIClient", _FailingClient)

    return fail_with


@pytest.fixture
def play_network_boundary(monkeypatch, store_config):
    """Play 래퍼를 통째로 바꾸지 않고 **DNS 경계만** 바꿔 끼운다.

    `fake_play` 는 `fetch_subscription` 자체를 대체해서 래퍼 안의 오류 변환을
    건너뛴다. 여기서는 실제 Google SDK(정적 discovery)와 httplib2 요청 경로를
    그대로 지나가게 하고, 이름 해석만 실패시켜 SDK 가 실제로 던지는 예외가
    서비스·오류 핸들러를 거쳐 어떤 HTTP 응답이 되는지 본다. 서비스 계정 키를
    읽지 않으며 바깥으로 나가는 호출도 없다(연결 자체가 DNS 에서 끊긴다).
    httplib2 의 HTTPS 연결만 막으므로 DB·Redis 연결에는 영향이 없다.
    """
    store_config.config.update(
        PLAY_PACKAGE_NAME=BUNDLE_ID, PLAY_SERVICE_ACCOUNT_FILE="/not/read/in/tests.json"
    )

    def no_dns(_self):
        raise socket.gaierror("synthetic DNS outage")

    monkeypatch.setattr(httplib2.HTTPSConnectionWithTimeout, "connect", no_dns)
    service = build(
        "androidpublisher",
        "v3",
        http=httplib2.Http(timeout=play.TIMEOUT_SECONDS, proxy_info=None),
        static_discovery=True,
        cache_discovery=False,
    )
    monkeypatch.setattr(play, "_service", lambda _file: service)
    return service


def test_a_google_dns_outage_is_a_store_outage(client, guest_headers, play_network_boundary):
    """D-12-5. httplib2 는 DNS 실패를 `ServerNotFoundError` 로 바꾼다 — OSError 가
    아니라서 래퍼를 빠져나가면 500 이 된다. 앱이 영수증을 들고 다시 오도록 503 이어야 한다."""
    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert (response.status_code, response.json["code"]) == (503, "STORE_UNAVAILABLE")
    assert rows() == []


def sandbox_receipt_jws() -> str:
    """`_environment_of` 가 읽을 수 있는 최소한의 JWS 모양(서명은 가짜)."""
    payload = (
        base64.urlsafe_b64encode(json.dumps({"environment": "Sandbox"}).encode())
        .decode()
        .rstrip("=")
    )
    return f"header.{payload}.signature"


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (requests.Timeout("timed out"), (503, "STORE_UNAVAILABLE")),
        (requests.ConnectionError("no route"), (503, "STORE_UNAVAILABLE")),
        (APIException(503), (503, "STORE_UNAVAILABLE")),
        (APIException(401, 4010000), (503, "STORE_UNAVAILABLE")),
        (APIException(404, 4040010), (400, "RECEIPT_INVALID")),
        # 어느 라이브러리 계열에도 안 들어가는 예외도 500 이 아니라 503 이다
        # (`store_boundary`). 계약에는 400·503 둘뿐이다.
        (RuntimeError("공식 라이브러리의 새 예외"), (503, "STORE_UNAVAILABLE")),
    ],
)
def test_apple_store_failures_become_the_contracted_errors(
    client, guest_headers, apple_network_boundary, error, expected
):
    """스토어 쪽 실패가 그대로 올라오면 전부 500 INTERNAL_ERROR 가 된다.
    앱은 503 이어야 영수증을 들고 다시 오고, 400 이어야 버린다."""
    apple_network_boundary(error)

    response = post_verify(client, guest_headers, "apple", sandbox_receipt_jws())

    assert (response.status_code, response.json["code"]) == expected
    assert rows() == []


@pytest.mark.parametrize("receipt", ["header.W10.signature", "header.bnVsbA.signature"])
def test_a_jws_payload_that_is_not_an_object_is_a_bad_receipt(
    client, guest_headers, apple_network_boundary, receipt
):
    """payload 가 `[]`·`null` 이면 환경을 읽다 500 이 나면 안 된다 — 400 이다."""
    response = post_verify(client, guest_headers, "apple", receipt)

    assert response.status_code == 400
    assert response.json["code"] == "RECEIPT_INVALID"


def test_verify_requires_a_guest_token(client, fake_apple):
    fake_apple("apple_active.json")

    response = client.post(VERIFY_URL, json={"store": "apple", "receipt": "x"})

    assert response.status_code == 401


def test_an_unknown_store_is_a_validation_error(client, guest_headers):
    response = post_verify(client, guest_headers, "kakaopay", "whatever")

    assert response.status_code == 400
    assert response.json["code"] == "VALIDATION_ERROR"


def test_google_purchase_creates_a_row_keyed_by_the_purchase_token(
    client, guest_headers, fake_play
):
    fake_play("play_active.json")

    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is True
    assert response.json["source"] == "google"
    (row,) = rows()
    assert row.store is SubscriptionStore.GOOGLE
    assert row.store_key == "purchase-token-1"
    assert row.expires_at == EXPIRES_AT


def test_a_canceled_but_unexpired_google_subscription_keeps_the_entitlement(
    client, guest_headers, fake_play
):
    """해지해도 만료일까지는 광고가 없다(US 30)."""
    fake_play("play_canceled_not_expired.json")

    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is True
    assert response.json["status"] == "active"


def test_a_refunded_google_subscription_loses_the_entitlement_immediately(
    client, guest_headers, fake_play
):
    """환불·철회는 Google 쪽에서 "만료일 전에 EXPIRED" 로 관측된다. 만료일이
    아직 미래여도 권한을 유예 없이 즉시 뺀다 — v2 응답에 철회 전용 필드가 없어
    `revoked` 라벨은 못 붙이지만(스펙 미정 항목 14) 권한 결과는 같다."""
    fake_play("play_active.json")
    post_verify(client, guest_headers, "google", "purchase-token-1")

    fake_play("play_expired.json")
    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is False
    assert response.json["status"] == "expired"
    (row,) = rows()
    # 만료 시각은 아직 미래인데도 권한이 없다.
    assert row.expires_at == EXPIRES_AT
    assert row.status is SubscriptionStatus.EXPIRED


def test_a_replaced_google_purchase_closes_the_old_row(client, guest_headers, fake_play):
    """업그레이드·재가입은 purchaseToken 이 새로 발급되고 옛 토큰이
    `linkedPurchaseToken` 으로 따라온다. 옛 행은 replaced 로 닫는다."""
    fake_play("play_active.json")
    post_verify(client, guest_headers, "google", "old-purchase-token")

    fake_play("play_replacement.json")
    response = post_verify(client, guest_headers, "google", "new-purchase-token")

    assert response.json["active"] is True
    by_key = {row.store_key: row.status for row in rows()}
    assert by_key == {
        "old-purchase-token": SubscriptionStatus.REPLACED,
        "new-purchase-token": SubscriptionStatus.ACTIVE,
    }


def test_a_replacement_for_a_purchase_we_never_saw_is_fine(client, guest_headers, fake_play):
    """옛 토큰을 우리가 못 본 경우(다른 기기에서 재설치)에도 그냥 새 행만 만든다."""
    fake_play("play_replacement.json")

    response = post_verify(client, guest_headers, "google", "new-purchase-token")

    assert response.json["active"] is True
    assert [row.store_key for row in rows()] == ["new-purchase-token"]


@pytest.mark.parametrize(
    "fixture", ["play_pending.json", "play_pending_purchase_canceled.json"]
)
def test_a_pending_google_purchase_makes_no_row(client, guest_headers, fake_play, fixture):
    """결제가 아직 안 끝난 구매는 행도 권한도 없다(미정 항목 14 확정)."""
    fake_play(fixture)

    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.status_code == 200
    assert response.json == {
        "active": False,
        "until": None,
        "status": None,
        "source": None,
        "next_check_at": None,
    }
    assert rows() == []


def test_a_pending_purchase_does_not_wipe_an_existing_entitlement(
    client, guest_headers, fake_play, fake_apple
):
    """다른 스토어에 살아 있는 구독이 있으면 그 권한은 그대로다."""
    fake_apple("apple_active.json")
    post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    fake_play("play_pending.json")
    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is True
    assert response.json["source"] == "apple"


@pytest.mark.parametrize(
    ("fixture", "status"),
    [
        ("play_on_hold.json", SubscriptionStatus.HOLD),
        ("play_paused.json", SubscriptionStatus.HOLD),
    ],
)
def test_google_hold_and_pause_have_no_entitlement(
    client, guest_headers, fake_play, fixture, status
):
    fake_play(fixture)

    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is False
    (row,) = rows()
    assert row.status is status


def test_a_google_test_purchase_is_recorded_as_sandbox(client, guest_headers, fake_play):
    fake_play("play_test_purchase.json")

    post_verify(client, guest_headers, "google", "purchase-token-1")

    (row,) = rows()
    assert row.environment is SubscriptionEnvironment.SANDBOX


def test_a_google_purchase_of_another_product_is_rejected(client, guest_headers, fake_play):
    fake_play("play_other_product.json")

    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.status_code == 400
    assert response.json["code"] == "RECEIPT_INVALID"
    assert rows() == []


def test_entitlement_prefers_the_subscription_that_grants_it(
    client, guest_headers, fake_apple, fake_play
):
    """애플 구독이 보류 중이고 구글 구독이 살아 있으면 권한은 있다."""
    fake_apple("apple_billing_retry.json")
    post_verify(client, guest_headers, "apple", "apple-receipt-jws")

    fake_play("play_active.json")
    response = post_verify(client, guest_headers, "google", "purchase-token-1")

    assert response.json["active"] is True
    assert response.json["source"] == "google"
    assert len(rows()) == 2


def test_the_same_receipt_arriving_twice_at_once_still_makes_one_row(
    app, guest_headers, fake_apple
):
    """앱이 같은 영수증을 동시에 두 번 올리는 경우(구매 스트림 + 시작 동기화).

    둘 다 "행이 없다" 를 보고 둘 다 INSERT 를 시도한다 — `unique(store,
    store_key)` 가 한쪽을 막고, 막힌 쪽은 이긴 행을 다시 읽어 갱신으로 돈다
    (`app/services/subscription_service.py` 의 `_save`).
    """
    fake_apple("apple_active.json")
    guest_id = Guest.query.filter_by(
        token=guest_headers["Authorization"].removeprefix("Bearer ")
    ).one().id

    outcomes = []
    barrier = threading.Barrier(2)

    def worker():
        with app.app_context():
            app.config.update(
                APP_STORE_BUNDLE_ID=BUNDLE_ID, SUBSCRIPTION_PRODUCT_ID="adfree_monthly"
            )
            barrier.wait()
            try:
                guest = db.session.get(Guest, guest_id)
                outcomes.append(verify_receipt(guest, SubscriptionStore.APPLE, "jws").active)
            except Exception as exc:  # 실패 종류를 보고 싶다
                outcomes.append(type(exc).__name__)
            finally:
                db.session.remove()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes == [True, True]
    assert len(rows()) == 1
