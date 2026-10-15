# 티켓 40 증거 — 최종 스토어 스크린샷 재촬영 (29~33·38 머지 후)

- 대상: 로컬 `main`(`3463865`, 티켓 33 머지 포함) 위 새 worktree
  `dosaem/t40-final-store-screenshots`.
- 범위: 스크린샷 PNG + 장면/스크립트의 **결정론 보정**. 앱 기능·메타데이터 문구는
  바꾸지 않았다(예외 하나 — 카운트다운의 시계 주입, §2.2. 코디네이터가 허용했다).
- 외부 업로드·프로덕션 접근·push 는 하지 않았다. 하위 워커도 쓰지 않았다.

## 0. 한 줄 요약

29~33 머지 뒤 장면을 실제로 렌더해 **기기·세션 상태에 따라 그림이 갈리는 자리 4개**를
찾아 고치고(광고 게이트·알림 권한·알림 설정·시계), iOS 3기기 + Play 폰·태블릿을
ko·en 으로 다시 찍었다 — Play 폰은 **네이티브 Android 에뮬레이터**로, 업로드 전
검사는 iOS·Play 모두 0건이다.

## 1. 장면이 29~33·38 이후 실제 화면과 맞는지 — 먼저 확인한 것

고치기 전에 장면 5개 × ko/en × 폰/태블릿 폭을 띄워 화면에 실제로 그려지는 글자를
전부 덤프했다(임시 위젯 테스트, 뒤에 지웠다). 코디네이터가 짚은 항목별 결과:

| 확인 항목 | 결과 | 근거 |
|---|---|---|
| S4 설정에 계정 카드 | 맞다 | `구글로 연결`·`Apple 로 연결`(Android 는 구글만) — `AccountCard`, `RecordsSlot.account` |
| S4 알림 2행 | **틀렸다** | 권한이 `notDetermined` 라 두 행 사이에 `알림 꺼짐 — 시스템 설정에서 켜기` 경고가 끼어 3행이었다 → §2.1 |
| S4 광고 개인정보 행 | 나오지 않는다(의도) | `showsPrivacyOptions` 는 UMP `privacyOptionsRequired` 라 EEA 전용 → 코디네이터 결정으로 **빼는 쪽** (§2.4) |
| S4 구독 카드 | 맞다 | `구독 · 광고 없이 플레이` (`SubscriptionCard` → `_OfferRow`). 가격은 `NoopPurchaseService` 라 비어 있고, 스펙 §A.8 대로 앱이 금액을 대신 적지 않는다 |
| 결과 시트의 계정 연결 1회성 안내 숨김 | 맞다 | 티켓 35 가 넣은 `localFlagStoreProvider` override 가 그대로 돈다. `result.link_account` 가 어느 장면에도 없다 |
| 순위표 `Guest #xxxx` | 맞다 | ko `게스트 #a3f1`, en `Guest #a3f1`·`1 try`/`2 tries` (티켓 38 의 `anon_tag`·plural) |
| 구독자/비구독자 광고 슬롯 | 슬롯 없음(의도) | 장면 셸은 `AdBannerSlot` 을 넣지 않는다(OVERRIDES §8 — 빈 회색 띠를 스토어 그림에 넣지 않는다). `home_shell.dart:42` 의 실제 슬롯은 장면 밖이다 |

추가로 **코디네이터 목록에 없던 결함 2개**를 같은 덤프에서 찾았다 — §2.2, §2.3.

## 2. 고친 것 (전부 결정론 보정)

### 2.1 S4 알림 권한 — 경고 행이 늘 찍혔다

- 증상: `notificationPermissionProvider` 의 기본값은 `notDetermined` 이고 장면에는
  OS 에 다시 묻는 코드(티켓 30 의 알림 동기화)가 없다. 그래서 S4 에
  `알림 꺼짐 — 시스템 설정에서 켜기` / `Notifications are off …` 가 **항상** 들어갔다.
- 고침: 장면이 `FixedNotificationPermissionNotifier(granted)` 로 바꿔 낀다
  (`storeScreenshotNotificationPermission`). 스토어 그림은 알림이 켜진 보통 사용자다.
- 결정: 코디네이터 승인(ask, 선택지 B).

### 2.2 S2 카운트다운 — 찍는 시각마다 숫자가 달랐다

