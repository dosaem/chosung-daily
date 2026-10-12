from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.api.rate_limit import rate_limited
from app.schemas.guess import GuessRequest
from app.services.guess_service import submit_guess
from app.services.puzzle_metrics import get_today_leaderboard, get_today_stats
from app.services.puzzle_service import get_today_puzzle_or_404, get_today_puzzle_view

bp = Blueprint("puzzles", __name__)


@bp.get("/puzzles/today")
@with_guest
def today():
    view = get_today_puzzle_view(g.guest)
    return jsonify(view.model_dump(mode="json"))


@bp.post("/puzzles/today/guesses")
@with_guest
@rate_limited
def guess():
    payload = GuessRequest.model_validate(request.get_json(silent=True) or {})
    result = submit_guess(g.guest, payload.guess)
    return jsonify(result.model_dump(mode="json"))


@bp.get("/puzzles/today/stats")
@with_guest
def stats():
    puzzle = get_today_puzzle_or_404()
    result = get_today_stats(puzzle.puzzle_date)
    return jsonify(result.model_dump(mode="json"))


@bp.get("/puzzles/today/leaderboard")
@with_guest
def leaderboard():
    limit = request.args.get("limit", default=20, type=int)
    puzzle = get_today_puzzle_or_404()
    result = get_today_leaderboard(puzzle.puzzle_date, limit, g.guest.id)
    return jsonify(result.model_dump(mode="json"))
