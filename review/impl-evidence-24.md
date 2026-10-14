# 티켓 24 구현 증거 — 태블릿 적응형 뼈대(`mobile/`)

- 브랜치: `dosaem/t24-app-tablet-adaptive-scaffold`, 로컬 `main` **1e764da**
  (티켓 15 머지) 위로 `git rebase main` 완료 — 작업 중 main 이 148715b → 1e764da 로
  움직여서 커밋 4개를 재적용했다. **충돌 없음**, 작업 트리 clean. rebase 후
  analyze·format·flutter test·ruff·pytest·heads 를 전부 다시 돌렸다(아래는 그 값).
- Flutter 3.38.6 / Dart 3.10.7 (설치돼 있던 것 사용, 설치 시도 없음)
- 백엔드 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t24`, Redis DB **12**,
  마이그레이션 왕복용 `chosung_daily_test_t24_migrations`
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL` 로 지정).
  두 DB 는 README "실행 방법" 절차대로 관리자로 한 번 만들었다(테스트 유저에게
  `CREATE DATABASE` 권한이 없다). 공용 `chosung_daily_test`·Redis 1 과 다른 워커의
  자원·컨테이너는 건드리지 않았다. 이 티켓은 **Python 코드를 한 줄도 바꾸지 않았고
  마이그레이션도 만들지 않았다**.
- **외부 서비스 호출 0건.** AdMob·Firebase·Sentry·스토어·Slack·NAS 어디에도 연결하지
  않았다. 광고 슬롯은 아직 자리와 폭만 넘기는 위젯이고(SDK 는 티켓 31), 네트워크를
  탄 건 `flutter pub get` 의 pub.dev 패키지 해석뿐이다. 배포·`git push` 없음.
- 시크릿 값은 어떤 파일·로그에도 쓰지 않았다. `.env`, `.env.prod*` 는 열지 않았다.
- 하위 워커·서브에이전트 없음. 판단 1건은 `orca orchestration ask` 로 코디네이터에게
  물었다(아래 "코디네이터 확정 사항").

## 코디네이터 확정 사항

