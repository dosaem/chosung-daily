# 티켓 12 구현 증거 — 구독 DB·스토어 검증 엔드포인트·상태 정규화

- 날짜: 2026-10-14
- 브랜치: `dosaem/t12-subscription-db-verify` (로컬 `main` = `72a2a3c` 위로 rebase 완료)
- 환경: macOS (Darwin 25.3.0), uv / Python 3.12.14, MySQL 8 · Redis 7 (로컬 compose)
- 전용 테스트 자원: DB `chosung_daily_test_t12`, 마이그레이션 DB
  `chosung_daily_test_t12_migrations`, Redis DB 14
  (`TEST_DATABASE_URL` / `TEST_MIGRATION_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 —
  공용 테스트 DB·Redis 와 다른 워커의 DB 는 건드리지 않았다)
- 외부 호출 0건: Apple·Google·Slack 어디에도 실제 요청을 보내지 않았다. 스토어
  호출 지점만 monkeypatch 로 바꿔 끼웠고 값은 실제 응답 모양 fixture 다.
- 키·토큰·비밀번호를 파일·로그·이 문서에 적지 않았다(설정 **이름**만). `.env`,
  `.env.prod*` 실제 값은 열지도 고치지도 않았다.
- UI 없음 — API 전용 티켓이라 `impeccable detect`(웹)/`audit.native`(Flutter)는
  해당 없다. 템플릿(`web/`)·Flutter(`mobile/`)를 건드리지 않았다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `app/models/enums.py` | `SubscriptionStore`(apple/google)·`SubscriptionEnvironment`(Sandbox/Production)·`SubscriptionStatus`(active/grace/hold/expired/revoked/replaced) 추가 |
| `app/models/subscription.py` | 신설. `Subscription` — `unique(store, store_key)`, `store_key` String(512) |
| `app/models/__init__.py` | 새 모델·enum export |
| `migrations/versions/a5bab2f58a7b_add_subscription_table.py` | 신설. `subscription` 테이블. `down_revision = 4e72a4045fbc`(티켓 02) |
| `app/services/subscription_status.py` | 신설. **순수 함수 2개** `apple_subscription_status` / `google_subscription_status` + `NormalizedSubscription` |
| `app/clients/app_store.py` | 신설. 외부 호출 함수 하나 `fetch_subscription`. JWS 검증(공식 라이브러리), `environment` 로 엔드포인트 선택, 4040010/4040005 → Sandbox 1회 폴백, 타임아웃 3초 |
| `app/clients/play.py` | 신설. 외부 호출 함수 하나 `fetch_subscription`(`purchases.subscriptionsv2.get`), 타임아웃 3초 |
| `app/services/subscription_service.py` | 신설. `verify_receipt` — 상품·번들 확인 → 검증 → `(store, store_key)` upsert → 권한 |
| `app/services/entitlement.py` | 신설. `build_entitlement`(순수) — **티켓 12 임시 판정**: `active|grace` 만 권한. 티켓 13 이 교체 |
| `app/repositories/subscription_repository.py` | 신설. `find_by_store_key` / `find_by_guest` |
| `app/schemas/subscription.py` | 신설. `VerifyReceiptRequest`, `EntitlementResponse` |
| `app/api/subscriptions.py`, `app/api/__init__.py` | `POST /api/v1/subscriptions/verify` (Bearer) 등록 |
| `app/errors.py` | `ReceiptInvalidError`(400 `RECEIPT_INVALID`), `StoreUnavailableError`(503 `STORE_UNAVAILABLE`) |
| `app/config.py` | `SUBSCRIPTION_PRODUCT_ID`, `APP_STORE_*` 5개, `PLAY_*` 2개 |
| `pyproject.toml` / `uv.lock` | `app-store-server-library>=1.5.0`(설치 3.1.2), `google-api-python-client>=2.0.0` |
| `tests/fixtures/store/` | 신설. 실제 응답 모양 fixture 19개 + `README.md` |
| `tests/test_subscription_status.py` | 신설. 순수 함수 21개 |
| `tests/test_store_clients.py` | 신설. 래퍼 경계 18개 |
| `tests/test_subscription_verify.py` | 신설. 엔드포인트·저장 29개 (스레드 동시성 1개 포함) |
| `.env.example` | `# [12]` 절 — App Store Server API 키·Play 서비스 계정 설정 |
| `README.md` | API 표에 `/subscriptions/verify` 행, "설계 판단" 에 `### 12.` |
| `docs/RELEASE.md` | `### 12. 구독 검증 — 배포 전 준비물` |
| `.scratch/store-launch/spec.md` | 미정 항목 **14** 를 fixture 확정 결과로 갱신(티켓이 지시한 항목) |

## 2. 실행한 명령과 출력

모두 아래 환경변수를 붙여 돌렸다(이하 `<ENV>` 로 줄임):

```
TEST_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t12?charset=utf8mb4
TEST_REDIS_URL=redis://localhost:6379/14
TEST_MIGRATION_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t12_migrations?charset=utf8mb4
```

### 2.1 전체 테스트 스위트 (rebase 후)

```
$ <ENV> uv run pytest -q
........................................................................ [ 28%]
........................................................................ [ 56%]
........................................................................ [ 85%]
......................................                                   [100%]
254 passed in 131.20s (0:02:11)
```

rebase 전 같은 명령은 `214 passed in 116.82s` 였다 — 차이 40개는 로컬 `main` 이
가져온 티켓 19·21 의 테스트다. 실패·skip·xfail 0건.

### 2.2 ruff (rebase 후)

```
$ uv run ruff check .
All checks passed!
```

### 2.3 티켓 12 테스트만

```
$ <ENV> uv run pytest tests/test_subscription_status.py tests/test_store_clients.py \
    tests/test_subscription_verify.py -q
....................................................................     [100%]
68 passed in 38.63s
```

### 2.4 마이그레이션 — heads 1줄, 왕복

```
$ FLASK_APP=wsgi.py DATABASE_URL=<t12_migrations> uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 4e72a4045fbc -> a5bab2f58a7b, add subscription table

$ FLASK_APP=wsgi.py DATABASE_URL=<t12_migrations> uv run flask db heads
a5bab2f58a7b (head)

$ FLASK_APP=wsgi.py DATABASE_URL=<t12_migrations> uv run flask db downgrade 4e72a4045fbc
INFO  [alembic.runtime.migration] Running downgrade a5bab2f58a7b -> 4e72a4045fbc, add subscription table

$ FLASK_APP=wsgi.py DATABASE_URL=<t12_migrations> uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 4e72a4045fbc -> a5bab2f58a7b, add subscription table

$ FLASK_APP=wsgi.py DATABASE_URL=<t12_migrations> uv run flask db check
No new upgrade operations detected.
```

`flask db heads` 가 1줄이고, `db check` 로 모델과 마이그레이션 사이 드리프트가
없음을 확인했다. 기존 `tests/test_migrations.py`(왕복 테스트)는 head 에서
`9ec267465b4e` 까지 내려가므로 **내 마이그레이션의 downgrade 도 그 경로에서 실제로
실행된다** — 2.1 의 254 passed 에 포함돼 있다.

### 2.5 라우트 등록 확인

```
$ uv run python -c "from app import create_app; a=create_app('testing'); \
    print([str(r) for r in a.url_map.iter_rules() if 'subscription' in str(r)])"
app factory ok
['/api/v1/subscriptions/verify']
```

## 3. 체크박스별 증거

| 티켓 체크박스 | 어디서 | 무엇이 증명하나 |
|---|---|---|
| `Subscription(...)` + `unique(store, store_key)` 마이그레이션, status enum 6종, `flask db heads` 1개 | `app/models/subscription.py`, `migrations/.../a5bab2f58a7b_*.py`, `app/models/enums.py` | 2.4 (`heads` 1줄, 왕복, `db check` 드리프트 0). 유니크가 실제로 동작하는 증거는 `test_the_same_receipt_arriving_twice_at_once_still_makes_one_row`(스레드 2개가 동시에 INSERT → 제약이 한쪽을 막고 행 1개). status 6종 전부 테스트로 관측: active/grace/hold/expired/revoked = `test_statuses_without_entitlement_are_still_recorded` + `test_apple_status_codes_map_to_our_statuses`, replaced = `test_a_replaced_google_purchase_closes_the_old_row` |
| `clients/app_store.py`(공식 라이브러리, JWS 검증, `environment` 로 엔드포인트, 4040010 → Sandbox 1회)·`clients/play.py`(공식 라이브러리) 래퍼 — 각 함수 하나, 타임아웃 3초 | `app/clients/app_store.py`, `app/clients/play.py` | 환경 선택 `test_apple_receipt_environment_picks_the_endpoint`; **Sandbox 폴백** `test_apple_production_miss_falls_back_to_sandbox_once`(호출 환경 기록 = `[PRODUCTION, SANDBOX]`); 폴백 **1회뿐** `test_apple_sandbox_miss_does_not_loop_back`; 다른 에러는 재시도 안 함 `test_apple_other_api_errors_are_not_retried`; 타임아웃 `test_apple_timeout_is_three_seconds`·`test_play_timeout_is_three_seconds`; 공식 라이브러리는 `pyproject.toml` 의 `app-store-server-library`·`google-api-python-client`, JWS 검증은 `SignedDataVerifier` 사용 |
| 상태 매핑 순수 함수 2개 (Apple 1→active/4→grace+`gracePeriodExpiresDate`/3→hold/2→expired/5→revoked; Google ACTIVE·CANCELED→active/IN_GRACE_PERIOD→grace/ON_HOLD→hold/EXPIRED→expired/PAUSED→hold/PENDING→행 없음) + 미정 14 기록 | `app/services/subscription_status.py` | `tests/test_subscription_status.py` 21개 전부. Apple 5코드 `test_apple_status_codes_map_to_our_statuses`, grace 종료 시각 `test_apple_grace_carries_the_store_grace_deadline`; Google 6상태 `test_google_states_map_to_our_statuses`, PENDING 2종 `test_google_pending_purchase_makes_no_row`, grace 시각 `test_google_grace_deadline_is_the_line_item_expiry`; 모르는 상태는 조용히 통과하지 않음 `test_apple_unknown_status_code_is_rejected`·`test_google_unknown_state_is_rejected`. 미정 14 는 스펙 "미정 항목" 14 줄에 결과 기록 + README `### 12.` |
| `POST /subscriptions/verify` (Bearer): 상품 ID·번들/패키지 확인 → 검증 → upsert(멱등) → `entitlement` 응답, 400 `RECEIPT_INVALID` / 503 `STORE_UNAVAILABLE`, 복원 시 재지정 | `app/api/subscriptions.py`, `app/services/subscription_service.py` | 정상 경로 + 응답 전체 필드 `test_apple_purchase_creates_one_row_and_grants_entitlement`; Bearer `test_verify_requires_a_guest_token`(401); 상품 불일치 400 `test_a_receipt_for_another_product_is_rejected`·`test_a_google_purchase_of_another_product_is_rejected`; 번들 불일치 400 `test_a_receipt_from_another_app_is_rejected`; 503 `test_store_outage_is_not_the_users_fault`; 잘못된 store 값 400 `test_an_unknown_store_is_a_validation_error`; 재지정 `test_restoring_on_another_guest_moves_the_row_instead_of_copying_it` |
| 테스트: 멱등 중복 전달 / linkedPurchaseToken 교체 → 옛 행 replaced / Sandbox 4040010 폴백 / 다른 게스트 복원 재지정 / 상품 ID 불일치 400 | `tests/test_subscription_verify.py`, `tests/test_store_clients.py` | 순서대로 `test_the_same_receipt_twice_keeps_one_row`(+ 동시 전달판, + 상태가 바뀐 재전송 `test_a_renewed_receipt_updates_the_same_row`) / `test_a_replaced_google_purchase_closes_the_old_row`(+ 옛 토큰을 못 본 경우 `test_a_replacement_for_a_purchase_we_never_saw_is_fine`) / `test_apple_production_miss_falls_back_to_sandbox_once` / `test_restoring_on_another_guest_moves_the_row_instead_of_copying_it`(+ `test_the_previous_guest_loses_the_entitlement_after_a_restore`) / 위 칸의 400 테스트 2개. provider 래퍼 monkeypatch + fixture JSON 으로만 돌렸다 |
| 권한 계산은 임시로 `status == active\|grace`, 판정표·TTL 은 13 에서 완성(`entitlement` 조립 함수를 13 이 교체) | `app/services/entitlement.py` | 모듈 독스트링에 "티켓 13 이 이 함수를 바꿔 끼운다" 를 명시했고 **시계를 읽지 않는다**(만료 비교 없음). active/grace 만 권한: `test_statuses_without_entitlement_are_still_recorded`(hold·expired·revoked → `active:false`), `test_google_hold_and_pause_have_no_entitlement`, grace 는 권한 있음 `test_a_renewed_receipt_updates_the_same_row`. `next_check_at = last_verified_at + 1h` 는 `test_next_check_at_is_an_hour_after_the_last_store_lookup` |
| `.env.example` 에 App Store·Play 설정 추가, README "설계 판단" 에 "공식 라이브러리·RevenueCat 미사용·store_key 멱등" | `.env.example` `# [12]` 절, `README.md` `### 12.` | 파일 그 자체. README 절에 세 항목 전부 + Sandbox 근거 + Google revoked 를 안 쓰는 근거까지 적었다 |

## 4. 코디네이터에게 물어 정한 것

`orca orchestration ask` 로 하나 물었다: **Google 매핑의 "revoked/환불 → revoked"
신호를 무엇으로 볼지**가 티켓·스펙·ADR 0003 에 없었다. Play Developer API v2
응답(`SubscriptionPurchaseV2`)에는 철회 전용 필드가 없고(번들 discovery doc 으로
확인), 그 신호는 Voided Purchases API 나 RTDN `SUBSCRIPTION_REVOKED` 에만 있는데
둘 다 이 티켓 범위 밖이다(웹훅은 미정 1).

**답변: B** — v2 응답만으로는 `revoked` 를 내지 않는다. `subscriptionState` 를
그대로 매핑하고, 순수 함수 입력에 명시적 `revoked` 플래그 자리만 둔다
(`google_subscription_status(purchase, *, revoked=False)`). 근거: 판정표에서
`expired` 와 `revoked` 가 둘 다 "권한 없음" 이라 사용자가 보는 결과가 같으므로,
라이브 API 로 검증하지 못한 해석(`developerInitiatedCancellation` = 환불)을 코드에
사실처럼 박지 않는다.

코디네이터가 함께 요구한 고정 테스트도 넣었다:
`test_a_refunded_google_subscription_loses_the_entitlement_immediately` — Google
구독이 **만료일 이전에** EXPIRED 로 바뀌면(환불·철회 시 실제로 관측되는 모양)
24h 유예 없이 즉시 권한이 사라진다. 결과는 스펙 "미정 항목" 14 와 README
`### 12.` 양쪽에 기록했다.

## 5. 설계 판단 요약 (면접 설명용)

- **멱등의 열쇠는 게스트가 아니라 `store_key`.** `unique(store, store_key)` 하나뿐
  (Apple `originalTransactionId` / Google `purchaseToken`). 앱이 같은 영수증을
  구매 직후·복원·앱 시작 동기화마다 다시 올리는 게 정상 동작이라서다. 동시
  전달은 유니크 제약이 한쪽을 막고 막힌 쪽이 갱신으로 도는 식으로 처리한다.
- **`guest_id` 에 유니크를 걸지 않았다.** 애플에서 사고 안드로이드로 옮기면 한
  게스트에 행이 둘인 상태가 실제로 생긴다. 그래서 `build_entitlement` 는 목록을
  받아 "권한을 주는 행이 하나라도 있나" 를 본다.
- **래퍼와 판정의 분리**(스펙 §A.17). 네트워크는 `clients/*.py`, 상태 해석은
  `services/subscription_status.py` 의 순수 함수. 순수 함수 입력을 라이브러리
  객체가 아니라 dict 로 둬서 fixture 를 실제 응답 모양 그대로 보관한다.
- **Sandbox 를 프로덕션에서도 받는다**(US 34a). 환경을 서버 설정으로 고정하지
  않고 영수증의 `environment` 를 따른다. 프로덕션 조회가 "없음" 이면 Sandbox 로
  한 번만 재조회한다.
- **타임아웃 3초.** 공식 라이브러리가 30초를 박아둬서 `_execute_request` 한 줄만
  덮어쓰는 서브클래스를 뒀다. 앱이 서버 응답 뒤에야 구매를 완료 처리하므로
  구매 화면을 30초 붙잡아 둘 수 없다.
- **400 과 503 을 가른다.** 영수증이 틀린 건 400(앱이 버린다), 스토어 장애·설정
  누락은 503(앱이 다음 시작에 다시 올린다). 설정이 비어 있을 때 영수증을 탓하지
  않는 게 중요하다 — 그러면 앱이 정상 영수증을 영구히 버린다.
- **거절 이유를 응답에 담지 않는다.** 상품·번들 불일치 이유는 로그에만 남긴다
  (남의 영수증을 떠보는 데 쓰일 수 있다).

## 6. 하지 않은 것 / 남은 것

- **권한 판정표·재조회 TTL (티켓 13).** `build_entitlement` 는 지금 시계를 읽지
  않고 `active|grace` 만 본다. 스펙 §A.8 의 "active 는 만료 +24h, grace 는
  `grace_expires_at > now`, 확인된 revoked/hold 에는 유예 없음" 과 `last_verified_at`
  1시간 TTL 재조회, 미정 18(만료 ±24h 구간 5분 상한)·19(`now >= next_check_at`
  경계)는 티켓 13 몫이다.
- **`/me/stats` 의 `entitlement` 필드 (티켓 13).** 이 티켓은 `/subscriptions/verify`
  응답까지만 만들었다. `app/services/stats_service.py` 는 건드리지 않았다.
- **스토어 웹훅·Voided Purchases (미정 1).** 그래서 Google 철회가 `revoked`
  라벨로 기록되지 않는다(4절).
- **Beat 매일 재조회 (스펙 §A.8 (c)).** Celery 배선은 이 티켓 범위가 아니다.
- **실기기·Sandbox 실구매 확인.** 스토어 계정·상품 등록이 사람 작업(스펙 D2)이라
  할 수 없다. 서버 쪽은 fixture 로 고정했고, 배포 전 준비물은
  `docs/RELEASE.md` `### 12.` 에 적었다.
