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


## 라운드 3

- 기준: 로컬 `main` = `8ddc8fd`, 구현 `HEAD` = `4fb8a8d`. `git diff main...HEAD`와 `git log main..HEAD`의 17개 커밋을 직접 확인했다. `origin/main`은 사용하지 않았다.
- 대조: 티켓 29의 8개 체크박스, 스펙 §A.6·A.7·B.21 및 US 18·18a·19·20·21·22, CONTEXT, SCREENS S2·S4·T2·T4, MASTER와 우선 규칙 OVERRIDES, e4_records 목업 및 현재 연결됨 골든, 구현 증거의 수정 라운드 2.
- 앱·테스트·설정·`.scratch/`는 수정하지 않았다. 추가 재현은 `/tmp`의 독립 하네스에서 실제 AccountNotifier·TodayPuzzleNotifier·TodayTab을 실행했다. 기존 FakeApiClient 및 메모리 저장소만 경계로 사용했으며 외부 OAuth·프로덕션에 접근하지 않았다.

### 체크박스별 충족 여부

| # | 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | ApiClient token-exchange·DELETE /me(Dio + Fake) | 충족 | Dio의 method/path/Bearer/body/Apple authorization_code 및 본문 없는 204 테스트 통과. 백업 코드는 별도 Bearer 조회다. |
| 2 | Google 7.x authenticate·플랫폼별 ID·Apple code·성공 시 토큰 교체·홈/기록 재조회·로컬 상태 폐기 | 미충족 | SDK 호출과 설정 연결, Apple code 전달, 토큰 저장 및 stats 교체는 확인했다. 그러나 홈 provider 무효화가 옛 보드를 폐기하지 않아 새 계정 토큰으로 옛 보드에서 제출할 수 있다(D-29-5). |
| 3 | 플랫폼별 AccountCard·provider 표시·마스킹·전환 안내·오류 문구 | 충족 | iOS 2개/Android Google만 노출, 이메일 마스킹, 전환 안내, ACCOUNT_ALREADY_LINKED/INVALID_ID_TOKEN 문구 테스트 통과. Google 중립 아이콘 보정은 아래 D-29-3 판정 및 참고 참조. |
| 4 | 백업 코드 Bearer GET /me/stats, 200 토큰/Provider 교체·상태 폐기·재조회, 401 문구 | 미충족 | 검증 전 저장 금지, 401 기존 토큰 보존, 검증 응답의 새 stats 채택은 충족. 성공한 전환 뒤 홈에 이전 계정 보드가 남는 D-29-5 때문에 로컬 상태 폐기 요구는 미충족이다. 서버 엔드포인트 추가는 없다. |
| 5 | 첫 완료 연결 안내 1회·로컬 플래그 | 충족 | result_sheet의 연결 여부 확인과 영속 플래그, 기노출/연결 계정 생략, 내 기록 이동 테스트 통과. |
| 6 | destructive 확인·구독 별도 해지 문구·DELETE·로컬 삭제·새 게스트·온보딩 유지 | 미충족 | 정상 삭제, 발급 실패 재시도, 복구 중 다른 계정 삭제 회귀는 통과. 실제 온보딩은 별도 SharedPreferences 저장소이며 삭제가 이 키를 지우지 않는다. 다만 새 게스트 채택 역시 D-29-5의 같은 _adopt 경로여서 이전 보드의 즉시 폐기는 충족하지 못한다. |
| 7 | 744 adaptive sheet/dialog 및 S4 열 유지 | 충족 | 두 진입점이 showAdaptiveSheet 사용. 744 위젯 테스트, 1024 골든 및 기존 열 배치 테스트 통과. |
| 8 | 지정 위젯 테스트·audit.native·목업 대조 | 미충족 | 기존 Flutter 449개와 골든은 통과했고 소스/골든으로 접근성·테마·플랫폼·폭 적응성을 확인했다. 새 계정 홈 응답 지연 중 제출 시나리오를 기존 테스트가 검증하지 못한다(D-29-5). |

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| D-29-1 | MAJOR | FIXED | MyStatsNotifier.adopt/discard가 옛 신원·streak를 AsyncData(null)로 지우고 새 stats를 채택한다. stats 실패 시 옛 신원 제거와 오류 표시 회귀 테스트 통과. 홈 보드의 별도 잔존은 신규 D-29-5로 분리한다. |
| D-29-2 | MAJOR | FIXED | 같은 삭제 토큰의 재시도는 DELETE를 반복하지 않고 발급을 재시도한다. 발급 실패 직후 perAccount 플래그와 stats 폐기, 재시도 성공 테스트가 통과했다. |
| D-29-3 | MINOR | FIXED | Google chrome 오용을 제거하고 중립 userCheck + Google 텍스트를 사용한다. 이는 orchestration ask로 코디네이터에게 직접 확인한 명시적 수용 기준 보정이다(응답: “허용된 보정으로 보고 D-29-3 은 FIXED 처리해라”). 중립 아이콘·텍스트·chrome 부재 및 Apple 분기 위젯 테스트 통과. 공식 브랜드 에셋 완료를 의미하지 않는다. |
| D-29-4 | MAJOR | FIXED | account_controller.dart:119에서 현재 토큰과 _deletedToken을 비교한다. A 삭제/발급 실패 → B 복원 → B 삭제 및 다른 경로의 토큰 교체 후 삭제에서 DELETE 2회를 확인하는 테스트와 실제 RecordsTab 회귀 테스트가 모두 통과했다. |

