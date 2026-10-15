# 티켓 33 최종 리뷰 — 구독 권한 반영: 시작/복귀 `/me/stats`·`next_check_at` 타이머·권한 해제 시 광고 복구

**브랜치:** `dosaem/t33-app-entitlement-refresh-timer` (`0ba1599`, `2b81c73`) · **기준:** 로컬 `main`(`4afda89`, 티켓 31 머지) · **날짜:** 2026-10-15 · **리뷰어:** Fable (Final Reviewer)

## 라운드 1

### 0. 한 줄 요약

티켓 체크박스 5개 모두 충족. 테스트·analyze·format·APK 빌드·백엔드 ruff/pytest/head 를 직접 돌려 증거 문서의 수치를 재현했다. 결함은 MINOR 2건(둘 다 "관측 시각" 규칙의 빈틈 — 떠난 조회가 겹치거나 이 컨트롤러가 떠나보내지 않은 조회일 때 구매 응답이 옛 응답에 덮일 수 있음. 1건은 임시 테스트로 재현해 확인). BLOCKER·MAJOR 없음. 병렬 티켓 32(미머지)와의 코드 충돌은 코디네이터 지시에 따라 판정에 넣지 않고 "참고" 에 통합 작업 지시용으로 적었다.

### 1. 직접 돌린 것 (증거 문서를 믿지 않고 재실행)

| 항목 | 명령 | 결과 |
|---|---|---|
| Flutter 정적 검사 | `cd mobile && flutter analyze` | `No issues found!`, exit 0 |
| Flutter 포맷 | `dart format --output=none --set-exit-if-changed lib/ test/ integration_test/` | exit 0 (변경 없음) |
| Flutter 전체 테스트 | `cd mobile && flutter test` | `+707: All tests passed!`, exit 0 (증거 §3.5 와 같은 707) |
| Android 디버그 빌드 (코디네이터 요청) | `cd mobile && flutter build apk --debug` | `✓ Built build/app/outputs/flutter-apk/app-debug.apk`, exit 0. 확인 뒤 `mobile/build` 삭제함 |
| 백엔드 lint | `uv run ruff check .` | `All checks passed!`, exit 0 |
| 마이그레이션 head | `./scripts/check_migration_heads.sh` (`flask db heads`) | `b1c7d4e0a932 (head)` 1개 — 이 티켓은 리비전을 만들지 않음, `migrations/` diff 0 |
| 백엔드 테스트 | `uv run pytest -q` (전용 자원) | `1509 passed in 1068.44s (0:17:48)`, exit 0 — 재실행 없이 통과 (증거 §7 과 같은 1509) |

백엔드는 구현 워커가 만들어 둔 전용 자원을 그대로 썼다 — `TEST_DATABASE_URL` 의 DB 이름 `chosung_daily_test_t33`, `TEST_REDIS_URL` 은 `redis://127.0.0.1:6379/7`, `TEST_MIGRATION_DATABASE_URL` 의 DB 이름 `chosung_daily_test_t33_migrations`(세 자원 모두 실행 전 ping 으로 접속 확인). 접속 형식은 `app/config.py` `TestingConfig` 기본값에서 DB 이름만 바꿨고 인증 값은 이 문서에 적지 않는다. 새 DB 를 만들지 않았고 기본 DB 로 전환하지 않았다. `app/`·`web/`·`tests/`·`migrations/`·`.env.example` 의 main 대비 diff 는 비어 있다(백엔드 실행은 회귀 확인용).

### 2. 티켓 체크박스별 판정

