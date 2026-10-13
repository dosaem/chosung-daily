from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.api.rate_limit import rate_limited
from app.errors import ValidationError
from app.models import Guest, PuzzleLanguage
from app.schemas.guess import GuessRequest
from app.services.guess_service import submit_guess
from app.services.puzzle_metrics import get_today_leaderboard, get_today_stats
from app.services.puzzle_service import get_today_puzzle_or_404, get_today_puzzle_view

bp = Blueprint("puzzles", __name__)


def _requested_language(guest: Guest) -> PuzzleLanguage:
    """`?language=` 가 있으면 그 언어, 없으면 게스트 선호 언어.

    통계·리더보드는 "내가 안 고른 언어의 집계"도 볼 수 있어야 해서(앱 기록 화면)
    쿼리 파라미터로 언어를 명시할 수 있다. 퍼즐 조회는 반대로 선호 언어 하나만
    돌려준다 — 플레이 중인 퍼즐이 요청마다 달라지면 안 된다.
    """
    raw = request.args.get("language")
    if raw is None:
        return guest.puzzle_language
    try:
        return PuzzleLanguage(raw)
    except ValueError:
        raise ValidationError(f"지원하지 않는 퍼즐 언어입니다: {raw}") from None


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
    language = _requested_language(g.guest)
    puzzle = get_today_puzzle_or_404(language)
    result = get_today_stats(puzzle.puzzle_date, language)
    return jsonify(result.model_dump(mode="json"))


@bp.get("/puzzles/today/leaderboard")
@with_guest
def leaderboard():
    limit = request.args.get("limit", default=20, type=int)
    language = _requested_language(g.guest)
    puzzle = get_today_puzzle_or_404(language)
    result = get_today_leaderboard(puzzle.puzzle_date, language, limit, g.guest.id)
    return jsonify(result.model_dump(mode="json"))
