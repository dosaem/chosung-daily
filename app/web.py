from datetime import date

from flask import Blueprint, current_app, redirect, render_template, request, session

from app.access_log import remember_actor
from app.csrf import csrf_protected, issue_csrf_token
from app.errors import ForbiddenError, UnauthorizedError
from app.extensions import db
from app.models import Guest
from app.services.account_deletion_service import delete_guest_account
from app.utils.ui_language import resolve_ui_language
from app.utils.ui_strings import strings_for

bp = Blueprint("web", __name__)

# 확인 폼을 그릴 때 "이 폼이 지우려는 게스트" 를 적어 두는 세션 키. CSRF 토큰과
# 짝으로 쓴다 — 토큰은 "이 폼을 우리가 그려줬다" 만 증명하고 대상은 증명하지 않는다.
DELETE_TARGET_SESSION_KEY = "delete_target_guest_id"

# 법적 문서의 시행일. 본문을 고칠 때 이 날짜도 같이 올린다 (README "법적 문서" 절).
LEGAL_EFFECTIVE_DATE = date(2026, 10, 16)

# 미정 9(Apple 표준 EULA vs 커스텀)의 기본 선택지. 커스텀 약관으로 가면 이 링크를 지운다.
APPLE_STANDARD_EULA_URL = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"

# 문서 "운영자 정보" 블록(`legal/_business_info.html`)에 싣는 사업자 정보:
# (설정 키, ko 라벨, en 라벨). 순서는 전자상거래법 제10조 제1항의 표기 순서다 —
# 상호·대표자 → 주소·전화·이메일 → 등록번호 → 통신판매업 신고번호.
# 값은 설정에서만 오고 코드에 없다 — 사업자 등록 전에는 전부 비어 있고, 그러면
# 서비스명·연락처·호스팅만 렌더된다(티켓 16: 레포에 상호·주소·등록번호를 적지 않는다).
LEGAL_BUSINESS_FIELDS = (
    ("LEGAL_BUSINESS_NAME", "상호", "Business name"),
    ("LEGAL_REPRESENTATIVE", "대표자", "Representative"),
    ("LEGAL_BUSINESS_ADDRESS", "주소", "Address"),
    ("LEGAL_BUSINESS_PHONE", "전화번호", "Phone"),
    ("LEGAL_BUSINESS_REG_NO", "사업자등록번호", "Business registration number"),
    ("LEGAL_MAIL_ORDER_REG_NO", "통신판매업 신고번호", "Mail-order business registration no."),
)


@bp.get("/")
def index():
    """게임 화면. 정적 틀과 UI 문구만 서버에서 내려주고, 나머지는 vanilla JS가
    /api/v1/*를 호출해서 채운다 (web/static/app.js).

    문구는 UI 언어로 고른 한 벌만 내려간다 — 템플릿은 `t.key` 로, JS 는 같은 사전을
    인라인 JSON(`#ui-strings`)에서 읽는다. 언어 판정은 법적 문서 페이지와 같은
    `resolve_ui_language` 다(`?lang=` > Accept-Language > ko).
    """
    language = _requested_ui_language()
    html = render_template(
        "index.html",
        ui_language=language,
        t=strings_for(language),
        # 스토어 링크·앱 ID 는 08 이 만든 설정값이다. 스토어 등록 전에는 비어 있고,
        # 그러면 템플릿이 배지와 Smart App Banner 메타 태그를 아예 안 그린다
        # (티켓 18 — README "18. 웹 앱 CTA").
        store_url_ios=current_app.config["STORE_URL_IOS"],
        store_url_android=current_app.config["STORE_URL_ANDROID"],
        app_store_id=current_app.config["APP_STORE_ID"],
        # 푸터가 법적 문서와 **같은 조각**(`legal/_business_info.html`)을 include
        # 한다 — 전자상거래법 제10조의 표시 위치가 초기 화면이라서다. 조각이 쓰는
        # 컨텍스트를 문서 페이지와 같은 함수에서 넘긴다(표시 범위는 티켓 16 소유).
        business_info=_business_info(language),
        contact_email=current_app.config["LEGAL_CONTACT_EMAIL"],
    )
    # 프록시·CDN 이 ko 로 그려진 페이지를 en 방문자에게 주지 않게 한다.
    return html, 200, {"Content-Language": language, "Vary": "Accept-Language"}


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
    language = _requested_ui_language()
    html = render_template(
        f"legal/{name}.{language}.html",
        ui_language=language,
        effective_date=LEGAL_EFFECTIVE_DATE,
        contact_email=current_app.config["LEGAL_CONTACT_EMAIL"],
        business_info=_business_info(language),
        # 비면 템플릿이 직책("운영자")으로 적는다 — 성명 표기는 사람이 값을 채워 고른다
        # (사용자 결정 2026-10-14, 개보법 제31조는 성명 **또는** 직책을 요구한다).
        privacy_officer=current_app.config["LEGAL_PRIVACY_OFFICER"].strip(),
        apple_standard_eula_url=APPLE_STANDARD_EULA_URL,
    )
    # 심사자·크롤러가 Accept-Language 없이 받아도 어느 언어인지 알 수 있게 명시한다.
    return html, 200, {"Content-Language": language}


