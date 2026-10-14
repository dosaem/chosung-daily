from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage
from app.schemas.subscription import EntitlementResponse


class LinkedAccount(BaseModel):
    provider: str
    email: str | None


class MyStatsResponse(BaseModel):
    puzzle_language: PuzzleLanguage
    current_streak: int
    max_streak: int
    solved_count: int
    linked_account: LinkedAccount | None
    # 광고를 끌지 말지. 앱은 이 응답을 받을 때마다 광고 상태를 맞추고,
    # `next_check_at` 에 타이머를 걸어 다시 부른다(스펙 §A.8).
    entitlement: EntitlementResponse


class TodayStatsResponse(BaseModel):
    date: date
    language: PuzzleLanguage
    total_solved: int
    by_attempt: dict[str, float]  # "1".."5" -> 그 시도 횟수에 맞춘 비율(0~1)
