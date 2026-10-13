from flask import Blueprint, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.utils.redis_safe import safe_redis_call

bp = Blueprint("health", __name__)

# 업타임 모니터(UptimeRobot)가 보는 등급. DB 가 죽으면 게임 자체가 안 되니
# 503 으로 깨우고, Redis 만 죽으면 캐시·랭킹·통계만 빠진 채 게임은 돌아가니
# 200 + degraded 로 알린다 (스펙 §C.29, README "설계 판단" 08 참고).
_OK = "ok"
_DOWN = "down"
_DEGRADED = "degraded"


@bp.get("/health")
def health():
    db_ok = _db_ok()
    redis_ok = safe_redis_call("ping", default=False) is True

    if not db_ok:
        status = _DOWN
    elif not redis_ok:
        status = _DEGRADED
    else:
        status = _OK

    body = {
        "status": status,
        "db": _OK if db_ok else _DOWN,
        "redis": _OK if redis_ok else _DOWN,
        # 애플 client_secret(JWT) 만료 시각. 요청 경로 갱신(스펙 §A.13)을 넣는
        # 티켓 11 에서 채운다 — 그때까지는 null 로 둔다.
        "apple_secret_expires_at": None,
    }
    return jsonify(body), 200 if db_ok else 503


def _db_ok() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
