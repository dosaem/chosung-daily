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
$ git rebase main
Current branch dosaem/t29-app-account-link-switch-delete is up to date.

$ git status --short
(비어 있음)

$ git log --oneline main..HEAD
42003f5 문서 29: README 설계 판단 · RELEASE 콘솔 등록 체크리스트 · 구현 증거
1ef8601 앱 29: 골든 비교 실패 이미지를 커밋에서 빼고 무시 목록에 넣는다
2bd2ba3 앱 29: 계정 삭제 — 새 토큰을 먼저 받고 죽은 토큰을 덮어쓴다
e0388d3 앱 29: iOS 구글 클라이언트 ID·Sign in with Apple 권한 설정
ca3e7c8 앱 29: S4 계정 카드·백업 코드 시트·삭제 다이얼로그, S2 연결 안내 1회
d48dd69 앱 29: 네이티브 로그인 경계와 계정 컨트롤러 — 토큰 교체 한 길
225445f 앱 29: ApiClient 에 계정 교환·삭제·백업 코드 확인 추가
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

---

## 수정 라운드 1

`review/impl-review-29.md` 라운드 1(FAIL, MAJOR 2 / MINOR 1)의 결함 3개를 전부
고쳤다. 각 결함은 리뷰에 적힌 재현 순서대로 **먼저 실패하는 테스트**로 고정한
뒤 고쳤다(아래 "빨강 → 초록" 은 그 실제 출력이다). 리뷰 파일은 고치지 않았다.

### D-29-1 (MAJOR) — 전환 후 재조회 실패를 성공 처리하며 이전 계정 정보를 유지

**원인.** 계정이 바뀌는 네 경로가 전부 `AccountNotifier._adopt` →
`MyStatsNotifier.refresh()` 를 불렀다. `refresh` 는 **플레이 뒤 재조회**용이라
실패하면 보던 숫자를 그대로 둔다(OVERRIDES §7 — 기록 숫자 하나 때문에 화면을
오류로 덮지 않는다). 그 정책을 계정 경계가 바뀌는 자리에 그대로 재사용한 것이
결함이다. 계정이 바뀌면 옛 `/me/stats` 는 "오래된 사본" 이 아니라 **다른
사람의 값**이라, 토큰은 B 인데 카드는 A 를 보여주고 그 화면에서 누른 삭제가
B 를 지운다. 백업 코드 경로는 그 위에 더해, 코드 확인으로 **이미 받아 둔 B 의
`/me/stats`** 를 버리고 다시 읽고 있었다.

**수정.**

- `mobile/lib/records/my_stats_controller.dart`: `discard()` + `adopt(MyStats?)`
  를 더했다. `adopt` 는 먼저 옛 값을 버리고, `stats` 를 받았으면 그걸 쓰고,
  없으면 새 토큰으로 읽는다. **읽기가 실패하면 옛 값을 되살리지 않고 예외를
  올린다** — 부른 쪽이 그 일이 시작된 자리에 실패 문구를 둘 수 있게.
  `refresh()` 는 손대지 않았다(플레이 경로의 조용한 재조회는 그대로다).
- `mobile/lib/account/account_controller.dart`: `_adopt(token, {stats})` 가
  `refresh()` 대신 `adopt(stats)` 를 부른다. `restoreWithBackupCode` 는 확인
  응답(`fetchMyStatsWithToken`)을 그대로 넘긴다 — 호출이 하나 줄고, 토큰 교체와
  표시 사이에 빈틈이 없다.
- **버리는 값은 `AsyncData<MyStats?>(null)` 이다.** 처음엔 `AsyncLoading`/
  `AsyncError` 로 눕혔는데 테스트가 계속 빨강이었다: Riverpod 3 의
  `$AsyncClassElement`(`riverpod-3.3.2/lib/src/core/element.dart:67`)가 모든
  상태 전이에 `AsyncValue.copyWithPrevious` 를 걸어 **직전 값을 새 상태에
  실어 준다**. 그래서 둘 중 무엇으로 눕혀도 `.value` 로 옛 계정이 되살아난다.
  이 provider 의 값 타입은 `MyStats?` 고 null 은 원래 "아직 모른다 → 스켈레톤"
  이라, null 이 정확히 맞는 표현이다. 이 함정은 주석으로 코드에 남겼다.

**증명하는 테스트.** (앞 3개가 새 테스트, 마지막은 기존 테스트의 단언 갱신)

- `test/account/account_controller_test.dart` — "백업 코드 확인 때 받은 새 계정
  기록을 그대로 쓴다 — 옛 계정이 남지 않는다": A(`a@icloud.com`, streak 99)가
  떠 있는 상태에서 B 의 코드를 넣고, 토큰 교체 뒤 재조회(`fetchMyStats`)만
  네트워크 오류로 실패시킨다 → `myStatsProvider` 가 `b@gmail.com` / streak 4.
- `test/account/account_controller_test.dart` — "구글·애플 연결 전환 뒤 기록을
  못 읽으면 옛 계정을 버리고 오류로 말한다": 토큰은 `other-device-token` 으로
  바뀌고 `myStatsProvider.value` 는 null, 오류는 `account.error_network`.
- `test/screens/records_account_test.dart` — "백업 코드 시트 전환하면 카드가
  바로 새 계정을 보여준다" / "AccountCard 전환 뒤 기록을 못 읽으면 옛 기록이
  사라지고 오류가 뜬다": 같은 순서를 실제 화면에서 돌려 "Apple ·
  a\*\*\*@icloud.com 연결됨" 이 사라지고 "Google · b\*\*\*@gmail.com 연결됨" 이
  뜨는지, 99일이 사라지고 "네트워크에 연결할 수 없어요" 가 뜨는지 본다.
