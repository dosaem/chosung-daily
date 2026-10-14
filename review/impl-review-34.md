# 티켓 34 최종 리뷰 — 라운드 1

- 기준: 로컬 `main...HEAD`, 구현 HEAD `2f93658` (커밋 5개). `origin/main` 미사용.
- 검토: 티켓 34, 스펙 BASELINE·§B.25·US 66, BASELINE 복사 목록 및 원본 파일, 구현 증거, 변경 파일 전체. UI 변경은 없다.
- 결과: **BLOCKER 0 / MAJOR 3 / MINOR 0**. 애플리케이션·테스트·설정·`.scratch/` 수정, 배포, 외부 서비스 호출, 실제 인증 정보 입력 없이 검토했다.

## 체크박스별 충족 여부

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| BASELINE 워크플로·fastlane·ExportOptions·Gradle 서명/심볼·키 예제 복사 및 식별자 치환, AAB strip 오탐 처리 | **미충족** | 대상 파일과 `com.dosaem.chosung`, Team, Flutter 3.38.6 치환 및 `mobile/` 경로는 존재한다. AAB 스텝의 오류 허용 뒤 파일/스트립 검증도 유지됐다. 그러나 iOS 아카이브 서명 설정이 match appstore와 연결되지 않아 D-34-1이 발생한다. |
| 개인정보 라벨 재작성 | **충족** | JSON을 직접 파싱하고 `/privacy`의 한국어 본문 1·3절과 대조했다. USER_ID, EMAIL_ADDRESS, GAMEPLAY_CONTENT, PURCHASE_HISTORY, DEVICE_ID, ADVERTISING_DATA, PRODUCT_INTERACTION, CRASH_DATA, PERFORMANCE_DATA에 게스트·이메일·시도·구독·광고·진단 항목이 대응한다. 실제 ASC 제출/SDK 수집 실측은 수행하지 않았다. |
| API_BASE_URL 브랜치 분기, 광고 ID·serverClientId dart-define 전달 | **미충족** | Actions는 main→PROD, 나머지→DEV variable을 선택하며 모든 빌드에 전달한다. DEV의 8090 인스턴스 도메인 등록은 D3 사람 항목이다. 하지만 문서가 지원하는 수동 fastlane 빌드에는 해당 인자가 전부 빠졌다(D-34-2). |
| flutter-ci 분리, self-hosted 러너, secrets·match 레포·테스터 그룹 문서화 | **충족** | flutter-ci는 변경되지 않았고 배포 잡 3개 모두 self-hosted다. RELEASE의 `### 34.`에 사용 중인 secrets/variables 전부와 match 저장소, testers 그룹이 있다. 보안상 실패 후 정리 누락은 별도 결함 D-34-3이다. |
| D0·D2 없는 debug APK 성공, release/IPA 전제 및 사람 업로드 체크리스트 | **충족** | Firebase 설정 2개와 key.properties가 없는 상태를 확인하고 `flutter build apk --debug --no-pub` 성공을 직접 확인했다. RELEASE에 D0·D2 전제, 실제 푸시·업로드 사람 단계가 분리돼 있다. |

## 직접 실행한 검증

- `uv run ruff check .`: **All checks passed**.
- `uv run pytest tests/test_app_deploy_workflow.py -q`: **71 passed in 0.25s**.
- 전체 `uv run pytest -q`: **814 passed in 729.19s (0:12:09)**, exit 0. 첫 실행에 전부 통과하여 재실행은 필요하지 않았다.
  - `TEST_DATABASE_URL`: 로컬 MySQL의 기존 `chosung_daily_test_t34` 지정, `TEST_REDIS_URL`: 로컬 Redis DB 8 지정. 접속 문자열/비밀번호는 기록하지 않는다.
  - 마이그레이션 테스트는 기본 파생 이름인 기존 `chosung_daily_test_t34_migrations` 사용. 새 DB 생성·기본 테스트 DB 폴백 없음.
