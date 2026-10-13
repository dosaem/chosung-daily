# 티켓 08 최종 리뷰 — 라운드 1

## 범위와 기준

- 검토 대상 HEAD: `f0342bb9ff76d7e5aabdbeb2cb473bfa9cd61274`.
- 로컬 main: `21856d88cc82d6cfb43afda30379ca6960691544`, merge-base: `72a2a3cb3202bc7d63cc884640081223f5ebf5f3`.
- `git diff main...HEAD` 전체 21파일과 `git log main..HEAD`의 5커밋을 확인했다. origin/main은 사용하지 않았다.
- 기준: 티켓 08, 스펙 §A.10·§A'·§C.29·§C.30, CONTEXT.md, 구현 증거 문서. UI 변경은 없어 디자인 검토 대상이 없다.
- 애플리케이션·테스트·설정·.scratch 파일은 수정하지 않았다. 외부 서비스 호출, 프로덕션 접근, 새 DB 생성은 하지 않았다.

## 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| AppSetting 테이블·마이그레이션·head 1개, 비인증 config 응답·60초 캐시 | 충족 | `app/models/app_setting.py`, `migrations/versions/ff06a1bf5afc_*.py`, `app/services/app_config_service.py`. 네 응답 필드, DB 행 반영, Redis 캐시와 TTL을 테스트가 실제 DB·Redis로 검증한다. head 출력은 아래 기록. 경로 `/api/v1/config`는 스펙 API prefix와 일치한다. |
| STORE_URL_IOS·STORE_URL_ANDROID·APP_STORE_ID 환경변수, 빈 링크 null, .env.example, 티켓 18 공용 설정 | 충족 | `app/config.py`가 세 환경변수를 읽는다. 별도 프로세스에서 세 변수에 합성 값을 지정하고 create_app 후 3개 값을 assert하여 통과했다. 빈 링크 null 및 지정 링크 응답은 config 테스트에서 확인한다. `.env.example`에 빈 값으로 추가했고 APP_STORE_ID는 티켓 18에서 쓸 Flask 설정으로 제공한다. 웹 구현 자체는 18의 범위다. |
| health 필드와 DB 실패 503 / Redis 실패 degraded 200 | 충족 | `app/api/health.py`의 실제 SELECT 1 및 Redis ping, `tests/test_health.py`의 정상·DB 장애·Redis 장애·동시 장애 검증. apple_secret_expires_at=null은 티켓 11 전까지 허용된다. |
| DSN 있을 때만 Sentry Flask·Celery 통합, 릴리스·환경 태그 | 충족 (보안 결함 별도) | 초기화 테스트와 별도로 실제 SDK + 메모리 Transport로 기존 Flask 콜백 500 오류와 Celery task.apply 오류 이벤트를 수집했다. 환경·릴리스 태그도 확인했다. DSN 없는 경로는 초기화하지 않는다. 다만 요청 본문 민감정보가 그대로 수집되는 D-08-1이 있다. |
| README 설계 판단 2개 및 UptimeRobot 사람 등록 메모 | 충족 | README의 `### 08.` 두 절과 운영 절에 DB 설정 선택 이유, 헬스 등급, HTTP 상태코드 모니터·5분 간격·사람 등록이 있다. |

## 직접 실행한 검증

- `uv run pytest -q` → **203 passed in 125.38s (0:02:05)** (exit 0). 실패·skip·xfail 없이 1회 통과하여 재실행하지 않았다. 기존 `chosung_daily_test_t08`, Redis DB 10, 기존 `chosung_daily_test_t08_migrations`를 재사용했다. 기본 테스트 DB로 폴백하지 않았다.
- 실행 환경은 `TEST_DATABASE_URL`을 로컬 전용 t08 DB, `TEST_REDIS_URL=redis://127.0.0.1:6379/10`, `TEST_MIGRATION_DATABASE_URL`을 로컬 전용 t08_migrations DB로 지정했다. 접속 문자열의 인증 부분은 이 문서에 기록하지 않는다. SENTRY_DSN·SLACK_WEBHOOK_URL은 비워 외부 전송을 막았다.
- `uv run ruff check .` → `All checks passed!` (exit 0).
- `FLASK_SKIP_DOTENV=1 SENTRY_DSN='' FLASK_APP=wsgi.py uv run flask db heads` → `ff06a1bf5afc (head)` 한 줄 (exit 0).
- `git diff main...HEAD --check` → 출력 없음 (exit 0).
- Sentry 수동 검증은 실제 SDK의 `Transport.capture_envelope`를 메모리 수집기로 대체했다. HTTP 전송 transport를 사용하지 않았고 provider 함수도 로컬 예외로 대체했다. Celery는 `task.apply(throw=False)`로 로컬 실행했다.

