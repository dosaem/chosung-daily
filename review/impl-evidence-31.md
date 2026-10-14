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