- `flutter test --no-pub` (`mobile/`): **87 passed**.
- `flutter analyze --no-pub` (레포 루트): **No issues found**.
- `JAVA_HOME=<로컬 JDK 17> flutter build apk --debug --no-pub` (`mobile/`): **exit 0**, `Built build/app/outputs/flutter-apk/app-debug.apk`, Gradle 22.7초. 의존성은 기존 캐시 사용. 빌드 검증 후 생성된 `mobile/build` 4.6GB는 코디네이터 요청에 따라 삭제하고 부재를 확인했다.
- `uv run flask db heads`: **`dae1b5af0cf7 (head)`** 한 줄. 본 티켓의 마이그레이션 변경은 없다.
- `git diff --check main...HEAD`: 통과. `git check-ignore`로 keystore, key.properties, ASC/Play 키 파일 제외를 확인했고 `git ls-files`에서 실제 서명 키 파일 추적은 발견되지 않았다.
- `xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner -configuration Release -showBuildSettings`: `CODE_SIGN_IDENTITY = iPhone Developer`, `DEVELOPMENT_TEAM = J8QUD7B666` 확인. 실제 서명·match 다운로드·IPA 업로드는 실행하지 않았다.

## 결함

### D-34-1 — MAJOR — iOS 아카이브가 match App Store 서명 구성을 사용하지 않는다

- 위치: `.github/workflows/flutter.yml:312`, `.github/workflows/flutter.yml:325`. 연결된 설정: `mobile/ios/Runner.xcodeproj/project.pbxproj:526`, `mobile/ios/Runner.xcodeproj/project.pbxproj:574`.
- 재현 명령: `xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner -configuration Release -showBuildSettings`에서 CODE_SIGN_IDENTITY, PROVISIONING_PROFILE_SPECIFIER를 확인한다.
- 기대: D2에서 준비한 App Store 배포 인증서와 `match AppStore com.dosaem.chosung` 프로파일만으로 Release archive가 생성되고 TestFlight export로 이어져야 한다.
- 실제: Release의 유효 서명 identity는 **iPhone Developer**이고 match 프로파일 지정이 없다. workflow는 `fastlane match appstore --readonly`만 실행하며 아카이브 설정을 바꾸지 않는다. 따라서 D2에서 문서대로 배포 인증서만 준비한 러너는 개발용 인증서/프로파일을 요구하는 archive 단계에서 막힌다. 개인 맥에 우연히 있는 개발 인증서에 의존하는 구성이다.
- `ExportOptions.plist`의 manual 서명은 이미 생성된 archive의 **export**에 적용된다. 로컬 Flutter SDK `build_ios.dart`에서 먼저 `super.runCommand()`로 archive한 다음 `-exportArchive -exportOptionsPlist`를 호출하는 순서를 확인했다. export plist만으로 archive 설정이 바뀌지 않는다. BASELINE Xcode 프로젝트에는 Release의 Apple Distribution/manual/match profile 지정이 있으나 이 앱에는 빠져 있다.
- 실제 인증서가 필요한 archive 실패를 실행한 것은 아니다. 설정 불일치는 위 로컬 명령으로 재현했으며 실제 D2 서명 리허설은 수정 후 사람 검증이 필요하다.

### D-34-2 — MAJOR — 수동 fastlane 배포가 서버·광고·로그인 설정 없이 앱을 다시 빌드한다

- 위치: `mobile/android/fastlane/Fastfile:15`, `mobile/ios/fastlane/Fastfile:16`.
- 재현 입력: 문서에 안내된 Android/iOS의 `fastlane beta` 또는 `fastlane release`를 호출할 때 첫 Flutter 빌드 명령을 확인한다. 외부 호출 방지를 위해 로컬 Ruby 하네스로 원본 Fastfile의 beta 블록을 평가하고 `sh`에서 명령만 포착한 뒤 중단했다.
- 실제 포착 명령: Android는 `flutter build appbundle --release`(오탐 처리 suffix 포함), iOS는 `flutter build ios --release --no-codesign`. **둘 다 dart-define 0개**다. beta/release 모두 같은 빌드 함수를 쓴다.
- 기대: 대상 서버 API 루트, 플랫폼별 광고 유닛, GOOGLE_SERVER_CLIENT_ID를 받아 빌드하거나 필수 입력이 없으면 업로드 전에 멈춰야 한다.
- 실제: Actions 잡에만 정의된 DART_DEFINES를 수동 lane은 읽지도 전달하지도 않는다. 빌드가 매번 새로 실행되므로 앞서 올바른 인자로 만든 바이너리도 대체된다. `mobile/lib/config/app_env.dart:7`의 에뮬레이터용 기본 API 주소가 들어가 실기기의 API 호출이 실패한다. 광고·로그인 인자 역시 전달되지 않는다.
- 기존 `test_every_build_passes_the_dart_defines`는 YAML의 Android/iOS 스텝만 검사하므로 이 경로 누락을 검출하지 않는다.