## 결함

### D-08-1 — Sentry가 OAuth 인증 코드·사용자 JSON을 요청 본문에 보존한다

- **심각도: MAJOR**
- **파일:라인:** `app/observability.py:22` (초기화 옵션), `app/observability.py:14` (잘못된 개인정보 보호 설명). 관련 문서 `README.md:570`, 검증 누락 `tests/test_sentry.py:17`.
- **원인:** `send_default_pii=False`만 지정하면 요청 본문이 제외된다는 가정은 실제 설치된 SDK 2.72.0 동작과 다르다. 기본 요청 본문 수집이 켜져 있고, OAuth의 `code` 및 문자열로 인코딩된 `user` JSON이 스크러빙되지 않는다.
- **재현 입력/절차:**
  1. `uv run python -`에서 `create_app('testing')`를 만들고 TESTING=False로 설정한다. 기존 테스트의 가짜 DSN과 임의 릴리스명을 사용하되, `sentry_sdk.init`에 메모리 전용 Transport를 추가해 실제 `init_sentry(app)`를 실행한다.
  2. 테스트 클라이언트 session에 `oauth_pending_guest_id=1`을 넣는다. `app.api.oauth._get_client`가 반환하는 객체의 `authorize_access_token`을 외부 요청 없이 RuntimeError를 발생시키는 함수로 교체한다.
  3. 기존 `/api/v1/auth/apple/callback`에 form POST한다. `code`에는 비밀이 아닌 임의 표식, `user`에는 가상 이메일을 담은 JSON 문자열을 넣는다. 실제 인증정보는 사용하지 않는다.
  4. `sentry_sdk.flush()` 후 수집한 이벤트의 `request.data`를 검사한다.
- **기대:** 오류 이벤트·환경·릴리스는 수집되지만 인증 코드와 사용자 개인정보는 제거되거나 마스킹된다.
- **실제:** HTTP 500, 이벤트 1건. `request.data.code`와 `request.data.user`가 입력과 동일하게 남았다. 별도의 JSON POST에서도 `authorization_code`와 `receipt` 필드가 원문으로 남는 것을 확인했다. 운영에서 DSN을 켜면 이 이벤트가 외부 Sentry로 전송된다.
- **영향:** 기존 Apple OAuth 콜백의 예외만으로 인증 코드와 최초 로그인 사용자 정보가 관측 시스템으로 복제된다. 현재 README·독스트링의 “쿠키·바디가 자동으로 따라가지 않는다”는 보장도 성립하지 않는다.
- **필요한 수정:** 요청 본문 수집을 끄거나 민감 필드와 중첩 JSON을 전송 전에 제거하고, 쿼리·로컬 변수 등 다른 이벤트 경로도 같은 보호 기준으로 검토해야 한다. 초기화 인자 mock 검증 외에 메모리 Transport를 사용하는 이벤트 내용 회귀 검증이 필요하다.

## 기타 검토 및 참고

- 테스트는 config의 실제 DB 행·Redis 캐시와 마이그레이션 upgrade/downgrade를 사용한다. health의 장애 mock은 외부 의존성 실패 경계를 대체한다. Sentry 테스트는 init 인자만 확인하여 위 결함을 탐지하지 못한다.
- 신규 API는 읽기 전용·비인증 요구사항에 맞고 DB 설정 쓰기 엔드포인트를 노출하지 않는다. 신규 마이그레이션은 독립 테이블 생성/삭제이며 기존 테이블 데이터를 변경하지 않는다.
- 공유 파일: `.env.example`은 끝에 `[08]` 블록을 추가했고 README 설계 판단은 해당 절 끝에 `### 08.`을 추가했다. API 표는 티켓 소유 config 행 추가 및 health 행 설명 갱신으로 한정되어 다른 티켓 행을 변경하지 않았다. 범위 밖 기능 변경은 발견하지 못했다.
- 변경 파일에서 실제 시크릿 하드코딩은 발견하지 못했다. 예시 DSN과 테스트 데이터는 더미다. D-08-1은 파일 저장 문제가 아니라 런타임 이벤트에 민감정보가 포함되는 문제다.
- 구현 증거의 “4커밋·20파일”은 현재 HEAD의 실제 5커밋·21파일과 다르다. 문서 자체 추가 등에 따른 메타데이터 차이로 기능 결함에 포함하지 않는다.
- UptimeRobot 실제 등록, 실제 Sentry 수신, 브로커를 이용한 별도 워커 프로세스 전송은 수행하지 않았다. 로컬 오류 수집 검증과 구분한다.

