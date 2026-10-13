from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import apple_secret_expires_at, db
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
        # 애플 client_secret(JWT) 만료 시각 — 웹 Services ID·앱 번들 ID 중 더 이른
        # 쪽이다(스펙 §A.13). 이 워커 프로세스가 지금 들고 있는 값이라, 요청 경로
        # 갱신이 돌면 150일 뒤로 밀린다. 애플 설정이 없으면 null.
        "apple_secret_expires_at": _apple_secret_expires_at(),
    }
    return jsonify(body), 200 if db_ok else 503


def _apple_secret_expires_at() -> str | None:
    expires_at = apple_secret_expires_at(current_app)
    return expires_at.isoformat() if expires_at else None


def _db_ok() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
