"""`/privacy`·`/terms` 렌더 테스트.

법적 문서는 스토어 심사·Play Data safety 양식이 가리키는 페이지라, "200 이 뜬다" 보다
"심사에 필요한 항목이 실제로 그 언어 본문에 있다" 를 확인해야 한다. 그래서 수집 항목·
제3자·국외 이전 같은 필수 항목을 언어별로 하나씩 문구로 검증한다.
"""

import importlib
from pathlib import Path

import pytest

from app import config

EN_HEADERS = {"Accept-Language": "en-US,en;q=0.9"}
KO_HEADERS = {"Accept-Language": "ko-KR,ko;q=0.9"}


def _body(client, path, **kwargs):
    res = client.get(path, **kwargs)
    assert res.status_code == 200
    return res.data.decode()


# --- 언어 전환 -------------------------------------------------------------


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_defaults_to_korean(client, path):
    res = client.get(path)

    assert res.status_code == 200
    assert '<html lang="ko">' in res.data.decode()
    assert res.headers["Content-Language"] == "ko"


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_accept_language_selects_english(client, path):
    html = _body(client, path, headers=EN_HEADERS)

    assert '<html lang="en">' in html


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_lang_query_beats_accept_language(client, path):
    # 스토어·앱이 링크로 특정 언어 문서를 고정해야 한다.
    assert '<html lang="en">' in _body(client, f"{path}?lang=en", headers=KO_HEADERS)
    assert '<html lang="ko">' in _body(client, f"{path}?lang=ko", headers=EN_HEADERS)


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_unknown_lang_falls_back(client, path):
    assert '<html lang="ko">' in _body(client, f"{path}?lang=fr")


# 브라우저가 보내는 흔한 조합: 선호 언어에는 지역 꼬리표가 붙고, 두 번째 언어는 낮은
# q 값으로 온다. 이때 q 값이 높은 쪽을 골라야 한다 (D-09-2).
@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@pytest.mark.parametrize(
    ("accept_language", "expected"),
    [
        ("en-US,ko;q=0.1", "en"),
        ("ko-KR,en;q=0.1", "ko"),
    ],
)
def test_region_tag_does_not_lose_to_low_q_language(client, path, accept_language, expected):
    res = client.get(path, headers={"Accept-Language": accept_language})

    assert res.status_code == 200
    assert res.headers["Content-Language"] == expected
    assert f'<html lang="{expected}">' in res.data.decode()


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_both_languages_are_discoverable(client, path):
    html = _body(client, path)

    assert f'<link rel="alternate" hreflang="ko" href="{path}?lang=ko"' in html
    assert f'<link rel="alternate" hreflang="en" href="{path}?lang=en"' in html
    # 사람이 쓸 전환 링크도 있다
    assert 'href="?lang=en"' in html


# --- 공용 토큰 CSS 사용 ----------------------------------------------------


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_uses_shared_token_stylesheet(client, path):
    html = _body(client, path)

    assert "/static/tokens.css" in html
    assert "/static/legal.css" in html
    # 기존 메인 페이지 스타일시트는 쓰지 않는다 (티켓 18 에서 교체될 파일)
    assert "/static/style.css" not in html
    assert "pretendard" in html.lower()


# --- 개인정보처리방침 필수 항목 --------------------------------------------

PRIVACY_REQUIRED_KO = [
    # 수집 항목
    "게스트 토큰",
    "계정 이메일",
    "refresh token",
    "시도 기록",
    "구독 식별자",
    "광고 ID",
    # 그 밖의 필수 항목
    "보유 기간",
    "제3자",
    "위탁",
    "국외 이전",
    "만 14세 미만",
    # 제3자 목록
    "Google",
    "Apple",
    "AdMob",
    "Firebase Analytics",
    "Sentry",
]

PRIVACY_REQUIRED_EN = [
    "guest token",
    "account email",
    "refresh token",
    "attempt history",
    "subscription identifier",
    "advertising id",
    "how long we keep it",
    "third part",
    "processors",
    "international transfer",
    "under 14",
    "google",
    "apple",
    "admob",
    "firebase analytics",
    "sentry",
]


# 문구 검증은 대소문자를 무시한다 — 확인하려는 건 "그 공시가 본문에 있는지" 이고,
# 제목에 쓰이면 대문자로 시작한다는 사정까지 테스트가 묶을 일은 아니다.
@pytest.mark.parametrize("phrase", PRIVACY_REQUIRED_KO)
def test_privacy_ko_covers_required_disclosures(client, phrase):
    assert phrase.lower() in _body(client, "/privacy?lang=ko").lower()


@pytest.mark.parametrize("phrase", PRIVACY_REQUIRED_EN)
def test_privacy_en_covers_required_disclosures(client, phrase):
    assert phrase.lower() in _body(client, "/privacy?lang=en").lower()


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_privacy_links_deletion_page_and_contact(client, app, lang):
    html = _body(client, f"/privacy?lang={lang}")
    contact = app.config["LEGAL_CONTACT_EMAIL"]

    assert "/account/delete" in html
    assert contact in html
    assert f"mailto:{contact}" in html


