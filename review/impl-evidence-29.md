# 티켓 29 구현 증거 — 앱 계정 연결·전환·백업 코드·삭제 다이얼로그

**브랜치:** `dosaem/t29-app-account-link-switch-delete` · **날짜:** 2026-10-14
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 29.` 한 절 +
`docs/RELEASE.md` `### 29.` 한 절. **백엔드·웹·마이그레이션은 한 줄도 건드리지
않았다** — `POST /auth/token-exchange`(티켓 10)와 `DELETE /me`(티켓 14)는 이미
있고, 앱이 부르기만 한다. 티켓이 못 박은 대로 **새 서버 엔드포인트를 만들지
않았다**(백업 코드 확인은 `GET /me/stats` 재사용).

## 0. 한 줄 요약

S4 의 AccountCard·백업 코드 시트·삭제 다이얼로그를 채우고, 네 경로(구글·애플
연결 / 백업 코드 / 계정 삭제)를 "토큰을 갈아끼우고 로컬 상태를 버린 뒤 서버에서
다시 읽는다" 한 길로 모았다. 앱 테스트 **376개 통과**(이 티켓이 더한 건 45개 — 신규 파일 3개 33개 + 기존 파일 12개,
골든 1장 추가), `flutter analyze` 0건 · `dart format` 변경 없음, 백엔드 `ruff
check` 통과 · pytest 전체 통과(§6).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| ApiClient 에 `POST /auth/token-exchange`, `DELETE /me` 추가(Dio + Fake) | `test/api/dio_api_client_test.dart` 그룹 "계정 연결·전환·삭제 (티켓 29)" 7개 — 경로·메서드·Bearer·구글은 `authorization_code` 키 자체가 없음·애플은 동봉·401/409 예외 분기·204 본문 없음·토큰 인자 분리·빈 코드 차단. `test/fakes/fake_api_client.dart` 에 세 메서드 + 호출 기록 | §3.1 |
| `google_sign_in` 7.x `authenticate()`, iOS 는 `Info.plist`(`GIDClientID`)·URL scheme, Android 는 `serverClientId`(dart-define), `sign_in_with_apple`(iOS) id_token + authorization_code. 성공 시 토큰 교체 → 홈·기록 재조회·로컬 상태 폐기 | `test/config/native_login_config_test.dart` 4개(Info.plist 치환·xcconfig `#include?`·entitlement 3설정·dart-define 2잡+fastlane), `test/account/account_controller_test.dart` "id_token 을 교환해 받은 토큰을 저장하고 기록을 다시 읽는다"·"애플은 authorization_code 를 같이 보낸다", `test/screens/records_account_test.dart` "구글 연결에 성공하면 전환 안내와 함께 기록을 다시 읽는다" | §3.2·§3.3·§3.5 |
| 27 의 AccountCard 자리를 채움: 미연결(버튼, Android 는 구글만) / 연결됨(아이콘 + 마스킹 이메일 + "전환됨") · `ACCOUNT_ALREADY_LINKED`·`INVALID_ID_TOKEN` 문구 | `test/screens/records_account_test.dart` 그룹 "AccountCard" 7개, `test/account/account_controller_test.dart` "다른 토큰이 오면 전환이다"·"같은 토큰이 오면 전환이 아니라 연결이다"·"이미 연결된 계정·틀린 id_token 은 각각의 문구다"·"maskEmail 은 …" | §3.2·§3.3 |
| 백업 코드 시트: Bearer 로 `GET /me/stats` → 200 교체·폐기·재조회 / 401 "올바르지 않은 백업 코드". 전환 완료 = 게스트 토큰 Provider 값 교체. 새 엔드포인트 없음 | `test/api/dio_api_client_test.dart` "백업 코드 확인은 저장된 토큰이 아니라 받은 토큰으로 /me/stats 를 부른다"·"틀린 백업 코드는 401…", `test/account/account_controller_test.dart` 그룹 "백업 코드" 2개, `test/screens/records_account_test.dart` 그룹 "백업 코드 시트" 3개 | §3.1·§3.2·§3.3 |
| 26 의 S2 연결 안내 자리에 첫 완료 후 1회 안내(로컬 플래그) | `test/widgets/result_sheet_test.dart` 그룹 "계정 연결 안내(US 20)" 4개(한 번 뜨고 플래그가 켜진다 / 이미 봤으면 안 뜬다 / 이미 연결돼 있으면 안 뜨고 플래그도 안 켠다 / 누르면 닫고 내 기록 탭) | §3.4 |
| 27 의 삭제 자리에 destructive 버튼 + 다이얼로그(되돌릴 수 없음·구독 별도 해지) → `DELETE /me` → 로컬 전부 삭제 → 새 게스트 → 온보딩 완료 상태 유지 | `test/screens/records_account_test.dart` 그룹 "계정 삭제" 3개, `test/account/account_controller_test.dart` 그룹 "계정 삭제" 2개(온보딩 자리 플래그가 살아남는 것 포함) | §3.2·§3.3 |
| 태블릿: 백업 코드 시트·삭제 다이얼로그는 `showAdaptiveSheet`(폭 744 위젯 테스트 1건). AccountCard 는 27 의 S4 열 안에 그대로 | `test/screens/records_account_test.dart` "폭 744 에서는 백업 코드 시트와 삭제 다이얼로그가 다이얼로그로 뜬다"(Dialog 1 · BottomSheet 0 · 폭 ≤560), 기존 `test/screens/ranking_records_tablet_test.dart` 7개가 그대로 통과(열 배치 불변) | §3.3·§3.6 |
| 위젯 테스트: 플랫폼별 버튼 노출, 전환 후 재조회, 백업 코드 200/401, 삭제 후 새 게스트. `audit.native`(태블릿 폭 포함) 통과, 목업 `e4_records` 대비 | 위 네 그룹 + §4 체크리스트 + §5 골든 3장(`records_light_390`·`records_linked_390`(신규)·`records_tablet_1024`) | §3.3·§4·§5 |

