# 티켓 22 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` b43567ef37b53615db4744f1ac5bcf52b216e0ba → 구현 HEAD 990290e21eda6ff0e7e829cd498e46711fb8f12e. `git log main..HEAD` 7커밋, `git diff main...HEAD` 175파일 확인. origin/main 사용 안 함.
- 읽은 요구: 티켓 22, spec §B.18–22·C.31, SCREENS 탭 구조·S7, OVERRIDES, BASELINE 복사 목록, 구현 증거 문서. 코드·테스트·네이티브 프로젝트·CI를 직접 대조했다.
- 결함: **BLOCKER 1 / MAJOR 1 / MINOR 1**. 기존 테스트 통과와 Android APK 생성만으로 실제 앱 시작 성공을 증명하지 못한다.

## 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| Flutter 루트 mobile/, CI working-directory | 충족 | mobile/ 루트와 flutter-ci.yml의 defaults.run.working-directory: mobile. Flask app/ 변경 없음. |
| 필수 패키지·식별자·앱 이름, Hive/freezed 없음 | 미충족 | pubspec.yaml에 지정 패키지 존재, Android/iOS 식별자 com.dosaem.chosung, Hive/freezed 없음. 그러나 iOS 최소 플랫폼 불일치 D-22-2와 한국어 앱 이름 리소스 누락 D-22-3. |
| Firebase gitignore·example·파일 없으면 초기화 스킵, analyze/test 통과 | 충족 | 실제 파일 2개 없음, git check-ignore 적용 확인, example은 자리표시자. Gradle 조건부 플러그인과 런타임 예외 처리 확인. 파일 없이 analyze/test/APK 빌드 통과. 다만 앱 전체 시작은 D-22-1 때문에 실패한다. |
| ApiClient 3메서드·Dio·Fake·API_BASE_URL·예외 골격 | 충족 | api_client.dart에 createGuest/fetchConfig/fetchMyStats만 존재. 실제 서버 응답 모델과 대조. Dio 전송 경계 테스트에서 본문·인증 헤더·예외 검증. AppEnv에 dart-define. |
| secure storage·en 게스트·401 재발급·전역 Provider | 충족 | SecureGuestTokenStore와 GuestTokenNotifier 확인. 시작 컨트롤러 테스트에서 복원/발급/en/401 후 1회 재발급/두 번째 401 전파를 검증. Provider 교체·구독 테스트 통과. 실기기 Keychain/Keystore 저장 검증은 하지 않음. |
| ThemeData 토큰·Pretendard·Lucide·그림자 없음·600px | 충족 | AppColors 라이트/다크 값이 OVERRIDES 표와 일치. Pretendard 3종과 OFL 원문 존재, Lucide 사용. 테마·다크 모드·iPad 폭 테스트 통과, MaxWidthBody maxWidth=600. |
| S7 점검/업데이트/정상 분기와 위젯 테스트 | 미충족 | planStartup과 Fake config 3분기 테스트 자체는 통과. 실제 main이 사용하는 locale 미지정 경로는 D-22-1로 화면 생성 전에 실패. |
| 3탭 뼈대·탭 바 아래 상시 배너 슬롯 | 충족 | HomeShell 3개 branch와 NavigationBar 아래 AdBannerSlot, SafeArea·예약 높이 확인. 탭 전환 및 슬롯 높이 테스트 통과. 실제 진입은 D-22-1 해결 필요. |
| ubuntu-latest CI·analyze 0건·audit.native 통과 기록 | 충족 | CI 파일 존재, 직접 analyze 0건. 증거 문서에 audit.native 15/20 기록 존재. 실기기/시뮬레이터 시각 검수까지 통과했다는 의미는 아니며 아래 검증 한계 참조. |
| README Flutter 상태 흐름·SDK·테스트 경계 문단 | 충족 | README 설계 판단 ### 22.에 세 문단 존재. 다만 문서의 앱 실행 가능 주장은 D-22-1에 의해 반증됨. |

## 직접 실행한 검증

