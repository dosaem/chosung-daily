from functools import wraps

from flask import g

from app.errors import RateLimitedError
from app.utils.redis_safe import safe_redis_call

GUESS_RATE_LIMIT = 10
GUESS_RATE_WINDOW_SECONDS = 60


def rate_limited(view):
    """게스트당 분당 GUESS_RATE_LIMIT회. `@with_guest` 뒤에 붙여서 g.guest를 쓴다.

    고정 윈도우(fixed window) 방식이다 — 게스트가 "처음" 요청한 시점부터 60초
    단위로 카운터가 리셋된다. 그래서 윈도우 경계에서 짧은 순간(예: 59.9초에
    10번 + 60.1초에 또 10번) 실질적으로 분당 10회보다 더 통과할 수 있다. 슬라이딩
    윈도우보다 구현이 단순하고, rate limit은 "악의적 스팸 방지"가 목적이라 이
    경계 케이스 정도의 오차는 감수하기로 했다(사용자 체감에는 영향 없음).

    Redis가 없거나 호출이 실패하면 제한 없이 통과시킨다(fail-open) — rate limit은
    보호 기능이지 게임 자체의 일부가 아니라서, "Redis 장애 시 게임 자체(조회/제출)는
    DB로 동작한다"는 스펙 규칙을 "제출"의 일부인 이 체크에도 그대로 적용한다.
    """

    @wraps(view)
    def wrapper(*args, **kwargs):
        key = f"ratelimit:guess:{g.guest.id}"
        count = safe_redis_call("incr", key)
        if count is None:
            return view(*args, **kwargs)

        if count == 1:
            safe_redis_call("expire", key, GUESS_RATE_WINDOW_SECONDS)

        if count > GUESS_RATE_LIMIT:
            raise RateLimitedError()

        return view(*args, **kwargs)

    return wrapper
