"""애플 연결 철회(Sign in with Apple revoke)와 실패 재시도.

US 22a: 애플 계정으로 로그인했던 게스트를 지우면 애플 쪽 연결도 실제로 끊겨야
한다 — 안 그러면 애플 설정의 "Apple ID 를 사용하는 앱" 에 유령 앱이 남는다.
애플은 **그 refresh token 을 발급한 client 의 자격증명** 으로만 철회를 받아주므로
(iOS 연결 = 번들 ID, 웹 연결 = Services ID) 그 짝이 맞는지가 이 파일의 핵심이다.

애플에 실제 요청은 보내지 않는다 — `requests.post` 대역이 받은 인자를 검사한다.
"""

import json
from datetime import timedelta

import jwt
import pytest
import requests
from sqlalchemy.exc import OperationalError

from app.clients import apple
from app.extensions import db
from app.models import Account, AppleRevocationRetry, Guest, OAuthProvider
from app.services import apple_revocation_service
from app.services.account_deletion_service import delete_guest_account
from app.services.account_service import ProviderTokens, link_or_switch_account
from app.services.apple_revocation_service import retry_pending_revocations
from app.services.guest_service import issue_guest
from app.utils.crypto import encrypt_secret
from app.utils.time import utcnow

REFRESH_TOKEN = "apple-refresh-token-1"


class _RecordingPost:
    """requests.post 대역. 호출 인자를 기록하고 정해둔 응답/예외를 돌려준다.

    tests/test_apple_client.py 의 같은 이름 클래스와 같은 역할이다 — 애플 토큰
    교환과 철회는 다른 엔드포인트라 테스트도 따로 두고, 대역은 각자 들고 있다.
    """

    def __init__(self, status_code=200, payload=None, raises=None):
        self.calls = []
        self._status_code = status_code
        self._payload = payload or {}
        self._raises = raises

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self._raises is not None:
            raise self._raises
        response = requests.Response()
        response.status_code = self._status_code
        response.url = url
        response._content = json.dumps(self._payload).encode()
        response.headers["Content-Type"] = "application/json"
        return response

    @property
    def data(self) -> dict:
        assert len(self.calls) == 1, f"철회 호출이 {len(self.calls)}번 일어났다"
        return self.calls[0][1]["data"]


@pytest.fixture
def apple_post(monkeypatch):
    post = _RecordingPost()
    monkeypatch.setattr(apple.requests, "post", post)
    return post


@pytest.fixture
def failing_apple_post(monkeypatch):
    post = _RecordingPost(raises=requests.ConnectionError("apple unreachable"))
    monkeypatch.setattr(apple.requests, "post", post)
    return post


def _apple_guest(app, client_id: str, provider_user_id: str = "apple-uid-1") -> Guest:
    """애플로 로그인해 둔 게스트. 연결·토큰 저장은 실제 서비스 함수를 쓴다."""
    guest = issue_guest()
    return link_or_switch_account(
        guest,
        OAuthProvider.APPLE,
        provider_user_id,
        None,
        provider_tokens=ProviderTokens(REFRESH_TOKEN, client_id),
    )


# --- 외부 호출 래퍼 ---------------------------------------------------------


def test_revoke_posts_the_refresh_token_to_apples_revoke_endpoint(app, apple_post):
    apple.revoke_refresh_token(REFRESH_TOKEN, client_id="com.example.app", client_secret="jwt")

    url, kwargs = apple_post.calls[0]
    assert url == apple.APPLE_REVOKE_URL
    assert kwargs["data"] == {
        "token": REFRESH_TOKEN,
        "token_type_hint": "refresh_token",
        "client_id": "com.example.app",
        "client_secret": "jwt",
    }
    assert kwargs["timeout"] == apple.TIMEOUT_SECONDS


def test_revoke_raises_when_apple_rejects_the_call(app, monkeypatch):
    monkeypatch.setattr(apple.requests, "post", _RecordingPost(status_code=400))

    with pytest.raises(requests.HTTPError):
        apple.revoke_refresh_token(REFRESH_TOKEN, client_id="x", client_secret="jwt")


# --- 발급 client 에 맞는 자격증명 -------------------------------------------


def test_ios_linked_account_is_revoked_with_the_app_bundle_id(app, apple_post):
    bundle_id = app.config["APPLE_APP_BUNDLE_ID"]
    guest = _apple_guest(app, bundle_id)

    delete_guest_account(guest)

    assert apple_post.data["token"] == REFRESH_TOKEN
    assert apple_post.data["client_id"] == bundle_id
    # client_secret 은 그 client_id 로 서명한 JWT 여야 한다(sub = client_id).
    claims = jwt.decode(apple_post.data["client_secret"], options={"verify_signature": False})
    assert claims["sub"] == bundle_id


