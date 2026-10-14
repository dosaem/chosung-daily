# 티켓 13 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14
- 기준: 로컬 `main` `bf287f6735b07eb0f8a596195bf368ebe31ccd1a`, 구현 HEAD `0c0071ee3e75be2453c624f7ed744925dcbb8aef`.
- `git log main..HEAD`: `c30aa2a` 구현, `0c0071e` 구현 증거 문서. `git diff main...HEAD`의 19개 파일을 검토했다. `origin/main`은 사용하지 않았다.
- 기준 문서: 티켓 13, 스펙 §A.8·A.12·A.17·Testing 및 미정 1·15·18·19, 정본 ADR 0003, CONTEXT.md. UI 변경이 없어 디자인 검토는 해당 없다.
- 구현 증거 문서는 참고만 하고 아래 명령과 재현을 직접 실행했다. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

## 체크박스별 확인

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 순수 권한 함수와 active 24h / grace 3일째 / hold / revoked 테스트 | 충족 | `app/services/entitlement.py:is_entitled`가 시계를 인자로 받고 표대로 판정한다. `tests/test_entitlement.py`의 27개 케이스가 전체 스위트에서 통과했다. |
| `/me/stats` entitlement, 1h 경계 포함 재조회, 3초 타임아웃, 실패 저장값 유지·카운터, 만료 ±24h 5분, next_check_at | 미충족 | 응답 필드·순차 TTL·실패 처리·5분 간격·`last_verified_at + 1h`는 구현되어 있고 테스트가 통과했다. 그러나 재조회가 겹치면 이미 확인한 철회를 오래된 응답으로 덮어 권한을 다시 주므로 “철회 확인 응답부터 권한 없음”을 지키지 못한다(D-13-1). 3초는 기존 Apple requests 및 Play httplib2 전송 설정을 실제 코드에서 확인했다. |
| 만료 20일 전 revoked, 정확히 1h / 59분, 만료 2일 뒤 verify 재전송, 1h 상한 테스트 | 충족 | `tests/test_subscription_recheck.py`의 해당 케이스가 실제 서비스·DB·API를 거쳐 통과한다. 정확한 시간 경계는 순수 함수 테스트에서 고정 시각으로 추가 확인한다. 2일 뒤 복구는 실제 `verify_receipt` 서비스 호출로 확인한다. |
| Beat 매일 만료 3일 이내 active/grace/hold 재조회, 직접 호출·배선, 연속 실패 3회 알림 | 미충족 | 대상 쿼리, 매일 03:30 스케줄, 서비스 위임, 실패 카운터·운영자 알림 테스트는 통과한다. Beat와 요청 경로가 같은 무조건 갱신 함수를 사용하므로 병행 실행 시 D-13-1이 적용된다. |
| 정본 ADR 0003을 1h TTL + ±24h 5분으로 갱신 | 충족 | `docs/adr/0003-subscription-entitlement-on-server.md` 재조회·Consequences 문구와 스펙 미정 항목의 티켓 13 추가 기록을 확인했다. |
| README 설계 판단에 상태 표·유예·TTL·웹훅 미도입 근거 | 충족 | `README.md`의 `### 13.`에 모든 내용이 있다. 별도로 공용 API 표 수정 방식은 규칙 위반이다(D-13-2). |

## 실행 검증

기존 전용 MySQL DB `chosung_daily_test_t13`, 마이그레이션 DB `chosung_daily_test_t13_migrations`, 로컬 Redis DB 15를 재사용했다. `TEST_DATABASE_URL`, `TEST_MIGRATION_DATABASE_URL`, `TEST_REDIS_URL`을 각각 지정했으며 접속 성공으로 기본 DB 폴백이나 새 DB 생성은 하지 않았다. 접속 자격 값은 이 문서에 기록하지 않는다.

| 명령 | 직접 실행 결과 |
|---|---|
| 위 테스트 환경을 지정한 `uv run pytest -q` | **746 passed in 486.76s (0:08:06)**, 종료 코드 0. 실패·재실행 없음. |
| `uv run ruff check .` | **All checks passed!**, 종료 코드 0. |
| `FLASK_APP=wsgi.py uv run flask db heads` | **d7a1f0ca0a29 (head)** 한 줄, 종료 코드 0. |
| `git diff --check main...HEAD` | 출력 없음, 종료 코드 0. |
| 전용 테스트 DB에서 `uv run python -`으로 아래 응답 역전 재현 | 최신 철회가 오래된 active로 덮이는 것을 확인, 종료 코드 0. |