| 명령 / 검사 | 결과 |
|---|---|
| mobile/에서 `flutter analyze` | exit 0, No issues found (2.5s) |
| mobile/에서 `flutter test` | exit 0, 81 passed (14s) |
| mobile/에서 `dart format --output=none --set-exit-if-changed .` | exit 0, 44 files, 0 changed. 파일 수정 금지 조건 때문에 비수정 옵션 사용. |
| 루트 `uv run ruff check .` | exit 0, All checks passed |
| Firebase 파일 부재 확인 후 `JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug --no-pub` | exit 0, APK 생성 (13.8s) |
| locale 미지정 추가 재현, 아래 D-22-1 코드 | exit 1, 1 failed, LateInitializationError |
| 로컬 CocoaPods Platform.supports? 비교 | iOS 13.0 / Firebase iOS 15.0 → compatible=false |
| xcodeproj로 Runner Resources와 플랫폼 설정 읽기 | 한국어 InfoPlist.strings 없음, Debug/Release/Profile 모두 13.0 |
| `git diff --check` | exit 0 |

코디네이터의 추가 지시("백엔드 변경이 없으면 생략 가능")에 따라 pytest는 생략했다. Python 애플리케이션·테스트·마이그레이션 변경은 없으며 DB/Redis에 접속하거나 새 DB를 만들지 않았다. 새 마이그레이션이 없어 flask db heads 조건은 해당하지 않는다. iOS 전체 빌드·실기기 실행·스크린샷은 수행하지 않았다. D-22-2는 전체 빌드 실패 로그 대신 설치된 정확한 패키지와 CocoaPods의 플랫폼 호환성 판정으로 확인했다.

## 결함

### D-22-1 — BLOCKER — 국제화 초기화 누락으로 실제 앱 시작 실패

- 위치: `mobile/lib/main.dart:10`, `mobile/lib/app.dart:26`, `mobile/test/app_startup_branch_test.dart:31` 및 `:51`.
- 원인: main은 EasyLocalization.ensureInitialized()를 호출하지 않고 startLocale=null인 AppLocalizationScope를 생성한다. 설치된 easy_localization 3.0.8은 기기 언어를 static late `_deviceLocale`에 저장하며 초기화 함수에서만 값을 넣는다. saveLocale=false는 기기 언어 초기화를 대신하지 않는다. 앱 코드의 "ensureInitialized도 필요 없다" 주석은 실제 라이브러리 동작과 반대다.
- 재현: 다음을 레포 밖 `/tmp/t22_startup_review_test.dart`로 저장하고 mobile/에서 `flutter test --no-pub /tmp/t22_startup_review_test.dart --reporter expanded` 실행. API·Firebase·스토어 호출 없이 실제 AppLocalizationScope의 기본 생성 경로만 사용했다.

```dart
import 'package:chosung/app.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('production localization scope initializes without forced locale', (tester) async {
    await tester.pumpWidget(const AppLocalizationScope(child: SizedBox()));
    expect(tester.takeException(), isNull);
  });
}
```

- 기대: 기기 언어를 선택하고 자식 위젯을 예외 없이 생성.
- 실제: `LateInitializationError: Field '_deviceLocale@…' has not been initialized.`, 1 failed. main도 같은 생성 경로이므로 게스트 발급/점검/업데이트/홈을 표시하기 전에 실패한다.
- 기존 테스트가 놓친 이유: 모든 앱 위젯 테스트가 startLocale를 강제로 전달하여 라이브러리의 기기 언어 분기를 우회한다. "기기 언어가 en" 테스트 역시 기기 설정을 읽지 않고 startLocale=en을 주입한다. 초기화와 강제 언어 없는 시작 회귀 검증이 필요하다.

### D-22-2 — MAJOR — iOS 프로젝트 최소 버전이 Firebase 의존성과 호환되지 않음