**마이그레이션 없음** → `flask db heads` 는 해당 없다(`migrations/` 변경 0건,
§2 의 파일 목록 참고). 백엔드 파이썬 파일 변경 0건.

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/account/social_sign_in.dart` | `SocialSignIn` typedef(SDK 경계) + `PlatformSocialSignIn`(google_sign_in 7.x `authenticate()` / sign_in_with_apple) + `AccountProvider`·`SocialCredential` |
| `mobile/lib/account/account_controller.dart` | `AccountNotifier` — 연결·전환·백업 코드·삭제를 `_adopt(token)` 하나로 모은다. `maskEmail` 순수 함수 |
| `mobile/lib/local/local_flags.dart` | `LocalFlag`(키 + `perAccount`) + `LocalFlagStore`(규칙은 base 에, 저장소만 교체) + secure storage 구현 |
| `mobile/lib/widgets/account_card.dart` | OVERRIDES §6 `AccountCard`. 미연결 버튼 / 연결됨 한 줄 / 오류 한 줄 |
| `mobile/lib/widgets/backup_code_sheet.dart` | 백업 코드 입력(`showAdaptiveSheet`) |
| `mobile/lib/widgets/delete_account_dialog.dart` | 삭제 확인(`showAdaptiveSheet`). 지우는 일은 하지 않고 묻기만 한다 |
| `mobile/ios/Runner/Runner.entitlements` | `com.apple.developer.applesignin` |
| `mobile/ios/Flutter/Secrets.xcconfig.example` | iOS 클라이언트 ID·URL 스킴 자리표시자(실제 파일은 gitignore) |
| `mobile/test/account/account_controller_test.dart` (15) · `mobile/test/screens/records_account_test.dart` (14) · `mobile/test/config/native_login_config_test.dart` (4) · `mobile/test/fakes/in_memory_local_flag_store.dart` · `mobile/test/golden/records_linked_390.png` | §3 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/api/api_client.dart` · `dio_api_client.dart` | `exchangeIdToken`·`deleteAccount`·`fetchMyStatsWithToken` 추가. `_authorized()` 를 `_bearer(token)` 로 갈라 빈 토큰을 한 자리에서 막는다 |
| `mobile/lib/api/api_exception.dart` | `InvalidIdTokenApiException`·`AccountAlreadyLinkedApiException` + 코드 매핑 2줄 |
| `mobile/lib/config/app_env.dart` | `googleServerClientId`(dart-define) + 빈 값 → null |
| `mobile/lib/screens/records_tab.dart` | 계정·백업 코드·삭제 자리 3개를 실제 동작으로. 삭제는 SettingsRow → destructive 텍스트 버튼(SCREENS S4) |
| `mobile/lib/widgets/result_sheet.dart` · `lib/screens/today_tab.dart` | 연결 안내를 로컬 플래그로 1회만 + 누르면 내 기록 탭(`onLinkAccount`) |
| `mobile/lib/settings/puzzle_language_controller.dart` | **(티켓 27 코드 1줄)** 퍼즐 언어의 출처를 `startupStatsProvider` → `myStatsProvider` 로. 이유는 §7 |
| `mobile/ios/Runner/Info.plist` | `GIDClientID`·`CFBundleURLTypes` 를 빌드 설정 치환으로 |
| `mobile/ios/Flutter/{Debug,Release}.xcconfig` · `ios/Runner.xcodeproj/project.pbxproj` · `mobile/.gitignore` | `#include? "Secrets.xcconfig"`, `CODE_SIGN_ENTITLEMENTS` 3개 설정, Secrets 무시 |
| `mobile/pubspec.yaml` · `pubspec.lock` | `google_sign_in ^7.2.0`, `sign_in_with_apple ^7.0.1` |
| `mobile/assets/translations/{ko,en}.json` | `account` 사전 24개(섹션 끝에 덧붙임, 다른 키 변경 0) |
| `mobile/test/...` 6개 harness | `localFlagStoreProvider` 가짜 주입 + 자리 활성화에 맞춘 단언 수정 |
| `README.md` · `docs/RELEASE.md` | 자기 번호 소제목 `### 29.` 만 섹션 끝에 추가 |

