"""`docs/legal-checklist.md` 와 법적 문서 본문을 묶는 테스트.

체크리스트는 "어느 조문 → 문서의 어느 절 → 어느 테스트" 표다. 표만 있으면 문서를
고치다가 절을 지워도 아무도 모르니, **표를 파싱해서 그 절 id 가 ko·en 두 본문에 실제로
있는지** 를 테스트가 지킨다. 반대 방향(본문에 있는 절이 표에 없는 경우)도 막는다 —
표가 문서보다 늦게 늘면 체크리스트가 거짓이 된다.

`tests/test_legal_pages.py` 는 "페이지가 뜨고 언어가 갈리는지" 를 보고, 이 파일은
"법이 요구한 항목이 두 언어에 같은 구조로 있는지" 를 본다.
"""

import re
from pathlib import Path

import pytest
from gunicorn.config import Config as GunicornConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_PATH = REPO_ROOT / "docs" / "legal-checklist.md"

# 체크리스트 "문서·절 id" 칸의 표기: `privacy#collection` / `terms#subscription`
SECTION_REF = re.compile(r"`(privacy|terms)#([a-z0-9-]+)`")

# 조문 표의 헤더. 이 헤더를 가진 표의 행만 "조문 → 절" 매핑으로 읽는다
# (사람 결정 표·절 id 목록 표는 열 구성이 달라서 섞이지 않는다).
CLAUSE_TABLE_HEADER = ("근거(조문·정책)", "요구 내용", "문서·절 id", "확인 테스트")

HEADING_ID = re.compile(r'<h2 id="([a-z0-9-]+)"')
DEFINITION_TERM = re.compile(r"<dt>(.+?)</dt>", re.DOTALL)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _clause_rows() -> list[list[str]]:
    """조문 표의 데이터 행만 모은다. 헤더를 따라가며 표를 구분한다."""
    rows = []
    in_clause_table = False
    for line in CHECKLIST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            in_clause_table = False
            continue
        cells = _cells(line)
        if tuple(cells) == CLAUSE_TABLE_HEADER:
            in_clause_table = True
            continue
        if not in_clause_table:
            continue
        if all(set(cell) <= set("-: ") for cell in cells):  # 구분선
            continue
        rows.append(cells)
    return rows


def _section_refs() -> set[tuple[str, str]]:
    return {ref for row in _clause_rows() for ref in SECTION_REF.findall(row[2])}


def _page(client, document: str, language: str) -> str:
    res = client.get(f"/{document}?lang={language}")
    assert res.status_code == 200
    return res.data.decode()


def _section(html: str, section_id: str) -> str:
    """한 절의 본문만 떼어낸다 — 다음 `<h2 id=` 또는 문서 끝까지."""
    start = html.index(f'<h2 id="{section_id}"')
    rest = html[start:]
    next_heading = HEADING_ID.search(rest, pos=1)
    return rest[: next_heading.start()] if next_heading else rest


# --- 표 자체 ---------------------------------------------------------------


def test_the_clause_tables_are_parseable():
    rows = _clause_rows()

    # 개보법 §30·§28의8·전상법·스토어 정책·해외 고지를 합치면 30행이 넘는다.
    # 표가 통째로 날아가도 "0행 통과" 가 되지 않게 하한을 둔다.
    assert len(rows) >= 30
    for row in rows:
        assert len(row) == len(CLAUSE_TABLE_HEADER)


def test_every_clause_row_points_at_a_document_section():
    for row in _clause_rows():
        assert SECTION_REF.findall(row[2]), f"절 id 가 없는 행: {row[0]}"
        assert row[3], f"확인 테스트가 빈 행: {row[0]}"


# --- ① 표의 절 id 가 두 언어 본문에 있다 -----------------------------------


@pytest.mark.parametrize(("document", "section_id"), sorted(_section_refs()))
@pytest.mark.parametrize("language", ["ko", "en"])
def test_every_checklist_section_id_exists_in_both_languages(
    client, language, document, section_id
):
    assert f'id="{section_id}"' in _page(client, document, language)


@pytest.mark.parametrize("document", ["privacy", "terms"])
@pytest.mark.parametrize("language", ["ko", "en"])
def test_rendered_section_ids_are_all_in_the_checklist(client, document, language):
    """본문에만 있고 체크리스트에 없는 절을 막는다 — 표가 문서보다 늦게 늘지 않게."""
    rendered = set(HEADING_ID.findall(_page(client, document, language)))
    listed = {section_id for doc, section_id in _section_refs() if doc == document}

    assert rendered <= listed, f"체크리스트에 없는 절: {sorted(rendered - listed)}"


# --- ② ko·en 절 구조·순서가 같다 -------------------------------------------