- 증상: `PuzzleCountdown` 이 `DateTime.now` 를 직접 읽어 다음 KST 자정까지를 센다.
  같은 세트의 ko·en 이 몇 분 차이로 다른 숫자가 되고(실측 `04:45:19` vs `04:45:18`),
  자정 직전에 돌리면 `00:00:03` 같은 그림이 남는다.
- 고침: **호출부 두 곳**이 `clockProvider` 의 시계를 넘긴다
  (`today_tab.dart` 의 `showResultSheet`, `_NoPuzzleCard`). `clockProvider` 의 기본값이
  `DateTime.now` 라 **앱 동작은 그대로**다. 장면은 고정 시각(KST 19:14:41)을 주입해
  `04:45:19` 로 찍는다.
- 이것이 이 티켓에서 유일한 `lib/` 변경이다. 코디네이터가 "최소 변경 + 위젯 테스트
  하나로 고정" 조건으로 허용했다.
- 고정하는 테스트: `mobile/test/widgets/countdown_clock_test.dart` 2건.
  **뮤테이션 확인**: `now: ref.read(clockProvider)` 두 줄을 지우면 두 테스트 모두 실패한다
  (`Found 0 widgets with text containing 다음 퍼즐까지 00:12:33`).

### 2.3 S1·S2 힌트 카드 — "지금은 광고를 불러올 수 없어요" 가 박혔다

- 증상: 장면은 `adServiceProvider` 기본값 `NoopAdService` 를 쓰고 그 `requestConsent()`
  는 `UmpStatus.failed()` 를 준다. ATT 도 `notDetermined` 라 `adGateFor` 가
  `canLoadAds=false` 를 내고, `today_tab.dart:320` 이 `hint.ad_unavailable` 안내를 달고
  미리 보기 버튼을 끈다 — **오류 문구가 스토어 스크린샷에 박힌다**.
- 고침: 장면이 `adGateProvider` 를 상수로 바꿔 낀다(`storeScreenshotAdGate`):
  `canLoadAds: true, showsBannerSlot: true, hintPreviewNeedsAd: true,
  showsPrivacyOptions: false` — **동의를 마친 비구독자**.

### 2.4 S4 광고 개인정보 행 — EEA 전용이라 뺀다

- `showsPrivacyOptions` 만 `false` 로 둔다. 그 행은 UMP 가 `privacyOptionsRequired` 를
  주는 EEA 에서만 보이고, 스토어 그림의 기준은 주 시장(한국·미국)의 기본 화면이다.
- 코디네이터 결정(ask 답변): *"광고 개인정보 행은 EEA 전용 조건부 행이라 빼는 게
  사실과 맞고, 내 목록의 그 항목은 내가 조건을 빠뜨린 것이다."*

### 2.5 S4 일일 알림 — 기기 저장소와 12/24시간 설정을 탔다

- 증상 ①: `notificationSettingsProvider` 는 `shared_preferences` 에서 읽는다. 그
  시뮬레이터에서 앱을 만져 본 적이 있으면 S4 의 "일일 알림" 값이 달라진다.
- 증상 ②: `MaterialLocalizations.formatTimeOfDay` 는 **기기의 24시간제 설정**을 본다 —
  같은 코드가 `오전 9:00` 과 `09:00` 을 오간다.
- 고침: 장면이 `MediaQuery` 로 `alwaysUse24HourFormat: false` + `withNoTextScaling` 을
  고정하고, 알림 설정은 아래 2.6 의 notifier 로 바꿔 낀다.

### 2.6 S4 리마인더 스위치 — **실제로 4장 중 2장이 꺼진 채 찍혔다** (재촬영 1회차에서 발견)

- 증상: 저장소만 메모리로 바꿨을 때(`notificationSettingsStoreProvider` override)
  `build()` 가 여전히 `Future` 라 첫 프레임이 `AsyncLoading` 이다. 스위치 값이
  `false → true` 로 **애니메이션**하고, `takeScreenshot` 은 기기 표면을 찍으므로 그
  전환 중에 걸리면 꺼진 스위치가 남는다.
- 실측(2026-10-15, 1차 재촬영 결과): iOS 폰 4장 중
  **`iphone69_en_04_records`·`iphone65_ko_04_records` 가 꺼짐**,
  `iphone69_ko`·`iphone65_en` 은 켜짐. 같은 코드·같은 스크립트인데 갈렸다.
  (두 그림 다 `9:00 AM`/`오전 9:00` 은 들어 있었다 — 설정은 로드됐고 **애니메이션만**
  안 끝난 상태였다.)