- 기존 "백업 코드 200 이면 그 토큰으로 갈아끼우고 다시 읽는다" 의
  `expect(api.fetchMyStatsCalls, 1)` → `0` 으로 바꾸고, 새 계정 streak(4)을
  확인하는 단언을 더했다. 재조회를 **일부러 없앤** 것이라 횟수 단언을 남겨
  두면 수정이 회귀로 보인다.

빨강(수정 전):

```
+7 -1: test/account/account_controller_test.dart: 구글·애플 연결 전환 뒤 기록을 못 읽으면 옛 계정을 버리고 오류로 말한다 [E]
  Expected: null
    Actual: <Instance of 'MyStats'>
+9 -2: test/account/account_controller_test.dart: 백업 코드 확인 때 받은 새 계정 기록을 그대로 쓴다 — 옛 계정이 남지 않는다 [E]
  Expected: 'b@gmail.com'
    Actual: 'a@icloud.com'
```

### D-29-2 (MAJOR) — 삭제 성공 후 새 게스트 발급 실패 시 삭제된 토큰에 갇힘

**원인.** 삭제는 "서버 삭제 → 로컬 정리 → 새 게스트 발급" 세 걸음인데, 코드가
셋을 **전부 성공 아니면 전부 없던 일**인 한 덩어리로 다뤘다. 그런데 `DELETE
/me` 는 되돌릴 수도, 다시 부를 수도 없는 단계다 — 그 토큰의 게스트는 이미
없어서 두 번째 DELETE 는 401 이다(`app/api/me.py` `delete_me`, 그 docstring 에
적혀 있다). 마지막 걸음(`POST /guests`)이 실패하면 예외가 그대로 올라가
`clearPerAccount()` 와 `_adopt` 에 닿지 못하고, 재시도는 다시 DELETE 부터 돌아
401 로 끝난다. 죽은 토큰·옛 계정 플래그가 그대로 남고, 삭제 자리에는 "삭제
실패" 로 읽히는 문구가 뜬다.

**수정.** `mobile/lib/account/account_controller.dart`

- `bool _serverDeleted` 를 둬서 서버 삭제가 끝났다는 사실을 기억한다. 재시도는
  DELETE 를 건너뛰고 **발급부터 잇는다.** 발급이 성공하면 다시 false 로 돌린다.
- 로컬 흔적(`clearPerAccount()` + `myStatsProvider.discard()`)은 발급을
  기다리지 않고 **서버 삭제 직후** 버린다. 중간에 멈춰도 이미 사라진 계정의
  이름·기록이 화면에 남아 있으면 안 된다.
- 토큰 교체 순서(발급 성공 뒤 `replaceWith`)는 그대로 뒀다 — 앱이 토큰 없는
  상태로 남지 않는다는 기존 성질과 그 테스트가 유효하다.

**증명하는 테스트.** (둘 다 새 테스트. 리뷰가 지적한 "기존 테스트는 토큰이
null 이 아닌지만 본다" 를 메운다 — 두 테스트 모두 **두 번째 DELETE 가 401 을
던지도록** 실제 서버 계약을 가짜에 넣고, 그래도 복구되는지 본다)

- `test/account/account_controller_test.dart` — "계정 삭제 새 게스트 발급이
  실패해도 네트워크가 돌아오면 그 자리에서 복구한다": 1차 실패 직후
  `linkAccountNoticeSeen` 이 false, `myStatsProvider.value` 가 null 임을 먼저
  확인하고, 네트워크 복구 후 재시도에서 `deleteAccountCalls == 1`(DELETE 는
  다시 안 부른다), `createGuestCalls == 2`, 토큰 `fresh-guest`, 오류 null.
- `test/screens/records_account_test.dart` — "계정 삭제 게스트 발급이
  실패했다가 돌아오면 다시 눌러 복구한다": 같은 순서를 실제 화면에서. 1차
  실패 뒤 "Google · a\*\*\*@gmail.com 연결됨" 과 "99일" 이 사라지고 네트워크
  문구가 뜨며, 다시 눌러 "계정을 삭제하고 새로 시작했어요" 까지 간다.

빨강(수정 전):

```
+12 -3: test/account/account_controller_test.dart: 계정 삭제 새 게스트 발급이 실패해도 네트워크가 돌아오면 그 자리에서 복구한다 [E]
  Expected: false
    Actual: <true>        (linkAccountNoticeSeen 이 지워지지 않았다)
```

### D-29-3 (MINOR) — 연결됨 카드에 요구된 provider 아이콘 없음

리뷰 지적을 받아들여 고쳤다(두 줄). 이전 라운드의 "이탈 1" 은 더 이상 해당하지
않는다.

**원인.** `_LinkedAccount` 가 provider 와 무관하게 `LucideIcons.userCheck` 를
그렸다. "Lucide 에 브랜드 마크가 없다" 는 **공식 로고를 쓸 수 없다**는 뜻이지,
두 provider 를 같은 아이콘으로 두어도 된다는 뜻이 아니다. 티켓 체크박스 3 과
SCREENS S4 는 "provider 아이콘" 을 명시했고 OVERRIDES 에 이를 취소하는 규정이
없다.