def _business_info(language: str) -> list[dict[str, str]]:
    """설정에 값이 있는 사업자 정보 항목만 `{key, label, value}` 로 돌려준다.

    없는 값을 "미등록" 같은 문구로 채우지 않는다: 사업자 등록 전에 빈 목록을 돌려주면
    템플릿이 서비스명·연락처만 보여주고, 등록 후 환경변수를 채우면 그 항목만 늘어난다.

    설정 키를 라벨과 함께 넘기는 이유: 조각(`legal/_business_info.html`)이 "주소 행이
    렌더됐는지" 를 **언어와 무관하게** 물어야 한다 — 주소를 축약해 넣기로 했으므로
    (사용자 결정 2026-10-14) 그 행이 있을 때만 "상세 주소는 요청 시 제공" 을 붙인다.
    """
    info = []
    for key, label_ko, label_en in LEGAL_BUSINESS_FIELDS:
        value = (current_app.config.get(key) or "").strip()
        if value:
            label = label_ko if language == "ko" else label_en
            info.append({"key": key, "label": label, "value": value})
    return info


@bp.get("/account/delete")
def account_delete():
    """계정 삭제 확인 페이지(ko/en). Play Data safety 의 "계정 삭제 URL" 이다.

    세션에 게스트가 있으면 확인 폼(1회용 CSRF 토큰 포함), 없으면 "기록이 있는
    기기에서 지워라 + 운영자 메일" 안내다. 세션은 프론트가 페이지 로드마다 호출하는
    `POST /api/v1/session/sync` 가 심는다(app/api/oauth.py) — 로그인 안 해도 게임을
    한 번 열었던 브라우저면 삭제할 수 있다.

    **GET 은 아무 상태도 바꾸지 않는다**(스펙 §A.7). 심사자·크롤러·링크 프리뷰가
    이 URL 을 먼저 열어보는데, 그걸로 계정이 사라지면 안 된다. 삭제는 POST 뿐이다.
    """
    language = _requested_ui_language()
    guest = _session_guest()
    html = render_template(
        f"account/delete.{language}.html",
        ui_language=language,
        contact_email=current_app.config["LEGAL_CONTACT_EMAIL"],
        # 폼을 그릴 때만 토큰을 발급한다 — 템플릿은 이 값의 유무로 두 갈래를 고른다.
        csrf_token=_issue_form_for(guest) if guest is not None else None,
    )
    return html, 200, {"Content-Language": language}


@bp.post("/account/delete")
def account_delete_submit():
    """확인 폼 제출. 세션 게스트를 지우고 세션을 비운 뒤 홈으로 보낸다.

    세션 확인이 CSRF 검증보다 **먼저** 와야 한다: 로그인 안 된 브라우저의 제출은
    "폼이 위조됐다"(403)가 아니라 "지울 게 누군지 모른다"(401)이기 때문이다
    (스펙 §A.7). 그래서 데코레이터를 겹쳐 쓰지 않고, 게스트를 먼저 찾은 뒤
    CSRF 로 보호된 함수를 부른다.

    세션 게스트가 **그 폼을 그릴 때 본 게스트** 와 같은지도 본다. 확인 화면을 띄워
    둔 채 다른 탭에서 백업 코드를 복원하거나 계정을 전환하면 세션이 다른 게스트를
    가리키는데, 그때 옛 버튼이 "지금 세션의 게스트" 를 지우면 플레이어가 지우려던
    계정은 남고 멀쩡한 계정이 사라진다.
    """
    guest = _session_guest()
    if guest is None:
        raise UnauthorizedError("삭제할 기록이 없습니다. 기록이 있는 기기에서 다시 시도해주세요.")
    remember_actor(f"guest.{guest.id}")
    if session.get(DELETE_TARGET_SESSION_KEY) != guest.id:
        # 폼을 다시 받아야 한다. 다른 계정을 지워주는 쪽보다 한 번 더 확인받는 쪽이 싸다.
        raise ForbiddenError()
    return _delete_session_guest(guest)


def _issue_form_for(guest: Guest) -> str:
    """이 게스트를 지우는 폼 하나를 발급한다: 1회용 CSRF 토큰 + 삭제 대상 기록.

    둘을 같은 자리에서 심는다 — 토큰만 심고 대상을 안 적으면 "우리가 그려준 폼" 이
    그릴 때와 다른 계정을 지울 수 있다(제출 시점의 세션 게스트를 따라가므로).
    """
    session[DELETE_TARGET_SESSION_KEY] = guest.id
    return issue_csrf_token()


@csrf_protected
def _delete_session_guest(guest: Guest):
    delete_guest_account(guest)
    # 지워진 게스트를 가리키는 세션이 남으면 다음 요청이 유령 게스트를 들고 돈다.
    session.clear()
    # `?deleted=1` 은 프론트(web/static/app.js)에 "저장된 토큰을 버리고 새 게스트를
    # 받아라" 를 알리는 신호다 — 안 버리면 모든 요청이 401 이 된다.
    return redirect("/?deleted=1")


def _session_guest() -> Guest | None:
    """세션 쿠키가 가리키는 게스트. 없거나 이미 지워졌으면 None.

    쿠키에 적힌 id 가 아직 살아 있는지 매번 확인한다 — 서명 쿠키 세션은 상태가
    전부 클라이언트에 있어서, 한 탭에서 삭제해도 다른 탭이 들고 있던 쿠키는
    그대로 남는다.
    """
    guest_id = session.get("current_guest_id")
    return db.session.get(Guest, guest_id) if guest_id else None


def _requested_ui_language() -> str:
    return resolve_ui_language(request.args.get("lang"), request.headers.get("Accept-Language"))


def register_web(app):
    app.register_blueprint(bp)
