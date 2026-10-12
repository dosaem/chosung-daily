from flask import Blueprint, jsonify

from app.schemas.guest import GuestResponse
from app.services.guest_service import issue_guest

bp = Blueprint("guests", __name__)


@bp.post("/guests")
def create_guest():
    guest = issue_guest()
    return jsonify(GuestResponse(token=guest.token).model_dump(mode="json")), 201