1. (`ask`) **배너 슬롯 예약 높이는 폭의 순수 함수로 두고 잠정값을 쓴다** —
   `AdBannerSlot.reservedHeightFor(width)`: 폭 <728 → 50, ≥728 → 90. 근거는
   어댑티브 배너 높이 상한이 90dp 이고 728×90(IAB leaderboard)이 태블릿 표준 배너
   라는 점. 티켓 31 이 SDK 의
   `getCurrentOrientationAnchoredAdaptiveBannerAdSize` 실제 값으로 대체·검증한다.
   코디네이터 요구대로 (a) 코드 주석, (b) README "### 24.", (c) 스펙 "미정 항목" 의
   `- (티켓 24 반영)` 줄에 각각 적었고, 경계 727/728 을 테스트로 고정했다.
   22 의 50dp 테스트는 폰 폭 기준이라 **무변경 통과**한다.

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 무엇이 증명하는가 |
|---|---|
| `AppBreakpoint` 헬퍼 — 현재 폭 기준 3단, 경계 599/600/839/840 | `mobile/lib/layout/app_breakpoint.dart`. `test/layout/app_breakpoint_test.dart` 5개 — "599 는 compact, 600 은 medium" / "839 는 medium, 840 은 expanded" / "iPad Split View 의 가장 좁은 폭(약 320)은 compact 로 떨어진다" / `hasRail` / **"MediaQuery 의 현재 폭만 본다 — 높이·플랫폼은 보지 않는다"**(같은 기기가 1024→744→320 으로 줄어드는 흐름을 폭만 바꿔 재현) |
| `AdaptiveScaffold` — compact = 22 의 `NavigationBar`, medium 이상 = 왼쪽 `NavigationRail`(아이콘+라벨, 같은 3항목·같은 경로) | `mobile/lib/layout/adaptive_scaffold.dart`, `lib/screens/home_shell.dart`(얇아짐). `test/layout/adaptive_scaffold_test.dart` "폰 폭(390)은 하단 탭 바, rail 없음" / "태블릿 폭(744.0·1024.0·1366.0)은 rail, 하단 탭 바 없음"(라벨 3개까지 확인) / "rail 도 하단 탭 바와 같은 콜백으로 탭을 옮긴다". 앱 트리에서는 `test/app_startup_branch_test.dart` "390.0·1024.0 폭에서 세 탭이 같은 go_router 경로를 쓴다"(`['/today','/ranking','/records']` 두 폭에서 동일) |
| 선택 상태는 OVERRIDES 토큰 — brand 는 아이콘·밑줄만 | `_Rail` 이 `useIndicator: false`(Material 기본 선택 표시가 면을 채운다) + `_SelectedTabIcon`(아이콘 + brand 2px 밑줄)을 하단 탭 바와 **공유**한다. 토큰 값 자체는 22 의 `test/theme/app_theme_test.dart` "brand 를 면·글자색으로 안 쓴다" 가 계속 지킨다 |
| `MaxWidthBody` 6개 사용처를 `ReadingWidth` 로 교체 | `mobile/lib/widgets/max_width_body.dart` **삭제**, `mobile/lib/layout/reading_width.dart` 추가. `grep -rn MaxWidthBody mobile/lib` → 0건(아래 §2). 교체처 6개: `today_tab`·`ranking_tab`·`records_tab`·`splash_screen`·`update_required_screen`·`maintenance_screen`. `test/layout/reading_width_test.dart` 3개 — 기본 600 / 화면별 `maxWidth` 480(T4 열) / 폰 폭에선 화면 그대로 |
| 22 의 "본문은 600px 를 넘지 않는다 (iPad)" 를 태블릿 뼈대 기준으로 다시 쓴다 | 그 테스트를 지우고 `test/app_startup_branch_test.dart` 의 `group('태블릿 적응형 셸')` 로 대체했다. 첫 테스트가 같은 834 폭(1668×2388 @2)에서 **rail 존재 + `NavigationBar` 없음 + 콘텐츠 열 = 834 − rail 폭 + 본문 ≤600** 을 잰다 |
| 그 외 22 테스트(3탭·배너 슬롯 높이·S7 분기·시작 분기)는 무변경 통과 | `git diff mobile/test/app_startup_branch_test.dart` 가 import 2줄과 마지막 iPad 테스트 교체·태블릿 group 추가만 보여준다. 나머지 13개 테스트 본문은 한 글자도 안 바뀌었고 §2 에서 통과한다 |
| 배너 슬롯 위치 — compact = 탭 바 아래(현행 유지), medium 이상 = 콘텐츠 영역 하단(rail 제외 폭), safe area 위 | `test/layout/adaptive_scaffold_test.dart` "배너 슬롯은 rail 을 제외한 콘텐츠 열 하단에 앉는다"(`slot.left == rail 폭`, `slot.width == 1024 − rail 폭`, `slot.bottom == 768`) / "폰 폭에서는 배너가 탭 바 아래, 화면 폭 전체다" / **"태블릿에서도 배너는 하단 safe area 위에 있다"**(뷰 하단 inset 20 을 주고 `slot.bottom == 768 − 20`) |
| 높이는 그 폭의 어댑티브 배너 높이로 예약(레이아웃 점프 금지) | `AdBannerSlot.reservedHeightFor`. `test/widgets/ad_banner_slot_test.dart` "폰 폭은 50, 728 부터는 90 (경계 727/728)" + 실제 렌더 높이 2개("좁은 슬롯은 50 + 여백 8", "태블릿 콘텐츠 열 폭에서는 90 + 여백 8"). 로드 전에도 높이가 있으므로 광고가 뜰 때 점프가 없다 |
| 슬롯이 현재 폭을 `bannerWidth` 로 노출 | `AdBannerSlot({Widget Function(BuildContext, double bannerWidth)? builder})` + `LayoutBuilder`. "현재 슬롯 폭을 bannerWidth 로 넘겨준다"(940 을 받는다). 광고 로드 자체는 티켓 31 |
| `showAdaptiveSheet` — compact = 바텀시트, medium 이상 = 가운데 다이얼로그(최대 560, 상하 여백) | `mobile/lib/layout/adaptive_sheet.dart`. `test/layout/adaptive_sheet_test.dart` 4개 — "폰 폭은 바텀시트로 뜬다"(화면 아래에 붙음) / "태블릿 폭은 가운데 다이얼로그 — 최대 폭 560, 상하 여백 48 이상"(폭 ≤560, 위 ≥48, 아래 ≤768−48, 가로 중앙 512) / "medium 경계(600)부터 다이얼로그다" / "어느 쪽이든 닫을 때 같은 값을 돌려준다"(26·29·32 가 `pop(value)` 로 쓰는 경로) |
| 회전·Split View 로 폭이 compact↔medium 을 넘나들 때 현재 탭·입력 중 텍스트·스크롤 유지 | `test/layout/adaptive_scaffold_test.dart` "회전·Split View: 폭이 390 → 744 → 390 이어도 탭·입력 텍스트·스크롤이 유지된다" — 390 에서 탭 1 로 옮기고 `TextField`(**컨트롤러 없이** — 상태가 위젯 State 안에 있어야 진짜 검증이다)에 "지하철역" 을 넣고 목록을 200 스크롤한 뒤, 744 로 늘려 rail 로 바뀐 것과 세 값이 그대로인 것을, 다시 390 으로 줄여 같은 것을 확인한다. 앱 트리 쪽은 "폭이 390 → 744 → 390 이어도 현재 탭이 유지된다"(순위 탭 유지) |
| iPad Split View 최소 폭(약 320dp)은 compact | `app_breakpoint_test.dart` 의 320 단언 + "현재 폭만 본다" 흐름 |
| 위젯 테스트: 390 = NavigationBar·rail 없음 / 744·1024 = rail·NavigationBar 없음, 세 탭 전환이 양쪽에서 같은 경로 | 위 두 칸. 1366 까지 함께 본다 |
| `flutter analyze` 0건 | §2 |
| `audit.native` 체크리스트에 "태블릿 폭(744·1024·1366) 포함" 항목 추가 + 통과 기록 | §4 |
| README Flutter 절에 한 단락 + 미정 24 결과 기록 | `README.md` "### 24. 태블릿 대응 — 기기 종류가 아니라 현재 폭". 미정 24 결과(T1 600+320, T4 480+480, Split View 최소 폭 약 320 → compact)는 그 단락과 스펙 "미정 항목" 의 `- (티켓 24 반영)` 줄에 |