### 신규 결함

#### D-29-5 — MAJOR — 계정 전환 후 홈 재조회 중 이전 계정 보드에서 새 계정에 답을 제출할 수 있음

- 위치: `mobile/lib/account/account_controller.dart:155`(계정 경계에서 invalidate만 수행). 관련 소비자: `mobile/lib/screens/today_tab.dart:102`, `mobile/lib/screens/today_tab.dart:182`, `mobile/lib/puzzle/today_puzzle_controller.dart:81`.
- 요구 근거: 티켓 체크박스 2·4의 “로컬 상태 폐기”, 스펙 §A.2의 “언어 변경·계정 전환 시 로컬 상태 폐기” 및 서버 이력으로 보드 복원. 계정 경계에서도 같은 계정의 일시적 새로고침처럼 옛 보드를 유지하면 안 된다.
- 재현 입력: A의 진행 중인 오늘 보드를 한 번 로드한다 → B의 유효한 백업 코드를 복원한다(GET /me/stats 200) → B의 GET /puzzles/today 응답만 지연시킨다 → 홈에서 길이가 맞는 답을 입력하고 “제출”을 누른다. 같은 날짜·언어라 A와 B의 puzzle_id가 같아도 각 게스트의 시도 이력은 다를 수 있다.
- 기대: B의 서버 이력을 읽기 전에는 A 보드·시도·힌트를 폐기하고 입력을 막는다. 이전 보드에 근거한 submitGuess 호출은 0회여야 한다.
- 실제: 토큰은 B이고 stats도 B로 바뀌었으며 계정 작업은 성공 상태다. 그러나 todayPuzzleProvider는 isLoading == true이면서 value에 A의 TodayPuzzleReady를 보존한다. TodayTab은 이 value 분기를 우선 선택하고, 오류도 제출 중 상태도 없어서 입력과 제출 버튼이 활성화된다. 실제 버튼을 누르면 submitGuess가 1회 호출된다. DioApiClient는 매 요청 현재 토큰을 읽으므로 실제 요청은 B의 Bearer로 전송된다.
- 원인: Riverpod의 invalidate는 이전 AsyncValue의 값을 지우는 API가 아니다. stats에는 이를 고려한 discard를 도입했지만 홈에는 같은 계정 경계 처리가 없다. submit 또한 state.value만 보고 계정 변경 후 재조회 중인지 검사하지 않는다. 기존 TodayTab의 “같은 계정 재조회 시 보드 유지” 동작이 이번 전환 경로와 결합해 발생한다.
- 영향: 화면의 시도/힌트/남은 기회와 쓰기 대상 계정이 달라진다. A·B가 같은 날 같은 언어의 퍼즐을 풀면 puzzle_id 검증으로도 이 불일치를 막지 못하며, B의 시도를 이전 보드 상태에서 소비할 수 있다. 소셜 전환과 삭제 후 새 게스트 채택도 동일 _adopt 경로를 사용한다.
- 직접 검증 1: `cd mobile && flutter test /tmp/t29_r3_probe_test.dart --reporter expanded` → **1 failed**, `Expected: <0>, Actual: <1>`. 실제 AccountNotifier·TodayPuzzleNotifier를 실행했고 B 토큰/B stats, 홈 isLoading, 옛 보드 객체 유지 단언이 모두 통과한 뒤 제출 횟수 단언이 실패했다.
- 직접 검증 2: `cd mobile && flutter test /tmp/t29_r3_widget_probe_test.dart --reporter expanded` → **1 failed**, 동일 `Expected: <0>, Actual: <1>`. 실제 TodayTab에서 TextField 입력과 FilledButton 탭으로 실행했다. “onPressed != null” 확인 후 호출 횟수를 검사했으므로 컨트롤러를 UI 밖에서 억지로 호출한 결과가 아니다.
- 독립 하네스 구성: 기존 `mobile/test/account/account_controller_test.dart`의 `_container` 또는 `mobile/test/screens/today_tab_test.dart`의 `_pumpToday`를 `/tmp`로 복사해 import를 절대 경로로 바꾼다. 실제 provider는 override하지 않고 Fake API·메모리 저장소·startup snapshot만 주입한다. 첫 보드를 읽은 다음 `api.fetchTodayPuzzleGate = Completer<void>()`로 새 조회를 지연시키고, `statsByToken`에 등록한 합성 B 코드로 restoreWithBackupCode를 실행한다. 새 토큰과 isLoading을 확인한 뒤 길이가 맞는 답을 제출하고 `api.submittedGuesses.length == 0`을 단언한다. API 게이트는 tearDown에서 해제한다. 실제 계정·키·토큰은 필요 없다.
- 기존 테스트 공백: 전환 테스트는 Fake의 홈 조회가 즉시 끝나는 조건에서 재조회 횟수와 최종 stats를 확인한다. 성공한 계정 전환과 아직 끝나지 않은 홈 조회 사이의 UI/제출 계약을 확인하지 않는다.

