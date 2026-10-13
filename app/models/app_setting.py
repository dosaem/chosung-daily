from datetime import datetime

from app.extensions import db
from app.utils.time import utcnow


class AppSetting(db.Model):
    """운영자가 재배포 없이 바꾸는 설정 한 줄 (점검 모드, 최소 앱 버전).

    키·값 테이블 하나로 둔 이유는 README "설계 판단" 의 08 항목 참고. 어떤 키가
    쓰이는지와 기본값은 app/services/app_config_service.py 가 들고 있다.
    """

    __tablename__ = "app_setting"

    # `key` 는 MySQL 예약어(KEY)라 컬럼 이름만 setting_key 로 두고, 코드에선 key 로 쓴다.
    key: str = db.Column("setting_key", db.String(60), primary_key=True)
    value: str = db.Column(db.String(500), nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
