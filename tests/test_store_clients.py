"""스토어 래퍼(`app/clients/app_store.py`·`play.py`)의 호출 경로 테스트.

여기서 검증하는 건 네트워크 경계의 행동뿐이다: 어떤 환경에 물어보는지,
실패를 400(영수증 잘못)과 503(스토어 장애)으로 어떻게 가르는지, 설정이
비었을 때 무슨 일이 나는지. 실제 Apple·Google 을 부르지 않는다 — 공식
라이브러리의 호출 지점만 가짜로 바꿔 끼운다.
"""

import base64
import json
from pathlib import Path

import pytest
from appstoreserverlibrary.api_client import APIException, _get_cattrs_converter
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.JWSRenewalInfoDecodedPayload import (
    JWSRenewalInfoDecodedPayload,
)
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import (
    JWSTransactionDecodedPayload,
)
from googleapiclient.errors import HttpError

from app.clients import app_store, play
from app.errors import ReceiptInvalidError, StoreUnavailableError
from app.models import SubscriptionEnvironment

FIXTURES = Path(__file__).parent / "fixtures" / "store"
BUNDLE_ID = "com.chosungdaily.app"
STORE_KEY = "2000000111111111"


def receipt_jws(environment: str = "Production") -> str:
    """환경 선택 단계가 읽을 수 있는 최소한의 JWS 모양 문자열.

    서명은 가짜다 — 검증 자체는 공식 라이브러리 몫이고 이 테스트에서는
    그 지점을 바꿔 끼운다. `_environment_of` 는 서명을 믿지 않고 환경만 읽는다.
    """
    payload = base64.urlsafe_b64encode(
        json.dumps({"environment": environment, "originalTransactionId": STORE_KEY}).encode()
    ).decode().rstrip("=")
    return f"header.{payload}.signature"


class _FakeVerifier:
    """공식 검증기 자리. fixture 를 라이브러리 객체로 되돌려 준다."""

    def __init__(self, item: dict):
        self._item = item

    def verify_and_decode_signed_transaction(self, _jws):
        return _structure(self._item["signedTransactionInfo"], JWSTransactionDecodedPayload)

    def verify_and_decode_renewal_info(self, _jws):
        return _structure(self._item["signedRenewalInfo"], JWSRenewalInfoDecodedPayload)


def _structure(payload: dict, model):
    return _get_cattrs_converter(model).structure(payload, model)


def _status_response(item: dict):
    """`get_all_subscription_statuses` 응답 모양(그룹 → 거래 목록)."""
    transaction = type(
        "_Item",
        (),
        {
            "originalTransactionId": item["originalTransactionId"],
            "rawStatus": item["status"],
            "signedRenewalInfo": "signed-renewal-info",
        },
    )()
    group = type("_Group", (), {"lastTransactions": [transaction]})()
    return type("_Response", (), {"data": [group]})()


@pytest.fixture
def app_store_configured(app, tmp_path, monkeypatch):
    """App Store 설정을 "채워진" 상태로 만든다(Root CA 파일 포함)."""
    cert = tmp_path / "AppleRootCA-G3.cer"
    cert.write_bytes(b"not-a-real-certificate")
    app.config.update(
        APP_STORE_BUNDLE_ID=BUNDLE_ID,
        APP_STORE_ISSUER_ID="issuer-id",
        APP_STORE_KEY_ID="key-id",
        APP_STORE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----",
        APP_STORE_ROOT_CERT_PATHS=str(cert),
    )
    return app


@pytest.fixture
def apple_calls(monkeypatch):
    """Apple 조회를 가로채고, 어떤 환경으로 몇 번 물어봤는지 기록한다."""
    item = json.loads((FIXTURES / "apple_active.json").read_text())
    environments: list[Environment] = []
    fail_with: dict[Environment, APIException] = {}

    monkeypatch.setattr(app_store, "_verifier", lambda *_: _FakeVerifier(item))

    class _FakeClient:
        def __init__(self, **kwargs):
            self._environment = kwargs["environment"]

        def get_all_subscription_statuses(self, _store_key):
            environments.append(self._environment)
            if self._environment in fail_with:
                raise fail_with[self._environment]
            return _status_response(item)

    monkeypatch.setattr(app_store, "_TimeoutAppStoreServerAPIClient", _FakeClient)
    return {"environments": environments, "fail_with": fail_with}


def test_apple_receipt_environment_picks_the_endpoint(app_store_configured, apple_calls):
    app_store.fetch_subscription(receipt_jws("Sandbox"))

    assert apple_calls["environments"] == [Environment.SANDBOX]


def test_apple_production_miss_falls_back_to_sandbox_once(app_store_configured, apple_calls):
    """심사용: 프로덕션 서버가 Sandbox 영수증을 받으면 4040010 뒤에 Sandbox 로 재조회."""
    apple_calls["fail_with"][Environment.PRODUCTION] = APIException(404, 4040010)

    result = app_store.fetch_subscription(receipt_jws("Production"))

    assert apple_calls["environments"] == [Environment.PRODUCTION, Environment.SANDBOX]
    assert result.environment is SubscriptionEnvironment.SANDBOX
    assert result.store_key == STORE_KEY