- 고침: 저장소가 아니라 **provider 자체**를 바꿔 끼고
  `build()` 가 `SynchronousFuture` 를 돌려준다
  (`StoreScreenshotNotificationSettings`). Riverpod 이 `then` 을 부르는 순간 값이 와서
  **첫 읽기가 이미 `AsyncData`** 다 — 상태가 바뀌지 않으니 애니메이션 자체가 없다.
  `ProviderContainer.read` 로 직접 확인: `AsyncData<NotificationSettings>(value: …)`.
- 고정하는 테스트: `… — S4 리마인더 스위치는 첫 프레임부터 켜져 있다` (settle 없이
  첫 프레임만 본다). **뮤테이션 확인**: `SynchronousFuture` 를 `Future.value` 로
  바꾸면 `Expected: true / Actual: <false> — 첫 프레임에 리마인더가 꺼져 있다` 로 깨진다.
- 이 결함 때문에 **10개 기기×로케일 세트를 전부 다시 찍었다**(1차 결과는 버렸다).

## 3. 바뀐 파일

### 3.1 코드·테스트 (4개)

| 경로 | 변경 |
|---|---|
| `mobile/integration_test/store_screenshot_scenes.dart` | 장면 override 4개 추가(시계·광고 게이트·알림 권한·알림 설정) + `MediaQuery` 고정. 각 상수에 실측 근거 주석 |
| `mobile/lib/screens/today_tab.dart` | `showResultSheet`·`_NoPuzzleCard` 가 `clockProvider` 의 시계를 넘긴다(+7줄). 기본값이 `DateTime.now` 라 앱 동작 동일 |
| `mobile/test/store/store_screenshot_scenes_test.dart` | 결정론 테스트 6종 추가(힌트 안내·알림 2행·광고 개인정보 행 부재·기기 저장소 미사용과 12시간 표기·첫 프레임 스위치·카운트다운 고정). ko/en 각각 → 12건 |
| `mobile/test/widgets/countdown_clock_test.dart` | 새 파일. `clockProvider` 배선을 고정하는 2건 |

### 3.2 스크린샷 PNG (52개 변경: 수정 12 · 추가 20 · 삭제 20)

**iOS deliver — 수정 12장** (`mobile/ios/fastlane/screenshots/{ko,en-US}/`):

```
ipad13_{ko,en}_02_result.png      ipad13_{ko,en}_04_records.png
iphone65_{ko,en}_02_result.png    iphone65_{ko,en}_04_records.png
iphone69_{ko,en}_02_result.png    iphone69_{ko,en}_04_records.png
```

나머지 18장(`01_home`·`03_leaderboard`·`06_language` × 3기기 × 2로케일)은 **다시
찍었지만 바이트가 같다**. 티켓 35 의 캡처는 티켓 29 까지만 머지된 코드였고, 그
화면들은 30~33 로 달라지지 않았다 — 힌트 카드도 광고 게이트가 들어오기 전의
"안내 없는" 모습이라 §2.3 의 override 가 그 모습을 되돌린다. 세트는 `capture` 가
통째로 교체했으므로 섞인 세트가 아니다.

**Play supply — 추가 20 / 삭제 20** (`mobile/android/fastlane/metadata/android/{ko-KR,en-US}/images/`):

```
삭제  phoneScreenshots/iphone69_{ko,en}_{01,02,03,04,06}_*.png      (iPhone 캡처 복사본)
삭제  tenInchScreenshots/ipad13_{ko,en}_{01,02,03,04,06}_*.png      (iPad 캡처 복사본)
추가  phoneScreenshots/android_{ko,en}_{01,02,03,04,06}_*.png       (네이티브 Android 에뮬레이터)
추가  tenInchScreenshots/androidtablet_{ko,en}_{01,02,03,04,06}_*.png (iPad 시뮬 + SHOT_IS_IOS=false)
```

장 수: 기기 유형마다 로케일당 **5장**(Play 상한 8장 이내). 합계 PNG 50장
(iOS 30 + Play 20) + 등록 자산 4개(featureGraphic·icon × 2로케일, 변경 없음).

