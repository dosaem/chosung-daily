# 티켓 28 구현 증거 — S6 온보딩 3장·언어 선택·알림/ATT 사전 안내·"하는 법" 다시 보기

**브랜치:** `dosaem/t28-app-onboarding-permissions-preprompts` · **날짜:** 2026-10-14
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 28.` 한 절. 백엔드·웹·
마이그레이션은 한 줄도 건드리지 않았다(`migrations/` 변경 0건, `app/`·`web/` 변경 0건).

## 0. 한 줄 요약

첫 실행에 S6 온보딩(iOS 4장 / Android 3장)이 뜨고, 1장 언어 칩이 `PATCH /me` 를
보내고, 알림·ATT 는 **사전 안내 카드를 거친 뒤에만** OS 프롬프트를 띄우며 그 결과를
티켓 30·31 이 읽을 provider 에 남긴다. 완료 플래그는 `shared_preferences` 에 저장되고
S4 설정 "하는 법" 이 같은 화면의 다시 보기 진입점이 됐다. 앱 테스트 391개 통과
(이 티켓이 더한 건 59개, 골든 5장 포함), `flutter analyze` 0건 · `dart format` 변경
없음 · 백엔드 `ruff check` 통과 · `pytest` 통과(§6).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| S6 페이지뷰 3장 + 언어 칩(선택 시 `PATCH /me`), 완료 플래그 로컬 저장 | `test/screens/onboarding_screen_test.dart` 그룹 "첫 실행"(3) · "언어 칩(1장)"(5) · "완료 플래그"(3), `test/onboarding/onboarding_controller_test.dart`(4), `test/onboarding/onboarding_pages_test.dart`(3), `test/onboarding/onboarding_sample_test.dart`(4) | §3.1·§3.2 |
| 27 의 S4 "하는 법" 자리를 실제 진입점으로(완료 플래그 유지) | `test/screens/onboarding_screen_test.dart` 그룹 "설정에서 다시 보기"(2) — 열고 닫기·끝까지 보기 둘 다 `writes == 0`, `test/screens/records_tab_test.dart` "29~32 가 채울 자리는…" | §3.3 |
| 알림 사전 안내 카드 → 허용 시 OS 권한 요청(Android 13+ `POST_NOTIFICATIONS`, iOS) — 결과를 상태로 보관 | `test/screens/onboarding_screen_test.dart` 그룹 "알림 사전 안내(3장)"(3), `test/permissions/permission_providers_test.dart` "알림 권한"(3), `test/config/native_permissions_test.dart`(3) | §3.4 |
| iOS ATT 사전 안내 → `app_tracking_transparency` 프롬프트 — 결과를 상태로 보관. Android 는 생략 | `test/screens/onboarding_screen_test.dart` 그룹 "ATT 안내(iOS 만)"(2), `test/permissions/permission_providers_test.dart` "ATT"(4), `test/onboarding/onboarding_pages_test.dart` | §3.4·§3.5 |
| 태블릿(T0): `ReadingWidth`(600) 가운데, 가로에서도 타일·삽화 크기는 폰과 같다 | `test/screens/onboarding_tablet_test.dart`(5) — 폭 1024×768 에서 본문 폭 600·rail 없음·타일 크기 폰과 동일 | §3.6 |
| 위젯 테스트: 폭 1024 가로에서 3장 스와이프·언어 칩 동작 | 같은 파일 "폭 1024 가로에서 3장을 스와이프로 넘긴다", "폭 1024 가로에서 언어 칩이 동작한다" | §3.6 |
| 위젯 테스트: 온보딩 언어 선택 반영 | "영어를 고르면 PATCH /me 가 가고 예시 타일이 영어로 바뀐다", "온보딩에서 고른 언어가 S4 설정에도 그대로 보인다", "기본 선택은 서버가 돌려준 퍼즐 언어다" | §3.2 |
| 위젯 테스트: 완료 후 재실행 시 홈 직행 | "플래그가 있으면 두 번째 실행은 홈으로 직행한다", `test/routing/startup_redirect_test.dart` 그룹 "온보딩(S6)"(6) | §3.1·§3.7 |
| 위젯 테스트: iOS/Android 분기 | "Android 는 ATT 안내가 없고 3장에서 끝난다"(점 개수까지 확인), `onboarding_pages_test.dart` | §3.5 |
| 위젯 테스트: 설정에서 재진입 | 그룹 "설정에서 다시 보기"(2) | §3.3 |
| `audit.native`(태블릿 폭 포함) 통과 | §4 체크리스트(5축 18/20) + 태블릿 폭 744·1024·1366 근거 | §4 |
| 목업 `e6_onboarding` 대비 기록(2·3장·ATT·알림 안내는 목업 없음 — 명세+토큰) | §5 골든 5장(`onboarding_light_390`·`_dark_390`·`_notice_390`·`_tracking_390`·`_tablet_1024`) | §5 |

마이그레이션을 만들지 않았으므로 `flask db heads` 는 그대로 1개다(§6에 실행 출력).

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/onboarding/onboarding_pages.dart` | `OnboardingPage` 열거 + `onboardingPages(isIos:)` — 장 구성(iOS 4 / Android 3)을 정하는 순수 함수 |
| `mobile/lib/onboarding/onboarding_sample.dart` | 1·2장에 그려지는 예시 보드를 만드는 순수 함수. 서버를 부르지 않는다 |
| `mobile/lib/onboarding/onboarding_store.dart` | 완료 플래그 저장소 인터페이스 + `shared_preferences` 구현 |
| `mobile/lib/onboarding/onboarding_controller.dart` | `onboardingSeenProvider`(`AsyncNotifier<bool>`) + `complete()` |
| `mobile/lib/permissions/notification_permission.dart` | `NotificationPermission` 3상태 · 요청 경계(인터페이스 + `flutter_local_notifications` 구현) · `notificationPermissionProvider`(티켓 30 이 읽는다) |
| `mobile/lib/permissions/tracking_permission.dart` | ATT 요청 경계(인터페이스 + `app_tracking_transparency` 구현) · `trackingStatusProvider`(티켓 31 이 읽는다) |
| `mobile/lib/screens/onboarding_screen.dart` | S6 화면. 헤더(언어 칩·건너뛰기/닫기) · 페이지뷰 · 점 · 장별 버튼 |
| `mobile/test/...` 7개 + 골든 5장 | §3·§5 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/routing/app_routes.dart` | 경로 `/onboarding`·`/how-to` 추가, `startupRedirect` 가 온보딩 플래그를 두 번째 입력으로 받는다 |
| `mobile/lib/routing/app_router.dart` | 두 경로의 `GoRoute`(셸 밖), `onboardingSeenProvider` 변경도 redirect 재실행 |
| `mobile/lib/screens/records_tab.dart` | S4 "하는 법" 자리 → `context.push('/how-to')` |
| `mobile/assets/translations/{ko,en}.json` | `onboarding` 사전 추가 |
| `mobile/pubspec.yaml`·`pubspec.lock` | `app_tracking_transparency`·`flutter_local_notifications` 추가, `shared_preferences` 를 dev → 일반 의존성으로 |
| `mobile/android/app/src/main/AndroidManifest.xml` | `POST_NOTIFICATIONS` 선언 |
| `mobile/ios/Runner/Info.plist`·`ko.lproj/InfoPlist.strings` | `NSUserTrackingUsageDescription`(영/한) |
| `mobile/test/app_startup_branch_test.dart`·`screens/play_result_refresh_test.dart` | 온보딩 저장소를 "이미 본" 상태로 덮는다(실제 앱 트리를 띄우는 두 파일) |
| `mobile/test/screens/records_tab_test.dart` | "하는 법" 이 이제 눌린다 — 나머지 자리만 비활성으로 확인 |
| `mobile/test/golden/records_{light_390,tablet_1024}.png` | "하는 법" 행이 "준비 중" → 화살표로 바뀌어 갱신 |
| `README.md` | "설계 판단" 끝에 `### 28.` 한 절(공통 규칙대로 자기 번호 소제목만 추가) |