### D-34-3 — MAJOR — self-hosted 러너의 인증 파일과 keychain이 실패 후 남는다

- 위치: `.github/workflows/flutter.yml:199`, `.github/workflows/flutter.yml:287`, `.github/workflows/flutter.yml:321`, `.github/workflows/flutter.yml:337`, `.github/workflows/flutter.yml:351` (Android 서명 파일 생성은 142·150행).
- 재현 방법: YAML에서 Firebase 업로드 `run` 블록을 읽어 임시 RUNNER_TEMP와 비인증 더미 문자열을 주고, `npx() { return 1; }`로 대체하여 `bash -e`로 실행한다. **exit 1 이후 서비스 계정 JSON 파일이 남음**을 직접 확인했다. 업로드 뒤에 있는 `rm`은 실행되지 않는다. altool 뒤의 P8 삭제도 같은 제어 흐름이다.
- 별도 재현: match 스텝에서 `security`·`openssl`은 외부 효과 없는 함수로, `fastlane`은 exit 1 함수로 대체하고 임시 GITHUB_ENV로 실행했다. **exit 1, GITHUB_ENV에 KEYCHAIN_NAME 없음**을 확인했다. 이름 export가 match 뒤에 있으므로 `always()` 정리 단계는 이미 생성한 keychain을 찾지 못한다.
- 기대: 성공/실패 모두에서 생성한 서명 파일·ASC API JSON·추출 P8·Firebase JSON·임시 keychain을 제거해야 한다.
- 실제: Android keystore/key.properties와 ASC api_key.json에는 성공 시에도 삭제가 없으며, 업로드 실패 시 홈 디렉터리의 P8과 match 실패 시 keychain까지 남을 수 있다. self-hosted는 잡 종료 때 호스트가 폐기되지 않으므로 후속 잡/프로세스가 인증 자료에 접근할 수 있다. gitignore는 커밋 방지일 뿐 러너의 잔존 인증 자료를 제거하지 않는다.
- 실제 키를 쓰거나 읽지 않았다. 기존 테스트는 cleanup 스텝의 `if: always()` 문자열만 검사하여 실패 전후 이름 전달/파일 정리를 검증하지 않는다.

## 범위·보안·검증 한계

- RELEASE 변경은 파일 끝 자기 번호 `### 34.` 추가뿐이다. 다른 티켓의 공용 절·행을 고친 흔적은 없으며 `.env.example`·스펙·마이그레이션 변경도 없다.
- 배포 트리거는 main/develop push와 수동 dispatch다. fork PR 이벤트 트리거는 없고, 커밋 메시지는 환경변수로 받은 뒤 인용하여 셸에 전달한다. 이번 diff에서 실제 키·토큰·비밀번호 값의 커밋은 발견하지 못했다.
- 테스트는 정적 계약 검사로 유용하지만 archive 서명, 수동 lane 인자, 실패 후 정리까지 입증하지 않는다. 구현 증거의 통과 기록만으로 배포 성공을 인정하지 않았다.
- 프로덕션/NAS 접근과 실제 Firebase·Apple·Play 호출은 하지 않았다. 실제 서명·배포 리허설은 D0·D2 준비 후 사람 단계로 남는다. 취향·스타일 제안은 결함에 포함하지 않았다.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` = `a520223`, 구현 HEAD = `8b0b423`. `git diff main...HEAD` 전체와 `git log main..HEAD`의 8개 커밋을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 34, 스펙 BASELINE·§B.25·US 66, BASELINE 복사 목록과 Android/iOS Fastfile 원본, 구현 증거의 수정 라운드, 이전 리뷰를 대조했다. UI 변경은 없다.
- 이전 결함 **D-34-1~3 모두 FIXED**. 새 결함 **D-34-4 MAJOR 1건**. 현재 미해결 합계 **BLOCKER 0 / MAJOR 1 / MINOR 0**.

### 체크박스별 충족 여부

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| BASELINE 워크플로·fastlane·ExportOptions·Gradle 서명/심볼·키 예제 복사·치환, AAB strip 처리 | **미충족** | 지정 파일, 식별자 `com.dosaem.chosung`, Team, Flutter 3.38.6, `mobile/` 경로 및 Actions의 스트립 검증은 존재한다. Xcode Release 서명 불일치는 수정됐다. 다만 수동 Android lane이 실제 빌드 실패를 삼킨 뒤 이전 AAB를 업로드하는 D-34-4가 남는다. |
| 개인정보 라벨 재작성 | **충족** | JSON 9개 카테고리를 직접 읽고 `web/templates/legal/privacy.ko.html`의 수집·외부 처리 항목과 대조했다. 게스트·이메일·시도·구독·광고·진단 항목이 대응한다. ASC 제출과 SDK 실측은 사람 검증 범위다. |
| API_BASE_URL 브랜치 분기, 광고 ID·serverClientId dart-define 전달 | **충족** | Actions main→PROD/그 외→DEV 분기와 플랫폼별 광고 변수 전달을 확인했다. 두 수동 Fastfile도 필수 5개 인자를 환경변수에서 읽어 실제 명령에 전달하고, 하나라도 없으면 빌드 전에 멈춘다. DEV 8090 인스턴스 도메인 등록은 문서의 D3 전제다. |
| flutter-ci 분리, self-hosted 러너, secrets·match 레포·App Distribution 그룹 문서화 | **충족** | flutter-ci 변경 없음. 배포 잡 3개 모두 self-hosted이고 RELEASE `### 34.` 표에 사용 변수·secret 이름, match 저장소, testers 그룹이 있다. |
| D0·D2 없는 debug APK 성공, release/IPA 전제와 사람 업로드 체크리스트 | **충족** | Firebase 설정 2개와 key.properties 부재를 확인한 뒤 이번 라운드에서 debug APK 빌드에 성공했다. RELEASE에 D0·D2 및 실제 업로드 사람 단계가 명시돼 있다. |