### 3.3 해상도

| 세트 | 해상도 | 비고 |
|---|---|---|
| iPhone 6.9" (`iphone69_*`) | 1320×2868 | ASC 필수 |
| iPhone 6.5" (`iphone65_*`) | 1242×2688 | ASC 선택 |
| iPad 13" (`ipad13_*`) | 2064×2752 | ASC 필수(iPad 지원) |
| Play 폰 (`android_*`) | 1080×2400 | 네이티브 에뮬레이터 |
| Play 태블릿 (`androidtablet_*`) | 2064×2752 | Play 는 폭·비율만 본다 |

세트 안에서 해상도가 섞인 파일은 없다(전수 확인).

## 4. 어떻게 찍었나

### 4.1 Android 는 네이티브 에뮬레이터로 찍었다 (티켓 35 의 대체 경로를 쓰지 않았다)

티켓 35 는 사용자 AVD `Medium_Phone_API_36.1` 의 `/data` 가 가득 차
(`Requested internal only, but not enough space`) iPhone 시뮬레이터 대체 경로로 갔다.
이번에도 같은 상태였다 — 부팅해 확인한 결과 **5.8G 중 5.3G 사용, 327M 여유**.

**사용자 AVD 는 지우지도 wipe 하지도 않았다.** 대신 같은 시스템 이미지
(`system-images/android-36.1/google_apis_playstore/arm64-v8a`, 이미 설치돼 있다)로
**전용 AVD `chosung_t40_shots`** 를 만들어(`disk.dataPartition.size=8G`) 거기서 찍었다.
`/data` 여유 6.9G, 설치·캡처 모두 정상이었다. 작업이 끝난 뒤 이 AVD 는 지웠다(§7).

- `avdmanager` 는 Java 런타임이 없어(`Unable to locate a Java Runtime`) 쓰지 못했고,
  `DataGrip.app` 의 JBR 로 돌려도 `sdkmanager` 가 설치 패키지를 못 읽었다. 그래서
  기존 AVD 의 `config.ini` 를 복사해 이름·데이터 파티션만 바꿔 만들었다.
- 결과: Play 폰 세트가 **실제 Android 구성**이다 — 온보딩 점이 **3개**(iOS 는 ATT
  안내 1장이 더 붙어 4개), 계정 카드에 `Apple 로 연결`이 없다. 눈으로 확인했다(§6).

### 4.2 Play 태블릿은 스크립트가 정한 방식 그대로

`play_tablet_set()` 이 iPad 시뮬레이터에서 `STORE_SHOT_IS_IOS=false` 로 한 번 더 찍는다
(티켓 35 의 D-35-8 수정). 레이아웃(rail + 2열)은 같은 코드라 같고, 플랫폼으로 갈리는
온보딩만 Android 구성으로 나온다 — 찍힌 그림에서 점 3개를 확인했다(§6).

### 4.3 메모리 부족으로 한 번 끊겼다 (숨기지 않는다)

`./scripts/store_screenshots.sh both` 를 백그라운드로 돌리던 중 하네스가
**시스템 메모리 부족**으로 그 프로세스를 죽였다(ko 전체 + en iPhone 6.9" 까지 끝난
뒤). 캡처 실패가 아니라 외부 요인이다. 이후에는 시뮬레이터·에뮬레이터를 단계마다
내리고 **기기 하나씩 포그라운드로** 돌렸다 — 스크립트의 `capture`·`replace_set`·
`play_tablet_set`·`android_device` 를 `STORE_SHOTS_LIB_ONLY=1` 로 **source 해서 그대로**
쓰는 얇은 래퍼(`/tmp` 에 둔 임시 파일, 레포에 넣지 않았다)이고 판정 로직은 건드리지
않았다. §2.6 을 고친 뒤 **10개 세트를 전부 다시 찍었으므로** 중단된 1차 결과는 남아
있지 않다.

## 5. 업로드 전 검사 (실제 출력)

```
$ cd mobile && python3 tool/verify_store_screenshots.py ios
screenshots OK: ios — 로케일마다 5 장씩
ios exit=0

$ python3 tool/verify_store_screenshots.py play
screenshots OK: play — 로케일마다 5 장씩
play exit=0
```