| # | 체크박스 | 판정 | 근거 |
|---|---|---|---|
| 1 | 권한 새로고침 스케줄 순수 함수 `(지금, next_check_at, foreground) → 시각 \| 없음` + 경계(`now >= next_check_at`, 미정 19)·백그라운드 정지·복귀 즉시 단위 테스트 | **충족** | `mobile/lib/subscription/entitlement_schedule.dart:17-24` — Flutter/Riverpod import 없는 순수 함수, `nextCheckAt.isAfter(now) ? nextCheckAt : now` 라 경계 포함. `mobile/test/subscription/entitlement_schedule_test.dart` 9개: 정각(=now 반환)·1초 전·이미 지남(=now, 복귀 즉시)·null·백그라운드 2종·UTC×로컬 2종. 직접 돌려 통과 |
| 2 | 앱 시작·복귀·타이머 만료 시 `GET /me/stats` → `entitlement` → 31 게이트 재평가. 권한 사라지면 배너 슬롯 복구·전면 재개, 생기면 제거(위젯 테스트) | **충족** | 시작: `entitlement_refresh.dart:58-78`(`..listen(myStatsProvider, …)` + 이미 값이 있으면 `scheduleMicrotask` 로 한 틱 뒤 `_adopt`), 테스트 "시작 응답의 권한이 광고 게이트에 들어간다". 복귀: `_changeVisibility` → `refresh()`(`:149`), 테스트 "복귀하면 next_check_at 을 기다리지 않고 바로 묻는다". 타이머: `_arm()` → `Timer(..., refresh)`(`:135`). 위젯 테스트 `entitlement_refresh_ads_test.dart` 가 앱 트리(`ChosungApp`)를 띄워 `AdBannerSlot` findsNothing→findsOne + `bannerWidths` 1(복구), findsOne→findsNothing + `bannerDisposals` 1(제거). 전면 재개는 `adGateProvider.canLoadAds` true 를 `entitlement_refresh_test.dart` "정확히 그 시각에…" 가 본다 |
| 3 | 가짜 시계: 포그라운드에 둔 채 `next_check_at` 정확히 그 시각에 `/me/stats` 자동 호출, Fake 가 권한 없음 → 광고 상태 변경 | **충족** | `entitlement_refresh_test.dart` "정확히 그 시각에 /me/stats 를 부르고 권한 해제를 반영한다": `clockProvider` 고정 + `tester.pump(1h-1s)` 에서 호출 0, 남은 1초 뒤 호출 1·`entitlementProvider` false·`showsBannerSlot` true·`canLoadAds` true. 실제 `Timer`·`AppLifecycleListener`·게이트 코드가 돈다(가짜는 ApiClient·시계·AdService 셋) |
| 4 | 32 의 verify 반영과 충돌하지 않도록 31 의 권한 Provider 를 쓴다(새 Provider 만들지 않음) | **충족** (main 기준) | 값을 담는 provider 는 `entitlement_provider.dart`(31) 하나이고 상태 타입 `bool?` 그대로. 새로 생긴 `entitlementRefreshProvider` 의 상태는 "걸린 타이머의 발화 시각" 이지 권한이 아니다. 테스트 "구매가 넣은 권한을 다음 /me/stats 가 덮는다"·"32 의 구매 응답이 뒤늦은 옛 조회에 덮이지 않는다" 가 같은 자리를 쓰는 걸 고정. **단** 미머지 32 브랜치와는 코드 충돌이 있다 — "참고 1" |
| 5 | README Flutter 절에 "권한 재확인 타이머" 한 단락 | **충족** | `README.md:2610` `### 33. 권한 재확인 타이머 — …` 를 설계 판단 절 끝(29·31·36·38 과 같은 자리)에 자기 번호 소제목으로 덧붙임. 31 도 같은 방식으로만 적었으므로(`git diff 269a55c..4afda89 -- README.md` 한 hunk) 선례와 일치 |

### 3. 스펙 대조 (§A.8 (a), US 30a~30c, 미정 19)

- **시작·복귀 호출, 타이머 재호출, 백그라운드 정지, 복귀 즉시** — 모두 코드·테스트로 확인(위 표). 시작은 스플래시가 이미 받은 `/me/stats` 응답을 재사용해 요청을 늘리지 않는다(`fetchMyStatsCalls == 0` 단정). 스펙 문구("시작 때 부른다")의 의도(시작 응답의 권한 반영)는 만족한다.
- **철회 감지 ≤ 1시간 + 타이머 오차(US 30c)** — `next_check_at = last_verified_at + 1h` 정각 호출이 서버 `is_recheck_due`(경계 포함, 미정 19) 와 같은 경계라 정각 호출이 곧 스토어 재조회. 서버 직렬화가 `_as_utc` 로 tz 를 붙이고(`app/services/entitlement.py:120-123`) Dart `DateTime.parse` 가 UTC 로 읽어 `isAfter` 가 절대 시각 비교를 한다(`api_models_test.dart` 가 `isUtc` 단정).
- **실패 시 저장값 유지** — `MyStatsNotifier.refresh` 가 오류를 commit 하지 않고, 컨트롤러는 5분 뒤 재시도(테스트 "조회가 실패하면 보던 권한을 그대로 두고 5분 뒤 다시 묻는다").
- **앱 쪽 하한 5분(이미 지난 `next_check_at`)** — 스펙에 없던 규칙이지만 서버가 `expired`·`revoked`·조회 실패 행에 `last_verified_at` 을 올리지 않아 생기는 호출 고리를 막는 것이고, 서버 재조회 상한(미정 18, 5분)과 같은 값이라 스토어 호출이 늘지 않는다. 스펙 "미정 항목" 에 자기 줄로 기록됨. 스펙과 다른 동작이 아니라 보강으로 본다.
- **관측 시각(`observedAt`)** — 코디네이터 승인(증거 §4, 2026-10-15). 규칙 자체는 `test/ads/entitlement_test.dart` 5개가 고정. 빈틈은 아래 결함 2건.

### 4. 결함 목록

#### D-33-1 — MINOR — 떠난 조회가 겹치면 두 번째 조회의 응답이 "지금 관측" 으로 들어가 구매 응답을 덮는다 (CONFIRMED, 재현함)

