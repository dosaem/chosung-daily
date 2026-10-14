# 티켓 29 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` (`34ec7ec`) 대비 `HEAD` (`d0d129f`), `git diff main...HEAD` 및 `git log main..HEAD`의 8개 커밋. `origin/main`은 사용하지 않았다.
- 대조: 티켓 29의 8개 체크박스, 스펙 §A.6·A.7·B.21 및 US 18·18a·19·20·21·22, CONTEXT, SCREENS S2·S4·T2·T4, 디자인 MASTER/OVERRIDES(OVERRIDES 우선), `e4_records.png`, 구현 증거 문서.
- 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다. 추가 재현은 `/tmp`의 독립 Flutter 하네스에서 실제 AccountNotifier/MyStatsNotifier와 기존 메모리 저장소를 실행했다. 외부 로그인·프로덕션 접근은 하지 않았다.

## 체크박스별 충족 여부

| # | 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | ApiClient token-exchange·DELETE /me, Dio + Fake | 충족 | `api_client.dart`, `dio_api_client.dart:145`, FakeApiClient 구현. Dio 테스트가 HTTP method/path/Bearer/body/Apple code 및 204를 검증한다. |
| 2 | Google 7.x authenticate, 플랫폼별 ID, Apple code, 성공 시 토큰 교체·재조회·로컬 상태 폐기 | 미충족 | SDK 호출·Info.plist/URL scheme·dart-define·entitlements·Apple code 전달은 구현됐다. 정상 전환 테스트도 통과하나, 새 토큰 적용 후 stats 재조회 실패 시 이전 신원·기록이 남는 D-29-1이 있다. 실제 네이티브 로그인 왕복은 미검증이다. |
| 3 | AccountCard 플랫폼별 버튼·연결 상태·provider 아이콘·마스킹·전환 안내·오류 문구 | 미충족 | iOS 두 버튼/Android Google만, 마스킹·전환 안내·두 오류 분기는 위젯 테스트로 확인했다. provider 아이콘 대신 공통 userCheck가 나오는 D-29-3이 남는다. |
| 4 | 백업 코드 Bearer GET /me/stats, 200 교체·폐기·재조회, 401 문구, Provider 교체 | 미충족 | 별도 서버 엔드포인트 없이 명시적 Bearer 조회, trim, 401 시 토큰 보존, secure storage 및 guestTokenProvider 교체를 확인했다. 첫 조회 200 후 후속 조회 실패를 성공 처리하면서 옛 계정 정보를 남기는 D-29-1 때문에 완전 충족은 아니다. |
| 5 | 첫 완료 후 연결 안내 1회·로컬 플래그 | 충족 | `result_sheet.dart:93`에서 연결 여부와 영속 플래그를 읽고 표시 시 기록한다. 1회 노출·기노출 생략·연결 계정 생략·내 기록 이동 테스트 통과. |
| 6 | destructive 삭제 확인·별도 구독 해지 문구·DELETE·로컬 삭제·새 게스트·온보딩 유지 | 미충족 | 확인/취소/정상 삭제는 동작하고 문구도 맞다. 기기 단위 키 보존은 테스트됐으나 실제 온보딩은 선행 구현 범위 밖이며 가짜 키로만 확인됐다. 삭제 성공 뒤 게스트 발급 실패 시 로컬 삭제와 재발급 재시도가 막히는 D-29-2가 있다. |
| 7 | 744 adaptive sheet/dialog 테스트 및 S4 열 유지 | 충족 | 두 진입점이 `showAdaptiveSheet` 사용. 744 Dialog/폭 제한 테스트와 기존 T4 열 배치 테스트, 1024 골든 통과. |
| 8 | 지정 위젯 테스트·audit.native·목업 대조 | 미충족 | 요구된 정상 경로/오류 코드/744 테스트 및 골든은 통과했다. 소스·골든으로 5축(접근성/성능/테마/플랫폼/적응성)을 점검했으나 D-29-1~2의 실패 경로가 빠져 있어 무조건 통과 판정을 뒷받침하지 못한다. provider 아이콘 요구도 미충족이다. |

## 결함

### D-29-1 — MAJOR — 전환 후 재조회 실패를 성공 처리하며 이전 계정 정보를 유지

