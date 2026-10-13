from app.extensions import db
from app.models import AppSetting


def find_all_settings() -> dict[str, str]:
    """설정 행 전체를 키→값 dict 로 읽는다.

    행이 열 개도 안 되는 테이블이라 키 하나씩 조회하는 대신 한 번에 읽는다 —
    /config 가 모든 키를 같이 쓰기 때문에 쿼리도 한 번이면 끝난다.
    """
    return {row.key: row.value for row in db.session.query(AppSetting).all()}
