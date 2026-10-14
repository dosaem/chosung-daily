import csv
from dataclasses import dataclass, field
from enum import StrEnum

from app.errors import ValidationError
from app.extensions import db
from app.models import PuzzleLanguage, Word, WordCategory
from app.repositories import word_repository
from app.schemas.book import BookSearchResult

# CSV 열 이름과 순서. CLI `flask seed-words` 가 읽는 파일과 운영자 페이지 업로드가
# 같은 포맷을 쓴다 (README "운영: 단어 CSV 업로드").
WORD_CSV_COLUMNS = ("language", "category", "answer", "hint")

# 운영자 목록 한 페이지의 줄 수.
WORDS_PER_PAGE = 20
# 테스트·템플릿이 같은 이름으로 참조하는 공개 이름.
ADMIN_WORDS_PER_PAGE = WORDS_PER_PAGE

# Word.answer / Word.hint 컬럼 길이. 넘기면 MySQL 이 에러를 내므로 먼저 걸러서
# 운영자에게 사유를 보여준다.
ANSWER_MAX_LENGTH = 50
HINT_MAX_LENGTH = 200

DUPLICATE_MESSAGE = "이미 등록된 단어입니다 (같은 언어·카테고리·정답)."

# 삭제를 막을 때 사유에 적어 보여줄 배정 날짜 수. 전부 나열하면 메시지가 길어진다.
_SHOWN_ASSIGNED_DATES = 3


class RowStatus(StrEnum):
    """CSV 한 행의 처리 결과."""

    ADDED = "added"
    DUPLICATE = "duplicate"
    ERROR = "error"


@dataclass(frozen=True)
class RowResult:
    """행 하나의 결과. `line` 은 CSV 파일의 줄 번호(헤더가 1행)다 —
    운영자가 스프레드시트에서 그 줄을 바로 찾을 수 있어야 한다."""

    line: int
    answer: str
    status: RowStatus
    reason: str = ""


@dataclass(frozen=True)
class WordInput:
    """저장할 수 있는 형태로 검증을 마친 단어 하나."""

    language: PuzzleLanguage
    category: WordCategory
    answer: str
    hint: str

    @property
    def duplicate_key(self) -> tuple[str, str, str]:
        return (self.language.value, self.answer, self.category.value)


@dataclass
class SeedResult:
    created: int = 0
    skipped: list[str] = field(default_factory=list)


def parse_word_input(
    language: str | None, category: str | None, answer: str | None, hint: str | None
) -> WordInput:
    """폼·CSV 가 보낸 문자열 네 개를 검증해서 `WordInput` 으로 바꾼다.

    실패하면 사람이 읽을 사유를 담은 `ValidationError` 를 던진다 — 운영자 폼은 그
    문구를 입력 옆에 그리고, CSV 적재는 행 결과의 사유 칸에 넣는다. 검증 규칙이
    두 입구에 각각 생기지 않게 여기 한 곳만 둔다.
    """
    answer = (answer or "").strip()
    hint = (hint or "").strip()
    if not answer:
        raise ValidationError("정답이 비어 있습니다.")
    if not hint:
        raise ValidationError("힌트가 비어 있습니다.")
    if len(answer) > ANSWER_MAX_LENGTH:
        raise ValidationError(f"정답이 너무 깁니다 (최대 {ANSWER_MAX_LENGTH}자).")
    if len(hint) > HINT_MAX_LENGTH:
        raise ValidationError(f"힌트가 너무 깁니다 (최대 {HINT_MAX_LENGTH}자).")

    # language 열은 없어도 된다 — 언어가 들어오기 전에 만든 CSV 가 그대로 돌아간다.
    language_value = (language or "").strip() or PuzzleLanguage.KO.value
    try:
        parsed_language = PuzzleLanguage(language_value)
    except ValueError:
        raise ValidationError(f"알 수 없는 language: {language_value!r}") from None

    try:
        parsed_category = WordCategory((category or "").strip())
    except ValueError:
        raise ValidationError(f"알 수 없는 category: {(category or '').strip()!r}") from None

    return WordInput(parsed_language, parsed_category, answer, hint)


