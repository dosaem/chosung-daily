import hashlib
import secrets
from functools import wraps

from flask import current_app, request, session

from app.errors import ForbiddenError
from app.utils.redis_safe import safe_redis_call

# 세션에 토큰을 담는 키와, 폼 hidden input 의 name. 양쪽 이름이 같아도 되지만
# 쓰는 자리가 다르니 상수를 따로 둔다 (템플릿은 FORM_FIELD 만 안다).
SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"

_USED_TOKEN_KEY_PREFIX = "csrf:used:"


def _used_token_key(token: str) -> str:
    """소비 기록용 Redis 키. 토큰 원문이 아니라 해시를 키로 쓴다.

    원문을 키로 쓰면 `KEYS`·`MONITOR`·슬로우로그 같은 운영 경로에 아직 유효한
    토큰이 그대로 남는다. "이 토큰이 이미 쓰였나" 판정에는 해시만 있으면 된다.
    """
    return _USED_TOKEN_KEY_PREFIX + hashlib.sha256(token.encode()).hexdigest()


def _claim_token(token: str) -> bool:
    """토큰을 "지금 내가 쓴다" 고 서버에 못 박는다. 처음 쓰는 토큰일 때만 True.

    `SET NX` 는 "없을 때만 쓰기" 를 Redis 왕복 한 번의 원자적 연산으로 한다 —
    `exists` 로 확인한 뒤 `set` 하는 2단계로 쪼개면 동시에 들어온 중복 제출 둘이
    모두 "아직 안 썼다" 를 보고 둘 다 통과한다.

    TTL 은 `PERMANENT_SESSION_LIFETIME`. Flask 는 세션 쿠키를 풀 때 이 값을
    `max_age` 로 검사하므로(`SecureCookieSessionInterface.open_session`), 그보다
    오래된 쿠키는 서명이 맞아도 세션 자체가 안 열린다. 즉 이 시간이 지나면 그
    토큰을 담은 쿠키로는 애초에 인증이 안 돼서 소비 기록을 더 들고 있을 이유가 없다.

    Redis 가 없거나 장애면 `safe_redis_call` 이 `None` 을 돌려주고, 이 함수는
    False(= 통과 불가) 가 된다. 1회용 보장을 못 지키는 상태에서 통과시키는 것보다
    403 으로 막는 쪽을 택했다 — 이 데코레이터를 쓰는 건 계정 삭제·운영자 폼이라,
    "안 지워졌다" 보다 "두 번 지워졌다" 가 훨씬 비싸다.
    """
    ttl_seconds = int(current_app.permanent_session_lifetime.total_seconds())
    claimed = safe_redis_call("set", _used_token_key(token), "1", nx=True, ex=ttl_seconds)
    return bool(claimed)


def issue_csrf_token() -> str:
    """세션에 1회용 토큰을 심고 그 값을 돌려준다. 폼 hidden 값으로 쓴다.

    폼을 그릴 때마다 새 토큰으로 덮는다 — 한 브라우저가 폼 두 개를 동시에 열면
    나중에 그린 폼만 유효하다. 계정 삭제·운영자 폼처럼 한 번에 하나씩 쓰는
    화면만 이 헬퍼를 쓰므로 토큰 하나로 충분하다(폼별 토큰 보관은 과하다).

    발급은 Redis 를 건드리지 않는다 — 소비 기록만 서버에 남기면 되고, 폼을 그리는
    GET 이 Redis 장애 때문에 500 이 되면 안 된다.
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
    삭제 POST 가 두 번 들어가는 걸 막는다. 세션에서 지우는 것만으로는 부족하다:
    서명 쿠키 세션은 상태가 전부 클라이언트에 있어서, `session.pop` 은 응답
    Set-Cookie 를 바꿀 뿐이고 브라우저·프록시가 들고 있던 **옛 쿠키를 그대로 다시
    보내면 토큰이 되살아난다**(동시 제출은 애초에 다 같은 옛 쿠키를 들고 온다).
    그래서 소비 사실은 Redis 에 원자적으로 기록하고, 세션 pop 은 옛 토큰을 계속
    실어 보내지 않기 위한 정리로만 남긴다.

    실패한 요청은 세션 토큰을 건드리지 않는다: 틀린 값을 던지는 요청이 사용자가
    열어둔 폼을 무효화하면 안 된다.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = session.get(SESSION_KEY)
        submitted = request.form.get(CSRF_FORM_FIELD, "")
        # bytes 로 비교한다 — compare_digest 는 비 ASCII 문자가 든 str 을 받으면
        # TypeError 를 내서, 아무 값이나 넣은 폼이 403 대신 500 이 돼버린다.
        if not expected or not secrets.compare_digest(expected.encode(), submitted.encode()):
            raise ForbiddenError()

        if not _claim_token(expected):
            raise ForbiddenError()

        session.pop(SESSION_KEY, None)
        return view(*args, **kwargs)

    return wrapper
