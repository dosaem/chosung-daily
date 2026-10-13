from pydantic import BaseModel, Field

from app.models.enums import OAuthProvider


class TokenExchangeRequest(BaseModel):
    """앱이 네이티브 로그인으로 받은 id_token 교환 요청(§A.6).

    `authorization_code` 는 애플만 보낸다 — 애플인데 비어 있으면 서비스가 거절한다
    (app/services/app_login_service.py).
    """

    provider: OAuthProvider
    id_token: str = Field(min_length=1)
    authorization_code: str | None = None
