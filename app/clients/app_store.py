"""App Store Server API 래퍼 — 외부 호출은 `fetch_subscription` 하나뿐이다.

검증은 Apple 공식 라이브러리(`app-store-server-library`)에 맡긴다. JWS 서명
체인을 직접 다루면 Apple 인증서 교체 때마다 우리 코드가 깨지고, 면접에서
설명할 값어치도 없다(README "설계 판단").

두 단계다:
1. 앱이 보낸 영수증(StoreKit 2 의 서명된 거래 JWS)을 검증·디코딩해서
   "누구의 어떤 구독인가"(originalTransactionId·bundleId·productId)를 얻는다.
2. 그 originalTransactionId 로 구독 상태를 조회한다 — 영수증 자체는 구매
   시점의 사실이라서 "지금 갱신됐는지/해지됐는지" 는 거기에 없다.

환경 선택: 영수증 안의 `environment` 를 그대로 따른다. App Review 는
프로덕션 서버에 Sandbox 영수증을 보내므로(US 34a) 서버 설정으로 환경을
고정하면 심사가 막힌다. 프로덕션 조회가 "그런 거래 없음" 으로 돌아오면
Sandbox 로 **한 번만** 더 물어본다(Apple 권장 폴백).

상태 해석(숫자 1~5 → 우리 status)은 여기서 하지 않는다 —
`app/services/subscription_status.py` 의 순수 함수 몫이다(스펙 §A.17).
"""

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import override

import attr
import requests
from appstoreserverlibrary.api_client import APIException, AppStoreServerAPIClient
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException
from flask import current_app

from app.errors import ReceiptInvalidError, StoreUnavailableError
from app.models import SubscriptionEnvironment

logger = logging.getLogger(__name__)

# 앱이 구매 직후 이 호출을 기다린다(서버 응답 뒤에야 completePurchase 를 한다).
# 스토어가 느리면 앱을 붙잡아 두지 말고 끊고, 앱이 다음 시작에 다시 올린다.
TIMEOUT_SECONDS = 3

# "이 환경에는 그런 거래가 없다" 는 뜻의 Apple 에러 코드들 — Sandbox 폴백 조건이다.
# 4040010(TRANSACTION_ID_NOT_FOUND) 은 Apple 문서가 폴백 예시로 쓰는 코드이고,
# 4040005(ORIGINAL_TRANSACTION_ID_NOT_FOUND) 는 구독 상태 조회가 같은 상황에서
# 주는 코드다. 둘 다 받아 둬야 심사용 Sandbox 영수증이 막히지 않는다.
_NOT_FOUND_IN_THIS_ENVIRONMENT = {4040010, 4040005}

_ENVIRONMENTS = {
    SubscriptionEnvironment.PRODUCTION: Environment.PRODUCTION,
    SubscriptionEnvironment.SANDBOX: Environment.SANDBOX,
}


@dataclass(frozen=True)
class AppleSubscription:
    """Apple 이 말해준 구독 하나. 상태 해석 없이 받은 사실만 담는다."""

    store_key: str  # originalTransactionId
    product_id: str
    bundle_id: str
    environment: SubscriptionEnvironment
    raw_status: int
    transaction: dict
    renewal_info: dict


@dataclass(frozen=True)
class _Credentials:
    """App Store Server API 호출에 필요한 설정 묶음."""

    bundle_id: str
    # App Store Connect 의 숫자 앱 ID. 공식 검증기가 Production 환경에서
    # 필수로 요구한다(없으면 생성자가 바로 ValueError).
    app_apple_id: int
    issuer_id: str
    key_id: str
    private_key: str
    root_certificates: list[bytes]


class _TimeoutAppStoreServerAPIClient(AppStoreServerAPIClient):
    """공식 라이브러리가 타임아웃을 30초로 박아둬서(`_execute_request`) 그 한
    줄만 바꾼다. 구매 화면에서 30초를 기다리게 할 수는 없다."""

    @override
    def _execute_request(self, method, url, params, headers, json, data):
        return requests.request(
            method,
            url,
            params=params,
            headers=headers,
            json=json,
            data=data,
            timeout=TIMEOUT_SECONDS,
        )