`.env.example` 은 더할 내용이 없다 — `GOOGLE_IOS_CLIENT_ID`·`GOOGLE_WEB_CLIENT_ID`·
`APPLE_APP_BUNDLE_ID` 는 티켓 10 이 이미 넣었고 이 티켓은 **서버 설정을 늘리지
않는다**. README API 표도 두 엔드포인트(93행)가 이미 있어 건드리지 않았다.
스펙 "미정 항목" 에 새로 생긴 미정은 없다.

## 3. 테스트 (무엇을 증명하는가)

### 3.1 API 경계 — `test/api/dio_api_client_test.dart` (+7, 파일 합계 29)

- `POST /auth/token-exchange` 가 Bearer 를 달고 `{provider, id_token}` 을 보낸다.
  **구글은 `authorization_code` 키 자체가 없다**(null-aware map entry) — 서버가
  "애플인데 코드가 비었다" 와 "구글이라 없다" 를 혼동하지 않는다.
- 애플은 `authorization_code` 를 동봉한다(§A.6 revoke 용).
- 401 `INVALID_ID_TOKEN` → `InvalidIdTokenApiException`(게스트 토큰이 끊긴
  `UnauthorizedApiException` 과 **다른 타입**이다 — 전자는 새 게스트를 발급하면
  안 된다), 409 `ACCOUNT_ALREADY_LINKED` → 전용 타입.
- `DELETE /me` 는 본문 없는 204 라 `_send` 의 `response.data!` 를 타지 않는다.
- `fetchMyStatsWithToken` 은 **저장된 토큰이 아니라 인자 토큰**으로 Bearer 를
  만든다(백업 코드), 401 은 그대로 올라오고, 공백뿐인 코드는 서버까지 안 간다.

### 3.2 계정 컨트롤러 — `test/account/account_controller_test.dart` (15)

