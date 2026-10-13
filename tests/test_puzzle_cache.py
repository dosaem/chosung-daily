import json

from app.extensions import get_redis
from app.models import DailyPuzzle, Word


def test_today_populates_cache_on_miss(client, guest_headers, today_puzzle):
    key = f"puzzle:{today_puzzle.puzzle_date.isoformat()}:ko"
    assert get_redis().get(key) is None

    res = client.get("/api/v1/puzzles/today", headers=guest_headers)
    assert res.status_code == 200

    cached = json.loads(get_redis().get(key))
    assert cached["chosung"] == "ㅅㄱ"
    assert cached["answer"] == "사과"


def test_today_uses_cache_hit_even_if_db_row_is_gone(client, guest_headers, today_puzzle, session):
    # 캐시를 먼저 채운다
    client.get("/api/v1/puzzles/today", headers=guest_headers)

    # DB에서 word/puzzle을 지워도 캐시에서 그대로 읽혀야 한다 (캐시 히트 경로 확인용).
    session.query(DailyPuzzle).delete()
    session.query(Word).delete()
    session.commit()

    res = client.get("/api/v1/puzzles/today", headers=guest_headers)
    body = res.get_json()
    assert res.status_code == 200
    assert body["chosung"] == "ㅅㄱ"