### 직접 실행한 검증

- `cd mobile && flutter test`: **449 passed**, 약 21초, 종료 코드 0. 로그 `/tmp/t29-r3-flutter.log`.
- `cd mobile && flutter analyze`: **No issues found**, 종료 코드 0.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **132 files, 0 changed**, 종료 코드 0.
- `uv run ruff check .`: **All checks passed**, 종료 코드 0.
- `git diff --check main...HEAD`: 오류 없음.
- 코디네이터 추가 지시의 `cd mobile && flutter build apk --debug`: **성공**, `Built build/app/outputs/flutter-apk/app-debug.apk`, 136.5초, 종료 코드 0. 로그 `/tmp/t29-r3-apk.log`. 완료 후 요청대로 이 worktree의 `mobile/build`를 삭제했다.
- D-29-5 독립 컨트롤러·실제 화면 하네스: 각각 **1 failed**. 위 결함의 직접 재현이며 기존 저장소 테스트는 수정하지 않았다.
- `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`을 지정한 `uv run pytest -q`: **1403 passed in 1363.35s (0:22:43)**, 종료 코드 0. 기존 `chosung_daily_test_t29`, Redis DB 3 및 `chosung_daily_test_t29_migrations`를 재사용했다. 새 DB 생성·기본 DB 대체·간헐 실패 재실행은 없었다. 접속 형식은 구현 증거와 `.env.example`를 따랐고 자격 증명은 기록하지 않는다. 로그 `/tmp/t29-r3-pytest.log`.
- 마이그레이션 diff가 없으므로 조건부 `flask db heads` 확인 대상이 아니다.

### 보안·범위·디자인 및 참고

