from datetime import date

from pydantic import BaseModel


class MyStatsResponse(BaseModel):
    current_streak: int
    max_streak: int
    solved_count: int


class TodayStatsResponse(BaseModel):
    date: date
    total_solved: int
    by_attempt: dict[str, float]  # "1".."5" -> 그 시도 횟수에 맞춘 비율(0~1)
