# 티켓 10 최종 리뷰 — 라운드 1

검토 기준: 로컬 `main` 491418fb → 구현 HEAD b3444c54 (`git diff main...HEAD`, `git log main..HEAD`). 구현 커밋은 796c23f, 60af0e7, d6f9f06, b3444c5이다. 티켓 10, 스펙 §A.6·§A.17·§A'·미정 17, ADR 0002, CONTEXT.md 및 구현 증거를 대조했다. UI 변경은 없어 디자인 검토는 해당하지 않는다.

## 체크박스별 확인

| 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|
| Account 두 컬럼, SECRET_KEY 파생 Fernet, 마이그레이션 head 1개 | 충족 | `app/models/account.py:37`, `app/utils/crypto.py`, f394da7f4d88 마이그레이션의 nullable Text/String 추가 및 역방향 제거 확인. 암복호화·다른 키 거부 테스트 통과, `flask db heads` 1줄 확인. 이번 리뷰에서는 upgrade/downgrade를 실행하지 않았다. |
| Google/Apple JWKS·토큰 교환 래퍼와 순수 검증 함수, 실제 서명 테스트 | 충족 | `clients/google_jwks.py`, `clients/apple.py`, `services/id_token_service.py` 분리 확인. RSA 서명·다른 서명·iss·aud·exp·없는 sub·HS256·none 거부 테스트가 실제 검증 함수를 실행하며 통과한다. 캐시의 키 교체 결함은 D-10-1. |
| Bearer token-exchange, aud 매트릭스, 연결/전환, 오류 코드 | 미충족 | 일반 연결/전환·401·409·Bearer 가드 테스트는 통과한다. 그러나 정상 키 교체 후 유효한 id_token이 최대 1시간 거부되어 정상 로그인 요구를 충족하지 못한다(D-10-1). |
| Apple code 교환, 번들 client/JWT, sub 일치, 암호화 저장·덮어쓰기 | 충족 | `app_login_service.py:109` 이후 및 `account_service.py:39` 이후 확인. 실제 서명한 교환 id_token을 다시 검증하고 sub 불일치 시 저장 없이 거부한다. 번들 ID 전달, 암호문 복호화, 전환 시 새 refresh token 저장 테스트 통과. |
| 웹 Apple 콜백의 refresh token·Services ID 저장, 기존 테스트 | 충족 | `oauth.py:87` 이후 및 신규 웹 콜백 저장 테스트 통과. 기존 리다이렉트 두 테스트는 외부 discovery 의존성이 있어 오프라인 대역을 넣은 추가 실행에서 확인했다(아래 실행 증거). |
| 신규 설정값·번들용 Apple 키 설정 설명, 미정 17 반영 | 충족 | Config/TestingConfig와 `.env.example`에 세 client ID 설정, 기존 Apple 서명 키 공유 설명이 있다. 스펙 미정 17의 두 client 자동 갱신 후속 범위도 기록됨. 단, 공유 파일 편집 방식은 D-10-2. |
| README ADR 0002 요약·aud 표·토큰 보관 이유 | 충족 | README `### 10.` 절에 플랫폼별 aud 표와 암호화·발급 client 저장 이유가 있다. 기존 절 수정은 D-10-2. |

## 직접 실행한 검증

- 테스트 DB: 기존 `chosung_daily_test_t10`, Redis DB 12를 `TEST_DATABASE_URL`·`TEST_REDIS_URL`로 지정했다. 로컬 접속 성공으로 기본 DB fallback이나 새 DB 생성은 하지 않았다. 접속 비밀번호·토큰 값은 이 문서에 기록하지 않는다.
- `uv run ruff check .` → `All checks passed!`.
- `FLASK_SKIP_DOTENV=1 FLASK_APP=wsgi.py uv run flask db heads` → `f394da7f4d88 (head)` 한 줄.
- `git diff --check main...HEAD` → 출력 없음, exit 0.
- 전체 테스트 최종 단독 실행: `uv run python` 안에서 아래 네트워크 가드를 설치하고 `pytest.main(['-q', '--tb=short'])` 실행 → **142 passed, 2 failed in 57.90s**.

```python
original = socket.socket.connect
def local_only(self, address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
        raise RuntimeError('review blocked external network')
    return original(self, address)
socket.socket.connect = local_only
```

두 실패는 `test_sync_then_login_redirects_to_provider`와 `test_sync_then_apple_login_redirects_to_provider`이다. `authorize_redirect → create_authorization_url → load_server_metadata → requests → socket.connect`에서 차단되었다. 기존 main에도 있는 테스트의 외부 discovery 의존성이므로 이번 구현의 회귀로 분류하지 않았다.

추가로 같은 네트워크 가드를 유지하면서 `FlaskOAuth2App.load_server_metadata`만 프로세스 메모리에서 provider별 `authorization_endpoint`를 반환하는 대역으로 교체하고 `pytest.main(['-q', 'tests/test_oauth_routes.py'])` 실행 → **10 passed in 6.78s**. 애플·구글 authorization endpoint 문자열만 제공했고 실제 요청은 하지 않았다. 이 결과는 실제 provider 왕복 성공을 뜻하지 않는다.

