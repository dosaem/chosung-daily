# 티켓 12 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14. 구현 HEAD: `cdd2622`.
- 기준: 로컬 `main` (`21856d8` 확인), `git diff main...HEAD`, `git log main..HEAD`; merge-base `72a2a3c`. origin/main 사용 안 함.
- 대상: 티켓 12, 스펙 §A.8·§A'·미정 14, ADR 0003, CONTEXT, 구현 증거 및 변경 파일. UI 변경 없음.
- 코드는 수정하지 않았다. 실제 외부 스토어·NAS·프로덕션 호출 없이 로컬 테스트와 설치된 SDK로 재현했다.

## 체크박스별 판정

| 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|
| Subscription 필드·6종 status·unique(store, store_key)·마이그레이션·단일 head | 충족 | 모델과 `a5bab2f58a7b` migration 일치, 실제 MySQL 중복·저장 테스트, `flask db heads` 한 줄 |
| 공식 Apple/Google 래퍼·JWS 검증·환경 선택·Sandbox 1회 폴백·3초 | 미충족 | 공식 SDK 의존성 및 실제 요청 timeout=3 배선은 있으나 Production 검증기 생성 자체가 실패(D-12-1). 폴백 테스트는 검증기를 전부 대체함 |
| 순수 상태 매핑 2개·grace 시각·pending 무행·미정 14 기록 | 충족 | 순수 함수와 fixture별 매핑 확인. Google revoked는 미정 14에 명시된 변경 계약(명시적 revoked 플래그만 사용, v2 EXPIRED는 expired) 기준으로 평가 |
| Bearer verify·상품/번들/패키지 확인·멱등 upsert·복원 재지정·권한·400/503 | 미충족 | 인증·상품·복원·DB 멱등은 테스트로 확인. Apple 오류는 500(D-12-2), 갱신 만료일은 과거 값 저장(D-12-3), 잘못된 JSON JWS도 500(D-12-4) |
| 지정 fixture 테스트 5종 | 충족 | 중복·동시 전달, linkedPurchaseToken 교체, Sandbox 폴백, 다른 게스트 복원, 상품 불일치 테스트 존재 및 실행. 다만 실제 SDK 경계의 검증 공백은 D-12-1/2/3에 포함 |
| 임시 active/grace 권한 함수; 판정표·TTL은 13으로 분리 | 충족 | `build_entitlement`는 상태만 판단하고 시계를 읽지 않음. 시간 판정·Beat·stats 미구현을 이 티켓 결함으로 세지 않음 |
| .env.example 스토어 설정·README 설계 판단 | 미충족 | 요청한 설정과 공식 라이브러리/RevenueCat 미사용/store_key 멱등 설명은 존재. 실제 Production에 필수인 appAppleId 설정 경로 누락(D-12-1) |

## 직접 실행한 검증

- `TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL`을 구현 증거의 로컬 접속 형식으로 지정했다. DB `chosung_daily_test_t12`, 기존 migration DB `chosung_daily_test_t12_migrations`, Redis DB 14를 재사용했다. 새 DB 생성·기본 DB 폴백 없음. 접속 비밀번호는 이 문서에 기록하지 않는다.
- 전체 테스트: `uv run pytest -q` — 실행 결과는 아래 최종 검증에 기록.
- `uv run ruff check .` → `All checks passed!` (exit 0).
- `FLASK_APP=wsgi.py uv run flask db heads` → `a5bab2f58a7b (head)` 한 줄 (exit 0).
- 별도 `uv run python - <<'PY'` 인라인 재현으로 아래 4건 확인. 파일에 테스트를 추가하거나 기존 테스트를 수정하지 않았다.

## 결함

### D-12-1 — BLOCKER — Production Apple 검증기 생성 불가

- 위치: `app/clients/app_store.py:182`, `app/config.py:40`, `tests/test_store_clients.py:107`.
- 재현: 아래 코드는 네트워크·실제 키 없이 설치된 공식 SDK 생성자를 그대로 실행한다.

```python
from app.clients import app_store as a
from app.models import SubscriptionEnvironment as E
c = a._Credentials('example.bundle', '', '', '', [])
a._verifier(c, E.PRODUCTION)
```

- 기대: 설정된 앱 식별자로 Production 검증기를 생성하고 JWS 검증 단계로 진행.
- 실제: `ValueError: appAppleId is required when the environment is Production`. 설치된 `app-store-server-library` 3.1.2의 `SignedDataVerifier.__init__`가 app_apple_id 없는 Production을 거부한다. 래퍼는 이 인자를 전달하지 않고 설정 항목도 없다. 정상 인증서·키를 넣어도 이 조건은 동일하다.
- 영향: Production 영수증이 전부 검증 전에 실패하며 Production→Sandbox 폴백에도 도달하지 못한다. `_verifier` 전체를 fake로 바꾼 기존 테스트는 이 실패를 숨긴다.

### D-12-2 — MAJOR — Apple API 실패/타임아웃이 계약된 오류로 변환되지 않음

