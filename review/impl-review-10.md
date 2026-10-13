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

## 라운드 2

검토 대상 HEAD `853bfb6`, 로컬 main `21856d8`, 공통 조상 `72a2a3c` 기준으로 `git diff main...HEAD`와 `git log main..HEAD`를 직접 확인했다. origin/main은 사용하지 않았다. 티켓 10, 스펙 §A.6·§A.17·§A'·미정 17, ADR 0002, CONTEXT.md, 이전 리뷰 및 구현 증거를 대조했다. UI 변경은 없다.

### 체크박스별 확인

| 티켓 요구 | 판정 | 근거 |
|---|---|---|
| Account 두 컬럼·SECRET_KEY 파생 Fernet·단일 migration head | 충족 | `app/models/account.py:37`, `app/utils/crypto.py:11`, migration `f394da7f4d88`의 nullable 컬럼 추가/제거 확인. 암복호·다른 키 거부 테스트 통과. 마이그레이션 왕복 테스트 4개는 두 전체 실행에서 통과했고 heads는 1개다. |
| Google/Apple 외부 래퍼·순수 id_token 검증·진짜 서명 테스트 | 충족 | `app/clients/google_jwks.py:10`, `app/clients/apple.py:8`, `app/services/id_token_service.py:17`. 테스트 RSA 키로 서명하고 실제 jwt.decode를 실행한다. 다른 서명·issuer·aud·만료·없는 sub·HS256·none 거부를 직접 실행해 확인했다. |
| Bearer token-exchange·aud 매트릭스·연결/전환·오류 코드 | 충족 | `app/api/oauth.py:109`, `app/services/app_login_service.py:69`. 관련 HTTP 테스트에서 Google iOS/Android aud, 401 INVALID_ID_TOKEN, 기존 게스트 전환, 409 ACCOUNT_ALREADY_LINKED, Bearer 누락 거부를 확인했다. D-10-1 수정도 통과. |
| Apple code 교환·번들 JWT·sub 대조·암호화 저장/덮어쓰기 | 충족 | `app/services/app_login_service.py:137`, `app/services/account_service.py:39`, `app/extensions.py:93`. 번들 client_id/JWT sub, 교환 토큰 재검증, sub 불일치 시 DB 저장 없음, 전환 시 새 토큰 복호화 및 client 저장을 확인했다. |
| 웹 Apple 콜백의 refresh token·Services ID 저장·기존 테스트 | 충족 | `app/api/oauth.py:87`, `tests/test_oauth_routes.py:146`. 웹 저장·Google 비저장 및 기존 로그인 가드/리다이렉트 테스트 통과. discovery만 대역으로 바뀌었으며 실제 외부 인증 성공을 보증하지는 않는다. |
| 신규 설정값·Apple 키 설명·미정 17 반영 | 충족 | `app/config.py:39`, `.env.example:43`, 스펙의 티켓 10 추가 행. 세 aud 설정과 기존 Apple 서명 키 공유, 두 client의 갱신 후속 범위가 명시되어 있다. |
| README ADR 0002·aud 표·보관 이유 | 충족 | `README.md:506`의 `### 10.` 절에 aud 표·암호화와 발급 client 보관 이유가 있다. 기존 문서 행 수정은 제거되었다. |

### 이전 결함 재판정

- **D-10-1 — FIXED (이전 MAJOR)**
  - 위치: `app/services/app_login_service.py:101`, `app/services/id_token_service.py:64`, `tests/test_token_exchange.py:339`.
  - 재현 입력: 이전 키 로그인으로 캐시를 채운 뒤 JWKS 대역을 새 kid의 키로 바꾸고 새 키로 서명한 정상 토큰을 POST한다. 기대는 200, JWKS 조회 2회, 계정 생성이며 실제 결과도 동일하다.
  - Apple 교환 응답만 새 키인 경우도 200 및 refresh token 덮어쓰기를 검증했다(`tests/test_token_exchange.py:402`). 모르는 kid를 반복 제출하면 계속 401이고 조회는 첫 조회+재조회 2회에 머문다(`:376`). 세 회귀 테스트가 아래 50개 실행에 포함되어 통과했다. 최대 1시간 고정 거부는 해소되었고 재조회에는 provider별 60초 제한이 있다.
