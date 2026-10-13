from pydantic import BaseModel, Field


class GuessRequest(BaseModel):
    # 퍼즐 고정(CONTEXT.md "퍼즐 고정"). 필수지만 pydantic 필수 필드로 두지 않는다 —
    # 빠진 요청은 400 VALIDATION_ERROR 가 아니라 409 PUZZLE_CHANGED 여야 하고
    # (클라이언트가 할 일은 "새로고침" 하나로 같다), 그 판정은 서비스가 한다.
    puzzle_id: int | None = None
    guess: str = Field(min_length=1, max_length=50)


class GuessResponse(BaseModel):
    is_correct: bool
    feedback: list[bool] | None = None
    attempts_left: int
    hint: str | None = None
    answer: str | None = None
