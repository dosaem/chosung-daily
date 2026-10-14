# 티켓 14 최종 리뷰 — 라운드 1

- 검토 기준: 로컬 `main` = `1e764da6d8ec4710d4ebf945249a6e264bd75f84`, 구현 HEAD = `6f6be586102ae8fefb61a9f68983409bbc24f7d7`.
- `git diff main...HEAD` 및 `git log main..HEAD`의 구현 커밋 5개를 검토했다. `origin/main`은 사용하지 않았다.
- 요구사항: 티켓 14, 스펙 §A.7·US 21/22/22a·미정 11, `CONTEXT.md`, 디자인 `SCREENS.md`와 `OVERRIDES.md` 우선 규칙. 구현 증거 문서는 참고하되 아래 검증을 직접 수행했다.
- 결함 합계: BLOCKER 0 / MAJOR 3 / MINOR 0.

## 체크박스별 판정

| 티켓 항목 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 공통 삭제 서비스, 6개 테이블 삭제·커밋, 언어별 오늘 ZREM, 옛 Bearer 401 | 충족(정상 경로) | `account_deletion_service.py:45` 이하에서 자식 5종과 Guest를 삭제·커밋하고 ko/en ZREM을 수행한다. `test_account_deletion.py`는 실제 MySQL·Redis로 삭제 범위, 다른 게스트 보존, 커밋, 401을 확인한다. Redis는 DB 트랜잭션 밖이며 장애 시 잔류 제한은 아래 참고에 기록했다. |
| 웹 GET 안내/확인·ko/en·토큰 CSS, POST 세션/CSRF·세션 비우기·리다이렉트, GET 무삭제 | 미충족 | 기본 401/403/302와 GET 무삭제는 구현되어 있다. 그러나 확인 폼의 삭제 대상이 렌더 시점 게스트에 묶이지 않아 계정 전환 후 다른 기록을 삭제한다(D-14-2). |
| Apple revoke 래퍼, 저장된 refresh token과 발급 client별 secret 사용 | 충족 | `clients/apple.py:52`의 요청 본문·timeout, `apple_revocation_service.py:104`의 공개 secret 접근자 호출 확인. 테스트는 실제 암호화·복호화·JWT 생성을 거치고 외부 HTTP만 대역 처리하여 iOS/웹 client_id 및 JWT sub를 확인한다. |
| 실패 재시도 행·마이그레이션·단일 head·매일 Beat·7일 초과 폐기/알림 | 미충족 | 정상 실패·재시도·폐기 및 Beat 배선은 구현되어 있다. 하지만 삭제 커밋과 재시도 저장이 분리되어 저장 실패 때 유일한 철회 자격증명이 영구 유실된다(D-14-3). head는 `94a83f12fddb` 하나다. |
| 삭제 성공 후 localStorage 정리·새 게스트·수동 체크리스트 | 미충족 | 정상 리다이렉트 후 새 게스트 발급은 동작하지만 삭제 성공 여부를 확인하지 않아 임의 링크만으로 살아 있는 게스트의 토큰을 잃는다(D-14-1). 체크리스트는 RELEASE §14에 있다. |
| 삭제 데이터 목록·방침 파기/권리 링크·ko/en 템플릿·핵심 문구 | 충족 | 양쪽 템플릿의 수집 항목 명칭, 되돌릴 수 없음·스토어 별도 해지, `#collection`·`#rights` 링크와 실제 방침 앵커를 대조했다. 문구의 법적 적정성은 티켓 16 범위다. |
| detect 0건·README 설계 판단·Play 삭제 URL | 충족 | 렌더한 ko/en × 안내/확인 4개 화면에서 detect exit 0/0건. README §14와 RELEASE §14의 삭제 URL을 확인했다. |
| 필요 시 재시도 구현을 별도 티켓으로 분할 | 충족(분할 불필요) | 재시도 테이블·Beat·7일 폐기를 이 티켓에 포함했다. |

## 결함

### D-14-1 — MAJOR — 임의 GET 링크로 유효한 게스트의 유일한 복구 수단을 제거

