"""Google Play Developer API 래퍼 — 외부 호출은 `fetch_subscription` 하나뿐이다.

공식 라이브러리(`google-api-python-client`)의 `purchases.subscriptionsv2.get` 을
그대로 쓴다. v1(`purchases.subscriptions`)이 아니라 v2 인 이유는 v2 가
`subscriptionState` 로 유예·보류·일시정지를 한 필드에 정리해서 주고
`linkedPurchaseToken`(구매 교체)도 같은 응답에 들어 있어서다 — v1 은
`paymentState`·`autoRenewing`·`expiryTimeMillis` 조합을 우리가 다시 추론해야 한다.

Apple 과 달리 영수증(purchaseToken)에는 서명된 내용이 없다. 토큰은 그냥
불투명한 문자열이고, "진짜인가" 는 이 조회가 성공하는지로 판단한다. 패키지명도
요청 경로에 우리 것이 들어가므로 **다른 앱의 토큰은 조회 자체가 실패한다** —
그래서 응답에 패키지명을 대조하는 단계가 따로 없다(응답에 그 필드가 없다).

상태 해석(`SUBSCRIPTION_STATE_*` → 우리 status)은
`app/services/subscription_status.py` 의 순수 함수 몫이다(스펙 §A.17).
"""

import logging

import google_auth_httplib2
import httplib2
from flask import current_app
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.errors import ReceiptInvalidError, StoreUnavailableError

logger = logging.getLogger(__name__)

# app_store.py 와 같은 이유로 3초. 앱이 구매 직후 이 호출을 기다린다.
TIMEOUT_SECONDS = 3

_SCOPE = "https://www.googleapis.com/auth/androidpublisher"

# 이 토큰으로는 구독을 찾을 수 없다 = 영수증이 틀렸다(400). 그 밖의 상태 코드는
# 스토어 장애로 보고 503 을 준다 — 앱이 다음 시작에 다시 올린다.
_RECEIPT_INVALID_STATUSES = {400, 404, 410}


def fetch_subscription(purchase_token: str) -> dict:
    """구독 구매 하나의 현재 상태(`SubscriptionPurchaseV2`)를 그대로 돌려준다.

    토큰이 우리 앱의 구독이 아니면 `ReceiptInvalidError`, Google 이 응답을 못
    주거나 설정이 비어 있으면 `StoreUnavailableError` 를 던진다.
    """
    package_name = current_app.config["PLAY_PACKAGE_NAME"]
    service_account_file = current_app.config["PLAY_SERVICE_ACCOUNT_FILE"]
    if not package_name or not service_account_file:
        logger.error("Play Developer API 설정이 비어 있다(PLAY_PACKAGE_NAME/서비스 계정)")
        raise StoreUnavailableError()

    try:
        service = _service(service_account_file)
        return (
            service.purchases()
            .subscriptionsv2()
            .get(packageName=package_name, token=purchase_token)
            .execute(num_retries=0)
        )
    except HttpError as exc:
        if exc.status_code in _RECEIPT_INVALID_STATUSES:
            logger.warning("Play 구독 조회 거부 (status=%s)", exc.status_code)
            raise ReceiptInvalidError() from exc
        logger.warning("Play 구독 조회 실패 (status=%s)", exc.status_code)
        raise StoreUnavailableError() from exc
    except (GoogleAuthError, OSError) as exc:
        # 서비스 계정 키를 못 읽거나(OSError) 토큰 발급이 막힌 경우(GoogleAuthError).
        # httplib2 의 타임아웃도 socket.timeout → OSError 로 올라온다.
        logger.warning("Play 인증·네트워크 실패 (%s)", type(exc).__name__)
        raise StoreUnavailableError() from exc


def _service(service_account_file: str):
    """서비스 계정으로 인증된 androidpublisher 클라이언트를 만든다.

    `static_discovery=True`: 라이브러리에 같이 들어 있는 discovery 문서를 쓴다.
    끄면 호출마다 Google 에서 API 명세를 먼저 받아오는 왕복이 하나 더 붙는다.
    """
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=[_SCOPE]
    )
    authorized_http = google_auth_httplib2.AuthorizedHttp(
        credentials, http=httplib2.Http(timeout=TIMEOUT_SECONDS)
    )
    return build(
        "androidpublisher", "v3", http=authorized_http, static_discovery=True, cache_discovery=False
    )
