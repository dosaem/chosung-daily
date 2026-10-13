"""스토어 래퍼(`app/clients/app_store.py`·`play.py`)의 호출 경로 테스트.

여기서 검증하는 건 네트워크 경계의 행동뿐이다: 어떤 환경에 물어보는지,
실패를 400(영수증 잘못)과 503(스토어 장애)으로 어떻게 가르는지, 설정이
비었을 때 무슨 일이 나는지. 실제 Apple·Google 을 부르지 않는다 — 공식
라이브러리의 호출 지점만 가짜로 바꿔 끼운다.
"""

import base64
import json
import ssl
from pathlib import Path

import httplib2
import pytest
import requests
from appstoreserverlibrary.api_client import APIException, _get_cattrs_converter
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.JWSRenewalInfoDecodedPayload import (
    JWSRenewalInfoDecodedPayload,
)
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import (
    JWSTransactionDecodedPayload,
)
from google.auth.exceptions import GoogleAuthError, RefreshError
from googleapiclient.errors import HttpError

from app.clients import app_store, play
from app.errors import ReceiptInvalidError, StoreUnavailableError
from app.models import SubscriptionEnvironment

FIXTURES = Path(__file__).parent / "fixtures" / "store"
BUNDLE_ID = "com.chosungdaily.app"
APP_APPLE_ID = "6450000000"
STORE_KEY = "2000000111111111"

# 상태 조회 응답이 들고 오는 "지금 유효한 거래" 의 JWS 자리. 앱이 올린 영수증
# JWS 와 다른 문자열이어야 둘 중 어느 쪽을 검증했는지 테스트가 구분할 수 있다.
LATEST_TRANSACTION_JWS = "signed-latest-transaction"


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
    """공식 검증기 자리. JWS 문자열을 fixture 페이로드로 되돌려 준다.

    앱이 올린 영수증과 상태 조회가 돌려준 최신 거래는 서로 다른 JWS 다 —
    어느 쪽을 검증했는지 `verified` 에 남겨 테스트가 확인한다.
    """

    def __init__(self, state: dict):
        self._state = state

    def verify_and_decode_signed_transaction(self, jws):
        self._state["verified"].append(jws)
        payload = (
            self._state["latest"] if jws == LATEST_TRANSACTION_JWS else self._state["submitted"]
        )
        return _structure(payload, JWSTransactionDecodedPayload)

    def verify_and_decode_renewal_info(self, _jws):
        return _structure(self._state["renewal_info"], JWSRenewalInfoDecodedPayload)


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
            "signedTransactionInfo": LATEST_TRANSACTION_JWS,
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
        APP_STORE_APP_APPLE_ID=APP_APPLE_ID,
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
    fail_with: dict[Environment, Exception] = {}
    state = {
        # 앱이 올린 영수증의 거래와 상태 조회가 돌려주는 최신 거래. 기본값은
        # 같은 내용이고, D-12-3 테스트만 최신 쪽을 갈아 끼운다.
        "submitted": item["signedTransactionInfo"],
        "latest": item["signedTransactionInfo"],
        "renewal_info": item["signedRenewalInfo"],
        "verified": [],
    }

    monkeypatch.setattr(app_store, "_verifier", lambda *_: _FakeVerifier(state))

    class _FakeClient:
        def __init__(self, **kwargs):
            self._environment = kwargs["environment"]

        def get_all_subscription_statuses(self, _store_key):
            environments.append(self._environment)
            if self._environment in fail_with:
                raise fail_with[self._environment]
            return _status_response(item)

    monkeypatch.setattr(app_store, "_TimeoutAppStoreServerAPIClient", _FakeClient)
    return {"environments": environments, "fail_with": fail_with, "state": state}


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
    """Sandbox 로 시작했는데 없으면 폴백할 곳이 없다 — 한 번만 물어보고 끝낸다.

    그리고 "어느 환경에도 없는 거래" 는 스토어 장애가 아니라 틀린 영수증이다(400).
    """
    apple_calls["fail_with"][Environment.SANDBOX] = APIException(404, 4040010)

    with pytest.raises(ReceiptInvalidError):
        app_store.fetch_subscription(receipt_jws("Sandbox"))

    assert apple_calls["environments"] == [Environment.SANDBOX]


def test_apple_production_fallback_miss_is_a_bad_receipt(app_store_configured, apple_calls):
    """폴백까지 갔는데도 없으면 더 물어볼 환경이 없다 — 영수증 잘못(400)."""
    apple_calls["fail_with"][Environment.PRODUCTION] = APIException(404, 4040010)
    apple_calls["fail_with"][Environment.SANDBOX] = APIException(404, 4040005)

    with pytest.raises(ReceiptInvalidError):
        app_store.fetch_subscription(receipt_jws("Production"))

    assert apple_calls["environments"] == [Environment.PRODUCTION, Environment.SANDBOX]


