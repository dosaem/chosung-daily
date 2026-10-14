from datetime import datetime

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app import create_app
from app.config import KST
from app.extensions import _REDIS_EXTENSION_KEY, db, get_oauth, get_redis
from app.models import (
    Account,
    DailyPuzzle,
    Guest,
    OAuthProvider,
    PuzzleLanguage,
    Word,
    WordCategory,
)
from app.services.guest_service import issue_guest


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # 캐시/랭킹/통계/rate limit 전부 Redis 상태를 쓰기 때문에, 테스트 DB(인덱스 1)를
        # 비워두지 않으면 이전 테스트가 심어둔 puzzle:{date} 캐시나 ratelimit 카운터가
        # 다음 테스트로 샌다 (실제로 이걸 안 했다가 테스트가 깨졌었음).
        get_redis().flushdb()
        yield app
        db.session.remove()
        db.drop_all()
        # 이 픽스처는 테스트마다 새 앱 = 새 엔진 = 새 커넥션 풀을 만든다. 풀을 안
        # 닫으면 쓰고 버린 연결이 스위트가 끝날 때까지 MySQL 에 Sleep 으로 쌓여서
        # (실측 43개 테스트에 28개), 공용 MySQL 의 max_connections(151) 를 두고
        # 병렬로 도는 다른 워커의 테스트를 굶긴다. 앱을 버릴 때 풀도 같이 버린다.
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    return db.session


# make_today_puzzle의 언어별 기본 단어. 언어를 바꿔도 테스트가 매번 정답·힌트를
# 적지 않아도 되게 한다.
_DEFAULT_WORDS = {
    PuzzleLanguage.KO: ("사과", "빨간 과일"),
    PuzzleLanguage.EN: ("apple", "red fruit"),
}


@pytest.fixture
def make_today_puzzle(app):
    """오늘(KST) 날짜로 주어진 언어의 Word + DailyPuzzle을 만든다.

    같은 날짜에 언어마다 하나씩 만들 수 있다(`DailyPuzzle`의 유니크 키가
    `(puzzle_date, language)`). 언어를 안 주면 ko다.
    """

    def _make(
        language: PuzzleLanguage = PuzzleLanguage.KO,
        answer: str | None = None,
        hint: str | None = None,
        category: WordCategory = WordCategory.GENERAL,
    ) -> DailyPuzzle:
        default_answer, default_hint = _DEFAULT_WORDS[language]
        word = Word(
            answer=answer or default_answer,
            language=language,
            category=category,
            hint=hint or default_hint,
        )
        db.session.add(word)
        db.session.flush()

        puzzle = DailyPuzzle(
            puzzle_date=datetime.now(KST).date(), language=language, word_id=word.id
        )
        db.session.add(puzzle)
        db.session.commit()
        return puzzle

    return _make


@pytest.fixture
def today_puzzle(make_today_puzzle):
    """오늘(KST)의 ko 퍼즐 하나. 언어가 상관없는 테스트가 그대로 쓴다."""
    return make_today_puzzle()


@pytest.fixture
def guest_headers(app):
    guest = issue_guest()
    return {"Authorization": f"Bearer {guest.token}"}


class _BrokenRedis:
    """모든 메서드 호출이 Redis 장애를 흉내 낸다."""

    def __getattr__(self, _name):
        def _raise(*args, **kwargs):
            raise RedisConnectionError("simulated redis outage")

        return _raise


@pytest.fixture
def broken_redis(app, monkeypatch):
    monkeypatch.setitem(app.extensions, _REDIS_EXTENSION_KEY, _BrokenRedis())


# provider discovery 문서(`server_metadata_url`)에서 로그인 시작이 실제로 쓰는 값만
# 추린 것. 등록된 실제 엔드포인트와 같은 값이지만, 테스트가 구글·애플 서버에 매번
# HTTPS 요청을 보내지 않도록 여기서 직접 준다.
PROVIDER_METADATA = {
    "google": {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_endpoint": "https://oauth2.googleapis.com/token",
    },
    "apple": {
        "authorization_endpoint": "https://appleid.apple.com/auth/authorize",
        "token_endpoint": "https://appleid.apple.com/auth/token",
    },
}


@pytest.fixture
def offline_provider_metadata(app, monkeypatch):
    """provider discovery 조회를 네트워크 없이 대신한다.

    Authlib 은 `authorization_endpoint` 를 discovery 문서에서 읽어오기 때문에, 이
    대역이 없으면 리다이렉트 테스트가 돌 때마다 구글·애플에 실제 요청이 나간다
    (소켓을 막고 돌리면 그 자리에서 실패한다 — 리뷰에서 지적된 지점).

    그래서 이 테스트가 보증하는 범위도 그만큼이다: "라우트가 provider 인가 URL 로
    302 를 만든다" 까지고, discovery 문서의 내용과 실제 로그인 왕복은 콘솔 등록 후
    수동 확인 대상이다(파일 상단 설명과 같은 이유).
    """
    with app.app_context():
        oauth = get_oauth()
        for name, metadata in PROVIDER_METADATA.items():
            provider_client = oauth.create_client(name)
            monkeypatch.setattr(
                provider_client, "load_server_metadata", lambda metadata=metadata: metadata
            )


# 스펙 §C "백엔드 접점" 이 이름을 정한 운영자 픽스처. 운영자 페이지(/admin)의 판정
# 경로가 세션 → Guest → Account.email 이라, 테스트도 그 경로를 그대로 태운다.
ADMIN_EMAIL = "admin-fixture@example.com"


@pytest.fixture
def web_login(app, client):
    """브라우저 세션으로 로그인한 상태를 만든다. 이메일을 주면 계정까지 연결한다.

    세션 딕셔너리를 직접 건드리지 않고 `POST /api/v1/session/sync` 를 통과시킨다 —
    운영자 판정이 실제 로그인 경로에서 심어지는 세션 키를 읽는지까지 같이 검증된다.
    """

    def _login(email: str | None = None) -> Guest:
        guest = issue_guest()
        if email is not None:
            db.session.add(
                Account(
                    guest_id=guest.id,
                    provider=OAuthProvider.GOOGLE,
                    provider_user_id=f"google-{guest.id}",
                    email=email,
                )
            )
        db.session.commit()
        client.post(
            "/api/v1/session/sync", headers={"Authorization": f"Bearer {guest.token}"}
        )
        return guest

    return _login


@pytest.fixture
def admin_session(app, client, web_login):
    """운영자 이메일로 로그인한 테스트 클라이언트. `ADMIN_EMAILS` 도 같이 세팅한다.

    `ADMIN_EMAILS` 는 기본값이 없어서(app/config.py) 테스트가 명시적으로 넣어야
    한다 — 설정을 깜빡한 환경에서 아무나 운영자가 되는 일이 없다는 뜻이다.
    """
    app.config["ADMIN_EMAILS"] = (ADMIN_EMAIL,)
    web_login(ADMIN_EMAIL)
    return client