`.env.example`·`docs/RELEASE.md`·스펙 "미정 항목" 은 더할 내용이 없어 건드리지 않았다
(새 설정값·새 사람 작업·새 미정이 없다. ATT·알림 권한 문구는 코드와 네이티브 설정에
들어가고, 콘솔 작업은 스펙 §D2 에 이미 있다).

## 3. 테스트 묶음 (59개)

### 3.1 첫 실행 분기 — `test/screens/onboarding_screen_test.dart` "첫 실행"(3) · "완료 플래그"(3)

실제 앱 트리(`ProviderScope → EasyLocalization → ChosungApp`)를 그대로 띄우고 서버·
저장소·OS 권한 세 경계만 가짜로 바꾼다. "시작 흐름이 끝나면 홈이 아니라 온보딩 1장이
뜬다", "다음을 누르면 2장·3장으로 넘어간다", "스와이프로도 장을 넘길 수 있다",
"끝까지 보면 기기에 플래그가 남는다"(`writes == 1`), "건너뛰기도 완료로 친다 — 다시
띄우지 않는다"(권한 요청 0회), "플래그가 있으면 두 번째 실행은 홈으로 직행한다".

### 3.2 언어 칩(5)

"영어를 고르면 PATCH /me 가 가고 예시 타일이 영어로 바뀐다"(`updatedPuzzleLanguages`
== `[en]`, 타일이 `_PPL_` 로 교체), "언어를 바꾸지 못하면 칩 아래 한 줄로 알린다"
(서버가 안 받았으면 예시도 한국어 그대로), "기본 선택은 서버가 돌려준 퍼즐 언어다"
(쓰기 0회), "온보딩에서 고른 언어가 S4 설정에도 그대로 보인다"(온보딩 → 홈 → 내 기록
까지 끌고 가 확인), "언어 칩은 1장에만 있다". 순수 함수 쪽은
`onboarding_sample_test.dart`(4): ko 는 초성 4칸, en 은 모음 자리가 **빈 타일**
(OVERRIDES §3 — 언더스코어 문자 금지).

