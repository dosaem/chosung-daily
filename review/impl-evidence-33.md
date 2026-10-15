# 티켓 33 구현 증거 — 구독 권한 반영: 시작/복귀 `/me/stats`·`next_check_at` 타이머·권한 해제 시 광고 복구

**브랜치:** `dosaem/t33-app-entitlement-refresh-timer` · **날짜:** 2026-10-15
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 33.` + 스펙 "미정 항목"
자기 줄 1개. 백엔드·웹·마이그레이션은 한 줄도 건드리지 않았다
(`app/`·`web/`·`migrations/` 변경 0건 — 이 티켓은 마이그레이션을 만들지 않는다.
`/me/stats` 의 `entitlement` 는 티켓 13 이 이미 내려보내고 있다).

## 0. 한 줄 요약

앱이 `/me/stats` 응답의 `entitlement` 를 31 의 `entitlementProvider` 에 넣고,
포그라운드에 머무는 동안 `entitlement.next_check_at` 에 타이머를 걸어 그 **정각**에
다시 불러 광고 게이트를 재평가한다. 백그라운드에서는 타이머를 멈추고 복귀 때 즉시
부른다. 판정("언제 부를지")은 순수 함수 하나이고, 호출은 `myStatsProvider` 가 한다
(요청이 두 번 나가지 않고 계정 경계 검사를 베끼지 않는다). 권한을 넣을 때 **관측
시각**을 같이 넘겨 떠난 조회가 그 사이 들어온 구매 응답(32)을 덮지 않게 했다(§4).
앱 테스트 **707개 통과**(이 티켓이 더한 건 **34개**), `flutter analyze` 0건 ·
`dart format` 변경 없음 · `flutter build apk --debug` exit 0 · 백엔드
`ruff check` 통과 · `pytest` 1509개 통과(§7).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| 권한 새로고침 스케줄 **순수 함수** `(지금, next_check_at, foreground) → 시각 \| 없음`. 단위 테스트: 경계 포함(`now >= next_check_at`, 미정 19), 백그라운드 정지, 복귀 즉시 | `test/subscription/entitlement_schedule_test.dart` **9개** — "정확히 그 시각이면 지금 부른다 (경계 포함, 미정 19)", "1초 전이면 아직 그 시각을 기다린다", "이미 지났으면 지금 부른다"(= 복귀 즉시), "백그라운드 … 아직 남았어도/이미 지났어도"(정지 2종), "구독 행이 없는 게스트는 부를 일이 없다", 서버 UTC × 기기 로컬 2종 | §3.1 |
| 앱 **시작**·**복귀**·**타이머 만료** 시 `GET /me/stats` → `entitlement` → 31 의 게이트 재평가 | `test/subscription/entitlement_refresh_test.dart` — 시작 3개("시작 응답의 권한이 광고 게이트에 들어간다" 등), 복귀 3개("복귀하면 next_check_at 을 기다리지 않고 바로 묻는다", "복귀 뒤에는 새 응답의 시각으로 타이머가 다시 돈다", "첫 알림이 paused 로 바로 와도 멈추고 다시 돈다"), 타이머 5개 | §3.2 |
| 권한 사라지면 **배너 슬롯 복구·전면 재개**, 생기면 제거 (**위젯 테스트**) | `test/subscription/entitlement_refresh_ads_test.dart` **3개** — 앱 트리를 통째로 띄워 "권한이 사라지면 배너 슬롯이 돌아오고 배너를 다시 요청한다"(`AdBannerSlot` findsOne + `bannerWidths` 1), "권한이 생기면 배너 슬롯이 사라지고 배너를 버린다"(findsNothing + `bannerDisposals` 1). 전면 재개는 `adGateProvider.canLoadAds` 로 `entitlement_refresh_test.dart` "정확히 그 시각에 …" 가 본다 | §3.3 |
| **가짜 시계 테스트**: 포그라운드에 둔 채 `next_check_at` **정확히 그 시각**에 `/me/stats` 가 자동 호출되고 Fake 가 권한 없음을 돌려주면 광고 상태가 바뀐다 | `test/subscription/entitlement_refresh_test.dart` "정확히 그 시각에 /me/stats 를 부르고 권한 해제를 반영한다" — `clockProvider` 를 고정 시각으로 덮고 `tester.pump(1시간 - 1초)` 에서 `fetchMyStatsCalls == 0`, 남은 1초를 흘리면 `== 1` + `showsBannerSlot` false→true + `canLoadAds` true | §3.4 |
| 32 의 verify 반영과 충돌하지 않게 **31 이 만든 권한 Provider 를 쓴다**(새 Provider 를 만들지 않는다) | `entitlement_refresh_test.dart` 그룹 "32 의 구매 응답과 같은 자리를 쓴다" 2개(구매가 넣은 `update(active: true)` 를 **구매 뒤에 떠난** `/me/stats` 가 덮고, 계정이 바뀌면 옛 계정 권한을 버린다) + 그룹 "떠난 조회 × 그 사이 끼어든 경로" 3개(지연 Fake) + `test/ads/entitlement_test.dart` 그룹 "관측 시각(observedAt)" 5개. 권한 상태 provider 는 `lib/subscription/entitlement_provider.dart`(31) 그대로이고 **값을 담는 새 provider 는 없다** | §2·§4 |
| README Flutter 절에 "권한 재확인 타이머" 한 단락 | `README.md` "### 33. 권한 재확인 타이머 — 사건 셋, 순수 함수 하나, 갱신 자리 하나"(설계 판단 절 끝, 공통 규칙대로 자기 번호 소제목) | §6 |

## 2. 무엇을 어디에 뒀는가

| 파일 | 하는 일 |
|---|---|
| `lib/subscription/entitlement_schedule.dart` **(신규)** | 순수 함수 `nextEntitlementCheck(now, nextCheckAt, foreground)` — 다음 호출 시각 또는 `null`. Riverpod·Flutter import 가 없다 |
| `lib/subscription/entitlement_refresh.dart` **(신규)** | `EntitlementRefreshController`(`Notifier<DateTime?>` — 상태 = 지금 걸린 타이머의 발화 시각) + `entitlementRefreshProvider`. 앱 수명·`AppLifecycleListener`·`Timer`·`myStatsProvider` 구독을 여기 모았다 |
| `lib/api/api_models.dart` | `Entitlement`(`active`, `nextCheckAt`) + `MyStats.entitlement`. `until`·`status`·`source` 는 이 티켓이 쓰지 않아 읽지 않는다(구독 화면 32 가 더한다) |
| `lib/subscription/entitlement_provider.dart` | 31 의 provider 에 둘만 더했다 — `clear()`(= "아직 모른다" 로 되돌리기, 계정 경계에서 쓴다)와 `update` 의 선택 인자 `observedAt`(관측 시각 비교, §4). 상태 타입은 `bool?` 그대로다 |
| `lib/app.dart` | `ChosungApp` 이 `entitlementRefreshProvider` 를 `listen` 한다(알림 동기화와 같은 자리·같은 이유) |
| `test/fakes/fake_api_client.dart` | `fakeMyStats(entitled:, nextCheckAt:)` — 기본값은 "구독 없는 게스트"(타이머 안 걸림). `fetchMyStatsGate`(`Completer`) — 조회를 떠난 상태로 붙잡아 두는 자리(§4) |

**호출 경로 한 줄.** `StartupNotifier`(시작) · `AppLifecycleListener.onShow/onResume`
(복귀) · `Timer`(만료) → `myStatsProvider`(= `/me/stats`) → 이 컨트롤러의 구독 →
`entitlementProvider.update/clear` → `adGateProvider`(31) → 배너 슬롯·전면·힌트.

**시작 때 `/me/stats` 를 다시 부르지 않는다.** 스플래시가 이미 그 응답을 기다리고
(`StartupNotifier._fetchStats`) `myStatsProvider` 가 그걸 들고 있으므로, 같은 요청을
한 번 더 쏘지 않고 그 값을 그대로 반영한다("시작 때 `/me/stats` 로 권한을 읽는다"는
스펙 §A.8 문구를 **요청 수를 늘리지 않고** 만족시키는 쪽). 증거: "시작 응답의 권한이
광고 게이트에 들어간다" 가 `fetchMyStatsCalls == 0` 을 같이 못 박는다.

## 3. 실행 출력 (앱)

### 3.1 순수 함수 단위 테스트

```
$ cd mobile && flutter test test/subscription/entitlement_schedule_test.dart
00:01 +9: All tests passed!
```

### 3.2~3.4 컨트롤러·가짜 시계·위젯 테스트

```
$ cd mobile && flutter test test/subscription/ test/ads/
00:10 +79: All tests passed!
```
(`test/subscription/` 29 = schedule 9 + refresh 17 + refresh_ads 3,
`test/ads/` 50 — 그중 5개가 이 티켓이 더한 "관측 시각" 그룹)

### 3.5 전체 앱 테스트 · analyze · format

```
$ cd mobile && flutter test
00:50 +707: All tests passed!

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 5.2s)