- 위치: `mobile/ios/Podfile:2`, `mobile/ios/Runner.xcodeproj/project.pbxproj:349` (동일 설정 :476, :527), `mobile/ios/Flutter/AppFrameworkInfo.plist:26`.
- 원인: Podfile의 platform 선언은 주석이고 Xcode 세 구성의 IPHONEOS_DEPLOYMENT_TARGET은 모두 13.0이다. lockfile에 고정된 firebase_core 4.15.0 및 firebase_analytics 12.6.0의 실제 podspec은 모두 iOS 15.0을 요구한다. Firebase 설정 파일이 없어도 네이티브 플러그인 의존성은 설치 대상이므로 런타임 예외 처리로 해결되지 않는다.
- 재현: `rg -n 'IPHONEOS_DEPLOYMENT_TARGET' mobile/ios/Runner.xcodeproj/project.pbxproj` 및 설치된 두 패키지의 `ios/*.podspec`에서 deployment_target 확인. 로컬 CocoaPods로 아래 판정을 실행했다(패키지 ios 디렉터리, Ruby에 cocoapods 로드).

```ruby
require './firebase_sdk_version'
$FirebaseSDKVersion = firebase_sdk_version!
spec = Pod::Specification.from_file('firebase_core.podspec')
required = spec.available_platforms.find { |p| p.name == :ios }
app = Pod::Platform.new(:ios, '13.0')
puts "app=#{app}, dependency=#{required}, compatible=#{app.supports?(required)}"
```

- 기대: 프로젝트의 iOS 플랫폼이 필수 패키지 플랫폼을 지원하여 CocoaPods 의존성을 해결할 수 있음.
- 실제: `app=iOS 13.0, dependency=iOS 15.0, compatible=false`. 현재 설정으로 iOS 의존성을 해결할 수 없다. iOS 전체 빌드는 실행하지 않았으며 이 판정은 로컬 podspec과 CocoaPods에서 직접 확인한 호환성 오류다. Android 빌드와 Dart analyze/test는 이 문제를 검사하지 않는다.

### D-22-3 — MINOR — 한국어 iOS 앱 이름 파일이 번들에 포함되지 않음

- 위치: `mobile/ios/Runner.xcodeproj/project.pbxproj:214`, `mobile/ios/Runner/ko.lproj/InfoPlist.strings:1`, `docs/RELEASE.md:323`.
- 재현: `rg -n 'InfoPlist.strings|ko.lproj' mobile/ios/Runner.xcodeproj/project.pbxproj` → 일치 없음. xcodeproj 라이브러리로 Runner의 resources_build_phase.files_references를 읽어도 해당 리소스/variant group이 없다.
- 기대: 한국어 기기에서 설치 앱 이름이 티켓에 지정된 "오늘의 초성"으로 표시되도록 한국어 이름 리소스가 빌드에 포함됨.
- 실제: 파일만 존재하고 Runner Resources에 연결되지 않아 Info.plist의 "Hidden Vowels"만 사용된다. RELEASE 문서도 수동으로 타깃에 추가해야 한다고 명시한다. 이는 인증서·계정이 필요한 작업이 아니라 이 티켓의 앱 이름 설정 누락이다. 실제 한국어 기기 설치는 하지 않았으며 번들 리소스 구성으로 확인했다.

## 보안·범위·테스트 경계 확인

- 신규 Firebase 파일은 .example만 추적하며 식별자/키가 자리표시자임을 확인했다. 실제 설정 파일은 부재하고 gitignore가 적용된다. 추적 파일에서 서명 키·key.properties·keystore·실제 Firebase 설정 파일은 발견하지 못했다. 리뷰 문서에 키·토큰·비밀번호 값을 기록하지 않았다.
- 토큰은 secure storage에 저장하고 ApiClient는 요청 시 Provider 값을 읽는다. 인증 필요 메서드는 토큰 없이 전송하지 않는다. 이번 변경에서 서버 인증·CSRF·DB 쓰기 로직의 변경이나 데이터 손상 경로는 발견하지 못했다.
- README 설계 판단은 자기 번호 ### 22. 추가, RELEASE는 자기 번호 절 추가. README API 표·.env.example·스펙 미정 항목 변경 없음. 기술 스택의 한 줄과 PRODUCT Platform 메모는 확인된 범위이며 다른 티켓 행/절을 덮어쓰지 않았다.
- Fake는 주로 외부 경계이며 분기·토큰 교체·라우팅 검증은 의미 있다. 다만 D-22-1처럼 실제 부트스트랩과 테스트 사이 차이가 존재한다. 증거 문서의 "Dio가 매 요청마다 토큰을 읽는 것을 테스트한다"는 설명은 과장되어 있다: 현 테스트는 단일 토큰의 헤더와 Provider의 교체를 따로 검증하며, 같은 Dio 클라이언트에서 교체 전후 두 요청을 직접 비교하지 않는다. 구현 자체는 매 호출 _readToken()을 사용하므로 이를 별도 결함으로 집계하지 않았다.