- 위치: `mobile/lib/account/account_controller.dart:121` (특히 129), 관련 `mobile/lib/records/my_stats_controller.dart:30` 및 `mobile/lib/widgets/account_card.dart:27`.
- 재현: A 계정의 stats가 이미 로드된 상태에서 B의 유효한 백업 코드를 입력한다. 코드 확인용 `GET /me/stats`는 200으로 두고, 토큰 교체 후 실행되는 두 번째 stats 조회만 네트워크 오류로 실패시킨다. 실제 AccountNotifier를 사용하는 임시 테스트에서 이 순서를 실행했다.
- 기대: A의 신원·기록 사본을 버리고 B의 검증된 stats를 사용하거나, B stats를 다시 읽는 오류/재시도 상태를 표시한다. A의 신원을 B의 현재 계정으로 보여주면 안 된다.
- 실제: 저장소 토큰은 B로 바뀌고 `switched == true`, `error == null`이지만 `myStatsProvider`에는 A의 이메일과 streak(재현값 99)이 그대로 남는다. `refresh()`가 예외를 삼키고 기존 값을 유지하기 때문이다. 백업 코드 확인 응답도 버려지므로 이미 얻은 B의 stats가 사용되지 않는다. Google/Apple 전환 및 삭제 후 `_adopt`도 같은 경로다.
- 영향: 카드가 보여주는 계정과 이후 API가 조작하는 계정이 달라진다. 이 상태에서 삭제를 누르면 화면에 표시된 A가 아니라 B가 삭제될 수 있다. 기존 플레이 후 조용한 refresh 정책을 계정 경계 변경에 그대로 재사용한 문제다.
- 테스트 공백: 기존 테스트는 정상 stats 응답만 제공하고 재조회 횟수를 확인한다. 토큰 교체 후 stats 실패와 신원 일치 여부를 검증하지 않는다.

### D-29-2 — MAJOR — 삭제 성공 후 새 게스트 발급 실패 시 삭제된 토큰에 갇힘

- 위치: `mobile/lib/account/account_controller.dart:101` (107~111 순서), 관련 `mobile/test/account/account_controller_test.dart:304` 부근의 새 게스트 실패 테스트.
- 재현: `DELETE /me`를 204로 성공시킨 다음 `POST /guests`만 네트워크 오류로 실패시킨다. 네트워크를 복구하고 삭제를 다시 누른다. 두 번째 DELETE는 삭제된 게스트 인증이므로 401을 반환하도록 실제 서버 계약(`app/api/me.py:59`)을 재현했다.
- 기대: 서버 삭제 완료를 기억하고 옛 토큰/계정 상태를 폐기한 뒤, 앱 재시작 없이 새 게스트 발급을 재시도하여 정상 사용으로 복귀한다.
- 실제: 로컬 플래그 삭제와 `_adopt`에 도달하지 못한다. 재시도는 다시 DELETE부터 실행해 401로 끝나며, `createGuest` 호출 횟수는 최초 1회 그대로다. 죽은 토큰과 perAccount 플래그가 유지되고 삭제 위치에는 로그인 실패 문구가 나온다.
- 영향: 삭제 후 새 게스트로 돌아간다는 요구를 충족하지 못하며 홈·기록 요청도 죽은 인증을 계속 사용한다. 시작 흐름의 401 복구는 `startupProvider` 재실행 때만 가능하고, 현재 삭제 흐름에는 이를 호출하는 코드가 없다.
- 테스트 공백: 기존 “새 게스트 발급이 실패해도 앱이 토큰 없이 남지 않는다” 테스트는 토큰이 null이 아닌지만 검사한다. 서버가 이미 무효화한 토큰이라는 점, 네트워크 복구 후 재시도, 로컬 정보 삭제를 확인하지 않는다. 구현 증거의 “다음 시작” 설명은 현재 세션 복구를 증명하지 않는다. 또한 `StartupNotifier._ensureGuestToken`은 토큰이 없어도 새 게스트를 발급하므로 죽은 토큰 보존이 재시작 복구의 필수 조건도 아니다.

### D-29-3 — MINOR — 연결됨 카드에 요구된 provider 아이콘 없음

