from datetime import datetime

from app.extensions import db
from app.utils.time import utcnow


class AppleRevocationRetry(db.Model):
    """애플 연결 철회(revoke)가 실패해서 다시 시도해야 하는 토큰 한 건.

    계정 삭제는 애플 응답을 기다려주지 않는다(스펙 §A.7) — 애플이 안 받아줘도
    플레이어의 데이터는 그 자리에서 지워지고, 철회만 이 테이블로 미뤄진다.
    그래서 `guest_id` 가 없다: 참조할 게스트 행이 이미 사라졌다. 철회에 실제로
    필요한 건 "토큰" 과 "그 토큰을 발급한 client" 둘뿐이다(Account 의 같은 두
    컬럼과 같은 짝).

    토큰은 `Account.provider_refresh_token` 과 **같은 암호문 그대로** 옮긴다 —
    지우는 길에 평문으로 바꿔 들고 있으면 암호화의 의미가 없다.
    """

    __tablename__ = "apple_revocation_retry"

    id: int = db.Column(db.Integer, primary_key=True)
    refresh_token_enc: str = db.Column(db.Text, nullable=False)
    client_id: str = db.Column(db.String(191), nullable=False)
    # 7일 폐기 기준점(스펙 §A.7). 실패해도 이 값은 그대로 둔다 — "언제부터 못
    # 지웠나" 가 기준이고, 마지막 시도 시각이 기준이면 폐기가 영원히 안 온다.
    created_at: datetime = db.Column(db.DateTime, nullable=False, default=utcnow)