## 참고

- PRODUCT Platform=web 유지와 태블릿 하단 탭 바는 코디네이터가 판단 사항으로 분류했으므로 결함에 포함하지 않았다. 현재 티켓의 3탭·600px 요구와 일치한다.
- audit.native 15/20은 문서에 기록되어 있지만 시뮬레이터/실기기 캡처와 iOS 빌드가 빠져 있다. 이번 리뷰 역시 시각적 완성도와 네이티브 런타임까지 검증했다고 주장하지 않는다.
- 앱 코드·테스트·설정·.scratch는 수정하지 않았다. 변경 산출물은 이 리뷰 문서 하나다.

판정: FAIL

## 라운드 2

- 검토 기준: 로컬 `main` = `bf287f6735b07eb0f8a596195bf368ebe31ccd1a`, 구현 HEAD = `b68582fd047815a56921d59cc5b3463b1836b0f6`. `git diff main...HEAD` 179파일, `git log main..HEAD` 12커밋을 기준으로 검토했다. origin/main은 사용하지 않았다.
- 티켓 22, spec §B.18–22·C.31, SCREENS 탭 구조·S7, OVERRIDES 및 구현 증거의 수정 라운드를 소스·테스트·빌드 결과와 대조했다. 별도 BASELINE 파일은 현재 worktree의 `.scratch`에서 찾지 못했으므로 해당 문서를 독립적으로 확인했다고 주장하지 않는다.
- 이전 결함 **D-22-1 / D-22-2 / D-22-3 모두 FIXED**. REPEAT 0건, 새 결함 0건. 현재 남은 결함은 **BLOCKER 0 / MAJOR 0 / MINOR 0**이다.

### 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| Flutter 루트 mobile/, CI working-directory | 충족 | Flutter 프로젝트가 mobile/에 있고 flutter-ci.yml의 defaults.run.working-directory가 mobile이다. Flask app/ 변경 없음. |
| 필수 패키지·식별자·ko/en 앱 이름, Hive/freezed 없음 | 충족 | pubspec/lock에 요구 패키지 존재. Android applicationId와 생성된 iOS 번들의 식별자 com.dosaem.chosung 확인. iOS 빌드 성공 및 한국어 이름 번들 포함 확인. Hive/freezed 없음. |
| Firebase gitignore·example·부재 시 초기화 스킵·analyze/test | 충족 | 실제 설정 파일 두 개가 없는 상태에서 analyze/test와 양 플랫폼 빌드 통과. git check-ignore 적용, example 자리표시자, Gradle 조건부 적용과 초기화 실패 처리 확인. 네이티브 런타임 실행은 검증 범위 밖이다. |
| ApiClient 3메서드·Dio·Fake·API_BASE_URL·예외 골격 | 충족 | createGuest/fetchConfig/fetchMyStats만 정의. 서버 응답과 모델, JSON 본문·인증 헤더·예외 테스트 대조. 동일 클라이언트의 토큰 교체 전후 요청 헤더 검증도 추가되어 통과. |
| secure storage·en 게스트·401 재발급·전역 Provider | 충족 | SecureGuestTokenStore와 전역 guestTokenProvider 확인. 복원/발급/영어/401 후 1회 재발급/두 번째 401 전파 테스트 통과. 기기 언어 Provider는 PlatformDispatcher.locale을 읽는다. |
| OVERRIDES 테마·Pretendard·Lucide·그림자 없음·600px | 충족 | AppColors 라이트/다크 값과 OVERRIDES 대조, 번들 폰트·OFL·Lucide·투명 그림자 및 600px 래퍼 확인. 시스템 다크 모드·테마·폭 위젯 테스트 통과. |
| S7 점검/업데이트/정상 분기와 위젯 테스트 | 충족 | Fake config로 세 화면과 스토어 버튼 호출 검증. 초기화 후 startLocale=null인 앱 트리도 HomeShell에 진입해 D-22-1 경로가 해소됨. |
| 3탭 뼈대·탭 아래 배너 슬롯 | 충족 | HomeShell의 StatefulShellRoute 3탭, NavigationBar 아래 AdBannerSlot, SafeArea 및 50px 예약 높이 확인. 탭 전환·슬롯 테스트 통과. |
| ubuntu-latest CI·analyze 0건·audit.native 기록 | 충족 | CI analyze/test 잡 존재, 직접 analyze 0건. audit.native 15/20 기록 존재하며 토큰·접근성·레이아웃 테스트와 대조. 실기기 시각 검수 완료를 뜻하지 않는다. |
| README 상태 흐름·SDK 선택·테스트 경계 문단 | 충족 | README ### 22.에 세 문단 존재. 국제화 초기화와 iOS 15.0 의존성 근거도 현재 구현과 일치한다. |

