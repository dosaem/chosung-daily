import enum


class WordCategory(enum.StrEnum):
    GENERAL = "general"
    BOOK_TITLE = "book_title"


class OAuthProvider(enum.StrEnum):
    GOOGLE = "google"
    KAKAO = "kakao"