- 위치: `web/static/app.js:349`–`360` (특히 351, 353), 호출 `web/static/app.js:385`.
- 재현 입력: 계정 연결·별도 백업이 없는 게스트로 플레이한 브라우저에서, 삭제 폼을 제출하지 않고 `/?deleted=1` 링크를 연다. `?deleted=0`이나 값 없는 `?deleted`도 같은 분기를 탄다.
- 기대: 서버에서 계정 삭제가 완료됐다는 확인 없이 기존 토큰·기록을 지우지 않는다.
- 실제: 쿼리 키의 존재만으로 `chosung_token`과 모든 `chosung_history_*`를 지운다. 이어 `ensureToken()`이 새 게스트를 발급하고 `syncSession()`이 기존 세션도 새 게스트로 바꾼다. DB의 옛 기록은 살아 있지만 계정 연결·백업이 없는 플레이어는 다시 접근할 수 없다. 외부 사이트가 보내는 링크만으로 유발할 수 있으며 서버 삭제 POST의 CSRF 방어를 거치지 않는다.
- 직접 검증: Node `vm`에서 저장소·DOM·fetch만 대역으로 제공하고 **실제 `web/static/app.js`**를 로드했다(마지막 자동 `init()` 호출만 제거). 기존 저장소를 넣고 위 URL로 `discardDeletedAccountState(); await ensureToken()` 실행 결과 `originalTokenRetained=false`, `historyRetained=false`, `issuedNewGuest=true`, 요청은 `POST /api/v1/guests` 한 건뿐이었다. 계정 삭제 요청은 없었다.
- 기존 검증의 빈틈: `tests/test_web.py:27`은 JS 문자열 세 개의 존재만 확인하므로 삭제 성공에 대한 검증 누락을 잡지 못한다.

### D-14-2 — MAJOR — 계정 전환 전에 연 삭제 폼이 전환 후 게스트를 삭제

- 위치: `app/web.py:103`, `app/web.py:117`–`125`.
- 재현 입력(실제 Flask 클라이언트·전용 MySQL/Redis): 게스트 A/B를 발급 → A의 Bearer로 `POST /api/v1/session/sync` → `GET /account/delete`에서 CSRF를 추출 → 같은 브라우저에서 B의 Bearer로 `POST /api/v1/session/sync` → A 화면에서 받은 CSRF로 `POST /account/delete`. 브라우저에서는 A 삭제 확인 탭을 둔 채 다른 탭에서 백업 코드를 복원하거나 계정을 전환한 뒤 옛 탭의 삭제 버튼을 누르는 상황이다.
- 기대: A에 대해 연 확인 폼은 B로 세션이 바뀌면 거부하고 B의 삭제 확인을 새로 받아야 한다.
- 실제: 302로 성공하고 **A는 남고 B가 삭제**된다. CSRF는 세션 전환 후에도 그대로 유효하며, POST가 현재 `current_guest_id`만 조회해 삭제 대상을 바꾼다. 따라서 다른 계정의 기록·구독 연결까지 되돌릴 수 없이 지운다.
- 직접 검증 결과: `status=302`, `original_guest_exists=true`, `switched_guest_exists=false`. 서비스와 DB 삭제를 mock하지 않았다.
- 기존 검증의 빈틈: 두 번째 탭 테스트는 이미 삭제된 동일 게스트의 옛 쿠키만 다루며, 폼 렌더와 제출 사이의 **다른 게스트로 전환**을 다루지 않는다.

### D-14-3 — MAJOR — 재시도 저장 전에 원본 계정을 커밋 삭제하여 철회 정보 유실