def test_apple_other_api_errors_are_not_retried(app_store_configured, apple_calls):
    """"없음" 이 아닌 에러(예: 인증 실패)는 Sandbox 로 다시 물어볼 일이 아니다.

    영수증을 탓할 근거도 없으니 스토어 장애(503)로 올린다.
    """
    apple_calls["fail_with"][Environment.PRODUCTION] = APIException(401, 4010000)

    with pytest.raises(StoreUnavailableError):
        app_store.fetch_subscription(receipt_jws("Production"))

    assert apple_calls["environments"] == [Environment.PRODUCTION]


def test_apple_server_trouble_is_a_store_outage(app_store_configured, apple_calls):
    """Apple 이 5xx 를 주면 "지금은 모른다" 다 — 앱이 다시 올리도록 503."""
    apple_calls["fail_with"][Environment.PRODUCTION] = APIException(503)

    with pytest.raises(StoreUnavailableError):
        app_store.fetch_subscription(receipt_jws("Production"))


def test_apple_network_timeout_is_a_store_outage(app_store_configured, apple_calls):
    """3초 타임아웃에 걸린 요청이 그대로 올라가면 500 이 된다 — 503 으로 바꾼다."""
    apple_calls["fail_with"][Environment.PRODUCTION] = requests.Timeout("timed out")

    with pytest.raises(StoreUnavailableError):
        app_store.fetch_subscription(receipt_jws("Production"))


def test_apple_uses_the_latest_transaction_from_the_status_lookup(
    app_store_configured, apple_calls
):
    """영수증은 구매 시점의 사실이라 만료일이 과거다. 저장할 값은 상태 조회가
    돌려준 최신 거래의 만료일이어야 한다."""
    apple_calls["state"]["submitted"] = apple_calls["state"]["submitted"] | {
        "expiresDate": 1000,
    }
    apple_calls["state"]["latest"] = apple_calls["state"]["latest"] | {
        "expiresDate": 1793491200000,
    }

    result = app_store.fetch_subscription(receipt_jws("Production"))

    assert result.transaction["expiresDate"] == 1793491200000
    assert result.store_key == STORE_KEY
    # 올라온 영수증도 여전히 검증한다 — 최신 거래만 믿으면 아무 영수증이나 통과한다.
    assert apple_calls["state"]["verified"] == [
        receipt_jws("Production"),
        LATEST_TRANSACTION_JWS,
    ]


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


@pytest.mark.parametrize("payload", [[], None, "string", 7])
def test_apple_jws_payload_that_is_not_an_object_is_rejected(
    app_store_configured, apple_calls, payload
):
    """JSON 으로는 읽히지만 객체가 아닌 payload 도 영수증 잘못(400)이다 —
    `.get` 을 바로 불러서 500 이 나면 안 된다."""
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    with pytest.raises(ReceiptInvalidError):
        app_store.fetch_subscription(f"header.{encoded}.signature")


def test_apple_production_verifier_is_built_with_the_configured_app_apple_id(
    app_store_configured,
):
    """공식 라이브러리는 Production 검증기에 appAppleId 를 요구한다 — 여기만
    빠져도 프로덕션 영수증이 전부 검증 전에 죽는다. 진짜 SDK 생성자를 부른다."""
    credentials = app_store._credentials()

    assert credentials.app_apple_id == int(APP_APPLE_ID)
    for environment in SubscriptionEnvironment:
        verifier = app_store._verifier(credentials, environment)
        assert verifier._app_apple_id == int(APP_APPLE_ID)


@pytest.mark.parametrize("value", ["", "not-a-number"])
def test_apple_bad_app_apple_id_is_a_store_outage(app_store_configured, apple_calls, value):
    """설정이 비었거나 숫자가 아니면 영수증 잘못이 아니라 서버 설정 문제(503)."""
    app_store_configured.config.update(APP_STORE_APP_APPLE_ID=value)

    with pytest.raises(StoreUnavailableError):
        app_store.fetch_subscription(receipt_jws())


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


@pytest.mark.parametrize(
    "error",
    [
        httplib2.ServerNotFoundError("Unable to find the server at x"),
        httplib2.RedirectLimit("too many redirects", None, b""),
        httplib2.ProxiesUnavailableError("no socks"),
    ],
)
def test_play_httplib2_transport_failure_is_a_store_outage(play_configured, monkeypatch, error):
    """D-12-5. 공식 SDK 가 쓰는 httplib2 는 전송 실패를 `HttpLib2Error` 로 바꾼다 —
    `OSError` 가 아니다. DNS 실패(`ServerNotFoundError`)가 대표 경우다."""
    _patch_play(monkeypatch, error=error)

    with pytest.raises(StoreUnavailableError):
        play.fetch_subscription("purchase-token-1")


