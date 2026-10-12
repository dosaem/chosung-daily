from flask import jsonify


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


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({"code": err.code, "message": err.message}), err.status_code

    @app.errorhandler(404)
    def handle_404(_err):
        return jsonify({"code": "NOT_FOUND", "message": "요청한 경로를 찾을 수 없습니다."}), 404

    @app.errorhandler(500)
    def handle_500(_err):
        return jsonify({"code": "INTERNAL_ERROR", "message": "서버 오류가 발생했습니다."}), 500
