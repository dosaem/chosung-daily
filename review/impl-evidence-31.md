# 티켓 31 구현 증거 — 광고 UMP/ATT 게이트·배너 슬롯·전면·보상형 힌트·구독자 무광고 힌트·광고 개인정보 설정

**브랜치:** `dosaem/t31-app-ads-gate-banner-interstitial-rewarded` · **날짜:** 2026-10-15
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 31.` · `docs/RELEASE.md`
`### 31.` · 스펙 "미정 항목" 자기 줄 1개. 백엔드·웹은 한 줄도 건드리지 않았다
(`app/`·`web/`·`migrations/` 변경 0건 — 이 티켓은 마이그레이션을 만들지 않는다).

## 0. 한 줄 요약

앱 시작마다 UMP 동의를 확인해(iOS 는 28 의 ATT 결과 뒤) `canRequestAds` 일 때만 광고
SDK 를 초기화하고, 배너는 탭 바 아래 예약 슬롯에 콘텐츠 열 폭으로 뜨며(구독자는 슬롯
자체 제거), 전면은 결과 시트를 **닫은 뒤** 퍼즐당 1회·첫 제출 전 금지, 보상형을 끝까지
보면 힌트가 열리고 구독자는 광고 없이 같은 호출을 쓴다. EEA 면 S4 에 "광고 개인정보
설정" 행이 생긴다. 앱 테스트 **457개 통과**(이 티켓이 더한 건 59개, 골든 5장 갱신),
`flutter analyze` 0건 · `dart format` 변경 없음 · 백엔드 `ruff check` 통과 ·
`pytest` 1403개 통과(§6).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| ApiClient 에 `POST /puzzles/today/hint-unlock` 추가(Dio + Fake) | `test/api/dio_api_client_test.dart` "POST /puzzles/today/hint-unlock 은 puzzle_id 를 보내고 힌트를 받는다"·"409 HINT_ALREADY_UNLOCKED…"·"409 ALREADY_FINISHED…"(3). Fake 는 `test/fakes/fake_api_client.dart`(`unlockedHintPuzzleIds`·`unlockHintError`·`unlockHintGate`) | §3.1 |
| 광고 게이트 순수 함수 — UMP 4종 + 구독자 + 오류 시 이번 세션 광고 없음·다음 시작 재시도 | `test/ads/ad_gate_test.dart`(10): UMP 4종(notRequired·obtained·required·unknown) + "UMP 를 아직 돌리지 않았으면" + 구독자 3종 + ATT 2종. 재시도는 `test/ads/ad_consent_test.dart` "다시 시작하면 동의를 다시 묻는다"·"동의 조회가 실패하면 실패 상태를 남기고 초기화하지 않는다" | §3.2 |
| UMP `requestConsentInfoUpdate` → 폼 → `canRequestAds` 후 `MobileAds.initialize`, iOS 는 ATT 결과 이후, 광고 ID `--dart-define`·디버그는 테스트 ID | `test/ads/ad_consent_test.dart`(6, iOS 2종 포함), `test/ads/ad_unit_ids_test.dart`(4), `test/config/bootstrap_test.dart` "시작 트리가 실제 광고 SDK 를 끼운다", `test/config/admob_native_config_test.dart`(4) | §3.3 |
| 배너: 22·24 슬롯에 로드(높이 고정, 실패해도 레이아웃 불변), 구독자는 슬롯 제거, 태블릿은 `bannerWidth` 로 어댑티브·폭 변경 시 재로드 1회 | `test/ads/banner_slot_gate_test.dart`(6) — "구독자는 배너 슬롯 자체가 없다", "로드가 실패해도 예약 높이는 그대로다", "태블릿은 rail 을 뺀 콘텐츠 열 폭으로 요청한다", **"회전으로 폭이 바뀌면 새 폭으로 한 번만 다시 요청한다"(높이 불변 + 재요청 1회 + 이전 배너 해제)**. 크기 선택은 `test/ads/banner_size_test.dart`(4) | §3.4 |
| 전면: 결과 시트 닫힘 후 퍼즐당 1회(로컬 플래그 puzzle_id 기준), 첫 제출 전 금지, 구독자 없음 | `test/ads/result_interstitial_test.dart`(8) + `test/screens/today_tab_ads_test.dart` 그룹 "전면 광고 타이밍"(4) — 실제 제출→시트→닫기 흐름에서 1회, "제출 없이 결과만 다시 열면 뜨지 않는다", "같은 퍼즐에서 시트를 다시 열어도 두 번은 없다", "구독자는 뜨지 않는다" | §3.5 |
| 보상형: 비구독자 "광고 보고 힌트 미리 보기" → 완료 콜백 → `hint-unlock`, **구독자는 "힌트 미리 보기" 로 광고 없이 바로**, 409 처리, 로드 실패 시 버튼 비활성 + 안내 | `test/screens/today_tab_ads_test.dart` 그룹 "보상형 힌트 미리 보기"(7) — 두 경로 + "광고를 못 띄우면 버튼이 잠기고 안내가 뜬다" + "광고를 중간에 닫으면 안내만 뜨고 다시 누를 수 있다" + "광고를 띄울 수 없는 세션이면 처음부터 비활성이다" + "409 이미 열림이면 재조회로 힌트를 보여준다" + "열지 못하면 보드는 그대로 두고 안내만 띄운다" | §3.6 |
| 27 의 S4 "광고 개인정보 설정" 자리: `privacyOptionsRequirementStatus == required` 일 때만 → `showPrivacyOptionsForm` | `test/screens/records_ad_privacy_test.dart`(3) — EEA 면 행 + 탭 시 폼 1회, 아니면 행 자체 없음, 구독자도 EEA 면 남음 | §3.7 |
| 광고 서비스 클래스는 인터페이스 + no-op 테스트 구현 | `lib/ads/ad_service.dart`(`AdService` + `NoopAdService`), 실제 구현 `lib/ads/google_ad_service.dart` 는 `main.dart` 만 끼운다(`bootstrap_test`). 테스트용 기록 가짜는 `test/fakes/fake_ad_service.dart` | §3.3 |
| 위젯 테스트: 게이트 상태별 배너 슬롯·전면 타이밍·보상형 → 힌트·구독자 힌트 무광고 | 위 네 줄(§3.4·§3.5·§3.6) | §3 |
| `audit.native`(태블릿 폭 포함) 통과 + audit 표 | §4 (5축 18/20, 태블릿 폭 744·1024·1366) | §4 |
| 목업 `e1_home`/`e7_home_dark`(HintCard·배너 슬롯) 대비 | §5 골든 3장 갱신(배너 슬롯 포함) + 차이 기록 | §5 |

## 2. 무엇을 어디에 뒀는가

| 파일 | 하는 일 |
|---|---|
| `lib/ads/ad_gate.dart` | `UmpStatus`(SDK `ConsentStatus` + privacy options 필요 여부) · `AdGate` · `adGateFor(ump, tracking, entitled)` 순수 함수 |
| `lib/ads/ad_service.dart` | `AdService` 인터페이스 · `LoadedBannerAd` · `NoopAdService`(provider 기본값) |
| `lib/ads/google_ad_service.dart` | 실제 `google_mobile_ads` 구현. UMP 콜백 API 를 Future 로 감싼다 |
| `lib/ads/ad_providers.dart` | `adServiceProvider`(기본 no-op) · `adConsentProvider`(시작마다 UMP) · `adGateProvider` |
| `lib/ads/ad_unit_ids.dart` | 포맷·플랫폼별 유닛 ID 선택(디버그·빈 값이면 Google 테스트 유닛) |
| `lib/ads/banner_size.dart` | 예약 높이에 들어가는 배너 크기 고르기(어댑티브 → 안 맞으면 고정) |
| `lib/ads/banner_ad_view.dart` | 슬롯 폭으로 배너 로드, 폭이 바뀌면 이전 배너를 버리고 1회 재로드 |
| `lib/ads/result_interstitial.dart` | 전면 타이밍(세션 플래그 + 퍼즐 플래그) |
| `lib/ads/interstitial_store.dart` | 퍼즐 플래그 저장소 인터페이스 + `shared_preferences` 구현 |
| `lib/subscription/entitlement_provider.dart` | 구독 권한 상태(초기 null). 32·33 이 갱신만 한다 |
| `lib/screens/home_shell.dart` | 게이트에 따라 슬롯을 두거나(빈 채로 예약) 지운다 |
| `lib/screens/today_tab.dart` | `_HintSlot`(보상형 → `hint-unlock`) · 결과 시트 닫힘 뒤 전면 |
| `lib/screens/records_tab.dart` | S4 "광고 개인정보 설정" 행(조건부) |
| `lib/puzzle/today_puzzle_controller.dart` | `unlockHint()` — 409 셋을 재조회로 받는다 |
| `lib/permissions/tracking_permission.dart` | `TrackingAuthorization.current()` 추가(두 번째 실행에서 시스템 선택 복원) |
| `lib/api/*` | `unlockHint` + 409 예외 두 개 |

설계 판단은 README "### 31." 에, 사람이 해야 하는 일(AdMob 앱 ID·유닛 6개·UMP 메시지·
실기기 확인)은 `docs/RELEASE.md` "### 31." 에 적었다.

## 3. 테스트

### 3.1 ApiClient (`test/api/dio_api_client_test.dart`, +3)
`/puzzles/today/hint-unlock` 이 Bearer 와 `{puzzle_id}` 를 보내고 `{hint}` 를 돌려주는
것, 409 `HINT_ALREADY_UNLOCKED`·`ALREADY_FINISHED` 가 각각 전용 예외로 오는 것.

### 3.2 게이트 순수 함수 (`test/ads/ad_gate_test.dart`, 10)
UMP `notRequired`/`obtained` → 로드 가능, `required`(폼 뒤에도 미동의)·`unknown`(조회
실패) → 이번 세션 광고 없음(슬롯은 그대로 예약). 구독자 → 배너·전면 없음 + 슬롯 제거 +
힌트 광고 불필요(US 31·32), 단 EEA 면 개인정보 설정 행은 남는다. 권한 null(아직 모름)
→ 비구독자로 다룬다. ATT `notDetermined` → 광고 보류, `authorized`/`denied`/`restricted`
→ 전부 로드 가능(UMP 와 별개 상태).

### 3.3 동의 흐름·서비스 경계 (`test/ads/ad_consent_test.dart` 6, `ad_unit_ids_test.dart` 4, `bootstrap_test.dart` +1, `admob_native_config_test.dart` 4)
동의 받으면 `initialize` 1회, 미동의면 0회, 조회 실패면 `UmpStatus.failed` + 초기화 0회
+ 게이트 닫힘, **다시 시작하면 다시 묻는다**(2회). iOS 는 ATT 선택 전 UMP 호출 0회 →
선택(거부 포함) 뒤 1회. 유닛 ID 는 릴리스·디버그·빈 값 3분기 + 플랫폼×포맷 6개가 전부
다른 값. 네이티브 앱 ID 는 매니페스트·plist 를 직접 읽어 꼴(`ca-app-pub-…~…`)과 "아직
테스트 ID" 를 확인하고, 매니페스트 주석에 XML 이 못 읽는 `--` 가 없는지도 본다(§7).

### 3.4 배너 (`test/ads/banner_slot_gate_test.dart` 6, `banner_size_test.dart` 4)
실제 앱 트리(`ChosungApp`)를 띄워 셸의 슬롯을 본다 — 슬롯은 `AdaptiveScaffold` 가
들고 있어서 셸 밖에서는 "슬롯 자체 제거" 를 증명할 수 없다.
- 동의한 비구독자: 슬롯 폭(390)으로 로드 1회, 배너가 그려진다
- 구독자: `AdBannerSlot` 자체가 없고 로드 요청 0회
- 미동의: 슬롯은 있고(예약 높이 50+8) 요청 0회
- 로드 실패: 예약 높이 그대로, 배너 없음
- 태블릿 1024: 요청 폭 < 1024(rail 제외) = 슬롯 폭, 예약 높이 90+8
- **1024×1366 → 1366×1024 회전: 슬롯 높이 불변, 요청 2회(새 폭이 더 넓다), 이전 배너 해제 1회**

`bannerSizeWithin` 은 예약 높이에 들어가면 어댑티브 크기를 그대로, 넘거나 null 이면
그 폭에 들어가는 고정 크기(320×50 / 728×90)를 고른다.

