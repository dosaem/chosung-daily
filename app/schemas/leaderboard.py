from datetime import date

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    guest_id: int
    attempts: int
    solved_in_seconds: int
    is_me: bool


class LeaderboardResponse(BaseModel):
    date: date
    entries: list[LeaderboardEntry]