def fetch_subscription(receipt_jws: str) -> AppleSubscription:
    """영수증(JWS)을 검증하고 그 구독의 현재 상태를 Apple 에서 읽어 온다.

    영수증이 위조·손상이면 `ReceiptInvalidError`, Apple 이 응답을 못 주거나
    설정이 비어 있으면 `StoreUnavailableError` 를 던진다.
    """
    credentials = _credentials()
    environment = _environment_of(receipt_jws)
    submitted = _verify_transaction(receipt_jws, credentials, environment)

    store_key = submitted.get("originalTransactionId")
    if not store_key:
        raise ReceiptInvalidError("영수증에 originalTransactionId 가 없습니다.")

    raw_status, latest, renewal_info, environment = _fetch_status(
        store_key, credentials, environment
    )

    # 올라온 영수증은 "이 구독의 주인이 맞다" 를 증명하는 데 쓰고, 저장할 사실
    # (만료일·상품)은 상태 조회가 돌려준 최신 거래에서 읽는다. 조회 응답에
    # 거래가 안 들어 있는 경우에만 영수증 쪽으로 돌아간다.
    transaction = latest or submitted

    return AppleSubscription(
        store_key=store_key,
        product_id=transaction.get("productId") or "",
        bundle_id=transaction.get("bundleId") or "",
        environment=environment,
        raw_status=raw_status,
        transaction=transaction,
        renewal_info=renewal_info,
    )


def _credentials() -> _Credentials:
    config = current_app.config
    values = {
        "APP_STORE_BUNDLE_ID": config["APP_STORE_BUNDLE_ID"],
        "APP_STORE_APP_APPLE_ID": config["APP_STORE_APP_APPLE_ID"],
        "APP_STORE_ISSUER_ID": config["APP_STORE_ISSUER_ID"],
        "APP_STORE_KEY_ID": config["APP_STORE_KEY_ID"],
        "APP_STORE_PRIVATE_KEY": config["APP_STORE_PRIVATE_KEY"],
        "APP_STORE_ROOT_CERT_PATHS": config["APP_STORE_ROOT_CERT_PATHS"],
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        # 설정 누락은 영수증 잘못이 아니다 — 앱에 "나중에 다시 올려라"(503)로 알린다.
        logger.error("App Store Server API 설정이 비어 있다: %s", ", ".join(missing))
        raise StoreUnavailableError()

    return _Credentials(
        bundle_id=values["APP_STORE_BUNDLE_ID"],
        app_apple_id=_app_apple_id(values["APP_STORE_APP_APPLE_ID"]),
        issuer_id=values["APP_STORE_ISSUER_ID"],
        key_id=values["APP_STORE_KEY_ID"],
        private_key=values["APP_STORE_PRIVATE_KEY"],
        root_certificates=_root_certificates(values["APP_STORE_ROOT_CERT_PATHS"]),
    )


def _app_apple_id(value: str | int) -> int:
    """`APP_STORE_APP_APPLE_ID` 는 숫자여야 한다 — 공식 라이브러리가 payload 의
    `appAppleId`(정수)와 그대로 비교한다. 문자열로 두면 조용히 안 맞는다."""
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.error("APP_STORE_APP_APPLE_ID 가 숫자가 아니다")
        raise StoreUnavailableError() from None


def _root_certificates(paths: str) -> list[bytes]:
    """Apple Root CA 인증서(DER)를 읽는다. 서명 체인 검증의 신뢰 기점이다."""
    certificates = []
    for raw_path in paths.split(","):
        path = Path(raw_path.strip())
        if not path.is_file():
            logger.error("Apple Root CA 인증서를 찾을 수 없다: %s", path)
            raise StoreUnavailableError()
        certificates.append(path.read_bytes())
    return certificates


def _environment_of(receipt_jws: str) -> SubscriptionEnvironment:
    """검증 **전에** 영수증의 환경만 먼저 읽는다.

    공식 라이브러리의 검증기는 환경을 생성자에 받으므로 순서가 이렇게 된다.
    서명을 아직 안 믿는 상태로 쓰는 값이지만 안전하다 — 환경을 틀리게 고르면
    바로 다음 단계의 검증이 `INVALID_ENVIRONMENT` 로 실패한다.
    """
    try:
        payload = receipt_jws.split(".")[1]
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError) as exc:
        raise ReceiptInvalidError("영수증이 JWS 모양이 아닙니다.") from exc

    # JSON 으로는 읽히지만 객체가 아닌 payload(`[]`·`null`·문자열)도 있다.
    # 바로 `.get` 을 부르면 AttributeError → 500 이 된다.
    if not isinstance(decoded, dict):
        raise ReceiptInvalidError("영수증 payload 가 JSON 객체가 아닙니다.")

    if decoded.get("environment") == SubscriptionEnvironment.SANDBOX.value:
        return SubscriptionEnvironment.SANDBOX
    return SubscriptionEnvironment.PRODUCTION


def _verifier(
    credentials: _Credentials, environment: SubscriptionEnvironment
) -> SignedDataVerifier:
    return SignedDataVerifier(
        root_certificates=credentials.root_certificates,
        # 온라인 체크(OCSP)는 Apple 서버를 한 번 더 타서 구매 화면을 더 느리게
        # 만든다. 인증서 체인 검증만으로 영수증 위조는 막힌다.
        enable_online_checks=False,
        environment=_ENVIRONMENTS[environment],
        bundle_id=credentials.bundle_id,
        app_apple_id=credentials.app_apple_id,
    )


