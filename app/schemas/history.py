from datetime import date

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class HistoryDay(BaseModel):
    date: date
    # 퍼즐 언어별 그날의 결과: success | fail | in_progress | none
    results: dict[PuzzleLanguage, str]
