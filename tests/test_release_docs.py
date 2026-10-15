"""릴리스 문서 한 벌을 묶는 테스트 (티켓 37).

`docs/RELEASE.md` 는 티켓마다 자기 절(`### NN.`)을 덧붙여 왔다. 운영자는 그걸 위에서
아래로 읽는 게 아니라 **"지금 뭘 해야 하나"** 로 읽는다. 그래서 이 티켓이 세 개의
통합 목차를 앞에 두는데, 통합 목차는 사람이 손으로 옮겨 적는 것이라 **원본이 늘면
조용히 거짓이 된다**. 아래 테스트가 그 둘을 묶는다:

- 워크플로가 실제로 쓰는 secret·variable 전부가 통합 목차에 있는지
- 통합 목차의 "상세" 칸이 가리키는 `### NN.` 절이 실제로 있는지
- 실기기 체크리스트의 모든 항목이 **기대 결과**(`→`)를 적었는지
- README "설계 판단" 이 스펙 §C.32 의 열 항목을 전부 덮는지

`tests/test_deploy_workflow.py`·`tests/test_app_deploy_workflow.py` 는 각 워크플로가
자기 secret 을 문서에 적었는지를 보고, 이 파일은 **문서 쪽에서** 전체를 본다.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_DOC = REPO_ROOT / "docs" / "RELEASE.md"
README = REPO_ROOT / "README.md"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SPEC = REPO_ROOT / ".scratch" / "store-launch" / "spec.md"

OPERATOR_EMAILS = ("dosaem90@gmail.com", "hsseo@dosaem.com")

HUMAN_ORDER_HEADING = "## 사람 작업 순서 (D0~D3)"
SECRET_INDEX_HEADING = "## GitHub Actions secrets · variables 통합 목차"
DEVICE_HEADING = "## 실기기 체크리스트 (통합)"

TICKET_SECTION = re.compile(r"`?### (\d{2})\.")
BACKTICKED_NAME = re.compile(r"^`([A-Z0-9_]+)`$")
README_SECTION_QUOTE = re.compile(r'"(\d{2}\. [^"]+)"')


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str, level: str = "## ") -> str:
    """`heading` 부터 같은 깊이의 다음 제목까지."""
    assert heading in text, f"{heading} 절이 없다"
    body = text.split(heading, 1)[1]
    return re.split(rf"\n{re.escape(level)}", body)[0]


def _subsection(body: str, heading: str) -> str:
    assert heading in body, f"{heading} 소제목이 없다"
    return re.split(r"\n### ", body.split(heading, 1)[1])[0]


def _first_cells(markdown: str) -> set[str]:
    """표 첫 칸에 `` `NAME` `` 으로 적힌 것들."""
    names = set()
    for line in markdown.splitlines():
        if not line.startswith("|"):
            continue
        match = BACKTICKED_NAME.fullmatch(line.split("|")[1].strip())
        if match:
            names.add(match.group(1))
    return names


def _workflow_text() -> str:
    return "\n".join(_text(path) for path in sorted(WORKFLOW_DIR.glob("*.yml")))


def _checklist_items(body: str) -> list[str]:
    """`- [ ]` 항목 하나를 이어지는 들여쓴 줄까지 합쳐서 돌려준다."""
    items: list[str] = []
    for line in body.splitlines():
        if line.startswith("- [ ]"):
            items.append(line)
        elif items and line.startswith(("      ", "\t")):
            items[-1] += " " + line.strip()
    return items


# --- D0~D3 사람 작업 순서 ----------------------------------------------------


@pytest.fixture(scope="module")
def release() -> str:
    return _text(RELEASE_DOC)


@pytest.fixture(scope="module")
def human_order(release: str) -> str:
    return _section(release, HUMAN_ORDER_HEADING)


@pytest.mark.parametrize("stage", ["### D0.", "### D1.", "### D2.", "### D3."])
def test_human_order_has_every_stage(human_order: str, stage: str):
    """스펙 §D 의 네 단계가 한 절 안에 순서대로 있어야 운영자가 위에서 아래로 읽는다."""
    assert stage in human_order


@pytest.mark.parametrize("email", OPERATOR_EMAILS)
def test_human_order_names_both_operator_accounts(human_order: str, email: str):
    """가입·콘솔은 이 둘 중 하나로만 한다 — 세 번째 계정이 생기면 복구가 불가능하다."""
    assert email in human_order


def test_human_order_items_point_at_a_detail_section(human_order: str, release: str):
    """항목이 가리키는 `### NN.` 절이 실제로 있어야 "상세" 가 거짓이 되지 않는다."""
    referenced = {
        match for item in _checklist_items(human_order) for match in TICKET_SECTION.findall(item)
    }

    assert referenced, "D0~D3 항목이 어느 티켓 절도 가리키지 않는다"
    for number in sorted(referenced):
        assert f"### {number}." in release, f"### {number}. 절이 RELEASE.md 에 없다"


def test_d2_names_the_grace_period_and_the_asc_name_clash(human_order: str):
    """스펙 D2 의 두 항목. Grace Period 를 안 켜면 `grace` 상태가 아예 안 온다."""
    body = _subsection(human_order, "### D2.")

    assert "Grace Period" in body
    assert "16일" in body
    assert "Hidden Vowels: Daily Word" in body


def test_d3_rechecks_the_submission_day_requirements(human_order: str):
    """제출일 기준으로 다시 봐야 하는 것들 — 스펙 §B.18, Play Data safety."""
    body = _subsection(human_order, "### D3.")

    assert "target SDK" in body
    assert "Billing 8" in body
    assert "Data safety" in body
    assert "/account/delete" in body


def test_d3_includes_the_nas_first_deploy_and_the_restore_rehearsal(human_order: str):
    """프로젝트명·볼륨 확인 없이 `up` 하면 빈 DB 로 뜬다(스펙 §C.26)."""
    body = _subsection(human_order, "### D3.")

    assert "docker volume ls" in body
    assert "복구 리허설" in body


@pytest.mark.parametrize(
    "needle", ["통신판매업", "보호책임자", "주소", "전문가", "EULA", "Data safety"]
)
def test_legal_items_from_ticket_16_are_in_the_d1_or_d3_stage(human_order: str, needle: str):
    """티켓 16 의 "사람이 확인할 법적 항목" 이 D1·D3 순서 안에 들어와 있어야 한다."""
    stages = _subsection(human_order, "### D1.") + _subsection(human_order, "### D3.")

    assert needle in stages


# --- secrets · variables 통합 목차 -------------------------------------------


def test_secret_index_covers_every_secret_the_workflows_use(release: str):
    """목차에 없는 secret 은 사람이 등록하지 못하고, 그 워크플로만 조용히 실패한다."""
    index = _section(release, SECRET_INDEX_HEADING)
    used = set(re.findall(r"secrets\.([A-Z0-9_]+)", _workflow_text()))

    assert used, "secret 을 쓰는 워크플로가 하나도 없다"
    assert used <= _first_cells(index), used - _first_cells(index)


def test_variable_index_covers_every_variable_the_workflows_use(release: str):
    """variable 이 비면 빌드가 멈추게 해 뒀다 — 목차가 빠지면 왜 멈췄는지 알 수 없다."""
    index = _section(release, SECRET_INDEX_HEADING)
    used = set(re.findall(r"vars\.([A-Z0-9_]+)", _workflow_text()))

    assert used, "variable 을 쓰는 워크플로가 하나도 없다"
    assert used <= _first_cells(index), used - _first_cells(index)


def test_secret_index_rows_point_at_a_detail_section(release: str):
    """목차는 값을 적지 않는다 — 어느 절에 설명이 있는지만 가리킨다."""
    index = _section(release, SECRET_INDEX_HEADING)
    referenced = set(TICKET_SECTION.findall(index))

    assert referenced, "목차가 어느 티켓 절도 가리키지 않는다"
    for number in sorted(referenced):
        assert f"### {number}." in release, f"### {number}. 절이 RELEASE.md 에 없다"


def test_secret_index_does_not_carry_values(release: str):
    """이름과 자리만 둔다. 값이 문서에 들어오면 레포가 유출 경로가 된다."""
    index = _section(release, SECRET_INDEX_HEADING)

    assert "BEGIN " not in index
    assert "ca-app-pub-" not in index


# --- 실기기 체크리스트 (통합) -------------------------------------------------


@pytest.fixture(scope="module")
def device_checklist(release: str) -> str:
    return _section(release, DEVICE_HEADING)


@pytest.mark.parametrize(
    "area",
    [
        "### 알림",
        "### 구독",
        "### 광고",
        "### 계정",
        "### 태블릿",
    ],
)
def test_device_checklist_has_a_subsection_per_area(device_checklist: str, area: str):
    assert area in device_checklist


def test_every_device_checklist_item_states_an_expected_result(device_checklist: str):
    """기대 결과가 없는 체크박스는 "봤다" 만 남기고 무엇이 정상인지 알려주지 않는다."""
    items = _checklist_items(device_checklist)

    assert len(items) >= 20, f"통합 체크리스트가 {len(items)} 개뿐이다"
    for item in items:
        assert "→" in item, item


@pytest.mark.parametrize(
    "needle",
    [
        "cold",
        "warm",
        "같은 날",
        "다음 날",
        "iOS",
        "Android",
        "Sandbox",
        "복원",
        "pending",
        "4040010",
        "유예",
        "UMP",
        "ATT",
        "새 게스트",
        "iPad",
        "rail",
        "배너",
        "결과 시트",
        "Split View",
        "가로",
    ],
)
def test_device_checklist_covers_every_item_the_spec_asks_for(device_checklist: str, needle: str):
    """스펙 Testing "실기기 체크리스트" + 티켓 37 의 추가 항목."""
    assert needle in device_checklist


# --- README "설계 판단" §C.32 ------------------------------------------------


@pytest.fixture(scope="module")
def readme() -> str:
    return _text(README)


@pytest.fixture(scope="module")
def c32_table(readme: str) -> str:
    return _subsection(readme, "### 37. 설계 판단 항목 점검")


@pytest.mark.parametrize(
    "item",
    [
        "퍼즐 언어 모델",
        "가림 포맷",
        "KST 고정",
        "id_token 교환",
        "구독 상태 판정표",
        "힌트 미리 보기",
        "로컬 알림",
        "애플 secret",
        "운영자 인증",
        "Slack",
    ],
)
def test_c32_checklist_lists_every_design_decision_item(c32_table: str, item: str):
    """스펙 §C.32 가 요구한 열 항목. 하나라도 빠지면 점검표가 거짓이 된다."""
    assert item in c32_table


def test_c32_checklist_points_at_sections_that_exist(c32_table: str, readme: str):
    """점검표가 가리키는 "NN. 제목" 이 실제 `### ` 제목이어야 한다."""
    quoted = README_SECTION_QUOTE.findall(c32_table)

    assert len(quoted) >= 10, quoted
    for title in quoted:
        assert f"### {title}\n" in readme, title


def test_readme_has_a_kst_design_decision(readme: str):
    """§C.32 의 "KST 고정" 은 ADR 0001 만 있고 README 절이 없었다 — 이 티켓이 채운다."""
    assert "### 37. KST 고정" in readme
    assert "0001-kst-fixed-day-boundary" in readme


def test_readme_flutter_section_states_the_interview_scope(readme: str):
    """스펙 Further Notes: 면접 설명 범위 = 백엔드 전부 + Flutter 는 세 가지."""
    flutter = _subsection(readme, "### 22. Flutter 앱")

    assert "면접 설명 범위" in flutter
    assert "상태 흐름" in flutter
    assert "SDK 선택" in flutter
    assert "테스트 경계" in flutter


@pytest.mark.parametrize("needle", ["권한 재확인 타이머", "로컬 알림"])
def test_readme_flutter_section_indexes_the_later_app_tickets(readme: str, needle: str):
    """상태 흐름·SDK·테스트 경계 뒤에 붙은 앱 판단(30·33)도 Flutter 절에서 찾아진다."""
    flutter = _subsection(readme, "### 22. Flutter 앱")

    assert needle in flutter


# --- 옛 티켓 번호 정리 (plan-add r1 번호 재배정) ------------------------------

# 구 번호 → 신 번호: 16→23, 23~34→25~36. 아래는 번호 재배정 **전에** 머지된 코드·
# 문서에 남아 있던 구 번호들이다(대응표: `review/plan-add-r1-response.md` §2).
STALE_TICKET_REFERENCES = [
    ("README.md", "티켓 22~31", "티켓 22~33"),
    ("README.md", "계정 연결·전환(티켓 27)", "계정 연결·전환(티켓 29)"),
    ("README.md", "로컬 알림(티켓 28)", "로컬 알림(티켓 30)"),
    ("docs/RELEASE.md", "서명·워크플로는 티켓 32", "서명·워크플로는 티켓 34"),
    ("docs/RELEASE.md", "최종본은 티켓 33 에서", "최종본은 티켓 35 에서"),
    ("docs/RELEASE.md", "티켓 08·16", "티켓 08·23"),
    ("app/services/word_service.py", "바꿔야 한다(티켓 16)", "바꿔야 한다(티켓 23)"),
    (
        "mobile/test/guest/guest_token_provider_test.dart",
        "티켓 27(계정 연결·전환)",
        "티켓 29(계정 연결·전환)",
    ),
    (
        "mobile/test/guest/guest_token_provider_test.dart",
        "티켓 28(로컬 알림)",
        "티켓 30(로컬 알림)",
    ),
    ("mobile/lib/config/firebase_bootstrap.dart", "티켓 24 가 이 결과를", "티켓 26 가 이 결과를"),
    ("mobile/lib/startup/startup_controller.dart", "(티켓 23·25)", "(티켓 25·27)"),
]


@pytest.mark.parametrize(
    ("path", "stale", "fixed"),
    STALE_TICKET_REFERENCES,
    ids=[f"{path}:{stale}" for path, stale, _ in STALE_TICKET_REFERENCES],
)
def test_old_ticket_numbers_are_renumbered(path: str, stale: str, fixed: str):
    text = _text(REPO_ROOT / path)

    assert stale not in text, f"{path}: 구 번호 '{stale}' 가 남아 있다"
    assert fixed in text, f"{path}: 신 번호 '{fixed}' 가 없다"


# --- 스펙 "미정 항목" 최종 상태 ----------------------------------------------

# 티켓에서 확정·해소된 번호(티켓 37 완료 조건). 나머지는 "운영 데이터 후" 또는
# 사람 작업·범위 밖으로 표시한다.
SETTLED_UNDECIDED = (9, 12, 13, 14, 18, 19, 20, 21, 22, 23, 24)
OPEN_UNDECIDED = (1, 6, 10, 11)


@pytest.fixture(scope="module")
def undecided_status() -> dict[int, str]:
    """스펙 "미정 항목" 끝의 최종 상태 표를 {번호: 상태} 로 읽는다."""
    body = _section(_text(SPEC), "## 미정 항목")
    rows = {}
    for line in body.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            rows[int(cells[0])] = cells[1]
    return rows


def test_the_spec_records_a_final_status_for_every_undecided_item(undecided_status):
    """번호 1~27 전부. 표에 없는 번호가 생기면 "남은 게 뭔지" 를 아무도 모른다."""
    expected = set(range(1, 28))

    assert set(undecided_status) == expected, sorted(expected - set(undecided_status))


@pytest.mark.parametrize("number", SETTLED_UNDECIDED)
def test_settled_undecided_items_name_the_ticket_that_settled_them(undecided_status, number: int):
    status = undecided_status[number]

    assert "티켓" in status, (number, status)
    assert re.search(r"(확정|해소)", status), (number, status)


@pytest.mark.parametrize("number", OPEN_UNDECIDED)
def test_open_undecided_items_are_marked_for_operational_data(undecided_status, number: int):
    assert "운영 데이터 후" in undecided_status[number], (number, undecided_status[number])


# --- 사용자 할 일 번호 · 알려진 한계 (코디네이터 추가 요구) ----------------------

USER_TODO = REPO_ROOT / ".scratch" / "store-launch" / "user-todo.md"


def test_the_human_order_references_every_user_todo_number(human_order: str):
    """`user-todo.md` 의 고정 번호 1~18 이 D0~D3 중 한 곳에는 걸려 있어야 한다 —
    번호가 빠지면 "내 차례가 언제인가" 를 그 파일만 보고 알 수 없다."""
    referenced = {int(number) for number in re.findall(r"`#(\d{1,2})`", human_order)}

    assert referenced == set(range(1, 19)), sorted(set(range(1, 19)) - referenced)


def test_the_human_order_does_not_duplicate_user_todo_state(human_order: str):
    """상태는 `user-todo.md` 가 정본이다 — 이 문서가 "끝/아직" 을 또 적으면 갈라진다."""
    assert "user-todo.md` 가 정본" in human_order or "그 파일이 정본" in human_order


@pytest.mark.parametrize(
    "needle",
    [
        "D-31-8",
        "D-33-3",
        "D-39-1",
        "D-38-1",
        "D-38-2",
        "D-17-6",
        "티켓 40",
        "Sandbox 결제",
        "배너 어댑티브 높이",
    ],
)
def test_known_limitations_section_collects_the_merged_minors(release: str, needle: str):
    """MINOR 로 머지한 것과 실기기로 넘긴 것을 한 절에 모은다(코디네이터 지시 5)."""
    limits = _section(release, "## 알려진 한계 (출시 시점)")

    assert needle in limits


def test_known_limitations_rows_cite_where_the_judgement_is_written(release: str):
    """판단의 출처가 없으면 다음 사람이 "MINOR 였는지" 를 처음부터 다시 따져야 한다."""
    limits = _section(release, "## 알려진 한계 (출시 시점)")

    assert limits.count("review/impl-review-") >= 5


def test_the_spec_ticket_range_includes_the_tickets_added_after_planning(release: str):
    """39 리뷰 D-39-2: 범위 표기가 `01~38` 에 멈춰 있었다. 38·40 은 계획 뒤 추가."""
    spec = _text(SPEC)

    assert "issues/01~40`" in spec
    assert "issues/01~38`" not in spec
    assert "### 39." in release


def test_every_ticket_section_heading_appears_once_at_the_start_of_a_line(release: str):
    """통합 목차가 `"### NN."` 로 절을 가리키기 때문에, 그 문자열은 본문에 여러 번 나온다.
    제목 자체는 **줄 머리에 한 번**뿐이어야 한다 — 절을 문자열로 잘라 읽는 테스트
    (`tests/test_app_deploy_workflow.py::_section_34`)가 엉뚱한 토막을 읽지 않게."""
    headings = re.findall(r"^### (\d{2})\.", release, re.M)

    assert len(headings) == len(set(headings)), sorted(headings)
