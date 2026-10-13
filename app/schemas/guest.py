from pydantic import BaseModel

from app.models.enums import PuzzleLanguage


class GuestCreateRequest(BaseModel):
    """`POST /guests` 본문. 언어를 안 보내면 ko다 — 기존 클라이언트가 그대로 돈다."""

    puzzle_language: PuzzleLanguage = PuzzleLanguage.KO


class GuestResponse(BaseModel):
    token: str


class PuzzleLanguageRequest(BaseModel):
    """`PATCH /me` 본문. 지원하지 않는 값은 pydantic이 걸러 VALIDATION_ERROR가 된다."""

    puzzle_language: PuzzleLanguage


class PuzzleLanguageResponse(BaseModel):
    puzzle_language: PuzzleLanguage