### 3.3 설정 "하는 법" 재진입(2 + 1)

"S4 '하는 법' 으로 열고 닫으면 내 기록으로 돌아온다" — 다시 보기엔 "건너뛰기" 대신
"닫기" 가 뜨고, 닫으면 `RecordsTab` 으로 돌아오며 **플래그를 다시 쓰지 않는다**
(`writes == 0`). "다시 보기에서도 마지막 장까지 가면 설정으로 돌아온다" 도 같은 확인.
`records_tab_test.dart` 의 자리 테스트는 "하는 법" 만 활성, 나머지 7자리는 비활성으로
바꿔 29~32 의 전제를 그대로 지킨다.

### 3.4 알림 사전 안내(3 + 3 + 3)

화면: "'알림 켜기' 를 눌러야 OS 권한을 묻고 결과가 상태로 남는다"(누르기 전
`requests == 0`), "거부하면 denied 가 남는다", "'나중에' 는 OS 프롬프트를 띄우지
않고 다음으로 넘어간다". provider: 초기값 `notDetermined`, 허용 → `granted`,
거부 → `denied`. 네이티브 설정(`test/config/native_permissions_test.dart`):
매니페스트의 `POST_NOTIFICATIONS`, `Info.plist` 의 `NSUserTrackingUsageDescription`
(빈 문자열이면 실패), 한국어 `InfoPlist.strings`.

### 3.5 ATT · iOS/Android 분기(2 + 4 + 3)

"iOS 는 마지막 장에서 안내 뒤 프롬프트를 띄우고 홈으로 간다"(안내 장에 들어온 시점엔
`requests == 0`, [계속] 뒤 1회, 결과 `denied` 가 `trackingStatusProvider` 에),
"Android 는 ATT 안내가 없고 3장에서 끝난다"(점 3개). provider: Android 는
`notSupported` 로 시작하고 `request()` 를 불러도 프롬프트를 띄우지 않는다.

### 3.6 태블릿 — `test/screens/onboarding_tablet_test.dart`(5)

폭 1024×768(가로): 본문 폭 == `ReadingWidth.defaultMaxWidth`(600), `NavigationRail`
없음(온보딩은 셸 밖 — SCREENS T0), 타일 크기가 폰(390)과 **같은 값**, 3장 스와이프
(마지막 장에서 더 넘어가지 않음), 언어 칩 동작, ATT 안내 카드도 같은 읽기 폭.