## 2. 실행한 명령과 출력

### Flutter 분석 (0건이어야 한다)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 2.7s)
```

### Flutter 포맷 (CI 와 같은 명령)

```
$ cd mobile && dart format --set-exit-if-changed lib test
Formatted 55 files (0 changed) in 0.17 seconds.
$ echo $?
0
```

### Flutter 테스트

```
$ cd mobile && flutter test
00:24 +120: All tests passed!
```

티켓 22 머지 직후가 **87개**였고 이 티켓이 **33개**를 더해 120개다. 실패·skip 0건.

| 파일 | 개수 | 내용 |
|---|---|---|
| `test/layout/app_breakpoint_test.dart` | 5 | 경계 599/600·839/840, Split View 320, `hasRail`, "현재 폭만 본다" |
| `test/layout/adaptive_scaffold_test.dart` | 9 | 390 탭 바 / 744·1024·1366 rail(3개) / rail 탭 전환 / 배너 위치 태블릿·폰 / 배너 safe area / 폭 왕복 상태 유지 / 구독자(배너 없음) |
| `test/layout/adaptive_sheet_test.dart` | 4 | 바텀시트·다이얼로그 분기, 560·48 여백, 경계 600, 반환값 |
| `test/layout/reading_width_test.dart` | 3 | 기본 600, 화면별 480, 폰 폭 |
| `test/widgets/ad_banner_slot_test.dart` | 4 | `reservedHeightFor` 경계 727/728, 렌더 높이 2종, `bannerWidth` 전달 |
| `test/app_startup_branch_test.dart` (태블릿 group) | 8 | 834 rail+600, 390 탭 바, 744·1024·1366 rail(3개), 390·1024 경로 동일(2개), 폭 왕복 탭 유지 |

가짜로 바꾼 건 22 와 같이 **`ApiClient` 와 `GuestTokenStore` 둘뿐**이다. 레이아웃
테스트는 아예 가짜가 없고 실제 `AdaptiveScaffold`·`NavigationRail`·`go_router`
셸을 그대로 돌린다.

### 백엔드 린트

```
$ uv run ruff check .
All checks passed!
```

### 백엔드 전체 테스트 스위트 (rebase 후)

```
$ TEST_DATABASE_URL=...chosung_daily_test_t24 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/12 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t24_migrations \
  uv run pytest -q