- 위치: `app/services/account_deletion_service.py:51`–`55`, `app/services/apple_revocation_service.py:44`–`45`.
- 재현 입력: 저장된 refresh token/client_id가 있는 Apple 계정 삭제 → Apple 호출 실패 → 그 뒤 재시도 INSERT의 커밋에서 DB 연결 장애. 전용 DB에서 실제 계정을 생성하고 `_revoke`만 실패 대역으로 바꾼 뒤 `db.session.commit`의 첫 호출은 실제 실행, 두 번째 호출은 `OperationalError`를 발생시키고 요청 종료에 해당하는 rollback을 수행했다.
- 기대: 삭제 후에도 철회가 성공하지 않은 토큰/client_id는 내구성 있게 남아 Beat가 재시도할 수 있어야 한다.
- 실제: `commits_attempted=2`, `guest_exists=false`, `account_exists=false`, `retry_count=0`. 삭제는 이미 커밋됐고 재시도 정보는 없으므로 Beat는 영구히 복구할 수 없다. 이후 같은 Bearer의 삭제 재요청도 401로 끝난다. 삭제 커밋 이후 프로세스가 종료되는 경우에도 같은 유실 구간이 존재한다.
- 기존 검증의 빈틈: `test_failed_revoke_still_deletes_the_account_and_records_a_retry`는 외부 호출만 실패시키고 이후 DB 저장이 항상 성공하는 경우만 확인한다. 삭제 성공과 철회 의무의 영속화 사이 장애를 확인하지 않는다.

## 직접 실행한 검증

- 테스트 환경: 기존 `chosung_daily_test_t14`, 기존 `chosung_daily_test_t14_migrations`, Redis DB 2를 각각 `TEST_DATABASE_URL`, `TEST_MIGRATION_DATABASE_URL`, `TEST_REDIS_URL`로 지정했다. 접속 성공하여 기본 테스트 DB로 폴백하지 않았고 새 DB도 만들지 않았다. 접속 자격증명은 이 문서에 기재하지 않는다.
- 전체 `uv run pytest -q`는 병렬 워커 실행 중 범위를 좁히기 위해 직접 중단했다: **117 passed in 191.42s**, KeyboardInterrupt, exit 2. 전체 스위트 통과로 계산하지 않는다.
- 변경 영역 및 인접 보안·문서 검증 명령:

```sh
uv run pytest -q tests/test_account_deletion.py tests/test_apple_revocation.py \
  tests/test_account_delete_page.py tests/test_web.py tests/test_celery_wiring.py \
  tests/test_migrations.py tests/test_csrf.py tests/test_legal_pages.py
```

- 위 집중 실행 결과: **175 passed in 296.01s (0:04:56)**, exit 0. 간헐 실패 없이 완료하여 재실행하지 않았다. 마이그레이션 왕복 테스트도 이 실행에 포함된다.
- `uv run ruff check .`: **All checks passed!**, exit 0.
- `FLASK_ENV=testing uv run flask --app wsgi db heads`: **`94a83f12fddb (head)` 한 줄**, exit 0.
- `git diff main...HEAD --check`: 출력 없음, exit 0.
- impeccable 0.1.14: Flask 템플릿을 ko/en·CSRF 유무별로 메모리에 렌더하고 127.0.0.1 임시 서버에서 실제 `tokens.css`·`legal.css`·`account.css`를 제공했다. 4개 URL 모두 **exit 0, findings 0**. 외부 호출 금지를 지키려고 메모리 HTML에서 CDN 폰트 링크만 제외했으며 원본 파일은 수정하지 않았다. 따라서 실제 CDN 폰트 로드까지 검증한 결과는 아니다. 탐지기 대조군 `design/archive/v2_softdark_home.html`은 **7건, exit 2**로 탐지 동작도 확인했다.
- 결함 재현은 셸 heredoc의 Node/Python 실행으로 수행했다. 앱·테스트·설정·`.scratch/` 파일은 수정하지 않았고, 실제 Apple·Google·Slack 호출 없이 대역과 로컬 자원만 사용했다.

## 범위·공유 파일·보안 점검 및 참고

