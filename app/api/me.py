from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.errors import ValidationError
from app.schemas.guest import PuzzleLanguageRequest, PuzzleLanguageResponse
from app.services.guest_service import change_puzzle_language
from app.services.stats_service import (
    DEFAULT_HISTORY_DAYS,
    MAX_HISTORY_DAYS,
    get_my_history,
    get_my_stats,
)

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


def _requested_days() -> int:
    """`?days=` 를 1..MAX_HISTORY_DAYS 안의 정수로 읽는다. 없으면 기본 7일.

    범위를 벗어나면 조용히 자르지 않고 400 을 돌려준다 — 클라이언트가 60일을
    요청했는데 31일이 오면, 빈 칸이 생긴 건지 상한에 걸린 건지 구분할 수 없다.
    """
    raw = request.args.get("days")
    if raw is None:
        return DEFAULT_HISTORY_DAYS
    try:
        days = int(raw)
    except ValueError:
        raise ValidationError(f"days 는 정수여야 합니다: {raw}") from None
    if not 1 <= days <= MAX_HISTORY_DAYS:
        raise ValidationError(f"days 는 1 이상 {MAX_HISTORY_DAYS} 이하여야 합니다: {days}")
    return days


@bp.get("/me/history")
@with_guest
def my_history():
    history = get_my_history(g.guest, _requested_days())
    return jsonify([day.model_dump(mode="json") for day in history])