**iOS·Play(폰·태블릿) 모두 0건.** 티켓 35 리뷰 라운드 3 에서는 같은 명령이
`종료 1, 4건 차단`(ko/en × 폰·태블릿의 iOS 복사본)이었다 — 그게 이 티켓의 숙제였고
이제 양쪽 다 0건이다.

검사기가 보는 것: 로케일×기기 유형마다 정확히 5장, Play 기기 유형별 상한 8장,
그리고 Play 세트에 iOS 온보딩 캡처와 **바이트까지 같은** 파일이 없을 것.

## 6. 눈으로 확인한 기록

세트마다 직접 열어 봤다(원본 PNG 를 축소해 확인). 본 것:
① 최신 UI(29~33 의 계정·구독·알림), ② 한글/영문 혼입 없음, ③ 1회성 안내 없음,
④ 광고 실패 문구 없음, ⑤ 플랫폼별 온보딩 장 수.

| 세트 | 연 파일 | 확인한 내용 |
|---|---|---|
| iOS ko iPhone 6.9" | 5장 전부 | S1 힌트 카드 `광고 보고 힌트 미리 보기` + **안내 문구 없음**. S2 시트에 계정 연결 안내 없음, `다음 퍼즐까지 04:45:19`. S3 `게스트 #a3f1`·`1회`(영문 0). S4 `구글로 연결`/`Apple 로 연결`·`구독 광고 없이 플레이`·`다른 기기 기록 불러오기`·`퍼즐 언어 한국어`·`일일 알림 오전 9:00`·`리마인더 켜짐`, **경고 행 없음**, 광고 개인정보 행 없음. S6 칩 `한국어/영어`, 점 **4개**(iOS) |
| iOS en iPhone 6.9" | 5장 전부 | 위와 대응. `Guest #a3f1`, `1 try`/`2 tries`(티켓 38 복수형), `Next puzzle in 04:45:19`, `Daily reminder 9:00 AM`, `Nudge if unsolved` 켜짐. **한글 0** |
| iOS ko iPhone 6.5" | `04_records` | 리마인더 켜짐(초록), `오전 9:00` |
| iOS en iPhone 6.5" | `04_records` | 리마인더 켜짐(초록), `9:00 AM` |
| iOS ko iPad 13" | `04_records` | **rail + 2열**(왼쪽 계정·구독, 오른쪽 설정), 리마인더 켜짐 |
| iOS en iPad 13" | `06_language` | 점 **4개**(iOS), 칩 `Korean/English`, 한글 0 |
| Play ko 폰 (`android_*`) | `04_records`, `06_language` | 계정 카드에 `구글로 연결`만(Apple 없음 = 실제 Android), 리마인더 켜짐, 경고 행 없음 / 온보딩 점 **3개** |
| Play en 폰 (`android_*`) | `04_records`, `06_language` | `Continue with Google` 만, `Nudge if unsolved` 켜짐 / 점 **3개**, 한글 0 |
| Play ko 태블릿 (`androidtablet_*`) | `04_records` | rail + 2열, `구글로 연결`만, 리마인더 켜짐 |
| Play en 태블릿 (`androidtablet_*`) | `06_language` | 점 **3개**(= iPad 의 4개와 다르다 → Android 구성 확인), 한글 0 |

추가로 **리마인더 스위치 상태를 10장 전수**로 다시 확인했다(§2.6 재발 방지):
iOS 폰 4장은 픽셀 검사로 초록(켜짐) 1671px 씩 동일, 태블릿 4장·Android 폰 2장은
그림으로 켜짐을 확인했다.

## 7. 정리한 것 (디스크)

- `mobile/build`, `mobile/ios/Pods`, `mobile/.dart_tool` 빌드 산출물, 시뮬레이터
  캐시, 전용 AVD `chosung_t40_shots` 를 작업 뒤 지웠다(§실행 기록).
- 사용자 AVD `Medium_Phone_API_36.1` 는 **건드리지 않았다** — 부팅해서 `df` 만 읽고
  `emu kill` 로 내렸다. `-no-snapshot-save` 로 띄워 상태도 남기지 않았다.
