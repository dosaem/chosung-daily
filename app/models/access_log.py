from datetime import datetime

from app.extensions import db


class AccessLog(db.Model):
    """개인정보 처리 행위 한 건의 접속기록(감사 로그).

    근거: **개인정보의 안전성 확보조치 기준**(개인정보보호위원회 고시 제2023-6호)
    제8조(접속기록의 보관 및 점검) — ① 1년 이상 보관 ② 월 1회 이상 점검
    ③ 위·변조·도난·분실 방지. 남기는 항목은 고시의 "접속기록" 정의(식별자·접속
    일시·접속지 정보·처리한 정보주체 정보·수행업무)에 맞췄다.

    **한 번 쓰면 고치지 않는다.** `updated_at` 이 없고 리포지토리에 update/delete
    함수도 없다(`app/repositories/access_log_repository.py`) — 만료 삭제만
    Beat 작업이 한다. 그래서 `prev_hash`/`hash` 가 SHA-256 체인을 이룬다: 앱을
    거치지 않고 행을 바꾸거나 지우면 `flask access-log verify` 가 그 지점을 찍는다.

    `actor` 에 전체 이메일을 넣지 않는다(운영자는 `h***@dosaem.com`, 플레이어는
    `guest.<id>`) — 로그에 개인정보를 최소로 남기는 기존 원칙을 따르면서 "누가"
    를 가려낼 수 있는 선이다.
    """

    __tablename__ = "access_log"

    id: int = db.Column(db.Integer, primary_key=True)
    # 초 단위다. MySQL DATETIME 은 기본 소수점 자리가 없어서, 마이크로초를 담은
    # 값으로 해시를 만들면 저장된 행에서 다시 계산한 해시가 달라진다.
    occurred_at: datetime = db.Column(db.DateTime, nullable=False, index=True)
    actor: str = db.Column(db.String(191), nullable=False)
    # IPv6 최대 길이(45자)까지 받는다.
    remote_ip: str = db.Column(db.String(45), nullable=False)
    action: str = db.Column(db.String(64), nullable=False, index=True)
    # 행위의 대상 식별자(단어 id, 배정 날짜 등). 대상이 없는 행위는 비어 있다.
    target: str | None = db.Column(db.String(191), nullable=True)
    # success / denied(401·403) / error. 상태 코드도 같이 남겨서 점검 때 "거부"
    # 와 "오류" 를 세는 기준이 글자열 해석에 의존하지 않게 한다.
    result: str = db.Column(db.String(16), nullable=False)
    status_code: int = db.Column(db.Integer, nullable=False)
    # 체인이 갈라지지 않게 **DB 가** 막는다: 한 해시를 두 행이 가리킬 수 없다.
    # 동시에 들어온 두 요청을 한 줄로 세우는 건 리포지토리의 네임드 락이고, 이
    # 유니크는 앱을 거치지 않은 INSERT 까지 막는 마지막 선이다 — 체인이 조용히
    # 두 갈래로 갈리는 쪽보다 INSERT 가 깨지는 쪽이 낫다.
    prev_hash: str = db.Column(db.String(64), nullable=False, unique=True)
    hash: str = db.Column(db.String(64), nullable=False, unique=True)
