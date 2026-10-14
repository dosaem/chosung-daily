from flask import jsonify
from pydantic import ValidationError as PydanticValidationError


class AppError(Exception):
    """도메인 예외 베이스. Spring의 커스텀 Exception + @ControllerAdvice 역할."""

    code = "INTERNAL_ERROR"
    status_code = 500
    message = "서버 오류가 발생했습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    message = "요청한 리소스를 찾을 수 없습니다."


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "인증이 필요합니다."


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    message = "권한이 없습니다."


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400
    message = "요청 값이 올바르지 않습니다."


class NoPuzzleTodayError(AppError):
    code = "NO_PUZZLE_TODAY"
    status_code = 404
    message = "오늘의 퍼즐이 아직 준비되지 않았습니다."


class AlreadyFinishedError(AppError):
    code = "ALREADY_FINISHED"
    status_code = 409
    message = "이미 종료된 퍼즐입니다."


class PuzzleChangedError(AppError):
    code = "PUZZLE_CHANGED"
    status_code = 409
    message = "퍼즐이 바뀌었어요. 새로고침해주세요."


class RateLimitedError(AppError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "제출이 너무 많습니다. 잠시 후 다시 시도해주세요."


class AccountAlreadyLinkedError(AppError):
    code = "ACCOUNT_ALREADY_LINKED"
    status_code = 409
    message = "이미 다른 계정이 연결된 게스트입니다."


class InvalidIdTokenError(AppError):
    code = "INVALID_ID_TOKEN"
    status_code = 401
    message = "로그인 정보를 확인할 수 없습니다. 다시 시도해주세요."


class OAuthProviderUnavailableError(AppError):
    code = "OAUTH_PROVIDER_UNAVAILABLE"
    status_code = 503
    message = "이 로그인 방식은 아직 설정되지 않았습니다."


class ReceiptInvalidError(AppError):
    code = "RECEIPT_INVALID"
    status_code = 400
    message = "영수증을 확인할 수 없습니다."


class StoreUnavailableError(AppError):
    """스토어 쪽 장애·설정 누락. 영수증이 틀린 게 아니라 "지금은 모른다" 라서
    앱이 나중에 다시 올려야 한다 — 그래서 400 이 아니라 503 이다."""

    code = "STORE_UNAVAILABLE"
    status_code = 503
    message = "스토어 확인에 실패했습니다. 잠시 후 다시 시도해주세요."


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({"code": err.code, "message": err.message}), err.status_code

    @app.errorhandler(PydanticValidationError)
    def handle_pydantic_error(err: PydanticValidationError):
        return jsonify({"code": "VALIDATION_ERROR", "message": str(err)}), 400

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify({"code": "NOT_FOUND", "message": "요청한 경로를 찾을 수 없습니다."}), 404

    @app.errorhandler(500)
    def handle_500(_err):
        return jsonify({"code": "INTERNAL_ERROR", "message": "서버 오류가 발생했습니다."}), 500