실행 과정의 제한도 남긴다. 최초 일반 pytest 실행에서 기존 두 테스트의 discovery 의존성을 뒤늦게 발견해 중단을 시도했으나 SIGINT가 즉시 종료시키지 못했고, 후속 실행과 DB 작업이 겹쳐 최초 결과는 112 passed/33 errors가 되었다. 두 프로세스의 종료를 확인한 뒤 위 단독 실행으로 다시 검증했다. 최초 실행은 네트워크 가드가 없었고 해당 리다이렉트 테스트가 통과했으므로, 리뷰 전체의 외부 호출 0건을 주장할 수 없다. 실제 계정 자격증명 입력·NAS 접속·배포·push는 하지 않았다. 구현 증거 문서의 “전체 테스트 통과, 외부 호출 0건” 역시 현재 테스트 코드만으로 뒷받침되지 않는다.

## 결함

### D-10-1 — MAJOR — 새 kid가 나타나도 JWKS를 갱신하지 않아 정상 로그인을 거부

- 위치: `app/services/app_login_service.py:81` 및 `app/services/id_token_service.py:41`.
- 재현: 기존 공개키로 `_verify`를 한 번 성공시켜 1시간 캐시를 채운다. JWKS 조회 대역의 응답을 새 kid의 공개키로 바꾸고, 그 키로 서명한 올바른 iss/aud/exp/sub의 토큰을 `_verify`에 전달한다.
- 기대: 캐시에 없는 kid이면 공개키를 제한적으로 다시 조회하고, 새 공개키와 서명이 맞는 정상 토큰을 수용한다. 갱신 뒤에도 없는 kid나 잘못된 서명은 계속 거부해야 한다.
- 실제: JWKS 조회 횟수는 1에 머물고 `INVALID_ID_TOKEN`이 발생한다. 같은 토큰으로 캐시만 비워 재시도하면 즉시 성공하며 조회 횟수가 2가 된다. 캐시가 따뜻한 각 프로세스에서 새 키로 발급된 로그인은 TTL 잔여 시간(최대 1시간) 동안 모두 실패할 수 있다. Apple은 code 교환 전에 실패한다.
- 기존 `test_unknown_kid_is_rejected`는 순수 검증 함수의 거부만 확인하고 서비스 계층의 키 갱신을 검증하지 않는다. 위 결과는 외부 호출 없이 다음 명령으로 직접 확인했다.

```sh
uv run python - <<'PY'
from app import create_app
from app.errors import InvalidIdTokenError
from app.models import OAuthProvider
from app.services import app_login_service as s
from tests.id_token_helpers import generate_rsa_key, jwks_for, sign_id_token
app = create_app('testing')
old, new = generate_rsa_key(), generate_rsa_key()
state = {'keys': jwks_for(old, 'old'), 'calls': 0}
def fetch():
    state['calls'] += 1
    return state['keys']
s.fetch_google_jwks = fetch
s._JWKS_CACHE.clear()
with app.app_context():
    aud = app.config['GOOGLE_IOS_CLIENT_ID']
    s._verify(OAuthProvider.GOOGLE, sign_id_token(old,
        issuer='https://accounts.google.com', audience=aud, kid='old'))
    state['keys'] = jwks_for(new, 'new')
    token = sign_id_token(new, issuer='https://accounts.google.com', audience=aud, kid='new')
    try:
        s._verify(OAuthProvider.GOOGLE, token)
    except InvalidIdTokenError:
        print('rotation: INVALID_ID_TOKEN; fetch calls:', state['calls'])
    s._JWKS_CACHE.clear()
    print('after cache clear:', bool(s._verify(OAuthProvider.GOOGLE, token)),
          'fetch calls:', state['calls'])
PY
```

출력: `rotation: INVALID_ID_TOKEN; fetch calls: 1`, `after cache clear: True fetch calls: 2`.

### D-10-2 — MINOR — 공유 파일의 자기 번호 append-only 규칙 위반

- 위치: `.env.example:24`, `.env.example:33`, `README.md:237`, `README.md:460`.
- 재현: `git diff main...HEAD -- .env.example README.md`.
- 기대: 티켓 공통 규칙대로 자신의 번호 소제목/행만 섹션 끝에 추가하고 기존 공유 내용을 수정하지 않는다.
- 실제: `.env.example` 기존 설명 행을 변경하고 번호 없는 설정 블록을 기존 Slack 설정 앞에 삽입했다. README는 허용된 API 행과 `### 10.` 추가 외에도 기존 OAuth 설명·제한사항의 함수명을 수정했다. 병렬 머지 충돌을 피하려고 명시한 편집 경계를 벗어난다. 기능 영향이 아닌 명시적 협업 규칙 위반이므로 MINOR로 분류한다.

## 참고 및 범위

신규 검증 테스트는 서명 판정을 mock하지 않으며, mock은 주로 JWKS/Apple 교환 경계에 있다. 토큰 저장은 Fernet 암호문이고 기존 계정 전환에서도 두 컬럼을 함께 갱신한다. Bearer 가드·고정 RS256·허용 issuer/aud·필수 exp/sub·Apple sub 대조를 확인했으며 변경분에서 실사용 시크릿 값 기록은 발견하지 못했다. revoke 및 자동 secret 갱신은 각각 후속 티켓 14·11의 범위라 누락 결함으로 올리지 않았다. 취향·스타일 제안은 없다.

결함 합계: BLOCKER 0, MAJOR 1, MINOR 1. 애플리케이션·테스트·설정·스펙은 수정하지 않았다.

판정: FAIL