- 위치: `mobile/lib/widgets/account_card.dart:89`.
- 재현: `linkedAccount.provider`가 Google인 상태와 Apple인 상태로 AccountCard를 각각 렌더한다. `flutter test test/screens/records_account_test.dart`의 연결 상태 하네스와 `records_linked_390.png`에서도 Google 사례를 확인할 수 있다.
- 기대: 티켓 체크박스 3 및 SCREENS S4가 명시한 provider 아이콘 + 마스킹 이메일.
- 실제: provider와 무관하게 `LucideIcons.userCheck`만 표시한다. provider 이름 텍스트는 있어 기능 식별은 가능하므로 MINOR다.
- 근거: 구현 문서도 이탈을 인정하지만, OVERRIDES에는 provider 아이콘 요구를 취소하는 규정이 없다. Lucide에 브랜드 마크가 없다는 것은 요구 충족의 증거가 아니다. 취향 제안이 아니라 명시된 산출물 누락이다.

## 직접 실행한 검증

- `cd mobile && flutter test --reporter expanded`: **376 passed**, 종료 코드 0. 전체 화면·컨트롤러·Dio·744 태블릿·골든 테스트 포함.
- `cd mobile && flutter analyze`: **No issues found**, 종료 코드 0.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **114 files, 0 changed**, 종료 코드 0.
- `uv run ruff check .`: **All checks passed**, 종료 코드 0.
- `git diff --check main...HEAD`: 오류 없음.
- 임시 재현: `cd mobile && flutter test /tmp/t29_review_probe_test.dart --name 'successful backup|delete retry' --reporter expanded` — D-29-1·2의 **현재 잘못된 상태를 관찰하는 단언 2개 통과**. 제품이 올바르다는 통과가 아니다. 기존 FakeApiClient/메모리 저장소와 실제 AccountNotifier·MyStatsNotifier를 사용했고, D-29-2에서만 DELETE 성공 이후의 401 계약을 가진 Fake 하위 클래스를 사용했다.
- `uv run pytest -q`: **1403 passed in 880.19s (0:14:40)**, 종료 코드 0. `TEST_DATABASE_URL`은 기존 `chosung_daily_test_t29`, `TEST_REDIS_URL`은 로컬 Redis DB 3으로 지정했다. 마이그레이션 테스트는 구현 증거에 기재된 기존 `chosung_daily_test_t29_migrations`를 `TEST_MIGRATION_DATABASE_URL`로 지정했다. 새 DB 생성·기본 DB 폴백·간헐 실패 재실행은 없었다. 접속 자격 증명은 기록하지 않는다.
- 마이그레이션 변경 없음(`git diff --name-only main...HEAD`). 따라서 조건부 `flask db heads` 확인 대상이 아니다.

## 범위·보안·디자인 확인 및 참고

- 백엔드·웹·마이그레이션 변경 없음. README는 설계 판단 `### 29.`, RELEASE는 `### 29.`만 추가했다. `.env.example` 및 스펙 변경 없음. 병렬 티켓 공유 파일 규칙 위반을 찾지 못했다.
- 모바일 API는 현재 토큰을 Bearer로 보내며, 백업 코드는 검증 성공 전 저장하지 않는다. INVALID_ID_TOKEN을 게스트 인증 만료와 구별한다. 앱 DELETE에는 Bearer 인증이 적용되고 웹 CSRF 처리 변경은 없다.
- diff의 네이티브 설정은 변수 참조/빈 예시이고 실제 OAuth 비밀값·실서비스 토큰을 새로 기록한 흔적을 찾지 못했다. 구현 증거의 로컬 테스트 접속 문자열은 예제 개발 자원이다. 본 문서에는 비밀번호·키·토큰 값을 재기록하지 않았다.
- `e4_records` 목업과 연결됨 골든을 직접 열어 계정 블록의 글자 구성·마스킹·헤어라인을 대조했다. T4 열 배치도 유지된다. 외곽선 연결 버튼, 가운데 destructive 텍스트 버튼, 설명 줄을 전환 안내로 바꾸는 선택은 결함으로 세지 않았다.
- `audit.native`는 독립 CLI 성공 로그가 아니라 구현 문서의 수동 체크리스트다. 이번 리뷰도 접근성(제목 semantics·텍스트 오류·터치 크기), 성능(중복 조회 범위), 테마(색 토큰), 플랫폼별 버튼/시트, 폭 적응성을 소스 및 위젯/골든 테스트로 확인했다. 실기기 VoiceOver/TalkBack·실제 OAuth 왕복·스토어 심사 준수까지 검증했다고 주장하지 않는다.
- 공식 로그인 버튼 에셋과 콘솔 등록/실기기 확인은 RELEASE에 미완 항목으로 남아 있다. 여기서는 확인하지 않은 외부 브랜드 정책을 별도 결함으로 단정하지 않았다.