**수정.** `mobile/lib/widgets/account_card.dart` 에 `providerIcon(String)` 을
더했다 — `google` → `LucideIcons.chrome`, `apple` → `LucideIcons.apple`, 모르는
값은 `providerDisplayName` 과 같은 이유로 `userCheck` 로 떨어진다. 브랜드 마크가
아니라 **provider 를 구분하는 선 아이콘**이다. 공식 로그인 버튼 에셋 교체는
그대로 `docs/RELEASE.md` "### 29." 5) 에 남아 있다.

**증명하는 테스트.** `test/screens/records_account_test.dart` 의 "AccountCard
연결됨 아이콘은 Google 이면 chrome 이다" / "… Apple 이면 apple 이다" / "모르는
provider 면 공통 아이콘으로 떨어진다" 3개. 골든 `records_linked_390.png` 는
아이콘이 바뀌어 `--update-goldens` 로 다시 떴다(계정 블록의 글자 구성·마스킹·
헤어라인은 그대로, 아이콘 글리프만 바뀜).

빨강(수정 전):

```
+18 -4: test/screens/records_account_test.dart: AccountCard 연결됨 아이콘은 Google 이면 chrome 이다 [E]
  Expected: exactly one matching candidate
    Actual: _IconWidgetFinder:<Found 0 widgets with icon "IconData(U+0F207)": []>
```

### 미수정 MINOR

없다. 라운드 1 의 MINOR 는 D-29-3 하나였고 고쳤다.

### 리뷰 지적 중 고치지 않은 것

없다. 세 결함 모두 재현됐고, 리뷰의 판정이 틀렸다고 본 항목은 없다.

### 문서

`README.md` "### 29." 에 설계 판단 두 개를 더했다 — (1) 계정 경계가 바뀌면 옛
`/me/stats` 를 버린다(+ `copyWithPrevious` 함정), (2) `DELETE /me` 는 재시도할
수 없는 단계라 완료를 기억한다. "알려진 제한" 의 아이콘 문장도 지금 구현에
맞게 고쳤다. `docs/RELEASE.md`·`.env.example`·스펙·마이그레이션은 건드리지
않았다.

### 수정 라운드 1 재실행

```
$ cd mobile && flutter test
00:14 +385: All tests passed!

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 5.2s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 114 files (0 changed) in 0.14 seconds.
```

앱 테스트 376 → **385**(+9: 컨트롤러 3, 화면 6). 마이그레이션 변경이 없어
`flask db heads` 는 이번에도 확인 대상이 아니다(`git diff --name-only
main...HEAD` 에 `migrations/` 없음).

백엔드는 이 라운드에서도 안 건드렸지만 회귀가 없는지 같은 전용 자원으로 다시
돌렸다(공용 테스트 DB 는 비우지 않았다):

```
$ export TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29?charset=utf8mb4'
$ export TEST_REDIS_URL='redis://localhost:6379/3'
$ export TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29_migrations?charset=utf8mb4'
$ uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 910.88s (0:15:10)
(종료 코드 0)

$ uv run ruff check .
All checks passed!
```

rebase: 로컬 `main` 은 이번에도 `34ec7ec` 그대로라 `git rebase main` 이
"Current branch dosaem/t29-app-account-link-switch-delete is up to date." 로
끝났다(= 이미 로컬 main 위다). `origin/main` 은 쓰지 않았다.

## 수정 라운드 2

리뷰 `review/impl-review-29.md` "라운드 2" 의 잔여 결함 **MAJOR 1건(D-29-4)**
을 고쳤다. 같은 절의 D-29-1·2·3 은 FIXED 로 재판정됐고 REPEAT 는 없다. 미수정
MINOR 도 없다(라운드 2 MINOR 0건). 리뷰어 지적을 반박한 항목은 없다 — D-29-4
는 재현 그대로 실재했다.

### D-29-4 (MAJOR) — 이전 계정의 삭제 완료 플래그가 복원된 계정의 서버 삭제를 생략시킴

**원인.** 라운드 1 에서 D-29-2 를 고치며 둔 `bool _serverDeleted` 가 **"삭제가
끝났다" 만 기억하고 "어느 계정의 삭제가 끝났는지" 는 기억하지 않았다.** 이
플래그가 참이라는 말은 사실 "지금 저장된 토큰이 가리키는 계정은 서버에서 이미
사라졌다" 라는 뜻이라, **토큰이 바뀌면 성립하지 않는다.** 그런데 토큰을 바꾸는
자리(`_adopt`)와 플래그를 내리는 자리(`deleteAccount` 의 발급 성공 뒤)가 서로
떨어져 있어서, 발급이 실패해 플래그가 참으로 남은 채 백업 코드로 다른 계정을
불러오면 그 참이 새 계정까지 따라왔다. 두 번째 삭제는 `DELETE /me` 와 로컬
정리를 통째로 건너뛰고 새 게스트만 발급하며, 오류가 없으니 화면에는 "계정을
삭제하고 새로 시작했어요" 가 떴다 — 서버의 B 계정과 기록은 삭제 요청조차
받지 않았다.

**수정.** `mobile/lib/account/account_controller.dart`

- `bool _serverDeleted` → `String? _deletedToken`. 삭제가 끝난 **토큰**을
  기억하고, `deleteAccount()` 는 지금 토큰을 읽어(`guestTokenProvider.future`,
  `link()` 이 "전환/연결" 을 가리려고 쓰는 것과 같은 방식) 그 토큰과 같을
  때만 `DELETE /me` 를 건너뛴다. 같은 계정의 발급 재시도(D-29-2)는 그대로
  건너뛰고, 다른 계정이면 제대로 지운다.
