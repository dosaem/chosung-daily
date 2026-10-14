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