- **파일:** `mobile/lib/subscription/entitlement_refresh.dart:84-91` (`refresh()` 의 `_departedAt` 단일 필드), `:105-116` (`_applied` 가 `observedAt: _departedAt` 로 넘김, `:113`)
- **내용:** `_departedAt` 이 컨트롤러 하나에 한 칸뿐이다. 타이머 조회 A 가 떠난 채(서버 스토어 재조회 최대 3초 + 네트워크) 사용자가 홈 → 복귀하면 복귀 조회 B 가 떠나며 `_departedAt` 을 덮고, **A 의 `await` 가 먼저 풀리는 순간 `_departedAt = null`** 이 된다(A 는 세대 불일치로 commit 안 됨). 그 뒤 도착한 B 는 `observedAt: null` = "지금" 으로 들어가 **늘 이긴다**. B 가 떠난 뒤 구매(32)가 끝났으면 구매 전 응답(`active:false`, `next_check_at` 구매 전 값)이 구매를 덮는다 — 증거 §4 첫 줄이 막았다고 한 바로 그 결과(돈 낸 사용자가 광고를 봄)다.
- **재현:** `entitlement_refresh_test.dart` 의 `start/leave/comeBack/advance` 그대로 + `api.fetchMyStatsGate`(Completer) 하나로: 시작 `fakeMyStats(nextCheckAt: now+1h)` → gate 걸고 `advance(1h)`(A 떠남, calls 1) → `leave()` → `advance(1m)` → `comeBack()`(B 떠남, calls 2) → `now += 1m` → `update(active: true)`(구매) → gate 해제 + `pump()`. **기대** `entitlementProvider == true`, **실제** `false` (`showsBannerSlot` true). 리뷰 중 임시 테스트 파일로 돌려 이 실패를 확인했고 파일은 지웠다(워크트리 clean).
- **피해 범위:** 다음 복귀/타이머 조회가 서버의 `active:true` 를 다시 가져오면 회복된다(구매 전 응답의 `next_check_at` 이 null 이면 타이머는 안 걸리지만 복귀 때는 부른다). 그러나 트리거가 "타이머 조회 in-flight 중 홈·복귀 + B in-flight 중 구매 완료" 라 수 초 창이 두 번 겹쳐야 해 실제 빈도는 매우 낮다 → MINOR.
- **고치는 방향(참고):** 떠난 시각을 호출별 지역 변수로 들고 `_adopt` 에 넘기거나, `MyStatsNotifier.refresh` 가 응답과 함께 떠난 시각을 돌려주게 한다(후자는 25·29 소유 파일 — 아래 D-33-2 와 같은 해법). 테스트는 위 재현 순서를 그대로 고정하면 된다.

#### D-33-2 — MINOR — 이 컨트롤러가 떠나보내지 않은 `/me/stats` 응답(플레이 결과 재조회 25·26)은 떠난 시각 없이 "지금" 으로 들어가 구매 응답을 덮는다 (CONFIRMED, 재현함)

- **파일:** `mobile/lib/subscription/entitlement_refresh.dart:111-113` (`_departedAt` 이 null 이면 `observedAt` 없이 `update`)
- **내용:** 증거 §8-9 가 "한계" 로 적은 항목. 제출 → 결과 시트가 `myStatsProvider.refresh()` 를 떠나보낸 뒤(Dio receive timeout 10초까지) 사용자가 Paywall 에서 구매를 끝내면, 늦게 온 구매 전 응답이 `observedAt: null` 로 들어가 `active:true` 를 `false` 로 덮는다. 증거는 "결제 시트가 모달이라 겹치는 입구가 없다" 고 했지만, 결과 시트 → S4/Paywall 진입 → 구매 완료가 10초 안에 끝나는 경우(샌드박스·빠른 네트워크의 Play 재구매) 를 코드가 막지는 않는다.
- **재현(입력 → 기대 vs 실제):** 시작 `fakeMyStats(nextCheckAt: now+1h)` → `fetchMyStatsGate` 걸고 `container.read(myStatsProvider.notifier).refresh()`(플레이 결과 경로, calls 1) → `now += 5s` → `update(active: true)`(구매) → gate 해제 + `await` + `pump()`. **기대** `entitlementProvider == true`, **실제** `false` (코드 경로 `_applied` → `update(active:false, observedAt:null)` → "늘 이김"). 리뷰 중 임시 테스트 파일로 돌려 이 실패를 확인했고 파일은 지웠다. D-33-1 과 같은 근본 원인(떠난 시각을 조회에 붙이지 않고 컨트롤러 필드로 들고 있음)이라 같은 수정으로 같이 닫힌다.
- **피해 범위:** 다음 복귀/타이머 조회에서 회복. 창이 좁고 구현자가 한계로 기록함 → MINOR. 수정은 `MyStatsNotifier`(25·29 소유)에 손대야 하므로 이 티켓 안에서 강제하지 않는다.

### 5. 코디네이터 메모 항목별 판단

