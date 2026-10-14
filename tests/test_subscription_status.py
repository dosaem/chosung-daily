"""스토어 응답 → `SubscriptionStatus` 매핑 순수 함수 (스펙 §A.8, 티켓 12).

여기서 검증하는 건 "스토어가 말하는 상태를 우리 enum 으로 어떻게 읽느냐" 뿐이다.
권한(광고를 끄느냐)은 이 상태를 보고 판정하는 별도 순수 함수의 일이고
판정표·TTL 은 티켓 13 에서 완성된다. 그래서 여기엔 "지금"이 안 나온다 —
fixture 의 만료일은 고정값이고, 함수는 시계를 읽지 않는다.

입력이 라이브러리 객체가 아니라 평범한 dict 인 이유: fixture 를 스토어 응답
그대로(`tests/fixtures/store/README.md`) 둘 수 있고, 매핑 규칙이 SDK 버전에
묶이지 않는다. 래퍼(`app/clients/*.py`)가 디코딩 결과를 dict 로 넘긴다.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.models import SubscriptionStatus
from app.services.subscription_status import (
    apple_subscription_status,
    google_subscription_status,
)

FIXTURES = Path(__file__).parent / "fixtures" / "store"

EXPIRES_AT = datetime(2026, 11, 1)  # naive UTC — DB 저장 포맷(app/utils/time.py)
GRACE_EXPIRES_AT = datetime(2026, 11, 4)


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def apple_status_of(name: str):
    item = load(name)
    return apple_subscription_status(
        item["status"], item["signedTransactionInfo"], item["signedRenewalInfo"]
    )


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("apple_active.json", SubscriptionStatus.ACTIVE),
        ("apple_expired.json", SubscriptionStatus.EXPIRED),
        ("apple_billing_retry.json", SubscriptionStatus.HOLD),
        ("apple_grace.json", SubscriptionStatus.GRACE),
        ("apple_revoked.json", SubscriptionStatus.REVOKED),
    ],
)
def test_apple_status_codes_map_to_our_statuses(fixture, expected):
    assert apple_status_of(fixture).status is expected


def test_apple_expiry_comes_from_the_transaction():
    assert apple_status_of("apple_active.json").expires_at == EXPIRES_AT


def test_apple_grace_carries_the_store_grace_deadline():
    """status 4(Billing Grace Period)는 유예 종료 시각이 따로 온다."""
    normalized = apple_status_of("apple_grace.json")

    assert normalized.status is SubscriptionStatus.GRACE
    assert normalized.grace_expires_at == GRACE_EXPIRES_AT


def test_apple_non_grace_statuses_have_no_grace_deadline():
    assert apple_status_of("apple_active.json").grace_expires_at is None


def test_apple_unknown_status_code_is_rejected():
    """스토어가 모르는 상태를 보내면 조용히 active 로 떨어지면 안 된다."""
    with pytest.raises(ValueError, match="99"):
        apple_subscription_status(99, load("apple_active.json")["signedTransactionInfo"], {})


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("play_active.json", SubscriptionStatus.ACTIVE),
        # 해지했지만 아직 만료 전 — 낸 돈만큼은 쓴다(US 30).
        ("play_canceled_not_expired.json", SubscriptionStatus.ACTIVE),
        ("play_in_grace_period.json", SubscriptionStatus.GRACE),
        ("play_on_hold.json", SubscriptionStatus.HOLD),
        # 일시정지는 "지금은 권한 없음, 돌아올 수 있음" 이라 hold 와 같은 칸이다(미정 14).
        ("play_paused.json", SubscriptionStatus.HOLD),
        ("play_expired.json", SubscriptionStatus.EXPIRED),
    ],
)
def test_google_states_map_to_our_statuses(fixture, expected):
    assert google_subscription_status(load(fixture)).status is expected


def test_google_expiry_comes_from_the_line_item():
    assert google_subscription_status(load("play_active.json")).expires_at == EXPIRES_AT


def test_google_grace_deadline_is_the_line_item_expiry():
    """미정 14 확정: Google 은 유예 종료 시각을 따로 주지 않고, 유예 중에는
    `lineItems[].expiryTime` 자체가 유예 종료 시각으로 연장돼 온다."""
    normalized = google_subscription_status(load("play_in_grace_period.json"))

    assert normalized.status is SubscriptionStatus.GRACE
    assert normalized.grace_expires_at == GRACE_EXPIRES_AT
    assert normalized.expires_at == GRACE_EXPIRES_AT


@pytest.mark.parametrize(
    "fixture",
    ["play_pending.json", "play_pending_purchase_canceled.json"],
)
def test_google_pending_purchase_makes_no_row(fixture):
    """미정 14 확정: 결제가 아직 안 끝난 구매는 행을 만들지 않는다(권한도 없음)."""
    assert google_subscription_status(load(fixture)).status is None


def test_google_revoked_only_comes_from_an_explicit_flag():
    """v2 응답에는 철회 전용 필드가 없다 — `revoked` 는 호출자(나중에 Voided
    Purchases / RTDN)가 명시적으로 알려줄 때만 나온다. 스펙 미정 항목 14 참고."""
    purchase = load("play_active.json")

    assert google_subscription_status(purchase).status is SubscriptionStatus.ACTIVE
    assert google_subscription_status(purchase, revoked=True).status is SubscriptionStatus.REVOKED


def test_google_unknown_state_is_rejected():
    with pytest.raises(ValueError, match="SUBSCRIPTION_STATE_UNSPECIFIED"):
        google_subscription_status(load("play_active.json") | {
            "subscriptionState": "SUBSCRIPTION_STATE_UNSPECIFIED"
        })
