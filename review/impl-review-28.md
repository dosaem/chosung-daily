# 티켓 28 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `34ec7ec`, 구현 HEAD = `9acd950`. `git log main..HEAD` 7개 커밋과 `git diff main...HEAD`를 검토했다. `origin/main`은 사용하지 않았다.
- 확인 자료: 티켓 28, 스펙 §B.21·US 33/35/46/47·검증/디자인 부족 항목, `CONTEXT.md`, `design/SCREENS.md` S6/T0, `design-system/hidden-vowels/OVERRIDES.md`, `review/impl-evidence-28.md`.
- 코드·테스트·설정은 수정하지 않았다. 아래 결과는 구현 증거를 인용한 통과 선언이 아니라 리뷰 중 직접 실행/열람한 결과다.

## 체크박스별 충족 여부

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 3장 페이지뷰·언어 칩 PATCH /me·로컬 완료 플래그·설정 재진입 시 플래그 유지 | 충족 | `onboarding_pages.dart`, `onboarding_store.dart`, `onboarding_screen.dart`, `records_tab.dart` 및 `puzzle_language_controller.dart`의 실제 호출 경로 확인. 화면 테스트가 칩 선택 후 API 인자와 예시 타일, 완료 후 홈 이동, 다시 보기의 저장 횟수 0을 검증한다. 실제 저장 구현은 `SharedPreferencesAsync`를 사용한다. |
| 알림 사전 안내 후 Android 13+/iOS OS 요청·결과 상태 보관 | 미충족 | UI 요청 순서와 provider 결과 보관은 구현됐지만 새 Android 플러그인의 필수 Gradle 설정이 누락됐다(D-28-1). Android 앱으로 제공할 수 있는 네이티브 통합이 완성되지 않았다. |
| iOS ATT 사전 안내·프롬프트·결과 보관, Android 생략 | 충족 | `tracking_permission.dart`에서 ATT 플러그인 호출 및 상태 갱신, Android 조기 반환 확인. plist 및 한국어 문자열의 Xcode 리소스 연결 확인. 화면 테스트에서 안내 진입 시 요청 0회, 계속 후 요청 1회와 상태 반영을 확인한다. 실제 OS 다이얼로그는 미검증이다. |
| 태블릿 ReadingWidth 600 중앙·동일 타일/삽화 크기·1024 가로 스와이프/언어 칩 테스트 | 충족 | `ReadingWidth`와 고정 타일 크기 경로 확인. `onboarding_tablet_test.dart` 5개와 1024 골든이 전체 테스트에서 통과했다. 이미지에서도 rail 없이 중앙 배치됨을 확인했다. |
| 위젯 테스트·audit.native(태블릿 포함)·e6 목업 대비 기록 | 증거 부족 | 요청된 주요 위젯 흐름과 골든 테스트는 통과했고 e6/폰/태블릿 이미지를 직접 비교했다. 그러나 S6의 744/1366 폭은 직접 검증하지 않고 별도 셸 테스트로 대체했으며, 셸 밖인 S6의 검증 증거와 같지 않다. 네이티브 적합성 통과 주장에는 D-28-1도 누락돼 있다. |

## 직접 실행한 검증

| 명령/범위 | 결과 |
|---|---|
| `cd mobile && flutter test` | **392 passed**, exit 0 (약 17초). 골든 5장 포함. |
| `cd mobile && flutter analyze` | **No issues found**, exit 0. |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | **121 files, 0 changed**, exit 0. |
| `uv run ruff check .` | **All checks passed**, exit 0. |
| `uv run pytest -q` | **1403 passed in 863.10s (14분 23초)**, exit 0. 첫 실행 통과, 재실행 불필요. |
| `git diff --check main...HEAD` | exit 0. |
| Android `gradle :app:checkDebugAarMetadata --offline` | exit 1. 로컬 캐시에 `androidx.media:media:1.1.0` AAR가 없어 의존성 해석에서 중단. 네트워크로 받거나 외부 서비스를 호출하지 않았다. |

백엔드 테스트는 기존 전용 DB `chosung_daily_test_t28`, 기존 마이그레이션 테스트 DB `chosung_daily_test_t28_migrations`, Redis DB 2를 `TEST_DATABASE_URL`/`TEST_MIGRATION_DATABASE_URL`/`TEST_REDIS_URL`로 지정했다. 접속 문자열의 계정·비밀번호는 이 문서에 기록하지 않는다. 새 DB 생성이나 기본 DB fallback은 하지 않았다. 이 티켓에 마이그레이션 변경은 없다.