실제 `ProviderContainer` 에서 돌린다. 가짜는 서버·secure storage·로그인 SDK
세 경계뿐이고, 토큰 교체·무효화·재조회는 앱 코드가 그대로 돈다.

- 구글 연결: 교환 → 저장소 토큰 교체 → `todayPuzzleProvider`·`historyProvider`
  가 **다시 읽힌다**(호출 횟수 +1) → `/me/stats` 1회.
- 애플: `authorization_code` 동봉.
- **전환 판정**: 돌아온 토큰이 다르면 `switched == true`, 같으면 false.
- **계정을 전환하면 퍼즐 언어도 새 계정 값**(ko → en).
- 로그인 창을 닫으면(=null) 교환도 토큰 교체도 없고 오류 문구도 없다.
- `ACCOUNT_ALREADY_LINKED`·`INVALID_ID_TOKEN`·SDK 실패가 각각의 문구 키로
  눕고, 실패하면 **쓰던 토큰은 그대로다**.
- 백업 코드: 200 이면 앞뒤 공백을 떼고 그 토큰으로 교체(+`switched`), 401 이면
  토큰을 바꾸지 않고 "올바르지 않은 백업 코드".
- 삭제: `DELETE /me` → 새 게스트 발급 → 토큰 교체. **`perAccount` 플래그만
  지우고 앱이 모르는 키(`onboarding_done` — 티켓 28 자리)는 남는다.** 삭제가
  실패하면 토큰도 플래그도 그대로고 새 게스트를 발급하지 않는다. 삭제는 됐는데
  **새 게스트 발급이 실패해도 앱이 토큰 없이 남지 않는다**(죽은 토큰을 들고
  있다가 다음 시작의 401 경로가 복구한다).
- 도는 동안 다음 요청을 받지 않는다(SDK 호출 1회).
- `maskEmail`: `hsseo@gmail.com` → `hs***@gmail.com`, 한 글자·빈 로컬파트·애플
  비공개 메일.

### 3.3 S4 화면 — `test/screens/records_account_test.dart` (14)

실제 `RecordsTab` 을 띄우고 누른다.

- iOS 는 구글·애플 두 버튼, **Android 는 구글만**(애플 버튼이 아예 없다).
- 연결됨이면 "Google · hs\*\*\*@gmail.com 연결됨" 이고 연결 버튼은 사라진다.
- 구글 연결 성공 → 카드가 연결됨 + "이 계정의 기록으로 전환됐어요", streak 숫자가
  새 계정 값(42일)으로 바뀌고, 오늘 퍼즐·7일 그리드가 다시 읽힌다.
- 두 오류 문구가 카드 아래 한 줄로 뜨고 토큰은 그대로.
- 백업 코드 시트: 200 → 시트가 닫히고 토큰 교체 / 401 → **시트가 열린 채로**
  `errorText` / 빈 입력이면 제출 버튼이 비활성.
- 삭제: 다이얼로그 문구(되돌릴 수 없음 + 스토어 별도 해지) → 취소하면 아무것도
  안 지운다 → 삭제하면 `DELETE /me` 1회 + 새 게스트 1회, 플래그가 지워지고
  "계정을 삭제하고 새로 시작했어요" + 연결 버튼이 다시 보인다.
- 태블릿 744: 두 시트 모두 `Dialog`(BottomSheet 0), 폭 ≤ `AdaptiveSheet.maxDialogWidth`.

### 3.4 S2 연결 안내 — `test/widgets/result_sheet_test.dart` (+4, 파일 합계 25)

- 첫 완료 뒤 한 번 뜨고, **띄운 그 자리에서** `link_account_notice_seen` 이
  켜진다(닫았든 그냥 지나갔든 본 건 같다).
- 이미 켜져 있으면 안 뜬다.
- 계정이 이미 연결돼 있으면 안 뜨고 **플래그도 켜지 않는다** — 계정을 지우고
  새로 시작하면 그때 한 번 본다.
- 누르면 시트를 닫고 내 기록 탭으로 보낸다(`onLinkAccount`).

