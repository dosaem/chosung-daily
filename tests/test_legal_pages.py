"""`/privacy`·`/terms` 렌더 테스트.

법적 문서는 스토어 심사·Play Data safety 양식이 가리키는 페이지라, "200 이 뜬다" 보다
"심사에 필요한 항목이 실제로 그 언어 본문에 있다" 를 확인해야 한다. 그래서 수집 항목·
제3자·국외 이전 같은 필수 항목을 언어별로 하나씩 문구로 검증한다.
"""

import pytest

from app.web import LEGAL_CONTACT_EMAIL

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
def test_privacy_links_deletion_page_and_contact(client, lang):
    html = _body(client, f"/privacy?lang={lang}")

    assert "/account/delete" in html
    assert LEGAL_CONTACT_EMAIL in html
    assert f"mailto:{LEGAL_CONTACT_EMAIL}" in html


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