def test_contact_email_defaults_to_the_operator_address(app):
    # 환경변수로 뺐지만 기본값은 그대로 운영자 주소다 — 설정을 깜빡해도 문서에
    # 연락처가 비지 않아야 한다(스토어 심사·Play Data safety 가 요구한다).
    assert app.config["LEGAL_CONTACT_EMAIL"] == "hsseo@dosaem.com"


def test_empty_contact_email_env_falls_back_to_the_default(monkeypatch):
    # `.env.example` 은 `LEGAL_CONTACT_EMAIL=` 로 키만 둔다. 그대로 복사해 쓰면
    # 환경에는 빈 문자열이 들어오는데, 그때도 기본값으로 떨어져야 한다.
    monkeypatch.setenv("LEGAL_CONTACT_EMAIL", "")
    importlib.reload(config)

    try:
        assert config.Config.LEGAL_CONTACT_EMAIL == "hsseo@dosaem.com"
    finally:
        monkeypatch.undo()
        importlib.reload(config)


# --- 국외 이전 거부 방법 (D-09-1) ------------------------------------------
#
# 서비스 사양상 앱 광고(AdMob)·분석(Firebase Analytics)·오류 추적(Sentry)은 계정 연결
# 여부와 무관하게 동작한다(스펙 §B.21 광고 게이트는 UMP 상태, §B.24 분석, §C.30 Sentry).
# 그래서 "게스트로만 플레이하면 국외 이전을 피할 수 있다" 는 안내는 실제로 전송을
# 멈추지 못하는 방법을 거부 절차로 제시하는 것이다. 아래 테스트는 4절 본문만 떼어
# 검사한다 — 같은 단어가 다른 절에 있어도 통과하지 않게.


def _international_transfer_section(client, lang: str) -> str:
    """4절(국외 이전) 본문만 떼어낸다. 절 번호는 두 언어가 같다."""
    html = _body(client, f"/privacy?lang={lang}")
    start = html.index("<h2>4.")
    return html[start : html.index("<h2>5.", start)]


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_transfer_section_is_the_international_transfer_section(client, lang):
    # 아래 두 테스트가 엉뚱한 절을 보고 통과하지 않게 먼저 못을 박는다.
    section = _international_transfer_section(client, lang).lower()

    assert ("국외 이전" if lang == "ko" else "international transfer") in section
    assert "admob" in section
    assert "sentry" in section


# "계정 연결 안 함 = 국외 이전 거부" 라는 틀린 안내를 다시 넣지 못하게 막는다.
@pytest.mark.parametrize(
    ("lang", "forbidden"),
    [
        ("ko", ["게스트로만 플레이", "게스트로 플레이하면"]),
        ("en", ["play as a guest without linking", "play as a guest instead"]),
    ],
)
def test_transfer_section_does_not_sell_guest_play_as_opt_out(client, lang, forbidden):
    section = _international_transfer_section(client, lang).lower()

    for phrase in forbidden:
        assert phrase.lower() not in section


# 거부 방법을 기능별로 정확하게 구분한다: 계정 연결과 무관하게 전송되는 것이 있고,
# 광고는 ATT·UMP 로 맞춤만 끌 수 있고, 분석·오류 추적은 개별 거부 수단이 없다.
PRIVACY_TRANSFER_KO = [
    "계정을 연결하지 않아도",
    "광고 개인정보 설정",
    "추적 허용",
    "개별 거부 수단",
    "구독",
]

PRIVACY_TRANSFER_EN = [
    "even without a linked account",
    "ad privacy settings",
    "tracking permission",
    "no per-feature opt-out",
    "subscription",
]


@pytest.mark.parametrize("phrase", PRIVACY_TRANSFER_KO)
def test_transfer_section_ko_states_real_opt_outs(client, phrase):
    assert phrase.lower() in _international_transfer_section(client, "ko").lower()


@pytest.mark.parametrize("phrase", PRIVACY_TRANSFER_EN)
def test_transfer_section_en_states_real_opt_outs(client, phrase):
    assert phrase.lower() in _international_transfer_section(client, "en").lower()


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_privacy_states_backup_retention(client, lang):
    # 매일 백업 덤프를 14일 보존하므로(티켓 21), 삭제 후에도 그만큼 남는다는 사실을 적는다.
    assert "14" in _body(client, f"/privacy?lang={lang}")


# --- 이용약관 필수 항목 ----------------------------------------------------

TERMS_REQUIRED_KO = ["자동 갱신", "해지", "App Store", "Google Play", "EULA"]
TERMS_REQUIRED_EN = ["automatically renew", "cancel", "App Store", "Google Play", "EULA"]


@pytest.mark.parametrize("phrase", TERMS_REQUIRED_KO)
def test_terms_ko_covers_subscription_rules(client, phrase):
    assert phrase.lower() in _body(client, "/terms?lang=ko").lower()