$ cd mobile && dart format lib/ test/ integration_test/
Formatted 187 files (0 changed) in 0.36 seconds.
```

### 3.6 Android 디버그 빌드

네이티브 플러그인을 더하지 않았지만(Dart·문서만 바뀜) 구현 메모 3)대로 확인했다.
확인 뒤 `mobile/build` 는 지웠다(디스크).

```
$ cd mobile && flutter build apk --debug
Running Gradle task 'assembleDebug'...
Note: Some input files use or override a deprecated API.
Note: Recompile with -Xlint:deprecation for details.
Running Gradle task 'assembleDebug'...                            132.0s
✓ Built build/app/outputs/flutter-apk/app-debug.apk
apk exit=0
```

## 4. 비동기 경로 쌍 표 (구현 메모 2)

겹칠 수 있는 두 경로를 칸으로 놓고, **조회를 떠난 상태로 붙잡는 지연 Fake**
(`FakeApiClient.fetchMyStatsGate`, `Completer`)로 순서를 직접 만들어 고정했다.
세로축은 **이 티켓이 떠나보내는 `/me/stats` 조회**(타이머·복귀)고, 가로축은 그
조회가 떠난 **뒤에** 끼어드는 사건이다.

| 떠난 조회 × 그 사이 끼어든 사건 | 무엇이 틀어질 수 있나 | 어떻게 막았나 | 고정한 테스트 |
|---|---|---|---|
| **구매 응답(32 verify)** | 떠난 조회는 **구매 전** 사실(active:false, `next_check_at:null`)을 들고 있다. 그대로 쓰면 돈 낸 사용자가 세션 내내 광고를 본다(타이머도 안 걸린다) | `update(active:, observedAt:)` 에 **조회를 떠난 시각**을 찍고, 그보다 뒤에 관측한 사실만 이긴다. 시각 없는 갱신(구매·복원)은 "지금" 이라 늘 이긴다 → 32 는 코드 변경 없음 | `entitlement_refresh_test.dart` "32 의 구매 응답이 뒤늦은 옛 조회에 덮이지 않는다" (지연 Fake) |
| **구매 → 그 뒤에 떠난 조회** (반대 방향) | 과하게 막으면 환불·hold 가 영원히 반영되지 않는다(US 30c 위반) | 구매 뒤에 떠난 조회는 관측 시각이 더 뒤라 **그대로 이긴다** | `entitlement_refresh_test.dart` "구매 뒤에 떠난 조회는 환불을 그대로 반영한다" (지연 Fake) |
| **계정 전환·연결·삭제(29)** | 떠난 조회가 **남의 계정** 권한을 새 계정에 쓴다 | 29 의 `accountEpochProvider`·`fetchIfSameAccount` 를 그대로 쓴다(`myStatsProvider.refresh` 안에 있다) — 세대가 다르면 응답을 상태에 쓰지 않고, `discard` 가 오면 권한도 `clear()` 로 "아직 모른다" 가 된다 | `entitlement_refresh_test.dart` "계정이 바뀌면 떠난 조회의 권한을 쓰지 않는다"(지연 Fake) + "계정이 바뀌면 옛 계정 권한을 버린다" |
| **앱이 백그라운드로** | 응답이 돌아왔을 때 타이머를 다시 걸면 안 보이는 앱이 계속 서버를 부른다 | 응답 반영 뒤 타이머를 **지금 상태로** 다시 건다 — 순수 함수가 백그라운드면 "없음" 을 돌려준다 | "백그라운드에서는 타이머가 멈춘다"(5시간을 흘려도 호출 0) |
| **조회 실패(서버 오류)** | 보던 권한을 잃거나, 반대로 타이머가 끊겨 세션 내내 다시 안 묻는다 | 실패는 저장값 유지(§A.8). 구독이 안 울리므로 `refresh()` 안에서 타이머를 다시 건다(5분 뒤) | "조회가 실패하면 보던 권한을 그대로 두고 5분 뒤 다시 묻는다" |
| **앱 재시작** | 시작 응답과 이 컨트롤러의 등장 순서에 따라 권한이 안 들어간다 | 구독(`ref.listen`)과 **이미 값이 있을 때의 한 틱 뒤 반영** 두 길로 같은 `_adopt` 를 거친다 | "시작 응답의 권한이 광고 게이트에 들어간다" + "시작이 끝난 뒤 응답이 와도 같은 길로 반영된다" |
| **내 조회 두 개(타이머 × 복귀)** | 늦게 도착한 옛 조회가 새 조회의 결과를 덮는다 | `MyStatsNotifier` 의 세대 번호(25·29)가 **나중에 떠난 조회만** 커밋한다 — 베끼지 않고 그걸 쓴다. 떠날 때 타이머는 늘 취소하므로 둘이 겹치는 입구는 "복귀 1회" 뿐이다 | 간접: "복귀 뒤에는 새 응답의 시각으로 타이머가 다시 돈다"(복귀 호출 1회 + 새 시각) |
| **플레이 결과 뒤 재조회(25·26)** | 그 조회도 `entitlement` 를 들고 오는데 떠난 시각을 모른다 | 내가 떠나보낸 조회가 아니면 `observedAt` 없이(= "지금") 반영한다. 결제 시트는 모달이라 **제출과 구매가 겹치는 입구가 없다** — 겹친다면 그 경로를 소유한 티켓이 떠난 시각을 들고 와야 한다(아래 §7-9 한계) | `test/screens/play_result_refresh_test.dart`(기존, 회귀) |

관측 시각 규칙 자체는 `test/ads/entitlement_test.dart` 그룹 "관측 시각(observedAt)"
5개가 따로 고정한다 — 시각 없는 갱신은 늘 이김 · 더 오래된 관측은 버림 · **같은
시각도 버림**(떠난 시각은 묵음의 하한일 뿐이라 동시각을 이기게 두면 막으려던 그
순서가 통과한다) · 더 뒤에 관측한 사실은 반영 · 계정 경계에서 시각도 버림.

**코디네이터 확정(2026-10-15).** 이 칸을 혼자 정하지 않고 `orca orchestration ask`
로 물었다(32 가 동시 진행 중이고 두 티켓이 같은 파일을 건드린다). 답: "A 로 가라.
관측 시각은 벽시계가 아니라 `clockProvider` 에서 읽고 '조회를 떠난 시각' 으로
찍어라. `observedAt` 없는 `update` 는 '지금' 으로 보고 항상 이기게 — 32 는 코드
변경 없이 그대로 동작해야 한다. 두 방향 다 지연 Fake 로 고정해라. 32 에도 이 변경을
알린다."

## 5. 가짜 시계를 어떻게 돌렸나 (그리고 어디서 못 돌렸나)

`testWidgets` 본문은 가짜 비동기 구역에서 돌아 `tester.pump(간격)` 이 **시간을
건너뛰며 `Timer` 를 터뜨린다**. 그래서 1시간짜리 타이머를 실제로 기다리지 않고
"정확히 `next_check_at`" 을 재현할 수 있다. `clockProvider`(22 가 테스트용으로
만든 자리)를 고정 시각으로 덮고, 타이머를 흘릴 때 그 변수도 같이 옮긴다
(`advance()`).

**앱 트리를 띄우는 테스트에서는 타이머를 터뜨리지 못한다.** `ChosungApp` 을
띄우려면 `tester.runAsync`(실제 비동기)가 필요하고(`easy_localization` 이 번역
자산을 읽는다) 그 구역에서 만들어진 `Timer` 는 `tester.pump(간격)` 이 건드리지
못한다 — 실제로 그 경로를 먼저 시도했고 타이머가 깨지 않는 것을 확인했다. 그래서
역할을 갈랐다: **타이머가 정각에 깨는지**는 앱 트리 없이 가짜 시계로
(`entitlement_refresh_test.dart`), **깼을 때 화면이 바뀌는지**는 앱 트리를 띄워
타이머가 깨서 하는 일(`refresh()`)을 그대로 불러
(`entitlement_refresh_ads_test.dart`) 본다. 둘 다 같은 코드 경로다.

## 6. 문서 · 공통 파일

| 파일 | 더한 것 |
|---|---|
| `README.md` | 설계 판단 절 끝에 `### 33. 권한 재확인 타이머 — 사건 셋, 순수 함수 하나, 갱신 자리 하나`(Flutter) |
| `.scratch/store-launch/spec.md` | "미정 항목" 끝에 `- (티켓 33 반영) 미정 19 의 앱 쪽 확정 …` 자기 줄 1개 |

