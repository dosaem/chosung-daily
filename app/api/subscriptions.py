from flask import Blueprint, g, jsonify, request

from app.api.auth import with_guest
from app.schemas.subscription import VerifyReceiptRequest
from app.services.subscription_service import verify_receipt

bp = Blueprint("subscriptions", __name__)


@bp.post("/subscriptions/verify")
@with_guest
def verify():
    """앱이 스토어에서 받은 영수증을 올리는 자리. 응답을 받은 뒤에야 앱이
    구매를 완료 처리한다(스펙 §A.8) — 그래서 실패를 400(영수증 잘못)과
    503(스토어 장애)으로 갈라 줘야 앱이 "다시 올릴지" 를 판단할 수 있다."""
    payload = VerifyReceiptRequest.model_validate(request.get_json(silent=True) or {})
    entitlement = verify_receipt(g.guest, payload.store, payload.receipt)
    return jsonify(entitlement.model_dump(mode="json"))