### 이전 결함 판정

| ID | 이전 심각도 | 판정 | 직접 재검증 |
|---|---|---|---|
| D-34-1 | MAJOR | **FIXED** | `mobile/ios/Runner.xcodeproj/project.pbxproj:526`, `:580`의 Release 설정을 확인했다. `xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner -configuration Release -showBuildSettings` 결과는 `CODE_SIGN_IDENTITY = Apple Distribution`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = J8QUD7B666`, `PROVISIONING_PROFILE_SPECIFIER = match AppStore com.dosaem.chosung`이다. ExportOptions와 같은 프로파일이다. |
| D-34-2 | MAJOR | **FIXED** | `mobile/android/fastlane/Fastfile:21`, `mobile/ios/fastlane/Fastfile:21`의 인자 검사·Shellwords 인용·명령 전달을 확인했다. Ruby 하네스로 원본 함수를 평가하는 20개 테스트가 필수 값 전달과 각 값 누락 시 exit 2/빌드 미실행을 검증하며 실제 통과했다. |
| D-34-3 | MAJOR | **FIXED** | `.github/workflows/flutter.yml:203`의 Firebase trap, `:352`의 P8 trap, `:321`의 match 이전 KEYCHAIN_NAME 전달과 두 always cleanup을 확인했다. 업로드/match 실패를 주입하는 셸 테스트가 통과했다. 문자열 검사에 그친 Android/ASC cleanup은 별도로 임시 파일을 만든 뒤 원본 run 블록을 실행하여 모두 삭제됨과 keychain 삭제 명령 호출을 확인했다. 실제 키·keychain은 사용하지 않았다. |

### 새 결함

#### D-34-4 — MAJOR — 수동 Android 배포가 빌드 실패 후 이전 AAB를 업로드한다

- 위치: `mobile/android/fastlane/Fastfile:45`, `:46`; 업로드 진입점 `:53`, `:55`, `:68`, `:71`.
- 재현 입력: 이전에 빌드했지만 아직 업로드하지 않은 `mobile/build/app/outputs/bundle/release/app-release.aab`가 있는 상태에서, 소스에 컴파일 오류가 있는 새 버전을 문서의 `fastlane beta`(기본 `clean` 미지정) 또는 `fastlane release`로 실행한다. 필수 dart-define 환경변수 5개는 모두 정상 지정한다.
- 기대: 이번 빌드가 새 AAB를 만들지 못하면 업로드 전에 실패해야 한다. strip false-positive를 허용하더라도 이번 실행이 생성한 산출물임을 보장해야 한다.
- 실제: 모든 Flutter 실패를 `|| echo`로 성공 처리하고, 이미 있던 AAB의 존재만 검사한다. 따라서 다른 API 환경·이전 소스·이전 버전의 AAB로 업로드를 진행할 수 있다. `clean`은 선택사항이고 문서의 기본 명령에는 없다.
- 직접 재현: 임시 `mobile/android/fastlane` 구조와 이전 AAB 더미를 만들고, PATH 앞의 임시 `flutter` 실행파일을 `echo compilation-failed >&2; exit 1`로 구성했다. 원본 Fastfile 전체를 Ruby로 읽어 `platform`/`lane` DSL을 평가하고 `LANES[:beta].call({})`를 실행했다. `sh`는 실제 셸을 실행했고, 외부 업로드 함수만 출력으로 대체했다. **exit 0, `compilation-failed`, `UPLOAD_REACHED: internal`**을 확인했다. AAB를 지운 동일 입력은 **exit 1, `AAB was not produced`**, 업로드 미진입이었다. 산출물 존재 이외의 차이 없이 실패가 업로드로 바뀌었다.
- 회귀 테스트 공백: `tests/test_app_deploy_workflow.py:662` 부근의 `CAPTURE_RB`는 `File.exist?`를 항상 true로 만들고 `sh`를 실행하지 않는다. dart-define 전달 검증에는 유효하지만, 새 산출물 생성 실패와 이전 산출물 재사용은 검증하지 않는다. 따라서 배포 테스트 102개 통과가 이 실패 경로의 안전성을 증명하지 않는다.
- 수정 방향: 빌드 전에 대상 AAB를 제거하거나 이번 실행이 새로 만든 파일임을 검증하고, 새 파일의 유효성을 검사한 뒤에만 오탐을 허용한다. 이전 AAB가 있는 상태의 실제 빌드 실패 회귀 사례가 필요하다. 리뷰에서는 코드를 수정하지 않았다.

### 직접 실행한 검증

- `uv run ruff check .`: **All checks passed**.
- `uv run pytest tests/test_app_deploy_workflow.py -q`: **102 passed in 1.83s**.
- 전체 `uv run pytest -q`: **1026 passed in 680.92s (0:11:20)**, exit 0. 첫 실행에 통과하여 재실행 없음.
  - `TEST_DATABASE_URL`로 기존 로컬 `chosung_daily_test_t34`, `TEST_REDIS_URL`로 로컬 Redis DB 8을 지정했다. 마이그레이션 왕복 테스트는 기존 파생 DB `chosung_daily_test_t34_migrations`를 사용했다. 새 DB 생성이나 기본 테스트 DB 폴백 없이 완료했다. 접속 문자열·비밀번호는 기록하지 않는다.
- `flutter analyze --no-pub` (레포 루트): **No issues found**, exit 0.
- `flutter test --no-pub` (`mobile/`): **120 passed**, exit 0.
- D0·D2 파일이 없는 상태에서 `JAVA_HOME=<로컬 JDK 17> flutter build apk --debug --no-pub` (`mobile/`): **exit 0**, `Built build/app/outputs/flutter-apk/app-debug.apk` (Gradle 26.6초).
- `uv run flask db heads`: **`d7a1f0ca0a29 (head)`** 한 줄. 티켓 자체 마이그레이션 변경 없음.
- `plutil -lint mobile/ios/Runner.xcodeproj/project.pbxproj`: **OK**. Xcode 유효 Release 설정은 D-34-1 재검증 표 참조.
- `git diff --check main...HEAD`: 통과. `git check-ignore`로 서명·스토어 인증 파일 제외를 확인했고, `git ls-files`에 실제 jks/keystore/P8/ASC·Play JSON 인증 파일은 없었다.

### 범위·보안·검증 한계

- 공유 파일 `docs/RELEASE.md`는 기존 내용 뒤에 자기 `### 34.`만 추가했다. `.env.example`·스펙·다른 티켓의 공유 절 변경 없음. 애플리케이션 변경은 app_env 주석 교정뿐이며, 이번 리뷰는 리뷰 문서만 수정한다.
- diff에서 실제 키·토큰·비밀번호 기록은 발견하지 못했다. 키 예제는 자리표시자이고 사용자 지정 secret은 환경변수로 전달한다. 인증·CSRF·데이터 모델 동작을 변경하지 않는다.
- 정적 계약 테스트와 로컬 실패 주입은 실제 서명·스토어 업로드 성공을 보장하지 않는다. D0·D2 준비 후 사람 리허설이 남는다. 프로덕션/NAS 접근, 실제 Firebase·Apple·Play 호출, 인증 정보 입력, push는 수행하지 않았다.
- 취향·스타일 제안은 결함에 포함하지 않았다.