### 3.5 네이티브 설정 — `test/config/native_login_config_test.dart` (4)

Dart analyze/test 가 전혀 안 보는 파일들이라 `ios_project_test.dart` 와 같은
방식으로 직접 읽는다.

- `Info.plist` 가 `$(GOOGLE_IOS_CLIENT_ID)`·`$(GOOGLE_IOS_URL_SCHEME)` 를
  참조한다(값을 박지 않는다).
- `Debug`·`Release` xcconfig 가 `#include? "Secrets.xcconfig"` 로 **선택적**으로
  읽고, 실제 파일은 레포에 없으며 `.gitignore` 에 있다.
- `Runner.entitlements` 에 `com.apple.developer.applesignin` 이 있고, pbxproj 의
  `CODE_SIGN_ENTITLEMENTS` 가 **정확히 3번**(Debug/Release/Profile) 나온다 —
  하나만 빠져도 그 빌드에서 애플 로그인이 1000 오류로 떨어진다.
- `AppEnv.googleServerClientId` 는 테스트에서 비어 있고 `…OrNull` 이 null 이다.
  릴리스 경로(`flutter.yml` 2개 잡 + android/ios Fastfile)가 이 define 을 넘긴다.

### 3.6 다른 티켓 테스트에 준 영향

- `test/screens/records_tab_test.dart` "28~32 가 채울 자리는 전부 있고 아직
  눌리지 않는다" → 자리 8개 존재 확인은 그대로, **"비활성" 단언은 아직 남은
  5개**(구독·일일 알림·리마인더·광고 개인정보·하는 법)로 좁혔다. 계정·백업
  코드·삭제는 이 티켓이 채웠으므로 비활성이면 틀린 단언이 된다.
- `today_tab_test`·`play_result_refresh_test`·`result_sheet_golden_test` 는
  결과 시트가 로컬 플래그를 읽게 되면서 `localFlagStoreProvider` 가짜를 주입했다
  (주입 안 하면 secure storage 플랫폼 채널로 `MissingPluginException`).
- `ranking_records_tablet_test`(T4 열 배치) 7개는 **손대지 않고 그대로 통과**한다
  — AccountCard 가 27 이 정한 열 안에 그대로 들어갔다는 증거다.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

22·24·25·26·27 과 같은 방식이다 — 브라우저 도구·`impeccable detect` 는 HTML/CSS
용이라 쓰지 않고, 소스를 `reference/ios.md`·`android.md` 기준으로 읽어 5축에
점수를 매긴다. 폭 확인은 눈이 아니라 위젯 테스트(390·744·1024)와 골든 3장이다.

| # | 축 | 27 | 29 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | 백업 코드 시트·삭제 다이얼로그 제목에 `Semantics(header: true)`. 삭제 버튼은 최소 높이 44(`SettingsRow.minHeight` 재사용) + `destructive` 색 + "계정 삭제" 라는 글자 자체가 뜻을 말한다(색만으로 구분하지 않음). 오류는 색 + 문구 둘 다. 백업 코드 오류는 `TextField.errorText` 라 스크린 리더가 입력과 묶어 읽는다. 진행 상태는 스피너가 아니라 "처리하는 중…" 글자(OVERRIDES §7) |
| 2 | Performance | 3 | 3 | 계정 동작마다 무효화하는 provider 는 3개 + `/me/stats` 1회다. 시작 흐름 전체를 다시 돌리지 않는다(§7). 백업 코드는 확인용 `/me/stats` 와 재조회 `/me/stats` 로 2회 — 드문 조작이라 경로를 하나로 두는 쪽을 골랐다(의도, §8) |
| 3 | Appearance & Theming | 4 | 4 | 새 위젯 전부 `AppColors` 토큰만 쓴다(raw hex 는 여전히 `app_colors.dart` 한 파일뿐). 연결 버튼은 `OutlinedButton`(목업의 "구독" 버튼과 같은 결), 삭제는 `destructive` 글자색, 연결됨 아이콘만 `brand`(면 채움 아님 — OVERRIDES §2) |
| 4 | Platform Conformance | 3 | 3 | Material 기본 컨트롤(`OutlinedButton`·`FilledButton`·`TextField`·`TextButton`), 시트/다이얼로그 판정은 `showAdaptiveSheet` 한 곳(T2). 키보드가 올라오면 `MediaQuery.viewInsetsOf` 로 시트 바닥을 띄운다. 애플 로그인은 **iOS 에서만** 노출(§A.6 표). **공식 브랜드 버튼 에셋 미적용** — RELEASE "### 29." 5)에 남겼다 |
| 5 | Adaptivity | 4 | 4 | 폭 390/744/1024 테스트 통과. AccountCard 는 T4 왼쪽 열, 삭제는 오른쪽 열 그대로. 두 시트는 744 이상에서 최대 폭 560 다이얼로그 |
| **합계** | | **18/20** | **18/20** | **Excellent (minor polish)** |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 744 는 이 티켓의 태블릿
테스트, 1024 는 골든 `records_tablet_1024`, 1366·834·320 은 24 의 셸 테스트가
덮는다(이 티켓 골든도 `AdaptiveScaffold` 안에서 찍는다).

