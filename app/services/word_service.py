import csv
from dataclasses import dataclass, field

from app.extensions import db
from app.models import Word, WordCategory
from app.schemas.book import BookSearchResult


@dataclass
class SeedResult:
    created: int = 0
    skipped: list[str] = field(default_factory=list)


def seed_words_from_csv(csv_path: str) -> SeedResult:
    """CSV(컬럼: answer,category,hint)를 읽어 Word를 등록한다.

    같은 (answer, category)가 이미 있으면 건너뛴다 — 여러 번 실행해도 중복 안 생기게.
    트랜잭션 경계: 이 메서드 전체가 하나의 커밋 단위다. 행 하나가 깨지면 그 행만
    건너뛰고 나머지는 계속 진행하되, 실제 DB commit은 맨 끝에 한 번만 한다.
    건너뛴 행 안내는 호출한 쪽(CLI)이 출력하도록 결과로만 돌려준다 — 서비스 레이어는
    사용자 출력을 직접 하지 않는다.
    """
    with open(csv_path, encoding="utf-8") as f:
        rows = [
            {k: v.strip() for k, v in row.items() if v is not None}
            for row in csv.DictReader(f)
        ]

    existing = {
        (answer, category)
        for answer, category in db.session.query(Word.answer, Word.category).all()
    }

    result = SeedResult()
    seen_in_file = set()
    for row in rows:
        answer, category_raw, hint = row["answer"], row["category"], row["hint"]

        try:
            category = WordCategory(category_raw)
        except ValueError:
            result.skipped.append(f"알 수 없는 category={category_raw!r}: {answer}")
            continue

        key = (answer, category.value)
        if key in existing or key in seen_in_file:
            continue
        seen_in_file.add(key)

        db.session.add(Word(answer=answer, category=category, hint=hint))
        result.created += 1

    db.session.commit()
    return result


def add_word_from_book(book: BookSearchResult) -> tuple[Word, bool]:
    """책 검색 결과를 book_title 카테고리 Word로 등록한다.

    (word, created) 튜플을 돌려준다 — 같은 (answer, category)가 이미 있으면
    새로 안 만들고 기존 걸 그대로 돌려준다(created=False). seed_words_from_csv의
    중복 체크와 같은 규칙인데, 이걸 빼먹었다가 `flask search-books ... --add`를
    같은 책으로 두 번 돌려서 "데미안"이 Word 두 개로 중복 등록되는 걸 실제로
    겪고 나서 추가했다.
    """
    existing = Word.query.filter_by(answer=book.title, category=WordCategory.BOOK_TITLE).first()
    if existing is not None:
        return existing, False

    hint = ", ".join(part for part in [book.author, book.publisher] if part)
    word = Word(answer=book.title, category=WordCategory.BOOK_TITLE, hint=hint or "책 제목")
    db.session.add(word)
    db.session.commit()
    return word, True