`.env.example`·`docs/RELEASE.md`·API 표는 건드릴 게 없다 — 새 설정값·사람 작업·
엔드포인트가 없다(`/me/stats` 는 13 이 이미 표에 적었다).

## 7. 백엔드 (변경 0건, 회귀 확인용)

전용 자원으로 돌렸다: `TEST_DATABASE_URL=…/chosung_daily_test_t33`,
`TEST_REDIS_URL=redis://127.0.0.1:6379/7`,
`TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t33_migrations`.

```
$ TEST_DATABASE_URL=… TEST_REDIS_URL=… TEST_MIGRATION_DATABASE_URL=… \
  uv run ruff check . && ./scripts/check_migration_heads.sh && uv run pytest -q
All checks passed!
ruff exit=0
b1c7d4e0a932 (head)
OK: Alembic head 1개
heads exit=0
........................................................................ [ 95%]
.....................................................................    [100%]
1509 passed in 1472.34s (0:24:32)
pytest exit=0
```

마이그레이션 head 는 1개 그대로다(이 티켓은 리비전을 만들지 않았다 —
`b1c7d4e0a932` 는 선행 티켓의 head).

**rebase.** 로컬 `main`(`4afda89`, 티켓 31 머지) 위에서 작업했고 `git rebase main`
은 "up to date"(옮길 커밋 없음)였다 — 위 실행들은 모두 머지될 트리 그대로다.
확인 사살로 커밋 뒤에 한 번 더 돌렸다: `flutter analyze` 0건 ·
`flutter test` 707 passed · `dart format` 0 changed.