@pytest.mark.parametrize("document", ["privacy", "terms"])
def test_section_ids_match_in_order_across_languages(client, document):
    ko = HEADING_ID.findall(_page(client, document, "ko"))
    en = HEADING_ID.findall(_page(client, document, "en"))

    assert ko == en
    assert len(ko) == len(set(ko)), f"같은 id 가 두 번: {ko}"


# --- ③ 핵심 문구 ----------------------------------------------------------
#
# 조문이 "무엇을 적어라" 를 요구하는 항목 중, 문구가 사라지면 공시가 사라지는 것들만
# 고정한다. 번역이 흔들려도 되는 설명문은 넣지 않는다.

PRIVACY_PHRASES_KO = [
    "14일",  # 백업 보존 = 삭제 후 잔존 기간
    "7일",  # 애플 revoke 재시도 보관
    "보유 기간",
    "파기",
    "국외 이전",
    "이전을 거부",
    "만 14세",
    "개인정보 보호책임자",
    "열람",
    "118",  # 개인정보침해신고센터
    "1833-6972",  # 개인정보 분쟁조정위원회
    "쿠키",
    "광고 ID 초기화",
    "법적 근거",  # 해외 사용자 절(GDPR 처리 근거)
    "시행일",
]

PRIVACY_PHRASES_EN = [
    "14 days",
    "7 days",
    "how long we keep",
    "destroy",
    "international transfer",
    "refuse the transfer",
    "under 14",
    "privacy officer",
    "access request",
    "118",
    "1833-6972",
    "cookie",
    "reset the advertising id",
    "legal basis",
    "supervisory authority",
    "do not sell",
    "effective date",
]

TERMS_PHRASES_KO = [
    "자동 갱신",
    "해지",
    "App Store",
    "Google Play",
    "환불",
    "청약철회",
    "디지털 콘텐츠",
    "호스팅",
]

TERMS_PHRASES_EN = [
    "auto-renew",
    "cancel",
    "App Store",
    "Google Play",
    "refund",
    "withdraw",
    "digital content",
    "hosting",
]


@pytest.mark.parametrize("phrase", PRIVACY_PHRASES_KO)
def test_privacy_ko_has_the_required_phrases(client, phrase):
    assert phrase.lower() in _page(client, "privacy", "ko").lower()


@pytest.mark.parametrize("phrase", PRIVACY_PHRASES_EN)
def test_privacy_en_has_the_required_phrases(client, phrase):
    assert phrase.lower() in _page(client, "privacy", "en").lower()


@pytest.mark.parametrize("phrase", TERMS_PHRASES_KO)
def test_terms_ko_has_the_required_phrases(client, phrase):
    assert phrase.lower() in _page(client, "terms", "ko").lower()


@pytest.mark.parametrize("phrase", TERMS_PHRASES_EN)
def test_terms_en_has_the_required_phrases(client, phrase):
    assert phrase.lower() in _page(client, "terms", "en").lower()


# --- 국외 이전: 받는 자별 한 행 (개보법 §28의8②) ---------------------------
#
# 받는 자 연락처는 각사가 공개한 개인정보 문서 URL 만 쓴다(추정 금지 — 티켓 PA-7).
# 그래서 "이름" 과 "그 회사가 공개한 URL" 을 짝으로 고정한다.

OVERSEAS_RECIPIENTS = [
    ("Google", "policies.google.com/privacy"),
    ("Apple", "apple.com/legal/privacy"),
    ("AdMob", "policies.google.com/technologies/ads"),
    ("Firebase", "firebase.google.com/support/privacy"),
    ("Sentry", "sentry.io/privacy"),
]


@pytest.mark.parametrize(("recipient", "policy_url"), OVERSEAS_RECIPIENTS)
@pytest.mark.parametrize("language", ["ko", "en"])
def test_overseas_section_lists_every_recipient(client, language, recipient, policy_url):
    section = _section(_page(client, "privacy", language), "overseas").lower()

    assert recipient.lower() in section
    assert policy_url in section


# --- ④ 삭제 페이지와 방침이 같은 약속을 한다 -------------------------------


@pytest.mark.parametrize("language", ["ko", "en"])
def test_delete_page_is_linked_from_the_rights_section(client, language):
    """권리 행사 방법 절이 실제 삭제 페이지를 가리켜야 한다(개보법 §30①5)."""
    section = _section(_page(client, "privacy", language), "rights")

    assert f"/account/delete?lang={language}" in section


