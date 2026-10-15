#!/usr/bin/env python3
"""단어 후보 CSV 를 `/admin/words/import` 에 올리기 전에 로컬에서 검사한다.

업로드 화면도 행별로 오류를 보여주지만(`import_word_rows`), 그건 **DB 에 넣으면서**
보는 결과다. 150행짜리 후보 파일을 그대로 올리면 "추가 137 / 오류 13" 이 되고,
들어간 137행 중 규칙에 안 맞는 힌트(정답 글자가 섞인 힌트)는 오류로도 안 잡혀 그냥
퍼즐로 나간다. 그래서 올리기 전에 DB 없이 같은 파일을 훑는 입구를 따로 둔다.

형식·중복 검증은 업로드와 같은 함수(`app.services.word_service.parse_word_input`)를
쓴다 — 규칙이 두 군데로 갈리면 "로컬은 통과인데 업로드는 오류" 가 생긴다. 여기서만
보는 건 **후보 생성 규칙**(README "운영: 단어 CSV 업로드" 의 프롬프트 골자)이다:
언어별 글자 범위·길이, 힌트에 정답이 새지 않는지, 파일 안 중복, `data/seed_words.csv`
와 겹치는지.

사용법:

    uv run python scripts/check_word_csv.py data/word-candidates/ko-general-01.csv ...

위반이 있으면 `줄번호: 사유` 를 찍고 종료 코드 1 이다(CSV 헤더가 1행).
"""

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 이 파일을 `python scripts/check_word_csv.py` 로 직접 실행하면 sys.path 에
# `scripts/` 만 들어가서 `app` 패키지를 못 찾는다. 레포 루트를 먼저 넣는다.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.errors import ValidationError  # noqa: E402
from app.models import PuzzleLanguage  # noqa: E402
from app.services.word_service import (  # noqa: E402
    CSV_EXTRA_FIELD_KEY,
    WordInput,
    duplicate_csv_columns,
    missing_csv_columns,
    parse_word_input,
)

SEED_WORDS_PATH = "data/seed_words.csv"

# 언어별 정답 길이. ko 는 음절 수, en 은 구분자를 포함한 글자 수다.
KO_ANSWER_RANGE = (2, 5)
EN_ANSWER_RANGE = (2, 12)

# 힌트는 타일 아래 한 줄로 들어간다 — 컬럼 상한(200자)보다 짧게 잡는다.
HINT_MAX_LENGTH = 60

# en 정답에 쓸 수 있는 글자와 구분자(공백·하이픈 합쳐 최대 1개 = 두 단어까지).
EN_ANSWER_PATTERN = re.compile(r"^[a-z -]+$")
EN_SEPARATORS = " -"
EN_MAX_SEPARATORS = 1

# 모음을 가리고 내는 문제라, 모음이 절반을 넘으면 남는 자음 뼈대가 단서가 안 된다
# (`aeon` → `_ _ N`). 가림 규칙은 app/utils/mask.py 와 같은 모음 집합을 본다.
EN_VOWELS = frozenset("aeiou")
EN_MAX_VOWEL_RATIO = 0.5

# 힌트에 정답이 새는지 볼 때, 두 단어 정답의 각 낱말은 3글자 이상만 본다 —
# `a`·`of` 같은 조각은 어느 힌트에나 들어 있어서 사유가 될 수 없다.
EN_HINT_PART_MIN_LENGTH = 3

KO_SYLLABLE_PATTERN = re.compile(r"^[가-힣]+$")


@dataclass(frozen=True)
class Violation:
    """규칙을 어긴 행 하나. `line` 은 CSV 줄 번호(헤더가 1행)다 — 운영자가
    스프레드시트에서 그 줄을 바로 찾아 지울 수 있어야 한다."""

    line: int
    reason: str


