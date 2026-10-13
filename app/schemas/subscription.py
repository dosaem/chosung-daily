from datetime import datetime

from pydantic import BaseModel

from app.models import SubscriptionStatus, SubscriptionStore


class VerifyReceiptRequest(BaseModel):
    store: SubscriptionStore
    # iOS 는 StoreKit 2 의 서명된 거래(JWS), Android 는 purchaseToken 이다.
    receipt: str


class EntitlementResponse(BaseModel):
    """"지금 이 게스트가 광고를 안 봐도 되는가" 와 그 근거.

    시각은 타임존을 붙여 UTC 로 보낸다 — DB 에는 naive UTC 로 저장하지만
    (`app/utils/time.py`), 앱이 "2026-11-01T00:00:00" 을 기기 로컬시로 읽으면
    만료 판단이 몇 시간씩 틀어진다.
    """

    active: bool
    # 권한이 언제까지인지. 구독이 없으면 None.
    until: datetime | None
    status: SubscriptionStatus | None
    # 어느 스토어에서 온 권한인지(`apple`/`google`). 구독이 없으면 None.
    source: SubscriptionStore | None
    # 앱이 이 시각 뒤에 `/me/stats` 를 다시 불러 권한을 갱신한다(스펙 §A.8).
    next_check_at: datetime | None
