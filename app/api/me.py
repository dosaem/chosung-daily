from flask import Blueprint, g, jsonify

from app.api.auth import with_guest
from app.services.stats_service import get_my_stats

bp = Blueprint("me", __name__)


@bp.get("/me/stats")
@with_guest
def my_stats():
    stats = get_my_stats(g.guest)
    return jsonify(stats.model_dump(mode="json"))
