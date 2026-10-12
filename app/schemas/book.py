from pydantic import BaseModel


class BookSearchResult(BaseModel):
    title: str
    author: str | None = None
    publisher: str | None = None
    isbn: str | None = None
    source: str