1. **비동기 경로 쌍 표의 빠진 쌍** — 계정 전환(`accountEpochProvider.bump` + `discard`)·앱 재시작(시작 응답 선/후)·32 구매/복원(양방향)·백그라운드·조회 실패·내 조회 두 개(타이머×복귀) 는 테스트로 덮여 있다. 빠진 쌍은 **"내 조회 두 개가 실제로 겹친 채 둘 다 도착"**(D-33-1 — 표에는 "복귀 1회뿐이라 겹치지 않는다" 고 적었지만 떠난 A 는 취소되지 않는다) 과 **"플레이 결과 재조회 × 구매"**(D-33-2, 표 마지막 줄의 한계). 32 의 복원(restore)은 구매와 같은 `update(observedAt 없음)` 경로라 별도 쌍이 아니다. 29 의 `adopt(stats)` 는 `discard` → `AsyncData(stats)` 순서로 `clear()` → `update` 가 돌아 테스트 "시작이 끝난 뒤 응답이 와도" 가 덮는다.
2. **observedAt 설계** — 승인 전제대로 `observedAt` 생략 시 늘 이김. 31/main 기준 32 의 `update(active: true)` 호출은 그대로 컴파일된다(미머지 32 브랜치와의 차이는 참고 1).
3. **알려진 한계 3건의 사용자 피해:**
   - 백그라운드 감지 없음 — 스펙 §A.8 그대로(백그라운드 정지, 복귀 즉시 1회). 피해 없음, 결함 아님.
   - 타이머 조회의 401 복구 없음 — `DioApiClient` 는 401 을 `UnauthorizedApiException` 으로 올리고 재발급은 `StartupNotifier._fetchStats` 에만 있다(`startup_controller.dart:53-61`). 타이머 조회가 401 이면 값 유지 + 5분마다 재시도. 세션 중 게스트 토큰이 무효가 되는 길은 계정 삭제·다른 기기 전환 같은 29 의 경계뿐이고 그때는 다른 호출도 전부 401 이라 이 경로만의 피해가 없다. 환불이 그 사이 확인돼도 다음 시작에서 반영된다. 결함 아님(참고 3).
   - 플레이 결과 재조회의 관측 시각 없음 — 실제 피해 가능(구독자가 다음 복귀까지 광고를 봄)하지만 창이 좁다 → D-33-2 MINOR.
4. **`flutter build apk --debug`** — 직접 돌려 exit 0 확인, `mobile/build` 삭제함(§1).

### 6. 보안·범위·공유 파일

- **보안:** 새 엔드포인트·입력·시크릿 없음. `/me/stats` 는 기존 Bearer 경로(`_bearer`). 시크릿 값이 파일에 기록된 곳 없음(증거 문서의 접속 문자열은 `…` 로 가림, 테스트 토큰은 `'guest-token'` 가짜).
- **데이터 손상:** 앱 로컬 상태만 바꾼다. 서버 쓰기 없음.
- **범위:** 변경 16파일 모두 `mobile/`·`README.md`·스펙 미정 1줄·`review/`. 백엔드·웹·마이그레이션 0건. 티켓 범위 밖 변경 없음.
- **공유 파일 규칙:** README `### 33.` 자기 번호 소제목 1개를 절 끝에, 스펙 "미정 항목" 끝에 `(티켓 33 반영)` 자기 줄 1개. `.env.example`·`docs/RELEASE.md`·API 표는 건드리지 않음(건드릴 것 없음). 규칙 위반 없음.
- **테스트 품질:** 가짜는 ApiClient·시계·AdService 셋뿐이고 타이머·수명 리스너·게이트·provider 가 실제로 돈다. `Completer` 로 순서를 만드는 테스트가 양방향을 고정한다. 항상 통과하는 테스트는 못 찾았다(위젯 테스트의 `wakeUp` 이 타이머 대신 `refresh()` 를 직접 부르는 건 `runAsync` 구역 한계를 증거 §5 가 설명하고, 정각 발화는 다른 파일이 본다).

### 7. 참고 (판정 미포함)

1. **미머지 티켓 32(`t32-app-subscription-purchase-paywall`, `8a1557a`)와의 코드 충돌 — 통합 작업 지시용.** 코디네이터 답(ask, 2026-10-15): "참고로 둬라. 33 은 main(31) 기준 단독 정확성으로 판정. 32 를 먼저 머지한 뒤 33 이 rebase 해 observedAt 규칙을 32 의 `Entitlement?` 위에 포팅하는 통합 작업을 따로 내고 다시 리뷰." 충돌 목록:
   - `mobile/lib/api/api_models.dart` — 32 가 `Entitlement(active, until, status, source, nextCheckAt)` + `_parseInstant`(`toUtc()`) 를 더했고, 33 도 같은 이름 `Entitlement(active, nextCheckAt)` 를 더함 → 클래스 중복. 33 의 `MyStats.entitlement`(required) 는 32 의 `Entitlement` 로 갈아끼우면 됨(32 의 `MyStats` 에는 `entitlement` 없음 — "33 이 더한다" 주석).
   - `mobile/lib/subscription/entitlement_provider.dart` — 32: `Notifier<Entitlement?>`, `update(Entitlement entitlement)` 포지셔널. 33: `Notifier<bool?>`, `update({required bool active, DateTime? observedAt})` + `clear()` + `_observedAt`. → 33 의 `observedAt`·`clear()` 를 32 의 `Entitlement?` 상태 위로 포팅(`update(Entitlement, {DateTime? observedAt})`).
   - `mobile/lib/ads/ad_providers.dart` — 32 가 `entitled: ref.watch(entitlementProvider)?.active` 로 바꿈. 33 의 `entitlement_refresh.dart:107` `entitled.update(active: entitlement.active, observedAt: _departedAt)` → `update(entitlement, observedAt: …)` 로.
   - `mobile/lib/app.dart` — 양쪽 다 `ref..listen(notificationSyncProvider)..listen(<자기 provider>)` 캐스케이드로 바꿈 → 세 줄 합치기.
   - `mobile/test/fakes/fake_api_client.dart` — 32 가 verify 쪽 가짜를, 33 이 `fakeMyStats(entitled:, nextCheckAt:)`·`fetchMyStatsGate` 를 더함 → 33 의 `fakeMyStats` 가 32 의 `Entitlement` 를 만들게.
   - `mobile/test/ads/entitlement_test.dart`·`mobile/test/api/api_models_test.dart` — 양쪽 다 수정. 33 의 "관측 시각" 5개는 `update(Entitlement(active: …), observedAt: …)` 로.
   - 33 의 `entitlement_refresh_test.dart`·`entitlement_refresh_ads_test.dart` 의 `update(active: true)`(구매 흉내) 호출도 32 시그니처로.
   - 증거 문서 §4 "32 는 코드 변경 없음" 은 main(31) 기준 서술이며 32 브랜치 기준으론 성립하지 않는다 — 통합 때 README "33." 의 같은 문장도 손봐야 한다.