마이그레이션 테스트는 실제 upgrade/downgrade 왕복과 기존 구독 행의 실패 카운터 0 초기화를 포함한다. 재조회 통합 테스트는 스토어 조회 경계를 대체하지만 TTL 판정·정규화·DB 저장·권한 응답은 실제 코드로 검증한다. 순차 테스트는 유효하나, 동시 요청의 응답 역전 검증은 없었다. 외부 Apple·Google·Slack 호출이나 프로덕션 접근 없이 실행했다.

## 결함

### D-13-1 — MAJOR — 늦은 재조회 응답이 확인된 철회를 덮어 권한을 복구함

- 위치: `app/services/subscription_recheck.py:101` (상태·만료일·확인 시각을 조건 없이 갱신하고 106행에서 커밋), 호출부 `app/services/subscription_recheck.py:60` 및 `:120`.
- 근거: 스펙 §A.8과 티켓은 확인된 철회에는 유예를 주지 않고 그 응답부터 권한을 제거하도록 한다. 현재 구현은 조회 중 다른 요청이 구독을 갱신했는지 확인하지 않는다. 행 잠금 또는 버전/조회 순서 검증도 없다. Beat와 `/me/stats`뿐 아니라 두 `/me/stats` 요청도 겹칠 수 있다.
- 재현 입력과 순서(실제 MySQL의 독립 Flask app context 두 개로 실행):
  1. `status=hold`, `expires_at=now+2일`, `last_verified_at=now-2시간`인 Apple 구독을 저장한다.
  2. 세션 A에서 `entitlement_for(guest)`를 호출한다. `fetch_subscription_status`는 먼저 관측된 Apple status 1(active) 응답을 반환 직전 보류한다.
  3. A의 스토어 경계 안에서 새 app context(독립 DB 세션 B)를 열고 같은 구독을 읽는다. B의 스토어 응답을 status 5(revoked)로 두고 실제 `recheck(row)`를 실행·커밋한다. 두 응답 모두 만료일은 2일 뒤다.
  4. B의 권한이 false임을 확인한 후 A의 보류된 status 1 응답을 반환한다. A는 실제 정규화·저장·권한 조립을 완료한다.
  5. DB 행을 expire/reload하여 최종 상태를 읽는다. 테스트 후 전용 DB의 테스트 테이블을 정리했다.
- 기대: B가 저장한 최신 철회가 유지되어 최종 `status=revoked`, `entitlement.active=false`. 오래된 조회 결과로 확인된 철회를 되돌리지 않아야 한다.
- 실제 출력:

  ```text
  B newer response: revoked False
  A delayed response: active True
  Final stored state: active
  ```

- 영향: 환불된 구독의 광고 제거 권한이 다시 살아난다. A는 `last_verified_at`도 현재로 갱신하므로 이 재현처럼 만료가 ±24h 밖이면 다음 1시간 TTL까지 잘못된 권한을 유지한다. 기존의 단일 요청 revoked 테스트와 순차 호출 상한 테스트는 이 경우를 잡지 못한다.

### D-13-2 — MINOR — 공유 README API 표의 기존 행을 직접 수정함

- 위치: `README.md:87`.
- 근거: 티켓 공통 규칙은 README API 표를 포함한 공유 절에 자기 번호 소제목/자기 행만 **절 끝에 덧붙이도록** 명시한다. 이번 변경은 기존 `/api/v1/me/stats` 공용 행을 삭제·치환했다.
- 재현 명령: `git diff main...HEAD -- README.md`.
- 기대: 기존 API 행을 유지하고 티켓 13의 추가 행을 해당 절 끝에 넣는 append-only 변경.
- 실제: `@@ -84,7 +84,7 @@`에서 기존 `/api/v1/me/stats` 행이 `-`로 제거되고 확장된 행이 `+`로 대체된다. 병렬 티켓이 같은 기존 행을 다룰 때 피하기로 한 충돌을 다시 만든다. 기능 동작 자체에는 영향이 없어 MINOR다.

## 기타 검토

