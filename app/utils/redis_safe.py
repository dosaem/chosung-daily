import logging

from redis.exceptions import RedisError

from app.extensions import get_redis

logger = logging.getLogger(__name__)


def safe_redis_call(method_name: str, *args, default=None, **kwargs):
    """Redis 클라이언트의 메서드를 이름(문자열)으로 호출한다.

    Redis가 설정 안 됐거나 장애여도 예외를 안 올리고 default를 돌려준다 —
    스펙 요구사항("Redis 장애 시 게임 자체는 DB로 동작, 랭킹·통계만 실패")을
    이 함수 하나로 구현한다.

    메서드를 이름으로 받는 이유: `redis_client.hincrby`처럼 메서드를 먼저
    참조하면 redis_client가 None일 때 그 참조 자체가 AttributeError를 던진다.
    그러면 호출부마다 "먼저 get_redis()로 None 체크"를 따로 반복해야 하는데,
    여기서 get_redis()를 직접 하면 호출부의 반복되는 가드가 전부 없어진다.
    """
    client = get_redis()
    if client is None:
        return default
    try:
        return getattr(client, method_name)(*args, **kwargs)
    except RedisError:
        logger.warning("Redis 호출 실패(%s), 폴백으로 진행", method_name, exc_info=True)
        return default