판정: FAIL


## 라운드 3

- 기준: 로컬 `main` = `82e59ea`, 구현 HEAD = `3077fdc`. `git diff main...HEAD` 전체와 `git log main..HEAD`의 10개 커밋을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 34, 스펙 BASELINE·§B.25·US 66, BASELINE 복사 목록과 원본 Fastfile, 구현 증거 및 이전 리뷰를 대조했다. UI 변경은 없다.
- 이전 결함 **D-34-1~4 모두 FIXED**. 새 결함 및 현재 미해결 결함 **BLOCKER 0 / MAJOR 0 / MINOR 0**.

### 체크박스별 충족 여부

| 티켓 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| BASELINE 워크플로·fastlane·ExportOptions·Gradle 서명/심볼·키 예제 복사·치환, AAB strip 처리 | **충족** | 지정 파일, `com.dosaem.chosung`, Team `J8QUD7B666`, Flutter 3.38.6, `mobile/` 경로를 확인했다. Release 유효 서명 설정과 ExportOptions가 일치한다. Actions와 수동 Android lane 모두 빌드 전 이전 AAB를 지우고 같은 검증 스크립트를 실행한다. 실패 및 스트립 오탐 대조 사례의 실행 결과는 아래와 같다. |
| 개인정보 라벨 재작성 | **충족** | JSON의 9개 카테고리와 `web/templates/legal/privacy.ko.html`의 수집·외부 처리 항목을 직접 대조했다. 게스트·이메일·시도·구독·광고·진단 항목이 대응한다. 실제 SDK 수집 실측 및 ASC 제출은 이번 검증 범위 밖이다. |
| API_BASE_URL 브랜치 분기, 광고 ID·serverClientId dart-define 전달 | **충족** | Actions는 main→PROD, develop→DEV variable을 선택하고 플랫폼별 광고 ID 및 OAuth ID를 빌드에 전달한다. 두 수동 Fastfile은 필수 값 5개를 검사하고 Shellwords로 인용해 전달한다. DEV 8090 인스턴스 도메인 등록은 RELEASE의 D3 전제다. |
| flutter-ci 분리, self-hosted 러너, secrets·match 레포·App Distribution 그룹 문서화 | **충족** | flutter-ci 변경 없음. 배포 잡 3개 모두 self-hosted이고 RELEASE `### 34.`에 사용 secret·variable 표, match 저장소, testers 그룹이 있다. 실패 시 인증 자료 정리도 실행 검증했다. |
| D0·D2 없는 debug APK 성공, release/IPA 전제와 사람 업로드 체크리스트 | **충족** | Firebase 설정 2개 및 key.properties 부재를 확인한 상태에서 이번 라운드의 debug APK 빌드가 성공했다. RELEASE에 D0·D2 전제와 사람이 수행할 실제 업로드 리허설이 명시돼 있다. |