........................................................................ [ 63%]
........................................................................ [ 73%]
........................................................................ [ 84%]
........................................................................ [ 94%]
....................................                                     [100%]
743 passed in 623.18s (0:10:23)
```

**실패·skip·xfail 0건.** 22 머지 시점의 555개에서 743개로 늘었다(그 사이 머지된
백엔드 티켓들이 더한 것 — 이 티켓은 Python 을 한 줄도 안 건드렸다). rebase 전
148715b 위에서도 같은 명령으로 **684 passed**(22분, 다른 워커 여럿이 같은 MySQL 에
붙어 있어 느렸다)였고, rebase 로 티켓 15 가 들어온 뒤 743개가 됐다.

### Android 디버그 빌드 (Firebase 설정 파일 **없이**)

```
$ cd mobile && test ! -f android/app/google-services.json && echo "google-services.json 없음"
google-services.json 없음
$ test ! -f ios/Runner/GoogleService-Info.plist && echo "GoogleService-Info.plist 없음"
GoogleService-Info.plist 없음
$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                            133.0s
✓ Built build/app/outputs/flutter-apk/app-debug.apk
```

### iOS 디버그 빌드 — **깨졌다(디스크 부족, 코드 문제 아님)**

코디네이터 메모의 "가능하면" 항목이라 시도했고, 실패를 숨기지 않고 적는다.

```
$ cd mobile && flutter build ios --no-codesign --debug
...
Error (Xcode): copy(.../GoogleUtilities_Privacy.bundle/Info.plist, ...):
  No space left on device (28)
Swift Compiler Error (Xcode): Unable to find module dependency: 'FirebaseCoreInternal'
/.../usr/include/os/availability.h:76:10: fatal error: could not build module '_AvailabilityInternal'
Encountered error while building for device.
```

`df -h` 가 `/System/Volumes/Data` 를 **100% (420Gi/460Gi, 여유 568Mi)** 로 보여줬다.
내 worktree 의 생성물 `mobile/build`(2.3G)를 지워 여유를 3.2Gi 로 만들었고
**코디네이터에게 escalation 으로 알렸다**(다른 워커의 pytest·네이티브 빌드도 같은
이유로 깨질 수 있다). `pod install` 이 건드린
`mobile/ios/Runner.xcodeproj/project.pbxproj`·`Runner.xcworkspace/contents.xcworkspacedata`·
`Podfile.lock`·`ios/Pods/` 는 **이 티켓 범위 밖이라 전부 되돌렸다**(CocoaPods 통합을
커밋할지는 22/34 가 정할 일이다). 작업 트리는 clean 이다. iOS 쪽 회귀는
`test/config/ios_project_test.dart`(22) 가 설정 파일을 직접 읽어 계속 지킨다 —
이 티켓은 Dart 레이아웃 코드만 바꿨고 Podfile·플러그인·에셋을 건드리지 않았다.


### 마이그레이션 head

이 티켓은 마이그레이션을 만들지 않았다. 확인만 했다.

```
$ FLASK_APP=wsgi.py DATABASE_URL=...chosung_daily_test_t24_migrations \
  ./scripts/check_migration_heads.sh
