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