2. `Entitlement.fromJson` 이 `json['entitlement'] as Map` 을 필수로 읽는다 — 서버(main, 티켓 13)는 늘 싣고 `tests/` 도 그렇다. 옛 서버에 새 앱이 붙는 배포 순서는 없으므로 결함으로 올리지 않는다(앱 배포 전 서버 배포가 전제).
3. 타이머 조회 401 은 5분마다 재시도 고리가 된다(값은 유지). 29 의 토큰 재발급을 공통 경로로 올리는 건 별도 티켓 거리.
4. 취향: `EntitlementRefreshController` 의 상태(`DateTime?` = 발화 시각)는 테스트용 관측 창 역할이 커서 이름만 보면 권한처럼 읽힐 수 있다 — 바꿀 필요는 없다.

판정: PASS

## 라운드 2 (통합 라운드)

**브랜치:** `dosaem/t33-app-entitlement-refresh-timer` (`2d8fdc9`, main 위로 rebase 됨 — `git merge-base main HEAD == main`) · **기준:** 로컬 `main`(`8de470b`, 티켓 32 머지) · **날짜:** 2026-10-15 · **리뷰어:** Fable (Final Reviewer)

### 0. 한 줄 요약

이전 결함 3건(D-33-1·D-33-2·D-32-6) 모두 **FIXED** — 각각 수정만 되돌리는 뮤테이션을 직접 돌려 새 테스트가 red 로 돌아오는 것을 확인했다. 32 의 구매 흐름은 통합 뒤에도 호출부가 그대로이고(`purchase_controller.dart` 의 diff 는 완료 게이트 한 줄뿐) 32 테스트 포함 782개가 통과한다. 새 결함은 MINOR 1건(D-33-3 — 세션 중 구매로 생긴 권한에는 타이머가 안 걸린다, 임시 테스트로 재현). BLOCKER·MAJOR 없음.

### 1. 직접 돌린 것 (증거 문서를 믿지 않고 재실행)

| 항목 | 명령 | 결과 |
|---|---|---|
| Flutter 정적 검사 | `cd mobile && flutter analyze` | `No issues found!`, **exit 0** (info 포함 0건) |
| Flutter 포맷 | `dart format --output=none --set-exit-if-changed lib/ test/ integration_test/` | `0 changed`, exit 0 |
| Flutter 전체 테스트 | `cd mobile && flutter test` | `+782: All tests passed!` (증거 §D 와 같은 782 = 통합 직후 779 + 이 라운드 3개) |
| Android 디버그 빌드 (코디네이터 요청) | `cd mobile && flutter build apk --debug` | `✓ Built build/app/outputs/flutter-apk/app-debug.apk`, **exit 0**. 확인 뒤 `mobile/build`·`mobile/android/.kotlin` 삭제, `git status` 깨끗함 |
| 뮤테이션 ① | `my_stats_controller.dart:63` `_observedAt = departedAt;` 한 줄 제거 → `flutter test test/subscription/entitlement_refresh_test.dart` | **-3**: "32 의 구매 응답이 뒤늦은 옛 조회에 덮이지 않는다"·"타이머 조회와 복귀 조회가 겹쳐도 구매를 덮지 않는다"·"플레이 결과 재조회가 뒤늦게 와도 구매를 덮지 않는다" 실패. 파일은 `git checkout` 으로 복원 |
| 뮤테이션 ② | `purchase_controller.dart:367` 게이트를 `entitlement.status != null` 로 되돌림 → `flutter test test/subscription/purchase_controller_test.dart` | **-1**: "앱이 모르는 상태 라벨이 와도 행이 있으면 완료한다 (D-32-6)" 만 실패, 나머지 28개 통과. 파일 복원 |
| 백엔드 lint | `uv run ruff check .` | `All checks passed!`, exit 0 |
| 마이그레이션 head | `./scripts/check_migration_heads.sh` (`flask db heads`) | `b1c7d4e0a932 (head)` 1개 — 이 티켓은 리비전을 만들지 않음(`migrations/` diff 0) |
| 백엔드 테스트 | `uv run pytest -q` (전용 자원) | `1509 passed in 993.93s (0:16:33)`, exit 0 — 재실행 없이 통과(증거 §D 와 같은 1509) |