- 위치: `app/clients/app_store.py:112`, `app/clients/app_store.py:205`, `tests/test_store_clients.py:143`.
- 재현: `_credentials`는 합성 설정, `_environment_of`는 Sandbox, `_verify_transaction`은 `{'originalTransactionId': 'synthetic'}`로 대체하고 `_status_from`에서 각각 `requests.Timeout()`, `APIException(503)`, `APIException(404, 4040010)`을 발생시킨다. Flask testing 앱에서 `PROPAGATE_EXCEPTIONS=False`, 인증 조회만 합성 guest로 대체한 후 `POST /api/v1/subscriptions/verify`에 `{store:'apple', receipt:'synthetic'}`를 보낸다. 실제 래퍼·서비스·오류 핸들러를 통과시켰다.
- 기대: 타임아웃/503 → HTTP 503 `STORE_UNAVAILABLE`; Sandbox에서도 존재하지 않는 거래 → HTTP 400 `RECEIPT_INVALID`.
- 실제 출력: 세 경우 모두 `500 INTERNAL_ERROR`. `_fetch_status`는 폴백 대상 외 APIException을 재던지고 requests 예외는 잡지 않는다. 상위에도 변환이 없다.
- 테스트 공백: 래퍼 테스트는 오히려 APIException 전파를 기대한다. endpoint outage 테스트는 이미 변환된 `StoreUnavailableError`를 주입해서 실제 변환 누락을 검증하지 않는다.

### D-12-3 — MAJOR — 최신 상태를 조회하고도 과거 영수증 만료일을 저장

- 위치: `app/clients/app_store.py:112`, `app/clients/app_store.py:120`, `app/clients/app_store.py:236`.
- 재현 입력: 제출 JWS의 거래는 originalTransactionId가 동일하고 expiresDate=1000인 과거 거래로 둔다. 상태 API 응답 `lastTransactions` 항목에는 `rawStatus=1`, 같은 originalTransactionId, 갱신된 거래의 `signedTransactionInfo='latest-transaction'`, `signedRenewalInfo='renewal'`을 둔다. `_TimeoutAppStoreServerAPIClient`만 합성 응답으로 대체하고 renewal 검증기는 SDK `JWSRenewalInfoDecodedPayload`를 반환한다. `fetch_subscription('old-receipt')`를 실행한다.
- 기대: 상태 API가 반환한 최신 signedTransactionInfo를 검증·디코딩하고 최신 만료일을 반환/저장.
- 실제 직접 관측: `result.transaction['expiresDate'] == 1000`, transaction 검증 호출 1회(제출 영수증만). `_status_from`은 최신 signedTransactionInfo를 전혀 읽지 않고 상태와 renewal만 반환한다. 이어지는 `apple_subscription_status`와 `_update`는 이 과거 expiresDate를 DB에 저장한다.
- 영향: 복원/재전송에서 최신 만료일이 과거로 되돌아갈 수 있고 entitlement.until도 틀린다. 이후 티켓 13의 시간 판정이 정상이어도 잘못된 저장값 때문에 유효 구독을 거절할 수 있다. 기존 fixture 테스트는 제출 거래와 조회 거래를 구분하지 않는다.

### D-12-4 — MINOR — JSON 객체가 아닌 JWS payload는 400 대신 500

- 위치: `app/clients/app_store.py:170`, `app/clients/app_store.py:174`.
- 재현: 설정된 Apple 경로에서 `{store:'apple', receipt:'header.W10.signature'}` POST (payload는 `[]`의 base64url). `header.bnVsbA.signature`(null)도 동일. 실제 키/네트워크 없이 `_credentials`만 합성 설정으로 대체해 확인했다.
- 기대: 잘못된 영수증이므로 400 `RECEIPT_INVALID`.
- 실제: `_environment_of`에서 `AttributeError`; HTTP 응답은 `500 INTERNAL_ERROR`. JSON 디코딩 후 객체 여부를 확인하지 않고 `.get`을 호출한다.

## 범위·보안·참고

- Bearer 인증은 기존 with_guest를 사용한다. 쿠키 인증 요청 경로가 아니므로 별도 CSRF 누락은 보고하지 않는다. Google은 configured packageName을 실제 API 요청에 넣는다.
- 공유 파일: README API 행과 `### 12.`, .env.example `[12]`, RELEASE `### 12.`만 추가했고 스펙은 티켓이 명시적으로 확정하도록 지시한 미정 14만 수정했다. 다른 티켓의 소제목/행 침범 없음.
- 변경 파일에서 실제 외부 서비스 키·토큰·비밀번호 노출은 발견하지 않았다. 증거의 로컬 테스트 DB 접속 문자열은 개발용 기본값이며 이 리뷰에는 복사하지 않았다. 테스트의 합성 키/영수증은 실제 자격증명이 아니다.
- 취향·스타일 결함은 올리지 않았다. Google 철회 라벨의 미정 14 합의, 티켓 13 책임인 시간 판정은 결함에 포함하지 않았다.

## 최종 검증

- 전체 최초 실행: `247 passed, 7 errors in 204.94s` (exit 1). 7건 모두 `tests/conftest.py:17`의 `db.create_all()` 연결 단계에서 MySQL `(1040, 'Too many connections')`; 서비스 assertion 실패가 아니다. 다른 worktree 테스트 프로세스가 병행 실행 중임을 확인했다.
- 같은 전용 DB/Redis 환경에서 실패분만 `uv run pytest -q --lf --tb=short`로 한 번 재실행: `7 passed in 10.87s` (exit 0). 대상은 puzzle_maintenance 3건 및 subscription_verify의 인증·입력·Google 구매/해지 4건이다. 따라서 총 254개 각각의 통과는 관측했지만, 전체 한 번 실행의 무오류 통과로 표현하지 않는다.
- 마이그레이션 왕복 테스트와 티켓 12의 나머지 fixture/동시성 테스트는 최초 실행에서 통과했다. 전용 DB는 접속 가능했으며 간헐 연결 한도 문제였으므로 기본 DB로 바꾸지 않았다.
- 결함 합계: BLOCKER 1, MAJOR 2, MINOR 1. 위 결함은 DB 연결 오류와 독립적으로 재현했다.

판정: FAIL