### 3.7 라우팅 순수 함수 — `test/routing/startup_redirect_test.dart`(12, 그중 6개가 새 것)

"첫 실행이면 홈 대신 온보딩으로", "플래그를 아직 못 읽었으면 스플래시에서 기다린다",
"플래그 읽기가 실패하면 가두지 않고 홈으로", "점검·업데이트가 온보딩보다 먼저",
"이미 본 사람이 다시 보기로 들어와도 그 자리에 머문다", "아직 안 본 사람이 다시 보기
경로로 들어오면 첫 실행 온보딩으로 모은다".

### 3.8 접근성·테마(4)

"진행 상황은 점 모양이 아니라 말로도 읽힌다"(`안내 1/4` → `안내 2/4` semantics),
"글자 크기를 1.3배로 키워도 네 장 모두 넘치지 않는다"(RenderFlex overflow 는
FlutterError 로 잡혀 테스트가 바로 실패한다), "다크 모드에서도 같은 토큰으로 그린다",
"기기 언어가 영어면 안내도 영어로 나온다"(UI 언어 en + 퍼즐 언어 ko 조합 확인).

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

22·24·25·27 과 같은 방식이다 — 브라우저 도구·`impeccable detect` 는 HTML/CSS 용이라
쓰지 않고, 소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매긴다.
폭 확인은 눈이 아니라 위젯 테스트(390·1024)와 골든 5장이다.

| # | 축 | 27 | 28 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | 제목은 `Semantics(header: true)`, 점은 모양만이 아니라 "안내 N/M" 으로 읽힌다. 언어 칩은 `Semantics(selected:, button:)` + 최소 높이 44, 주 버튼은 테마의 48. 2장은 색만으로 설명하지 않고 "자리까지 맞음 / 아님" 범례를 글로 같이 둔다(타일 자체도 체크·취소선을 쓴다 — 티켓 25 의 `BoardTile` 그대로). 글자 1.3배 테스트 통과 |
| 2 | Performance | 3 | 3 | `PageView` 는 기본 설정(`allowImplicitScrolling: false`)이라 보이는 장만 만든다 — 테스트에서 1장에 있을 때 2장의 글자가 안 잡히는 것으로 확인된다. 예시 보드는 서버를 부르지 않는 const 데이터 |
| 3 | Appearance & Theming | 4 | 4 | 새 위젯 전부 `AppColors` 토큰만 쓴다(raw hex 는 여전히 `app_colors.dart` 한 파일뿐). brand 는 **선택 칩 테두리·불꽃 아이콘·현재 점**에만 썼다 — 면으로 칠한 건 주 버튼(`primary-button`)뿐이다. 알림 안내 카드는 면 없이 헤어라인 1px(OVERRIDES §4) |
| 4 | Platform Conformance | 3 | 3 | 권한은 각 OS 의 표준 API 로만 요청한다(Android 13+ `POST_NOTIFICATIONS`, iOS `UNUserNotificationCenter`/ATT). ATT 는 사전 안내가 닫히는 애니메이션(200ms) 뒤에 띄운다 — 겹치면 iOS 가 프롬프트를 버린다. 정확한 알람 권한은 요청하지 않는다(티켓 30 이 inexact 로 간다) |
| 5 | Adaptivity | 4 | 4 | 폰(390)·태블릿 가로(1024) 모두 `ReadingWidth` 600 가운데, 타일 크기 동일. 내용은 세로 가운데에 서되 짧은 화면·큰 글자에서는 그대로 스크롤된다(`LayoutBuilder` + `minHeight`) |
| **합계** | | **18/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 1024 는 이 티켓의 태블릿 테스트가
직접 덮고, 744·1366·834·320 은 24 의 셸 테스트가 덮는다. 온보딩은 셸 **밖** 화면이라
rail 구간 분기가 없고(`ReadingWidth` 하나로 모든 폭을 받는다) 744·1366 에서 1024 와
달라지는 분기 자체가 없다 — 그래서 폭 테스트를 1024 한 곳으로 줄였다.

### 디자인 파일과 다르게 구현한 곳 / 판단 (커밋 메시지에도 적는다)