### 이전 결함 재판정

#### D-22-1 — FIXED (이전 BLOCKER)

- 위치: `mobile/lib/main.dart:10`, `mobile/lib/main.dart:24`, `mobile/lib/l10n/localization_bootstrap.dart:8`.
- 재현/확인: mobile/에서 `flutter test --no-pub` 실행. `test/l10n/localization_bootstrap_test.dart`의 실제 국제화 초기화 후 startLocale 없는 생성 경로와 초기화 순서 테스트, `test/app_startup_branch_test.dart:256`의 locale=null 홈 진입 테스트를 직접 확인했다.
- 기대: 기기 언어 초기화 후 앱 트리가 생성되어 LateInitializationError 없이 홈 진입. 실제: 위 테스트 모두 통과하며 main은 bootstrapChosungApp을 호출하고 Firebase → initializeLocalization → runApp 순서를 await한다.
- 초기화를 호출하지 않는 라운드 1의 단독 위젯 스니펫은 수정된 main의 실행 경로가 아니다. 이번 판정은 실제 초기화 함수와 강제 언어 없는 앱 트리를 검증한 결과다. 저장소만 플랫폼 경계에서 대체하며 국제화 초기화 자체를 전부 mock으로 우회하지 않는다.

#### D-22-2 — FIXED (이전 MAJOR)

- 위치: `mobile/ios/Podfile:4`, `mobile/ios/Runner.xcodeproj/project.pbxproj:362` (동일 설정 :489, :540), `mobile/ios/Flutter/AppFrameworkInfo.plist:24`.
- 재현/확인: 설정 세 곳을 직접 읽고, mobile/ 복사본에서 `flutter build ios --no-codesign --debug --no-pub` 실행. 원본 설정 변경을 피하려고 `/tmp/t22-review-mobile`에서 CocoaPods/Xcode를 실행했다.
- 기대: Firebase iOS 15.0 요구치를 만족해 pod install과 Xcode 빌드 성공. 실제: pod install 2.5초, Xcode 69.7초, exit 0으로 Runner.app 생성. 생성 번들의 MinimumOSVersion도 15.0이다.
- 새 설정 테스트는 파일 값 일치와 설치된 podspec 요구치를 검사한다. 이번에는 그 정적 테스트뿐 아니라 실제 네이티브 빌드로도 확인했다.

#### D-22-3 — FIXED (이전 MINOR)

