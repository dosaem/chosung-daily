from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.models.enums import PuzzleLanguage, WordCategory
from app.utils.mask import MaskTile


class AttemptView(BaseModel):
    """시도 이력 한 행. 구분자를 뺀 글자열과 같은 길이의 피드백이다(spec §A.2)."""

    guess: str
    feedback: list[bool]


class TodayPuzzleResponse(BaseModel):
    puzzle_id: int
    date: date
    language: PuzzleLanguage
    # 플레이어가 보는 문제 그 자체. 언어와 무관하게 같은 포맷이다(app/utils/mask.py).
    mask: list[MaskTile]
    # ko 호환 필드. ko 는 `Word.chosung` 현행 값, en 은 `mask` 의 보이는 글자로 만든
    # 문자열(빈 타일은 "_")이다. 신규 클라이언트는 `mask` 를 쓴다.
    chosung: str
    # 구분자(공백·하이픈)를 뺀 글자 수.
    length: int
    category: WordCategory
    attempts_left: int
    # 제출한 순서 그대로. 웹·앱은 로컬 저장 이력을 버리고 이걸로 보드를 그린다.
    attempts: list[AttemptView]
    status: Literal["in_progress", "success", "fail"]
    # 힌트 미리 보기(보상형 광고)로 힌트를 연 적이 있는가(`HintUnlock` 행).
    hint_unlocked: bool
    hint: str | None = None
    answer: str | None = None


class HintUnlockRequest(BaseModel):
    # 제출(`GuessRequest`)과 같은 이유로 선택 필드다 — 빠진 요청도 409
    # PUZZLE_CHANGED 로 돌려줘야 하고, 그 판정은 서비스가 한다.
    puzzle_id: int | None = None


class HintUnlockResponse(BaseModel):
    hint: str