- API의 Bearer 인증과 204 처리, 백업 코드 검증 전 저장 금지·공백 입력 처리, INVALID_ID_TOKEN 분리, Apple authorization_code 동봉을 확인했다. 웹 인증·CSRF·백엔드 처리를 바꾸지 않았다. D-29-5는 인증 우회가 아니라 화면 상태와 현재 인증 주체가 일치하지 않는 문제다.
- README/RELEASE는 자기 `### 29.` 절만 추가한다. `.env.example`·스펙·마이그레이션·백엔드에는 변경이 없다. 계정 전환 시 설정 언어를 새 stats에 맞추는 변경과 티켓 28 온보딩 병합은 이 범위에 필요한 통합이다. 다른 티켓 공유 절 위반·불필요한 기능 추가를 찾지 못했다.
- 네이티브 설정은 변수 참조와 빈 예시이고 실제 OAuth 키·실서비스 토큰을 커밋한 흔적을 찾지 못했다. 구현 증거의 로컬 테스트용 예제 접속 문자열은 본 리뷰에 재기록하지 않았다.
- e4_records 목업과 records_linked_390 골든을 직접 열어 계정 줄·마스킹·헤어라인을 대조했다. OVERRIDES 우선 색 토큰, 텍스트 오류, 제목 semantics, 플랫폼별 노출, 744 다이얼로그 및 1024 열 배치를 확인했다. audit.native는 독립 CLI의 실행 결과가 아니라 이 범위의 소스·위젯·골든 검토다.
- Android debug 빌드는 확인했지만 iOS 네이티브 빌드·실기기 VoiceOver/TalkBack·실제 OAuth 왕복은 실행하지 않았다. 공식 Google/Apple 로그인 버튼 에셋 및 콘솔 등록은 코디네이터가 별도 RELEASE 사람 확인 항목으로 유지한다고 확인했다. 티켓 코드 통과나 debug 빌드 성공을 출시 준비 완료로 해석하지 않는다.
- 참고: README의 `_serverDeleted` 명칭과 구현 증거 앞부분의 백업 stats 2회 호출 설명은 후속 수정 전 설명이다. 현재 코드는 `_deletedToken`을 비교하고 백업 검증 stats를 재사용한다. 이 문서 잔여 설명을 별도의 기능 결함이나 취향·스타일 결함으로 세지 않았다.

라운드 3 잔여 결함 합계: BLOCKER 0 / MAJOR 1 / MINOR 0. 이전 결함 FIXED 4 / REPEAT 0, 신규 D-29-5 1건.

판정: FAIL

## 라운드 4

- 기준: 로컬 `main` = `b11f011`, 구현 `HEAD` = `e9dbd89`. `git diff main...HEAD`와 `git log main..HEAD`를 직접 확인했다. `origin/main`은 사용하지 않았다.
- 대조 문서: 티켓 29의 체크박스 8개, 스펙 §A.2·A.6·A.7·B.21 및 US 18·18a·19·20·21·22, CONTEXT, SCREENS S2·S4·T2·T4, 디자인 MASTER/OVERRIDES(OVERRIDES 우선), 구현 증거 및 이전 리뷰 3개 라운드.
- 리뷰 문서만 수정했다. 독립 재현 하네스는 `/tmp`에 만들었고 실제 AccountNotifier·TodayPuzzleNotifier·TodayTab을 사용했다. API·저장소만 기존 Fake로 대체했다. 프로덕션·외부 OAuth 서비스 접근, 실제 계정 입력, 새 DB 생성은 하지 않았다.

### 체크박스별 충족 여부