### 디자인 파일과 다르게 구현한 곳 (커밋 메시지에도 적는다)

1. **연결됨 줄에 provider 브랜드 아이콘 대신 상태 아이콘(`userCheck`)을 썼다.**
   티켓 체크박스는 "provider 아이콘" 이지만 Lucide 에는 구글·애플 브랜드 마크가
   없고(`chrome` 은 Chrome 로고, `apple` 은 과일 아이콘이다), 두 회사 모두
   자사 로고를 임의 대체 아이콘으로 쓰는 것을 금지한다. 목업 `e4_records` 도
   아이콘 없이 "Google · hs\*\*\*@gmail.com 연결됨" 글자로만 provider 를 말한다 —
   목업을 따르고 상태 아이콘 하나만 뒀다. 공식 에셋 교체는 RELEASE "### 29." 5).
2. **연결 버튼이 `primary-button` 면 버튼이 아니라 외곽선 버튼이다.** OVERRIDES
   §1 이 "면 채움은 제출 버튼 하나뿐" 이라고 못 박았고, 목업에서 같은 자리의
   "구독" 버튼도 외곽선이다. 검정 면 버튼 둘을 나란히 두면 S4 의 무게 중심이
   계정으로 쏠린다.
3. **삭제는 `SettingsRow` 가 아니라 가운데 정렬 텍스트 버튼이다.** 27 이 자리를
   `SettingsRow`(화살표 있는 행)로 잡아 뒀지만 SCREENS S4 는 "맨 아래 destructive
   **텍스트 버튼**" 이고 목업 `e4_records` 도 가운데 빨간 글자다. 키
   (`RecordsSlot.deleteAccount`)는 그대로 둬서 27 의 T4 열 배치 테스트가 계속
   같은 자리를 본다.
4. **"전환됨" 을 별도 배지가 아니라 설명 줄 교체로 보여준다.** 연결됨 카드의
   둘째 줄이 평소엔 "어느 기기에서든 같은 기록", 방금 전환했으면 "이 계정의
   기록으로 전환됐어요" 다. 줄을 하나 더 쌓으면 목업의 2줄 구성이 깨진다.
5. **백업 코드 시트·삭제 다이얼로그는 목업이 없다**(SCREENS "목업 파일 매핑" 에도
   없음). SCREENS S4 의 문구와 OVERRIDES 토큰(간격 24, 제목 `titleMedium`,
   본문 `bodySmall`, 삭제는 `destructive`)으로 지었다.