- `/me/stats`의 기존 Bearer `with_guest` 인증은 유지되고 재조회 대상도 해당 게스트로 제한된다. 신규 입력·인증 우회·CSRF 경로 추가는 없다.
- 새 운영자 알림에 store key를 넣지 않는 것을 코드와 테스트에서 확인했다. 변경분에서 운영용 키·토큰·비밀번호는 발견하지 못했다. 증거 문서의 로컬 DB URL은 기존 예제 자격 값을 포함하므로 여기에는 복사하지 않았다.
- `.env.example`, `docs/RELEASE.md` 변경은 없다. 스펙은 미정 항목 끝에 자기 티켓 기록만 추가하고 README 설계 판단도 `### 13.`으로 추가했다. 정본 ADR 변경은 티켓이 명시적으로 요구한 범위다.
- 취향·스타일 관련 제안은 결함에 포함하지 않았다.

결함 수: BLOCKER 0, MAJOR 1, MINOR 1. 기존 테스트와 ruff 통과와 별개로, 직접 재현한 권한 상태 역전 때문에 승인할 수 없다.

판정: FAIL

## 라운드 2

- 검토일: 2026-10-14. 구현 HEAD: `292eacfa3ca5ab1b40e51a177989603af82fb59a`.
- 로컬 `main` 기준 `git diff main...HEAD` 20개 파일과 `git log main..HEAD`를 직접 확인했다. 커밋은 `dc80f1b`, `f7aae0f`, `fd2e07b`, `efd2d5e`, `292eacf`다. 검토 중 main이 `1e764da`에서 `b8f63cc`로 이동했으나 merge-base는 `1e764da6d8ec4710d4ebf945249a6e264bd75f84`로 동일하고 diff도 동일함을 마지막에 재확인했다. `origin/main`은 사용하지 않았다.
- 티켓 13의 모든 체크박스, 스펙 §A.8·A.12·Testing·미정 1/15/18/19, 정본 ADR 0003, CONTEXT.md, 이전 리뷰 및 구현 증거의 수정 라운드를 대조했다. UI 변경은 없어 디자인 검토는 해당 없다.
- 코드·테스트·설정·`.scratch/`는 수정하지 않았다. 아래 테스트 및 재현은 기존 로컬 테스트 자원만 사용했고 외부 스토어·Slack·프로덕션에 접근하지 않았다.

### 체크박스별 확인

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 순수 권한 함수 및 active 24h / grace 3일째 / hold / revoked 테스트 | 충족 | `app/services/entitlement.py:41`의 `is_entitled`는 상태·시각만으로 판정한다. active만 24h, grace는 스토어 유예 종료까지, hold/revoked/expired/replaced는 없음이다. `tests/test_entitlement.py`의 경계·상태 테스트를 포함한 전체 테스트가 통과했다. |
| `/me/stats` entitlement, 1h 경계 포함 재조회, 3초 타임아웃, 실패 저장값 유지·카운터, 만료 ±24h 5분, next_check_at | 미충족 | 응답 필드·TTL·5분 간격·실패 처리·`last_verified_at + 1h`는 코드와 테스트로 확인했다. Apple requests와 Play httplib2의 3초 전송 설정도 확인했다. 그러나 스토어가 철회를 반환한 요청에서조차 active를 응답하는 동시성 결함 D-13-3이 있다. |
| 만료 20일 전 revoked / 정확히 1h / 59분 / 만료 2일 뒤 verify 재전송 / 1h 상한 테스트 | 충족 | `tests/test_subscription_recheck.py:205`, `:223`, `:235`, `:509`가 실제 서비스·DB·API 또는 verify 서비스로 검증한다. 정확한 시간 경계는 `tests/test_entitlement.py:132`와 `:145`에서 고정 시각으로 검사한다. 전체 스위트 통과. |
| Beat 매일 만료 3일 이내 active/grace/hold 재조회, 서비스·배선, 연속 실패 3회 알림 | 미충족 | 대상 쿼리, 03:30 매일 스케줄, 실제 서비스 호출 및 위임 테스트, 실패 3회 알림과 성공 리셋은 확인했다. 다만 Beat도 같은 `recheck`를 사용하여 병행 요청의 active 저장 뒤 받은 철회를 폐기하는 D-13-3이 적용된다. |
| 정본 ADR 0003 갱신 | 충족 | `docs/adr/0003-subscription-entitlement-on-server.md`에 1h TTL, ±24h 5분, 경계 포함, next_check_at을 명시했다. 스펙 미정 항목 끝의 티켓 13 기록도 확인했다. |
| README 상태 표·유예·TTL·웹훅 미도입 근거 | 충족 | `README.md`의 `### 13.`에 모두 있다. API 표 변경은 기존 행을 보존하고 티켓 13 행을 끝에 추가하여 D-13-2도 수정됐다. |

