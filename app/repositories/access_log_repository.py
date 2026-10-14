"""접속기록 테이블의 **INSERT 전용** 리포지토리.

update/delete 함수를 두지 않는다. 기록 경로 옆에 수정·삭제 함수가 있으면 그게
곧 "지울 수 있는 로그" 라서, 해시 체인으로 위·변조를 검출하는 의미가 없어진다
(고시 제8조 제3항). 만료 삭제는 서비스(`app/services/access_log_service.py`)의
Beat 작업만 하고, 그 한 곳이 기간 지난 행을 통째로 지운다.
"""

from contextlib import contextmanager
from datetime import datetime

from app.extensions import db
from app.models import AccessLog

# 체인의 시작점. 첫 행의 `prev_hash` 자리를 비워 두지 않는다 — 비어 있는 값이면
# "첫 행" 과 "앞을 지운 행" 이 구분되지 않는다.
GENESIS_HASH = "0" * 64

# 네임드 락을 기다리는 한도. 기록은 응답 훅에서 일어나므로 무한정 기다리면 요청이
# 멈춘다 — 못 잡으면 예외로 올려서 훅이 Sentry 에 남긴다.
APPEND_LOCK_TIMEOUT_SECONDS = 10


class AppendLockTimeout(RuntimeError):
    """체인 잠금을 제한 시간 안에 못 잡았다 — 그 기록은 남지 않는다."""


@contextmanager
def _chain_lock():
    """체인 끝에 붙이는 동안 **MySQL 네임드 락**으로 한 줄로 세운다.

    직전 행을 `SELECT ... FOR UPDATE` 로 잠그는 방식으로는 부족하다. (a) 테이블이
    비어 있으면 잠글 행이 아예 없고, (b) 잠금을 기다리던 쪽이 깨어나도 그 사이
    커밋된 **새 꼬리**는 이미 지나간 인덱스 스캔에 안 들어와서 낡은 `prev_hash`
    로 INSERT 한다 — 유니크 제약이 체인이 갈라지는 건 막지만, 응답 훅이 예외를
    삼키는 만큼 개인정보 처리 기록 자체가 사라진다(동시 10건에 7~8건 유실).

    락은 **전용 연결**에서 잡는다. 네임드 락은 트랜잭션이 아니라 연결에 붙어
    있어서, 기록 세션의 연결로 잡으면 commit 이 그 연결을 풀에 돌려준 뒤에는
    같은 연결로 RELEASE_LOCK 을 부른다는 보장이 없다(영영 안 풀리는 락이 된다).
    이름에 DB 이름을 붙여 같은 MySQL 서버의 prod/develop/테스트가 서로를 막지
    않게 한다 — 네임드 락은 서버 전역이다.
    """
    name = f"access_log_append:{db.engine.url.database}"
    # AUTOCOMMIT: 이 연결은 락만 잡는다. 트랜잭션을 열어두면 기록 세션이 쓰는
    # 연결과 둘이 서로를 기다릴 여지가 생긴다.
    connection = db.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        acquired = connection.exec_driver_sql(
            "SELECT GET_LOCK(%s, %s)", (name, APPEND_LOCK_TIMEOUT_SECONDS)
        ).scalar()
        if acquired != 1:
            raise AppendLockTimeout(
                f"could not acquire {name} in {APPEND_LOCK_TIMEOUT_SECONDS}s"
            )
        try:
            yield
        finally:
            # 커밋이 끝난 **뒤에** 푼다 — 순서가 반대면 다음 기록이 아직 안 보이는
            # 꼬리를 읽어서 같은 유실이 그대로 돌아온다.
            connection.exec_driver_sql("SELECT RELEASE_LOCK(%s)", (name,))
    finally:
        connection.close()


# ruff PLR0913(인자 5개 제한)을 끄지 않고 행 내용을 한 덩어리로 받는다 — 어차피
# 호출부(서비스)가 한 행을 만들어 넘기는 자리라 묶는 게 더 읽기 쉽다.
def append(row: AccessLog, hash_row) -> AccessLog:
    """행 하나를 체인 끝에 붙여 커밋한다.

    `row` 는 `prev_hash`/`hash` 만 비어 있는 행이고, `hash_row(row)` 가 해시를
    계산하는 함수다 — 해시 규칙은 서비스가 들고 있고(점검 CLI 가 같은 함수로 다시
    계산한다) 리포지토리는 "직전 행을 읽어서 붙인다" 만 한다.
    """
    with _chain_lock():
        # 격리 수준이 READ COMMITTED 라(app/config.py) 락을 잡은 뒤의 이 SELECT 는
        # 앞 기록이 커밋한 꼬리를 그대로 본다. 모델의 `prev_hash`/`hash` 유니크는
        # 그래도 남겨둔다 — 앱을 거치지 않은 INSERT 까지 DB 가 막는 마지막 선이다.
        previous = db.session.query(AccessLog).order_by(AccessLog.id.desc()).first()
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