1. **1장 타일에 테두리를 두지 않고 `tile-empty` 면을 썼다.** 목업 `e6_onboarding` 은
   타일에 `border: #E7E5E4` 를 그리지만 OVERRIDES §2 `tile-empty` 가 "면 채움, 테두리
   없음" 이고 SCREENS 머리말이 충돌 시 OVERRIDES 우선이라고 못 박았다. 실제 보드
   (`BoardTile`, 티켓 25)와 같은 위젯을 써서 **온보딩에서 본 모양이 첫 퍼즐에 그대로**
   나오게 한 결과이기도 하다.
2. **현재 장을 가리키는 점은 brand 면이다.** OVERRIDES §2 는 brand 면 채움을
   금지하지만 "활성 탭 밑줄" 은 허용한다. 24×8 짜리 진행 표시는 밑줄과 같은 부류의
   가는 디테일로 보고 목업(`bg-[#EA580C]`)을 따랐다. 글자색으로는 쓰지 않았다.
3. **본문은 세로 가운데 정렬이되 스크롤된다.** 목업은 `my-auto` 로 가운데에 두는데,
   그대로 두면 글자를 키웠을 때 위아래가 잘린다. `LayoutBuilder` 로 "최소 높이 =
   보이는 높이" 를 준 스크롤 뷰 안에서 가운데 정렬했다.
4. **"건너뛰기" 를 남겼다.** SCREENS S6 본문엔 없고 목업 헤더엔 있다. 규칙은 설정
   "하는 법" 에서 언제든 다시 볼 수 있으니 첫 실행을 강제로 4장 넘기게 할 이유가 없다.
   다시 보기에서는 같은 자리가 "닫기" 가 된다 — 건너뛸 첫 실행이 아니다.
5. **ATT 안내 장에 "나중에" 를 두지 않았다.** 거부는 시스템 프롬프트에서 하는 게
   ATT 사전 안내의 표준 모양이고(스펙 §B.21 "안내 후 시스템 프롬프트"), 앱 안에 또
   하나의 거부 버튼을 두면 "앱에서 거부 → 시스템 프롬프트가 영영 안 뜸" 이 된다.
6. **2·3장과 ATT/알림 안내는 목업이 없다**(스펙 "디자인 부족 항목"). SCREENS 의 문장과
   OVERRIDES 토큰만으로 만들고 §5 골든으로 결과를 남겼다.

### 남은 결함 / 의도된 이탈

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | 광고 게이트 | UMP 동의 폼은 이 티켓에 없다. ATT 까지만 하고 `trackingStatusProvider` 를 남긴다 | 티켓 31 |
| P2 | 알림 권한 상태 | 앱을 다시 켜면 `notDetermined` 로 돌아간다. OS 에 현재 상태를 다시 묻는 건 티켓 30 의 일이다(정본은 OS — README `### 28.`) | 티켓 30 |
| P3 | 온보딩 | 장을 넘긴 뒤 뒤로 돌아가는 버튼이 없다(스와이프로는 된다). SCREENS 에 없어서 넣지 않았다 | — (의도) |
| P2 | — | 시뮬레이터·실기기 스크린샷은 없다. 골든은 테스트 렌더러이고, **실제 OS 권한 다이얼로그가 뜨는지는 위젯 테스트로 증명할 수 없다**(플랫폼 채널은 가짜로 바꿨다) | 티켓 37 실기기 체크리스트 |
| P3 | 네이티브 빌드 | `flutter build` (apk/ios)는 돌리지 않았다 — 디스크 여유 제약. 새 플러그인 2개의 네이티브 연결은 pod 요구 버전 검사(`ios_project_test.dart`)와 매니페스트/plist 검사까지만 확인했다 | 티켓 34 |

## 5. 목업 대비 기록 (골든 5장)