def missing_csv_columns(fieldnames: list[str] | None) -> list[str]:
    """CSV 헤더에 빠진 열 이름. 비어 있으면 통과다.

    열 순서와 앞뒤 공백은 따지지 않는다 — 사람이 스프레드시트로 만드는 파일이고,
    순서가 달라도 `DictReader` 가 이름으로 읽는다.
    """
    present = {(name or "").strip() for name in fieldnames or ()}
    return [column for column in WORD_CSV_COLUMNS if column not in present]


def import_word_rows(rows: list[dict[str, str]]) -> list[RowResult]:
    """CSV 행 리스트를 적재하고 행별 결과를 돌려준다.

    파일 객체가 아니라 행 리스트를 받는다 — 업로드(웹)와 파일 읽기(CLI)가 같은
    적재 규칙을 쓰고, 테스트가 임시 파일 없이 규칙만 검증할 수 있다. 파일을 읽고
    인코딩·헤더를 확인하는 건 호출부(`app/admin.py`, `seed_words_from_csv`)의 일이다.

    트랜잭션 경계: 이 함수 전체가 커밋 하나다. 깨진 행은 그 행만 결과에 사유를
    담아 건너뛰고 나머지는 계속 넣는다 — 행 하나 때문에 100행 파일을 다시 올리게
    하지 않는다.
    """
    existing = word_repository.existing_keys()
    results: list[RowResult] = []

    for index, raw_row in enumerate(rows):
        # 헤더가 1행이라 데이터 첫 줄이 2행이다. 헤더 이름의 앞뒤 공백도 떼서
        # `missing_csv_columns` 가 통과시킨 헤더를 여기서도 같은 이름으로 읽는다.
        line = index + 2
        row = {(key or "").strip(): value for key, value in raw_row.items()}
        answer = (row.get("answer") or "").strip()

        try:
            parsed = parse_word_input(
                row.get("language"), row.get("category"), row.get("answer"), row.get("hint")
            )
        except ValidationError as err:
            results.append(RowResult(line, answer, RowStatus.ERROR, err.message))
            continue

        # 파일 안에서 같은 단어가 두 번 나오는 것도 중복이다 — DB 에 넣기 전이라
        # 조회로는 안 걸리니, 방금 넣은 키를 같은 집합에 더해가며 본다.
        if parsed.duplicate_key in existing:
            results.append(RowResult(line, parsed.answer, RowStatus.DUPLICATE, DUPLICATE_MESSAGE))
            continue

        existing.add(parsed.duplicate_key)
        db.session.add(_new_word(parsed))
        results.append(RowResult(line, parsed.answer, RowStatus.ADDED))

    db.session.commit()
    return results


def seed_words_from_csv(csv_path: str) -> SeedResult:
    """CSV 파일(컬럼: language,category,answer,hint)을 읽어 Word를 등록한다.

    적재 규칙은 `import_word_rows` 가 들고 있다 — 운영자 페이지 업로드와 이
    CLI 가 같은 중복·검증 규칙을 쓴다. 이 함수는 파일을 열어 행으로 바꾸고,
    CLI 가 출력할 모양(`SeedResult`)으로 결과를 접는다. 중복은 조용히 건너뛰고
    (여러 번 돌려도 같은 결과), 깨진 행만 사유와 함께 돌려준다.
    """
    # utf-8-sig: 엑셀이 저장한 CSV 의 BOM 을 헤더 이름에 끌어들이지 않는다.
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    outcomes = import_word_rows(rows)
    return SeedResult(
        created=sum(1 for outcome in outcomes if outcome.status is RowStatus.ADDED),
        skipped=[
            f"{outcome.reason} ({outcome.line}행): {outcome.answer}"
            for outcome in outcomes
            if outcome.status is RowStatus.ERROR
        ],
    )


