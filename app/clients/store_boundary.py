"""스토어 조회 경계 — 래퍼 밖으로 변환되지 않은 예외가 새지 않게 막는 한 곳.

`POST /subscriptions/verify` 의 계약(티켓 12·스펙 §A' 표)에는 결과가 두 개뿐이다:
영수증이 틀렸으면 400 `RECEIPT_INVALID`, 스토어가 지금 답을 못 주면 503
`STORE_UNAVAILABLE`. 세 번째는 없다. 그런데 Apple·Google 공식 라이브러리는
전송 단계 실패를 **각자의 예외 계열**로 바꿔 던지고(`requests.RequestException`,
`httplib2.HttpLib2Error`, `GoogleAuthError`, …) 그 계열은 라이브러리 버전에 따라
늘어난다. 한 줄이라도 빠뜨리면 스토어 장애인데 500 이 나가고, 앱은 정상 영수증을
버릴지 다시 올릴지 알 수 없게 된다(D-12-5 가 정확히 그 경우였다).

그래서 각 래퍼의 공개 함수 하나를 이 데코레이터로 감싼다. 아래 규칙이다.

- 이미 우리 계약으로 변환된 예외(`AppError`)는 그대로 통과시킨다 — 400 을
  503 으로 덮어쓰지 않는다.
- 그 밖의 예외는 503 으로 바꾸되 **ERROR + 스택**으로 남긴다. 사용자의 구매를
  우리 쪽 버그 때문에 잃게 하지 않으면서, 분류가 빠진 예외는 로그에서 바로
  보이게 하려는 선택이다(조용히 503 으로 묻지 않는다).

구체적인 예외 계열 → 400/503 분류는 각 래퍼가 명시적으로 한다. 이 데코레이터는
그 분류가 놓친 것을 받는 마지막 그물이고, 여기까지 내려온 예외는 결함이다.
"""

import functools
import logging
from collections.abc import Callable

from app.errors import AppError, StoreUnavailableError

logger = logging.getLogger(__name__)


def translating_store_failures(store: str) -> Callable:
    """감싼 함수에서 우리 계약 밖의 예외가 나가지 않게 한다."""

    def decorate(call: Callable) -> Callable:
        @functools.wraps(call)
        def translated(*args, **kwargs):
            try:
                return call(*args, **kwargs)
            except AppError:
                raise
            except Exception as exc:
                logger.error(
                    "%s 구독 조회에서 분류되지 않은 예외 (%s) — 503 으로 바꿔 내보낸다",
                    store,
                    type(exc).__name__,
                    exc_info=True,
                )
                raise StoreUnavailableError() from exc

        return translated

    return decorate