### 남은 결함 / 의도된 이탈

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | 연결 버튼 | 구글·애플 **공식 로그인 버튼 에셋**이 아니다. 애플은 심사 항목이다 | RELEASE "### 29." 5) — 콘솔 등록 때 |
| P2 | — | 실기기·시뮬레이터에서 실제 구글/애플 로그인 왕복을 해본 적이 없다. 개발자 콘솔에 앱이 아직 없고(README "알려진 제한사항"), 이 티켓은 외부 호출을 전부 fake 로 검증했다 | RELEASE "### 29." 4) 체크리스트 |
| P3 | `AccountCard` | "전환됨" 안내는 앱을 다시 켤 때까지 남는다(세션 상태). 사라지는 시점을 정할 근거가 티켓·SCREENS 에 없어 "방금 한 일" 로 남겨 뒀다 | — (의도) |
| P3 | 백업 코드 | 확인 1회 + 재조회 1회로 `/me/stats` 를 두 번 부른다. 경로를 하나로 두려는 선택이다 | — (의도) |
| P3 | 삭제 후 | 삭제 뒤에도 내 기록 탭에 그대로 머문다(새 게스트의 0 기록을 보여준다). 온보딩으로 되돌리지 않는 건 티켓 조건("온보딩 완료 상태 유지") 그대로다 | — (의도) |
| P2 | `lib/local/local_flags.dart` | 온보딩 완료 플래그는 아직 **없다**(티켓 28 이 만든다). 삭제가 그걸 남기는지는 "앱이 모르는 키가 살아남는다" 로만 증명된다 | 티켓 28 |

## 5. 목업 대비 기록 (골든 3장)

`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`.
Pretendard 를 실제로 불러와 찍는다. 골든 하네스는 iOS 로 고정했다(스토어
스크린샷 기준, 티켓 35).

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `records_linked_390.png` (신규) | `design/stitch/e4_records.png` | 목업의 계정 블록과 같다 — 굵은 "Google · hs\*\*\*@gmail.com 연결됨" + 보조 줄 "어느 기기에서든 같은 기록", 구분은 헤어라인. 다른 점은 위 1(아이콘) |
| `records_light_390.png` (갱신) | 같은 목업의 미연결 상태(목업에 없음) | 준비 중 행 → "어느 기기에서든 같은 기록" + 외곽선 버튼 2개. 다른 점은 위 2 |
| `records_tablet_1024.png` (갱신) | SCREENS T4 와이어 | 왼쪽 열 = streak·7일·계정·구독·백업 코드, 오른쪽 열 = 설정 + 가운데 빨간 "계정 삭제". 열 폭 ≤480 — 27 이 정한 배치 그대로 |

## 6. 검증 (실제 실행 명령과 출력)

### 6.1 앱 테스트 (전체)

```
$ cd mobile && flutter test
+376: All tests passed!
```

파일별(이 티켓이 더하거나 바꾼 것만, `--reporter=failures-only` 의 마지막 줄):

```
test/api/dio_api_client_test.dart           -> +29: All tests passed  (기존 22 + 7)
test/account/account_controller_test.dart   -> +15: All tests passed  (신규 15)
test/screens/records_account_test.dart      -> +14: All tests passed  (신규 14)
test/config/native_login_config_test.dart   ->  +4: All tests passed  (신규 4)
test/widgets/result_sheet_test.dart         -> +25: All tests passed  (기존 21 + 4)
test/golden/ranking_records_golden_test.dart->  +5: All tests passed  (기존 4 + 1)
test/screens/records_tab_test.dart          -> +11: All tests passed  (개수 그대로, 단언만 수정)
```

7 + 15 + 14 + 4 + 4 + 1 = **45개**(파일별 증가분의 합). 지우거나 비활성으로
돌린 테스트는 없다 — `records_tab_test` 만 개수 그대로 단언을 좁혔다(§3.6).