- README 설계 판단은 `### 14.`를 추가했고 API/Beat 표도 자기 기능 행을 덧붙였다. RELEASE는 `### 14.` 추가뿐이다. 다른 티켓의 절을 덮어쓰거나 `.env.example`·스펙을 수정하지 않았다. 방침 템플릿 변경은 삭제 페이지 링크용 앵커 두 개씩 추가한 범위다.
- Bearer 인증, 세션 유효 Guest 조회, CSRF 불일치/누락, 암호문 보관, 외부 호출 timeout을 확인했다. 신규 파일에서 실제 서비스 비밀키·토큰은 발견하지 않았다. 테스트 더미와 공개 개발 접속 예시는 실제 운영 시크릿으로 분류하지 않았다.
- Redis ZREM은 DB 커밋 뒤 best-effort이며 재시도가 없다. Redis 장애 시 당일 순위가 남는다는 구현 증거의 제한은 코드와 일치한다. DB와 Redis가 원자적 한 트랜잭션이라는 증거 문서의 체크박스 표현으로 해석해서는 안 된다.
- RELEASE §14 수동 체크리스트의 “삭제 전 … 옛 토큰 … 401”은 문맥상 삭제 **후** 확인을 뜻한다. 실제 삭제 전 토큰은 정상적으로 유효하다.
- 브라우저 전체 클릭 E2E와 실제 Apple 철회 수락은 이번 리뷰에서 실행하지 않았다. 정상 경로 자동 테스트 통과가 위 세 경계 상황의 안전성을 보장하지 않는다.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` = `b8f63cc4c71572f541f926558e565bb0ddd38010`, 구현 HEAD = `301fa1140efdcc74eb2995292e1a0820c8a32454`. `git diff main...HEAD`와 `git log main..HEAD`의 8개 커밋을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 14, 스펙 §A.7·US 21/22/22a·미정 11, `CONTEXT.md`, `SCREENS.md`, 우선하는 `OVERRIDES.md`와 구현 증거의 수정 라운드 1을 대조했다. 하위 에이전트 없이 직접 검토했다.
- 이전 결함: **D-14-1 FIXED / D-14-2 FIXED / D-14-3 FIXED**. REPEAT 0건, 새 결함 0건. 현재 미해결 합계: **BLOCKER 0 / MAJOR 0 / MINOR 0**.

### 체크박스별 판정

| 티켓 항목 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 공통 삭제 서비스·6개 테이블 삭제/커밋·언어별 오늘 ZREM·옛 Bearer 401 | 충족 | `account_deletion_service.py:54`부터 철회 의무를 추가하고 자식 5종과 Guest를 같은 DB 트랜잭션으로 커밋한다. API와 웹이 이 함수를 공유한다. 실제 MySQL/Redis 테스트에서 삭제 범위, 다른 게스트 보존, rollback 후 삭제 유지, ko/en ZREM, 옛 토큰 401을 확인했다. Redis 원자성 한계는 아래 참고와 같다. |
| GET 확인/안내·ko/en·토큰 CSS·POST 세션/CSRF·세션 비우기/리다이렉트·GET 무삭제 | 충족 | 페이지 테스트가 실제 session/sync와 DB를 거쳐 401/403/302, GET 후 Guest 보존을 확인한다. `app/web.py:129`의 대상 일치 검사로 세션 전환 후 옛 폼은 거부된다(D-14-2 FIXED). |
| Apple revoke 래퍼·저장 토큰/client별 공개 secret 접근자·iOS/웹 테스트 | 충족 | `app/clients/apple.py:52` 이하의 POST 본문·3초 timeout, `apple_revocation_service.py`의 `apple_client_secret` 사용을 확인했다. 실제 계정 연결·암복호화·JWT 생성 후 외부 HTTP만 대역으로 받아 번들 ID/Services ID와 JWT sub를 각각 검사하는 테스트가 통과했다. |
| 실패 시 재시도 행·마이그레이션/단일 head·매일 Beat·7일 초과 폐기/알림 | 충족 | 실패 뒤 INSERT하던 구조가 삭제와 함께 의무를 저장하는 구조로 바뀌었다(D-14-3 FIXED). 정상 성공/실패, 복호화 실패, 재시도 성공/유지, 7일 초과 폐기와 알림, Beat 등록/위임 테스트 및 실제 마이그레이션 왕복 테스트가 통과했다. head는 `94a83f12fddb` 하나다. |
| 성공 리다이렉트 후 localStorage 정리·새 게스트·수동 체크리스트 | 충족 | 실제 `app.js` 실행 테스트에서 옛 토큰 401일 때만 토큰/기록 삭제 및 새 게스트 발급을 확인했다. 200과 네트워크 오류에는 저장소를 보존한다(D-14-1 FIXED). RELEASE §14에 정상/가짜 신호/세션 전환 수동 점검 항목이 있다. |
| 삭제 데이터 목록·방침 파기/권리 링크·ko/en 템플릿·핵심 문구 | 충족 | 양쪽 삭제 템플릿과 방침의 수집 항목 명칭, `#collection`·`#rights` 실재 앵커, 되돌릴 수 없음·스토어 별도 해지 문구를 대조했다. 페이지/법적 문서 테스트가 통과했다. 법적 적정성 보완은 티켓 16 범위다. |
| impeccable 0건·README 설계 판단·Play 삭제 URL | 충족 | ko/en × 안내/확인 4개 렌더 화면에서 직접 detect 0건을 확인했다. README §14에 삭제 커밋과 철회 재시도 판단, RELEASE §14에 Play 삭제 URL이 명시되어 있다. |
| 필요 시 재시도 구현 별도 티켓 분할 | 충족(분할 불필요) | 재시도 테이블·Beat·7일 폐기까지 구현되어 별도 분할하지 않았다. |