def _verify_transaction(
    receipt_jws: str, credentials: _Credentials, environment: SubscriptionEnvironment
) -> dict:
    try:
        transaction = _verifier(credentials, environment).verify_and_decode_signed_transaction(
            receipt_jws
        )
    except VerificationException as exc:
        logger.warning("Apple 영수증 검증 실패 (%s)", exc.status)
        raise ReceiptInvalidError() from exc
    return attr.asdict(transaction)


def _fetch_status(
    store_key: str, credentials: _Credentials, environment: SubscriptionEnvironment
) -> tuple[int, dict | None, dict, SubscriptionEnvironment]:
    """구독 상태를 조회한다. 프로덕션에 없으면 Sandbox 로 한 번 더(심사용)."""
    try:
        raw_status, transaction, renewal_info = _status_from(store_key, credentials, environment)
    except APIException as exc:
        can_fall_back = (
            environment is SubscriptionEnvironment.PRODUCTION
            and exc.raw_api_error in _NOT_FOUND_IN_THIS_ENVIRONMENT
        )
        if not can_fall_back:
            raise _as_our_error(exc) from exc

        logger.info("프로덕션에 없는 거래라 Sandbox 로 재조회 (code=%s)", exc.raw_api_error)
        environment = SubscriptionEnvironment.SANDBOX
        try:
            raw_status, transaction, renewal_info = _status_from(
                store_key, credentials, environment
            )
        except APIException as fallback_exc:
            raise _as_our_error(fallback_exc) from fallback_exc

    return raw_status, transaction, renewal_info, environment


def _as_our_error(exc: APIException) -> ReceiptInvalidError | StoreUnavailableError:
    """더 물어볼 환경이 없는 Apple 오류를 우리 계약(400/503)으로 바꾼다.

    그냥 올려보내면 Flask 기본 핸들러가 500 INTERNAL_ERROR 를 준다 — 앱은
    그걸 보고 영수증을 버려야 할지 다시 올려야 할지 알 수 없다.
    """
    if exc.raw_api_error in _NOT_FOUND_IN_THIS_ENVIRONMENT:
        # 프로덕션·Sandbox 어디에도 없는 거래 = 우리 앱의 영수증이 아니다.
        logger.warning("어느 환경에도 없는 거래 (code=%s)", exc.raw_api_error)
        return ReceiptInvalidError()

    # 인증 실패·레이트 리밋·Apple 장애는 전부 "지금은 모른다" 다.
    logger.warning(
        "App Store Server API 실패 (http=%s code=%s)", exc.http_status_code, exc.raw_api_error
    )
    return StoreUnavailableError()


def _status_from(
    store_key: str, credentials: _Credentials, environment: SubscriptionEnvironment
) -> tuple[int, dict | None, dict]:
    client = _TimeoutAppStoreServerAPIClient(
        signing_key=credentials.private_key.encode(),
        key_id=credentials.key_id,
        issuer_id=credentials.issuer_id,
        bundle_id=credentials.bundle_id,
        environment=_ENVIRONMENTS[environment],
    )
    try:
        response = client.get_all_subscription_statuses(store_key)
    except requests.RequestException as exc:
        # 3초 타임아웃·연결 실패. 공식 라이브러리는 이걸 감싸지 않고 그대로 올린다.
        logger.warning("App Store Server API 통신 실패 (%s)", type(exc).__name__)
        raise StoreUnavailableError() from exc

    item = _find_transaction(response, store_key)
    if item is None:
        raise ReceiptInvalidError("구독 상태에서 이 거래를 찾을 수 없습니다.")

    verifier = _verifier(credentials, environment)
    try:
        renewal_info = verifier.verify_and_decode_renewal_info(item.signedRenewalInfo)
        # 앱이 올린 영수증은 **구매 시점**의 거래라 만료일이 이미 지났을 수 있다.
        # 지금 저장해야 할 값은 상태 조회가 돌려준 최신 거래 쪽이다.
        transaction = (
            attr.asdict(verifier.verify_and_decode_signed_transaction(item.signedTransactionInfo))
            if item.signedTransactionInfo
            else None
        )
    except VerificationException as exc:
        logger.warning("Apple 구독 상태 검증 실패 (%s)", exc.status)
        raise ReceiptInvalidError() from exc

    return item.rawStatus, transaction, attr.asdict(renewal_info)


def _find_transaction(response, store_key: str):
    """구독 그룹 안의 거래 중 우리가 물어본 originalTransactionId 를 찾는다."""
    for group in response.data or []:
        for item in group.lastTransactions or []:
            if item.originalTransactionId == store_key:
                return item
    return None
