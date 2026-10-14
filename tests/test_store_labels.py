"""스토어 라벨 1:1 대조 (티켓 35).

같은 사실을 세 곳에 적는다 — 개인정보처리방침(`privacy#collection`·`#overseas`),
ASC 개인정보 라벨(`mobile/ios/fastlane/app_privacy_details.json`), Play 데이터 보안
(`docs/play-data-safety.md`). 한 곳만 고치면 **방침에 없는 수집을 신고**하거나
**신고하지 않은 수집을 하는** 상태가 되는데, 어느 쪽도 눈으로는 안 보인다.
그래서 `docs/legal-checklist.md` "스토어 라벨" 절의 대조표를 파싱해서 세 곳을 묶는다.

방침은 템플릿 파일을 직접 읽는다 — 이 대조는 DB·Redis 없이 성립한다
(`tests/test_legal_checklist.py` 는 렌더한 페이지로 같은 절을 본다).
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST = REPO_ROOT / "docs" / "legal-checklist.md"
DATA_SAFETY = REPO_ROOT / "docs" / "play-data-safety.md"
ASC_LABELS = REPO_ROOT / "mobile" / "ios" / "fastlane" / "app_privacy_details.json"
PRIVACY_TEMPLATE = REPO_ROOT / "web" / "templates" / "legal" / "privacy.ko.html"

DEFINITION_TERM = re.compile(r"<dt>(.+?)</dt>", re.DOTALL)
STORE_LABEL_HEADER = (
    "방침 `#collection` 항목",
    "ASC category",
    "Play 데이터 유형",
    "공유(받는 자)",
)
DATA_SAFETY_HEADER = (
    "`/privacy` `#collection` 항목",
    "Play 데이터 유형",
    "수집",
    "공유",
    "필수/선택",
    "목적",
    "비고",
)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(path: Path, header: tuple[str, ...]) -> list[list[str]]:
    """그 헤더를 가진 표의 데이터 행. 문서의 다른 표와 섞이지 않게 헤더로 고른다."""
    rows = []
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            inside = False
            continue
        cells = _cells(line)
        if tuple(cells) == header:
            inside = True
            continue
        if not inside or all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def _section(html: str, section_id: str) -> str:
    start = html.index(f'<h2 id="{section_id}"')
    rest = html[start:]
    following = re.search(r'<h2 id="', rest[1:])
    return rest[: following.start() + 1] if following else rest


def _policy_items() -> list[str]:
    section = _section(PRIVACY_TEMPLATE.read_text(encoding="utf-8"), "collection")
    return [term.strip() for term in DEFINITION_TERM.findall(section)]


def _overseas_text() -> str:
    return _section(PRIVACY_TEMPLATE.read_text(encoding="utf-8"), "overseas")


def _label_rows() -> list[list[str]]:
    return _table(CHECKLIST, STORE_LABEL_HEADER)


def _asc_categories() -> list[str]:
    return [entry["category"] for entry in json.loads(ASC_LABELS.read_text(encoding="utf-8"))]


def _without_qualifier(item: str) -> str:
    """"접속·오류 기록(Sentry 오류)" → "접속·오류 기록". 한 항목이 여러 라벨로
    갈릴 때 괄호로 어느 쪽인지 적어 두기 때문에 비교 전에 벗긴다."""
    return re.sub(r"\(.*\)$", "", item).strip()


def test_the_store_label_table_is_parseable():
    rows = _label_rows()

    assert len(rows) >= 10, "스토어 라벨 표를 못 읽었다 — 헤더가 바뀌었나"
    assert all(len(row) == len(STORE_LABEL_HEADER) for row in rows)


def test_every_collected_item_in_the_policy_has_a_store_label():
    """방침이 "수집한다" 고 적은 항목은 두 스토어 라벨에 다 나와야 한다."""
    labelled = {_without_qualifier(row[0]) for row in _label_rows()}

    missing = [item for item in _policy_items() if item not in labelled]
    assert not missing, f"스토어 라벨에 없는 수집 항목: {missing}"


def test_the_table_does_not_invent_items_the_policy_never_mentions():
    """반대 방향 — 방침에 없는 걸 스토어에 신고하면 거짓 신고다.

    기준은 티켓 35 가 정한 대로 **수집 항목 절 + 국외 이전 절** 둘 다다. "앱 사용
    이벤트"(Firebase)처럼 `#collection` 의 목록에는 없고 `#overseas` 표에만 적힌
    항목이 있어서다 — 그 자체가 대조에서 찾은 차이 3번이고, 방침 본문을 고치는
    것은 티켓 16 의 범위라 `docs/legal-checklist.md` "스토어 라벨" 에 남겼다.
    """
    items = set(_policy_items())
    overseas = _overseas_text()

    extra = [
        row[0]
        for row in _label_rows()
        if _without_qualifier(row[0]) not in items and _without_qualifier(row[0]) not in overseas
    ]
    assert not extra, f"방침 어디에도 없는 항목: {extra}"


def test_the_table_and_the_asc_labels_declare_the_same_categories():
    table = {row[1].strip("`") for row in _label_rows()}

    assert table == set(_asc_categories())


def test_the_table_and_the_play_answers_declare_the_same_data_types():
    table = {row[2] for row in _label_rows()}
    answers = {row[1] for row in _table(DATA_SAFETY, DATA_SAFETY_HEADER)}

    assert table == answers


@pytest.mark.parametrize(
    ("category", "item"),
    [
        ("OTHER_DATA_TYPES", "애플 refresh token"),
        ("OTHER_DIAGNOSTIC_DATA", "접속·오류 기록"),
    ],
)
def test_the_two_labels_found_by_the_cross_check_are_declared(category, item):
    """대조에서 찾은 차이 2건(docs/legal-checklist.md "스토어 라벨").

    둘 다 방침은 이미 적고 있었는데 ASC 라벨에만 없었다 — 되돌아가지 않게 못 박는다.
    """
    assert category in _asc_categories()
    assert item in {_without_qualifier(row[0]) for row in _label_rows()}


def test_data_linked_to_the_account_is_not_declared_as_anonymous():
    """계정·기록에 묶이는 항목은 `DATA_LINKED_TO_YOU` 다.

    접속기록은 행위자(`guest.<id>`·가린 운영자 이메일)와 원격 IP 가 남아서
    Sentry 진단(요청 본문·IP·식별자를 보내지 않는다)과 다르다.
    """
    entries = {
        entry["category"]: entry for entry in json.loads(ASC_LABELS.read_text(encoding="utf-8"))
    }

    for category in ("USER_ID", "EMAIL_ADDRESS", "OTHER_DATA_TYPES", "OTHER_DIAGNOSTIC_DATA"):
        assert "DATA_LINKED_TO_YOU" in entries[category]["data_protections"], category
    for category in ("CRASH_DATA", "PERFORMANCE_DATA"):
        assert entries[category]["data_protections"] == ["DATA_NOT_LINKED_TO_YOU"], category


def test_every_overseas_recipient_shows_up_in_the_play_sharing_answers():
    """국외 이전 표의 받는 자는 Play "공유" 답안에도 있어야 한다."""
    overseas = _section(PRIVACY_TEMPLATE.read_text(encoding="utf-8"), "overseas")
    recipients = {"Google", "Apple", "AdMob", "Firebase", "Sentry"}
    for recipient in recipients:
        assert recipient in overseas, f"방침 국외 이전 표에 {recipient} 가 없다"

    shared = " ".join(row[3] for row in _label_rows())
    missing = [recipient for recipient in recipients if recipient not in shared]
    assert not missing, f"Play 공유 답안에 없는 받는 자: {missing}"