백엔드는 구현 워커가 만들어 둔 전용 자원을 그대로 썼다 — `TEST_DATABASE_URL` 의 DB 이름 `chosung_daily_test_t33`, `TEST_REDIS_URL` 은 `redis://127.0.0.1:6379/7`, `TEST_MIGRATION_DATABASE_URL` 의 DB 이름 `chosung_daily_test_t33_migrations`(세 자원 모두 실행 전 ping 으로 접속 확인). 접속 형식은 `app/config.py` `TestingConfig` 기본값에서 DB 이름만 바꿨고 인증 값은 적지 않는다. 새 DB 를 만들지 않았고 기본 DB 로 전환하지 않았다. 다른 워크트리(t39)의 pytest 가 동시에 돌고 있었지만 각자 전용 DB 라 겹치지 않는다. `app/`·`web/`·`tests/`·`migrations/`·`.env.example` 의 main 대비 diff 는 비어 있다(백엔드 실행은 회귀 확인용).

### 2. 이전 결함 판정

| ID | 라운드 1 심각도 | 판정 | 근거 |
|---|---|---|---|
| D-33-1 | MINOR | **FIXED** | 떠난 시각이 컨트롤러 필드(`_departedAt`)에서 `MyStatsNotifier.refresh()`/`adopt()` 의 **지역 변수** `departedAt`(`my_stats_controller.dart:54, :97`)로 옮겨졌고, 세대 검사를 통과해 커밋하는 조회만 `_observedAt = departedAt`(`:63, :104`)을 남긴다. 컨트롤러는 `observedAt` getter(`:34`)를 읽어 넘기기만 한다(`entitlement_refresh.dart:114`). 라운드 1 의 재현 순서(타이머 조회 A in-flight → 홈 → 복귀로 B → 구매 → 둘 다 도착)가 테스트 "타이머 조회와 복귀 조회가 겹쳐도 구매를 덮지 않는다"(`entitlement_refresh_test.dart:413`)로 고정됐고, 뮤테이션 ① 에서 red 로 돌아온다. 코드 경로 확인: A 가 먼저 풀리면 `generation != _generation` 으로 커밋도 시각도 안 남기고, B 는 자기 `departedAt`(구매 전)으로 커밋 → `EntitlementNotifier.update` 의 `!observedAt.isAfter(previous)`(`entitlement_provider.dart:45`)에 걸려 구매(지금 관측)를 못 덮는다 |
| D-33-2 | MINOR | **FIXED** | 같은 수정으로 닫힘 — 떠난 시각을 **부른 쪽이 아니라 `MyStatsNotifier`** 가 찍으므로 플레이 결과 재조회(25·26)가 직접 부른 `refresh()` 에도 시각이 붙는다. 라운드 1 재현 순서(gate 걸고 `myStatsProvider.notifier.refresh()` → 5초 뒤 구매 → gate 해제)가 테스트 "플레이 결과 재조회가 뒤늦게 와도 구매를 덮지 않는다"(`:444`)로 고정, 뮤테이션 ① 에서 red. 시각이 null 인 경우는 이제 시작 응답(`build()` `:45`)·`discard()`(`:78`)·`adopt(stats)`(방금 받은 값)뿐이고 셋 다 "지금" 이 맞다 |
| D-32-6 (32 리뷰 라운드 3) | MINOR | **FIXED** | `purchase_controller.dart:367` 게이트가 `entitlement.nextCheckAt != null` 로 바뀜. 서버 계약을 직접 확인: `Subscription.last_verified_at` 은 `nullable=False`(`app/models/subscription.py:58`), `build_entitlement` 는 행이 있으면 `next_check_at = last_verified_at + 1h` 를 **늘** 채우고 행이 없으면 `NO_ENTITLEMENT`(다섯 칸 null)를 돌려주며(`app/services/entitlement.py`), `verify_receipt` 는 그 함수로 응답을 만든다(`app/services/subscription_service.py:51`). 즉 "행이 있는가" 와 정확히 같은 뜻이고 라벨 집합에 묶이지 않는다. 테스트(`purchase_controller_test.dart:547`)는 wire JSON `status: 'paused'` 를 `Entitlement.fromJson` 으로 넣어 `status == null` 을 먼저 단정하고 `completed` 1개를 본다 — 뮤테이션 ② 에서 red. 반대편(행 없음 → 완료 안 함)은 기존 테스트가 지킨다(`fakeEntitlement()` 기본값은 `status`·`nextCheckAt` 둘 다 null, `fake_api_client.dart:62`). 32 리뷰가 "참고 1" 에 적은 크로스 스토어 성질(Apple 행이 있으면 Play 토큰 verify 도 non-null)은 `status` 때와 같다 |

### 3. 티켓 체크박스별 판정 (통합 뒤 재확인)