def load_seed_keys(path: str = SEED_WORDS_PATH) -> set[tuple[str, str, str]]:
    """`data/seed_words.csv` 의 (언어, 정답, 카테고리) 키. 파일이 없으면 빈 집합이다.

    키 모양은 `WordInput.duplicate_key` 와 같다 — 업로드가 중복으로 건너뛸 행을
    후보 파일에 남겨두면, 사람이 "추가 137 / 중복 13" 을 보고 뭘 잘못했는지 찾게 된다.
    """
    try:
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return set()

    keys = set()
    for row in rows:
        try:
            parsed = parse_word_input(
                row.get("language"), row.get("category"), row.get("answer"), row.get("hint")
            )
        except ValidationError:
            continue
        keys.add(parsed.duplicate_key)
    return keys


def check_file(path: str, seed_keys: set[tuple[str, str, str]]) -> list[Violation]:
    """CSV 한 파일의 위반 목록. 파일을 읽는 것 말고는 바깥(DB·네트워크)을 안 본다."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, restkey=CSV_EXTRA_FIELD_KEY)
        header_problems = _check_header(reader.fieldnames)
        if header_problems:
            # 헤더가 깨졌으면 행 사유는 전부 "힌트가 비어 있습니다" 같은 2차 피해라
            # 헤더만 알려준다.
            return header_problems
        rows = list(reader)

    violations: list[Violation] = []
    seen: dict[tuple[str, str, str], int] = {}

    for index, raw_row in enumerate(rows):
        line = index + 2
        if raw_row.get(CSV_EXTRA_FIELD_KEY):
            violations.append(Violation(line, "열이 헤더보다 많습니다 (쉼표가 들어간 값)."))
            continue

        # 헤더 이름의 앞뒤 공백을 떼서 읽는다 — `missing_csv_columns` 가 공백을
        # 무시하고 통과시킨 헤더(` answer`)를 여기서도 같은 이름으로 봐야 업로드와
        # 같은 결과가 나온다(`import_word_rows` 와 같은 처리).
        row = {(key or "").strip(): value for key, value in raw_row.items()}
        try:
            parsed = parse_word_input(
                row.get("language"),
                row.get("category"),
                row.get("answer"),
                row.get("hint"),
            )
        except ValidationError as err:
            violations.append(Violation(line, err.message))
            continue

        violations.extend(
            Violation(line, reason) for reason in _row_reasons(parsed, seen, seed_keys, line)
        )

    return violations


def _check_header(fieldnames: list[str] | None) -> list[Violation]:
    missing = missing_csv_columns(fieldnames)
    duplicated = duplicate_csv_columns(fieldnames)
    problems = []
    if missing:
        problems.append(Violation(1, f"헤더에 빠진 열: {', '.join(missing)}"))
    if duplicated:
        problems.append(Violation(1, f"헤더에 두 번 나온 열: {', '.join(duplicated)}"))
    return problems


def _row_reasons(
    parsed: WordInput, seen: dict[tuple[str, str, str], int], seed_keys: set, line: int
) -> list[str]:
    reasons = _answer_reasons(parsed) + _hint_reasons(parsed)

    key = parsed.duplicate_key
    if key in seen:
        reasons.append(f"같은 파일 안에서 중복된 정답입니다 ({seen[key]}행과 같음).")
    elif key in seed_keys:
        reasons.append(f"{SEED_WORDS_PATH} 에 이미 있는 정답입니다.")
    else:
        seen[key] = line
    return reasons


def _answer_reasons(parsed: WordInput) -> list[str]:
    if parsed.language is PuzzleLanguage.EN:
        return _en_answer_reasons(parsed.answer)
    return _ko_answer_reasons(parsed.answer)


def _ko_answer_reasons(answer: str) -> list[str]:
    reasons = []
    if not KO_SYLLABLE_PATTERN.match(answer):
        reasons.append("정답에 완성형 한글이 아닌 글자가 있습니다 (공백·숫자·기호·영문 금지).")
    low, high = KO_ANSWER_RANGE
    if not low <= len(answer) <= high:
        reasons.append(f"정답이 {len(answer)}글자입니다 (ko 는 {low}~{high}글자).")
    return reasons


def _en_answer_reasons(answer: str) -> list[str]:
    reasons = []
    if not EN_ANSWER_PATTERN.match(answer):
        reasons.append("정답은 소문자 a-z 와 공백·하이픈만 쓸 수 있습니다.")
    low, high = EN_ANSWER_RANGE
    if not low <= len(answer) <= high:
        reasons.append(f"정답이 {len(answer)}자입니다 (en 은 {low}~{high}자).")

    separators = sum(1 for ch in answer if ch in EN_SEPARATORS)
    if separators > EN_MAX_SEPARATORS:
        reasons.append(f"구분자(공백·하이픈)가 {separators}개입니다 (최대 1개 = 두 단어까지).")

    letters = [ch for ch in answer.lower() if ch not in EN_SEPARATORS]
    vowels = sum(1 for ch in letters if ch in EN_VOWELS)
    if letters and vowels / len(letters) > EN_MAX_VOWEL_RATIO:
        reasons.append(
            f"모음이 {vowels}/{len(letters)} 입니다 — 모음을 가리면 자음 뼈대가 안 남습니다."
        )
    return reasons


def _hint_reasons(parsed: WordInput) -> list[str]:
    hint = parsed.hint
    reasons = []
    if len(hint) > HINT_MAX_LENGTH:
        reasons.append(f"힌트가 {len(hint)}자입니다 (1~{HINT_MAX_LENGTH}자).")
    if "\n" in hint or "\r" in hint:
        reasons.append("힌트는 한 줄이어야 합니다.")
    if any(ch in hint for ch in '",'):
        reasons.append("힌트에 따옴표·쉼표를 쓸 수 없습니다.")

    if parsed.language is PuzzleLanguage.EN:
        reasons.extend(_en_hint_leak_reasons(parsed.answer, hint))
    else:
        reasons.extend(_ko_hint_leak_reasons(parsed.answer, hint))
    return reasons


def _ko_hint_leak_reasons(answer: str, hint: str) -> list[str]:
    """힌트가 정답 음절을 하나라도 쓰면 초성이 그대로 보인다 — `책상` 의 힌트에
    `책` 이 있으면 ㅊ ㅅ 두 칸 중 한 칸이 공짜다."""
    # 한글 음절만 본다 — 정답에 섞인 공백·기호는 어느 힌트에나 있어서 사유가
    # 안 되고, 그건 정답 쪽 규칙(`_ko_answer_reasons`)이 따로 잡는다.
    shared = sorted(
        {
            syllable
            for syllable in answer
            if KO_SYLLABLE_PATTERN.match(syllable) and syllable in hint
        }
    )
    if not shared:
        return []
    return [f"힌트에 정답 음절이 들어 있습니다: {' '.join(shared)}"]


def _en_hint_leak_reasons(answer: str, hint: str) -> list[str]:
    """힌트에 정답 단어(또는 복수형)가 낱말로 들어 있으면 문제가 아니라 답이다."""
    words = " ".join(re.findall(r"[a-z]+", hint.lower()))
    phrase = answer.replace("-", " ")
    targets = {phrase} | {
        part for part in phrase.split() if len(part) >= EN_HINT_PART_MIN_LENGTH
    }

    for target in sorted(targets):
        for form in _plural_forms(target):
            if re.search(rf"\b{re.escape(form)}\b", words):
                return [f"힌트에 정답 단어가 들어 있습니다: {form}"]
    return []


def _plural_forms(word: str) -> set[str]:
    forms = {word, f"{word}s"}
    if word.endswith("y"):
        forms.add(f"{word[:-1]}ies")
    if word.endswith(("s", "sh", "ch", "x", "z")):
        forms.add(f"{word}es")
    return forms


def main(argv: list[str] | None = None) -> int:
    paths = argv if argv is not None else sys.argv[1:]
    if not paths:
        print("사용법: scripts/check_word_csv.py <csv> [<csv> ...]")
        return 2

    seed_keys = load_seed_keys()
    failed = False
    for path in paths:
        try:
            violations = check_file(path, seed_keys)
        except OSError as err:
            print(f"{path}: 파일을 읽을 수 없습니다 ({err.strerror}).")
            failed = True
            continue

        print(f"{path}: 위반 {len(violations)}건")
        for violation in violations:
            print(f"  {violation.line}: {violation.reason}")
        failed = failed or bool(violations)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
