from datetime import datetime

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app import create_app
from app.config import KST
from app.extensions import _REDIS_EXTENSION_KEY, db, get_oauth, get_redis
from app.models import DailyPuzzle, PuzzleLanguage, Word, WordCategory
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