### 6.2 앱 정적 분석·포맷 (CI `flutter-ci.yml` 과 같은 명령)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 1.2s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
(변경 없음 — 종료 코드 0)
```

### 6.3 백엔드 (이 티켓은 백엔드를 안 건드렸지만 회귀가 없는지 돌렸다)

전용 자원으로 돌렸다(다른 워커와 겹치지 않게):

```
$ export TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29?charset=utf8mb4'
$ export TEST_REDIS_URL='redis://localhost:6379/3'
$ export TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29_migrations?charset=utf8mb4'
$ uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 964.07s (0:16:04)
```

```
$ uv run ruff check .
All checks passed!
```

### 6.3b 네이티브 빌드는 돌리지 않았다 — 대신 정적으로 확인한 것

CI(`.github/workflows/flutter-ci.yml`)는 ubuntu 에서 `dart format`·`analyze`·
`flutter test` 만 돌리고 네이티브 빌드를 하지 않는다. 이 머신도 디스크 여유가
적어 Pods/gradle 산출물을 만들지 않았다. 새 플러그인이 네이티브 요구치를
깨지 않는지는 파일로 확인했다:

- iOS 최소 버전: `test/config/ios_project_test.dart` 가 `.dart_tool/package_config.json`
  에 풀린 **모든** 패키지의 podspec `deployment_target` 을 읽어 프로젝트 설정과
  비교한다 — `google_sign_in_ios`·`sign_in_with_apple` 이 추가된 상태에서
  통과했다(§6.1 의 전체 실행에 포함).
- Android 최소 SDK: `google_sign_in_android-7.2.11` 이 `minSdk = 24`,
  `sign_in_with_apple` 이 16 을 요구한다. 앱은 `flutter.minSdkVersion`
  (Flutter 3.38.6 기본값 24)을 그대로 쓰므로 둘 다 만족한다.

실제 `flutter build ipa`/`appbundle` 은 서명·콘솔 등록이 필요한 단계와 함께
`docs/RELEASE.md` "### 29." 4) 의 실기기 체크리스트에서 돈다.

`uv run ruff format --check .` 는 **돌리지 않았다** — CI(`.github/workflows/ci.yml`)
는 `ruff check` 만 돌리고, `ruff format --check` 를 지금 돌리면 이 티켓이 건드리지
않은 파일 60개가 재포맷 대상으로 잡힌다(기존 상태). 이 티켓은 파이썬 파일을 한
줄도 바꾸지 않았다.

### 6.4 rebase 후 상태

```
<REBASE_OUTPUT>
```

## 7. 설계 판단 메모 (리뷰어용)

**왜 `startupProvider` 를 무효화하지 않았나.** 그게 가장 깨끗한 "로컬 상태
폐기" 지만, 무효화하면 `startupProvider` 가 `AsyncLoading` 이 되고 라우터가
스플래시 → 홈 탭으로 보낸다. 연결 버튼을 누른 사용자가 결과("연결됨"·"전환됨")를
보지 못한 채 화면을 떠나는 셈이라, 티켓이 요구한 "연결됨 + 전환됨 안내" 가
사실상 보이지 않는다. 그래서 토큰을 쓰는 provider 만 집어서 버린다.

**그 대가로 티켓 27 코드 한 줄을 바꿨다.** `puzzleLanguageProvider.build()` 가
시작 snapshot(`startupStatsProvider`)을 보면, 계정을 전환해도 설정의 퍼즐 언어
행만 옛 계정 값으로 남는다. `/me/stats` 의 최신 사본인 `myStatsProvider` 를
보게 바꿨다(시작 시점 값은 같으므로 첫 화면은 동일하다). 27 이 이미 넣어 둔
세대 번호(`_generation`)가 "다시 빌드되면 떠나 있던 쓰기 응답을 버린다" 를
그대로 처리한다 — 그 주석이 이 경우를 미리 적어 뒀다. 회귀는 앱 테스트
376개로 확인했고, 전환 시 언어가 따라오는지는 전용 테스트가 하나 있다.

**토큰 비교로 전환을 판정하는 게 안전한가.** 서버 `link_or_switch_account` 는
전환이면 기존 계정의 게스트를, 신규 연결이면 `current_guest` 를 돌려주고,
`GuestResponse` 는 그 게스트의 토큰이다. 같은 게스트면 토큰도 같다. 응답에
구분 필드가 없으므로 이게 유일하게 있는 신호다 — 서버에 플래그를 더하는 건
이 티켓 범위 밖이라(백엔드 무변경) 있는 값으로 읽었다.
