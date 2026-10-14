# 티켓 13 구현 증거 — 구독 권한 판정표·1h TTL 재조회·Beat 재검증

- 날짜: 2026-10-14
- 브랜치: `dosaem/t13-subscription-entitlement-recheck-beat`
  (로컬 `main` = `bf287f6` "Merge 티켓 06" 위로 rebase 완료)
- 환경: macOS (Darwin 25.3.0), uv / Python 3.12.14, MySQL 8.4.11 · Redis 7.4.11
  (로컬 compose, 다른 워커가 쓰는 컨테이너를 내리지 않았다)
- 전용 테스트 자원: DB `chosung_daily_test_t13`, 마이그레이션 DB
  `chosung_daily_test_t13_migrations`, Redis DB **15**
  (`TEST_DATABASE_URL` / `TEST_MIGRATION_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 —
  공용 테스트 DB·Redis 와 다른 워커의 DB 는 건드리지 않았다)
- 외부 호출 0건: Apple·Google·Slack 어디에도 실제 요청을 보내지 않았다. 스토어
  조회 함수와 `notify_operator` 만 monkeypatch 로 바꿔 끼웠고, 값은 실제 응답
  모양 fixture(`tests/fixtures/store/`)다.
- 키·토큰·비밀번호를 파일·로그·이 문서에 적지 않았다(설정 **이름**만). `.env`,
  `.env.prod*` 실제 값은 열지도 고치지도 않았다.
- UI 없음 — 백엔드 전용 티켓이라 `impeccable detect`(웹)/`audit.native`(Flutter)는
  해당 없다. `web/`·`mobile/` 을 건드리지 않았다. 티켓 체크박스에도 UI 항목이 없다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `app/services/entitlement.py` | 티켓 12 의 임시 판정을 **판정표**로 교체. 순수 함수 `is_entitled(status, expires_at, grace_expires_at, now)` · `recheck_interval(expires_at, now)` · `is_recheck_due(subscription, now)`, 상수 `RENEWAL_GRACE`(24h) · `RECHECK_INTERVAL`(1h) · `NEAR_EXPIRY_WINDOW`(24h) · `NEAR_EXPIRY_RECHECK_INTERVAL`(5분) · `RECHECKABLE_STATUSES`. `build_entitlement(subscriptions, now)` 로 시계를 인자화 |
| `app/services/subscription_recheck.py` | **신설**. `entitlement_for(guest)`(= `/me/stats` 경로, TTL 지난 구독만 재조회) · `recheck(subscription)`(행 하나, 커밋 포함) · `recheck_expiring_subscriptions()`(Beat) · `_alert_on_repeated_failures()`. 상수 `BEAT_RECHECK_WINDOW`(3일) · `FAILURE_ALERT_THRESHOLD`(3) |
| `app/clients/app_store.py` | `fetch_subscription_status(store_key, environment)` 추가 — 영수증 없이 상태만 조회(재조회·Beat 용). 거래 정보가 없으면 `StoreUnavailableError` |
| `app/models/subscription.py` | `recheck_failures` 컬럼(NOT NULL, 기본 0) + `last_verified_at` 주석 갱신("성공한 조회 시각") |
| `migrations/versions/d7a1f0ca0a29_add_subscription_recheck_failures.py` | **신설**. `subscription.recheck_failures`, `server_default='0'`. `down_revision = dae1b5af0cf7`(티켓 06, 선행 머지 리비전 위로 재설정 — 아래 2.4) |
| `app/repositories/subscription_repository.py` | `find_expiring(statuses, before)` · `find_with_repeated_failures(at_least)` 추가 |
| `app/schemas/stats.py` | `MyStatsResponse.entitlement: EntitlementResponse` |
| `app/services/stats_service.py` | `get_my_stats` 가 `entitlement_for(guest)` 를 채운다 |
| `app/services/subscription_service.py` | `build_entitlement(..., utcnow())` — 시계 인자화에 맞춘 호출부 1줄 |
| `app/tasks/scheduled.py` | `tasks.recheck_expiring_subscriptions` 태스크 + Beat `03:30 KST` |
| `README.md` | API 표 `/api/v1/me/stats` 행에 `entitlement` 추가, Beat 스케줄 표 03:30 행 + 수동 트리거 한 줄, "설계 판단" 에 `### 13.` |
| `docs/adr/0003-subscription-entitlement-on-server.md` | 재조회 문구를 §A.8 기준(1h TTL + 만료 ±24h 5분 상한)으로 갱신, 폴링 설명·Consequences 도 같이 (미정 15) |
| `.scratch/store-launch/spec.md` | "미정 항목" 끝에 `(티켓 13 반영)` 한 줄 — 미정 18·19·15 확정 결과(티켓이 지시한 항목) |
| `tests/test_entitlement.py` | **신설**. 순수 함수 27개(판정표·간격·경계) |
| `tests/test_subscription_recheck.py` | **신설**. `/me/stats` TTL·실패 카운터·Beat 28개 |
| `tests/test_store_clients.py` | `fetch_subscription_status` 4개 추가(영수증 없이 조회·환경 유지·거래 정보 없음·Sandbox 폴백) |
| `tests/test_celery_wiring.py` | 태스크 등록·03:30 스케줄·서비스 위임 3곳 추가 |
| `tests/test_migrations.py` | `recheck_failures` 왕복 2개 추가(상수 `RECHECK_COUNTER_PARENT_REVISION`) |

Beat 스케줄 표의 03:30 행은 시각 순서가 아니라 **표 끝**에 덧붙였다 — 공유
파일은 자기 행만 섹션 끝에 붙이는 공통 규칙(병렬 티켓 충돌 방지)을 따른 것이고,
머지 후 정렬이 필요하면 코디네이터가 한 줄 옮기면 된다.

손대지 않은 공유 파일: `.env.example`(새 설정값 없음 — 간격·임계는 코드 상수다),
`docs/RELEASE.md`(사람이 출시 전에 할 일이 늘지 않는다).

## 2. 실행한 명령과 출력

모두 아래 환경변수를 붙여 돌렸다(이하 `<ENV>` 로 줄임):

```
TEST_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t13?charset=utf8mb4
TEST_MIGRATION_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t13_migrations?charset=utf8mb4
TEST_REDIS_URL=redis://localhost:6379/15
```

### 2.1 전체 테스트 스위트 (rebase 후)

```
$ <ENV> uv run pytest -q
........................................................................ [  9%]
........................................................................ [ 19%]
........................................................................ [ 28%]
........................................................................ [ 38%]
........................................................................ [ 48%]
........................................................................ [ 57%]
........................................................................ [ 67%]
........................................................................ [ 77%]
........................................................................ [ 86%]
........................................................................ [ 96%]
..........................                                               [100%]
746 passed in 523.80s (0:08:43)
```

### 2.2 ruff (rebase 후)

```
$ uv run ruff check .
All checks passed!
```

### 2.3 티켓 13 테스트만

```
$ <ENV> uv run pytest tests/test_entitlement.py tests/test_subscription_recheck.py \
    tests/test_celery_wiring.py tests/test_store_clients.py tests/test_migrations.py \
    tests/test_subscription_verify.py -q
........................................................................ [ 43%]
........................................................................ [ 86%]
.......................                                                  [100%]
167 passed in 232.25s (0:03:52)
```

### 2.4 마이그레이션 — heads 1줄, 체인, 드리프트

rebase 로 티켓 06 의 `dae1b5af0cf7`(hint_unlock)가 먼저 들어왔고 그 리비전의
부모가 내 것과 같은 `a5bab2f58a7b` 였다 → **heads 2개**가 될 상황이라 티켓의
공통 규칙대로 내 `down_revision` 을 `dae1b5af0cf7` 로 재설정했다.

```
$ FLASK_APP=wsgi.py DATABASE_URL=<t13_migrations> uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade ff06a1bf5afc -> a5bab2f58a7b, add subscription table
INFO  [alembic.runtime.migration] Running upgrade a5bab2f58a7b -> dae1b5af0cf7, add hint_unlock table for early hint
INFO  [alembic.runtime.migration] Running upgrade dae1b5af0cf7 -> d7a1f0ca0a29, add subscription recheck_failures

$ FLASK_APP=wsgi.py DATABASE_URL=<t13_migrations> uv run flask db heads
d7a1f0ca0a29 (head)

$ FLASK_APP=wsgi.py DATABASE_URL=<t13_migrations> uv run flask db check
No new upgrade operations detected.
```

`heads` 가 1줄이고 `db check` 로 모델–마이그레이션 드리프트가 없음을 확인했다.
downgrade 는 `tests/test_migrations.py` 의 왕복 테스트가 실제로 실행한다(2.1 에 포함).

### 2.5 `/me/stats` 응답 모양

저장된 구독 하나(apple, active, 만료 20일 뒤, `last_verified_at` 10분 전)를 심고
테스트 클라이언트로 한 번 불러 본 응답이다. TTL(1시간) 안이라 스토어를 부르지
않았고, 기존 필드 뒤에 `entitlement` 가 붙는다.

```
$ <ENV> PYTHONPATH=. uv run python <scratch>/stats_shape.py
200
{
  "current_streak": 0,
  "entitlement": {
    "active": true,
    "next_check_at": "2026-10-14T01:36:47Z",
    "source": "apple",
    "status": "active",
    "until": "2026-11-03T00:46:47Z"
  },
  "linked_account": null,
  "max_streak": 0,
  "puzzle_language": "ko",
  "solved_count": 0
}
```

`next_check_at`(01:36:47Z) = `last_verified_at`(00:36:47Z, 호출 시점 00:46 의 10분
전) + 1시간이다. 시각에 타임존(`Z`)이 붙어 나간다 — 앱이 기기 로컬시로 읽으면
만료 판단이 몇 시간씩 틀어지기 때문이다(`EntitlementResponse` 독스트링).

스크립트는 테스트 DB 에만 붙고 `.scratch`/프로덕션을 건드리지 않는다. 같은
응답 모양은 `tests/test_subscription_recheck.py` 의 두 테스트가 자동으로 지킨다.

## 3. 체크박스별 증거

| 티켓 체크박스 | 어디서 | 무엇이 증명하나 |
|---|---|---|
| 권한 판정은 순수 함수(상태, expires_at, grace_expires_at, now) → bool, `revoked\|hold\|expired\|replaced` 없음 / `grace` → `grace_expires_at > now` / `active` → `expires_at + 24h > now` | `app/services/entitlement.py` `is_entitled` | `tests/test_entitlement.py`: `test_an_active_subscription_keeps_the_entitlement_for_24h_after_expiry`, `test_an_active_subscription_loses_the_entitlement_after_the_24h_grace`, `test_a_grace_subscription_has_the_entitlement_on_the_third_day`, `test_a_grace_subscription_loses_the_entitlement_when_the_grace_ends`, `test_a_hold_subscription_has_no_entitlement_even_before_expiry`, `test_a_revoked_subscription_loses_the_entitlement_immediately`, `test_statuses_in_the_no_entitlement_column_never_grant_it[expired/revoked/replaced]`, `test_a_missing_timestamp_does_not_grant_the_entitlement` |
| 단위 테스트: active 유예 24h · grace 3일째 있음 · hold 없음 · revoked 없음 | 같음 | 위 표의 네 케이스가 각각 그것. 시계를 인자로 받으므로 DB·Flask·monkeypatch 없이 돈다(파일 전체 27 passed) |
| `GET /me/stats` 가 `entitlement {active, until, status, source, next_check_at}` 를 돌려준다 | `app/schemas/stats.py`, `app/services/stats_service.py` | `tests/test_subscription_recheck.py::test_stats_without_a_subscription_reports_no_entitlement`(5개 키 전부 None), `::test_stats_reports_the_entitlement_and_the_next_check_time`(기존 필드 `current_streak` 도 그대로) |
| `status ∈ {active, grace, hold}` 이고 `now >= last_verified_at + 1h`(경계 포함, 미정 19)면 재조회 | `is_recheck_due` + `entitlement_for` | 순수: `test_the_recheck_is_due_exactly_at_the_next_check_time`(정확히 그 시각), `test_the_recheck_is_not_due_a_second_early`(1초 전), `test_live_statuses_are_rechecked[active/grace/hold]`, `test_finished_statuses_are_never_rechecked[...]`. 엔드포인트: `test_a_subscription_revoked_at_the_store_loses_the_entitlement_after_an_hour`(정확히 1시간 전 → 조회 1회), `test_a_hold_subscription_is_rechecked_so_a_recovered_payment_shows_up`, `test_finished_subscriptions_are_not_rechecked[...]` |
| 타임아웃 3초 | `app/clients/app_store.py` `TIMEOUT_SECONDS = 3`(`_TimeoutAppStoreServerAPIClient`), `app/clients/play.py` `httplib2.Http(timeout=3)` — 티켓 12 에서 둔 값을 재조회가 그대로 쓴다(같은 래퍼 함수 경로) | `tests/test_store_clients.py::test_apple_timeout_is_three_seconds`·`::test_play_timeout_is_three_seconds`(상수 3초), `::test_apple_network_timeout_is_a_store_outage`·`::test_play_network_timeout_is_a_store_outage`(타임아웃 → 503). 재조회가 같은 래퍼 경로를 쓴다는 것은 `::test_apple_status_lookup_needs_no_receipt`(`_TimeoutAppStoreServerAPIClient` 를 지나간다)가 보여준다 |
| 실패 시 저장값 유지 + 실패 카운터 | `recheck` 의 `except (StoreUnavailableError, ReceiptInvalidError, ValueError)` | `test_a_failed_recheck_keeps_the_stored_values_and_counts_the_failure[StoreUnavailableError/ReceiptInvalidError]` — 상태·`last_verified_at` 그대로, `recheck_failures == 1`, 응답은 200 + 저장된 권한. `test_a_successful_recheck_resets_the_failure_counter` |
| 만료 ±24h 안에서는 재조회 상한 5분(미정 18 확정 + 스펙 기록) | `recheck_interval` | 순수: `test_the_recheck_interval_drops_to_five_minutes_around_the_expiry[-24h/0/+24h]`, `test_the_expiry_window_is_24h_wide_on_both_sides`. 엔드포인트: `test_near_the_expiry_the_interval_drops_to_five_minutes`(6분 전 → 조회), `test_near_the_expiry_a_call_within_five_minutes_is_not_rechecked`(4분 전 → 조회 없음), `test_outside_the_expiry_window_six_minutes_is_not_enough`(같은 6분인데 만료 20일 전이면 조회 없음). 스펙 기록: `.scratch/store-launch/spec.md` "미정 항목" 의 `(티켓 13 반영)` 줄 |
| `next_check_at = last_verified_at + 1h` | `build_entitlement` | `test_stats_reports_the_entitlement_and_the_next_check_time`(저장된 `last_verified_at + 1h` 와 문자열 비교), 기존 `tests/test_subscription_verify.py::test_next_check_at_is_an_hour_after_the_last_store_lookup` 도 통과 유지 |
| 테스트: 만료 20일 전 구독의 provider 상태만 revoked, `last_verified_at` 정확히 1시간 전 → 권한 제거 | — | `test_a_subscription_revoked_at_the_store_loses_the_entitlement_after_an_hour`: 조회 1회, 응답 `active=False`/`status=revoked`, DB 행도 revoked |
| 테스트: 59분 전이면 재조회 없음 | — | `test_a_subscription_verified_59_minutes_ago_is_not_rechecked`: 스토어 호출 0건, 저장된 권한 그대로 |
| 테스트: 만료 2일 뒤 verify 재전송 즉시 반영 | — | `test_resending_the_receipt_two_days_after_expiry_takes_effect_at_once`: 먼저 `/me/stats` 가 `active=False`(24h 유예 끝) + 스토어 호출 0건(TTL 안), 그 뒤 `verify_receipt` 한 번에 `active=True`, 행은 그대로 1개 |
| 테스트: 재조회 1시간 상한 | — | `test_the_hourly_interval_caps_the_store_calls`: `/me/stats` 3연속 호출에 스토어 조회 1회 |
| Beat 매일: `active\|grace\|hold` 중 만료 3일 이내 재조회(서비스 함수 직접 호출 + 배선) | `recheck_expiring_subscriptions`, `app/tasks/scheduled.py` | 서비스: `test_the_beat_rechecks_subscriptions_expiring_within_three_days`, `test_the_beat_ignores_subscriptions_that_expire_later`, `test_the_beat_only_rechecks_live_statuses[expired/revoked/replaced]`, `test_the_beat_ignores_the_ttl_and_rechecks_anyway`, `test_one_failing_subscription_does_not_stop_the_others`. 배선: `tests/test_celery_wiring.py::test_tasks_are_registered`, `::test_subscription_recheck_runs_daily_away_from_the_midnight_batch`(03:30), `::test_tasks_delegate_to_the_service_functions` |
| 재조회 실패 연속 3회 누적 → `notify_operator` | `_alert_on_repeated_failures` | `test_the_beat_alerts_the_operator_after_three_consecutive_failures`(kind = "구독 재조회 실패 누적", 본문에 행 ID 있고 `store_key` 는 없음), `test_the_beat_does_not_alert_before_the_threshold`, `test_the_beat_does_not_alert_when_every_recheck_succeeds` |
| `docs/adr/0003-*.md` 의 "만료 ±24h" 문구를 §A.8 기준으로 갱신(미정 15) | `docs/adr/0003-subscription-entitlement-on-server.md` | 세 군데: 요약 문단(폴링 + 1h TTL), **재조회** 문단(경계 포함·5분 상한·실패 시 저장값 유지·3회 알림), **Consequences**("무상한" → "5분 간격"). `.scratch` 사본은 계획 당시 원본이라 선택 사항이라 그대로 뒀다 |
| README "설계 판단" 에 판정표·유예·TTL 재조회·웹훅 미도입 근거 | `README.md` `### 13.` | 판정표 표 + 24h 유예를 active 에만 주는 이유, 시계 인자화 근거, 재조회 세 경로, ±24h 5분 상한과 `next_check_at` 에 안 싣는 이유, 실패 시 저장값 유지, 연속 3회 알림을 한 건으로 묶는 이유·`store_key` 미포함, 영수증 없이 도는 재조회, 웹훅 미도입 근거 |

## 4. 설계 판단과 그 근거 (리뷰어가 볼 지점)

1. **판정 함수는 시계를 인자로 받는다.** `is_entitled(status, expires_at,
   grace_expires_at, now)`. 티켓이 지정한 시그니처이기도 하고, 이 덕에
   `tests/test_entitlement.py` 27개가 DB·Flask·monkeypatch 없이 0.03초에 돈다.
2. **24h 유예는 `active` 에만.** 스펙 §A.8 의 "확인된 revoked/hold 에는 적용
   안 함" 을 그대로 구현했다. 유예를 상태 밖으로 빼내 `if` 하나로 두면 환불한
   사용자도 하루 더 쓰게 된다.
3. **`grace` 는 `grace_expires_at` 만 본다.** 값이 비어 있으면 권한 없음이다 —
   "미래까지 유효" 를 증명할 수 없는 행에 권한을 주는 쪽이 더 위험하고, 스토어
   둘 다 유예 종료 시각을 주므로(Apple `gracePeriodExpiresDate`, Google 은
   `expiryTime` 이 연장돼 옴) 빈 값은 데이터 이상이다. 다음 재조회가 채운다.
4. **재조회 실패는 `last_verified_at` 을 올리지 않는다.** 올리면 장애 중에 TTL
   이 리셋돼 "한 시간 동안 아무도 다시 안 묻는" 구간이 생긴다. 안 올리니 다음
   `/me/stats` 가 바로 재시도하고, 그 대신 같은 장애에서 호출이 반복되는 비용을
   받는다(그래서 연속 실패 카운터가 필요하다).
5. **`ReceiptInvalidError`(400)도 권한을 뺏지 않는다.** Apple 이 "어느 환경에도
   없는 거래" 라고 답하는 경우는 설정·환경 혼선일 수도 있어서, 권한 제거는
   스토어가 분명히 말해준 상태(`revoked`·`expired`·`hold`)로만 한다. `ValueError`
   (모르는 상태 코드)도 같은 칸에 넣어 `/me/stats` 가 500 이 되지 않게 했다.
6. **커밋 경계는 "구독 하나".** `recheck()` 가 자기 행을 커밋한다. Beat 가 수십
   건을 돌다 스토어가 죽어도 앞의 결과는 남아야 하고, 한 구독의 재조회는 다른
   구독과 같이 되돌릴 이유가 없는 독립된 사실이다(레포 규칙 "함수 하나 = 커밋
   하나" 를 구독 하나 단위로 읽었다).
7. **`entitlement_for` 는 호출한 게스트의 구독만 본다.** 전체를 훑으면 한 사람의
   `/me/stats` 가 전체 구독 수만큼 스토어 API 를 때린다
   (`test_the_recheck_only_touches_the_calling_guests_subscriptions`).
8. **Beat 는 TTL 을 보지 않는다.** 이 경로의 목적이 "앱을 안 켜는 구독자의 행도
   하루 한 번은 본다" 라서, 방금 조회한 행을 한 번 더 묻는 비용을 받는다.
9. **Beat 03:30 KST.** 자정 배치(퍼즐 배정 00:00·통계 00:05)와 떼어놨다 —
   스토어 조회가 느려도 퍼즐 배정을 밀지 않게. 09:00 잔량 알림과도 겹치지 않는다.
10. **알림은 한 건으로 묶고 `store_key` 를 싣지 않는다.** 설정이 틀어진 날
    구독마다 보내면 채널이 같은 메시지로 덮인다. 결제 식별자를 Slack 으로
    복제하지 않는 것은 `apple_secret_service` 가 JWT 를 안 싣는 것과 같은 규칙이다.
11. **재조회용 Apple 조회 함수를 따로 뒀다.** `fetch_subscription_status(store_key,
    environment)`. 구매 경로는 영수증으로 주인을 확인해야 하지만 재조회는 이미
    받아들인 구독을 보는 것이고, Beat 는 앱의 JWS 를 아예 못 본다. 상태 조회에
    거래 정보가 없으면 저장값을 덮지 않도록 503 으로 올린다.
12. **MySQL DATETIME 반올림.** `tests/test_subscription_recheck.py` 의 행 심기
    헬퍼는 `utcnow().replace(microsecond=0)` 를 기준으로 상대 시각을 만든다 —
    마이크로초까지 심으면 MySQL 이 초 단위로 반올림해서 "정확히 1시간 전" 경계
    테스트가 그 반올림에 좌우된다(처음에 실제로 이 이유로 깨졌다).

## 5. 남은 것 / 범위 밖

- **스토어 웹훅은 미도입**(미정 항목 1). 구독자가 생기면 폴링을 보완하는 형태로
  붙인다 — 근거는 README `### 13.` 마지막 항목.
- **Flutter 쪽 타이머·광고 반영**은 티켓 31 몫이다. 서버는 `next_check_at` 까지만
  준다. 미정 19 의 "Flutter 가짜 시계 테스트" 도 그 티켓에서 다룬다(서버 쪽
  경계 해석은 `is_recheck_due` 의 순수 테스트 두 개로 못 박아 뒀다).
- **Google `revoked` 라벨**은 여전히 못 붙인다(미정 1·14, 티켓 12 결정 유지).
  환불은 "만료일 전 EXPIRED" 로 관측되고 판정표에서 같은 칸이라 권한 결과는 같다.
- 실패·skip·건너뛴 명령 없음. 위 2.1·2.2 출력이 그대로 그 증거다.

## 수정 라운드 1

- 날짜: 2026-10-14
- 기준: `review/impl-review-13.md` "티켓 13 최종 리뷰 — 라운드 1"(판정 FAIL,
  BLOCKER 0 · MAJOR 1 · MINOR 1). 리뷰 파일은 고치지 않았다.
- 로컬 `main` = `1e764da`("Merge 티켓 15") 위로 rebase 했다. 작업 중에 main 이
  두 번 움직여서(티켓 22 머지 `148715b` → 티켓 15 머지 `1e764da`) 두 번 rebase
  했고, 두 번 다 충돌이 없었다. 아래 재실행 수치는 **마지막 rebase 뒤**의 것이다.
  `origin/main` 은 쓰지 않았다. 전용 테스트 자원(위 2절의 DB·Redis 15)과
  외부 호출 0건·시크릿 미기록 조건은 그대로다.
- 수정 커밋: `fix(13): 겹친 재조회가 확인된 철회를 덮지 않도록 쓰기 직전 행 잠금`
  (`README.md`, `app/repositories/subscription_repository.py`,
  `app/services/subscription_recheck.py`, `tests/test_subscription_recheck.py`).
  결함 수정 범위 밖의 리팩토링·기능 추가는 없다.

### D-13-1 (MAJOR) — 늦은 재조회 응답이 확인된 철회를 덮어 권한을 복구함

**재현(수정 전).** 리뷰가 적은 절차를 그대로 돌렸다 — 전용 테스트 DB 에서
독립 app context 두 개(= 독립 DB 세션 두 개), A 는 `status 1`(active) 응답을
받기 직전 보류하고 그 사이에 B 가 `status 5`(revoked) 로 재조회·커밋한다.

```
$ <ENV> PYTHONPATH=. uv run python repro_d13_1.py   # 수정 전
B newer response: revoked False
A delayed response: active True
Final stored state: active
```

**원인.** `recheck()` 가 스토어 응답을 받으면 **조회 중에 그 행이 바뀌었는지
보지 않고** `status`·`expires_at`·`grace_expires_at`·`last_verified_at` 을
무조건 덮어썼다. 재조회는 "읽고(TTL 판정) → 외부 호출(최대 3초) → 쓰기" 라서
그 사이가 비는데, 행 잠금도 버전·조회 순서 검증도 없었다. 그래서 먼저 출발한
조회가 늦게 도착하면 이미 저장된 철회를 되돌리고, `last_verified_at` 까지
현재로 올려서 다음 TTL(1시간)까지 잘못된 권한이 남았다. 겹치는 조합은
`/me/stats` 두 요청, `/me/stats` 와 Beat, 둘 다 같은 `recheck()` 를 지난다.

**수정.** 쓰기 직전에 행을 잠그고 다시 읽어 **조회 전에 본 값과 비교**한다.

- `app/repositories/subscription_repository.py` — `lock_and_refresh(subscription)`
  추가. `db.session.refresh(..., with_for_update=True)` = `SELECT ... FOR UPDATE`.
  InnoDB 의 잠금 읽기는 REPEATABLE READ 스냅샷이 아니라 최신 커밋을 보므로,
  잠금을 받은 뒤 읽으면 그 사이의 커밋이 그대로 보인다
  (`guest_stats_repository.lock_for_guest` 와 같은 규칙).
- `app/services/subscription_recheck.py` — `_row_state()` 로 조회 전 상태
  (상태·만료·유예·확인 시각·실패 카운터)를 들고 있다가, 쓰기 직전
  `_superseded()` 가 잠그고 다시 읽어 다르면 **우리 응답을 버리고 커밋만 한다**
  (잠금을 바로 놓고, 행은 이미 최신 값으로 채워져 있어 호출부의 권한 판정이
  최신 상태를 본다). 성공·실패·결제 대기 세 경로 모두에 둔다 — 실패 경로가
  그대로면 그 사이에 성공한 조회가 0 으로 돌린 카운터를 되돌린다.
- 조회 **앞**에 잠그지 않은 이유: 외부 호출이 끝날 때까지 행을 들고 있으면 같은
  구독의 다른 요청이 전부 최대 3초를 기다린다. 비교 기준을 시각이 아니라 "값이
  바뀌었나" 로 둔 이유: MySQL `DATETIME` 은 소수점 초를 버려서(위 4절 12번)
  같은 초 안에서 겹치면 시각 비교가 뒤집힌다.

**증명.**

```
$ <ENV> PYTHONPATH=. uv run python repro_d13_1.py   # 수정 후
B newer response: revoked False
A delayed response: revoked False
Final stored state: revoked
```

재현을 고정한 테스트(`tests/test_subscription_recheck.py`, "겹친 재조회" 절):

| 테스트 | 무엇을 못 박나 |
|---|---|
| `test_a_delayed_store_response_does_not_revive_a_confirmed_revocation` | A 의 스토어 경계 안에서 B(독립 세션)가 철회를 저장하면, A 의 늦은 active 응답이 버려지고 `entitlement.active is False` · 저장 상태 `revoked` |
| `test_a_delayed_failure_does_not_count_against_a_fresh_success` | 같은 겹침에서 A 의 실패가 B 가 리셋한 `recheck_failures`(0)를 건드리지 않음 |

```
$ <ENV> uv run pytest tests/test_subscription_recheck.py -q -k delayed   # 수정 전
FAILED tests/test_subscription_recheck.py::test_a_delayed_store_response_does_not_revive_a_confirmed_revocation
  assert entitlement.active is False
  AssertionError: assert True is False
FAILED tests/test_subscription_recheck.py::test_a_delayed_failure_does_not_count_against_a_fresh_success
  assert row.recheck_failures == 0
  AssertionError: assert 3 == 0
2 failed, 28 deselected in 3.18s

$ <ENV> uv run pytest tests/test_subscription_recheck.py -q                # 수정 후
30 passed in 28.85s
```

**남는 순서 하나(의도).** 두 조회가 **동시에 떠 있고** A(active, 더 오래된
사실)가 B(revoked)보다 먼저 쓰는 순서에서는, B 가 자기 응답을 버린다 — 둘 중
어느 응답이 더 최신인지 서버가 알 방법이 없기 때문이다(Play 응답에는 비교할
시각이 없다). 이때 철회는 "되돌려지는" 게 아니라 **다음 재조회(≤1시간, 또는
Beat 03:30)로 밀린다** — 스펙 §A.8 이 폴링에 허용한 반영 지연 안이고, 불확실할
때 돈 낸 구독자 쪽으로 기울이는 이 모듈의 기존 규칙(실패 시 저장값 유지)과도
같은 방향이다. 리뷰가 지적한 "이미 저장된 철회가 오래된 응답에 덮이는" 경우는
어느 순서에서도 없어졌다: 마지막에 쓰는 쪽은 항상 그 직전 값을 잠금 아래에서
다시 읽은 쪽이다.

### D-13-2 (MINOR) — 공유 README API 표의 기존 행을 직접 수정함

**원인.** 티켓 공통 규칙(공유 절은 자기 행만 **절 끝에** 덧붙이기)을 API 표에
적용하지 않고, 기존 `/api/v1/me/stats` 행에 `entitlement` 설명을 끼워 넣어
기존 행을 치환했다. 같은 행을 건드리는 병렬 티켓과 충돌한다.

**수정.** 기존 행을 원문 그대로 복원하고, 티켓 13 행을 표 **끝**(티켓 06 의
`hint-unlock` 행 다음)에 덧붙였다. Beat 스케줄 표 03:30 행과 수동 트리거 한
줄은 이미 각 절 끝에 붙여 둔 상태라 그대로다. 겹친 재조회 규칙은 내 소유 절인
README `### 13.` 안에 한 항목으로 적었다.

```
$ git diff main...HEAD -- README.md | grep '^[-+]| GET | `/api/v1/me/stats'
+| GET | `/api/v1/me/stats` | (티켓 13) 위 응답에 `entitlement {active, until, status, source, next_check_at}` 추가 — …

$ git diff main...HEAD -- README.md | grep -c '^-| '
0
```

기존 행 삭제(`-`)가 0 줄이다 = append-only. `rebase` 로 티켓 22 가 더한 README
`### 22.` 절과도 충돌 없이 합쳐졌다.

### 미수정 MINOR

없다. 리뷰의 MINOR 1건(D-13-2)은 위에서 고쳤다. 리뷰어 지적이 틀렸다고 판단해
그대로 둔 항목도 없다.

### 재실행 (로컬 main `1e764da` 위 rebase 후)

전용 테스트 자원은 그대로다(DB `chosung_daily_test_t13`, 마이그레이션 DB
`chosung_daily_test_t13_migrations`, Redis DB 15). 같은 MySQL 을 다른 워커
두 곳(t15·t17)이 동시에 쓰고 있어서 벽시계 시간만 길어졌다 — 실패·skip 은 없다.

```
$ <ENV> uv run pytest -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 62%]
........................................................................ [ 71%]
........................................................................ [ 80%]
........................................................................ [ 89%]
........................................................................ [ 98%]
...............                                                          [100%]
807 passed in 628.48s (0:10:28)
```

내 쪽에서 늘어난 건 **2개**(위 D-13-1 재현 테스트)다. 첫 rebase(`148715b`,
티켓 22) 위에서는 `746 passed → 748 passed in 1357.82s`, 두 번째 rebase
(`1e764da`, 티켓 15 머지로 그 티켓의 테스트가 main 에 들어옴) 위에서는 위
**807 passed** 다. 두 실행 모두 실패·skip 0, 종료 코드 0.

```
$ uv run ruff check .
All checks passed!

$ FLASK_APP=wsgi.py uv run flask db heads
d7a1f0ca0a29 (head)

$ git diff --check main...HEAD      # 출력 없음, 종료 코드 0
$ git status --short                # 출력 없음 (clean)
```

마이그레이션은 이 라운드에서 건드리지 않았다 — 추가·삭제 없고 `down_revision`
체인도 그대로다(`dae1b5af0cf7` → `d7a1f0ca0a29`). 티켓 22 머지는 마이그레이션을
더하지 않아서 rebase 후에도 heads 는 1개다.

`FOR UPDATE` 가 실제로 나가는지도 SQL 로 확인했다(`before_cursor_execute` 로 문장
기록, 전용 테스트 DB):

```
SELECT subscription.id, …, subscription.recheck_failures, subscription.created_at
  FROM subscription WHERE subscription.id = %(pk_1)s FOR UPDATE
```

이 라운드에서도 Apple·Google·Slack 실제 호출 0건, 프로덕션 접근·`git push` 없음,
시크릿 값은 파일·로그·이 문서에 남기지 않았다(설정 이름만). 재현·확인 스크립트는
세션 scratchpad 에 뒀고 레포에 커밋하지 않았다 — 레포에 남는 재현은 위 테스트 2개다.