def test_web_linked_account_is_revoked_with_the_services_id(app, apple_post):
    services_id = app.config["APPLE_CLIENT_ID"]
    guest = _apple_guest(app, services_id)

    delete_guest_account(guest)

    assert apple_post.data["client_id"] == services_id
    claims = jwt.decode(apple_post.data["client_secret"], options={"verify_signature": False})
    assert claims["sub"] == services_id


def test_google_account_deletion_never_calls_apple(app, apple_post):
    guest = issue_guest()
    link_or_switch_account(guest, OAuthProvider.GOOGLE, "google-uid-9", "g@example.com")

    delete_guest_account(guest)

    assert apple_post.calls == []


def test_guest_without_any_account_never_calls_apple(app, apple_post):
    delete_guest_account(issue_guest())

    assert apple_post.calls == []


# --- 실패 시: 삭제는 진행, 재시도 행 ----------------------------------------


def test_failed_revoke_still_deletes_the_account_and_records_a_retry(app, failing_apple_post):
    bundle_id = app.config["APPLE_APP_BUNDLE_ID"]
    guest = _apple_guest(app, bundle_id)
    guest_id = guest.id
    stored = Account.query.filter_by(guest_id=guest_id).one().provider_refresh_token

    delete_guest_account(guest)

    assert db.session.get(Guest, guest_id) is None
    retry = AppleRevocationRetry.query.one()
    assert retry.client_id == bundle_id
    # 재시도 행도 평문을 들고 있지 않다 — 계정 테이블과 같은 암호문이다.
    assert retry.refresh_token_enc == stored
    assert retry.refresh_token_enc != REFRESH_TOKEN


def test_successful_revoke_leaves_no_retry_row(app, apple_post):
    delete_guest_account(_apple_guest(app, app.config["APPLE_APP_BUNDLE_ID"]))

    assert AppleRevocationRetry.query.count() == 0


def test_a_token_that_cannot_be_decrypted_does_not_break_deletion(app, apple_post):
    """SECRET_KEY 가 바뀐 뒤의 옛 암호문. 삭제는 끝까지 가고 재시도 행만 남는다."""
    guest = _apple_guest(app, app.config["APPLE_APP_BUNDLE_ID"])
    account = Account.query.filter_by(guest_id=guest.id).one()
    account.provider_refresh_token = "not-a-fernet-token"
    db.session.commit()
    guest_id = guest.id

    delete_guest_account(guest)

    assert db.session.get(Guest, guest_id) is None
    assert apple_post.calls == []  # 복호화를 못 했으니 애플에 보낼 토큰이 없다
    assert AppleRevocationRetry.query.count() == 1


def test_apple_account_without_a_stored_client_cannot_be_revoked(app, apple_post):
    """`provider_client_id` 가 없으면 어느 자격증명으로 철회할지 알 수 없다 —
    아무 client 로 찍어 보내지 않고 재시도 행도 만들지 않는다(재시도도 같은 이유로
    실패할 수밖에 없다). 티켓 10·11 이후 연결은 항상 둘을 같이 저장한다."""
    guest = _apple_guest(app, app.config["APPLE_APP_BUNDLE_ID"])
    account = Account.query.filter_by(guest_id=guest.id).one()
    account.provider_client_id = None
    db.session.commit()
    guest_id = guest.id

    delete_guest_account(guest)

    assert db.session.get(Guest, guest_id) is None
    assert apple_post.calls == []
    assert AppleRevocationRetry.query.count() == 0


# --- Beat 재시도 ------------------------------------------------------------


def _pending_retry(app, *, age: timedelta = timedelta(0)) -> AppleRevocationRetry:
    retry = AppleRevocationRetry(
        refresh_token_enc=encrypt_secret(REFRESH_TOKEN),
        client_id=app.config["APPLE_APP_BUNDLE_ID"],
        created_at=utcnow() - age,
    )
    db.session.add(retry)
    db.session.commit()
    return retry


def test_retry_removes_the_row_when_apple_accepts(app, apple_post):
    _pending_retry(app)

    outcome = retry_pending_revocations()

    assert apple_post.data["token"] == REFRESH_TOKEN
    assert outcome.revoked == 1
    assert outcome.discarded == 0
    assert AppleRevocationRetry.query.count() == 0


def test_retry_keeps_the_row_while_apple_keeps_failing(app, failing_apple_post):
    _pending_retry(app, age=timedelta(days=3))

    outcome = retry_pending_revocations()

    assert outcome.revoked == 0
    assert outcome.pending == 1
    assert AppleRevocationRetry.query.count() == 1