### 이전 결함 재검증

#### D-14-1 — FIXED (이전 MAJOR)

- 위치: `web/static/app.js:347`, `web/static/app.js:374`, `web/static/app.js:386`, `web/static/app.js:415`.
- 재현 입력: 유효한 토큰과 보드 기록이 있는 상태에서 삭제 없이 `/?deleted=1` 진입. 기대는 기존 토큰/기록 보존이며, 현재 실제 결과도 보존이다. 서버가 401로 거절한 토큰만 삭제하고 새 게스트를 발급한다. 네트워크 확인 실패는 토큰/기록과 재확인용 쿼리를 모두 보존한다.
- 직접 실행한 `tests/test_web.py -k deleted_signal` 해당 3개가 아래 핵심 테스트 실행에 포함돼 모두 통과했다. 하네스가 실제 app.js 함수를 실행하며 저장소·DOM·fetch만 대역이다. 단순 문자열 존재 검사를 통과 근거로 삼지 않았다.

#### D-14-2 — FIXED (이전 MAJOR)

- 위치: `app/web.py:129`, `app/web.py:135`, `tests/test_account_delete_page.py:268`.
- 재현 입력: A로 세션 동기화 → 삭제 폼/CSRF 수령 → B로 세션 동기화 → A 폼 제출. 기대는 403과 A/B 모두 보존이며 현재 테스트 실제 결과도 동일하다. B로 새 폼을 받은 뒤 제출하면 B만 정상 삭제된다.
- 기존 CSRF와 삭제 대상 id를 함께 발급하고 POST에서 대상 일치를 확인한다. 재렌더하면 CSRF도 새로 발급되어 옛 폼의 토큰이 새 대상에 재사용되지 않는다. 두 회귀 테스트는 실제 Flask·MySQL·Redis·session/sync 경로를 사용하며 삭제 서비스를 mock하지 않는다.

#### D-14-3 — FIXED (이전 MAJOR)

- 위치: `app/services/account_deletion_service.py:57`, `app/services/account_deletion_service.py:65`, `app/services/apple_revocation_service.py:34`.
- 재현 입력: Apple 계정 삭제 시 첫 DB 커밋 이후 커밋 장애를 주입하고 Apple 호출을 실패시킨다. 기대는 Guest 삭제와 재시도 의무 보존이며 현재 실제 결과도 Guest 없음/재시도 1행이다. 커밋 직후 철회 시도에서 프로세스 종료에 해당하는 예외를 주입하고 rollback해도 재시도 1행이 남는다.
- `schedule_revocation`은 행만 추가하고 커밋하지 않는다. 이 행과 계정 삭제가 같은 첫 커밋에 들어가고, 철회 성공 후에만 의무를 삭제한다. `test_the_revocation_duty_is_committed_together_with_the_deletion` 및 `test_a_failed_revoke_survives_a_db_outage_after_the_deletion_commit`이 실제 DB에서 통과했다.