Android 검사는 프로젝트가 지정한 로컬 Gradle 8.14 실행 파일과 JDK 17을 사용했다(체크아웃에 `gradlew`가 없어 설치된 동일 버전을 사용). 위 실패를 desugaring 오류가 직접 출력된 것으로 해석하지 않았다. D-28-1은 아래의 실제 생성 메타데이터와 앱 설정 불일치로 확인했다.

## 결함

### D-28-1 — MAJOR — 알림 플러그인을 추가하면서 필수 Android desugaring 설정 누락

- 위치: `mobile/pubspec.yaml:21`; 누락된 통합 위치 `mobile/android/app/build.gradle.kts:25`.
- 내용: 새로 추가한 `flutter_local_notifications` 22.3.2는 알림 예약을 사용하지 않더라도 앱에서 core library desugaring을 활성화해야 한다. 앱의 `compileOptions`에는 Java 17만 있고 `isCoreLibraryDesugaringEnabled` 및 `coreLibraryDesugaring` 의존성이 모두 없다. Java 언어 수준 17만 지정하는 것은 라이브러리 desugaring 활성화가 아니다.
- 직접 확인: 설치된 **정확한 버전**의 패키지 README `Android Setup / Gradle setup`과 `android/build.gradle`을 읽었다. 리뷰의 Gradle 실행이 생성한 `mobile/build/flutter_local_notifications/intermediates/aar_metadata/debug/writeDebugAarMetadata/aar-metadata.properties`에는 `coreLibraryDesugaringEnabled=true`, `desugarJdkLib=com.android.tools:desugar_jdk_libs:2.1.4`가 기록돼 있다.
- 재현: `rg -n 'coreLibraryDesugaring' mobile/android` → 일치 없음. 위 AAR 메타데이터를 읽으면 활성화 요구가 확인된다. 의존성이 캐시된 환경에서 `cd mobile/android && gradle :app:checkDebugAarMetadata --offline` 또는 정상 APK 빌드를 수행한다.
- 기대: 소비 앱이 라이브러리의 desugaring 요구를 충족하고 Android 빌드가 통과하여 온보딩 알림 권한 요청을 실행할 수 있어야 한다.
- 실제: 앱 설정이 라이브러리 요구를 충족하지 않아 Android 빌드 검증에 걸리는 구성이다. 이 환경의 전체 Gradle 검사는 별도의 캐시 누락에서 먼저 멈췄으므로 정확한 최종 Gradle 오류 로그는 확보하지 못했다.
- 영향/검증 누락: Android 앱 전체의 빌드 가능성에 영향을 준다. `native_permissions_test.dart`는 매니페스트 문자열만 확인하고, provider/화면 테스트는 실제 권한 requester를 fake로 치환하므로 392개 테스트 통과로 이 통합 결함을 발견할 수 없다. 새 의존성 도입 티켓에서 필수 설정을 함께 완성해야 하며 알림 예약 티켓 30이나 빌드 티켓 34로 미룰 수 없다.

## 보안·범위·공유 파일 점검

- 인증/CSRF/서버 입력 검증 경로, 서버 DB 모델 및 마이그레이션 변경은 없다. 언어 변경은 기존 인증 API 클라이언트를 사용한다. 완료 플래그만 일반 로컬 설정에 저장하며 게스트 토큰 저장 방식을 바꾸지 않는다.
- README는 설계 판단 끝에 자기 번호 `### 28.`만 추가했다. `.env.example`, `docs/RELEASE.md`, `.scratch/`, 서버/웹 파일은 변경하지 않았다. 범위 밖 기능 추가나 다른 티켓의 공유 문서 절 덮어쓰기는 발견하지 못했다.
- 구현 증거 237/239행에는 로컬 테스트 DB 인증값이 포함된 URL이 있다. 기존 `.env.example`의 공개 개발 기본값과 같고 운영 시크릿 유출 증거는 아니다. 리뷰에는 값을 옮기지 않았다.

## 참고 및 검증 한계