- `_adopt` 에서 플래그를 내리는 방식(한 줄로 더 간단하다)을 **쓰지 않았다.**
  토큰을 바꾸는 길이 `_adopt` 만이 아니기 때문이다 — 시작 흐름의 401 복구
  (`mobile/lib/startup/startup_controller.dart` `_fetchStats` → `clear()` +
  `_issueGuestToken()`)도 토큰을 갈아끼운다. "플래그 내리는 자리를 외우는"
  방식은 그 길에서 같은 누수가 다시 난다. 지금 토큰과 맞춰 보는 방식은 토큰이
  어디서 바뀌든 성립한다.
- 발급 성공 뒤에 있던 `_serverDeleted = false` 는 지웠다(비교가 대신한다).

**증명하는 테스트.** (3개 전부 새 테스트)

- `test/account/account_controller_test.dart` — "계정 삭제 삭제 복구 중 다른
  계정으로 전환하면 그 계정도 서버에서 지운다": 리뷰의 재현 순서 그대로
  (`createGuestError` → `deleteAccount()` → 오류 해제 → `restoreWithBackupCode(B)`
  → B 토큰·이메일 확인 → `deleteAccount()`). `deleteAccountCalls == 2`,
  `createGuestCalls == 2`, 토큰 `fresh-guest`, 오류 null.
- `test/account/account_controller_test.dart` — "계정 삭제 삭제 복구 중 시작
  흐름이 토큰을 바꿔도 새 계정을 서버에서 지운다": 같은 원인의 **다른 길**을
  막아 둔다. 발급 실패 뒤 `guestTokenProvider.notifier.replaceWith(...)` 로
  시작 흐름의 401 복구와 같은 토큰 교체를 일으키고 다시 삭제한다.
- `test/screens/records_account_test.dart` — "계정 삭제 발급 실패 뒤 다른
  계정을 불러오면 그 계정을 지운다": 같은 순서를 실제 `RecordsTab`·백업 코드
  시트·삭제 다이얼로그에서. 중간에 "Google · b\*\*\*@gmail.com 연결됨" 을,
  마지막에 "계정을 삭제하고 새로 시작했어요" 를 **먼저** 단언한 뒤
  `deleteAccountCalls == 2` 를 본다 — 리뷰가 지적한 "잘못된 성공 안내" 가
  그대로 재현되는 자리다.

빨강(수정 전) — 리뷰가 보고한 값과 같다:

```
$ flutter test test/account/account_controller_test.dart --plain-name '삭제 복구 중 다른 계정으로 전환하면'
00:00 +0 -1: 계정 삭제 삭제 복구 중 다른 계정으로 전환하면 그 계정도 서버에서 지운다 [E]
  Expected: <2>
    Actual: <1>
  test/account/account_controller_test.dart 492:7  main.<fn>.<fn>

$ flutter test test/screens/records_account_test.dart --plain-name '발급 실패 뒤 다른 계정을 불러오면'
00:01 +0 -1: 계정 삭제 발급 실패 뒤 다른 계정을 불러오면 그 계정을 지운다 [E]
  Expected: <2>
    Actual: <1>
  test/screens/records_account_test.dart 532:7  main.<fn>.<fn>
```

(화면 재현이 멈춘 532 행은 `deleteAccountCalls` 단언이다. 그 **앞**의 "계정을
삭제하고 새로 시작했어요" 단언은 통과했다 — 삭제가 안 된 채로 성공 안내가
뜬다는 리뷰의 지적이 그대로 확인된다.)

위 빨강 출력의 행 번호는 **그때 돌린 시점의 것**이다. 이후 두 번째 재현
테스트와 D-29-3 보정이 같은 파일에 들어가면서 밀렸다 — 지금은 컨트롤러
`test/account/account_controller_test.dart:493`·`:523`, 화면
`test/screens/records_account_test.dart:536` 이 그 단언이다.

초록(수정 후):

```
$ flutter test test/account/account_controller_test.dart test/screens/records_account_test.dart --plain-name '삭제 복구 중'
00:00 +1: 계정 삭제 삭제 복구 중 다른 계정으로 전환하면 그 계정도 서버에서 지운다
00:00 +2: All tests passed!

$ flutter test test/screens/records_account_test.dart --plain-name '발급 실패 뒤 다른 계정을 불러오면'
00:00 +1: All tests passed!
```

**두 번째 테스트가 실제로 더 센지 확인했다.** 더 간단한 수정(`_adopt` 에서
플래그 해제)을 일부러 넣고 돌려 보니, 백업 코드 경로 테스트는 통과하지만 시작
흐름 경로 테스트는 같은 `Expected: <2> / Actual: <1>` 로 실패한다 — 두 테스트가
서로 다른 길을 보고 있다는 증거다(확인 후 되돌렸다).

```
00:00 +1: 계정 삭제 삭제 복구 중 다른 계정으로 전환하면 그 계정도 서버에서 지운다
00:00 +1 -1: 계정 삭제 삭제 복구 중 시작 흐름이 토큰을 바꿔도 새 계정을 서버에서 지운다 [E]
  Expected: <2>
    Actual: <1>
```

### D-29-3 보정 (코디네이터 추가 지시) — 구글 아이콘 `chrome` → 중립 아이콘