| # | 체크박스 | 판정 | 근거 |
|---|---|---|---|
| 1 | 스케줄 순수 함수 + 경계·백그라운드·복귀 단위 테스트 | **충족** | `entitlement_schedule.dart` 변경 없음(라운드 1 그대로), `entitlement_schedule_test.dart` 9개 통과 |
| 2 | 시작·복귀·타이머 만료 시 `/me/stats` → 게이트 재평가, 배너 복구/제거 위젯 테스트 | **충족** | 시작 `entitlement_refresh.dart:65`(listen) + 한 틱 뒤 `_adopt`, 복귀 `:151`, 타이머 `:137`. 위젯 테스트 `entitlement_refresh_ads_test.dart` 3개(앱 트리 통째, `AdBannerSlot` findsNothing↔findsOne, `bannerWidths`/`bannerDisposals`) 통과 |
| 3 | 가짜 시계: 정확히 `next_check_at` 에 자동 호출 → 권한 없음 → 광고 상태 변경 | **충족** | "정확히 그 시각에 /me/stats 를 부르고 권한 해제를 반영한다" 통과 — 1h-1s 에서 호출 0, 1초 뒤 1 |
| 4 | 31 의 권한 Provider 를 쓴다(새 Provider 없음) — 32 의 verify 반영과 충돌 없음 | **충족** (32 머지 기준) | 값을 담는 provider 는 `entitlementProvider` 하나, 상태 타입은 32 의 `Entitlement?` 그대로. 33 은 `update(entitlement, {observedAt})`·`clear()` 를 **덧붙였을 뿐** 32 의 호출 `update(entitlement)` 는 한 글자도 안 바뀐다(`git diff main...HEAD -- mobile/lib/subscription/purchase_controller.dart` 의 코드 변경은 완료 게이트 한 줄). `ad_providers.dart` 는 diff 0. 32 테스트(purchase_controller 29개·subscription_state·paywall 등) 전부 782 안에서 통과 |
| 5 | README Flutter 절 "권한 재확인 타이머" 한 단락 | **충족** | `README.md:2721` `### 33.` 한 hunk(`@@ -2718,6 +2718,78 @@`), 31·32 소제목 뒤·"부하 테스트 요약" 앞. 이 라운드가 더한 두 단락("떠난 시각은 `MyStatsNotifier` 가"·"(32 에 걸친 수정)")도 `### 33.` 안이다 |

### 4. 코디네이터 메모 항목별 판단

1. **32 의 구매 흐름이 통합 후에도 그대로인가** — 위 표 4번. 호출부 무변경, 32 테스트 전부 통과. 32 의 `Entitlement`·`_parseInstant(toUtc)` 를 그대로 쓰고 33 의 중복 클래스는 지워졌다(`api_models.dart` diff 는 `MyStats.entitlement` 추가뿐).
2. **증거 §C 쌍 표에 빈 칸이 있는가** — 13쌍 모두 테스트가 지목돼 있고 각 테스트가 실제로 존재·통과한다. **빠진 쌍 하나**: "구매(verify) × 타이머 걸기" — 세션 중 구매로 **처음** 권한이 생긴 경우 verify 응답의 `next_check_at` 으로는 타이머가 안 걸린다(아래 D-33-3). 표의 1·2번은 "조회가 떠나 있는 동안의 구매" 만 다룬다.
3. **flutter analyze(info 포함) exit 0 · APK** — §1, 둘 다 exit 0 직접 확인.
4. **D-32-6 FIXED/REPEAT** — §2, FIXED.

### 5. 결함 목록

#### D-33-3 — MINOR — 세션 중 구매로 생긴 권한에는 재확인 타이머가 걸리지 않는다 (CONFIRMED, 재현함)

- **파일:** `mobile/lib/subscription/entitlement_refresh.dart:104-121` (`_applied` — `_nextCheckAt` 을 `/me/stats` 응답에서만 받는다), `:65` (`myStatsProvider` 만 듣고 `entitlementProvider` 는 듣지 않는다)
- **내용:** 타이머의 입력 `_nextCheckAt` 은 `/me/stats` 응답에서만 온다. 구독 행이 없는 게스트(시작 응답 `next_check_at: null` → 타이머 없음)가 **세션 중에 구매**하면 32 의 verify 응답(행 있음, `next_check_at` 포함)이 `entitlementProvider` 에 권한을 넣지만 이 컨트롤러는 그걸 듣지 않아 타이머가 그대로 없다. 그 뒤 백그라운드 복귀·플레이 결과 재조회(둘 다 `/me/stats`)가 오기 전까지는 포그라운드에 아무리 머물러도 `/me/stats` 를 다시 부르지 않는다. US 30c("앱을 쓰고 있는 구독자라면 최대 1시간 안에 확인")가 이 구독자에게는 다음 복귀/플레이까지 미뤄진다.
- **재현(입력 → 기대 vs 실제):** `entitlement_refresh_test.dart` 의 `start` 와 같은 컨테이너로 — 시작 `fakeMyStats()`(행 없음) → `entitlementProvider.notifier.update(fakeEntitlement(active: true, nextCheckAt: now+1h))`(구매 흉내) → `pump()` → 가짜 시계를 1시간씩 6번 흘림(`now += 1h; tester.pump(1h)`). **기대** `entitlementRefreshProvider != null`(타이머 걸림) 이고 `fetchMyStatsCalls > 0`. **실제** `entitlementRefreshProvider == null`, 호출 0. 리뷰 중 임시 테스트 파일(`test/subscription/zz_review_tmp_test.dart`)로 돌려 실패를 확인했고 파일은 지웠다(워크트리 clean).
- **피해 범위:** 트리거는 "세션 중 구매 + 같은 포그라운드 세션에서 환불/hold 확인 + 그 사이 백그라운드·플레이 없음". 창이 좁고 다음 복귀·플레이·재시작 중 하나에서 회복된다. 과금 방향(구독자가 광고를 안 봄)이라 사용자 손해는 없다 → MINOR.
- **고치는 방향(참고):** 컨트롤러가 `entitlementProvider` 도 `listen` 해 그 값의 `nextCheckAt` 으로 `_nextCheckAt` 을 갱신하고 `_arm()` 하거나(33 파일만 손댐), 32 가 verify 뒤 `myStatsProvider.refresh()` 를 떠나보내게 한다(32 파일·요청 1회 추가). 전자가 티켓 경계에 맞는다. 테스트는 위 재현 순서 그대로.

