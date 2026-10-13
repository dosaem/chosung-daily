from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class LinkedAccount(BaseModel):
    provider: str
    email: str | None


class MyStatsResponse(BaseModel):
    puzzle_language: PuzzleLanguage
    current_streak: int
    max_streak: int
    solved_count: int
    linked_account: LinkedAccount | None


class TodayStatsResponse(BaseModel):
    date: date
    language: PuzzleLanguage
    total_solved: int
    by_attempt: dict[str, float]  # "1".."5" -> 그 시도 횟수에 맞춘 비율(0~1)
