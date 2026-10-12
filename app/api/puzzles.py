from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.schemas.guess import GuessRequest
from app.services.guess_service import submit_guess
from app.services.puzzle_service import get_today_puzzle_view

bp = Blueprint("puzzles", __name__)


@bp.get("/puzzles/today")
@with_guest
def today():
    view = get_today_puzzle_view(g.guest)
    return jsonify(view.model_dump(mode="json"))


@bp.post("/puzzles/today/guesses")
@with_guest
def guess():
    payload = GuessRequest.model_validate(request.get_json(silent=True) or {})
    result = submit_guess(g.guest, payload.guess)
    return jsonify(result.model_dump(mode="json"))