def test_play_missing_settings_is_a_store_outage(app):
    app.config.update(PLAY_PACKAGE_NAME="", PLAY_SERVICE_ACCOUNT_FILE="")

    with pytest.raises(StoreUnavailableError):
        play.fetch_subscription("purchase-token-1")


def test_play_timeout_is_three_seconds():
    assert play.TIMEOUT_SECONDS == 3


# ---------------------------------------------------------------------------
# 예외 계열 → 우리 계약(400/503) 표 (D-12-5 후속)
#
# 두 래퍼가 쓰는 공식 라이브러리는 전송·인증·파싱 실패를 각자의 예외 계열로
# 바꿔 던진다. 계열을 하나라도 빠뜨리면 스토어 장애인데 500 이 나가서 앱이
# 정상 영수증을 버린다(D-12-5). 아래 두 테스트가 그 표 전체를 고정한다.
# "파싱 실패"·"알 수 없음" 행은 어느 라이브러리 계열에도 안 들어가는 자리이고,
# `store_boundary.translating_store_failures` 가 마지막 그물로 받는다.
# ---------------------------------------------------------------------------

#: (계열 이름, 래퍼에 들어오는 예외, 기대하는 우리 예외)
APPLE_FAILURES = [
    ("연결 실패", requests.ConnectionError("no route to host"), StoreUnavailableError),
    (
        "DNS",
        requests.ConnectionError("Failed to resolve 'api.storekit.itunes.apple.com'"),
        StoreUnavailableError,
    ),
    ("타임아웃", requests.Timeout("timed out"), StoreUnavailableError),
    ("TLS", requests.exceptions.SSLError("certificate verify failed"), StoreUnavailableError),
    ("HTTP 5xx", APIException(503), StoreUnavailableError),
    ("레이트 리밋", APIException(429, 4290000), StoreUnavailableError),
    ("인증 실패", APIException(401, 4010000), StoreUnavailableError),
    ("어느 환경에도 없는 거래", APIException(404, 4040010), ReceiptInvalidError),
    ("응답 파싱 실패", ValueError("Expecting value: line 1 column 1"), StoreUnavailableError),
    ("알 수 없음", RuntimeError("공식 라이브러리의 새 예외"), StoreUnavailableError),
]

PLAY_FAILURES = [
    ("연결 실패", OSError("no route to host"), StoreUnavailableError),
    ("DNS", httplib2.ServerNotFoundError("Unable to find the server at x"), StoreUnavailableError),
    ("타임아웃", TimeoutError("timed out"), StoreUnavailableError),
    ("TLS", ssl.SSLError("certificate verify failed"), StoreUnavailableError),
    ("프록시 불가", httplib2.ProxiesUnavailableError("no socks"), StoreUnavailableError),
    ("HTTP 5xx", _http_error(503), StoreUnavailableError),
    ("레이트 리밋", _http_error(429), StoreUnavailableError),
    ("인증 실패", RefreshError("invalid_grant"), StoreUnavailableError),
    ("토큰 발급 실패", GoogleAuthError("no credentials"), StoreUnavailableError),
    ("토큰으로 구독을 못 찾음", _http_error(404), ReceiptInvalidError),
    ("응답 파싱 실패", ValueError("Expecting value: line 1 column 1"), StoreUnavailableError),
    ("알 수 없음", RuntimeError("공식 라이브러리의 새 예외"), StoreUnavailableError),
]


@pytest.mark.parametrize(
    ("error", "expected"),
    [pytest.param(error, expected, id=name) for name, error, expected in APPLE_FAILURES],
)
def test_apple_failures_all_become_our_contract(
    app_store_configured, apple_calls, error, expected
):
    """Apple 래퍼에서는 400/503 둘 중 하나만 나간다 — 500 은 계약에 없다."""
    apple_calls["fail_with"][Environment.PRODUCTION] = error
    apple_calls["fail_with"][Environment.SANDBOX] = error

    with pytest.raises(expected):
        app_store.fetch_subscription(receipt_jws("Production"))


@pytest.mark.parametrize(
    ("error", "expected"),
    [pytest.param(error, expected, id=name) for name, error, expected in PLAY_FAILURES],
)
def test_play_failures_all_become_our_contract(play_configured, monkeypatch, error, expected):
    """Google 래퍼에서도 마찬가지다. DNS 행이 D-12-5 였다."""
    _patch_play(monkeypatch, error=error)

    with pytest.raises(expected):
        play.fetch_subscription("purchase-token-1")
