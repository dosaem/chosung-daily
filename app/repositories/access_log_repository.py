"""접속기록 테이블의 **INSERT 전용** 리포지토리.

update/delete 함수를 두지 않는다. 기록 경로 옆에 수정·삭제 함수가 있으면 그게
곧 "지울 수 있는 로그" 라서, 해시 체인으로 위·변조를 검출하는 의미가 없어진다
(고시 제8조 제3항). 만료 삭제는 서비스(`app/services/access_log_service.py`)의
Beat 작업만 하고, 그 한 곳이 기간 지난 행을 통째로 지운다.
"""

from datetime import datetime

from app.extensions import db
from app.models import AccessLog

# 체인의 시작점. 첫 행의 `prev_hash` 자리를 비워 두지 않는다 — 비어 있는 값이면
# "첫 행" 과 "앞을 지운 행" 이 구분되지 않는다.
GENESIS_HASH = "0" * 64


# ruff PLR0913(인자 5개 제한)을 끄지 않고 행 내용을 한 덩어리로 받는다 — 어차피
# 호출부(서비스)가 한 행을 만들어 넘기는 자리라 묶는 게 더 읽기 쉽다.
def append(row: AccessLog, hash_row) -> AccessLog:
    """행 하나를 체인 끝에 붙여 커밋한다.

    `row` 는 `prev_hash`/`hash` 만 비어 있는 행이고, `hash_row(row)` 가 해시를
    계산하는 함수다 — 해시 규칙은 서비스가 들고 있고(점검 CLI 가 같은 함수로 다시
    계산한다) 리포지토리는 "직전 행을 잠그고 읽어서 붙인다" 만 한다.
    """
    # 직전 행을 **잠그고** 읽는다. 두 요청이 같은 직전 행을 읽으면 체인이 두
    # 갈래로 갈리는데, 이 잠금이 둘을 한 줄로 세운다(guess_service 의
    # `SELECT ... FOR UPDATE` 와 같은 패턴). 커밋과 함께 풀리는 행 잠금이라
    # MySQL 네임드 락처럼 커넥션에 남지 않는다. 테이블이 비어 있을 때는 잠글 행이
    # 없어서 첫 행만 경합이 가능한데, 그건 `prev_hash` 유니크가 막는다.
    previous = (
        db.session.query(AccessLog).order_by(AccessLog.id.desc()).with_for_update().first()
    )
    row.prev_hash = previous.hash if previous is not None else GENESIS_HASH
    row.hash = hash_row(row)
    db.session.add(row)
    db.session.commit()
    return row


def find_ordered(since: datetime | None = None, until: datetime | None = None):
    """id 순(= 체인 순) 행 목록. 점검·보고가 쓴다."""
    query = db.session.query(AccessLog)
    if since is not None:
        query = query.filter(AccessLog.occurred_at >= since)
    if until is not None:
        query = query.filter(AccessLog.occurred_at < until)
    return query.order_by(AccessLog.id).all()