### 이전 결함 판정

| ID | 이전 심각도 | 판정 | 위치·재현 입력 → 기대 및 실제 |
|---|---|---|---|
| D-34-1 | MAJOR | **FIXED** | `mobile/ios/Runner.xcodeproj/project.pbxproj:526`, `:580`. `xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner -configuration Release -showBuildSettings` → 기대한 `Apple Distribution`, `Manual`, Team `J8QUD7B666`, `match AppStore com.dosaem.chosung`이 실제 출력됐다. |
| D-34-2 | MAJOR | **FIXED** | `mobile/android/fastlane/Fastfile:21`, `mobile/ios/fastlane/Fastfile:21`. 필수 dart-define 환경변수 전달 및 각 값 누락 입력 → 기대한 인자 전달/누락 시 빌드 전 중단이 원본 함수 Ruby 실행 테스트에서 통과했다. 이 테스트의 셸 캡처만으로 실제 빌드 성공을 주장하지 않는다. |
| D-34-3 | MAJOR | **FIXED** | `.github/workflows/flutter.yml:188`, `:308`, `:339`, `:231`, `:355`. Firebase·match·TestFlight 실패 주입 → 임시 키 삭제와 match 실패 전 KEYCHAIN_NAME 전달을 확인했다. Android/iOS always cleanup 원본 블록도 임시 더미 파일과 security 스텁으로 실제 실행해 keystore·key.properties·ASC JSON·Firebase JSON 삭제 및 keychain 삭제 명령 호출을 확인했다. |
| D-34-4 | MAJOR | **FIXED** | `mobile/android/fastlane/Fastfile:48`, `:54`, `:56`; `.github/workflows/flutter.yml:171`, `:174`, `:175`. 이전 AAB 존재 + Flutter exit 1 + 새 파일 없음 → 수동 beta/release 회귀 테스트에서 비정상 종료·업로드 미진입. 별도로 Actions 원본 run 블록을 임시 트리에서 `bash -e`로 실행해 exit 1 및 이전 AAB 부재를 확인했다. 새 정상 AAB 생성 + exit 1의 오탐 대조군은 수동 lane과 Actions 모두 exit 0으로 통과했다. 새 미스트립 AAB·잘린 zip·파일 누락은 회귀 테스트에서 거부됐다. |

