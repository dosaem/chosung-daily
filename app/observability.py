import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

# Sentry 가 이벤트에 자동으로 끼워 넣는 데이터 중 무엇을 받을지 고른 것.
#
# 왜 `send_default_pii=False` 로는 부족한가: 그 옵션은 "쿠키·유저 식별자" 같은
# 일부만 끈다. 요청 **본문**은 PII 설정과 무관하게 기본 수집이고(SDK 2.72 의
# `_wsgi_common.RequestExtractor.extract_into_event` 가 `attach_request_body`
# 기본값을 True 로 둔다), 쿼리스트링도 그대로 붙는다. 그래서 OAuth 콜백이 한 번
# 500 이 나면 애플이 보낸 인증 코드(`code`)와 최초 로그인 `user` JSON(이메일·이름)
# 이 이벤트에 실려 외부로 복제된다 — 최종 리뷰에서 실제로 재현된 결함이다.
# 기본 EventScrubber 도 `code`/`user` 는 민감어 목록에 없고 비재귀라 못 막는다.
#
# `data_collection` 은 SDK 2.72 에서 `send_default_pii` 를 대체한 구조화 옵션이고
# (옛 옵션은 DeprecationWarning 이 뜬다), 수집 범주를 하나씩 끌 수 있다. 단, 이
# 옵션을 넘기는 순간 나머지 범주는 "수집" 쪽 기본값을 쓰므로 끌 것은 전부 적는다.
SENTRY_DATA_COLLECTION = {
    # 요청 본문: OAuth 콜백의 `code`·`user`, 영수증 검증의 `receipt` 가 들어오는
    # 자리. 어느 필드를 거를지 고르는 대신 본문 자체를 받지 않는다 — 새 엔드포인트가
    # 생길 때마다 민감 필드 목록을 따라 늘려야 하는 쪽이 더 잘 샌다.
    "http_bodies": [],
    # 쿼리스트링: 구글 콜백은 같은 인증 코드를 `?code=` 로 보낸다.
    "url_query_params": {"mode": "off"},
    # 쿠키: 서명된 세션 쿠키(어느 게스트인지)가 들어 있다.
    "cookies": {"mode": "off"},
    # IP·유저 식별자.
    "user_info": False,
    # SQL 바인드 파라미터(닉네임·정답 등).
    "database_query_data": False,
    # Celery task 인자.
    "queues": False,
    # 스택 프레임의 지역 변수. 디버깅에 제일 쓸모 있는 데이터라 아까웠지만 껐다 —
    # 이름 기준 필터로는 못 막는다. 예외가 터진 뷰의 프레임만 올라오는 게 아니라
    # `flask/app.py:wsgi_app` 프레임도 같이 올라오고, 그 프레임의 `environ` 지역
    # 변수에 `QUERY_STRING`·`RAW_URI`(= `?code=...`)와 `HTTP_COOKIE` 가 통째로
    # 들어 있다. werkzeug `Request` 객체의 repr 도 전체 URL 을 그대로 보여준다.
    # 필터는 변수 "이름" 만 보니 이런 중첩·repr 안쪽을 들여다보지 못한다
    # (`tests/test_sentry.py` 의 쿼리스트링 테스트가 이걸 잡는다).
    "stack_frame_variables": False,
}


def init_sentry(app) -> bool:
    """`SENTRY_DSN` 이 있을 때만 Sentry 를 켠다. 켰으면 True.

    초기화 지점이 create_app() 하나인 이유: Celery worker/beat 도 celery_app.py
    에서 create_app() 으로 Flask 앱을 만들어 쓰기 때문에, 여기서 Flask·Celery
    통합을 같이 등록하면 웹·워커가 같은 설정을 탄다. 웹 프로세스에 걸린 Celery
    통합은 할 일이 없을 뿐 해롭지 않다.

    개인정보처리방침(스펙 §A.15)에 Sentry 를 수탁자로 적어둔 만큼, 어떤 데이터가
    실려 나가는지는 `SENTRY_DATA_COLLECTION` 에서 범주별로 못 박는다. 그 설정이
    실제 이벤트에 반영되는지는 `tests/test_sentry.py` 가 메모리 Transport 로 완성된
    이벤트 payload 를 받아 확인한다(초기화 인자만 보면 이번 결함을 또 놓친다).
    """
    dsn = app.config["SENTRY_DSN"]
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration(), CeleryIntegration()],
        environment=app.config["ENV_NAME"],
        release=app.config["SENTRY_RELEASE"] or None,
        data_collection=SENTRY_DATA_COLLECTION,
        # 성능 추적 10% — 용량 계획의 판정 기준(자정 10분 p95 > 300ms 3일 연속)을 보려고.
        # 트랜잭션엔 경로·상태·지연만 담기고 본문·헤더는 위 data_collection 규칙이 막는다.
        traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE") or 0.1),
    )
    return True
