import enum


class WordCategory(enum.StrEnum):
    GENERAL = "general"
    BOOK_TITLE = "book_title"


class OAuthProvider(enum.StrEnum):
    GOOGLE = "google"
    APPLE = "apple"


class PuzzleLanguage(enum.StrEnum):
    """퍼즐 언어 — 플레이어가 고르는 문제의 언어. UI 언어와 별개다(CONTEXT.md)."""

    KO = "ko"
    EN = "en"