## 최종 결과

BLOCKER 0개 / MAJOR 1개 / MINOR 0개. D-08-1 수정 후 재리뷰가 필요하다.

판정: FAIL

## 라운드 2

### 범위와 기준

- 검토 HEAD `bcc02b49e7290377e4c2f7a42eda8b12a31927b4`, 로컬 main `0abb1d79d8eea3701893e57313745ad566e19632`, merge-base `20d279a256d0f17152ae6ac273f4758c80fbb712`.
- `git diff main...HEAD` 22파일 및 `git log main..HEAD` 9커밋을 확인했다. origin/main은 사용하지 않았다. 티켓 08, 스펙 §A.10·§A' config/health·§C.29·§C.30, CONTEXT.md와 구현 증거의 수정 라운드를 대조했다.
- UI 변경이 없어 디자인 검토는 해당 없음. 하위 에이전트 없이 직접 검토했다. 리뷰 문서 외 파일 변경, 새 DB 생성, 프로덕션 접근, 실제 외부 서비스 호출은 하지 않았다.

### 티켓 체크박스별 확인

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| AppSetting 테이블·마이그레이션·head 1개, 비인증 config 네 필드·60초 캐시 | 충족 | 모델/마이그레이션과 `app/services/app_config_service.py:20`의 TTL 60을 확인했다. `tests/test_app_config.py`가 실제 DB 설정 행 반영, 인증 없는 응답 전체, Redis 캐시 유지·TTL·장애 폴백을 검증한다. 마이그레이션 6개 테스트와 head 확인이 통과했다. 새 마이그레이션의 부모는 `f394da7f4d88`이다. |
| 환경변수 STORE_URL_IOS·STORE_URL_ANDROID·APP_STORE_ID, 빈 링크 null, .env.example, 티켓 18 공용 출처 | 충족 | `app/config.py:65`부터 세 환경변수를 읽고 `.env.example` 끝의 08 블록에 선언한다. 별도 프로세스에서 세 환경변수에 합성 값을 넣어 create_app 설정값 일치를 직접 assert했다. 기본 null 및 링크 응답 테스트 통과. APP_STORE_ID를 Flask 설정으로 제공하며 웹 배지 자체 구현은 18 범위다. |
| health 네 필드, DB 실패 503 / Redis 실패 200+degraded | 충족 | `app/api/health.py:18`과 실제 SELECT 1·Redis ping 경로를 확인했다. 정상·DB 장애·Redis 장애·동시 장애 테스트 모두 통과. apple_secret_expires_at=null은 티켓 11 전까지 허용된다. |
| DSN 있을 때만 Sentry Flask·Celery 통합, 환경·릴리스 태그 | 충족 | `app/observability.py:57`의 DSN 가드, 통합 등록과 태그를 확인했다. 실제 SDK와 메모리 Transport로 Flask 오류 및 Celery 로컬 task 오류를 수집하는 회귀 테스트가 통과했다. D-08-1 수정 확인은 아래 기록. |
| README 설계 판단 두 항목 및 UptimeRobot 사람 등록 메모 | 충족 | README의 `### 08.` 두 절과 운영 절에 DB 설정 선택 이유, DB/Redis 헬스 등급, 5분 HTTP 상태코드 모니터와 사람 등록 안내가 있다. |

### 직접 실행한 검증