- **D-10-2 — FIXED (이전 MINOR)**
  - 위치: `.env.example:43`, `README.md:506`.
  - 재현 명령: `git diff main...HEAD -- .env.example README.md .scratch/store-launch/spec.md`.
  - 기대는 기존 공유 행 보존 및 자기 설정/절/행 추가이며 실제로 세 파일 모두 삭제·수정 행 0개다. 환경 설정은 파일 끝, README는 API 행과 자기 번호 절, 스펙은 미정 항목 끝의 티켓 10 행으로 추가되어 이전 삽입 위치·기존 함수명 수정 문제가 사라졌다.

신규 결함 없음. 미해결 결함: **BLOCKER 0, MAJOR 0, MINOR 0**.

### 직접 실행한 검증과 제한

기존 로컬 `chosung_daily_test_t10` 및 Redis DB 12를 `TEST_DATABASE_URL`·`TEST_REDIS_URL`로 지정했다. 마이그레이션 테스트는 기존 `chosung_daily_test_t10_migrations`를 기본 이름 규칙으로 재사용했다. DB를 새로 만들지 않았고 기본 DB로 전환하지 않았다. 전용 DB 접속 자체는 성공했으며 아래 오류는 MySQL 서버의 접속 개수 한도였다. 비밀번호나 토큰 값은 기록하지 않는다.

모든 pytest 실행은 `FLASK_SKIP_DOTENV=1 uv run python`에서 다음 가드를 설치한 뒤 `pytest.main(...)`으로 실행했다. 코드·테스트 파일을 바꾸거나 검증 함수를 대역으로 바꾸지 않았다.

```python
import socket
original = socket.socket.connect
def local_only(self, address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
        raise RuntimeError('review blocked external network')
    return original(self, address)
socket.socket.connect = local_only
```

- `uv run ruff check .` → **All checks passed!** (exit 0).
- `FLASK_SKIP_DOTENV=1 FLASK_APP=wsgi.py uv run flask db heads` → **f394da7f4d88 (head)** 한 줄.
- `git diff --check main...HEAD` → 출력 없음, exit 0.
- 전체 1차 `pytest.main(['-q', '--tb=short'])` → **222 passed, 3 errors in 135.33s**. `tests/test_word_service.py`의 seed_words 테스트 3개가 fixture setup의 `db.create_all()` 접속 단계에서 `(1040, 'Too many connections')`로 실패했다.
- 지시대로 전체 재실행 `pytest.main(['-q', '--tb=line'])` → **190 passed, 35 errors in 148.28s**. 역시 같은 MySQL 접속 오류이며 실패 위치가 퍼즐·통계·암호화 등의 fixture setup으로 바뀌었다. 테스트 assertion 실패는 없었다. 다른 프로세스와의 경합 여부까지 확정하지는 못했으며 DB 설정 변경이나 다른 세션 종료는 하지 않았다.
- 티켓 관련 파일을 새 프로세스로 분리 실행: `pytest.main(['-q', '--tb=line', 'tests/test_token_exchange.py', 'tests/test_id_token_verify.py', 'tests/test_secret_crypto.py', 'tests/test_apple_client.py', 'tests/test_oauth_routes.py', 'tests/test_account_service.py'])` → **50 passed in 38.33s**, exit 0.

따라서 구현 증거의 전체 225개 통과 주장을 이번 환경에서 재확인했다고 쓰지 않는다. 전체 회귀 검증에는 위 접속 한도 제한이 남아 있지만, 티켓 관련 50개는 별도 실행에서 모두 통과했고 최초 전체 실행의 오류 3개는 이번 diff에서 변경되지 않은 단어 시드 테스트의 DB 접속 단계다. 이 환경 오류를 티켓 구현 결함으로 분류할 근거는 발견하지 못했다.

### 보안·범위 및 참고

Bearer 가드, 고정 RS256, 허용 issuer/aud와 필수 exp/sub, Apple 교환 토큰의 sub 대조, Fernet 암호문 저장 및 두 컬럼의 동일 커밋 갱신을 확인했다. 서명 검증을 항상 통과시키는 mock은 없고 외부 provider 경계를 대체한다. 신규 실사용 시크릿 기록·데이터 삭제 경로·무관한 기능 변경은 발견하지 못했다. OAuth discovery 대역은 이전 리뷰의 외부 호출 문제를 해결하는 테스트 변경이다. 실제 provider 왕복, 콘솔 설정, revoke(티켓 14), secret 자동 갱신(티켓 11)은 이번 판정 범위 밖이다. 취향·스타일 제안은 없다.

이번 리뷰는 애플리케이션·테스트·설정·`.scratch/`를 변경하지 않고 이 리뷰 파일만 수정했다. NAS·배포·실제 외부 서비스 호출·push는 하지 않았다.

판정: PASS