- 위치: `mobile/ios/Runner.xcodeproj/project.pbxproj:13`, `:59`, `:223`, `:300`; `mobile/ios/Runner/ko.lproj/InfoPlist.strings:3`.
- 재현/확인: 위 iOS 빌드 후 `plutil -p /tmp/t22-review-mobile/build/ios/iphoneos/Runner.app/ko.lproj/InfoPlist.strings` 실행.
- 기대: 한국어 이름 리소스가 Runner 번들에 포함됨. 실제: 파일 존재, CFBundleDisplayName과 CFBundleName 모두 "오늘의 초성". PBXFileReference → PBXVariantGroup → PBXBuildFile → Resources 연결과 knownRegions의 ko도 확인했다.
- 한국어 기기의 홈 화면을 직접 캡처한 것은 아니지만, 이전 결함인 번들 리소스 누락은 실제 산출물에서 해소됐다.

### 직접 실행한 검증

| 명령 / 검사 | 결과 |
|---|---|
| mobile/ `flutter analyze` | exit 0, No issues found (3.4초) |
| mobile/ `dart format --output=none --set-exit-if-changed .` | exit 0, 47 files / 0 changed; 비수정 모드 사용 |
| mobile/ `flutter test --no-pub` | exit 0, 87 passed |
| 루트 `uv run ruff check .` | exit 0, All checks passed |
| mobile/ `JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug --no-pub` | exit 0, APK 생성 (13.1초) |
| mobile/ 복사본 `flutter build ios --no-codesign --debug --no-pub` | exit 0, Runner.app 생성, 한국어 리소스 및 iOS 15.0 확인 |
| `plutil -lint mobile/ios/Runner.xcodeproj/project.pbxproj` | OK |
| 전용 테스트 자원으로 `uv run pytest -q` | exit 0, 684 passed in 552.41s (9분 12초); 실패·skip 0건 |
| `uv run flask db heads` | `dae1b5af0cf7 (head)` 1줄. 이 티켓의 새 마이그레이션은 없음 |
| `git diff --check` | exit 0 |

백엔드 테스트는 `TEST_DATABASE_URL`에 로컬 기존 `chosung_daily_test_t22`, `TEST_REDIS_URL`에 로컬 Redis DB 10, `TEST_MIGRATION_DATABASE_URL`에 기존 `chosung_daily_test_t22_migrations`를 지정했다. 접속 정보 값은 문서에 기록하지 않는다. DB 생성이나 공용 DB fallback은 하지 않았다.

### 보안·범위·검증 한계

- 추적 Firebase 파일은 example만 있으며 실제 설정 두 개는 부재·ignore 대상이다. 추적 파일에서 실제 설정 파일·서명 키·keystore·key.properties는 발견하지 못했다. 토큰 저장은 secure storage이고 요청 시 전역 Provider 값을 읽는다. 서버 인증·CSRF·DB 쓰기 구현 변경은 없으며 새 데이터 손상 경로는 발견하지 못했다.
- 공유 파일의 README 설계 판단과 RELEASE는 자기 번호 ### 22. 절만 추가/수정했다. README API 표, .env.example, 스펙 미정 항목 변경은 없다. 기술 스택 한 줄과 PRODUCT Platform 메모는 라운드 1에서 이미 확인한 범위이며 다른 티켓 행/절을 덮어쓰지 않았다.
- API·저장소·플랫폼 버전·스토어 실행 경계를 대체한 테스트는 분기와 상태 변경을 실제 코드로 검증한다. 네이티브 Firebase 초기화 실패 처리, Keychain/Keystore 저장, 기기 언어 변경 후 재실행은 실제 기기에서 확인하지 않았다. 빌드 성공을 실제 앱 실행 성공으로 확대 해석하지 않는다.
- 실기기 설치·시뮬레이터 캡처 및 audit.native의 시각 검수는 수행하지 않았다. 후속 티켓 32·34 범위라는 기존 한계를 유지한다. 네이티브 빌드 미실행이라는 이전 한계는 이번 검증으로 해소했다.
- 프로덕션·NAS·배포·외부 서비스 계정·push에 접근하지 않았다. 원본 애플리케이션·테스트·설정·.scratch는 수정하지 않았고, 리뷰 문서만 변경한다.

판정: PASS
