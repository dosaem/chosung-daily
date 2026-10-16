#!/usr/bin/env python3
"""단어 후보 CSV 를 `/admin/words/import` 에 올리기 전에 로컬에서 검사한다.

업로드 화면도 행별로 오류를 보여주지만(`import_word_rows`), 그건 **DB 에 넣으면서**
보는 결과다. 150행짜리 후보 파일을 그대로 올리면 "추가 137 / 오류 13" 이 되고,
들어간 137행 중 규칙에 안 맞는 힌트(정답 글자가 섞인 힌트)는 오류로도 안 잡혀 그냥
퍼즐로 나간다. 그래서 올리기 전에 DB 없이 같은 파일을 훑는 입구를 따로 둔다.

형식·중복 검증은 업로드와 같은 함수(`app.services.word_service.parse_word_input`)를
쓴다 — 규칙이 두 군데로 갈리면 "로컬은 통과인데 업로드는 오류" 가 생긴다. 여기서
보는 **후보 생성 규칙**(언어별 글자 범위·길이, 힌트에 정답이 새지 않는지, 파일 안
중복, `data/seed_words.csv` 와 겹치는지)은 `app/services/word_rules.py` 가 들고 있고
LLM 생성 서비스도 같은 함수를 쓴다 — 이 스크립트는 파일을 읽어 그 규칙에 넣는
입구일 뿐이다.

사용법:

    uv run python scripts/check_word_csv.py data/word-candidates/ko-general-01.csv ...

위반이 있으면 `줄번호: 사유` 를 찍고 종료 코드 1 이다(CSV 헤더가 1행).
"""

import csv
import sys
from pathlib import Path

# 이 파일을 `python scripts/check_word_csv.py` 로 직접 실행하면 sys.path 에
# `scripts/` 만 들어가서 `app` 패키지를 못 찾는다. 레포 루트를 먼저 넣는다.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.errors import ValidationError  # noqa: E402
from app.services.word_rules import (  # noqa: E402
    Violation,
    candidate_reasons,
    duplicate_reasons,
)
from app.services.word_service import (  # noqa: E402
    CSV_EXTRA_FIELD_KEY,
    WordInput,
    duplicate_csv_columns,
    missing_csv_columns,
    parse_word_input,
)

SEED_WORDS_PATH = "data/seed_words.csv"

SEED_WORDS_PATH = "data/seed_words.csv"


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
    return candidate_reasons(parsed) + duplicate_reasons(
        parsed, seen, seed_keys, line, SEED_WORDS_PATH
    )


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
