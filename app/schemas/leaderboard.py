from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class LeaderboardEntry(BaseModel):
    rank: int
    display: str
    attempts: int
    seconds: int
    is_me: bool


class MyRank(BaseModel):
    """내 순위만 따로 — 페이지(limit) 밖이어도 내 위치를 보여주기 위한 필드."""

    rank: int
    attempts: int
    seconds: int


class LeaderboardResponse(BaseModel):
    date: date
    language: PuzzleLanguage
    entries: list[LeaderboardEntry]
    me: MyRank | None