| # | 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | ApiClient token-exchange·DELETE /me(Dio + Fake) | 충족 | `dio_api_client.dart:145` 이하와 Dio 테스트에서 HTTP method/path/Bearer/body, Apple authorization_code, 본문 없는 204를 검증한다. |
| 2 | Google 7.x authenticate·플랫폼별 ID·Apple code·토큰 교체·홈/기록 재조회·로컬 폐기 | 미충족 | SDK 호출, Info.plist의 GIDClientID/URL scheme, dart-define, entitlements, 토큰 저장·stats 채택은 확인했다. 그러나 전환 전의 최초 홈 조회가 늦게 끝나면 새 계정의 정상 보드가 사라지는 D-29-6이 있다. |
| 3 | 플랫폼별 AccountCard·연결 표시·마스킹·전환 안내·오류 문구 | 충족 | iOS 2개/Android Google만 노출, Google 중립 아이콘+이름 및 Apple 분기, 마스킹, 두 오류 문구와 전환 안내를 실제 위젯 테스트로 확인했다. D-29-3의 기존 코디네이터 수용 기준 보정을 유지한다. |
| 4 | 백업 코드 Bearer GET /me/stats·200 교체/폐기/재조회·401 문구·Provider 교체 | 미충족 | 별도 엔드포인트 없이 코드 확인 응답의 stats를 채택하고 secure storage/guestTokenProvider를 교체한다. 401 시 기존 토큰 보존과 문구는 통과한다. 최초 홈 조회와 겹치는 전환에서 D-29-6이 재현된다. |
| 5 | 첫 완료 후 연결 안내 1회·로컬 플래그 | 충족 | `result_sheet.dart:93` 이하와 테스트에서 미연결/미노출 조건, 영속 플래그, 닫기, 내 기록 이동, 기연결/기노출 생략을 검증한다. |
| 6 | destructive 삭제 확인·구독 별도 해지 문구·DELETE·로컬 정리·새 게스트·온보딩 유지 | 미충족 | 정상 삭제·발급 실패 재시도·복원한 다른 계정의 실제 DELETE, perAccount 플래그 삭제와 기기 플래그 보존은 통과한다. 다만 새 게스트 채택도 동일 `_adopt`를 사용하므로 최초 홈 조회가 겹치면 D-29-6 경합을 공유한다. |
| 7 | 폭 744 adaptive sheet/dialog·S4 열 유지 | 충족 | 두 진입점 모두 showAdaptiveSheet 사용. 744 Dialog/폭 제한 위젯 테스트와 1024 골든 통과. AccountCard는 T4 왼쪽 열을 유지한다. |
| 8 | 지정 위젯 테스트·audit.native·목업 대조 | 미충족 | 저장소의 Flutter 537개는 통과했고 390/744/1024 및 플랫폼별 위젯·골든을 확인했다. 그러나 최초 A 조회 → B 보드 완료 → A 조회 완료 순서를 검증하지 않아 D-29-6을 놓친다. 수동 audit 범위는 아래에 명시했다. |

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 직접 확인한 근거 |
|---|---|---|---|
| D-29-1 | MAJOR | FIXED | `MyStatsNotifier.adopt/discard`가 기존 신원을 비우고 백업 확인 stats를 채택한다. 소셜 전환 뒤 stats 실패 시 옛 이메일·streak가 사라지고 오류가 표시되는 컨트롤러/위젯 테스트 통과. |
| D-29-2 | MAJOR | FIXED | 삭제 완료 토큰을 기억하고 같은 토큰의 재시도는 새 게스트 발급부터 시작한다. 삭제 후 발급 실패 → 네트워크 복구 테스트에서 DELETE 1회/발급 2회와 로컬 플래그·stats 폐기를 검증한다. |
| D-29-3 | MINOR | FIXED | 이전 라운드에 기록된 코디네이터의 명시적 보정(Google 중립 아이콘+텍스트 허용)을 적용했다. userCheck+Google 라벨, chrome 부재, Apple 분기 위젯 테스트 및 연결됨 골든 확인. |
| D-29-4 | MAJOR | FIXED | `_deletedToken`과 현재 토큰을 비교한다. A 삭제/발급 실패 → B 백업 복원 → B 삭제에서 DELETE 2회를 컨트롤러와 실제 RecordsTab 테스트로 확인했다. |
| D-29-5 | MAJOR | FIXED | `_adopt`가 홈을 invalidate하는 대신 `discardTodayPuzzle`로 비운다. B 홈 응답을 지연한 상태에서 옛 PuzzleBoard/GuessInput 부재, 제출 API 0회, B 보드 도착 후 제출 재개를 테스트한다. 토큰 세대 가드도 추가됐다. 원래의 '전환 후 홈 재조회 중 옛 보드에서 새 계정에 제출' 재현은 해결됐으며, 최초 조회 완료 순서의 새 문제는 아래 D-29-6으로 구분한다. |

### 신규 결함