- UMP/광고 초기화와 알림 예약은 각각 티켓 31/30 범위이므로 이 티켓의 누락 결함으로 세지 않았다. 메모리 권한 상태가 앱 재시작 시 초기화되는 점은 문서화된 후속 티켓 계약이다.
- e6 목업과 첫 장 골든의 구성 순서는 일치한다. 타일 테두리 대신 면을 쓰는 변경은 우선순위가 높은 OVERRIDES에 부합한다. 다크/알림/ATT 골든과 1.3배 글자 테스트도 통과했다.
- 실기기 권한 다이얼로그, 실제 저장소를 통한 프로세스 재시작, iOS 네이티브 빌드는 실행하지 않았다. 주요 UI 테스트의 fake 경계는 합리적이지만 해당 네이티브 동작 자체를 증명하지는 않는다.
- 취향·스타일 제안은 결함 수에 포함하지 않았다.

결함 합계: BLOCKER 0 / MAJOR 1 / MINOR 0.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` = `34ec7ec`, 구현 HEAD = `2320a52`. `git log main..HEAD` 10개 커밋 및 `git diff main...HEAD` 전체 변경을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 28, 스펙 §B.21·US 33/35/46/47·검증·디자인 부족 항목, `CONTEXT.md`, SCREENS S6/T0, OVERRIDES, 구현 증거의 수정 라운드 1과 이전 리뷰를 대조했다.
- 코드·테스트·설정·`.scratch/`는 수정하지 않았다. 리뷰 문서만 추가했다.

### 체크박스별 충족 여부

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| S6 3장·언어 칩 PATCH /me·로컬 완료 플래그·S4 재진입 시 플래그 유지 | 충족 | `onboarding_pages.dart`의 기본 3장, 화면의 언어 변경 → `PuzzleLanguageNotifier.change` → 인증된 `DioApiClient.updatePuzzleLanguage` PATCH 경로를 확인했다. `PreferencesOnboardingStore`는 실제 `SharedPreferencesAsync`를 사용한다. 화면 테스트가 언어 요청 인자·예시 변경·완료 후 홈·기존 플래그의 홈 직행·다시 보기의 쓰기 0회를 검증한다. |
| 알림 사전 안내 → Android 13+/iOS 권한 요청·상태 보관 | 충족 | 안내 진입 시 요청 0회, 버튼 입력 후 요청 1회와 granted/denied 상태를 테스트로 확인했다. 실제 requester의 플랫폼 API 호출과 매니페스트를 읽었고, 설치된 플러그인의 Android/iOS 네이티브 구현에서 OS 권한 요청으로 연결됨을 확인했다. Android 네이티브 구성 결함 D-28-1은 FIXED. |
| iOS ATT 안내·프롬프트·상태 보관, Android 생략 | 충족 | iOS 네 번째 장과 `AppTrackingTransparency.requestTrackingAuthorization()` 호출, 상태 갱신, plist의 설명 문구를 확인했다. Android 3장 종료 및 ATT 요청 0회, iOS 안내 후 요청·결과 보관 테스트가 통과했다. |
| 태블릿 ReadingWidth 600 중앙·폰과 같은 타일/삽화 크기·1024 스와이프/언어 칩 | 충족 | `ReadingWidth`의 Center/최대 600 제약과 고정 타일·아이콘 크기를 확인했다. 태블릿 테스트 5개가 전체 실행에서 통과했고, 1024 골든을 직접 열어 rail 없는 중앙 배치를 확인했다. |
| 주요 위젯 테스트·audit.native(태블릿 포함)·e6 목업 대비 기록 | 증거 부족 | 지정된 위젯 흐름과 골든 5개는 통과했다. e6 원본과 390/1024 골든을 직접 대조했고 구성 순서 및 OVERRIDES 우선 적용을 확인했다. 다만 이전 리뷰처럼 744·1366의 S6 직접 검증은 없고, 구현 증거가 인용한 셸 테스트는 셸 밖 S6 검증을 대신하지 못한다. 이 제한은 라운드 1과 동일하며 새 런타임 결함으로 확인된 것은 아니다. |

### 이전 결함 재판정

#### D-28-1 — FIXED — 기존 MAJOR: Android core library desugaring 설정 누락

- 위치: `mobile/android/app/build.gradle.kts:31`, `mobile/android/app/build.gradle.kts:87`; 회귀 검사 `mobile/test/config/android_desugaring_test.dart:39`.
- 수정 확인: `compileOptions`에 `isCoreLibraryDesugaringEnabled = true`, `dependencies`에 `desugar_jdk_libs:2.1.4`가 함께 선언돼 있다. 설치된 `flutter_local_notifications` 22.3.2의 Gradle 요구와 일치한다.
- 재현/검증: `cd mobile/android`에서 JDK 17과 프로젝트 지정 Gradle 8.14로 `:app:checkDebugAarMetadata --offline` 실행 → 기대: 소비 앱의 desugaring 요구 충족 및 성공 / 실제: **BUILD SUCCESSFUL in 13s**, 19 tasks executed, exit 0.
- 새 Dart 테스트도 전체 393개 실행에서 통과했다. 텍스트 검사만으로 네이티브 통합 성공을 단정하지 않고 실제 AGP 검사 성공을 함께 확인했다.
- 최초 PATH의 Gradle 9.5.1 실행은 Kotlin DSL 플러그인 6.5.7의 오프라인 해석 실패로 중단됐다. wrapper 설정의 8.14와 달랐으므로 설치된 정확한 8.14 실행 파일로 다시 검증했다. 앱 파일 변경 없이 성공했고, 최초 환경 오류를 REPEAT로 세지 않았다.

### 신규 결함

없음. 미해결 BLOCKER 0 / MAJOR 0 / MINOR 0. 기존 D-28-1은 FIXED, REPEAT는 없다.

### 범위·보안·검증 한계

- README는 설계 판단 절 끝에 자기 번호 `### 28.`만 추가했다. `.env.example`, `docs/RELEASE.md`, 스펙, 백엔드·웹·마이그레이션 변경은 없다. 티켓 범위 밖 기능 변경이나 다른 번호의 공유 문서 수정은 확인되지 않았다.
- 언어 선택은 기존 Bearer 인증 PATCH 경로를 사용하며 새 서버 인증/CSRF 경계를 만들지 않는다. 완료 플래그는 비밀이 아닌 bool이고 게스트 토큰 저장소와 분리돼 있다. 새 운영 키·토큰 노출이나 데이터 손상 경로는 확인되지 않았다. 구현 증거의 DB 접속 예시는 로컬 테스트 자원용이며 리뷰에는 계정·비밀번호 값을 옮기지 않았다.
- API·저장소·OS requester만 fake로 교체하고 실제 화면·라우팅·provider를 실행하는 테스트 구조는 요구 흐름을 검증한다. 다만 실제 OS 다이얼로그, 실제 저장소를 통한 프로세스 재시작, iOS 네이티브 빌드는 이번에도 검증하지 않았다. Android 검증도 AAR 메타데이터 검사까지이며 구현자의 전체 APK 성공 주장을 리뷰에서 독립 재현했다고 적지 않는다.
- 알림 예약·시작 시 권한 재조회와 UMP/광고 초기화는 티켓 30/31의 후속 범위다. 디자인 취향·스타일 제안은 결함으로 세지 않았다.

