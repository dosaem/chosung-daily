from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class LeaderboardEntry(BaseModel):
    rank: int
    # 언어 중립 익명 태그("a3f1"). "게스트 #"/"Guest #" 는 UI 언어를 아는 쪽이
    # 붙인다 — 서버가 만들면 영어 화면에 한글이 섞인다(README "38.").
    anon_tag: str
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