- `pod install` 이 바꾼 `mobile/ios/Podfile.lock`(+100), `Runner.xcodeproj/project.pbxproj`
  (+146), `Runner.xcworkspace/contents.xcworkspacedata`(+3) 는 **되돌렸다** — 빌드
  부산물이고 이 티켓 범위가 아니다. 다만 **커밋된 `Podfile.lock` 은 낡았다**: 티켓
  35 가 커밋한 뒤 30~33 이 더한 플러그인(`google_mobile_ads`, `google_sign_in_ios`,
  `flutter_timezone`, `app_settings`, `GoogleUserMessagingPlatform` 등)이 빠져 있다.
  iOS 빌드 설정 담당 티켓에서 갱신할 일로 남긴다(§9).

## 8. 전체 검증 (실행 명령과 출력)

### 8.1 Flutter

```
$ cd mobile && dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 201 files (0 changed) in 0.49 seconds.        (exit 0)

$ flutter analyze --no-pub
Analyzing mobile...
No issues found! (ran in 3.9s)                          (info 포함 0건)

$ flutter test --no-pub --reporter compact
00:58 +796: All tests passed!
```

`test/store` 만 따로: **49 passed**(티켓 35 의 37건 + 이번 12건).

### 8.2 백엔드

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=…/chosung_daily_test_t40 \
  TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t40_migrations \
  TEST_REDIS_URL=redis://127.0.0.1:6379/14 \
  uv run pytest -q
1526 passed in 805.55s (0:13:25)        (exit 0)
```

테스트 전용 자원만 썼다: MySQL `chosung_daily_test_t40`(+ `_migrations`, 이 작업에서
새로 만들었다), Redis DB **14**. 접속 자격 증명은 여기 적지 않는다. 다른 티켓의
테스트 DB·기본 DB 로 떨어지지 않았고, 간헐 실패·재실행도 없었다.

### 8.3 기타

```
$ git diff --check main...HEAD        # 통과(공백 오류 없음)
$ git diff --name-only main...HEAD -- migrations   # 출력 없음 → flask db heads 대상 없음
```

## 9. 남은 한계 (숨기지 않는다)

1. **카운트다운은 "고정"이지 "실제"가 아니다.** 장면이 KST 19:14:41 을 주입하므로
   S2 는 늘 `04:45:19` 로 찍힌다. 실제 사용자는 그 순간의 남은 시간을 본다 — 스토어
   그림이 고정값인 것은 다른 숫자(연속 12일·41문제·순위)와 같은 성격이다.
2. **Podfile.lock 이 낡았다**(§7). 이 티켓에서 고치지 않았다 — iOS 빌드 설정 담당
   쪽 일이다. 지금 상태로도 CI 는 `pod install` 을 다시 돌리므로 빌드는 된다.
3. **구독 카드에 가격이 없다.** `NoopPurchaseService` 라 `광고 없이 플레이` /
   `Play without ads` 로만 찍힌다. 실기기 Sandbox 로 찍으면 금액이 들어가지만,
   스펙 §A.8 은 앱이 금액을 대신 적지 않는다고 못박았고 티어는 콘솔 값이라
   스크린샷에 금액을 박는 쪽이 오히려 틀릴 수 있다.
4. **광고 개인정보 행은 EEA 사용자만 본다** — 스크린샷에는 없다(§2.4, 코디네이터 결정).
5. **배너 슬롯은 어느 그림에도 없다**(OVERRIDES §8). 구독자/비구독자 차이를 보여주는
   그림은 이 5장에 들어 있지 않다.
6. **업로드는 하지 않았다.** 사람이 `docs/RELEASE.md` "### 35." 의 순서로 한다.
   이 티켓은 그 문서의 "Play 폰 스크린샷 — 지금은 업로드가 막혀 있다" 체크박스를
   해소했고, 근거를 `### 40.` 절에 적었다.
7. **`impeccable detect` / `audit.native` 는 돌리지 않았다.** 화면 코드(`lib/`)의 변경은
   시계 주입 7줄뿐이고 UI 를 바꾸지 않는다.

## 10. 다른 티켓과 공유하는 파일

- `docs/RELEASE.md`: 끝에 `### 40.` 절만 더했다. 더해서 `### 35.` 의 Play 폰
  체크박스 한 줄을 `[x]` 로 바꾸고 `### 40.` 을 가리키게 했다 — 그 줄이 "지금은
  업로드가 막혀 있다" 라고 **사실과 다르게** 남으면 출시 순서를 잘못 읽는다.
- `README.md`·`.env.example`·스펙 "미정 항목"·마이그레이션은 **바꾸지 않았다**.