@pytest.mark.parametrize("language", ["ko", "en"])
def test_deleted_data_names_are_a_subset_of_the_policy_items(client, web_login, language):
    """삭제 페이지가 "지운다" 고 적은 항목은 방침 "처리 항목" 절에 있어야 한다.

    부분집합으로 비교한다 — 방침에는 삭제 대상이 아닌 항목(광고 ID 처럼 서버에
    저장하지 않는 것, 접속·오류 기록)도 있어서 양쪽이 같을 수는 없다. 반대로 삭제
    페이지에만 있는 이름은 "방침에 없는 데이터를 지운다" 는 뜻이라 막아야 한다.
    """
    web_login()

    res = client.get(f"/account/delete?lang={language}")
    assert res.status_code == 200
    deleted = set(DEFINITION_TERM.findall(res.data.decode()))
    collected = set(
        DEFINITION_TERM.findall(_section(_page(client, "privacy", language), "collection"))
    )

    assert deleted, "삭제 페이지에 항목 목록이 없다 — 세션이 안 심겼을 수 있다"
    assert deleted <= collected, f"방침에 없는 항목: {sorted(deleted - collected)}"


# --- 사업자 정보는 레포에 없다 ---------------------------------------------

BUSINESS_REG_NO = re.compile(r"\d{3}-\d{2}-\d{5}")

# 사업자등록번호가 섞여 들어갈 수 있는 곳: 템플릿·설정·문서. 테스트 파일은 제외다 —
# 거기엔 "값이 채워지면 렌더되는지" 를 보려고 더미 번호가 들어 있다.
SCANNED_PATHS = ["web/templates", "app", "docs", "README.md", ".env.example"]


def test_repo_has_no_business_registration_number():
    offenders = []
    for target in (REPO_ROOT / path for path in SCANNED_PATHS):
        files = sorted(target.rglob("*")) if target.is_dir() else [target]
        for path in files:
            if not path.is_file():
                continue
            found = BUSINESS_REG_NO.findall(path.read_text(encoding="utf-8", errors="ignore"))
            if found:
                offenders.append((path.relative_to(REPO_ROOT).as_posix(), found))

    assert not offenders, f"사업자등록번호 패턴이 들어 있다: {offenders}"


# --- 수정 라운드 1 · D-16-2: 백업 보호 조치가 실제 백업 방식과 같다 ---------


def test_the_backup_script_only_compresses_the_dump():
    """재현 고정: 백업은 gzip 압축만 한다 — 암호화 단계가 없다.

    방침이 "암호화된 덤프" 를 보장하면 이 스크립트 때문에 거짓이 된다(D-16-2).
    암호화를 **구현하라는** 테스트가 아니라, 고지가 따라가야 하는 현행 방식을 못 박는다.
    """
    script = (REPO_ROOT / "scripts" / "backup.sh").read_text(encoding="utf-8")

    assert "| gzip -c" in script
    assert not re.search(r"\b(openssl|gpg|age)\b|--encrypt", script)


BACKUP_WORDING = {
    "ko": {"required": ["압축된 덤프", "암호화하지는 않"], "forbidden": ["암호화된 덤프"]},
    "en": {
        "required": ["compressed dump", "are not encrypted"],
        "forbidden": ["encrypted dump"],
    },
}


@pytest.mark.parametrize("language", ["ko", "en"])
def test_destruction_section_describes_the_real_backup_protection(client, language):
    section = _section(_page(client, "privacy", language), "destruction").lower()
    wording = BACKUP_WORDING[language]

    for phrase in wording["required"]:
        assert phrase.lower() in section, f"{language} 파기 절에 없는 문구: {phrase}"
    for phrase in wording["forbidden"]:
        assert phrase.lower() not in section, f"{language} 파기 절의 과장 문구: {phrase}"


# --- 수정 라운드 1 · D-16-3: 서버 로그 보유 기간이 구현에 근거한다 ---------


def test_the_production_entrypoint_has_no_access_log():
    """재현 고정: 운영 실행 경로에 요청 접근 로그 설정이 없다(D-16-3).

    Gunicorn 기본값이 "접근 로그 없음" 이고 Dockerfile·compose 가 그 기본값을
    덮어쓰지 않는다. 그래서 방침이 "접속기록을 1년 이상 보관한다" 고 적으면 근거가 없다.
    """
    assert GunicornConfig().accesslog is None

    for name in ("Dockerfile", "docker-compose.prod.yml"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "accesslog" not in text, name
        assert "access-logfile" not in text, name


LOG_RETENTION_WORDING = {
    "ko": {
        "required": ["따로 모아 보관하지 않", "출시 전"],
        "forbidden": ["1년 이상 보관", "법령이 정한 기간이 지나면 삭제"],
    },
    "en": {
        "required": ["not collected into separate storage", "before launch"],
        "forbidden": ["at least a year", "once the period required by law has passed"],
    },
}


@pytest.mark.parametrize("language", ["ko", "en"])
def test_privacy_does_not_promise_unimplemented_log_retention(client, language):
    page = _page(client, "privacy", language).lower()
    wording = LOG_RETENTION_WORDING[language]

    for phrase in wording["required"]:
        assert phrase.lower() in page, f"{language} 방침에 없는 문구: {phrase}"
    for phrase in wording["forbidden"]:
        assert phrase.lower() not in page, f"{language} 방침의 근거 없는 보유 약속: {phrase}"