dae1b5af0cf7 (head)
OK: Alembic head 1개
```

## 3. 구현에서 실제로 잡은 것 두 가지

테스트를 먼저 쓰면서(red → green) 설계가 두 번 바뀌었다. 둘 다 "위젯만 바꿔 끼우면
된다" 는 첫 구현을 깬 문제라 적어 둔다.

### (a) rail 이 생기고 사라질 때 Element 가 버려진다

첫 구현은 `Row(children: [if (hasRail) rail, content])` 였다. 폭이 바뀌면 `Row` 의
자식 수가 1 ↔ 2 로 바뀌는데, 키가 없으면 Flutter 가 기존 `Expanded` 를 새 것으로
보고 **콘텐츠 subtree 를 통째로 버린다** — 입력 중 텍스트와 스크롤 위치가 날아간다.
콘텐츠에 `ValueKey('adaptive-content')` 를 붙여 Element 가 재사용되게 했다.
"폭이 390 → 744 → 390 이어도 …" 테스트가 이걸 지킨다.

### (b) rail 의 시맨틱스가 통째로 사라진다 (실제 접근성 결함)

22 의 `접근성 레이블이 탭마다 붙어 있다` 테스트가 rail 로 바뀐 뒤 깨졌다. rail 은
화면에 보이고(`find.text('순위')` 1개, 크기 80×600) **시맨틱스 트리에만 없었다.**
원인은 `Row` 의 그리는 순서다 — 콘텐츠 안쪽 go_router 분기 `Navigator` 의 라우트
배리어가 `BlockSemantics` 를 들고 있고, 그게 **먼저 그려진 형제(= rail)의 시맨틱스를
전부 지운다**. 22 에서는 탭 바가 `Scaffold.bottomNavigationBar`(본문보다 나중에
그려지는 슬롯)에 있어서 드러나지 않았다. 콘텐츠를 `Semantics(container: true)` 로
감싸 그 지우기를 콘텐츠 안쪽에 가뒀다(디버깅 과정에서 `Row` 자식 순서를 뒤집어
보면 시맨틱스가 살아나는 것으로 원인을 확정했다). 스크린 리더로 태블릿 탭을 아예
못 읽는 결함이었고, 지금은 22 의 그 테스트가 무변경으로 통과한다.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

**브라우저 도구·`impeccable detect` 는 쓰지 않는다**(HTML/CSS 용이다). 22 와 같이
소스를 `reference/ios.md` + `reference/android.md` 기준으로 읽고 5개 축에 점수를
매겼다. 이 티켓은 체크리스트에 **"태블릿 폭(744·1024·1366) 포함"** 항목을 더해
Adaptivity 를 그 세 폭 + 834 + 390 + 320 으로 확인했다(SCREENS "태블릿 레이아웃"
요구). 폭별 확인은 눈이 아니라 위젯 테스트로 했다.

| # | 축 | 22 | 24 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 3 | 3 | rail 시맨틱스가 지워지던 결함을 §3(b) 에서 고쳤다. rail·탭 바 레이블·글자 1.3배 통과. `StreakBadge` 가 "연속 기록" 문맥 없이 숫자만 읽히는 건 그대로(티켓 23) |
| 2 | Performance | 3 | 3 | 변화 없음. 폭 변화는 레이아웃만 다시 돌고 Element 는 재사용된다(§3(a)) — 분기 Navigator 가 다시 세워지지 않는다 |
| 3 | Appearance & Theming | 4 | 4 | rail 도 `AppColors` 토큰만 쓴다. raw hex 는 여전히 `app_colors.dart` 한 파일뿐 |
| 4 | Platform Conformance | 3 | 3 | Material `NavigationRail`(기본 선택 표시만 OVERRIDES 때문에 끔). 시스템 back·edge-swipe 를 건드리지 않는다. 아이콘 Lucide 는 의도된 이탈(22 와 동일) |
| 5 | **Adaptivity** | **2** | **3** | 22 의 P2 "태블릿에서도 하단 탭 바" 해소 — `android.md` "Navigation bar (bottom, 3–5 destinations) on compact width; navigation rail or drawer on expanded width. Never ship a phone bottom-bar untouched on a tablet." 를 만족한다. **남은 1점은 화면별 2열(T1·T3·T4)이 아직 placeholder 라서** — 티켓 25~32 |
| **합계** | | **15/20** | **16/20** | **Good** (약한 축: Adaptivity — 2열 재배치가 뒤 티켓) |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 세 폭 모두에서 rail 1개 ·
`NavigationBar` 0개이고 콘텐츠 열이 rail 을 제외한 폭을 받는다
(`adaptive_scaffold_test.dart` 의 폭별 테스트 3개 + 앱 트리 쪽 3개). 834(iPad 세로
전체)와 390(폰), 320(Split View 최소)도 같이 본다. 회전·Split View 는 폭 왕복
테스트가 상태 유지까지 확인한다.

### 의도된 이탈 (22 에서 이어짐 + 이 티켓 1건)

1. **아이콘이 Lucide** — OVERRIDES §8(웹과 앱이 같은 아이콘 세트). **P2**, 바꾸려면
   OVERRIDES 를 먼저 고쳐야 한다.
2. **그림자 0 / tonal elevation 미사용** — OVERRIDES §4. **P3**.
3. **Dynamic Color 미사용** — OVERRIDES §2. **P3**.
4. **(이 티켓) `NavigationRail` 의 기본 선택 표시(indicator)를 끈다** — Material 은
   pill 모양 면 채움을 쓰지만 OVERRIDES §2 가 brand 면 채움을 금지한다(라이트
   `#EA580C` on `#FAFAF9` ≈ 3.9:1 로 AA 미달). 하단 탭 바와 **같은**
   `_SelectedTabIcon`(아이콘 + brand 밑줄)로 통일했다. **P3** — 선택 상태는 밑줄 +
   아이콘 색(`foreground` vs `mutedForeground`) + Material 의 `selected` 시맨틱스로
   알리므로 색만으로 구분하지 않는다.
