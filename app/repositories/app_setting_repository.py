from app.extensions import db
from app.models import AppSetting


def find_all_settings() -> dict[str, str]:
    """설정 행 전체를 키→값 dict 로 읽는다.

    행이 열 개도 안 되는 테이블이라 키 하나씩 조회하는 대신 한 번에 읽는다 —
    /config 가 모든 키를 같이 쓰기 때문에 쿼리도 한 번이면 끝난다.
    """
    return {row.key: row.value for row in db.session.query(AppSetting).all()}


def save_settings(values: dict[str, str]) -> None:
    """키→값 여러 개를 한 커밋으로 upsert 한다. 없던 키는 만든다.

    키가 네 개뿐이라(점검 2 + 최소 버전 2) 운영자가 폼을 저장하면 네 개를 한꺼번에
    쓴다 — 일부만 반영된 설정(점검은 켜졌는데 메시지는 옛 값)이 생기지 않게
    `save_operator_settings` 의 커밋 하나에 묶는다.
    """
    existing = {row.key: row for row in db.session.query(AppSetting).all()}
    for key, value in values.items():
        row = existing.get(key)
        if row is None:
            db.session.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.session.commit()
