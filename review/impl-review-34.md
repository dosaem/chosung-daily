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