def search_words(
    *,
    language: PuzzleLanguage | None = None,
    category: WordCategory | None = None,
    keyword: str = "",
    page: int = 1,
    per_page: int = WORDS_PER_PAGE,
):
    """운영자 목록 조회. 필터를 정리해서 리포지토리에 넘긴다."""
    return word_repository.search(
        language=language,
        category=category,
        keyword=keyword.strip(),
        page=max(page, 1),
        per_page=per_page,
    )


def create_word(
    language: str | None, category: str | None, answer: str | None, hint: str | None
) -> Word:
    """운영자 폼으로 단어 하나를 추가한다. 가림은 모델 이벤트가 계산한다."""
    parsed = parse_word_input(language, category, answer, hint)
    if word_repository.find_duplicate(parsed.language, parsed.answer, parsed.category):
        raise ValidationError(DUPLICATE_MESSAGE)

    word = _new_word(parsed)
    db.session.add(word)
    db.session.commit()
    return word


def update_word(
    word: Word,
    language: str | None,
    category: str | None,
    answer: str | None,
    hint: str | None,
) -> Word:
    """단어를 고친다. `mask`·`chosung` 은 `Word` 의 before_update 이벤트가 다시 계산한다
    (app/models/word.py) — 저장 경로마다 가림 계산을 기억하지 않아도 되는 이유다."""
    parsed = parse_word_input(language, category, answer, hint)
    if word_repository.find_duplicate(
        parsed.language, parsed.answer, parsed.category, exclude_id=word.id
    ):
        raise ValidationError(DUPLICATE_MESSAGE)

    word.language = parsed.language
    word.category = parsed.category
    word.answer = parsed.answer
    word.hint = parsed.hint
    db.session.commit()
    return word


def delete_word(word: Word) -> None:
    """단어를 지운다. 이미 퍼즐로 배정된 단어는 막는다.

    배정된 단어를 지우면 그 날짜의 퍼즐이 참조를 잃고, 이미 푼 사람의 시도 이력도
    가리킬 단어가 없어진다. 배정표에서 그 날짜의 단어를 먼저 바꿔야 한다(티켓 16).
    """
    assigned_dates = word_repository.assigned_puzzle_dates(word.id)
    if assigned_dates:
        shown = ", ".join(
            puzzle_date.isoformat() for puzzle_date in assigned_dates[:_SHOWN_ASSIGNED_DATES]
        )
        more = " 등" if len(assigned_dates) > _SHOWN_ASSIGNED_DATES else ""
        raise ValidationError(
            f"이미 퍼즐로 배정된 단어는 삭제할 수 없습니다 (배정일 {shown}{more})."
        )

    db.session.delete(word)
    db.session.commit()


def add_word_from_book(
    book: BookSearchResult, language: PuzzleLanguage = PuzzleLanguage.KO
) -> tuple[Word, bool]:
    """책 검색 결과를 book_title 카테고리 Word로 등록한다.

    (word, created) 튜플을 돌려준다 — 같은 (language, answer, category)가 이미 있으면
    새로 안 만들고 기존 걸 그대로 돌려준다(created=False). CSV 적재의
    중복 체크와 같은 규칙인데, 이걸 빼먹었다가 `flask search-books ... --add`를
    같은 책으로 두 번 돌려서 "데미안"이 Word 두 개로 중복 등록되는 걸 실제로
    겪고 나서 추가했다.
    """
    existing = word_repository.find_duplicate(language, book.title, WordCategory.BOOK_TITLE)
    if existing is not None:
        return existing, False

    hint = ", ".join(part for part in [book.author, book.publisher] if part)
    word = Word(
        language=language,
        answer=book.title,
        category=WordCategory.BOOK_TITLE,
        hint=hint or "책 제목",
    )
    db.session.add(word)
    db.session.commit()
    return word, True


def _new_word(parsed: WordInput) -> Word:
    return Word(
        language=parsed.language,
        answer=parsed.answer,
        category=parsed.category,
        hint=parsed.hint,
    )