### 3.5 전면 (`test/ads/result_interstitial_test.dart` 8, `today_tab_ads_test.dart` 그룹 2개 중 1개 4)
첫 제출 전 0회 / 제출 뒤 시트를 닫으면 1회 + 퍼즐 플래그 기록 / 같은 퍼즐 두 번째 0회 /
앱을 다시 켜도(플래그가 남아 있으면) 0회 / 다음 퍼즐은 1회 / 구독자 0회 / 미동의 0회 /
**광고가 뜨지 않으면 플래그를 남기지 않는다**. 위젯 쪽은 실제 제출 → 시트 → 배리어 탭으로
닫기 흐름에서 같은 결과를 본다(시트가 떠 있는 동안에는 0회).

### 3.6 보상형 힌트 (`today_tab_ads_test.dart` 그룹 "보상형 힌트 미리 보기" 7)
비구독자: 레이블 "광고 보고 힌트 미리 보기" → 탭 → 보상형 1회 → `hint-unlock(puzzleId)`
→ 힌트 문장 표시 + 버튼 사라짐. 구독자: 레이블 "힌트 미리 보기" → 보상형 0회 → 같은
`hint-unlock` → 힌트 표시. 광고를 **못 띄움**(`RewardedOutcome.unavailable`): 버튼 비활성 +
"지금은 광고를 불러올 수 없어요" + `hint-unlock` 0회. 떴는데 **중간에 닫음**
(`dismissed`): "광고를 끝까지 봐야 힌트가 열려요" + 버튼은 그대로 살아 있고,
다시 눌러 끝까지 보면 힌트가 열린다. 게이트가 닫힌 세션: 처음부터 비활성. 409 이미 열림: 재조회로 힌트
표시(`fetchTodayPuzzleCalls == 2`). 네트워크 실패: 보드 유지 + "힌트를 열지 못했어요".

### 3.7 S4 광고 개인정보 설정 (`records_ad_privacy_test.dart` 3)
`privacyOptionsRequired` 면 행이 뜨고 "준비 중" 문구가 사라지며 탭 시
`showPrivacyOptionsForm` 1회. 아니면 행 자체가 없다. 구독자도 EEA 면 남는다.
27 의 "자리 전부 있음" 테스트에서는 이 자리를 빼고(조건부가 됐다) 주석으로 옮겼다.

### 3.8 바뀐 기존 테스트
- `test/permissions/permission_providers_test.dart` +1: iOS 두 번째 실행에서 시스템에
  남은 ATT 선택을 읽어온다
- `test/screens/ranking_records_tablet_test.dart`: T4 열 배치를 **EEA 구성**으로 본다
  (광고 개인정보 행이 있어야 그 행의 열을 확인할 수 있다)
- `test/golden/today_tab_golden_test.dart`: 광고를 띄울 수 있는 비구독자 + 배너 슬롯 포함

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

브라우저 도구·`impeccable detect` 는 쓰지 않는다(HTML/CSS 용). 22·24·25·26·27·28 과
같이 소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매겼다.
폭 확인은 눈이 아니라 위젯 테스트(390·744·1024·1366)와 골든 3장이다.

| # | 축 | 28 | 31 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | 힌트 버튼은 `OutlinedButton.icon` 이라 레이블이 그대로 읽히고, 광고를 못 띄우면 **버튼을 끄고 그 이유를 같은 카드 안 텍스트로** 남긴다(색·아이콘만으로 알리지 않는다). S4 광고 개인정보 행은 기존 `SettingsRow`(최소 높이 44) 그대로. 배너 슬롯은 장식이 아니라 실제 광고 자리라 Semantics 를 따로 덮지 않았다 — 광고 뷰는 SDK 가 자기 접근성 트리를 들고 온다 |
| 2 | Performance | 3 | 3 | 배너는 폭이 **바뀔 때만** 다시 로드하고 이전 광고를 즉시 해제한다(세대 번호로 늦게 온 응답 폐기). 전면·보상형은 필요한 순간에만 로드하고 닫히면 바로 `dispose`. 게이트는 순수 함수 + `Provider` 라 입력 셋이 안 바뀌면 다시 계산되지 않는다 |
| 3 | Appearance & Theming | 4 | 4 | 새 UI 는 HintCard 안내 한 줄(=`bodySmall` + `mutedForeground`)과 설정 행 하나뿐이고 둘 다 토큰만 쓴다. raw hex 는 여전히 `app_colors.dart` 한 파일뿐 |
| 4 | Platform Conformance | 3 | 3 | UMP 폼·전면·보상형은 SDK 가 네이티브로 띄운다. iOS 는 ATT → UMP 순서를 지키고(Apple 요구), 앱 ID 는 매니페스트·plist 에 선언했다. Android 13+ 권한·desugaring 등 기존 설정은 건드리지 않았다 |
| 5 | Adaptivity | 4 | 4 | 배너는 rail 을 뺀 콘텐츠 열 폭으로 요청하고 회전·Split View 에서 새 폭으로 1회 재요청하며 예약 높이는 24 규칙 그대로. 구독자는 슬롯이 사라지고 콘텐츠가 그 자리를 채운다 |
| **합계** | | **18/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭 포함": 통과.** 1024(세로)·1366(가로)는
`banner_slot_gate_test.dart` 의 회전 테스트가, 744·834·390·320 은 24 의 셸 테스트와
27 의 T4 테스트가 그대로 덮는다(이 티켓의 변경은 셸 안에서 돈다). 태블릿 골든
`today_tablet_1024.png` 가 rail + 콘텐츠 열 하단 배너 슬롯(90)을 그림으로 고정한다.

## 5. 목업 대비 기록

골든 3장(`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`).
이 티켓에서 셸에 **배너 슬롯을 포함**시켰다 — 실제 앱(`HomeShell`)은 비구독자에게 늘
슬롯을 넘기므로, 슬롯이 없는 골든은 목업과도 앱과도 다른 그림이었다.

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `today_light_390.png` | `design/stitch/e1_home.html` | HintCard 잠김 + "광고 보고 힌트 미리 보기"(재생 아이콘, 활성) + 탭 바 아래 `muted` 배너 슬롯(상단 헤어라인, 50+8). 목업과 같은 순서 |
| `today_dark_390.png` | `design/stitch/e7_home_dark.html` | 같은 구성의 다크 토큰. 슬롯도 다크 `muted` |
| `today_tablet_1024.png` | SCREENS T0·T1 | rail + 콘텐츠 열 하단 배너 슬롯(90), 오른쪽 열 HintCard |
| `records_light_390.png`·`records_tablet_1024.png` | `design/stitch/e4_records.html` · T4 | 비 EEA 구성이라 "광고 개인정보 설정" 행이 빠졌다(SCREENS S4 의 "required 인 지역에서만 표시") |

### 디자인 파일과 다르게 구현한 곳

1. **전면 광고 타이밍.** SCREENS S2 는 "시트가 완전히 뜬 뒤 전면 광고 1회" 지만 티켓
   31 과 US 24("결과 확인 **후**")를 따라 **시트를 닫은 뒤**로 좁혔다. 결과를 읽는
   중에 전면이 덮으면 확인 자체를 못 한다. 커밋 메시지·README "31." 에도 적었다.
2. **빈 배너 슬롯에 "광고" 캡션을 넣지 않았다.** 목업(e1_home)은 빈 슬롯 가운데에
   작게 "광고" 를 적지만, 로드 전·실패 상태에서 광고가 없는 자리에 "광고" 라고 적는
   꼴이 된다. 22·24 가 만든 빈 슬롯 그대로 뒀다(`ads.slot_label` 키는 쓰지 않는다).
3. **힌트 미리 보기가 링크가 아니라 버튼이다.** 목업은 잠김 문구 오른쪽의 텍스트
   링크지만 25 가 OVERRIDES §4·§6 에 따라 카드 안 전폭 `OutlinedButton` 으로 뒀고,
   이 티켓은 그 자리를 그대로 쓰면서 레이블·아이콘·활성 여부만 채웠다.

## 6. 검증 (실제 실행 명령과 출력)

```
$ cd mobile && dart format --set-exit-if-changed .
Formatted 145 files (0 changed) in 0.17 seconds.        # exit 0

$ flutter analyze
Analyzing mobile...
No issues found! (ran in 3.1s)

$ flutter test
00:36 +457: All tests passed!                           # 28 머지 시점 398 → 457
```

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t31 TEST_REDIS_URL=redis://127.0.0.1:6379/5 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t31_migrations uv run pytest -q
........................................ [100%]
1403 passed in 1171.65s (0:19:31)
```

백엔드는 한 줄도 안 건드렸다(`git diff main..HEAD -- app/ web/ tests/ migrations/`
빈 결과). 위 실행은 **로컬 `main`(티켓 28 머지, `8ddc8fd`) 위에 rebase 된 상태**
에서 돌렸고(`git rebase main` 은 "up to date" — main 이 안 움직였다), 그 뒤의
커밋은 `mobile/` 만 건드렸다. 전용 자원: DB `chosung_daily_test_t31`, Redis 5,
마이그레이션 DB `chosung_daily_test_t31_migrations`.

네이티브 빌드 — **둘 다 처음에는 실패했고 §7 에 고친 내용을 적었다**:

```
$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                            103.2s
✓ Built build/app/outputs/flutter-apk/app-debug.apk

$ cd ios && pod repo update        # 캐시된 spec 색인이 Google-Mobile-Ads-SDK 13.x 를 몰랐다
Updating spec repo `trunk`