### 직접 실행한 검증

- 기존 `chosung_daily_test_t14`, `chosung_daily_test_t14_migrations`, Redis DB 2를 각각 `TEST_DATABASE_URL`, `TEST_MIGRATION_DATABASE_URL`, `TEST_REDIS_URL`로 지정했다. 모두 접속되어 기본 DB 폴백·새 DB 생성은 없었다. 접속 비밀번호·토큰은 이 리뷰에 적지 않는다.
- 처음 아래 두 묶음을 하나의 pytest 명령으로 실행했으나 진행 중 **exit 143(SIGTERM)**으로 종료됐다. 실패 traceback과 최종 집계는 없었고 종료 원인은 확인되지 않았다. 이 실행은 통과로 계산하지 않았다. 같은 자원에서 두 묶음으로 나누어 한 차례 다시 실행한 결과는 다음과 같다.

```sh
uv run pytest -q tests/test_account_deletion.py tests/test_apple_revocation.py \
  tests/test_account_delete_page.py tests/test_web.py tests/test_celery_wiring.py \
  tests/test_csrf.py
# 73 passed in 37.81s, exit 0

uv run pytest -q tests/test_migrations.py tests/test_legal_pages.py
# 109 passed in 137.06s (0:02:17), exit 0

uv run ruff check .
# All checks passed!, exit 0

FLASK_ENV=testing uv run flask --app wsgi db heads
# 94a83f12fddb (head), 한 줄, exit 0

git diff main...HEAD --check
# 출력 없음, exit 0
```

- 완료된 테스트는 합계 **182 passed**, skip 없이 통과했다. 이번 라운드에서 전체 800개 스위트를 다시 실행했다고 주장하지 않는다.
- impeccable 0.1.14로 현재 템플릿을 메모리에서 ko/en·폼/안내로 렌더하고 로컬 HTTP 서버가 실제 tokens/legal/account CSS를 제공하게 했다. 네 URL 모두 exit 0/출력 없음(0건). 대조군 `design/archive/v2_softdark_home.html`은 7건/exit 2였다. 외부 접속 방지를 위해 메모리 HTML의 CDN 폰트 링크만 제외했으며 저장된 템플릿은 수정하지 않았다.

### 범위·보안 및 참고

- README는 자기 API/Beat 행과 `### 14.` 절을 추가했고 RELEASE도 `### 14.`만 추가했다. `.env.example`·스펙을 수정하지 않았고 다른 티켓 절을 덮어쓰지 않았다. 방침 템플릿 변경은 삭제 페이지가 가리킬 앵커 추가다. 티켓 범위 밖 기능 변경은 발견하지 못했다.
- Bearer 인증, 유효 Guest 세션 조회, 삭제 대상 결합, 일회용 CSRF, 암호문 저장, 외부 호출 timeout과 알림의 토큰 미포함을 확인했다. 신규 diff에서 실제 운영 시크릿을 발견하지 못했다. 구현 증거의 로컬 개발용 접속 예시와 테스트 더미는 운영 시크릿으로 분류하지 않았고 이 문서로 복사하지 않았다.
- Redis ZREM은 DB 커밋 뒤 best-effort이고 재시도가 없다. 따라서 DB와 Redis가 원자적인 한 트랜잭션이라는 의미는 아니며, Redis 장애 시 당일 익명 순위가 남는 라운드 1의 제한은 그대로다.
- 실제 Apple 철회 수락과 브라우저 전체 클릭 E2E는 실행하지 않았다. 테스트는 외부 HTTP/운영자 알림을 대역 처리했고, JS는 Node vm으로 검증했다. 법적 문구 적정성은 티켓 16의 후속 범위다.
- 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다. 이번 리뷰의 변경 파일은 `review/impl-review-14.md` 하나다.

판정: PASS