### 6. 보안·범위·공유 파일

- **보안:** 새 엔드포인트·입력·시크릿 없음. `/me/stats` 는 기존 Bearer 경로. 리뷰·증거 문서의 접속 문자열은 `…` 로 가려져 있고 테스트 토큰은 가짜다. 시크릿 값이 파일에 기록된 곳 없음.
- **데이터 손상:** 앱 로컬 상태만. 서버 쓰기 없음. D-32-6 수정은 acknowledge 가 **더 나가는** 방향(행이 있으면 완료)이고 행 없음(`NO_ENTITLEMENT`)은 여전히 막는다 — D-32-5 회귀 없음(테스트 "서버가 구독 행을 만들지 못한 응답에는 completePurchase 를 부르지 않는다" 통과).
- **범위:** 변경 20파일 — `mobile/` 16, `README.md`, 스펙 "미정 항목" 1블록, `review/` 2. 백엔드·웹·마이그레이션 0건. 32 쪽 파일 2개(`purchase_controller.dart`, `my_stats_controller.dart`)를 건드린 건 코디네이터가 이 라운드에 지시한 D-32-6 과 라운드 1 D-33-2 "고치는 방향" 이 지목한 자리라 범위 안이다. 기존 테스트 깨진 것 없음.
- **공유 파일 규칙:** README `### 33.` 한 hunk, 스펙 "미정 항목" 끝 `(티켓 33 반영)` 자기 블록 1개. `.env.example`·`docs/RELEASE.md`·API 표 미변경. `review/impl-review-33.md` 는 라운드 1 커밋(`38c9a6a`) 이후 구현 워커가 건드리지 않았다(`git diff 38c9a6a..HEAD -- review/impl-review-33.md` 0줄). 규칙 위반 없음.
- **테스트 품질:** 새 테스트 3개는 지연 Fake(`Completer`)·wire JSON 으로 순서를 직접 만들고, 뮤테이션 ①·② 로 각각 코드 변경에 민감함을 확인했다. `FakeApiClient.fetchMyStats` 가 응답을 **호출 시점** 값으로 잡는 변경(`fake_api_client.dart:328`)은 "늦게 도착한 옛 응답" 을 만들기 위한 것으로 기존 테스트 의미를 바꾸지 않는다. `fakeEntitlement` 의 "행이 있으면 `nextCheckAt` 도 있다" 기본값은 서버 짝과 일치하고, 그 때문에 타이머가 걸리는 `banner_slot_gate_test.dart` 에는 `clockProvider` 고정(`:59`)이 들어갔다. `entitled: true` 를 쓰면서 시계를 고정하지 않은 다른 테스트 5파일(ad_gate·result_interstitial·records_ad_privacy·today_tab_ads·subscription_state)은 `ChosungApp` 을 띄우지 않아 재확인 컨트롤러가 서지 않는다 — 벽시계 의존 없음.

### 7. 참고 (판정 미포함)

1. **기기 시계가 뒤로 가면 관측 시각 비교가 한동안 조회를 버린다.** `observedAt` 는 벽시계라, 구매(지금 관측 = T)를 넣은 뒤 사용자가 기기 시각을 T 이전으로 돌리면 그 뒤 떠난 조회(`departedAt < T`)가 전부 `!isAfter` 로 떨어져 환불이 시계가 T 를 다시 지날 때까지 반영되지 않는다. 재시작하면 `build()` 가 시각을 비워(`my_stats_controller.dart:45`) 시작 응답이 이긴다. 수동 시계 조작은 지원 시나리오가 아니고 서버 판정은 그대로라 결함으로 올리지 않는다 — 코디네이터가 승인한 설계(관측 시각)의 성질이다.
2. 서버 `build_entitlement` 는 만료 ±24h 구간에서도 `next_check_at = last_verified_at + 1h` 를 준다(5분 상한은 서버 안쪽, 스펙 미정 18 "응답에 싣지 않는다"). 앱 타이머는 그 값을 따르므로 스펙대로다 — 그 구간의 갱신 반영이 앱 쪽에서는 최대 1시간이지만 24h 유예가 권한을 유지해 광고가 켜지지 않는다. 결함 아님.
3. 타이머 조회 401 은 5분마다 재시도 고리(값 유지) — 라운드 1 참고 3 그대로.
4. `Entitlement.fromJson` 이 `json['entitlement']` 를 필수로 읽는다 — 라운드 1 참고 2 그대로(서버가 늘 싣고 앱 배포 전 서버 배포가 전제).

판정: PASS
