from pydantic import BaseModel


class MyStatsResponse(BaseModel):
    current_streak: int
    max_streak: int
    solved_count: int
