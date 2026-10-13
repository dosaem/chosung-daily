import secrets
from functools import wraps

from flask import request, session

from app.errors import ForbiddenError

# 세션에 토큰을 담는 키와, 폼 hidden input 의 name. 양쪽 이름이 같아도 되지만
# 쓰는 자리가 다르니 상수를 따로 둔다 (템플릿은 FORM_FIELD 만 안다).
SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def issue_csrf_token() -> str:
    """세션에 1회용 토큰을 심고 그 값을 돌려준다. 폼 hidden 값으로 쓴다.

    폼을 그릴 때마다 새 토큰으로 덮는다 — 한 브라우저가 폼 두 개를 동시에 열면
    나중에 그린 폼만 유효하다. 계정 삭제·운영자 폼처럼 한 번에 하나씩 쓰는
    화면만 이 헬퍼를 쓰므로 토큰 하나로 충분하다(폼별 토큰 보관은 과하다).
    """
    token = secrets.token_urlsafe(32)
    session[SESSION_KEY] = token
    return token


def csrf_protected(view):
    """폼 hidden 토큰이 세션 토큰과 같을 때만 통과시킨다. 불일치면 403 FORBIDDEN.

    쿠키 세션만으로 인증하는 웹 폼(계정 삭제·운영자 화면)은 다른 사이트가 만든
    POST 에도 쿠키가 실릴 수 있어서, "이 폼을 우리가 그려줬다" 는 증거를 하나
    더 요구한다. `SESSION_COOKIE_SAMESITE` 가 애플 로그인 때문에 프로덕션에서
    `None` 으로 풀려 있어(app/config.py) 쿠키 설정만으로는 막을 수 없다.

    검증에 성공한 토큰은 즉시 버린다(1회용) — 브라우저 새로고침으로 같은
    삭제 POST 가 두 번 들어가는 걸 막는다. 실패한 요청은 세션 토큰을 건드리지
    않는다: 틀린 값을 던지는 요청이 사용자가 열어둔 폼을 무효화하면 안 된다.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = session.get(SESSION_KEY)
        submitted = request.form.get(CSRF_FORM_FIELD, "")
        # bytes 로 비교한다 — compare_digest 는 비 ASCII 문자가 든 str 을 받으면
        # TypeError 를 내서, 아무 값이나 넣은 폼이 403 대신 500 이 돼버린다.
        if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
            raise ForbiddenError()

        session.pop(SESSION_KEY, None)
        return view(*args, **kwargs)

    return wrapper