`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`.
Pretendard·Lucide 를 실제로 불러와 찍는다.

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `onboarding_light_390.png` | `design/stitch/e6_onboarding.png` | 칩 2개 + 건너뛰기 → 타일 4칸(ㅈㅎㅊㅇ) → "하루 한 문제" → 2줄 설명 → 점 → 전폭 검정 버튼 "다음" 까지 같은 순서·같은 배치. 다른 점은 위 1·2·3 |
| `onboarding_dark_390.png` | OVERRIDES §2 Dark 열 | 같은 구성, `background #141A26` · 타일 `muted #253044` · 주 버튼 `#F1F5F9`. brand 는 칩 테두리·점에만 |
| `onboarding_notice_390.png` | 목업 없음(SCREENS S6 3장) | 불꽃 + "연속 12일" → "매일 이어가기" → 설명 → 헤어라인 카드("매일 아침 알려드릴까요?") → [알림 켜기] [나중에] |
| `onboarding_tracking_390.png` | 목업 없음(SCREENS S6 ATT 장) | 확성기 아이콘 → "맞춤 광고 허용" → 설명 → 점 4개(마지막 활성) → [계속] |
| `onboarding_tablet_1024.png` | SCREENS T0 와이어 | rail 없이 `ReadingWidth` 600 가운데, 타일·글자는 폰과 같은 크기, 버튼은 읽기 폭 전폭 |

## 6. 검증 (실제 실행 명령과 출력)

### 6.1 앱 테스트 (전체)

```
$ cd mobile && flutter test
00:27 +392: All tests passed!
```

머지 기준점(`main` = 34ec7ec)에서 같은 명령은 `+332` 였다 — 이 티켓이 60개를 더했다.
파일별로 따로 돌린 결과:

```
test/onboarding/onboarding_pages_test.dart        -> +3
test/onboarding/onboarding_sample_test.dart       -> +4
test/onboarding/onboarding_controller_test.dart   -> +4
test/permissions/permission_providers_test.dart   -> +7
test/screens/onboarding_screen_test.dart          -> +23
test/screens/onboarding_tablet_test.dart          -> +5
test/golden/onboarding_golden_test.dart           -> +5
test/config/native_permissions_test.dart          -> +3
test/routing/startup_redirect_test.dart           -> 12 (기존 6 + 새 6)
```

### 6.2 앱 정적 분석·포맷 (CI `flutter-ci.yml` 과 같은 명령)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 4.3s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 121 files (0 changed) in 0.20 seconds.   # exit 0
```

### 6.3 백엔드 테스트 (전용 자원)

```
$ TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@127.0.0.1:3306/chosung_daily_test_t28?charset=utf8mb4' \
  TEST_REDIS_URL='redis://127.0.0.1:6379/2' \
  TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@127.0.0.1:3306/chosung_daily_test_t28_migrations?charset=utf8mb4' \
  uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 934.19s (0:15:34)
```

DB `chosung_daily_test_t28` / `_migrations` 는 이 티켓 전용으로 새로 만들었고
(root 로 `CREATE DATABASE … ; GRANT ALL ON … TO 'chosung'@'%'`), Redis 는 DB 2 를 썼다.
공용 테스트 DB·Redis 는 건드리지 않았다. 백엔드 코드는 한 줄도 바꾸지 않았으므로
이 1403개는 회귀 확인용이다.

### 6.4 백엔드 린트 · 마이그레이션 head

```
$ uv run ruff check .
All checks passed!

$ ./scripts/check_migration_heads.sh
b1c7d4e0a932 (head)
OK: Alembic head 1개
```

`ruff format --check .` 는 이 레포에서 **CI 에 없는 명령**이고 머지 기준점에서도 60개
파일이 걸린다(이 티켓은 `.py` 를 한 줄도 바꾸지 않았다). CI(`.github/workflows/ci.yml`)
가 돌리는 `ruff check .` 만 게이트로 본다.

### 6.5 돌리지 않은 것

- `flutter build apk` / `flutter build ios` — 이 머신의 디스크 여유 제약으로 네이티브
  빌드는 돌리지 않았다. 새 플러그인 2개의 iOS 최소 버전 요구는
  `test/config/ios_project_test.dart` 가 podspec 을 읽어 검사하고(통과), Android 권한과
  iOS 사용 설명 문자열은 `test/config/native_permissions_test.dart` 가 검사한다.
- 실기기/시뮬레이터에서의 **실제 권한 다이얼로그** — 위젯 테스트는 플랫폼 채널을 가짜로
  바꾼다. 티켓 37 실기기 체크리스트 몫이다.