- `uv run pytest -q` → **318 passed in 145.86s (0:02:25)**, exit 0. 실패·skip·xfail 없이 1회 통과하여 재실행하지 않았다.
- 기존 로컬 `chosung_daily_test_t08`와 `chosung_daily_test_t08_migrations`를 각각 `TEST_DATABASE_URL`·`TEST_MIGRATION_DATABASE_URL`로 지정하고 `TEST_REDIS_URL=redis://127.0.0.1:6379/10`을 사용했다. 접속 성공으로 기본 테스트 DB 폴백은 없었다. 인증 부분은 기록하지 않는다. `FLASK_SKIP_DOTENV=1`, SENTRY_DSN·SLACK_WEBHOOK_URL 빈 값으로 실행했다.
- `uv run ruff check .` → `All checks passed!`, exit 0.
- `FLASK_SKIP_DOTENV=1 SENTRY_DSN='' FLASK_APP=wsgi.py uv run flask db heads` → `ff06a1bf5afc (head)` 한 줄, exit 0.
- `git diff main...HEAD --check` → 출력 없음, exit 0.
- 별도 `uv run python -` 프로세스에서 환경변수 3개 로딩을 assert하고, 실제 Sentry SDK의 Transport만 메모리 수집기로 교체해 JSON POST 오류를 발생시켰다. 본문 authorization_code·receipt, 쿼리 code, Authorization 헤더에 넣은 더미 표식이 이벤트 전체에 없고 스택 프레임 vars도 없음을 assert했다. HTTP 500/오류 이벤트 1건과 환경·릴리스가 유지됐다. 외부 전송은 하지 않았다.

### 이전 결함 판정

#### D-08-1 — FIXED (이전 심각도 MAJOR)

- **파일:라인:** `app/observability.py:18`, `app/observability.py:66`; 회귀 검증 `tests/test_sentry.py:147`, `tests/test_sentry.py:172`, `tests/test_sentry.py:188`, `tests/test_sentry.py:211`.
- **재현:** 위 테스트 환경에서 `uv run pytest -q` 실행. Apple form POST에 code/user/id_token 더미 표식을 넣고 provider 경계에서 로컬 RuntimeError를 발생시키며, Google GET 콜백에는 code 쿼리 표식을 넣는다. 실제 SDK가 만든 메모리 이벤트를 확인한다. 추가 JSON POST 수동 검증도 같은 오류 수집 경로로 실행했다.
- **기대:** 오류 자체와 환경·릴리스는 보존하고 요청 본문·쿼리·쿠키·지역 변수의 인증정보는 이벤트에 남기지 않는다.
- **실제:** 회귀 테스트와 수동 검증이 통과했다. data_collection이 본문·쿼리·쿠키·유저 정보·SQL 바인드 데이터·큐 인자·지역 변수 수집을 끈다. SDK 초기화 인자를 mock으로 확인하는 데 그치지 않고 실제 완성된 이벤트의 민감 표식 부재와 오류 존재를 검증한다. 이전 결함은 재현되지 않았다.

### 새 결함 및 기타 검토

- 새 결함 없음. 미해결 BLOCKER 0개 / MAJOR 0개 / MINOR 0개, REPEAT 0개, FIXED 1개.
- 신규 config는 읽기 전용 비인증 요구에 맞고 설정 쓰기 API는 노출하지 않는다. 기존 인증·CSRF 경로 변경은 없다. 마이그레이션은 독립 설정 테이블을 만들며 기존 테이블 데이터를 바꾸지 않는다. downgrade/upgrade 및 SQL 직접 삽입 검증도 통과했다.
- 공유 파일은 README 08 설계 판단·config 행·health 소유 행 설명과 해당 운영 안내, `.env.example`의 08 블록에 한정된다. 다른 티켓의 설계 판단·환경변수 블록 변경이나 범위 밖 기능 변경은 발견하지 못했다. 변경 파일에 실제 시크릿이 기록된 정황은 발견하지 못했다.
- 참고: pyproject의 SDK 하한은 넓지만 현재 uv.lock과 Dockerfile의 frozen 설치가 검증한 SDK 2.72.0을 사용한다. 이번 판정은 이 잠금 환경 기준이다.
- 한계: 실제 Sentry 서버 수신, 별도 브로커/워커 프로세스 전송, UptimeRobot 등록은 수행하지 않았다. 메모리 Transport와 Celery 로컬 실행 검증으로 구분한다. Apple 만료 시각 채우기와 웹 배지는 각각 후속 티켓 11·18의 범위다.

판정: PASS