결함 합계: BLOCKER 0 / MAJOR 2 / MINOR 1.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` = `34ec7ec`, 구현 `HEAD` = `eae4127`. `git log main..HEAD`의 12개 커밋과 `git diff main...HEAD`를 확인했다. 라운드 1 이후 수정은 `adf8f76`, 정리는 `85dd0b6`, 증거 갱신은 `eae4127`이다.
- 티켓 29, 스펙 §A.6·A.7·B.21 및 US 18·18a·19·20·21·22, CONTEXT, SCREENS S2·S4·T2·T4, MASTER 및 우선 규칙 OVERRIDES를 대조했다. 구현 증거의 성공 주장을 그대로 채택하지 않고 아래 명령을 직접 실행했다.
- 작업 범위: 이 리뷰 문서만 변경한다. 추가 재현 파일은 `/tmp`에 두고 실제 앱의 AccountNotifier·RecordsTab·시트를 import했다. 저장소·API 경계는 기존 메모리 Fake를 사용했고 프로덕션·외부 OAuth 서비스에는 접근하지 않았다.

### 체크박스별 충족 여부

| # | 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | ApiClient token-exchange·DELETE /me(Dio + Fake) | 충족 | `dio_api_client.dart:145` 이하 및 Dio 테스트에서 method/path/Bearer/body/Apple authorization_code, 본문 없는 204를 검증한다. |
| 2 | Google 7.x authenticate·플랫폼별 ID·Apple code·성공 시 토큰 교체와 재조회 | 충족 | `social_sign_in.dart`의 authenticate/Apple code 전달, Info.plist·xcconfig·entitlements·dart-define 연결을 확인했다. 컨트롤러/화면 테스트로 교환 후 토큰·홈·기록 변경과 재조회 실패 시 옛 신원 폐기를 확인했다. 실제 OAuth 왕복은 별도 출시 검증이다. |
| 3 | 플랫폼별 AccountCard·provider 아이콘·마스킹·전환 안내·오류 문구 | 충족 | iOS 2개/Android Google만 노출, provider별 chrome/apple 아이콘, 마스킹, 전환 안내, 두 서버 오류별 문구를 위젯 테스트로 확인했다. 연결됨 골든과 e4_records 목업도 직접 열어 대조했다. |
| 4 | 백업 코드 GET /me/stats Bearer, 200 교체·상태 폐기·재조회, 401 문구·Provider 교체 | 충족 | 검증 응답을 새 stats로 채택하고 저장소/guestTokenProvider를 교체한다. 홈·history·leaderboard를 무효화한다. 401은 기존 토큰을 보존한다. 이미 받은 stats를 재사용하는 것은 동일 응답을 한 번 더 요청하지 않는 구현이며 요구한 기록 갱신은 충족한다. 단, 이 경로 뒤 삭제 상태가 잘못 이어지는 D-29-4는 #6 결함이다. |
| 5 | 첫 완료 연결 안내 1회·로컬 플래그 | 충족 | `result_sheet.dart:93`의 연결 여부·영속 플래그 확인과 1회 표시, 이미 본 경우/연결된 계정 생략, 내 기록 이동 테스트 통과. |
| 6 | destructive 확인·구독 별도 해지 문구·서버/로컬 삭제·새 게스트·온보딩 유지 | 미충족 | 정상 삭제와 같은 계정의 실패 후 재시도는 통과한다. 그러나 삭제 후 발급 실패 → 다른 계정 복원 → 삭제에서 새 계정의 DELETE를 생략하고 성공 안내를 띄운다(D-29-4). 기기 단위 플래그 보존은 확인했지만 실제 온보딩 구현과의 통합은 이 브랜치 범위 밖이다. |
| 7 | 폭 744 adaptive sheet/dialog·S4 열 유지 | 충족 | 744 Dialog/최대 폭 테스트, 기존 T4 배치 테스트 및 1024 골든 통과. 두 진입점 모두 showAdaptiveSheet를 사용한다. |
| 8 | 지정 위젯 테스트·audit.native·목업 대조 | 미충족 | 요구한 기본 위젯 테스트와 골든은 실행해 통과했다. 다만 삭제 복구 중 계정 전환 시나리오가 빠져 D-29-4를 잡지 못한다. audit.native는 아래 제한 범위의 소스·위젯·골든 검토이며 무조건 통과로 볼 수 없다. |

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 근거 |
|---|---|---|---|
| D-29-1 | MAJOR | FIXED | `_adopt`가 `refresh()` 대신 `adopt(stats)`를 사용한다. 백업 코드 확인 응답의 B stats를 즉시 채택하고, 소셜 전환 후 조회 실패에서는 `AsyncData(null)`로 A 신원을 제거하면서 오류를 노출한다. 해당 컨트롤러·위젯 회귀 테스트를 직접 실행해 통과했다. |
| D-29-2 | MAJOR | FIXED | 서버 삭제 직후 플래그와 stats를 버리며, 새 게스트 발급 실패 후 **같은 삭제 작업을 재시도**하면 DELETE를 반복하지 않고 발급부터 재개한다. 두 번째 DELETE를 401로 설정한 컨트롤러·위젯 테스트가 통과했다. 새로 도입한 복구 상태의 계정 간 누수는 별도 D-29-4로 기록한다. |
| D-29-3 | MINOR | FIXED | `providerIcon`이 Google/Apple을 chrome/apple로 구분한다. 각 아이콘 및 알 수 없는 provider fallback 테스트와 변경 골든이 통과했다. |

### 신규 결함

#### D-29-4 — MAJOR — 이전 계정의 삭제 완료 플래그가 복원된 계정의 서버 삭제를 생략시킴

- 위치: `mobile/lib/account/account_controller.dart:110` (`_serverDeleted` 분기), `mobile/lib/account/account_controller.dart:101` 및 `:143` (백업 복원/adopt에서 플래그를 초기화하거나 계정에 귀속시키지 않음). 성공 안내는 `mobile/lib/screens/records_tab.dart:474`의 error 유무 판정으로 표시된다.
- 재현 입력: A 계정에서 삭제 확인 → `DELETE /me`는 성공시키고 뒤의 `POST /guests`만 네트워크 오류로 실패시킨다 → 네트워크를 복구한다 → “다른 기기 기록 불러오기”에서 유효한 B 계정 백업 코드를 입력한다 → B의 연결 상태가 표시되는 것을 확인한다 → 다시 계정 삭제를 확인한다.
- 기대: B의 Bearer로 `DELETE /me`를 호출해 B 계정과 기록을 삭제한 뒤 새 게스트로 전환한다. 전체 흐름의 DELETE 호출은 A와 B 각각 1회, 합계 2회여야 한다.
- 실제: A 삭제 후 남은 `_serverDeleted == true`가 백업 복원 후에도 유지된다. 두 번째 삭제는 110행의 블록 전체를 건너뛰어 B 삭제 및 로컬 플래그 정리를 생략하고 새 게스트만 발급한다. 오류는 null이며 화면에 “계정을 삭제하고 새로 시작했어요”가 표시된다. 서버의 B 계정과 기록은 삭제 요청조차 받지 않는다.
- 직접 검증: `/tmp/t29_r2_probe_test.dart`의 실제 AccountNotifier 재현과 `/tmp/t29_r2_widget_probe_test.dart`의 실제 RecordsTab/백업 시트/삭제 확인 위젯 재현에서 모두 `Expected: <2>, Actual: <1>`로 실패했다. 위젯 재현은 B의 연결됨 문구와 최종 삭제 성공 문구를 각각 먼저 단언한 뒤 DELETE 횟수를 검사했다. 실행 명령: `cd mobile && flutter test /tmp/t29_r2_widget_probe_test.dart --plain-name 'review r2:' --reporter expanded`.
- 독립 재현의 핵심 순서(기존 FakeApiClient와 메모리 저장소, 실제 AccountNotifier 사용): `createGuestError = NetworkApiException` → `deleteAccount()` → 발급 오류 해제 → `restoreWithBackupCode(B)` → B 토큰·stats 확인 → `deleteAccount()` → `deleteAccountCalls == 2` 단언. B는 Fake의 `statsByToken`에 미리 등록한다. 실제 계정 정보는 필요하지 않다.
- 영향: 계정 삭제가 완료됐다는 잘못된 안내로 사용자의 데이터 삭제 요구가 이행되지 않는다. D-29-2 원래 재현은 고쳤으나 복구 상태가 삭제 대상과 연결되지 않은 회귀다. 기존 테스트는 같은 계정 삭제의 연속 재시도만 확인해 이 상태 전이를 놓친다.

### 직접 실행한 검증

- `cd mobile && flutter test`: **385 passed**, 약 19초, All tests passed. 로그 `/tmp/t29-review-flutter.log`.
- `cd mobile && flutter analyze`: **No issues found**, 종료 코드 0.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **114 files, 0 changed**, 종료 코드 0.
- `uv run ruff check .`: **All checks passed**, 종료 코드 0.
- `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`을 지정한 `uv run pytest -q`: **1403 passed in 877.62s (0:14:37)**, 종료 코드 0. 기존 `chosung_daily_test_t29`, Redis DB 3 및 `chosung_daily_test_t29_migrations`를 사용했다. 새 DB 생성·기본 DB 대체·간헐 실패 재실행은 없었다. 접속 문자열 형식은 구현 증거 문서와 `.env.example`를 따랐으며 비밀번호는 여기 기록하지 않는다. 로그 `/tmp/t29-review-pytest.log`.
- 추가 회귀 하네스 2건: 각각 **1 failed**, 동일한 D-29-4를 컨트롤러와 실제 화면에서 독립 확인했다. 저장소 내 테스트는 수정하지 않았다.
- `git diff --name-only main...HEAD`에 마이그레이션 변경이 없으므로 이번 티켓에 `flask db heads` 요구는 적용되지 않는다.

### 보안·범위·디자인 및 검증 한계

- Bearer 인증, 백업 코드 검증 전 저장 금지, INVALID_ID_TOKEN 분리, 빈 입력 처리, Apple code 전송을 확인했다. 웹 CSRF 처리를 건드리지 않는다. 이번 신규 결함은 인증 우회가 아니라 삭제 요청 생략 및 잘못된 성공 안내다.
- 공유 문서 README/RELEASE는 자기 `### 29.` 절만 추가했고 `.env.example`·스펙에는 diff가 없다. 변경된 퍼즐 언어 provider는 계정 전환 후 언어 갱신에 필요한 범위다. 다른 티켓 공유 절 변경이나 무관한 기능 추가를 찾지 못했다.
- 설정 diff는 변수 참조·빈 예시이며 실제 OAuth 비밀값·실서비스 토큰을 새로 커밋한 흔적을 찾지 못했다. 증거 문서의 로컬 개발 DB 예제 접속정보는 리뷰에 재기록하지 않는다.
- e4_records 목업과 연결됨 골든을 직접 열어 마스킹 이메일·연결 상태·헤어라인을 확인했다. OVERRIDES 우선 토큰, 플랫폼별 버튼, 시트 semantics, 744/1024 적응성 및 기존 열 배치를 검토했다. audit.native는 별도 실행 도구의 성공 로그가 아니라 수동 검토다. 실기기 접근성·네이티브 빌드·실제 OAuth 왕복·공식 버튼 브랜드 정책 준수는 확인하지 않았다.
- 참고: 공식 로그인 버튼 에셋과 콘솔 등록/실기기 확인은 RELEASE에 출시 전 작업으로 남아 있다. 취향·스타일 제안은 결함으로 세지 않았다.

라운드 2 잔여 결함 합계: BLOCKER 0 / MAJOR 1 / MINOR 0. 이전 결함 FIXED 3 / REPEAT 0, 신규 D-29-4 1건.

판정: FAIL