$ cd .. && flutter build ios --no-codesign --debug
Running pod install...                                             15.4s
Running Xcode build...
Xcode build done.                                            17.3s
✓ Built build/ios/iphoneos/Runner.app
```

빌드 뒤 `mobile/build`·`mobile/ios/Pods` 를 지웠고, `pod install` 이 건드린
`ios/Runner.xcodeproj/project.pbxproj`·`Runner.xcworkspace/contents.xcworkspacedata`·
`Podfile.lock` 은 **되돌렸다**(CocoaPods 통합 산출물이라 이 티켓의 변경이 아니다 —
티켓 24 와 같은 처리). `ios/Podfile` 과 `ios/Flutter/*.xcconfig` 의 변경은 §7 의
의도된 수정이라 남겼다.

마이그레이션은 만들지 않았다(`migrations/versions/` 변경 0건) — `flask db heads` 는
선행 머지 상태 그대로다.

## 7. 네이티브 빌드에서 실제로 잡은 결함 3건 (Dart 테스트는 전부 통과한 상태였다)

1. **XML 주석 안의 `--` 가 Android 빌드를 죽였다.** AdMob 앱 ID 옆에 적은 주석에
   "`--dart-define` 으로 못 넘긴다" 가 들어 있었는데, XML 주석에는 `--` 를 넣을 수
   없다. `flutter test`·`analyze` 는 전부 통과한 채
   `:app:processDebugMainManifest` 가 "Error parsing AndroidManifest.xml" 로 멈췄다.
   문구에서 `--` 를 빼고, **매니페스트 주석에 `--` 가 없는지 보는 테스트**를 더했다
   (`test/config/admob_native_config_test.dart`).
2. **CocoaPods spec 색인이 오래돼 `pod install` 이 멈췄다.** 캐시된 CDN 색인이
   `Google-Mobile-Ads-SDK` 13.x 를 몰라서 "specs repository is too out-of-date" 로
   끝났다. `pod repo update` 한 번으로 풀린다 — 레포 변경 없음. CI(티켓 34)는
   러너에서 `pod install` 을 돌리므로 같은 일이 생기면 러너에서 한 번 하면 된다.
3. **`google_mobile_ads` 9.1.0 이 SDK 의 PrivateHeader 를 include 한다.**
   `FLTAd_Internal.h`·`FLTAdPreloader.h` 가 `GoogleMobileAds_Beta.h` 를 include 해서
   Xcode 모듈 검사가 "Include of non-modular header inside framework module" 로
   iOS 빌드를 막는다. **SDK 를 13.7.0 으로 내려도 같아서**(13.11 → 13.7 둘 다 확인)
   버전 핀은 되돌리고, `CLANG_ALLOW_NON_MODULAR_INCLUDES_IN_FRAMEWORK_MODULES=YES`
   를 **두 곳**에 뒀다: `ios/Podfile` post_install 에서 `google_mobile_ads` 타깃만,
   그리고 `ios/Flutter/Debug.xcconfig`·`Release.xcconfig`(Runner 타깃). 모듈은
   **import 하는 타깃이 컴파일할 때** 검증돼서 Pods 쪽 예외만으로는 빌드가 통과하지
   않았다 — 빌드를 통과시킨 건 xcconfig 쪽이고, Podfile 쪽은 플러그인 타깃 자체의
   컴파일(CI 의 깨끗한 빌드)을 위해 같이 남겼다. 앱·다른 플러그인의 모듈 검사는
   그대로다. 플러그인이 고치면 두 곳을 같이 지운다(주석에 적어 뒀다).

## 8. 의도된 이탈 / 남은 결함

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | 배너 예약 높이 | **미정 24 의 실측을 못 했다.** 어댑티브 높이는 플랫폼 채널로만 나와서 테스트로 잴 수 없다. 24 의 잠정값을 두고 "예약을 넘는 크기는 안 쓰고 고정 크기로 떨어뜨린다" 로 막았다. 실측은 `docs/RELEASE.md "### 31."` 체크리스트 | 실기기(37) |
| P2 | `GoogleAdService` | 플랫폼 채널을 타는 실제 구현에는 단위 테스트가 없다(`firebase_analytics_service.dart` 와 같은 경계). 로직은 전부 `AdService` 바깥(게이트·크기 선택·타이밍)으로 빼서 테스트했고, 남은 건 SDK 호출 배선뿐 | 실기기(37) |
| P3 | 힌트 버튼 | 광고 **가용 여부를 미리 묻지 않는다**(preload 없음). 광고를 못 띄운 경우에만 그 퍼즐에서 버튼을 끄는 쪽을 골랐다(중간에 닫은 건 다시 누를 수 있다) — 누를 때마다 다시 로드해 보면 매번 몇 초 뒤 같은 실패를 본다. 대신 첫 탭에서는 광고 로딩을 기다린다 | — (의도) |
| P3 | 구독 권한 null | 시작 직후 `/me/stats` 가 오기 전에는 비구독자로 다뤄 배너를 요청한다. 구독자가 광고를 보는 시간은 왕복 한 번이고, 33 의 갱신이 들어오면 슬롯이 사라진다 | 티켓 33 |
| P3 | 폰 레이아웃 | 보드가 두 행 넘게 찬 상태(390×844)에서는 배너 슬롯까지 들어가면 제출 버튼이 스크롤 아래로 내려간다. 이 티켓이 만든 게 아니라 **원래 앱의 레이아웃**이고, 슬롯을 포함한 골든이 그걸 드러냈다 | — (기존 동작) |
| P2 | — | 시뮬레이터·실기기 스크린샷은 없다. 골든은 테스트 렌더러이고 **광고가 실제로 그려진 그림은 한 장도 없다** | 티켓 35·37 |

## 수정 라운드 1 (리뷰 r1 — BLOCKER 0 / MAJOR 3 / MINOR 0)

세 결함 모두 **리뷰의 재현 절차대로 먼저 실패하는 테스트를 만들고** 나서 고쳤다.
아래 "재현(수정 전)" 출력은 고치기 전에 실제로 받은 실패다. MINOR 는 0건이라
미수정 MINOR 가 없다.

### D-31-1 — ko/en 왕복 시 같은 퍼즐에 전면 광고 재노출

**원인.** `InterstitialStore` 가 **마지막 퍼즐 하나**만 기억했다
(`interstitial_shown_puzzle_id` int 1개). "퍼즐당 1회" 를 "오늘 퍼즐 하나" 로 읽은
전제가 틀렸다 — 오늘 퍼즐은 **언어마다 따로**이고(ko·en 각각 다른 `puzzle_id`)
설정에서 언어를 바꾸면 `PuzzleLanguageNotifier.change` 가 오늘 퍼즐을 다시 읽는다.
그래서 A(ko) → B(en) 로 바꾸면 `markShown(B)` 가 A 의 기록을 덮고, A 로 돌아와
"결과 보기" 를 열면 세 번째 광고가 나간다. 왕복할 때마다 반복된다.

**수정.** `mobile/lib/ads/interstitial_store.dart` — 인터페이스를
`lastShownPuzzleId()` → `hasShown(int puzzleId)` 로 바꿔 **기록 전체에 물어보게**
했다. 저장은 문자열 목록(`interstitial_shown_puzzle_ids`)에 최근 4개까지 남기고
오래된 쪽부터 밀어낸다 — 동시에 "오늘" 이 될 수 있는 건 언어 수만큼이고, 자정이
지나면 새 ID 가 들어오므로 지난 퍼즐의 기록은 들고 있을 이유가 없다. 값 타입이
int → 목록으로 바뀌어 **키 이름도 새로 썼다**(같은 키로 `getStringList` 를 부르면
이전 버전이 넣어둔 int 에서 타입 오류가 난다). `ResultInterstitial` 은
`if (await store.hasShown(puzzleId)) return false;` 한 줄로 바뀌었다.

**증명.** `test/ads/result_interstitial_test.dart` "언어를 왕복해도 퍼즐마다 1회다"
— 41(ko) 1회 → 42(en) 1회 → 41 재열기 **거부** → 42 재열기 **거부**,
`interstitialShowCalls == 2`.

```
# 재현(수정 전) — 41 재열기에서 세 번째 광고가 나갔다
$ flutter test test/ads/result_interstitial_test.dart
+7 -1: 언어를 왕복해도 퍼즐마다 1회다 [E]
  Expected: false
    Actual: <true>
  test/ads/result_interstitial_test.dart 167:5

# 수정 후
$ flutter test --plain-name "언어를 왕복해도 퍼즐마다 1회다" test/ads/result_interstitial_test.dart
00:02 +1: All tests passed!
```

기기에 남는 기록 자체는 순수 함수(`nextShownPuzzleIds`)로 빼서
`test/ads/interstitial_store_test.dart`(4)가 본다 — 처음 기록 / 다른 언어 퍼즐을
같이 들고 있기 / 같은 ID 중복 방지 / 용량 초과 시 오래된 쪽부터 밀어내기.
(`SharedPreferencesAsync` 는 플랫폼 채널을 타므로 저장 호출 자체는 테스트하지
않는다 — `OnboardingStore` 와 같은 경계다.)

가짜 저장소(`test/fakes/in_memory_interstitial_store.dart`)도 기록을 `Set<int> shown`
으로 들고 있게 바꿨다 — 하나만 남기면 어느 쪽 기록이 밀렸는지 테스트가 볼 수 없다.
기존 단정 `store.puzzleId` 는 `store.shown` 으로 같이 옮겼다.

### D-31-2 — 제출 중 힌트 요청이 제출 응답과 입력 잠금을 손상

**원인.** `unlockHint()` 가 `_submitting` 을 보지 않고 `_generation` 을 올렸다.
세대 번호는 "나중에 떠난 요청이 이긴다" 는 규칙이라, 올리는 순간 **먼저 떠난 제출
응답이 103행에서 폐기**된다. 그러면 ① 서버에서 이미 소비된 시도가 보드에 안 쌓이고
② 힌트 성공은 제출 전 `puzzle` 에 `copyWith(hint:)` 를 해서 그 상태를 굳히고
③ 힌트가 실패하면 상태를 아무도 복구하지 않아 화면의 `submitting: true` 가 남아
재조회/재시작 전까지 입력이 잠긴다(`finally` 는 내부 `_submitting` 만 되돌린다).
기존 보호(`refresh` 의 `_refreshQueued`)를 새 경로가 우회한 것이다.

**수정.** `mobile/lib/puzzle/today_puzzle_controller.dart` — 제출이 끝나면 완료되는
`Completer<void> _submitDone` 을 두고, `unlockHint()` 가 **그걸 먼저 기다린 뒤**
현재 상태를 다시 읽어 요청을 보낸다(줄 세우기). 재조회처럼 호출을 버리지 않는
이유: 힌트 버튼을 눌렀는데 아무 일도 안 일어나면 안 된다. 버튼을 잠그지 않은
이유: 힌트는 시도·순위를 건드리지 않으므로(US 5) 제출 중에도 누를 수 있는 게 맞다.

**증명.** `test/puzzle/today_puzzle_controller_test.dart` 그룹 "응답 경합" 2개.
- "제출을 기다리는 동안 힌트를 열어도 쌓인 행과 힌트가 모두 남는다" — 제출 응답
  전에는 `unlockHint` 가 서버로 나가지 않고(`unlockedHintPuzzleIds` 빈 목록),
  풀린 뒤에는 시도 1개 + `attemptsLeft 4` + 힌트 + `submitting: false` 가 모두 맞다.
- "제출 대기 중 힌트가 실패해도 제출 결과와 잠금 해제가 남는다" — 힌트를
  `NetworkApiException` 으로 실패시켜도 제출은 `true` 로 끝나고 입력 잠금이 풀린다.

```
# 재현(수정 전) — 힌트가 제출 응답을 앞질러 나가고, 제출 결과가 폐기됐다
$ flutter test test/puzzle/today_puzzle_controller_test.dart
+13 -2: 응답 경합 제출을 기다리는 동안 힌트를 열어도 쌓인 행과 힌트가 모두 남는다 [E]
  Expected: empty
    Actual: [41]
  제출 응답 전에는 보내지 않는다
+13 -3: 응답 경합 제출 대기 중 힌트가 실패해도 제출 결과와 잠금 해제가 남는다 [E]
  Expected: true
    Actual: <false>

# 수정 후
$ flutter test test/puzzle/today_puzzle_controller_test.dart
00:03 +24: All tests passed!
```

### D-31-3 — 광고 실패 후 구독 권한이 생겨도 무광고 힌트가 계속 잠김

**원인.** `_HintSlot` 이 "광고를 못 띄웠다" 를 `_adUnavailable` 플래그와 `_notice`
문구로 **따로** 들고 있었고, `blocked = !gate.canPreviewHint || _adUnavailable` 이
구독 여부와 무관하게 그 플래그를 적용했다. 그래서 같은 퍼즐의 `_HintSlot` 이 살아
있는 동안(`ValueKey(puzzle.puzzleId)`) 권한이 켜져도 레이블만 "힌트 미리 보기" 로
바뀌고 버튼은 계속 비활성, 안내도 "지금은 광고를 불러올 수 없어요" 로 남았다.

**수정.** `mobile/lib/screens/today_tab.dart` — 상태를 **마지막 보상형 결과 하나**
(`RewardedOutcome? _adFailure`)로 모으고 안내 문구·버튼 잠금을 거기서 파생시킨다.
그리고 그 기록은 **광고가 필요한 동안만** 적용한다:
`final adFailure = gate.hintPreviewNeedsAd ? _adFailure : null;`. 권한이 켜지면
(티켓 32 구매·33 갱신이 같은 `entitlementProvider` 를 쓴다) 잠금과 안내가 같이
사라지고 광고 없이 바로 `hint-unlock` 이 나간다. 서버가 힌트를 못 연 경우는
광고와 무관하므로 `_unlockFailed` 로 따로 둔다.

**증명.** `test/screens/today_tab_ads_test.dart` "광고 실패 뒤 구독 권한이 생기면
바로 열 수 있다" — `RewardedOutcome.unavailable` 로 버튼이 잠긴 뒤
`entitlementProvider.notifier.update(active: true)`(32·33 이 쓸 실제 인터페이스)를
부르면 레이블이 "힌트 미리 보기" 로 바뀌고 안내가 사라지고 버튼이 활성화된다.
탭하면 `rewardedShowCalls` 가 1 그대로(광고 재요청 없음)이고
`unlockedHintPuzzleIds == [1]`, 힌트 문구가 보인다.

```
# 재현(수정 전) — 구독 권한이 켜져도 안내와 잠금이 남았다
$ flutter test test/screens/today_tab_ads_test.dart
+4 -1: 보상형 힌트 미리 보기 광고 실패 뒤 구독 권한이 생기면 바로 열 수 있다 [E]
  Expected: no matching candidates
    Actual: Found 1 widget with text "지금은 광고를 불러올 수 없어요"
  test/screens/today_tab_ads_test.dart line 200

# 수정 후
$ flutter test test/screens/today_tab_ads_test.dart
00:12 +12: All tests passed!
```

### 고치지 않은 지적

- **SDK `canRequestAds` 직접 확인**(체크박스 "증거 부족" 행). 리뷰도 "이 차이만으로
  실제 잘못된 노출을 단정하지 않아 별도 결함 수에는 넣지 않았다" 로 적었고 결함
  ID 가 없다. `GoogleAdService.requestConsent()` 는 `getConsentStatus()` 를 읽고
  `UmpStatus.canRequestAds` 가 SDK 와 같은 네 값으로 판정한다
  (`notRequired`·`obtained` → true). 바꾸려면 `UmpStatus` 에 필드를 하나 더 들여
  게이트·가짜·테스트를 같이 손봐야 해서 **이번 수정 범위(결함 수정)를 넘는다** —
  실제 SDK 값과 자체 판정의 일치는 §8 의 실기기 검증(티켓 37) 몫으로 남긴다.
- **실제 광고 렌더링·어댑티브 높이 실측·네이티브 audit**: §8 표에 이미 P2 로 적어
  둔 한계이고 이 라운드에서 달라진 게 없다.

### 수정 라운드 1 검증 (실제 실행 명령과 출력)

```
$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 146 files (0 changed) in 0.27 seconds.        # exit 0

$ flutter analyze
Analyzing mobile...
No issues found! (ran in 5.1s)

$ flutter test
00:29 +465: All tests passed!                           # 리뷰 시점 457 → 465 (+8)
```

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t31 TEST_REDIS_URL=redis://127.0.0.1:6379/5 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t31_migrations uv run pytest -q
........................................ [100%]
1403 passed in 1599.82s (0:26:39)
```

더한 테스트 8개: 언어 왕복 전면 1(`result_interstitial_test.dart`), 저장 기록
4(`interstitial_store_test.dart`), 제출↔힌트 경합 2
(`today_puzzle_controller_test.dart`), 실패→구독 전환 1
(`today_tab_ads_test.dart`).

백엔드는 이 라운드에서도 한 줄도 건드리지 않았다
(`git diff main..HEAD -- app/ web/ tests/ migrations/ .env.example` 빈 결과).
`migrations/versions/` 변경이 없어 조건부 `flask db heads` 는 해당하지 않는다.
`git rebase main`(로컬 `main` = `8ddc8fd`, 리뷰가 쓴 기준과 같다)은 "up to date" —
main 이 움직이지 않았다. `git diff --check main...HEAD` exit 0, 작업 트리 clean.
전용 자원만 썼다: DB `chosung_daily_test_t31`, Redis DB 5, 마이그레이션 DB
`chosung_daily_test_t31_migrations`. 접속 문자열의 인증 값은 문서에 싣지 않는다.
공용 테스트 DB 는 건드리지 않았다.

실기기·실제 광고 호출·스토어·프로덕션 접근은 이 라운드에도 없다 — §8 의 한계가
그대로다.

## 수정 라운드 2

라운드 2 리뷰(Codex, FAIL)의 신규 **MAJOR 1건(D-31-4)** 을 고쳤다. BLOCKER·REPEAT·
MINOR 는 없었다. 이전 결함 3건은 리뷰가 모두 FIXED 로 재판정했다.

### D-31-4 — 힌트 응답 대기 중 제출하면 성공한 힌트가 폐기되고 광고를 다시 요구한다

**재현(리뷰의 절차 그대로).** 힌트가 없는 진행 중 퍼즐에서 `unlockHint()` 를
띄워 놓고(`api.unlockHintGate`) 그 응답 전에 답을 제출해 제출만 네트워크 오류로
끝낸 뒤, 앞서 성공한 hint-unlock 응답을 전달한다. 수정 전에는 `unlockHint()` 가
`false` 를 돌려주고 보드의 `hint` 가 `null` 로 남았다 — 화면은 "힌트를 열지
못했어요" 를 띄우고, 비구독자가 다시 누르면 `_preview()` 가 **보상형 광고부터**
다시 재생했다.

**원인.** 응답 경합을 `_generation` **하나**로만 끊었다. 그 규칙은 "나중에 떠난
요청이 이긴다, 먼저 떠난 응답은 버린다" 인데, 보드 전체를 실어 오는 재조회에는
맞지만 **힌트 한 칸**에는 틀렸다. hint-unlock 의 새 정보는 "서버가 힌트를 열었다"
뿐이고 시도 행·남은 기회·상태와 겹치지 않는다. 그런데

- `unlockHint()` 는 떠날 때 세대를 N 으로 올리고, 끼어든 제출이 N+1 로 올린다.
  돌아온 힌트는 `_canCommit(N) == false` 로 **폐기**된다
  (`today_puzzle_controller.dart:168`, 수정 전).
- 성공·실패 양쪽이 **떠날 때의 스냅샷**(`puzzle`)에 자기 변경만 얹어 썼다.
  그래서 반대 순서(힌트가 먼저 도착)에서도 뒤따르는 제출 커밋이
  `applyGuess(puzzle: <힌트 없던 스냅샷>)` 로 그 힌트를 **되돌렸고**,
  제출 실패 경로 `_commitNotice(…, puzzle, …)` 도 같은 스냅샷으로 덮었다.
- 힌트의 409(이미 열림)·끝난 퍼즐·바뀐 퍼즐 재조회도 **떠날 때의 세대**로
  커밋해서, 응답을 받은 뒤 떠난 조회인데도 그 사이 끝난 제출 때문에 버려졌다.
  (서버는 이미 열어 둔 힌트를 돌려주고 있었다.)

증상(화면에 힌트가 없다)만 가리려면 UI 에서 다시 조회하면 되지만, 원인은
"겹치지 않는 변경을 세대 하나로 서로 지운다" 였다.

**수정** (`mobile/lib/puzzle/today_puzzle_controller.dart`).

- `_boardFor(puzzleId)` 를 들였다 — 응답을 올릴 **지금의** 보드를 돌려주고,
  그 사이 퍼즐이 바뀌었거나(자정·언어) 보드가 없으면 `null`(= 이 응답은 버린다).
- 힌트 성공은 세대 검사 대신 `_boardFor` 로 커밋한다: 지금 보드에
  `copyWith(hint:, hintUnlocked: true)` 로 **그 칸만** 올리고
  `submitting`·`notice` 는 그대로 들고 간다(제출 잠금을 일찍 풀지 않는다 —
  라운드 1 D-31-2 의 증상이었다).
- 제출 성공도 `applyGuess(puzzle: board.puzzle, …)` 로 지금 보드에 한 행을
  쌓고, 제출 실패 안내(`_commitNotice`)도 지금 보드 위에 올린다. 그래서 어느
  순서로 응답이 와도 시도 행과 힌트가 **둘 다** 남는다.
- 힌트의 재조회 세 경로는 `_reloadAfterHint()` 로 모았다 — 응답을 받은 뒤
  떠나는 조회라 **새 세대**로 쓰고, 제출이 아직 떠 있으면 직접 읽지 않고
  `_refreshQueued` 로 제출 뒤 재조회에 넘긴다(지금 읽는 서버 이력엔 방금 보낸
  답이 없다 — `submit()` 이 쓰는 규칙과 같다).

세대 번호는 그대로 남는다: 재조회·제출끼리는 여전히 "나중 것이 이긴다" 다
(`응답 경합` 그룹의 기존 테스트 6개가 그대로 통과한다).

**증명.** 재현 테스트 5개를 먼저 추가해 실패를 고정하고(red) 고쳤다.
`mobile/test/puzzle/today_puzzle_controller_test.dart` 4개:

| 테스트 | 무엇을 고정하는가 |
|---|---|
| 힌트를 기다리는 동안 제출이 실패해도 열린 힌트는 보드에 남는다 | 리뷰의 재현 그대로. 힌트가 남고 `hintUnlocked` true, 제출 실패 안내(offline)도 같이 남고, `unlockedHintPuzzleIds == [41]`(재요청 없음) |
| 힌트를 기다리는 동안 제출이 성공하면 쌓인 행과 힌트가 모두 남는다 | 시도 1행·남은 기회 4 + 힌트 동시 보존 |
| 제출 응답보다 힌트가 먼저 와도 제출이 그 힌트를 덮어 지우지 않는다 | 반대 순서. 힌트가 먼저 커밋될 때 `submitting: true` 유지, 뒤이은 제출 커밋이 힌트를 되돌리지 않음 |
| 힌트가 이미 열려 있었다는 409 는 제출이 끼어들어도 보드를 다시 읽는다 | `_reloadAfterHint` 의 새 세대 — 재조회 결과(열린 힌트)가 버려지지 않음 |

`mobile/test/screens/today_tab_ads_test.dart` 1개 — 화면 경로(실제 `TodayTab`·
컨트롤러·`HintCard`): "힌트를 기다리는 동안 제출이 실패해도 힌트가 열린다" 는
광고를 끝까지 본 뒤 힌트 응답을 붙잡고 제출을 실패시킨 다음 힌트를 전달하면
힌트 문구가 보이고 "힌트를 열지 못했어요" 가 없고 미리 보기 버튼이 사라지며
`rewardedShowCalls == 1`(= **같은 힌트에 광고를 다시 요구하지 않는다**) 임을 본다.

```
# 재현(수정 전) — lib 만 수정 직전으로 되돌려 같은 테스트를 돌렸다
$ git show HEAD~1:mobile/lib/puzzle/today_puzzle_controller.dart \
    > mobile/lib/puzzle/today_puzzle_controller.dart
$ cd mobile && flutter test test/puzzle/today_puzzle_controller_test.dart \
    test/screens/today_tab_ads_test.dart
+15 -1: 응답 경합 힌트를 기다리는 동안 제출이 실패해도 열린 힌트는 보드에 남는다 [E]
  Expected: true
    Actual: <false>
+15 -2: 응답 경합 힌트를 기다리는 동안 제출이 성공하면 쌓인 행과 힌트가 모두 남는다 [E]
  Expected: true
    Actual: <false>
+15 -3: 응답 경합 제출 응답보다 힌트가 먼저 와도 제출이 그 힌트를 덮어 지우지 않는다 [E]
  Expected: true
    Actual: <false>
+15 -4: 응답 경합 힌트가 이미 열려 있었다는 409 는 제출이 끼어들어도 보드를 다시 읽는다 [E]
  Expected: '서울에 가장 많다'
    Actual: <null>
  재조회 결과가 버려지면 안 된다
+36 -5: ... 힌트를 기다리는 동안 제출이 실패해도 힌트가 열린다 [E]
  Expected: exactly one matching candidate
    Actual: _TextWidgetFinder:<Found 0 widgets with text "서울에 가장 많다": []>
00:12 +36 -5: Some tests failed.

# 수정 후 (git checkout -- 으로 수정본 복원)
$ cd mobile && flutter test test/puzzle/today_puzzle_controller_test.dart \
    test/screens/today_tab_ads_test.dart
00:06 +41: All tests passed!
```

### 고치지 않은 지적 (라운드 2)

- **SDK `canRequestAds` 직접 확인**(체크박스 "증거 부족"). 리뷰가 라운드 1·2 모두
  "실제 오노출을 확인하지 못했으므로 별도 결함으로 승격하지 않았다" 로 적었고
  결함 ID 가 없다. 근거와 범위 판단은 라운드 1 절의 같은 항목과 같다 —
  `UmpStatus.canRequestAds` 가 SDK 와 같은 네 값으로 판정하고, 바꾸려면 게이트·
  가짜·테스트를 함께 손봐야 해서 결함 수정 범위를 넘는다. 실기기 확인은 §8·티켓 37.
- **실제 광고 렌더링·어댑티브 높이 실측·네이티브 빌드 재검증·UMP 재선택 결과**:
  §8 표의 기존 한계이고 이 라운드에서 달라진 게 없다. 이 라운드도 실기기·실제
  광고·스토어·프로덕션에 접속하지 않았다.

### 수정 라운드 2 검증 (실제 실행 명령과 출력)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 3.1s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 146 files (0 changed) in 0.31 seconds.        # exit 0

$ cd mobile && flutter test        # 티켓 30 통합 rebase 전, main = 1172b9b
00:40 +480: All tests passed!                           # 리뷰 시점 465 → +5(이번 라운드), rebase 로 main 의 10 개가 더해져 480
```

```
$ uv run ruff check .
All checks passed!                                      # exit 0

$ TEST_DATABASE_URL=...chosung_daily_test_t31 TEST_REDIS_URL=redis://127.0.0.1:6379/5 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t31_migrations uv run pytest -q
........................................ [100%]
1412 passed in 1603.52s (0:26:43)                       # exit 0, 재실행 없이 통과
```

더한 테스트 5개뿐이고 다른 테스트는 고치지 않았다 — 제출↔힌트 경합 4
(`today_puzzle_controller_test.dart`), 화면 경로 1(`today_tab_ads_test.dart`).
`lib` 수정은 `mobile/lib/puzzle/today_puzzle_controller.dart` 한 파일이다.
백엔드는 이 라운드에도 한 줄도 건드리지 않았다
(`git diff main..HEAD -- app/ web/ tests/ migrations/ .env.example` 빈 결과).
`migrations/versions/` 변경이 없어 조건부 `flask db heads` 는 해당하지 않는다.

`git rebase main` — 아래 "티켓 30 통합" 절을 보라. 로컬 `main` 이 작업 중에 두 번
움직였다(`8ddc8fd` → `1172b9b` → `b11f011`). 최종 base 는 `b11f011` 이다. `git diff --check main...HEAD` exit 0,
작업 트리 clean. 전용 자원만 썼다: DB `chosung_daily_test_t31`, Redis DB 5,
마이그레이션 DB `chosung_daily_test_t31_migrations`. 접속 문자열의 인증 값은
문서에 싣지 않는다. 공용 테스트 DB 는 비우지도, 접속하지도 않았다.
`review/impl-review-31.md` 는 수정하지 않았다.

### 티켓 30 통합 (rebase 기준이 두 번 움직였다)

리뷰가 쓴 기준은 `main = 8ddc8fd` 였는데, 이 라운드 작업 중에 로컬 `main` 이
**두 번** 움직였다: `1172b9b`(티켓 38 머지) → `b11f011`(티켓 30 앱 로컬 알림
머지). D-31-4 수정과 전체 테스트(flutter 480 / pytest 1412)는 `1172b9b` 위에서
돌렸고, 그 뒤 `b11f011` 위로 다시 올렸다. 티켓 30 과는 충돌 5곳이 났고,
코디네이터 확인을 받아(옵션 A) 아래처럼 **양쪽을 더해서** 해소했다.

| 충돌 | 해소 |
|---|---|
| `mobile/android/app/src/main/AndroidManifest.xml` | 알림 리시버 2개(30, `ScheduledNotificationReceiver`·`...BootReceiver`)와 AdMob `APPLICATION_ID` meta-data(31)를 **둘 다** 둔다. 서로 다른 선언이라 더하기로 끝난다 |
| `mobile/lib/main.dart` (import) | `notification_bootstrap.dart`(30)와 `flutter/foundation.dart`(31, `defaultTargetPlatform`) 둘 다 |
| `mobile/lib/main.dart` (ProviderScope overrides) | `notificationBootstrapProvider`(30)와 `adServiceProvider = GoogleAdService(...)`(31) 둘 다. 시작 순서는 30 이 정한 Firebase → 국제화 → 알림 → runApp 그대로 |
| `mobile/lib/screens/records_tab.dart` (S4 설정 리스트) | 두 티켓이 **서로의 자리를 "준비 중" 행으로** 들고 있었다. 30 의 실제 `_NotificationRows()` + 31 의 조건부 광고 개인정보 행을 둘 다 실제 위젯으로 둔다. 개인정보 행은 `showsPrivacyOptions` 가 false 면 **구분선까지 같이** 숨겨 빈 칸을 안 남긴다. 쓰이지 않게 된 `pending` 지역 변수 1줄 제거(analyze 가 잡는다) |
| `.scratch/store-launch/spec.md` | 30 의 미정 6 항목과 31 의 미정 24 항목 둘 다 |
| `test/golden/records_light_390.png`, `records_tablet_1024.png` | 아래 골든 갱신 |

**골든 3장 갱신**(`flutter test --update-goldens test/golden/ranking_records_golden_test.dart`).
충돌한 2장에 더해 `records_notification_off_390.png`(30 의 "알림 꺼짐" 장면)도
같은 이유로 바뀌어 3장이 됐다. 바뀐 내용은 **두 티켓의 자리 채우기가 서로
교차한 결과**다:

- 들어온 것(30): "일일 알림 — 오전 9:00" 행, "리마인더" 스위치 행,
  "그 날 안 풀었으면 저녁 8시에 한 번 더" 힌트 줄, (권한 꺼진 장면에서는)
  "알림 꺼짐 — 시스템 설정에서 켜기" 안내.
- 빠진 것(31): "광고 개인정보 설정 — 준비 중" 자리 행. 골든 환경은 UMP
  privacy options 가 required 가 아니라 **행이 아예 없는 게 맞다**(SCREENS S4,
  스펙 §B.23). required 인 경우의 노출은 골든이 아니라
  `test/screens/records_ad_privacy_test.dart` 가 지킨다(통과).
- 픽셀 차이: `records_light_390` 3.84%(12,643px), `records_tablet_1024`
  5.15%(40,480px), `records_notification_off_390` 1.01%(3,327px). 3장 모두
  직접 열어 레이아웃(폰 1열 / 태블릿 T4 2열)과 구분선·빈 칸을 확인했다.

**통합 때문에 고친 테스트 1개.** `test/config/bootstrap_test.dart`
"시작 트리가 실제 광고 SDK 를 끼운다"(31)가 `initializeNotificationsFn` 을 안 줘서
머지 뒤 **실제** 알림 초기화를 타고 실패했다. 티켓 30 자신의 테스트와 같은 방식
(`NotificationBootstrap(available: false, ...)`)으로 대신한다 — 이 테스트가 보는
건 광고 override 하나뿐이고, 실제 초기화는 플랫폼 채널을 탄다.

**남은 실패 1건은 내 것이 아니다 — main 의 시각 의존 테스트.**
`test/notifications/notification_controller_test.dart` "앱 시작 OS 에 권한 상태를
물어보고 그 결과로 예약한다"(티켓 30)가 실패한다. `git archive main(b11f011)` 로
`mobile/` 만 꺼내 **티켓 31 코드가 하나도 없는 복사본**에서 돌려도 같은 실패다:

```
$ git archive main mobile | tar -x -C /tmp/.../mainchk && cd /tmp/.../mainchk/mobile
$ flutter pub get && flutter test test/notifications/notification_controller_test.dart
00:07 +0 -1: 앱 시작 OS 에 권한 상태를 물어보고 그 결과로 예약한다 [E]
  Expected: [ ... ]
    Actual: MappedListIterable<ScheduledNotification, NotificationKind>:[ ... ]
     Which: at location [0] is NotificationKind:<NotificationKind.reminder>
            instead of NotificationKind:<NotificationKind.daily>
00:07 +17 -1: Some tests failed.                        # exit 1
```

원인은 `notification_plan.dart:154` 가 예약을 **발화 시각 순**으로 정렬
(`plan..sort((a, b) => a.when.compareTo(b.when))`)하는데 테스트가
`[daily, 7×reminder]` 순서를 고정한 것이다. 기본 일일 알림 09:00 이 지난 시각에
돌리면(이 검증은 09:13 KST) 다음 daily 는 **내일** 09:00, 첫 reminder 는 **오늘**
20:00 이라 reminder 가 앞선다 — 09:00~20:00 사이에는 항상 실패한다. 티켓 30 의
파일이고 이 티켓의 결함 수정 범위가 아니라 **고치지 않고** 코디네이터에
에스컬레이션했다(`escalation: main(b11f011) 의 티켓 30 테스트 1건이 시각 의존
플래키`). 고친다면 티켓 30 쪽에서 `now` 를 주입하거나 순서 대신 집합으로 비교하면 된다.

### 최종 검증 (티켓 30 통합 후, main = b11f011)

```
$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 166 files (0 changed) in 0.23 seconds.        # exit 0

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 3.7s)

$ cd mobile && flutter test
test/notifications/notification_controller_test.dart: 앱 시작 OS 에 권한 상태를 물어보고 그 결과로 예약한다 [E]
00:41 +550 -1: Some tests failed.
# 실패 1건은 위의 main 시각 의존 테스트(티켓 30)다. 티켓 31 의 테스트는 전부 통과한다.

$ cd mobile && flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk    # exit 0 — 알림 리시버 + AdMob meta-data 가 같이 들어간 매니페스트로 빌드된다
```

백엔드(`app/`, `web/`, `tests/`, `migrations/`, `.env.example`)는 이 라운드에 한 줄도
바뀌지 않았고 `1172b9b`→`b11f011` 사이에도 변경이 없어(`git diff` 빈 결과)
위의 pytest 1412 통과가 최종 트리에 그대로 해당한다 — 코디네이터 확인을 받아
재실행하지 않았다. 마이그레이션 변경이 없어 조건부 `flask db heads` 는 해당 없음.
`git merge-base main HEAD == main`(= `b11f011`), `git diff --check main...HEAD` exit 0,
작업 트리 clean.

## 수정 라운드 3

리뷰 `review/impl-review-31.md` "라운드 3" 의 판정 **FAIL — 신규 MAJOR 2건
(D-31-5·D-31-6), BLOCKER 0 / MINOR 0 / REPEAT 0**. 두 건 모두 결함으로 인정해
고쳤고, 각각 리뷰에 적힌 재현 순서를 **실패하는 테스트로 먼저 고정**한 뒤 원인을
고쳤다. 아래 "증명" 칸은 수정 전 그 테스트가 실제로 실패하는 출력(RED)과 수정 후의
통과 출력(GREEN) 둘 다다 — RED 는 테스트만 둔 채 `lib/` 수정만 임시로 되돌려 받았다.

코디네이터가 이 라운드에 세 가지를 더 지시했고(**"한 라운드에 결함 하나씩 나오는
패턴을 끊어라"**), 세 가지 모두 이 절에 반영했다:

1. D-31-5 는 검사와 기록을 두 단계로 나누지 말고 **광고 요청을 시작하는 순간
   원자적으로 예약**한다 — 실패 시 예약을 풀지 않는 정책을 골랐고 근거를 적었다.
2. D-31-6 은 보드를 바꾸는 모든 비동기 경로를 **하나의 직렬화 지점**으로 모았다 —
   컨트롤러 클래스 주석의 두 줄 규칙과 `_writingBoard`/`_refreshQueued`/
   `_endBoardWrite`/`_readBoard` 네 자리다.
3. 이 컨트롤러·전면 광고의 **경로 쌍을 표로 만들고 빈 칸을 지연 Fake 테스트로
   메웠다** — 아래 "경로 쌍 표".

이 라운드는 리뷰 라운드 3 이후 움직인 **로컬 `main` = `d78e082`(티켓 29 머지)**
위로 rebase 하는 작업까지 포함한다. §수정 라운드 3 끝의 "통합" 절에 그 충돌 해소를
적었다.

### D-31-5 — MAJOR — 전면 로드 중 결과 시트 재진입으로 같은 퍼즐 광고 중복 노출

**원인.** 노출 기록(`InterstitialStore`)은 광고가 **닫힌 뒤**에 남는다
(`result_interstitial.dart` 의 `markShown` 은 `showInterstitial()` 을 await 한
다음 줄이다). 그래서 "기록을 읽고 → 광고를 띄우고 → 기록을 남긴다" 사이에 창이
있고, 그 창에서 들어온 두 번째 호출도 `hasShown == false` 를 읽어 **자기 광고를
따로 로드**한다. `GoogleAdService.showInterstitial` 은 로드가 끝나면 기록을 다시
보지 않고 바로 표시하므로, 두 번째 로드가 첫 광고가 닫힌 뒤에 완료되면 같은 퍼즐에서
두 번 뜬다. `_openResult` 의 `await` 는 자기 호출만 기다리고 "결과 보기" 버튼을
잠그지 않으므로 사용자는 그 창에서 시트를 다시 열고 닫을 수 있다. 저장 용량(D-31-1)
과 무관한 **검사-후-행동(check-then-act) 경합**이다.

**수정** (`mobile/lib/ads/result_interstitial.dart`,
`mobile/lib/ads/interstitial_store.dart`). 코디네이터 지시대로 **검사와 기록을 두
단계로 나누지 않는다**. 두 겹으로 막는다:

1. **떠 있는 호출을 퍼즐별로 들고 있다**(`Map<int, Future<bool>> _showing`). 같은
   퍼즐의 두 번째 호출은 **그 future 를 그대로 받는다** — 지도에 넣는 건 첫 `await`
   전의 동기 구간이라 두 호출이 같이 통과할 틈이 구조적으로 없다. 두 번째 호출도
   방금 뜬 그 광고의 결과를 받으므로 호출부의 반환값 의미가 바뀌지 않는다.
2. **광고를 요청하기 전에 저장소에 예약한다.** `InterstitialStore` 의 뜻을
   "띄웠다"(`hasShown`/`markShown`)에서 **"그 퍼즐의 한 번을 썼다"**
   (`hasReserved`/`reserve`)로 바꾸고, `showInterstitial()` **앞**으로 옮겼다.
   광고가 뜬 채로 앱이 죽어 표시 결과를 못 받아도 다시 켤 때 또 뜨지 않는다 —
   메모리 지도로는 못 막는 경우다. 저장 키(`interstitial_shown_puzzle_ids`)는 담는
   것과 타입이 같고 이 티켓은 아직 출시 전이라 그대로 뒀다.

**실패 정책 (코디네이터가 적으라고 한 항목).** **로드·표시가 실패해도 예약을 풀지
않는다** — 그 퍼즐의 한 번은 쓴 것으로 센다. 이전 동작(실패면 기록 없음)을 바꾼
것이고, 바꾼 이유는 둘이다. ① 풀어 주면 "결과 보기" 를 누를 때마다 실패한 로드를
다시 요청해 같은 퍼즐에서 몇 번이고 AdMob 을 때린다(무효 트래픽). ② "퍼즐당 1회" 의
경계가 **실패 횟수에 따라 흐려져** 리뷰가 세 라운드 동안 같은 자리를 다시 짚게 된다.
잃는 건 실패한 노출 한 번뿐이다. 바뀐 테스트는
`result_interstitial_test.dart` "광고가 뜨지 않아도 그 퍼즐의 한 번은 쓴 것이다"
(이전 이름 "광고가 뜨지 않으면 퍼즐 플래그를 남기지 않는다").

**증명.** 재현 테스트 `mobile/test/ads/result_interstitial_test.dart`
"전면 광고가 떠 있는 동안 시트를 다시 닫아도 퍼즐당 1회다". 리뷰의 "첫 로드를
지연한다" 를 표현하려고 `FakeAdService.interstitialGate`(Completer)를 더했다 —
`fetchTodayPuzzleGate` 와 같은 방식이다. 첫 호출을 **await 하지 않고** 두 번째를
부르고, 그 뒤 gate 를 풀어 두 호출을 모은다.

```
# 수정 전(테스트만 둔 채 lib/ 되돌림) — RED
$ cd mobile && flutter test --no-pub test/ads/result_interstitial_test.dart
전면 광고가 떠 있는 동안 시트를 다시 닫아도 퍼즐당 1회다 [E]
  Expected: <1>
    Actual: <2>
  같은 퍼즐에서 두 번 띄우면 안 된다
  test/ads/result_interstitial_test.dart 99:5

# 수정 후 — GREEN (예약 정책 2건 포함 10개)
$ cd mobile && flutter test --no-pub test/ads/result_interstitial_test.dart
+10: All tests passed!
```

예약을 **요청 전에** 적는다는 것 자체도 테스트로 고정했다 —
"표시 결과를 받기 전에 이미 예약이 적혀 있다"(gate 로 광고를 붙잡은 상태에서
`store.reserved == {41}` 을 확인) 와 "광고가 뜨지 않아도 그 퍼즐의 한 번은 쓴
것이다"(실패 뒤 두 번째 호출이 로드를 또 때리지 않는다). 저장소 자체의 순수 계산은
`interstitial_store_test.dart` 4개가 이름만 바뀐 채 그대로 통과한다.

### D-31-6 — MAJOR — 힌트 요청 중 복귀 재조회가 성공한 힌트를 다시 잠근다

**원인.** `refresh()` 는 `_submitting` 만 보고 미룬다. 힌트가 떠 있는 동안에도
세대를 올리고 `GET /puzzles/today` 를 보내는데, 그때 서버 보드엔 방금 연 힌트가
**아직 없다**(hint-unlock 쓰기가 끝나지 않았다). 힌트 성공은 세대를 바꾸지 않고 같은
퍼즐의 보드에 그 칸만 병합하므로(r2 D-31-4 수정), 뒤늦게 도착한 GET 이 최신 세대로
인정돼 `_commitLoad` 가 보드를 통째로 `hint=null`·`hintUnlocked=false` 로 갈아
끼운다. HintCard 는 다시 광고 버튼을 띄우고 비구독자는 **이미 산 같은 힌트에 보상형을
다시 봐야 한다**(US 4·5a). 원인은 세대 번호가 아니라 **힌트 쓰기가 끝나기 전에 조회를
보낸 것** 이고, 제출(`_refreshQueued`)이 이미 같은 이유로 같은 처방을 쓰고 있었다.

**수정** (`mobile/lib/puzzle/today_puzzle_controller.dart`). 코디네이터 지시대로
경로마다 조건을 따로 쓰지 않고 **직렬화 지점 하나**로 모았다. 클래스 주석에 규칙을
두 줄로 적어 두고, 코드에서는 네 자리가 그 규칙의 전부다:

| 자리 | 하는 일 |
|---|---|
| `bool get _writingBoard => _submitting \|\| _unlockingHint` | **읽기를 미룰지 판정하는 단 하나의 조건.** 쓰기를 하나 더할 때 조건을 다시 쓰다가 한 곳을 빼먹는 길을 없앴다 |
| `bool _refreshQueued` | 쓰기 때문에 미뤄둔 읽기. 제출·힌트가 **같은 큐**를 쓴다 |
| `void _endBoardWrite()` | 쓰기가 끝나면(성공·실패 모두) 미뤄둔 읽기를 돌리는 **단 하나의 자리.** 제출·힌트의 `finally` 가 각자 복사해 갖고 있던 4줄을 여기로 합쳤다 |
| `Future<void> _readBoard(generation, {notice})` | 읽기 응답이 `_commitLoad` 로 가는 **단 하나의 통로.** 복귀 재조회·계정 경계·제출 409·힌트 뒤 재조회가 전부 이걸 쓴다 |

규칙 자체는 두 줄이다. **① 쓰기가 떠 있으면 읽기를 미룬다**(지금 읽는 서버 보드엔
방금 보낸 답·힌트가 아직 없다) — 미루는 것이지 버리는 것이 아니라서 복귀 재조회는
쓰기 뒤에 반드시 한 번 돌아간다. **② 읽기가 떠 있으면 쓰기가 세대를 올려 그 응답을
버린다**(읽기는 보드를 통째로 갈아 끼우므로 쓰기보다 과거면 쓸 수 없다). 쓰기 응답은
세대로 버리지 않고 `_boardFor` 로 **지금의 보드에 병합**한다(r2 D-31-4). 그래서 "늦은
응답이 더 최신 성공 상태를 덮는" 길이 두 방향 모두 막힌다 — D-31-6 은 ①이 힌트에
빠져 있어서 생긴 구멍이었다.

`_reloadAfterHint`(409·끝난 퍼즐·바뀐 퍼즐 경로)는 자기가 그 조회를 하므로
`_refreshQueued` 를 소비해 바로 뒤에 같은 GET 을 또 보내지 않는다.

**증명.** 재현 테스트 `mobile/test/puzzle/today_puzzle_controller_test.dart`
"힌트를 기다리는 동안 떠난 복귀 재조회가 열린 힌트를 되돌리지 않는다". 리뷰의 순서를
그대로 쓴다: `unlockHintGate` 로 힌트를 붙잡고 → `refresh()` → `fetchTodayPuzzleGate`
로 GET 응답을 붙잡아 힌트보다 늦게 도착하게 만들고 → 서버 보드에 힌트를 쓴 뒤 힌트
응답을 풀고 → 마지막에 GET 응답을 푼다. 눈에 보이는 증상(사라진 힌트)을 먼저 재고
미룸 여부(호출 수)는 뒤에서 확인한다.

```
# 수정 전(테스트만 둔 채 lib/ 되돌림) — RED. 리뷰가 적은 "실제" 그대로다.
$ cd mobile && flutter test --no-pub test/puzzle/today_puzzle_controller_test.dart \
    --plain-name '힌트를 기다리는 동안 떠난 복귀 재조회가 열린 힌트를 되돌리지 않는다'
응답 경합 힌트를 기다리는 동안 떠난 복귀 재조회가 열린 힌트를 되돌리지 않는다 [E]
  Expected: '서울에 가장 많다'
    Actual: <null>
     Which: not an <Instance of 'String'>
  서버가 연 힌트를 잃으면 안 된다
  test/puzzle/today_puzzle_controller_test.dart 517:7

# 수정 후 — GREEN (기존 경합 테스트 포함 29개)
$ cd mobile && flutter test --no-pub test/puzzle/today_puzzle_controller_test.dart
+29: All tests passed!
```

### 경로 쌍 표 (코디네이터 지시 3)

보드·전면 광고를 바꾸는 비동기 경로를 쌍으로 모두 적고, 각 쌍을 **지연 Fake**
(`unlockHintGate`·`submitGuessGate`·`fetchTodayPuzzleGate`·`interstitialGate`)로
고정했다. "A 가 떠 있는 동안 B 가 시작" 순서다.

| A(떠 있음) × B(시작) | 규칙 | 고정 테스트 | 이번 추가 |
|---|---|---|---|
| 첫 조회 × 복귀 재조회 | 두 번째 조회를 아예 띄우지 않는다 | `첫 조회가 끝나기 전의 복귀는 그 조회를 기다린다 — 두 번 읽지 않는다` | |
| 첫 조회 × 제출 / 힌트 | 보드를 모르면 쓸 자리가 없다 — 서버로 안 보낸다 | `첫 조회가 끝나기 전에는 제출도 힌트도 서버로 가지 않는다` | **추가** |
| 복귀 재조회 × 복귀 재조회 | 나중에 떠난 쪽이 이긴다(세대) | `느린 재조회 뒤에 떠난 재조회가 이긴다` | |
| 복귀 재조회 × 제출 | 쓰기가 세대를 올려 늦은 조회를 버린다 | `제출 전에 떠난 조회가 늦게 도착해도 쌓인 행을 지우지 않는다` | |
| 복귀 재조회 × 힌트 | 같음 — 늦은 조회가 열린 힌트를 지우지 못한다 | `힌트보다 먼저 떠난 재조회가 늦게 도착해도 열린 힌트를 지우지 않는다` | **추가** |
| 제출 × 복귀 재조회 | 조회를 미루고 제출 뒤에 돌린다 | `제출을 기다리는 동안엔 재조회가 보드를 건드리지 않는다 — 잠금도 유지된다` | |
| 제출 × 힌트 | 힌트를 제출 뒤로 **줄 세운다**(버리지 않는다) | `제출을 기다리는 동안 힌트를 열어도 쌓인 행과 힌트가 모두 남는다`, `제출 대기 중 힌트가 실패해도 제출 결과와 잠금 해제가 남는다` | |
| 제출 × 제출 | 보드의 `submitting` 잠금이 두 번째를 끊는다 | `제출 응답을 기다리는 동안 다시 제출해도 서버로 한 번만 간다` | **추가** |
| 힌트 × 제출 | 힌트 응답을 세대로 버리지 않고 지금 보드에 병합(r2 D-31-4) | `힌트를 기다리는 동안 제출이 실패해도 열린 힌트는 보드에 남는다`, `…제출이 성공하면 쌓인 행과 힌트가 모두 남는다`, `제출 응답보다 힌트가 먼저 와도 제출이 그 힌트를 덮어 지우지 않는다` | |
| 힌트 × 복귀 재조회 | **조회를 미루고 힌트 뒤에 돌린다(D-31-6 이 이 칸이었다)** | `힌트를 기다리는 동안 떠난 복귀 재조회가 열린 힌트를 되돌리지 않는다` | **추가** |
| 힌트 × 힌트 | 컨트롤러는 막지 않는다 — **화면이** 응답 대기 중 버튼을 끈다 | `힌트를 여는 동안에는 버튼이 꺼져 있다`(위젯) | **추가** |
| 힌트 409 뒤 재조회 × 제출 | 재조회를 새 세대로 써서 서버가 연 힌트를 받는다 | `힌트가 이미 열려 있었다는 409 는 제출이 끼어들어도 보드를 다시 읽는다` | |
| 전면 광고 × 결과 시트 재진입 | **떠 있는 호출에 같은 future 를 돌려준다(D-31-5 가 이 칸이었다)** | `전면 광고가 떠 있는 동안 시트를 다시 닫아도 퍼즐당 1회다` | **추가** |
| 전면 광고 × 앱 재시작 | 요청 **전에** 예약하므로 표시 결과를 못 받아도 다시 안 뜬다 | `표시 결과를 받기 전에 이미 예약이 적혀 있다`, `이미 띄운 퍼즐은 다시 시작해도 건너뛴다` | **추가** |
| 전면 광고 × 언어 왕복 | 퍼즐 ID 목록을 들고 있다(r1 D-31-1) | `언어를 왕복해도 퍼즐마다 1회다` | |
| 계정 경계(`discard`) × 떠 있는 조회·제출 | 세대 + 계정 epoch 로 남의 응답을 버린다 | 티켓 29 의 `account_controller_test`·`records_account_test` 가 소유 — 이 티켓은 `discard()` 가 `_unlockingHint` 도 같이 비우게 한 줄만 더했다 | |

빈 칸 없이 모든 쌍에 고정 테스트가 있다. **컨트롤러 테스트 35개 · 전면 광고 테스트
10개 · 오늘 탭 광고 위젯 테스트 14개**가 전부 통과한다(아래 최종 검증).

> **라운드 4 정정.** 이 표의 마지막 행("계정 경계 × 떠 있는 조회·제출")이 **힌트와
> 전면을 빼고** 있었고, 그 빈 칸이 그대로 r4 D-31-7 이었다. 쓰기 입구를 하나 더할
> 때 표의 열이 아니라 **행**도 같이 늘려야 한다 — 보강한 표는
> §수정 라운드 4 의 "경로 쌍 표 — 계정 경계 행 보강" 이다.

### 고치지 않은 지적

- **`google_ad_service.dart:28` 이 SDK `canRequestAds()` 대신 `getConsentStatus()`
  를 읽는다** (라운드 1·3 "증거 부족"). 리뷰어가 두 라운드 모두 "실제 오노출을
  단정하지 않아 **별도 결함 수에 넣지 않았다**" 로 명시했고 이번 라운드 결함 목록
  (D-31-5·D-31-6)에도 없다. 고치려면 `UmpStatus` 가 SDK 의 허용값을 직접 실어야
  하고, 그러면 `ad_gate.dart:30` 의 순수 판정과 UMP 4종·구독자·ATT 테스트 전부가
  같이 바뀐다 — 결함 수정 범위를 넘는 설계 변경이라 이 라운드에서 하지 않았다.
  실측(실기기 UMP 재선택)이 없으면 어느 쪽도 증명되지 않는 항목이기도 하다.
  스펙 "미정 항목" 으로 남긴다.
- **MINOR 0건** 이라 "미수정 MINOR" 는 없다.

### 통합 — 로컬 `main` = `d78e082`(티켓 29 머지) 위로 rebase

리뷰 라운드 3 의 기준 main 은 `b11f011` 이었는데 그 뒤 티켓 29(앱 계정 연결·전환·
백업 코드·삭제)가 머지돼 `d78e082` 가 됐다. 15개 커밋을 그 위로 rebase 하며 해소한
충돌은 전부 **양쪽 의도를 같이 살리는** 쪽으로 끝냈다:

| 파일 | 충돌 | 해소 |
|---|---|---|
| `mobile/lib/api/api_exception.dart` | 29 의 `INVALID_ID_TOKEN`·`ACCOUNT_ALREADY_LINKED` 와 31 의 `HINT_ALREADY_UNLOCKED`·`ALREADY_FINISHED` 가 같은 자리에 추가 | 네 예외·네 코드 매핑 모두 유지. 주석의 "뒤 티켓" 은 남은 `32·33` 으로 갱신 |
| `mobile/pubspec.yaml`·`pubspec.lock` | `google_sign_in`(29) vs `google_mobile_ads`(31) | 둘 다 유지, `flutter pub get` 으로 lock 재생성 |
| `mobile/test/fakes/fake_api_client.dart` | 29 의 토큰 교환·백업 코드 필드 vs 31 의 `hintUnlockResponse`·`unlockHintError` | 양쪽 전부 유지 |
| `mobile/lib/config/app_env.dart` | 29 의 `googleServerClientId` vs 31 의 AdMob 유닛 ID 3종 | 양쪽 전부 유지 |
| `mobile/lib/screens/records_tab.dart` | import 블록 | 양쪽 전부 유지 |
| `mobile/lib/screens/today_tab.dart` | 29 가 `_openResult` 에 `onLinkAccount` 추가 vs 31 이 "시트 닫힌 뒤 전면 광고" 로 바꿈 | 둘 다 — `onLinkAccount` 를 넘기고, 시트가 닫힌 뒤 `showAfterResultSheet` 를 부른다 |
| `mobile/ios/Flutter/{Debug,Release}.xcconfig` | 29 의 `#include? "Secrets.xcconfig"` vs 31 의 `CLANG_ALLOW_NON_MODULAR_INCLUDES_IN_FRAMEWORK_MODULES` | 양쪽 전부 유지 |
| `mobile/lib/puzzle/today_puzzle_controller.dart` | 29 가 `_load()` 를 `Future<AsyncValue<TodayState?>?>` 로 바꿔 호출부가 `AsyncValue.guard(_load)` 를 더 쓰지 않는다 / 29 의 `_accountEpoch`·`discard()` 와 31 의 `_submitDone`·`_unlockingHint`·`_reloadAfterHint` 가 같은 자리 | 31 의 호출부 4곳을 `await _load()` 로 맞추고 필드·분기는 양쪽 전부 유지 |
| `mobile/test/golden/records_{light_390,tablet_1024,notification_off_390}.png` | 29 의 계정 카드와 31 의 광고 개인정보 행이 같은 화면 | `flutter test test/golden --update-goldens` 로 재생성 후 골든 17장 전부 통과 확인 |

rebase 중 드러난 두 줄도 같은 커밋에 담았다 — 둘 다 29 와 31 이 만나서 생긴 것이다:

- `discard()`(29, 계정 경계에서 보던 보드를 버린다)가 `_submitting`·`_refreshQueued`
  를 비우면서 `_unlockingHint` 는 안 비우면, 계정이 바뀐 직후의 복귀 재조회가 옛
  계정의 힌트 응답이 돌아올 때까지 미뤄진다. 같은 자리에 한 줄 더해 같이 비운다.
- `today_tab_ads_test` 의 결과 시트가 29 의 "계정 연결" 안내를 읽으면서
  `flutter_secure_storage` 플랫폼 채널을 타 `MissingPluginException` 으로 깨졌다.
  다른 29 테스트들과 같이 `localFlagStoreProvider` 를 `InMemoryLocalFlagStore` 로
  덮는다.

### 최종 검증 (main = `d78e082`)

```
$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 178 files (0 changed) in 0.21 seconds.        # exit 0

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 2.3s)                          # exit 0

$ cd mobile && flutter test
00:22 +629: All tests passed!                           # exit 0
# 이 라운드가 더한 테스트 6개(경로 쌍 표의 "추가" 5칸 + 전면 예약 1개) 포함.
# 라운드 2 에서 에스컬레이션한 티켓 30 의 시각 의존 테스트도 이번 실행 시각에는 통과했다.
# 그 플래키는 여전히 티켓 30 쪽 문제이고 이 티켓은 건드리지 않았다(코디네이터도 무시 지시).

$ cd mobile && flutter build apk --debug
Running Gradle task 'assembleDebug'...                             56.5s
✓ Built build/app/outputs/flutter-apk/app-debug.apk     # exit 0
# 확인 후 mobile/build 는 지웠다(이전 라운드와 같다).

$ uv run ruff check .
All checks passed!                                      # exit 0

$ TEST_DATABASE_URL=...chosung_daily_test_t31 TEST_REDIS_URL=redis://127.0.0.1:6379/5 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t31_migrations uv run pytest -q
........................................ [100%]
1412 passed in 954.09s (0:15:54)                        # exit 0

$ git diff --check main...HEAD                          # exit 0
```

백엔드 pytest 는 리뷰가 지정한 전용 자원(DB `chosung_daily_test_t31`, Redis DB 5,
마이그레이션 DB `chosung_daily_test_t31_migrations`)으로 **rebase 된 트리에서 다시
돌렸다**(위 출력). 공용 테스트 DB 는 비우지 않았고 새 DB 를 만들지도 않았다. 그 뒤의
변경은 `mobile/` 과 이 문서뿐이다 —
`git diff main...HEAD -- app/ web/ tests/ migrations/ .env.example` 는 빈 결과이고
마이그레이션 변경이 없어 조건부 `flask db heads` 는 해당 없음.
`git merge-base main HEAD == main`(= `d78e082`), 작업 트리 clean.

## 수정 라운드 4

리뷰 라운드 4(Codex, FAIL)의 지적은 **MAJOR 1건(D-31-7), BLOCKER 0 / MINOR 0 /
REPEAT 0** 이다. 결함으로 인정해 고쳤고, 리뷰에 적힌 재현 순서를 **실패하는
테스트로 먼저 고정한 뒤** 원인을 고쳤다("증명" 칸은 수정 전 RED 출력과 수정 후
GREEN 출력 둘 다 — RED 는 테스트만 둔 채 `lib/` 수정 두 파일을
`git checkout` 으로 임시로 되돌려 받았다).

코디네이터가 이 라운드에 두 가지를 지시했고(사용자 승인) 둘 다 반영했다:

1. **새 장치를 만들지 말고 티켓 29 의 계정 세대 장치를 재사용한다** —
   `accountEpochProvider`·`sendIfSameAccount`·`fetchIfSameAccount`
   (`mobile/lib/guest/account_epoch.dart`, main 에 이미 있다). 요청 시점 세대와
   응답 시점 세대가 다르면 응답을 보드에 반영하지 않는다. 아래 수정은 이 세 개
   말고 아무것도 새로 만들지 않는다(추가한 것은 `_sameAccount(epoch)` 한 줄짜리
   비교 헬퍼뿐이고, 그것도 `_account.state` 를 읽는다).
2. **경로 쌍 표에 "계정 경계 × (조회·재조회·제출·힌트·전면)" 행을 추가해 빈 칸을
   지연 Fake 테스트로 모두 메운다** — 아래 "경로 쌍 표 — 계정 경계 행 보강".
   표를 메우는 과정에서 같은 부류 1건(전면 광고 세션 플래그)이 더 드러나 같이
   고쳤다.

### D-31-7 — MAJOR — 계정 전환 전에 요청한 힌트 응답이 새 계정 보드를 연다

**원인.** 쓰기 응답이 보드에 올라가는 판정이 **계정을 보지 않는다**. 힌트 응답은
세대(`_generation`)로 버리지 않는 게 r2 D-31-4 의 결론이고(그 사이 제출이 끝났다는
이유로 버리면 서버가 이미 연 힌트를 화면이 잃는다), 그래서 남은 판정은
`_boardFor(puzzleId)` 의 **퍼즐 번호 비교 하나**였다. 그런데 `puzzle_id` 는
날짜·언어로만 갈리는 **게스트 공용 번호**다(`app/services/puzzle_service.py` —
계정 식별자가 아니다). 계정을 바꿔도 같은 날 같은 언어면 같은 번호이므로 비교가
통과하고, A 의 힌트가 B 보드에 `hint` + `hintUnlocked=true` 로 올라간다. 서버는
unlock 을 `guest_id + puzzle_id` 로 기록하므로(`app/services/hint_service.py`)
B 에게는 그 기록이 없고, 다음 재조회에서 힌트가 다시 잠긴다 — 서버 데이터 손상이
아니라 **화면이 남의 계정 상태를 섞어 보여 주는** 결함이다(US 19).

보내는 쪽도 같이 비어 있었다. 제출은 `sendIfSameAccount(_accountEpoch, …)` 로
쓰기 직전에 한 번 더 보지만(D-29-5), `unlockHint` 는 `_api.unlockHint` 를 직접
불렀다. 토큰만 바뀌는 입구(시작 흐름의 401 복구)는 보드를 버려 주지 않으므로, 옛
보드에서 누른 힌트가 **새 계정의 unlock 으로 서버에 기록**된다.

**수정** (`mobile/lib/puzzle/today_puzzle_controller.dart`). 세대와 **따로** 계정을
본다. 쓰기는 이제 두 번 계정을 지난다 — 보낼 때와 올릴 때다:

1. **보낼 때.** `unlockHint` 도 제출과 같은 문을 지난다 —
   `_account.sendIfSameAccount(epoch, () => _api.unlockHint(…))`. `unlockHint` 는
   `Future<String>` 이라 `null` 은 "보내지 않았다" 하나뿐이고
   (`sendIfSameAccount` 가 요구하는 전제다), 거절되면 제출과 같이 보드를 버린다
   (`discard()`).
2. **올릴 때.** 쓰기 응답의 단 하나의 commit 지점인 `_boardFor` 가 퍼즐 번호와
   **계정**을 같이 본다(`_boardFor(int puzzleId, int epoch)`). 제출·힌트 둘 다
   떠날 때의 `_accountEpoch` 를 **지역 변수로 고정**해서 넘긴다 — 필드는 그 사이
   끼어든 조회(`_load`)가 덮어쓰므로 보낼 때와 올릴 때가 다른 값을 보게 된다.
3. **쓰지 않는 것만으로는 모자란 자리.** 응답이 남의 것이면 보고 있는 보드도 남의
   것이다. 제출은 `state` 에 `submitting: true` 를 이미 올려 둔 상태라 그냥
   돌아가면 **입력이 영구히 잠긴** 옛 계정 보드가 남는다. 그래서 제출 성공
   경로·제출 실패 안내 경로(`_commitNotice`)·힌트 경로 모두 계정이 바뀌었으면
   `discard()` 로 보드를 버린다(= 새 계정 보드를 읽는다). 비교는 `_sameAccount`
   한 자리에 모았다.

**증명.** 리뷰가 적어 준 Fake 재현 절차를 그대로 테스트 2개로 옮겼다
(`mobile/test/puzzle/today_puzzle_controller_test.dart`).

```
# RED (테스트만 두고 lib/puzzle/today_puzzle_controller.dart 를 되돌린 상태)
$ flutter test test/puzzle/today_puzzle_controller_test.dart --plain-name "계정이 바뀐 뒤"
00:08 +1 -1: 계정이 바뀐 뒤 도착한 힌트 응답은 새 계정 보드를 열지 않는다 [E]
  Expected: false
    Actual: <true>
  남의 응답은 "열렸다" 로 세지 않는다
00:08 +1 -2: 계정이 바뀐 뒤에는 옛 보드로 힌트를 열지 않는다 [E]
  Expected: false
    Actual: <true>
00:08 +1 -2: Some tests failed.

# 같은 RED 에서 반환값 검사를 한 줄 미루고 **보드 증상**을 직접 본 출력
  Expected: null
    Actual: '서울에 가장 많다'
  A 의 힌트가 B 보드에 올라갔다          # ← B 의 보드에 A 의 힌트가 실제로 올라간다

# GREEN (수정 후)
$ flutter test test/puzzle/today_puzzle_controller_test.dart --plain-name "계정이 바뀐 뒤"
00:02 +3: All tests passed!
```

- `계정이 바뀐 뒤 도착한 힌트 응답은 새 계정 보드를 열지 않는다` — A 보드 로드 →
  `api.unlockHintGate` 로 힌트 응답을 붙잡고 → `replaceWith('guest-b')` →
  `discard()` 로 같은 `puzzle_id` 의 **잠긴 B 보드**를 읽고 → 게이트를 풀어 A 의
  성공 응답을 늦게 도착시킨다. 반환값이 `false` 이고 B 보드의 `hint` 는 `null`,
  `hintUnlocked` 는 `false` 로 남는다.
- `계정이 바뀐 뒤에는 옛 보드로 힌트를 열지 않는다` — 토큰만 바뀌는 입구(401
  복구)다. 새 계정 보드 조회를 붙잡아 옛 보드가 화면에 남은 그 순간에 힌트를
  누른다. `api.unlockedHintPuzzleIds` 가 비어 있다(= 새 계정으로 unlock 이 나가지
  않았다) 그리고 보드는 버려진다.

실제 계정·인증 정보는 입력하지 않았다 — 토큰은 `InMemoryGuestTokenStore` 의
문자열(`guest-a`/`guest-b`)이고 리뷰도 같은 구성을 지정했다.

### 표를 메우며 드러난 같은 부류 1건 — 전면 광고 세션 플래그

**원인.** `ResultInterstitial._submittedThisSession` 은 bool 하나였다. 이 플래그의
뜻은 "이번 실행에 **이 사람이** 제출했는가"(US 25)인데 계정을 모르므로, A 가
제출한 뒤 B 로 전환하면 **A 의 제출이 B 의 전면 광고가 된다** — B 가 다른 기기에서
이미 끝낸 보드를 열어 "결과 보기" 를 닫는 순간이다(`today_tab.dart:123` →
`_openResult` → `showAfterResultSheet`). `puzzle_id` 와 똑같이 이 플래그도 계정을
모르는 값이어서 생긴, D-31-7 과 같은 부류다. 리뷰가 짚은 건 아니고 코디네이터
지시 2(표의 빈 칸 메우기)로 "계정 경계 × 전면" 칸을 쓰면서 드러났다.

**수정** (`mobile/lib/ads/result_interstitial.dart`). bool 을 **제출한 계정의
세대**로 바꿨다(`int? _submittedEpoch`). `markSubmitted()` 가
`_ref.read(accountEpochProvider)` 를 적고, `_show` 는 그 값이 아직 지금 계정일
때만 통과시킨다. 여기서도 29 의 장치를 그대로 쓴다.

반대쪽(퍼즐 예약)은 **고치지 않는 것이 맞다** — `InterstitialStore` 는 기기 로컬이고
"노출은 기기에서 일어난다"(`interstitial_store.dart:37`)가 의도다. 계정 단위로
바꾸면 계정을 바꿔 가며 같은 퍼즐에 전면을 여러 번 띄우는 길이 열린다. 두 쪽을
각각 테스트로 못박았다.

**증명** (`mobile/test/ads/result_interstitial_test.dart`).

```
# RED (lib/ads/result_interstitial.dart 를 되돌린 상태)
00:03 +47 -5: 계정이 바뀌면 옛 계정의 제출로 전면 광고를 띄우지 않는다 [E]
  Expected: false
    Actual: <true>

# GREEN
$ flutter test test/ads/result_interstitial_test.dart
00:03 +13: All tests passed!
```

- `계정이 바뀌면 옛 계정의 제출로 전면 광고를 띄우지 않는다` — A `markSubmitted()`
  → `replaceWith('guest-b')` → B 의 시트를 닫아도 `interstitialShowCalls` 가 0 이고
  **B 의 퍼즐 예약도 쓰지 않는다**. B 가 직접 제출하면 그때 1회 뜬다.
- `계정이 바뀌어도 이미 쓴 퍼즐의 전면은 다시 뜨지 않는다` — 기기 단위 정책을
  고정한다. 이 테스트는 수정 전에도 통과했다(의도된 동작의 회귀 고정이다).

### 경로 쌍 표 — 계정 경계 행 보강 (코디네이터 지시 2)

라운드 3 표의 마지막 행은 "계정 경계 × 떠 있는 조회·제출" 뿐이었고, **힌트·전면이
빈 칸**이었다. 그 빈 칸이 D-31-7 이다. 지시대로 행을 다섯 칸으로 늘려 전부 지연
Fake 테스트로 메웠다. "추가" 는 이 라운드에서 새로 쓴 테스트다.

| 계정 경계 × | 어떻게 끊는가 | 고정 테스트 | |
|---|---|---|---|
| 첫 조회 | `build` 의 future 는 commit 을 못 건너므로 `initialStateOrCurrent` 가 지금 상태를 돌려줘 무해하게 만든다(D-29-6) | `첫 조회 중 계정이 바뀌면 그 응답은 보드가 되지 않는다`, `늦게 끝난 첫 조회는 새 계정의 오류 카드도 지우지 않는다` | |
| 복귀 재조회 | 읽기는 `fetchIfSameAccount` 가 `null`("쓰지 마라")로 가려낸다 | `복귀 재조회가 떠 있는 동안 계정이 바뀌면 그 응답은 새 보드를 덮지 않는다` | **추가** |
| 제출 (보내기 전) | `sendIfSameAccount` 가 요청을 **안 보내고** 보드를 버린다 | `계정이 바뀐 뒤에는 옛 보드로 제출하지 않는다` | |
| 제출 (떠 있는 응답) | 올릴 때 계정을 다시 보고 **보드까지 버린다** — 안 그러면 `submitting: true` 로 잠긴 남의 보드가 남는다 | `제출 응답을 기다리는 사이 계정이 바뀌면 그 응답도 보드도 버린다`, `제출이 실패로 끝나도 그 사이 바뀐 계정의 보드에는 안내를 올리지 않는다` | **추가** |
| 힌트 (보내기 전 / 떠 있는 응답) | **D-31-7 이 이 칸이었다** — 같은 문 두 개(`sendIfSameAccount` + `_boardFor` 의 계정 비교)를 지난다 | `계정이 바뀐 뒤에는 옛 보드로 힌트를 열지 않는다`, `계정이 바뀐 뒤 도착한 힌트 응답은 새 계정 보드를 열지 않는다` | **추가** |
| 전면 (세션 플래그) | 제출을 **계정별로** 센다(`_submittedEpoch`) | `계정이 바뀌면 옛 계정의 제출로 전면 광고를 띄우지 않는다` | **추가** |
| 전면 (퍼즐 예약) | **기기 단위가 의도다** — 계정이 바뀌어도 예약은 남는다(US 24) | `계정이 바뀌어도 이미 쓴 퍼즐의 전면은 다시 뜨지 않는다` | **추가** |

행이 늘어나는 규칙을 코드에도 적었다: 보드를 바꾸는 **쓰기 입구를 하나 더할 때**
세대·퍼즐 번호만 보면 안 되고 계정도 같이 봐야 한다는 두 문장을
`TodayPuzzleNotifier` 클래스 주석과 `_sameAccount`/`_boardFor` 주석에 남겼다.

### 고치지 않은 지적 (라운드 4)

- **`google_ad_service.dart:28` 이 SDK `canRequestAds()` 대신 `getConsentStatus()`
  를 읽는다** (라운드 1·3·4 "증거 부족"). 라운드 4 도 "실제 오노출로 단정해 신규
  결함으로 세지 않았다" 로 명시했다. 이유는 라운드 3 과 같다 — 고치려면 `UmpStatus`
  가 SDK 허용값을 직접 실어야 하고 `ad_gate.dart:30` 의 순수 판정과 UMP 4종·구독자·
  ATT 테스트가 전부 같이 바뀌는 설계 변경이다. 실기기 UMP 재선택 실측이 없으면
  어느 쪽도 증명되지 않는 항목이기도 하다. 스펙 "미정 항목" 에 남아 있다.
- **실기기 실측이 필요한 한계** — 배너 어댑티브 높이 실측, 실제 UMP 재선택 결과,
  실제 광고 렌더링, iOS 실행. 리뷰도 "별도 검증 한계" 로 분류했고 이 라운드에서도
  바뀌지 않았다.
- **MINOR 0건** 이라 "미수정 MINOR" 는 없다. 리뷰가 결함 수에 넣지 않고 참고로만
  적은 문서 1건은 아래처럼 **고쳤다**.

### 리뷰가 참고로 적은 문서 불일치 1건 (고쳤다)

라운드 4 "보안·범위·공유 파일과 참고" 의 지적: README 31절의 "광고가 실제로 뜨지
않았으면(로드 실패) 퍼즐 플래그를 남기지 않는다" 가 r3 D-31-5 수정 뒤의 정책
(요청 **전** 예약, 실패해도 풀지 않음)과 어긋난다. 맞는 지적이라 그 문단을 현재
정책과 근거(검사-후-행동 경합, 실패한 노출 한 번을 잃는 쪽을 고른 이유)로 바꿨다
(`README.md` "전면 광고는 플래그 두 개가 막는다"). 런타임 동작 변경은 없다.

### 최종 검증 (라운드 4, main = `d78e082`)

```
$ git rebase main
Current branch dosaem/t31-app-ads-gate-banner-interstitial-rewarded is up to date.
# 로컬 main 은 리뷰 라운드 4 의 기준(d78e082)에서 움직이지 않았다 — rebase 는 no-op.
# origin/main 은 쓰지 않았다.

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 4.1s)                          # exit 0

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 178 files (0 changed) in 0.23 seconds.        # exit 0

$ cd mobile && flutter test
00:41 +636: All tests passed!                           # exit 0
# 629 → 636. 이 라운드가 더한 테스트 7개(컨트롤러 5 + 전면 광고 2)다.
# 그중 5개는 수정 전 RED 였고(위 출력), 2개는 의도된 동작의 회귀 고정이다.

$ cd mobile && flutter build apk --debug
Running Gradle task 'assembleDebug'...                             66.2s
✓ Built build/app/outputs/flutter-apk/app-debug.apk     # exit 0
# 확인 후 mobile/build 는 지웠다(이전 라운드와 같다).

$ uv run ruff check .
All checks passed!                                      # exit 0

$ TEST_DATABASE_URL=...chosung_daily_test_t31 TEST_REDIS_URL=redis://127.0.0.1:6379/5 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t31_migrations uv run pytest -q
........................................ [100%]
1412 passed in 1116.67s (0:18:36)                       # exit 0

$ git diff --check main...HEAD                          # exit 0
```

백엔드 pytest 는 리뷰·티켓이 지정한 전용 자원(DB `chosung_daily_test_t31`,
Redis DB 5, 마이그레이션 DB `chosung_daily_test_t31_migrations`)으로 돌렸다. 공용
테스트 DB 는 비우지 않았고 새 DB 를 만들지도 않았다. 이 라운드의 변경은
`mobile/lib` 2개 · `mobile/test` 2개 · `README.md` · 이 문서뿐이다 —
`git diff main...HEAD -- app/ web/ tests/ migrations/ .env.example` 는 빈 결과이고
마이그레이션 변경이 없어 조건부 `flask db heads` 는 해당 없음.
`git merge-base main HEAD == main`(= `d78e082`), 작업 트리 clean.
