from datetime import date

from flask import Blueprint, current_app, render_template, request

from app.utils.ui_language import resolve_ui_language

bp = Blueprint("web", __name__)

# 법적 문서의 시행일. 본문을 고칠 때 이 날짜도 같이 올린다 (README "법적 문서" 절).
LEGAL_EFFECTIVE_DATE = date(2026, 10, 14)

# 미정 9(Apple 표준 EULA vs 커스텀)의 기본 선택지. 커스텀 약관으로 가면 이 링크를 지운다.
APPLE_STANDARD_EULA_URL = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"

# 문서 "운영자 정보" 블록에 싣는 사업자 정보: (설정 키, ko 라벨, en 라벨).
# 전자상거래법 표기 순서를 그대로 쓴다. 값은 설정에서만 오고 코드에 없다 —
# 사업자 등록 전에는 전부 비어 있고, 그러면 서비스명과 연락처만 렌더된다.
LEGAL_BUSINESS_FIELDS = (
    ("LEGAL_BUSINESS_NAME", "상호", "Business name"),
    ("LEGAL_REPRESENTATIVE", "대표자", "Representative"),
    ("LEGAL_BUSINESS_REG_NO", "사업자등록번호", "Business registration number"),
    ("LEGAL_MAIL_ORDER_REG_NO", "통신판매업 신고번호", "Mail-order business registration no."),
    ("LEGAL_BUSINESS_ADDRESS", "주소", "Address"),
)


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
        contact_email=current_app.config["LEGAL_CONTACT_EMAIL"],
        business_info=_business_info(language),
        apple_standard_eula_url=APPLE_STANDARD_EULA_URL,
    )
    # 심사자·크롤러가 Accept-Language 없이 받아도 어느 언어인지 알 수 있게 명시한다.
    return html, 200, {"Content-Language": language}


def _business_info(language: str) -> list[tuple[str, str]]:
    """설정에 값이 있는 사업자 정보 항목만 (라벨, 값) 으로 돌려준다.

    없는 값을 "미등록" 같은 문구로 채우지 않는다: 사업자 등록 전에 빈 목록을 돌려주면
    템플릿이 서비스명·연락처만 보여주고, 등록 후 환경변수를 채우면 그 항목만 늘어난다.
    """
    info = []
    for key, label_ko, label_en in LEGAL_BUSINESS_FIELDS:
        value = (current_app.config.get(key) or "").strip()
        if value:
            info.append((label_ko if language == "ko" else label_en, value))
    return info


def register_web(app):
    app.register_blueprint(bp)
