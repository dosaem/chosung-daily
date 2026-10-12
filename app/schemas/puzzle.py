from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.models.enums import WordCategory


class TodayPuzzleResponse(BaseModel):
    date: date
    chosung: str
    length: int
    category: WordCategory
    attempts_left: int
    status: Literal["in_progress", "success", "fail"]
    hint: str | None = None
    answer: str | None = None
