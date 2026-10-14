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
