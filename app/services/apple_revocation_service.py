import logging
from datetime import timedelta
from typing import NamedTuple

import requests
from cryptography.fernet import InvalidToken
from flask import current_app

from app.clients.apple import revoke_refresh_token
from app.extensions import apple_client_ids, apple_client_secret, db
from app.models import AppleRevocationRetry
from app.services.operator_alert_service import notify_operator
from app.utils.crypto import decrypt_secret
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# 스펙 §A.7: 실패한 철회는 매일 재시도하고 이 나이를 넘으면 폐기 + 운영자 알림.
# 이 값이 적절한지는 운영 데이터로 다시 본다(스펙 "미정 11") — 그때 고칠 자리가
# 이 상수 하나다.
RETRY_MAX_AGE = timedelta(days=7)


class RetryOutcome(NamedTuple):
    """재시도 한 바퀴의 결과. 태스크 로그와 테스트가 애플 호출을 들여다보지 않고
    확인할 수 있게 숫자로 돌려준다(`word_pool_service` 가 bool 을 돌려주는 것과
    같은 이유 — 여기선 셋을 구분해야 해서 숫자 세 개다)."""

    revoked: int
    discarded: int
    pending: int


def revoke_or_schedule_retry(refresh_token_enc: str, client_id: str) -> bool:
    """애플 연결을 철회한다. 실패하면 재시도 행을 남기고 False.

    계정 삭제(`account_deletion_service`)가 **커밋을 끝낸 뒤** 부른다 — 애플이
    느리거나 죽어 있어도 플레이어의 삭제는 이미 끝나 있어야 하기 때문이다
    (스펙 §A.7 "실패하면 삭제는 진행하되").
    """
    if _revoke(refresh_token_enc, client_id):
        return True

    db.session.add(AppleRevocationRetry(refresh_token_enc=refresh_token_enc, client_id=client_id))
    db.session.commit()
    return False


def retry_pending_revocations() -> RetryOutcome:
    """Celery Beat 매일. 못 끝낸 철회를 다시 시도하고, 오래된 건 폐기한다.

    폐기 판정을 **시도해 본 뒤에** 내린다: 7일이 지난 행도 그날 한 번은 애플에
    보내보고, 그래도 실패하면 버린다. 덕분에 `notify_operator` 가 울리는 건
    "방금도 안 됐다" 는 뜻이고, 운영자가 알림을 보고 할 일(애플 콘솔에서 사용자
    연결 확인)이 분명해진다.

    한 행에서 터진 예외가 나머지 행의 그날 재시도를 날리지 않게, 실패는 전부
    `_revoke` 안에서 False 로 접힌다.
    """
    revoked = discarded = pending = 0
    now = utcnow()

    for retry in AppleRevocationRetry.query.order_by(AppleRevocationRetry.id).all():
        if _revoke(retry.refresh_token_enc, retry.client_id):
            db.session.delete(retry)
            revoked += 1
        elif now - retry.created_at > RETRY_MAX_AGE:
            db.session.delete(retry)
            discarded += 1
            notify_operator(
                "Apple revoke 재시도 폐기",
                f"{RETRY_MAX_AGE.days}일 동안 애플 연결 철회에 실패해서 토큰을 폐기했습니다.\n"
                f"client_id: {retry.client_id}\n"
                f"삭제 요청 시각(UTC): {retry.created_at.isoformat()}",
            )
        else:
            pending += 1

    db.session.commit()
    return RetryOutcome(revoked, discarded, pending)


def _revoke(refresh_token_enc: str, client_id: str) -> bool:
    """철회 한 번. 성공이면 True, 실패·불가면 False(예외를 올리지 않는다).

    실패를 예외로 올리지 않는 이유: 호출자 둘(삭제 경로, Beat 재시도)이 모두
    "실패해도 계속 간다" 라서, 예외를 올리면 양쪽에 같은 try 가 생긴다.

    복호화 실패(`InvalidToken`)도 실패로 접는다 — SECRET_KEY 를 바꾸면 옛 암호문은
    열 수 없는데, 그걸 예외로 올리면 삭제 요청이 500 이 되거나 Beat 한 바퀴가
    한 행 때문에 멈춘다.
    """
    if client_id not in apple_client_ids(current_app):
        # 서명 키가 없거나 설정에 없는 client — 자격증명을 만들 수 없으니 호출도 못 한다.
        logger.warning("애플 철회를 건너뜀: 서명할 수 없는 client_id(%s)", client_id)
        return False

    try:
        refresh_token = decrypt_secret(refresh_token_enc)
    except InvalidToken:
        logger.warning("애플 철회용 refresh token 복호화 실패(client_id=%s)", client_id)
        return False

    try:
        revoke_refresh_token(
            refresh_token,
            client_id=client_id,
            client_secret=apple_client_secret(current_app, client_id),
        )
    except requests.RequestException:
        logger.warning("애플 철회 호출 실패(client_id=%s)", client_id, exc_info=True)
        return False

    return True