라운드 1 에서 D-29-3 을 고치며 Google 자리에 `LucideIcons.chrome` 을 썼는데,
코디네이터가 이를 바로잡으라고 지시했다. **근거: `chrome` 은 구글 계정이 아니라
브라우저 제품의 브랜드 마크다** — 계정 연결 표시에 쓰면 "Chrome 으로 연결됨"
으로 읽혀 다른 제품을 가리킨다(브랜드 오용). 리뷰가 D-29-3 에서 짚은 "Lucide 에
브랜드 마크가 없다는 것은 요구 충족의 증거가 아니다" 는 **비슷한 마크로
대신하라는 뜻도 아니었다.**

- `mobile/lib/widgets/account_card.dart` `providerIcon`: `'google' =>
  LucideIcons.chrome` 분기를 지웠다. Google 은 공통 분기(`LucideIcons.userCheck`)
  로 떨어지고, provider 는 바로 옆 "Google · hs\*\*\*@gmail.com 연결됨" 텍스트
  라벨이 가린다. Apple 은 Lucide 의 `apple` 이 **그 회사** 마크라 그대로 뒀다.
- 공식 'G' 로고 에셋은 저장소에 받아 둔 것이 없어 새로 내려받지 않았다. 공식
  로그인 버튼 에셋은 콘솔 등록과 함께 넣는 출시 전 작업으로 `docs/RELEASE.md`
  "### 29." 에 이미 적혀 있다.
- README 설계 판단 `### 29.` 의 "알려진 제한" 문단을 이 판단으로 갱신했다.
- 테스트 `test/screens/records_account_test.dart` "AccountCard 연결됨 Google 은
  중립 아이콘과 텍스트 라벨로 가른다": 중립 아이콘 1개 + "Google · …" 라벨을
  단언하고 `LucideIcons.chrome` 이 **없음**을 못 박아 되돌아가지 못하게 했다.
  Apple 쪽 테스트는 apple 마크가 뜨고 중립 아이콘이 안 뜨는지로 바꿔 두
  provider 가 여전히 서로 구분되는지 본다.
- 골든 `records_linked_390.png` 를 다시 떴다(194px, 0.06% — 아이콘 자리만).

```
$ flutter test test/screens/records_account_test.dart --plain-name '연결됨'
00:03 +1: AccountCard 연결됨 Google 은 중립 아이콘과 텍스트 라벨로 가른다
00:03 +2: AccountCard 연결됨 아이콘은 Apple 이면 apple 이다
00:03 +2: All tests passed!
```

### 라운드 2 rebase 와 재실행

**rebase 는 이번에 no-op 이 아니었다.** 라운드 1 때와 달리 로컬 `main` 이
`34ec7ec` → `8ddc8fd`(티켓 28 "앱 온보딩·권한 사전 안내" 머지)로 나아가 있었다.
`git rebase main`(로컬 main. `origin/main` 은 쓰지 않았다)에서 충돌 7건을 두
티켓의 뜻을 모두 살려 풀었다:

- `mobile/pubspec.yaml` — 같은 자리에 티켓 28 `shared_preferences`, 티켓 29
  `sign_in_with_apple` 가 각각 들어왔다. 둘 다 필요해서 둘 다 둔다.
- `mobile/assets/translations/{ko,en}.json` — 같은 자리에 형제 키 블록
  (`onboarding` / `account`)이 각각 들어왔다. 둘 다 두고 JSON 파싱으로 확인했다.
- `mobile/test/screens/records_tab_test.dart` — 의미 충돌이다. 티켓 28 이
  "하는 법" 행을 누를 수 있게 만들었고, 티켓 29 는 계정·백업·삭제 행을 채우며
  나머지를 `pending` 집합으로 단언했다. 합치면 `pending` 에서 `howTo` 를 빼고
  (28 이 채웠다) `howTo` 의 `onTap` 이 null 이 **아님**을 단언해야 맞다. 그렇게
  고쳤다 — 한쪽을 고르면 다른 티켓이 채운 자리가 검증에서 빠진다.
- `mobile/test/screens/play_result_refresh_test.dart` — override 가 양쪽 다
  필요하다(onboardingStore + localFlagStore). 둘 다 두고 import 순서를 맞췄다.
- 골든 `records_light_390.png`·`records_tablet_1024.png`·`records_linked_390.png`
  — 3개가 **전부 같은 622px(0.19%/0.08%)** 만큼 어긋났다. 숫자가 같다는 게
  단서라 `failures/..._isolatedDiff.png` 를 직접 열어 보니 차이가 "하는 법" 행
  하나에만 있었다(티켓 28 이 붙인 `>`). 계정 블록은 그대로다. 확인한 뒤
  `--update-goldens` 로 다시 뜨고, 다시 뜬 이미지를 눈으로 열어 계정 카드(29)와
  `>`(28)가 함께 있는지 봤다.

그 밖에 `mobile/test/golden/failures/` 아티팩트가 작업 트리에 남아 있었다.
티켓 29 가 이미 `.gitignore` 에 넣은 경로이고 `main` 에도 추적되지 않는다 —
커밋에 들어가지 않게 지웠다.

재실행(전부 rebase 후, 로컬 main 위):

```
$ cd mobile && flutter test
00:59 +449: All tests passed!

$ cd mobile && flutter analyze
No issues found! (ran in 4.2s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 132 files (0 changed) in 0.28 seconds.

$ export TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29?charset=utf8mb4'
$ export TEST_REDIS_URL='redis://localhost:6379/3'
$ export TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29_migrations?charset=utf8mb4'
$ uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 2126.04s (0:35:26)
(종료 코드 0)

$ uv run ruff check .
All checks passed!
```