## 8. 설계 판단 · 알려진 한계

1. **이미 지난 `next_check_at` 에 하한 5분.** 서버는 스토어 조회 실패나 재조회
   대상이 아닌 행(`expired`·`revoked`)에 `last_verified_at` 을 올리지 않아
   `next_check_at` 이 계속 과거로 온다. 순수 함수의 "지났으니 지금" 을 그대로
   따르면 응답이 다음 호출을 부르는 **고리**가 돼 포그라운드 내내 `/me/stats` 를
   때린다. 하한은 컨트롤러에 뒀다 — "방금 불렀다" 를 아는 건 컨트롤러뿐이고,
   순수 함수는 티켓이 적은 입력 셋을 그대로 유지한다. 테스트: "이미 지난
   next_check_at 은 고리가 되지 않고 5분 뒤다"(5분마다 한 번씩만 부름).
   스펙 "미정 항목" 에 기록.
2. **복귀는 `next_check_at` 과 무관하게 무조건 부른다**(스펙 §A.8 "앱은 시작·
   포그라운드 복귀 때 `/me/stats` 를 부르고"). 떠나 있던 사이 타이머가 멈춰
   있었기 때문이다. 순수 함수의 "지났으니 지금" 은 그 뒤 다시 걸 때 쓰인다.
3. **앱 상태 콜백을 두 쌍 듣는다**(`onShow`+`onResume`, `onHide`+`onPause`).
   `AppLifecycleListener` 는 직전 상태로 콜백을 고르고 직전 상태를 모르면
   (컨트롤러가 선 뒤 첫 알림) 나가는 길에 둘 중 하나만 온다. 같은 값은
   걸러내므로 둘 다 와도 한 번이다. 테스트: "첫 알림이 paused 로 바로 와도
   멈추고 다시 돈다".
4. **계정 경계에서 권한을 버린다.** `myStatsProvider` 가 숫자를 버리면
   (`discard` — 연결·전환·삭제, 티켓 29) 권한도 `clear()` 로 "아직 모른다" 로
   되돌리고 타이머를 끊는다. 게이트는 null 을 비구독자로 다루므로(31) 결과는
   "광고 있음" 이고, 새 계정의 `/me/stats` 가 오면 그 값으로 다시 선다.
5. **시작 응답을 `build` 안에서 바로 반영하지 못한다.** Riverpod 3 은 provider
   초기화 중에 다른 provider 를 쓰는 것을 막는다(`Providers are not allowed to
   modify other providers during their initialization` — 실제로 그 단정에
   부딪혔다). 실제 앱에서는 시작 응답이 컨트롤러보다 늦게 와서 구독이 받지만,
   순서에 기대지 않으려고 **이미 값이 있을 때만** 한 틱 뒤로 미뤄 같은 길로
   반영한다(`scheduleMicrotask`).
6. **조회 실패는 저장값 유지**(스펙 §A.8). 실패한 `/me/stats` 는
   `MyStatsNotifier` 가 보던 값을 그대로 두므로 권한도 그대로고, 타이머는
   5분 뒤로 다시 건다(실패하면 구독이 울리지 않아 `refresh()` 안에서 다시
   거는 자리가 따로 필요했다). 테스트: "조회가 실패하면 보던 권한을 그대로 두고
   5분 뒤 다시 묻는다".
7. **한계 — 백그라운드 감지 없음.** 앱이 백그라운드에 있는 동안은 권한을 다시
   확인하지 않는다(스펙 그대로: 복귀 때 즉시 1회). 백그라운드 fetch·푸시는
   범위 밖이고 웹훅은 미정 1 이다.
8. **관측 시각은 `clockProvider` 에서 읽는다**(구현 메모 5). 기기 시계가
   뒤로 가면(사용자가 시간을 바꾸면) 조회 하나가 "오래된 관측" 으로 버려질 수
   있는데, 그때 잃는 건 그 한 번의 갱신이고 다음 타이머·복귀가 고친다.
   앱에서 고른 쪽은 **단조 시계가 아니라 테스트가 고정할 수 있는 시계**다 —
   재확인 자체가 서버 시각(`next_check_at`)과 기기 시각을 비교하는 일이라
   두 시계를 섞지 않는 게 더 중요했다.
9. **한계 — 플레이 결과 뒤 재조회는 떠난 시각을 모른다.** 그 `/me/stats` 도
   `entitlement` 를 들고 오지만 떠난 시각은 그 경로(25·26)만 안다. 지금은
   "지금 관측" 으로 다루므로, 제출 재조회가 떠난 뒤 구매가 끝나면 같은 부류의
   역전이 가능하다 — 다만 결제 시트가 모달이라 제출과 구매가 겹치는 입구가
   없다. 겹치게 되면 `MyStatsNotifier` 가 떠난 시각을 들고 오게 고치는 쪽이
   맞고, 그건 그 provider 를 소유한 티켓의 일이다.
10. **한계 — 401 복구는 이 경로에 없다.** 타이머 조회가 401 이면
   `MyStatsNotifier.refresh` 가 값을 그대로 두고 끝난다(29·25 의 계약).
   게스트 재발급은 시작 경로(`StartupNotifier`)에만 있다 — 이 티켓에서 바꾸면
   두 티켓의 계약을 같이 건드리게 돼 그대로 뒀다.
