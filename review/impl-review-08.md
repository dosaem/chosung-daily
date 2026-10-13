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