앱 테스트 385 → **449**. 늘어난 64개 중 이번 라운드가 더한 것은 4개
(D-29-4 재현 3개 + D-29-3 보정 테스트는 기존 테스트를 고친 것)이고, 나머지는
티켓 28 이 `main` 으로 들어오며 합류한 테스트다. 백엔드는 이번 라운드에도 안
건드렸고 같은 전용 자원(DB `chosung_daily_test_t29`, Redis DB 3)으로 돌렸다 —
공용 테스트 DB 는 비우지 않았고 새 DB 를 만들지도, 기본 DB 로 떨어지지도
않았다. 35분이 걸린 것은 다른 워커(t31·t35)의 pytest 와 같은 기계를 나눠 썼기
때문이고 실패·재실행은 없다. 마이그레이션 변경이 없어(`git diff --name-only
main...HEAD` 에 `migrations/` 없음) `flask db heads` 는 이번에도 대상이 아니다.

작업 트리는 clean 이고 `main`(`8ddc8fd`)이 `HEAD` 의 조상이다.

### 미수정 MINOR

없다. 라운드 2 리뷰의 잔여 결함은 MAJOR 1건(D-29-4)뿐이었고 고쳤다.

### 범위 밖이라 손대지 않은 것 (후속 티켓 제안)

티켓 28 과 29 가 **기기 로컬 플래그 저장소를 각각 하나씩** 들고 왔다
(`mobile/lib/onboarding/onboarding_store.dart`, `mobile/lib/local/local_flags.dart`.
둘 다 shared_preferences 위다). 지금은 서로 간섭 없이 함께 돌고 테스트도 둘 다
통과하지만, 같은 일을 하는 길이 둘인 상태다. 결함이 아니고 이번 수정 범위도
아니라 건드리지 않았다 — 통합은 별도 티켓이 맞다.

## 수정 라운드 3

라운드 3 리뷰의 잔여 결함은 MAJOR 1건(D-29-5)이다. 코디네이터가 추가 지시를
보냈다: "계정 경계를 넘은 뒤에는 이전 계정에서 만든 화면 값으로 **어떤 쓰기
요청도** 나가면 안 된다. 개별 화면마다 막지 말고 토큰 세대 같은 **하나의
장치**로 보장하고, 지연되는 Fake(Completer)로 재현 테스트를 만들어라." 그대로
했다.

### D-29-5 — MAJOR — 계정 전환 후 홈 재조회 중 이전 계정 보드에서 새 계정에 답을 제출할 수 있음

**재현(리뷰의 입력 그대로, 저장소 테스트로 고정).** A 의 보드를 한 번 읽고 →
B 의 백업 코드로 복원(`GET /me/stats` 200) → B 의 `GET /puzzles/today` 만
`fetchTodayPuzzleGate` 로 붙잡고 → 길이가 맞는 답을 제출. 수정 전:

```
$ cd mobile && flutter test test/account/account_controller_test.dart --reporter expanded
00:00 +11 -1: 백업 코드 새 계정 보드를 읽기 전에는 옛 보드가 폐기되고 제출도 막힌다 [E]
  Expected: null
    Actual: <Instance of 'TodayPuzzleReady'>
  옛 계정 보드가 남았다
```

실제 `TodayTab` 에서도 같다 — 보드와 입력창이 그대로 있고 제출 버튼이 살아
있었다(`test/screens/today_tab_test.dart`, 수정 전 1 failed).

**원인은 두 겹이다.**

1. `AccountNotifier._adopt` 가 `ref.invalidate(todayPuzzleProvider)` 만 했다.
   Riverpod 의 무효화는 **값을 지우는 API 가 아니다** — 다시 빌드하는 동안
   직전 값을 새 상태에 실어 준다(`AsyncValue.copyWithPrevious`,
   `riverpod-3.3.2/lib/src/core/element.dart:67` `asyncTransition`). 그래서
   `todayPuzzleProvider` 는 `isLoading == true` 이면서 `value` 에 A 의
   `TodayPuzzleReady` 를 들고 있었고, `TodayTab` 은 그 값 분기를 먼저 고른다
   (`lib/screens/today_tab.dart:93`). 오류도 제출 중 상태도 없어서 입력과
   제출 버튼이 열려 있었다. `MyStatsNotifier` 는 이미 이 함정을 알고
   `discard()`(= `AsyncData(null)`)를 쓰고 있었는데(D-29-1 수정) 홈에는 그
   처리가 없었다. — `AsyncLoading`·`AsyncError` 로 눕히는 것도 답이 아니다:
   `AsyncLoading.copyWithPrevious` 는 `isRefresh` 가 false 여도 `value` 를
   그대로 실어 준다(`core/async_value.dart:780`). 직접 읽고 확인했다.
2. **토큰이 바뀌는 길은 `_adopt` 만이 아니다.** 시작 흐름의 401 복구
   (`StartupNotifier._fetchStats` → `clear()` + `_issueGuestToken()`)도 토큰을
   갈아끼우고, 그 길은 보드를 버려 주지 않는다. 즉 화면 폐기만으로는 "옛 계정
   값으로 쓰기가 나가지 않는다" 를 보장할 수 없다. 제출 쪽도 `state.value` 만
   보고 그 값이 **어느 계정에서** 온 것인지 보지 않았다.

**수정.** 두 겹을 각각 끊었다. 둘 다 새 추상화가 아니라 이미 있는 방식
(`MyStatsNotifier.discard`, 세대 번호)을 그대로 쓴다.

