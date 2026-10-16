"""접속기록(개인정보 처리 행위 감사 로그)의 해시 체인·보관·점검.

근거 조문은 **개인정보의 안전성 확보조치 기준**(개인정보보호위원회 고시
제2023-6호) 제8조(접속기록의 보관 및 점검)다.

- 제1항 보관: 1년 이상. 5만명 이상 정보주체·고유식별정보·민감정보·기간통신사업자면
  2년 이상인데 이 서비스는 셋 다 아니라(수집 항목은 방침 `#collection`) 기본값이
  **365일**이다(`ACCESS_LOG_RETENTION_DAYS`). 규모가 커지면 설정값만 올린다.
- 제2항 점검: 월 1회 이상 → `flask access-log report --month YYYY-MM`(사람이 돌린다,
  `docs/RELEASE.md` "### 36.").
- 제3항 위·변조 방지: 행마다 `hash = sha256(prev_hash + 행 내용)` 체인 →
  `flask access-log verify`.

기록 **지점**(어느 요청이 어떤 행위로 남는가)은 `app/access_log.py` 에 있다.
이 모듈은 "무엇을 해시하고, 언제 지우고, 어떻게 점검하는가" 만 안다.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from app.models import AccessLog
from app.repositories import access_log_repository
from app.services.operator_alert_service import notify_operator
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# 체인 시작점은 저장 규칙이라 리포지토리가 들고 있고, 점검·테스트가 서비스 쪽에서도
# 읽어서 이름만 다시 내보낸다.
GENESIS_HASH = access_log_repository.GENESIS_HASH

SUCCESS = "success"
DENIED = "denied"
ERROR = "error"

# 401·403 은 "거부", 그 밖의 4xx·5xx 는 "오류" 다(점검이 둘을 갈라 센다).
DENIED_STATUS_CODES = (401, 403)
FIRST_ERROR_STATUS_CODE = 400


def result_for(status_code: int) -> str:
    """상태 코드를 결과 한 단어로. 점검이 "거부" 를 세는 기준이다."""
    if status_code in DENIED_STATUS_CODES:
        return DENIED
    if status_code >= FIRST_ERROR_STATUS_CODE:
        return ERROR
    return SUCCESS


def row_hash(row: AccessLog) -> str:
    """`sha256(prev_hash + 행 내용)`.

    행 내용은 컬럼을 `|` 로 이어 붙인다 — JSON 처럼 키 순서·공백에 따라 달라지는
    직렬화를 쓰면 같은 행의 해시가 파이썬 버전에 따라 변할 수 있다.
    """
    content = "|".join(
        [
            row.prev_hash,
            row.occurred_at.isoformat(timespec="seconds"),
            row.actor,
            row.remote_ip,
            row.action,
            row.target or "",
            row.result,
            str(row.status_code),
        ]
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def record_access(
    *,
    action: str,
    actor: str,
    remote_ip: str,
    target: str | None,
    status_code: int,
) -> AccessLog:
    # 요청이 남긴 미커밋 변경을 먼저 되돌린다. 이 함수는 응답 훅에서 불리는데,
    # 거기서 commit 을 하면 요청이 **커밋하지 않고 끝낸** 변경(검증 실패로 중단된
    # CSV 적재처럼)이 같이 저장된다 — 접속기록을 남기는 일이 데이터를 바꿔선 안 된다.
    db.session.rollback()
    row = AccessLog(
        # 초 단위로 끊는다 — MySQL DATETIME 이 마이크로초를 버리기 때문에, 그대로
        # 해시하면 저장된 행에서 다시 계산한 값이 달라져 체인이 끊긴 것처럼 보인다.
        occurred_at=utcnow().replace(microsecond=0),
        actor=actor,
        remote_ip=remote_ip,
        action=action,
        target=target,
        result=result_for(status_code),
        status_code=status_code,
    )
    return access_log_repository.append(row, row_hash)


@dataclass(frozen=True)
class ChainCheck:
    checked: int
    broken_at: int | None


def verify_chain() -> ChainCheck:
    """남아 있는 체인을 다시 계산해 끊긴 첫 행의 id 를 찾는다.

    두 가지가 다 잡힌다: 행 내용이 바뀌면 그 행의 `hash` 가 안 맞고, 중간 행이
    사라지면 다음 행의 `prev_hash` 가 앞 행의 `hash` 와 안 맞는다.

    **맨 앞 행의 `prev_hash` 는 검사하지 않는다.** 보관 기간이 지난 행은 날마다
    지워지므로(고시가 요구하는 것은 1년 보관이고, 더 들고 있으면 그게 위반이다)
    첫 행은 이미 사라진 행을 가리키는 게 정상이다. 그 자리를 genesis 와 비교하면
    첫 만료 삭제 이후 verify 가 영원히 "끊겼다" 를 찍어 도구가 쓸모없어진다.
    대가: **맨 앞을 지운 것**은 만료 삭제와 구분되지 않는다 — 그건 보관 기간 안의
    기록을 통째로 지워야 하는 일이라 행 수·월별 보고(`monthly_report`)에서 드러난다.
    """
    previous_hash: str | None = None
    checked = 0
    for row in access_log_repository.find_ordered():
        checked += 1
        chained = previous_hash is None or row.prev_hash == previous_hash
        if not chained or row.hash != row_hash(row):
            return ChainCheck(checked=checked, broken_at=row.id)
        previous_hash = row.hash
    return ChainCheck(checked=checked, broken_at=None)


def _delete_rows_before(cutoff: datetime) -> int:
    deleted = (
        db.session.query(AccessLog)
        .filter(AccessLog.occurred_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return deleted


def purge_expired_access_logs() -> int:
    """보관 기간이 지난 행을 지운다. Beat 가 매일 한 번 부른다.

    오래된 쪽을 앞에서 지우면 남은 첫 행의 `prev_hash` 는 사라진 행을 가리킨 채로
    남는다 — 그래서 `verify_chain` 이 맨 앞 행의 `prev_hash` 만 검사하지 않는다
    (그 함수의 독스트링).
    """
    days = current_app.config["ACCESS_LOG_RETENTION_DAYS"]
    cutoff = utcnow() - timedelta(days=days)
    try:
        deleted = _delete_rows_before(cutoff)
    except Exception:
        # 지우지 못하면 보관 기간을 넘긴 개인정보가 계속 남는다 — 조용히 넘기지 않는다.
        db.session.rollback()
        notify_operator(
            "접속기록 만료 삭제 실패",
            f"보관 기간 {days}일이 지난 접속기록을 지우지 못했습니다. 서버 로그를 확인하세요.",
            channel="alerts",
        )
        raise
    if deleted:
        logger.info("access_log: pruned %s rows older than %s", deleted, cutoff)
    return deleted


@dataclass(frozen=True)
class MonthlyReport:
    month: str
    total: int
    by_action: dict[str, int]
    denied: int
    chain: ChainCheck


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    try:
        start = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise ValueError(f"month must be in YYYY-MM form: {month!r}") from None
    # "다음 달 1일" 을 달의 길이를 몰라도 구한다(28일 + 7일 → 다음 달 어딘가 → 1일).
    end = (start.replace(day=28) + timedelta(days=7)).replace(day=1)
    return start, end


def monthly_report(month: str) -> MonthlyReport:
    """고시 제8조 제2항의 "월 1회 이상 점검" 에 쓰는 집계.

    사람이 보는 숫자는 세 개다: 행위별 건수(평소와 다른 행위가 있나), 거부 건수
    (막힌 접근 시도가 있나), 체인 검증 결과(기록 자체가 손대졌나).
    """
    since, until = _month_bounds(month)
    rows = access_log_repository.find_ordered(since=since, until=until)
    by_action: dict[str, int] = {}
    for row in rows:
        by_action[row.action] = by_action.get(row.action, 0) + 1
    return MonthlyReport(
        month=month,
        total=len(rows),
        by_action=by_action,
        denied=sum(1 for row in rows if row.result == DENIED),
        chain=verify_chain(),
    )
