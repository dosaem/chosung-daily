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


def schedule_revocation(refresh_token_enc: str, client_id: str) -> AppleRevocationRetry:
    """ "이 토큰의 애플 연결을 철회해야 한다" 를 재시도 테이블에 적는다. **커밋하지
    않는다** — 호출자가 삭제와 같은 트랜잭션에 넣어 같이 커밋한다.

    왜 삭제보다 먼저 적는가: 애플 호출이 실패한 **뒤에** 이 행을 저장하면, 삭제
    커밋과 저장 사이에서 DB·프로세스가 죽은 요청은 계정만 지우고 철회 자격증명을
    영구히 버린다(게스트 행이 없으니 다시 찾을 수도, 플레이어가 다시 요청할 수도
    없다). 그래서 의무를 먼저 내구성 있게 적고, 성공했을 때 지운다.
    """
    retry = AppleRevocationRetry(refresh_token_enc=refresh_token_enc, client_id=client_id)
    db.session.add(retry)
    return retry


def complete_scheduled_revocation(retry: AppleRevocationRetry) -> bool:
    """예약해 둔 철회를 지금 한 번 시도한다. 성공하면 그 행을 지우고 True.

    계정 삭제(`account_deletion_service`)가 **커밋을 끝낸 뒤** 부른다 — 애플이
    느리거나 죽어 있어도 플레이어의 삭제는 이미 끝나 있어야 하기 때문이다
    (스펙 §A.7 "실패하면 삭제는 진행하되"). 실패하면 행을 그대로 두고 Beat 가
    매일 다시 시도한다.
    """
    if not _revoke(retry.refresh_token_enc, retry.client_id):
        return False

    db.session.delete(retry)
    db.session.commit()
    return True


def retry_pending_revocations() -> RetryOutcome:
    """Celery Beat 매일. 못 끝낸 철회를 다시 시도하고, 오래된 건 폐기한다.

    폐기 판정을 **시도해 본 뒤에** 내린다: 7일이 지난 행도 그날 한 번은 애플에
    보내보고, 그래도 실패하면 버린다. 덕분에 `notify_operator` 가 울리는 건
    "방금도 안 됐다" 는 뜻이고, 운영자가 알림을 보고 할 일(애플 콘솔에서 사용자
    연결 확인)이 분명해진다.

    한 행에서 터진 예외가 나머지 행의 그날 재시도를 날리지 않게, 실패는 전부
    `_revoke` 안에서 False 로 접힌다.

    삭제 요청이 아직 철회를 시도하는 중인 행도 집어 올 수 있다(의무를 삭제와 같은
    커밋에 적으므로 — `schedule_revocation`). 같은 토큰에 철회가 두 번 가는 게
    최악이고, 애플 쪽 결과는 같다. 하루에 한 번 도는 태스크라 실제로 겹칠 창도
    삭제 요청 한 번의 길이뿐이다.
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
                channel="alerts",
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
