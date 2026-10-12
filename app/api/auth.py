from functools import wraps

from flask import g, request

from app.errors import UnauthorizedError
from app.services.guest_service import get_guest_by_token


def with_guest(view):
    """Authorization: Bearer <token> 를 파싱해 g.guest에 넣는다.

    Spring의 인증 인터셉터/필터 대응. 뷰 함수는 g.guest만 믿고 쓰면 된다.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise UnauthorizedError("Authorization: Bearer <token> 헤더가 필요합니다.")

        token = header.removeprefix("Bearer ").strip()
        guest = get_guest_by_token(token)
        if guest is None:
            raise UnauthorizedError("유효하지 않은 토큰입니다.")

        g.guest = guest
        return view(*args, **kwargs)

    return wrapper
