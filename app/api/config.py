from flask import Blueprint, jsonify

from app.services.app_config_service import get_app_config

bp = Blueprint("config", __name__)


@bp.get("/config")
def app_config():
    return jsonify(get_app_config().model_dump(mode="json"))
