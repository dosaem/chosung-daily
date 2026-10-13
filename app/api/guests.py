from flask import Blueprint, jsonify, request

from app.schemas.guest import GuestCreateRequest, GuestResponse
from app.services.guest_service import issue_guest

bp = Blueprint("guests", __name__)


@bp.post("/guests")
def create_guest():
    payload = GuestCreateRequest.model_validate(request.get_json(silent=True) or {})
    guest = issue_guest(payload.puzzle_language)
    return jsonify(GuestResponse(token=guest.token).model_dump(mode="json")), 201