@pytest.mark.parametrize("phrase", TERMS_REQUIRED_EN)
def test_terms_en_covers_subscription_rules(client, phrase):
    assert phrase.lower() in _body(client, "/terms?lang=en").lower()


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_terms_marks_eula_choice_as_pending(client, lang):
    # 미정 9(Apple 표준 EULA vs 커스텀)이 사람 결정이라, 표준 EULA 링크 자리를 둔다.
    html = _body(client, f"/terms?lang={lang}")

    assert "apple.com/legal/internet-services/itunes/dev/stdeula" in html


# --- 문서 메타 ------------------------------------------------------------


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_shows_effective_date(client, path):
    # 갱신 책임자가 "언제 기준 문서인지" 를 바로 볼 수 있어야 한다.
    assert "2026" in _body(client, path)


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_cross_links_the_other_document(client, path):
    html = _body(client, path)

    assert 'href="/privacy' in html
    assert 'href="/terms' in html


# --- 운영자 정보 블록 ------------------------------------------------------
#
# 사업자 정보는 아직 실제 값이 없다(출시 전 사람이 채운다 — docs/RELEASE.md "### 09.").
# 그래서 두 상태를 모두 검증한다: 비어 있을 때 서비스명·연락처만 나오는지, 값을
# 채우면 그 항목만 늘어나는지. 값을 코드에 넣어 두지 않았다는 것도 같이 고정한다.

OPERATOR_FIELD_LABELS_KO = [
    "상호",
    "대표자",
    "사업자등록번호",
    "통신판매업 신고번호",
    "주소",
]

OPERATOR_FIELD_LABELS_EN = [
    "Business name",
    "Representative",
    "Business registration number",
    "Mail-order business registration no.",
    "Address",
]

FILLED_BUSINESS_CONFIG = {
    "LEGAL_BUSINESS_NAME": "테스트 상호",
    "LEGAL_REPRESENTATIVE": "테스트 대표",
    "LEGAL_BUSINESS_REG_NO": "000-00-00000",
    "LEGAL_MAIL_ORDER_REG_NO": "제0000-서울-0000호",
    "LEGAL_BUSINESS_ADDRESS": "서울특별시 테스트구 테스트로 1",
}


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_operator_block_shows_service_and_contact(client, app, path, lang):
    html = _body(client, f"{path}?lang={lang}")
    heading = "운영자 정보" if lang == "ko" else "Operator information"

    assert heading in html
    assert "chosung.dosaem.com" in html
    assert f"mailto:{app.config['LEGAL_CONTACT_EMAIL']}" in html


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@pytest.mark.parametrize(
    ("lang", "labels"),
    [("ko", OPERATOR_FIELD_LABELS_KO), ("en", OPERATOR_FIELD_LABELS_EN)],
)
def test_unset_business_info_is_not_rendered(client, path, lang, labels):
    # 기본 설정은 전부 빈 문자열이라 "상호: (빈칸)" 같은 줄이 생기면 안 된다.
    html = _body(client, f"{path}?lang={lang}")

    for label in labels:
        assert f"<dt>{label}</dt>" not in html


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
@pytest.mark.parametrize(
    ("lang", "labels"),
    [("ko", OPERATOR_FIELD_LABELS_KO), ("en", OPERATOR_FIELD_LABELS_EN)],
)
def test_set_business_info_is_rendered(client, app, path, lang, labels):
    app.config.update(FILLED_BUSINESS_CONFIG)

    html = _body(client, f"{path}?lang={lang}")

    for label in labels:
        assert f"<dt>{label}</dt>" in html
    for value in FILLED_BUSINESS_CONFIG.values():
        assert value in html


@pytest.mark.parametrize("path", ["/privacy", "/terms"])
def test_partially_set_business_info_renders_only_filled_rows(client, app, path):
    # 사업자 등록만 끝나고 통신판매업 신고가 아직인 중간 상태.
    app.config.update(
        LEGAL_BUSINESS_NAME="테스트 상호",
        LEGAL_REPRESENTATIVE="테스트 대표",
        LEGAL_BUSINESS_REG_NO="000-00-00000",
    )

    html = _body(client, f"{path}?lang=ko")

    assert "<dt>상호</dt>" in html
    assert "<dt>사업자등록번호</dt>" in html
    assert "<dt>통신판매업 신고번호</dt>" not in html
    assert "<dt>주소</dt>" not in html


def test_business_info_values_are_not_hardcoded():
    # 값은 환경변수에서만 온다. 코드에 지어 넣은 상호·등록번호가 없어야 한다.
    config_py = (Path(__file__).resolve().parent.parent / "app" / "config.py").read_text(
        encoding="utf-8"
    )

    for name in [
        "LEGAL_BUSINESS_NAME",
        "LEGAL_REPRESENTATIVE",
        "LEGAL_BUSINESS_REG_NO",
        "LEGAL_MAIL_ORDER_REG_NO",
        "LEGAL_BUSINESS_ADDRESS",
    ]:
        assert f'{name} = os.environ.get("{name}", "")' in config_py
