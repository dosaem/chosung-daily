import json
from dataclasses import dataclass
from datetime import date

from app.models import DailyPuzzle, PuzzleLanguage, WordCategory
from app.utils.mask import MaskTile
from app.utils.redis_safe import safe_redis_call

# 날짜·언어별로 키가 갈리기 때문에(puzzle:2026-10-12:ko) TTL이 정확히 자정에 맞을
# 필요는 없다 — 지나간 날짜의 키는 그냥 다시 조회될 일이 없다. 26시간은 메모리
# 정리용 여유값일 뿐이다.
CACHE_TTL_SECONDS = 60 * 60 * 26


@dataclass
class CachedWord:
    chosung: str
    answer: str
    hint: str
    category: WordCategory
    mask: list[MaskTile]


@dataclass
class CachedPuzzle:
    """DailyPuzzle ORM과 같은 속성(id, puzzle_date, language, word.*)을 노출해서,
    호출부(puzzle_service, guess_service)가 캐시 히트/미스를 구분할 필요가
    없게 한다."""

    id: int
    puzzle_date: date
    language: PuzzleLanguage
    word: CachedWord


def _cache_key(puzzle_date: date, language: PuzzleLanguage) -> str:
    """같은 날 ko/en 퍼즐이 공존하므로 키에 언어가 들어간다."""
    return f"puzzle:{puzzle_date.isoformat()}:{language.value}"


def get_cached_puzzle(puzzle_date: date, language: PuzzleLanguage) -> CachedPuzzle | None:
    raw = safe_redis_call("get", _cache_key(puzzle_date, language))
    if raw is None:
        return None

    data = json.loads(raw)
    return CachedPuzzle(
        id=data["id"],
        puzzle_date=puzzle_date,
        language=language,
        word=CachedWord(
            chosung=data["chosung"],
            answer=data["answer"],
            hint=data["hint"],
            category=WordCategory(data["category"]),
            mask=data["mask"],
        ),
    )


def invalidate_cached_puzzle(puzzle_date: date, language: PuzzleLanguage) -> None:
    """그 날짜·언어 캐시를 버린다. 다음 조회가 DB 에서 다시 읽어 채운다.

    TTL(26시간)만 믿으면 배정된 단어를 고쳐도 당일 내내 옛 값이 나간다 — 저장하는
    쪽(`word_service.update_word`)이 고친 퍼즐의 키를 지워줘야 한다. Redis 가 죽어
    있으면 `safe_redis_call` 이 조용히 넘어가고, 캐시는 TTL 로 결국 사라진다.
    """
    safe_redis_call("delete", _cache_key(puzzle_date, language))


def cache_puzzle(puzzle: DailyPuzzle) -> None:
    payload = json.dumps(
        {
            "id": puzzle.id,
            "chosung": puzzle.word.chosung,
            "answer": puzzle.word.answer,
            "hint": puzzle.word.hint,
            "category": puzzle.word.category.value,
            "mask": puzzle.word.mask,
        }
    )
    safe_redis_call(
        "set",
        _cache_key(puzzle.puzzle_date, puzzle.language),
        payload,
        ex=CACHE_TTL_SECONDS,
    )