def test_apple_sandbox_miss_does_not_loop_back(app_store_configured, apple_calls):
    """Sandbox 로 시작했는데 없으면 폴백할 곳이 없다 — 한 번만 물어보고 끝낸다."""
    apple_calls["fail_with"][Environment.SANDBOX] = APIException(404, 4040010)

    with pytest.raises(APIException):
        app_store.fetch_subscription(receipt_jws("Sandbox"))

    assert apple_calls["environments"] == [Environment.SANDBOX]


def test_apple_other_api_errors_are_not_retried(app_store_configured, apple_calls):
    """"없음" 이 아닌 에러(예: 인증 실패)는 Sandbox 로 다시 물어볼 일이 아니다."""
    apple_calls["fail_with"][Environment.PRODUCTION] = APIException(401, 4010000)

    with pytest.raises(APIException):
        app_store.fetch_subscription(receipt_jws("Production"))

    assert apple_calls["environments"] == [Environment.PRODUCTION]


def test_apple_returns_the_facts_without_interpreting_them(app_store_configured, apple_calls):
    result = app_store.fetch_subscription(receipt_jws("Production"))

    assert result.product_id == "adfree_monthly"
    assert result.bundle_id == BUNDLE_ID
    assert result.raw_status == 1
    assert result.transaction["originalTransactionId"] == STORE_KEY


def test_apple_missing_settings_is_a_store_outage(app, apple_calls):
    """키를 아직 안 넣은 서버는 영수증을 탓하지 않고 503 을 준다."""
    app.config.update(APP_STORE_BUNDLE_ID="", APP_STORE_ISSUER_ID="")

    with pytest.raises(StoreUnavailableError):
        app_store.fetch_subscription(receipt_jws())


def test_apple_malformed_receipt_is_rejected(app_store_configured, apple_calls):
    with pytest.raises(ReceiptInvalidError):
        app_store.fetch_subscription("not-a-jws")


def test_apple_timeout_is_three_seconds():
    """구매 화면이 기다리는 호출이라 공식 라이브러리의 30초 기본값을 쓰지 않는다."""
    assert app_store.TIMEOUT_SECONDS == 3


def _http_error(status: int) -> HttpError:
    response = type("_Response", (), {"status": status, "reason": "nope"})()
    return HttpError(response, b'{"error": {"message": "nope"}}')


@pytest.fixture
def play_configured(app):
    app.config.update(
        PLAY_PACKAGE_NAME="com.chosungdaily.app",
        PLAY_SERVICE_ACCOUNT_FILE="/not/read/in/tests.json",
    )
    return app


def _patch_play(monkeypatch, *, result=None, error=None):
    calls = {}

    class _Request:
        def execute(self, num_retries=None):
            calls["num_retries"] = num_retries
            if error is not None:
                raise error
            return result

    class _Subscriptions:
        def get(self, **kwargs):
            calls.update(kwargs)
            return _Request()

    class _Purchases:
        def subscriptionsv2(self):
            return _Subscriptions()

    class _Service:
        def purchases(self):
            return _Purchases()

    monkeypatch.setattr(play, "_service", lambda _file: _Service())
    return calls


def test_play_asks_for_our_package_and_token(play_configured, monkeypatch):
    purchase = json.loads((FIXTURES / "play_active.json").read_text())
    calls = _patch_play(monkeypatch, result=purchase)

    assert play.fetch_subscription("purchase-token-1") == purchase
    assert calls["packageName"] == "com.chosungdaily.app"
    assert calls["token"] == "purchase-token-1"


@pytest.mark.parametrize("status", [400, 404, 410])
def test_play_unknown_token_is_a_bad_receipt(play_configured, monkeypatch, status):
    _patch_play(monkeypatch, error=_http_error(status))

    with pytest.raises(ReceiptInvalidError):
        play.fetch_subscription("purchase-token-1")


@pytest.mark.parametrize("status", [429, 500, 503])
def test_play_server_trouble_is_a_store_outage(play_configured, monkeypatch, status):
    _patch_play(monkeypatch, error=_http_error(status))

    with pytest.raises(StoreUnavailableError):
        play.fetch_subscription("purchase-token-1")


def test_play_network_timeout_is_a_store_outage(play_configured, monkeypatch):
    _patch_play(monkeypatch, error=TimeoutError("timed out"))

    with pytest.raises(StoreUnavailableError):
        play.fetch_subscription("purchase-token-1")


def test_play_missing_settings_is_a_store_outage(app):
    app.config.update(PLAY_PACKAGE_NAME="", PLAY_SERVICE_ACCOUNT_FILE="")

    with pytest.raises(StoreUnavailableError):
        play.fetch_subscription("purchase-token-1")


def test_play_timeout_is_three_seconds():
    assert play.TIMEOUT_SECONDS == 3