### 직접 실행한 검증

| 명령/범위 | 이번 리뷰 결과 |
|---|---|
| `cd mobile && flutter test` | **393 passed**, exit 0, 약 39초. 골든 5장과 새 desugaring 검사 포함. |
| `cd mobile && flutter analyze` | **No issues found**, exit 0. |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | **122 files, 0 changed**, exit 0. |
| `uv run ruff check .` | **All checks passed**, exit 0. |
| 테스트용 환경변수 지정 후 `uv run pytest -q` | **1403 passed in 907.72s (15분 7초)**, exit 0. 첫 실행 통과, 재실행 불필요. |
| JDK 17 + Gradle 8.14 `:app:checkDebugAarMetadata --offline` | **BUILD SUCCESSFUL**, exit 0. |
| `git diff --check main...HEAD` 및 리뷰 변경 `git diff --check` | exit 0. |

백엔드 테스트는 구현 증거의 접속 형식을 읽어 `TEST_DATABASE_URL`에 기존 `chosung_daily_test_t28`, `TEST_MIGRATION_DATABASE_URL`에 기존 `chosung_daily_test_t28_migrations`, `TEST_REDIS_URL`에 로컬 Redis DB 2를 지정했다. 새 DB 생성이나 기본 테스트 DB fallback은 하지 않았다. 이 티켓에는 마이그레이션 변경이 없으므로 조건부 `flask db heads` 검사는 해당하지 않는다.

Gradle 실행 파일은 wrapper 설정과 같은 로컬 `~/.gradle/wrapper/dists/gradle-8.14-all/c2qonpi39x1mddn7hk5gh9iqj/gradle-8.14/bin/gradle`을 사용했다. 프로덕션/NAS 접근, 배포, 실제 계정·결제·인증 서비스 호출은 하지 않았다.

결함 합계(미해결): BLOCKER 0 / MAJOR 0 / MINOR 0. 기존 결함: FIXED 1 / REPEAT 0.

판정: PASS