def test_a_row_older_than_seven_days_is_discarded_and_the_operator_is_told(
    app, failing_apple_post, monkeypatch
):
    alerts = []
    monkeypatch.setattr(
        apple_revocation_service,
        "notify_operator",
        lambda kind, message: alerts.append((kind, message)) or True,
    )
    _pending_retry(app, age=apple_revocation_service.RETRY_MAX_AGE + timedelta(minutes=1))

    outcome = retry_pending_revocations()

    assert outcome.discarded == 1
    assert AppleRevocationRetry.query.count() == 0
    assert len(alerts) == 1
    kind, message = alerts[0]
    assert "revoke" in kind.lower()
    # 알림에 토큰(평문이든 암호문이든)을 싣지 않는다 — Slack 으로 자격증명을 흘리지 않는다.
    assert REFRESH_TOKEN not in message
    assert app.config["APPLE_APP_BUNDLE_ID"] in message


def test_a_row_at_seven_days_is_still_retried_not_discarded(app, failing_apple_post, monkeypatch):
    """경계: 7일을 "넘어야" 폐기다(스펙 §A.7 "7일 후 폐기")."""
    alerts = []
    monkeypatch.setattr(
        apple_revocation_service, "notify_operator", lambda kind, message: alerts.append(kind)
    )
    _pending_retry(app, age=apple_revocation_service.RETRY_MAX_AGE - timedelta(minutes=1))

    outcome = retry_pending_revocations()

    assert outcome.discarded == 0
    assert outcome.pending == 1
    assert alerts == []


def test_one_bad_row_does_not_stop_the_others(app, apple_post):
    """한 행의 암호문이 깨져도 나머지 행은 그날 재시도된다."""
    broken = _pending_retry(app)
    broken.refresh_token_enc = "not-a-fernet-token"
    db.session.commit()
    _pending_retry(app)

    outcome = retry_pending_revocations()

    assert outcome.revoked == 1
    assert outcome.pending == 1
    assert AppleRevocationRetry.query.count() == 1


def test_nothing_pending_means_no_apple_call(app, apple_post):
    outcome = retry_pending_revocations()

    assert (outcome.revoked, outcome.discarded, outcome.pending) == (0, 0, 0)
    assert apple_post.calls == []


# --- 철회 의무의 영속성(D-14-3) ---------------------------------------------
#
# 삭제 커밋과 "철회해야 한다" 의 기록이 **같은 커밋** 이 아니면, 그 사이에 프로세스나
# DB 가 죽은 요청은 계정만 지우고 철회 자격증명(refresh token, 발급 client)을 영구히
# 버린다 — 게스트 행이 없어서 다시 찾을 수도, 플레이어가 다시 요청할 수도 없다.


def test_the_revocation_duty_is_committed_together_with_the_deletion(app, monkeypatch, apple_post):
    """철회를 시도하다 프로세스가 터져도 재시도 행은 이미 DB 에 있다."""
    guest = _apple_guest(app, app.config["APPLE_APP_BUNDLE_ID"])
    guest_id = guest.id

    def exploding_revoke(*_args, **_kwargs):
        raise RuntimeError("프로세스가 여기서 죽었다")

    monkeypatch.setattr(apple_revocation_service, "_revoke", exploding_revoke)

    with pytest.raises(RuntimeError):
        delete_guest_account(guest)
    db.session.rollback()  # 요청 종료의 teardown 과 같은 자리

    assert db.session.get(Guest, guest_id) is None
    assert apple_post.calls == []
    assert AppleRevocationRetry.query.count() == 1


def test_a_failed_revoke_survives_a_db_outage_after_the_deletion_commit(
    app, monkeypatch, failing_apple_post
):
    """삭제가 커밋된 뒤의 모든 커밋이 DB 장애로 막혀도 철회 의무는 남는다."""
    guest = _apple_guest(app, app.config["APPLE_APP_BUNDLE_ID"])
    guest_id = guest.id

    real_commit = db.session.commit
    commits = []

    def flaky_commit():
        commits.append(1)
        if len(commits) == 1:
            return real_commit()
        raise OperationalError("COMMIT", {}, Exception("db down"))

    monkeypatch.setattr(db.session, "commit", flaky_commit)

    delete_guest_account(guest)  # 철회 실패는 삭제를 막지 않는다(스펙 §A.7)

    monkeypatch.undo()
    db.session.rollback()
    assert db.session.get(Guest, guest_id) is None
    assert AppleRevocationRetry.query.count() == 1
