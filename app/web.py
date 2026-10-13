from datetime import date

from flask import Blueprint, render_template, request

from app.utils.ui_language import resolve_ui_language

bp = Blueprint("web", __name__)

# 법적 문서의 시행일. 본문을 고칠 때 이 날짜도 같이 올린다 (README "법적 문서" 절).
LEGAL_EFFECTIVE_DATE = date(2026, 10, 14)

# 문서에 싣는 공개 연락처. 운영자 계정 두 개(CONTEXT.md "운영자") 중 Play 조직 계정을
# 쓴다 — 스토어 콘솔·Play Data safety 양식이 가리키는 주소와 같아야 한다. 환경변수로
# 빼지 않는 이유: CONTEXT.md 가 "이 둘 중 하나로만 한다" 로 고정한 프로젝트 사실이라
# 배포 환경마다 달라질 값이 아니다.
LEGAL_CONTACT_EMAIL = "hsseo@dosaem.com"

# 미정 9(Apple 표준 EULA vs 커스텀)의 기본 선택지. 커스텀 약관으로 가면 이 링크를 지운다.
APPLE_STANDARD_EULA_URL = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"


@bp.get("/")
def index():
    """게임 화면. 정적 틀만 서버에서 내려주고, 나머지는 vanilla JS가
    /api/v1/*를 호출해서 채운다 (web/static/app.js)."""
    return render_template("index.html")


@bp.get("/privacy")
def privacy():
    """개인정보처리방침. 스토어 심사·Play Data safety 양식이 가리키는 URL."""
    return _render_legal_document("privacy")


@bp.get("/terms")
def terms():
    """이용약관. 구독 화면(Paywall)과 스토어 등록 정보가 가리키는 URL."""
    return _render_legal_document("terms")


def _render_legal_document(name: str):
    """ko/en 본문을 각각 템플릿 파일로 두고 UI 언어로 고른다.

    한 템플릿 안에서 if 로 두 언어를 섞지 않는 이유: 본문이 길어서 번역이 섞이면
    어느 언어를 고쳤는지 diff 로 안 보이고, 한쪽만 고쳐진 문서가 나간다.
    """
    language = resolve_ui_language(request.args.get("lang"), request.headers.get("Accept-Language"))
    html = render_template(
        f"legal/{name}.{language}.html",
        ui_language=language,
        effective_date=LEGAL_EFFECTIVE_DATE,
        contact_email=LEGAL_CONTACT_EMAIL,
        apple_standard_eula_url=APPLE_STANDARD_EULA_URL,
    )
    # 심사자·크롤러가 Accept-Language 없이 받아도 어느 언어인지 알 수 있게 명시한다.
    return html, 200, {"Content-Language": language}


def register_web(app):
    app.register_blueprint(bp)
