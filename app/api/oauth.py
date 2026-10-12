import secrets

from flask import Blueprint, g, jsonify, redirect, session, url_for

from app.api.auth import with_guest
from app.errors import NotFoundError, OAuthProviderUnavailableError, UnauthorizedError
from app.extensions import db, get_oauth
from app.models import Guest, OAuthProvider
from app.services.account_service import link_or_switch_account

bp = Blueprint("oauth", __name__)

_SUPPORTED = {p.value for p in OAuthProvider}


def _get_client(provider: str):
    if provider not in _SUPPORTED:
        raise NotFoundError(f"지원하지 않는 로그인 방식입니다: {provider}")
    oauth = get_oauth()
    client = oauth.create_client(provider) if oauth else None
    if client is None:
        raise OAuthProviderUnavailableError(f"{provider} 로그인이 아직 설정되지 않았습니다.")
    return client


@bp.post("/session/sync")
@with_guest
def sync_session():
    """프론트가 페이지 로드마다(그리고 토큰 복원 직후) 호출해서, "이 브라우저는
    지금 이 게스트"라는 걸 서명된 세션 쿠키에 남겨둔다.

    왜 필요한가: 처음엔 /auth/<provider>/login이 쿼리파라미터 token=으로 어느
    게스트에 연결할지 받았는데, 그러면 공격자가 자기 게스트 토큰을 넣은 링크를
    피해자에게 보내서 피해자가 그 링크로 구글/애플 로그인을 완료하게 만들면
    피해자의 진짜 계정이 공격자 게스트에 영구 연결돼버리는 로그인 CSRF가
    가능했다(보안 리뷰로 발견). 그 쿼리파라미터를 아무나 원하는 값으로 채워서
    보낼 수 있다는 게 근본 원인이라, "현재 브라우저가 어느 게스트인지"는 이제
    Authorization 헤더로 인증된 이 엔드포인트를 통해서만 세션 쿠키(서명돼 있어
    위조 불가, SameSite=Lax라 다른 사이트에서 강제로 못 심음)에 심는다. 공격자가
    보낸 링크를 피해자가 눌러도, 그 요청엔 피해자 자신의 세션 쿠키가 실리지
    공격자 것은 못 실린다.
    """
    session["current_guest_id"] = g.guest.id
    return jsonify({"ok": True})


@bp.get("/auth/<provider>/login")
def login(provider):
    client = _get_client(provider)

    guest_id = session.get("current_guest_id")
    guest = db.session.get(Guest, guest_id) if guest_id else None
    if guest is None:
        raise UnauthorizedError("먼저 /api/v1/session/sync로 세션을 동기화해야 합니다.")

    session["oauth_pending_guest_id"] = guest.id
    redirect_uri = url_for("oauth.callback", provider=provider, _external=True)

    # 구글/애플 둘 다 OIDC라 id_token 재생 방지용 nonce가 필요하다(Authlib 표준 패턴).
    nonce = secrets.token_urlsafe(16)
    session["oauth_nonce"] = nonce
    return client.authorize_redirect(redirect_uri, nonce=nonce)


@bp.route("/auth/<provider>/callback", methods=["GET", "POST"])
def callback(provider):
    # 애플은 콜백을 GET 리다이렉트가 아니라 POST(response_mode=form_post)로
    # 보낸다 — 그래서 이 라우트만 POST도 받는다(구글은 GET으로 온다).
    client = _get_client(provider)

    guest_id = session.pop("oauth_pending_guest_id", None)
    if guest_id is None:
        raise UnauthorizedError("로그인 세션이 만료됐습니다. 다시 시도해주세요.")

    token = client.authorize_access_token()
    nonce = session.pop("oauth_nonce", None)
    user_info = client.parse_id_token(token, nonce=nonce)
    provider_user_id, email = str(user_info["sub"]), user_info.get("email")

    current_guest = db.session.get(Guest, guest_id)
    linked_guest = link_or_switch_account(
        current_guest, OAuthProvider(provider), provider_user_id, email
    )

    # 프론트(web/static/app.js)가 ?login_token=을 읽어서 localStorage 토큰을
    # 바꾸고 새로고침한다. 이 경로는 .env에 GOOGLE/APPLE 키를 실제로 넣고 콘솔에
    # 앱을 등록하기 전까진 실제로 돌려본 적이 없다 — 등록 후 가장 먼저 테스트해야
    # 하는 지점. 특히 애플은 POST 콜백이라 리다이렉트 응답이 브라우저에서 실제로
    # 기대대로 동작하는지(폼 제출 이후 redirect를 그대로 따라가는지)도 같이 확인.
    return redirect(f"/?login_token={linked_guest.token}")