- `TodayPuzzleNotifier.discard()`(`lib/puzzle/today_puzzle_controller.dart`):
  보던 보드를 비우고(`AsyncData(null)` — 화면은 스켈레톤) 세대를 올려 떠나
  있던 옛 계정의 응답까지 버린 뒤 새 계정 보드를 읽는다. provider 상태 타입이
  `TodayState?` 가 된 이유가 이것이다 — "보드를 아직 모른다" 를 null 로 두는
  건 `MyStatsNotifier` 와 같은 규칙이고, 로딩·오류를 `TodayState` 안에 또
  세지 않는다. 경계에서 부르는 자리는 `discardTodayPuzzle(ref)` 하나이고
  (계정 경계 + 언어 경계), "아직 아무도 읽지 않은 홈은 만들지 않는다"
  (`ref.exists`)는 규칙도 그 함수가 들고 있다 — 무효화와 같은 게으름을 지킨다.
- **계정 세대**(`lib/guest/account_epoch.dart`, 코디네이터가 말한 "하나의
  장치"): 토큰이 바뀔 때마다 하나 올라가는 숫자다. 올리는 자리는
  `GuestTokenNotifier.replaceWith`·`clear` 둘뿐이라 — 앱에서 토큰이 바뀌는
  길이 그 둘뿐이라 — 계정 경계의 정의가 한 곳에 있다. 서버에서 읽어 만든 화면
  값은 그때의 세대를 적어 두고, **쓰기는 `sendIfSameAccount(epoch, send)` 로
  감싼다**: 세대가 어긋나면 요청을 보내지 않는다. 지금 이 문을 지나는 쓰기는
  제출(`POST /puzzles/today/guesses`)과 퍼즐 언어(`PATCH /me`) 둘이고, 화면
  폐기를 빼먹은 길이 생겨도 남의 계정에 쓰이지 않는다.
  - 비교를 **요청을 만드는 자리**에 둔 이유: `DioApiClient._authorized()` 는
    매 요청 지금 토큰을 동기적으로 읽어 Bearer 에 붙인다. 보내고 나서
    걸러낼 방법이 없고, 비교와 토큰 읽기 사이에 `await` 가 없어야 한다.

**증명하는 테스트(5개 추가, 전부 수정 전 실패를 확인했다).**

| 테스트 | 무엇을 고정하는가 |
|---|---|
| `test/account/account_controller_test.dart` 백업 코드 — 새 계정 보드를 읽기 전에는 옛 보드가 폐기되고 제출도 막힌다 | 리뷰의 재현 그대로. 보드 폐기 + 제출 0회 + 보드가 도착하면 다시 제출됨 |
| 같은 파일, 계정 삭제 — 삭제한 계정의 보드는 새 게스트 보드가 오기 전에 사라진다 | 삭제 → 새 게스트도 같은 `_adopt` 길이다 |
| `test/screens/today_tab_test.dart` — 계정을 전환하면 새 보드를 읽기 전까지 옛 보드로 제출할 수 없다 | 실제 `TodayTab`: `PuzzleBoard`·`GuessInput` 이 사라지고 스켈레톤이 그 자리를 받는다 |
| `test/puzzle/today_puzzle_controller_test.dart` — 계정이 바뀐 뒤에는 옛 보드로 제출하지 않는다 | `_adopt` **밖**에서 토큰이 바뀐 경우(시작 흐름의 401 복구). 계정 세대가 마지막 문이다 |
| `test/settings/puzzle_language_controller_test.dart` — 계정이 바뀐 뒤의 탭은 새 계정 언어를 덮어쓰지 않는다 | 같은 장치가 두 번째 쓰기(`PATCH /me`)도 막는다 |

수정 전 실패 출력(각각 해당 수정만 되돌려 확인했다):

```
$ cd mobile && flutter test test/account/account_controller_test.dart test/screens/today_tab_test.dart --reporter compact
  (보드 폐기를 되돌림: `_adopt` 가 invalidate 만)
00:06 +11 -1: ... 백업 코드 새 계정 보드를 읽기 전에는 옛 보드가 폐기되고 제출도 막힌다 [E]
00:08 +31 -2: ... 계정을 전환하면 새 보드를 읽기 전까지 옛 보드로 제출할 수 없다 [E]
00:09 +46 -2: Some tests failed.

$ cd mobile && flutter test test/account/account_controller_test.dart --reporter compact
00:04 +13 -2: 계정 삭제 삭제한 계정의 보드는 새 게스트 보드가 오기 전에 사라진다 [E]

$ cd mobile && flutter test test/puzzle/today_puzzle_controller_test.dart test/settings/puzzle_language_controller_test.dart --reporter compact
  (계정 세대 비교만 되돌림)
00:02 +28 -2: ... 계정이 바뀐 뒤에는 옛 보드로 제출하지 않는다 [E]
00:02 +6 -1: ... 계정이 바뀐 뒤의 탭은 새 계정 언어를 덮어쓰지 않는다 [E]
```

### 같이 고친 같은 원인 한 자리 (언어 경계)

스펙 §A.2 는 "**언어 변경**·계정 전환 시 로컬 상태 폐기" 다. 언어를 바꾸는
길도 주석으로는 "스켈레톤부터 다시 간다" 라고 적어 두고 무효화를 하고 있었다 —
같은 함정이라 같은 `discardTodayPuzzle(ref)` 를 쓰게 했고, 옛 언어 보드가 새
보드 전에 사라지는 테스트를 하나 더 붙였다(라운드 3 리뷰의 결함은 아니다).
쓰기(`PATCH /me`)는 계정 세대로 이미 막힌다.

### 리뷰어 지적이 틀렸다고 본 것

없다. D-29-5 는 리뷰의 재현 입력 그대로 저장소 테스트에서 재현됐다.

### 미수정 MINOR·관찰

라운드 3 리뷰에 MINOR·BLOCKER 는 없었다. 고치지 않고 적어 두는 것 둘:

- **7일 그리드(S4)는 계정 전환 중 옛 계정 값이 남는다.** `historyProvider` 는
  `FutureProvider` 라 버릴 notifier 가 없고(`lib/records/history_controller.dart`
  — "읽기 한 번이라 Notifier 를 둘 이유가 없다"), `records_tab.dart:234` 가
  `AsyncValue(:final List<HistoryDay> value)` 분기를 먼저 고른다. 읽기 전용
  표시라 **남의 계정에 쓰는 길은 아니고**, 고치려면 provider 를 Notifier 로
  바꿔야 해서(= 티켓 27 화면의 리팩토링) 이번 결함 범위 밖으로 뒀다. 계정 줄과
  streak 3칸은 `myStatsProvider.discard` 로 이미 비워지므로 화면에 남는 것은
  7일 칸 하나다. 후속 티켓이 `historyProvider` 를 Notifier 로 바꿀 때 같은
  `discard` 를 붙이는 게 맞다.
- **공식 Google/Apple 로그인 버튼 에셋**은 여전히 `docs/RELEASE.md` "### 29."
  의 사람 확인 항목이다(라운드 1~3 과 같음).

### 재실행 (로컬 main 위, 전부 수정 후)

로컬 `main` 은 `8ddc8fd`(티켓 28 머지) 그대로여서 `git rebase main` 은
`up to date` 였다 — 라운드 2 에서 이미 그 위로 올려 둔 상태다.

```
$ git log --oneline -1 main
8ddc8fd Merge 티켓 28: 앱 온보딩·권한 사전 안내

$ git rebase main
Current branch dosaem/t29-app-account-link-switch-delete is up to date.

$ cd mobile && flutter test
00:36 +456: All tests passed!

$ cd mobile && flutter analyze
No issues found! (ran in 4.8s)

$ cd mobile && dart format --output=none --set-exit-if-changed .
Formatted 133 files (0 changed) in 0.18 seconds.

$ cd mobile && flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk
(종료 코드 0, 코디네이터 추가 지시. 끝난 뒤 `mobile/build` 는 지웠다)

$ uv run ruff check .
All checks passed!

$ export TEST_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29?charset=utf8mb4'
$ export TEST_REDIS_URL='redis://localhost:6379/3'
$ export TEST_MIGRATION_DATABASE_URL='mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t29_migrations?charset=utf8mb4'
$ uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 1423.63s (0:23:43)
```

앱 테스트 **449 → 456**. 늘어난 7개 중 6개가 이 라운드의 재현 테스트고(위 표의
5개 + "첫 조회 중 계정이 바뀌면 그 응답은 보드가 되지 않는다"), 1개는 언어
경계 폐기 테스트다. 백엔드는 이번 라운드에도 한 줄도 건드리지 않았고
(`git diff --name-only main...HEAD` 에 `app/`·`migrations/`·`tests/` 없음)
같은 전용 자원(DB `chosung_daily_test_t29`, Redis DB 3, 마이그레이션 전용
`..._migrations`)으로 돌렸다 — 공용 테스트 DB 를 비우지 않았고 새 DB 를 만들지도,
기본 DB 로 떨어지지도 않았다. 1403 passed / 실패·재실행 0. 23분이 걸린 것은 다른
워커(t30·t31)의 pytest 와 같은 기계를 나눠 썼기 때문이다. 마이그레이션 변경이
없으므로 `flask db heads` 는 이번에도 확인 대상이 아니다.

작업 트리는 clean 이고 `main`(`8ddc8fd`)이 `HEAD` 의 조상이다. 이 라운드의
커밋은 4개다 — 결함 수정(보드 폐기 + 계정 세대), 언어 경계 폐기, 조회 응답
경계 보강, 가드 주석 한 줄.

### 바뀐 파일 (이 라운드)

| 파일 | 무엇 |
|---|---|
| `mobile/lib/guest/account_epoch.dart` | **새 파일.** 계정 세대와 `sendIfSameAccount` — 하나의 장치 |
| `mobile/lib/guest/guest_token_provider.dart` | 토큰이 바뀌는 두 길에서 세대를 올린다(= 계정 경계의 정의) |
| `mobile/lib/puzzle/today_puzzle_controller.dart` | `discard()`·`discardTodayPuzzle(ref)`, 상태 타입 `TodayState?`, 제출을 가드로 감싸기, 경계를 넘은 조회 응답 폐기 |
| `mobile/lib/account/account_controller.dart` | `_adopt` 가 무효화 대신 보드를 폐기 |
| `mobile/lib/settings/puzzle_language_controller.dart` | 같은 폐기를 언어 경계에, `PATCH /me` 를 가드로 감싸기 |
| `mobile/test/...` (4개 파일) | 재현 테스트 6개, 하네스에 토큰 저장소 주입 자리 |
| `README.md` | 홈 보드 폐기와 계정 세대 문단, `_serverDeleted` → `_deletedToken` 명칭 정정 |
