from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class LeaderboardEntry(BaseModel):
    rank: int
    guest_id: int
    attempts: int
    solved_in_seconds: int
    is_me: bool


class LeaderboardResponse(BaseModel):
    date: date
    language: PuzzleLanguage
    entries: list[LeaderboardEntry]
