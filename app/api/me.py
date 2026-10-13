from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.schemas.guest import PuzzleLanguageRequest, PuzzleLanguageResponse
from app.services.guest_service import change_puzzle_language
from app.services.stats_service import get_my_stats

bp = Blueprint("me", __name__)


@bp.patch("/me")
@with_guest
def update_me():
    payload = PuzzleLanguageRequest.model_validate(request.get_json(silent=True) or {})
    guest = change_puzzle_language(g.guest, payload.puzzle_language)
    response = PuzzleLanguageResponse(puzzle_language=guest.puzzle_language)
    return jsonify(response.model_dump(mode="json"))


@bp.get("/me/stats")
@with_guest
def my_stats():
    stats = get_my_stats(g.guest)
    return jsonify(stats.model_dump(mode="json"))