### 직접 실행한 검증

`TEST_DATABASE_URL`은 기존 `chosung_daily_test_t13`, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t13_migrations`, `TEST_REDIS_URL`은 로컬 Redis DB 15로 지정했다. 접속 성공으로 기본 DB 폴백이나 새 DB 생성은 없었다. URL의 자격 값은 기록하지 않는다.

| 명령 | 결과 |
|---|---|
| 위 환경의 `uv run pytest -q` | **807 passed in 809.73s (0:13:29)**, 종료 코드 0. 간헐 실패 및 재실행 없음. |
| `uv run ruff check .` | **All checks passed!**, 종료 코드 0. |
| `FLASK_APP=wsgi.py uv run flask db heads` | **d7a1f0ca0a29 (head)** 한 줄, 종료 코드 0. |
| `git diff --check main...HEAD` | 출력 없음, 종료 코드 0. |
| 위 전용 DB·Redis 환경의 `uv run python -` 동시성 재현 | 실제 MySQL 독립 app context 두 개와 실제 `/api/v1/me/stats`를 사용하여 아래 두 순서 확인, 종료 코드 0. |

전체 테스트에는 실패 카운터 마이그레이션 upgrade/downgrade와 기존 행 0 초기화가 포함된다. 스토어 조회와 운영자 알림 경계만 대체하는 테스트는 정규화·저장·TTL·응답을 실제로 검증한다. 새 동시성 테스트 두 개도 독립 DB 세션을 사용하므로 무의미한 mock 테스트는 아니다. 다만 철회가 먼저 저장되는 순서만 다루어 D-13-3을 놓친다.

### 이전 결함 판정

| ID | 이전 심각도 | 판정 | 근거 |
|---|---|---|---|
| D-13-1 | MAJOR | FIXED | `app/services/subscription_recheck.py:116` 및 `:173`, `app/repositories/subscription_repository.py:48`의 잠금·최신 행 재조회로, 먼저 저장된 revoked를 늦은 active가 덮지 않는다. 기존 재현 순서를 직접 실행하여 DB와 두 API 응답 모두 revoked/false임을 확인했다. |
| D-13-2 | MINOR | FIXED | `git diff main...HEAD -- README.md`에서 기존 `/api/v1/me/stats` 행은 삭제·치환되지 않으며, `README.md:104`에 티켓 13 행만 API 표 끝에 추가된다. |

### 새 결함

#### D-13-3 — MAJOR — 먼저 커밋된 active 때문에 뒤에 확인된 철회 응답을 버림

- 위치: `app/services/subscription_recheck.py:116`(성공 응답도 무조건 폐기), `:173`(조회 전 값과 현재 행이 다르기만 하면 superseded), 관련 테스트 `tests/test_subscription_recheck.py:565`.
- 원인: DB가 조회 시작 이후 바뀌었다는 사실을, 현재 받은 스토어 응답이 더 오래됐다는 증거로 취급한다. 스토어의 최신 상태가 revoked여도 다른 요청이 active를 먼저 커밋하면 `_superseded`가 True여서 철회 저장을 건너뛰고 active를 응답한다. 행 잠금은 쓰기를 직렬화하지만 이 응답 선택 규칙을 정당화하지 않는다.
- 재현 입력/순서: 전체 스위트 종료 후 동일 전용 DB에서 `uv run python -`으로 실행했다. 스토어 경계 `app_store.fetch_subscription_status`만 `unittest.mock.patch.object`로 교체했다.
  1. 게스트와 Apple 구독을 생성한다. `status=active`, `expires_at=now+20일`, `last_verified_at=now-2시간`, `recheck_failures=0`으로 저장하고 커밋한다. 두 스토어 응답은 같은 구독 식별자와 같은 미래 만료일을 사용한다.
  2. 세션 A에서 Bearer 인증을 붙여 `client.get('/api/v1/me/stats', headers=headers)`를 호출한다. A의 스토어 응답을 반환하기 전에 독립 `with app.app_context()` 세션 B를 연다.
  3. B는 `db.session.get(Subscription, row_id)` 후 실제 `subscription_recheck.recheck(row)`를 호출한다. B의 스토어 응답은 Apple status 1(active)이며 정상 커밋한다.
  4. B 종료 후 A의 스토어 응답을 Apple status 5(revoked)로 반환한다. 실제 정규화·잠금·저장 판단·API 직렬화가 실행된다. 이 순서는 겹친 요청 중 active 조회가 먼저 처리·커밋되고, 나머지 조회가 그 뒤 철회를 확인하는 경우다.
  5. A의 응답과 expire/reload한 DB를 읽고, 같은 게스트의 `/me/stats`를 즉시 한 번 더 호출하여 스토어 호출 수를 확인한다.
- 기대: 철회를 실제 확인한 A의 응답부터 `entitlement.active=false`, 저장 상태 revoked. 아직 스토어에 묻지 못한 시간에 허용되는 1h 지연을, 이미 성공 응답으로 받은 철회를 무시하는 데 적용해서는 안 된다.
- 실제: A의 스토어 상태는 5지만 A 응답과 DB가 active이고, 후속 요청도 active이며 재조회하지 않는다. B가 `last_verified_at`을 갱신했으므로 만료 ±24h 밖인 이 입력에서는 다음 1h TTL까지 철회를 반영하지 않는다.

```text
original B committed: revoked
original A provider status: 1
original A response: revoked False
original Final DB: revoked
original Next response: revoked False store calls: 2
reverse B committed: active
reverse A provider status: 5
reverse A response: active True
reverse Final DB: active
reverse Next response: active True store calls: 2
```

`original`은 D-13-1 수정 확인을 위한 대조군으로 3~4단계의 status를 서로 바꾼 것이다. `reverse`가 이번 결함이며, store calls 2는 A/B 각 한 번뿐이고 후속 요청은 재조회하지 않았음을 뜻한다. 재현 종료 후 테스트 테이블과 Redis DB 15를 정리했다.

구현 증거 `review/impl-evidence-13.md:310`은 이 순서를 “의도” 및 허용된 폴링 지연이라고 설명한다. 그러나 티켓과 스펙 §A.8은 **철회가 확인되면 그 응답부터 권한 없음**을 요구하며, 실패 시 저장값 유지와 성공한 revoked 응답 폐기는 다르다. 따라서 문서의 주장을 승인 근거로 삼을 수 없다. 기존에 저장된 철회를 덮는 D-13-1과 구분하여 새 ID로 기록한다.

### 기타 검토 및 참고

- 기존 Bearer 인증과 게스트별 구독 조회 범위는 유지된다. 새 인증·CSRF 입력 경로 추가는 없다. 운영자 알림에 store key를 넣지 않는 것을 코드와 테스트에서 확인했다.
- 변경분에서 실제 운영 시크릿이 추가된 증거는 발견하지 못했다. 구현 증거에는 기존 예제와 같은 로컬 테스트 DB 자격 값이 있으나 운영용 시크릿으로 확인된 값은 아니다. 이 리뷰에는 자격 값을 복사하지 않았다.
- README 공유 API 표, 설계 판단, 스펙 미정 항목은 티켓 13의 행/절을 추가하는 방식이다. `.env.example`과 `docs/RELEASE.md` 변경은 없다. ADR 변경은 티켓의 명시 요구다. 티켓 범위 밖 기능 변경이나 추가 데이터 손상 결함은 확인하지 못했다.
- 스타일·취향 제안은 결함에 포함하지 않았다. 실서비스 스토어 통신은 수행하지 않았으며, 3초 설정은 코드·기존 래퍼 테스트 범위에서 확인했다.

현재 미해결 결함: BLOCKER 0, MAJOR 1(D-13-3), MINOR 0. 이전 D-13-1과 D-13-2는 FIXED이며 REPEAT는 없다. 전체 테스트 통과와 별개로 직접 재현한 철회 응답 폐기 때문에 승인할 수 없다.

판정: FAIL
