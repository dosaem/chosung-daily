from pydantic import BaseModel, Field


class GuessRequest(BaseModel):
    guess: str = Field(min_length=1, max_length=50)


class GuessResponse(BaseModel):
    is_correct: bool
    feedback: list[bool] | None = None
    attempts_left: int
    hint: str | None = None
    answer: str | None = None