### 새 결함

없음. 기존 D-34-4를 막는 테스트는 원본 Fastfile을 평가하고 실제 셸과 파일 검사를 실행한다. Flutter 컴파일과 외부 업로드만 대체하며, 실패 사례와 성공 대조군이 모두 있어 항상 성공/실패하는 테스트가 아니다.

### 직접 실행한 검증

- `uv run ruff check .`: **All checks passed**, exit 0.
- `uv run pytest tests/test_app_deploy_workflow.py -q`: **114 passed in 4.23s**, exit 0.
- 전체 `uv run pytest -q`: **1110 passed in 665.51s (0:11:05)**, exit 0. 첫 실행에 통과해 재실행 없음.
  - `TEST_DATABASE_URL`로 기존 로컬 `chosung_daily_test_t34`, `TEST_REDIS_URL`로 로컬 Redis DB 8 지정. 마이그레이션 테스트는 기존 파생 DB `chosung_daily_test_t34_migrations`를 사용했다. 새 DB 생성·기본 테스트 DB 폴백 없이 완료했다. 접속 문자열·비밀번호는 기록하지 않는다.
- `flutter analyze --no-pub` (레포 루트): **No issues found**, exit 0.
- `flutter test --no-pub` (`mobile/`): **120 passed**, exit 0.
- D0·D2 파일 부재 확인 후 `JAVA_HOME=<로컬 JDK 17> flutter build apk --debug --no-pub` (`mobile/`): **exit 0**, `Built build/app/outputs/flutter-apk/app-debug.apk`, Gradle 27.0초.
- `uv run flask db heads`: **`d7a1f0ca0a29 (head)`** 한 줄. 본 티켓 마이그레이션 변경 없음.
- `plutil -lint mobile/ios/Runner.xcodeproj/project.pbxproj`: **OK**. Xcode 유효 Release 서명 설정은 D-34-1 행 참조.
- `git diff --check main...HEAD`: 통과. `git check-ignore`로 서명·스토어 인증 파일 제외를 확인했고, `git ls-files`에 실제 jks/keystore/P8/ASC·Play 인증 JSON 파일은 없었다.

### 범위·보안·검증 한계

- 공유 파일 `docs/RELEASE.md`는 기존 내용 뒤에 자기 `### 34.`만 추가했다. `.env.example`·스펙·flutter-ci·다른 티켓 공유 절 변경 없음. 앱 동작 변경은 없고 app_env 변경은 주석 교정이다.
- diff에서 실제 키·토큰·비밀번호 기록은 발견하지 못했다. 키 예제는 자리표시자이고, 외부 입력인 커밋 메시지는 셸에 직접 삽입하지 않고 환경변수로 전달한다. 인증·CSRF·데이터 모델 변경은 없다.
- 새 AAB 검사는 생성 여부·zip 열기·manifest 엔트리·libapp 스트립 여부를 확인하는 배포 전 검사이며, 모든 스토어 유효성 검사를 대신하지 않는다. 실제 서명·match 다운로드·스토어 업로드 성공은 D0·D2 준비 후 사람이 리허설해야 한다.
- 프로덕션/NAS 접근, 실제 Firebase·Apple·Play 호출, 인증 정보 입력, push는 수행하지 않았다. 이번 리뷰의 추적 파일 수정은 이 문서 하나다.
- 취향·스타일 제안은 결함으로 올리지 않았다.

판정: PASS