5. **(이 티켓) rail 을 medium(600)부터 쓴다** — `android.md` 문장은 "expanded width"
   라고만 적지만 Material 3 의 window size class 권고(medium 600~839 = rail)와
   스펙 §B.19·SCREENS 표를 따랐다. **P3**, 문서 기준끼리의 차이다.

### 남은 결함 (뒤 티켓이 받는다)

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | 각 탭 | expanded(≥840) 2열·넓은 표가 아직 1열 placeholder — 이 티켓은 뼈대만 | 티켓 25~32 (SCREENS T1·T3·T4) |
| P2 | `AdBannerSlot` | 예약 높이 50/90 이 **잠정값** — SDK 실측이 아니다 | 티켓 31 (`getCurrentOrientationAnchoredAdaptiveBannerAdSize`) |
| P3 | `lib/screens/today_tab.dart` | `StreakBadge` 가 "3일" 만 읽힌다 | 티켓 23 |
| P3 | `lib/widgets/skeleton_box.dart` | 스켈레톤이 스크린 리더에 노출된다 | 티켓 23·25 |
| P2 | — | **시뮬레이터·실기기 스크린샷 없음** — 태블릿 폭 확인은 전부 위젯 테스트다 | 티켓 35(iPad 스크린샷)·36 |

## 5. 검증 한계 (숨기지 않는 것)

- **네이티브 빌드·실기기를 돌리지 않았다.** 이 티켓은 Dart 레이아웃 코드만 바꾸고
  Gradle/Podfile·플러그인·에셋을 건드리지 않아서 22 가 한 `flutter build apk --debug`
  를 다시 돌릴 이유가 없었다. 실제 iPad 에서의 rail 폭·배너 겉모습은 티켓 35·36 의
  사람 체크리스트가 받는다.
- **`tester.binding.setSurfaceSize` 를 쓰지 않았다.** 티켓 본문은 그걸 지정했지만
  Flutter 3.38 에서는 `MediaQuery` 에 반영되지 않는다 — 표면만 바뀌고
  `MediaQuery.sizeOf(context).width` 는 기본 800 그대로다(작은 테스트로 직접 확인:
  `SEEN=[800.0]`). 그래서 회전·Split View 가 실제로 바꾸는 값인
  `tester.view.physicalSize`(+ `devicePixelRatio`)를 쓴다. 폭 390→744→390 왕복이라는
  티켓의 요구 자체는 그대로 지켰다.
- **목업이 없는 화면이다.** SCREENS "태블릿 레이아웃" 의 ASCII 와이어 + OVERRIDES
  토큰만으로 만들었다(SCREENS 가 "목업 없음" 으로 명시). 그래서 "디자인과 다르게
  구현" 한 곳은 없고, 대신 위 "의도된 이탈" 4·5 가 Material 기본값과의 차이다.