#### D-29-6 — MAJOR — 늦은 최초 조회가 이미 로드된 새 계정 보드를 지워 홈이 스켈레톤에 머묾

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:72`. 관련: 같은 파일 `:57`의 `build()` 반환 Future, `:96`의 `discard()`, `mobile/lib/account/account_controller.dart:158`의 전환 후 보드 폐기, `mobile/lib/screens/today_tab.dart:120`의 스켈레톤 분기.
- 재현 입력: A 계정으로 앱을 열고 최초 `GET /puzzles/today` 응답을 지연시킨다 → 홈 조회가 아직 진행 중인 채 내 기록 탭에서 B의 유효한 백업 코드로 전환한다 → B의 stats와 홈 조회는 먼저 200으로 완료시켜 B 보드가 표시되게 한다 → 마지막으로 A의 최초 홈 조회 응답을 완료한다. 셸이 탭을 유지하므로 내 기록으로 이동해도 최초 홈 조회는 계속 살아 있다(`app_router.dart:64`). 소셜 전환과 삭제 후 새 게스트도 같은 `_adopt` 경로다.
- 기대: 계정 경계를 넘은 A 응답은 현재 상태에 아무 영향도 주지 않아야 한다. 이미 받은 B 보드·입력창을 유지하고 플레이할 수 있어야 한다.
- 실제: B 보드가 한 번 정상 표시된 뒤 A 응답이 도착하면 `todayPuzzleProvider`가 `AsyncData(null)`로 바뀐다. 실제 TodayTab에서 PuzzleBoard는 1개에서 0개로 사라지고 스켈레톤만 남는다. 진행 중인 새 조회도 오류/재시도 버튼도 없어 탭 왕복만으로는 복구되지 않는다. 앱 포그라운드 복귀 등의 별도 refresh가 필요하다.
- 원인: `_load()`는 계정이 바뀐 응답에 `null`을 반환한다. 그러나 최초 `build()`가 반환한 Future는 `_commitLoad`의 `_generation` 검사를 거치지 않고 Riverpod이 직접 상태에 쓴다. `discard()`는 새 조회와 상태 교체를 수행하지만 기존 build Future를 무효화하지 않아, '옛 응답을 무시'하려던 null이 '현재 B 보드를 지우기'로 반영된다.
- 영향: 계정 전환·복원 직후 핵심 플레이 화면이 멈춘다. 서버 요청 실패나 실기기 OAuth가 없어도 로컬 가짜 API의 응답 순서만으로 재현된다. 옛 계정의 답을 새 계정에 쓰는 D-29-5와는 증상·발생 조건이 달라 새 ID를 부여했다.
- 직접 검증(컨트롤러): `cd mobile && flutter test /tmp/t29_r4_probe_test.dart --plain-name 'pending initial A load cannot clear completed B board' --reporter expanded` → **1 failed**, `Expected: TodayPuzzleReady, Actual: null`. B 전환 후 TodayPuzzleReady 확인은 통과하고 A 응답 완료 후 동일 단언이 실패한다.
- 직접 검증(화면): `cd mobile && flutter test /tmp/t29_r4_widget_probe_test.dart --reporter expanded` → **1 failed**, `Expected: exactly one matching candidate, Actual: Found 0 widgets with type PuzzleBoard`. B 보드 1개 확인 후 A 응답을 완료하고 다시 pump한 마지막 단언에서 실패했다.
- 경로 확장 검증: `cd mobile && flutter test /tmp/t29_r4_paths_probe_test.dart --reporter expanded` → **2 failed**. 백업 복원 대신 실제 `link(AccountProvider.google)` 또는 `deleteAccount()`를 호출해도 새 보드 존재 확인은 통과하고 A 최초 응답 완료 후 null이 되는 마지막 단언이 실패했다. 따라서 체크박스 2·4·6에 같은 결함을 반영했다.
- 하네스 재구성: `mobile/test/account/account_controller_test.dart`의 `_container`와 `mobile/test/screens/today_tab_test.dart`의 `_pumpToday`를 `/tmp`에 복사하고 상대 import를 절대 경로로 바꾼다. FakeApiClient의 `statsByToken`에 합성 B 코드를 등록하고, `fetchTodayPuzzleGate = Completer<void>()`를 설정한 뒤 최초 provider 조회/화면 pump를 시작한다. Fake의 gate 필드만 null로 바꿔 **이후 B 조회는 즉시 완료**되게 하고 실제 `restoreWithBackupCode`를 호출한다. 이벤트 루프 처리 후 B 보드 존재를 확인하고, 보관한 A gate를 complete한 뒤 보드 존재를 다시 단언한다. 실제 코드·계정·외부 서비스는 필요 없다.
- 기존 테스트 공백: 새 '첫 조회 중 계정이 바뀌면 그 응답은 보드가 되지 않는다' 테스트는 토큰만 직접 교체하고 A 응답이 null인 것을 기대한다. 실제 `_adopt`가 B 보드를 먼저 로드한 뒤 A가 완료되는 경우를 검증하지 않아, 이 null 덮어쓰기 회귀를 잡지 못한다. 정상 전환 테스트와 D-29-5 지연 테스트는 A 최초 조회가 이미 끝난 상태에서 시작한다.

### 직접 실행한 검증

- `cd mobile && flutter test`: **537 passed**, 약 48초, 종료 코드 0. `/tmp/t29-r4-flutter.log`.
- `flutter analyze`(저장소 루트에서 mobile 포함 분석): **No issues found**, 종료 코드 0. `/tmp/t29-r4-analyze.log`.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **153 files, 0 changed**, 종료 코드 0.
- `uv run ruff check .`: **All checks passed**, 종료 코드 0.
- `git diff --check main...HEAD`: 오류 없음.
- D-29-6 독립 컨트롤러·실제 TodayTab 하네스: 각각 **1 failed**, 소셜 연결/삭제 경로 확장 하네스 **2 failed**. 모두 같은 결함의 기대 동작 단언 실패이며 저장소 테스트·앱 코드 변경 없음.
- `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`을 지정한 `uv run pytest -q`: **1412 passed in 1284.55s (0:21:24)**, 종료 코드 0. 기존 `chosung_daily_test_t29`, Redis DB 3, `chosung_daily_test_t29_migrations`를 재사용했다. 새 DB 생성·기본 DB 폴백·간헐 실패·재실행은 없었다. 접속 형식은 구현 증거와 `.env.example`를 따랐으며 자격 증명은 기록하지 않는다. `/tmp/t29-r4-pytest.log`.
- `git diff --name-only main...HEAD -- migrations`: 빈 출력. 이 티켓에 마이그레이션 변경이 없어 조건부 `flask db heads` 확인 대상이 아니다.

### 보안·범위·디자인 및 참고

- Dio의 현재 Bearer 적용, 백업 코드 검증 전 저장 금지·공백 거부, INVALID_ID_TOKEN의 일반 게스트 401과 분리, Apple authorization_code 동봉을 확인했다. 백엔드·웹·CSRF·마이그레이션 변경 없음. 인증 우회·추가 서버 엔드포인트·실제 OAuth 비밀값 신규 기록을 찾지 못했다. 구현 증거의 로컬 개발 DB 접속 문자열은 본 문서에 옮기지 않았다.
- README 설계 판단과 RELEASE는 자기 `### 29.` 절을 추가하고 다른 티켓 절을 바꾸지 않았다. `.env.example`·스펙 변경 없음. 티켓 30 통합의 nullable 홈 상태 시그니처 조정·S4 계정/알림 공존·골든 갱신은 필요한 통합 범위다.
- `e4_records.png`, `records_linked_390.png`, `records_tablet_1024.png`를 직접 열어 계정 줄·마스킹·헤어라인·T4 양쪽 열과 티켓 30 알림 행의 공존을 대조했다. 색·타이포·간격은 OVERRIDES 우선으로 검토했다. 시트/삭제 확인의 제목 semantics, 오류 문구, 플랫폼별 버튼 및 744 폭 적응성도 소스와 테스트로 확인했다.
- `audit.native`는 독립 CLI 실행 결과가 아닌 수동 접근성/성능/테마/플랫폼/적응성 점검이다. 실기기 VoiceOver/TalkBack·실제 OAuth 왕복·서명한 iOS 빌드·스토어 제출은 검증하지 않았다. 공식 로그인 버튼 에셋/콘솔 등록은 이전 라운드에서 승인된 RELEASE 사람 확인 항목이며 이번에 별도 결함으로 재분류하지 않았다.

라운드 4 잔여 결함 합계: BLOCKER 0 / MAJOR 1 / MINOR 0. 이전 결함 FIXED 5 / REPEAT 0, 신규 D-29-6 1건.

판정: FAIL
