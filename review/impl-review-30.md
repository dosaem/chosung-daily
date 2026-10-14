# 티켓 30 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` `8ddc8fd` → 구현 `HEAD` `e43dc5a` (`git diff main...HEAD`, `git log main..HEAD`). `origin/main`은 사용하지 않았다.
- 확인: 티켓 30 전체 체크박스, 스펙 §A.9·US 35~40·미정 6, 구현 증거 문서, SCREENS S4/T4, hidden-vowels OVERRIDES, `e4_records.png`, 변경 코드·테스트·골든.
- 결함: **BLOCKER 0 / MAJOR 3 / MINOR 0**. 앱·테스트·설정·스펙 파일은 수정하지 않았다. 재현용 코드는 `/tmp`에서만 실행했다.

## 체크박스별 결과

| 티켓 체크박스 | 결과 | 직접 확인한 근거 |
|---|---|---|
| 예약 계획 순수 함수: 일일 고정 ID 반복, 7일 1회성, KST 완료 제외·동시각 제외·최대 8개 | 충족 | `notification_plan.dart`의 `planNotifications`는 입력만으로 계획을 만든다. 기기 시간대는 `now.location`에 포함된다. scheduler가 daily에만 `DateTimeComponents.time`을 지정한다. 계획 테스트 17건을 포함한 전체 Flutter 테스트 통과. |
| 단위 테스트: 오늘 제외·내일 유지·미주 KST 경계·두 언어·롤링·최대 개수·시간대 변경 | 충족 | 순수 계획 테스트가 실제 함수를 호출하여 해당 경우를 검증한다. 다만 컨트롤러의 시간대 변경 테스트는 내부 계획만 확인해 OS 예약 누락을 놓친다(D-30-1). |
| 여섯 사건 구독·OS diff·Android inexact·exact 권한 제외·로컬 존·28 권한 사용 | 미충족 | `notification_controller.dart`에서 사건 구독, 권한 조회, 직렬 동기화는 확인했다. Android manifest의 리시버·권한도 확인했다. 하지만 시간대 변경 후 동일 ID의 기존 리마인더를 갱신하지 않으며(D-30-1), 시작 중 완료 날짜를 잃을 수 있다(D-30-3). |
| 알림 탭 cold/warm → 오늘 탭 + 최신 퍼즐 재조회 | 미충족 | Dart 스트림에서 router/refresh로 이어지는 경로와 위젯 테스트는 통과한다. iOS 네이티브 notification center delegate가 연결되지 않아 실제 OS 탭이 그 스트림에 도달하지 않는다(D-30-2). |
| S4 시각 picker·스위치·권한 안내·시스템 설정·태블릿 열·폭 744 adaptive sheet·audit.native·목업 대비 | 미충족 | `records_notifications_test.dart` 10건 포함 전체 테스트 통과. 설정 변경이 저장소와 scheduler까지 반영되고, 폭 744 picker가 Dialog가 되는 것을 검증한다. 390 권한 거부 골든과 1024 골든을 직접 열어 목업/SCREENS와 비교했다. 토큰·헤어라인·설정 열 배치가 유지된다. 접근성 추가 점검에서 스위치 semantics에 `리마인더` 라벨과 토글 상태가 함께 포함됨을 확인했다. UI 조작·배치·접근성 부분은 충족하나, iOS 플랫폼 배선 D-30-2 때문에 구현 증거의 native audit 전체 통과 주장은 수용하지 않는다. |
| iOS·Android 사람 실행 체크리스트·README 로컬 알림 근거 | 충족 | RELEASE의 자기 번호 `### 30.`에 당일 취소·다음 날 유지·cold/warm·권한·재부팅·시간대 항목이 있다. README 자기 번호 `### 30.`에 서버 푸시 대신 로컬 예약을 고른 이유와 한계를 적었다. 실기기 실행 자체는 티켓이 사람에게 맡긴 항목이므로 수행했다고 간주하지 않았다. |

## 결함

### D-30-1 — 시간대 변경 후 기존 리마인더가 이전 시간대로 남음

- **심각도: MAJOR**
- 위치: `mobile/lib/notifications/notification_sync.dart:38` (특히 41~42), `mobile/lib/notifications/notification_controller.dart:104`.
- 요구: 스펙 §A.9·티켓 세 번째 체크박스의 복귀 시 기기 시간대 재계산 및 원하는 `(id, 발화 시각)` 집합으로 OS 동기화.
- 재현 입력: 완료 날짜 없음, 기본 설정, 서울에서 7일치 예약 → 기기 시간대를 `America/New_York`로 바꾸고 foreground resume. 기존 `FakeNotificationScheduler`에서 `scheduled` 로그만 비운 뒤 resume하고, 새 계획 중 기존 ID와 같지만 `when`이 달라진 리마인더가 실제 `schedule` 호출에도 포함되는지 검사했다.
- 기대: 날짜 ID가 같아도 발화 순간/시간대가 바뀐 리마인더는 새 로컬 20:00으로 갱신된다.
- 실제: 새 계획에는 뉴욕 20:00이 있지만 겹치는 ID는 전부 skip된다. 직접 실행 결과 변경 대상 ID는 `[20261015, 20261016, 20261017, 20261018, 20261019, 20261020]`인데 실제 예약 호출 ID는 `[20261014, 1]`뿐이었다. 10/15 서울 20:00 예약은 뉴욕 10/15 07:00에 해당하므로, 다음 실행의 내부 계획이 맞아도 사용자에게는 잘못된 시각에 알림이 온다. 그 예약의 실제 KST 날짜와 새 계획의 KST 날짜도 달라져 완료 취소 판정까지 어긋날 수 있다.
- 원인: diff가 `pendingIds`만 받고 reminder는 ID 유무만 비교한다. 같은 로컬 날짜 ID라도 시간대가 바뀌면 발화 순간이 같다는 보장은 없다. 설치된 plugin native source도 iOS trigger에 명시적 `NSCalendarUnitTimeZone`을 넣고 Android는 지정 zone을 epoch millis로 변환하므로, 기존 예약이 새 기기 시간대로 자동 교체되지는 않는다.
- 검증 공백: `notification_controller_test.dart:346`의 복귀 테스트는 `notificationSyncProvider`의 `when.location.name`만 확인한다. 실제 scheduler에 전달된 변경은 확인하지 않는다.
- 직접 실행: `cd mobile && flutter test /tmp/t30-review-repro_test.dart --plain-name review --reporter expanded`의 `review timezone must update scheduled reminders`가 해당 기대값에서 실패했다.

### D-30-2 — iOS notification center delegate 미등록으로 실제 알림 탭이 전달되지 않음

- **심각도: MAJOR**
- 위치: `mobile/lib/notifications/notification_bootstrap.dart:118`, 누락된 네이티브 연결 위치 `mobile/ios/Runner/AppDelegate.swift:10`.
- 요구: US 40, 스펙 §A.9, 티켓 네 번째 체크박스의 실제 OS 알림 탭 cold/warm 처리.
- 재현 입력: iOS에서 알림 허용·예약 → 내 기록 탭을 띄운 상태로 백그라운드 이동 → 도착한 로컬 알림을 탭한다. 종료 상태 launch 정보도 같은 delegate 경로를 확인해야 한다.
- 기대: OS의 `didReceiveNotificationResponse`가 Flutter plugin에 전달되어 Dart callback → 오늘 탭 이동·퍼즐 재조회가 실행된다.
- 실제 확인: AppDelegate에는 plugin 등록과 `super.application` 호출만 있고 `UNUserNotificationCenter.current().delegate` 설정이 전혀 없다. 고정된 의존성 `flutter_local_notifications 22.3.2`의 로컬 README **iOS setup / General setup**은 AppDelegate에서 이 delegate 연결을 요구한다. 같은 버전 native source의 `registerWithRegistrar`는 Flutter application delegate 목록에만 plugin을 추가하며 notification center delegate를 설정하지 않는다. `didReceiveNotificationResponse`에서만 warm callback 또는 `_launchingAppFromNotification = true`를 설정한다. 설치된 Flutter engine의 `FlutterAppDelegate.mm` 역시 전달 메서드만 구현하며 center delegate를 스스로 등록하지 않는다. 따라서 현재 앱에서는 OS 응답이 그 전달 경로에 연결되지 않아 warm 탭 시 이전 탭이 유지되고 cold launch 판별도 누락된다.
- 직접 확인 명령: `rg -n 'UNUserNotificationCenter|delegate' mobile/ios/Runner/AppDelegate.swift`는 매치 없음. 로컬 pub cache의 해당 버전 README 469~483행과 plugin native source 145~159·1112~1134행, Flutter engine AppDelegate의 초기화·launch·응답 전달 코드를 대조했다.
- 검증 범위: 실기기 탭을 실행한 결과가 아니라 **앱과 실제 설치된 고정 버전 native source의 배선 검토**로 확인한 결함이다. Dart 위젯 테스트는 `NotificationTaps.add()` 또는 `launchedByNotification: true`를 직접 주입하므로 이 누락을 검증하지 않는다. 선행 티켓에서 권한만 추가했더라도 실제 예약/탭을 활성화하는 이번 티켓에서 연결해야 하는 경로다.

### D-30-3 — 시작 시 늦게 완료된 저장소 읽기가 새 완료 날짜를 덮어씀

- **심각도: MAJOR**
- 위치: `mobile/lib/notifications/completed_puzzle_dates.dart:65`, `:85`, `:90` (특히 91·109).
- 요구: US 38·스펙 §A.9의 완료한 KST 날짜 리마인더 제외 및 퍼즐 완료 이벤트 동기화.
- 재현 입력: `CompletedPuzzleDateStore.read()`가 시작 시 빈 집합을 읽어 반환 대기 중인 상태에서, 오늘 API가 먼저 완료된 퍼즐을 반환하거나 완료 이벤트가 발생해 `markCompleted(today)`를 호출한다. write가 완료된 뒤 초기 read가 빈 집합을 반환하도록 `Completer<Set<String>>`로 순서를 고정했다. 실제 notifier/provider를 사용했고 저장소 경계만 지연시켰다.
- 기대: 최종 provider 상태에 오늘 완료 날짜가 남아 있고 해당 리마인더가 제외된다.
- 실제: `markCompleted` 직후 `{2026-10-15}` → 늦은 build 반환 직후 `{}`. 시작 read가 최신 완료를 덮어써 이 실행의 동기화가 완료한 날짜의 리마인더를 다시 예약할 수 있다. 오래된 날짜 정리 write까지 발생하면 저장소도 오래된 집합으로 덮어쓸 수 있다.
- 원인: 초기 build를 기다리지 않고 `state.value ?? {}`로 완료 처리를 시작하며, build의 비동기 read 결과와 새 상태를 조정하는 처리가 없다. 컨트롤러는 완료 날짜 초기 로드와 오늘 API 구독을 함께 시작하므로 두 결과의 도착 순서는 보장되지 않는다.
- 직접 실행: 같은 재현 파일의 `review delayed store read must preserve completion`에서 `expect(finalDates, contains(todayKey))`가 실패했다. 출력은 `before late read: {2026-10-15}`, `after late read: {}`다. 기존 메모리 저장소는 즉시 응답하므로 현재 테스트는 이 순서를 만들지 않는다.

## 직접 실행한 검증

| 명령/대상 | 결과 |
|---|---|
| `cd mobile && flutter test` | **458 passed**, 종료 코드 0, 34초. 기존 골든 비교 포함. |
| `cd mobile && flutter analyze` | **No issues found**, 종료 코드 0. |
| `uv run ruff check .` | **All checks passed**, 종료 코드 0. |
| `uv run flask db heads` | `b1c7d4e0a932 (head)` 한 줄. 이 티켓 자체는 마이그레이션 변경 없음. |
| 추가 경합·시간대 재현 | 실제 provider/controller를 쓰는 2건 모두 결함 기대값에서 실패(위 D-30-1·3). 제품 테스트 파일은 변경하지 않음. |
| 리마인더 switch semantics 별도 점검 | **1 passed**, 종료 코드 0. `리마인더` 라벨과 enabled/toggled 상태 확인. |
| 백엔드 전체 `uv run pytest -q` | **1403 passed in 1368.27s (0:22:48)**, 종료 코드 0. 지정 전용 DB/Redis로 첫 실행 통과; 기본 DB 대체·재실행 없음. |
| `cd mobile && flutter build apk --debug` | **성공**, 종료 코드 0, Gradle 136.1초. `app-debug.apk` 생성 확인 후 지시대로 `mobile/build` 삭제 완료. |

백엔드는 `TEST_DATABASE_URL`로 **로컬 `chosung_daily_test_t30`**, `TEST_REDIS_URL`로 **로컬 Redis DB 4**, `TEST_MIGRATION_DATABASE_URL`로 기존 **`chosung_daily_test_t30_migrations`**를 지정했다. 자격증명은 문서에 기록하지 않는다. 새 DB 생성이나 프로덕션/외부 서비스 접근은 하지 않았다. APK 빌드의 의존성 다운로드는 코디네이터가 추가 허용했다.

## 범위·보안·공유 파일 확인

- 백엔드·웹·마이그레이션 변경 없음. 알림 설정·기기 완료 날짜·권한 상태를 추가한 범위이며 인증/CSRF 경계를 변경하지 않았다.
- README/RELEASE는 자기 번호 `### 30.`만 추가했고, 스펙 미정 절은 `(티켓 30 반영)` 행을 절 끝에 추가했다. 다른 티켓 내용을 덮어쓰지 않았다.
- 변경 파일에서 실제 키·토큰·비밀번호의 추가 기록을 발견하지 않았다. 테스트의 guest 문자열은 가짜 입력이다.
- 데이터 측면의 결함은 완료 날짜 경합 D-30-3에 기록했다. 서버 퍼즐/계정 데이터 변형은 추가하지 않았다.

## 참고

- 30분 단위 시각 목록은 티켓이 분 단위 정밀도를 명시하지 않아 취향 결함으로 올리지 않았다. 목록 방식·보조 설명 줄·권한 안내 별도 행도 요구 범위에서 허용 가능한 구현이다.
- 7일 이후 리마인더 중단은 스펙이 수용한 한계다. 실기기 iOS/Android 실제 발화·재부팅 검증은 RELEASE의 사람 체크리스트로 남아 있으며 자동 테스트 통과로 대체할 수 없다.
- 기존 Flutter 테스트 통과와 별개로 네이티브 delegate 연결, OS에 전달한 시각, 비동기 초기 로드 경합까지 보장되지는 않는다.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` `8ddc8fd` → 구현 `HEAD` `0686472`. `git diff main...HEAD`, `git log main..HEAD` 전체와 이전 리뷰 이후 수정 diff를 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 30, 스펙 §A.9·US 35~40·미정 6, 구현 증거의 수정 라운드 1, SCREENS S4/T4, hidden-vowels OVERRIDES와 목업을 대조했다.
- 이전 결함 **FIXED 3 / REPEAT 0**, 신규 결함 **BLOCKER 0 / MAJOR 0 / MINOR 0**. 아래 FIXED 항목의 MAJOR는 이전 심각도이며 현재 미해결 결함 수에 포함하지 않는다.

### 체크박스별 결과

| 티켓 체크박스 | 결과 | 직접 확인한 근거 |
|---|---|---|
| 순수 예약 계획: 고정 ID 일일 반복 1개·7일 1회성·KST 완료 제외·동시각 제외·최대 8개 | 충족 | `notification_plan.dart`의 입력 기반 계획과 `notification_scheduler.dart:69`의 daily 전용 반복 설정을 확인했다. 전체 실행에 포함된 계획 테스트 17건이 KST 경계·7일 보충·상한을 검증한다. |
| 단위 테스트: 오늘 제외·내일 유지·미주 KST 경계·두 언어 중 하나 완료·롤링·상한·시간대 변경 | 충족 | 실제 순수 함수와 controller를 사용한다. 이번 시간대 회귀 테스트는 provider의 계획뿐 아니라 `scheduler.scheduled`에 새 시각의 예약 전체가 전달됐는지 검증한다. |
| 여섯 사건 구독·OS diff·Android inexact·exact 권한 제외·로컬 존·28 권한 사용 | 충족 | `notification_controller.dart`의 시작·resume·완료·탭·설정·guestToken 구독과 직렬 sync를 확인했다. pending payload의 UTC 발화 순간을 읽어 비교하므로 동일 ID의 시각 변경도 재예약된다(D-30-1 FIXED). 초기 완료 날짜 읽기 경합도 수정됐다(D-30-3 FIXED). Android manifest 리시버 및 exact 권한 미포함, scheduler의 `inexactAllowWhileIdle`을 확인했다. |
| cold/warm 알림 탭 → 오늘 탭·최신 퍼즐 재조회 | 충족 | bootstrap의 callback/launch details → controller의 router/refresh 경로와 탭 테스트를 확인했다. iOS delegate 연결을 설치된 plugin native source·Flutter header와 대조하고 AppDelegate를 타입체크했다(D-30-2 FIXED). 실제 기기 cold/warm 실행은 사람 체크리스트로 남는다. |
| S4 picker·스위치·권한 안내·설정 앱 열기·태블릿 열·폭 744 adaptive sheet·native audit·목업 대비 | 충족 | 화면 테스트 10건과 전체 골든 비교 통과. 390 권한 거부·1024 태블릿 골든을 직접 열어 e4_records 및 T4와 대조했다. 오른쪽 설정 열, 헤어라인, 색 토큰과 최소 터치 높이를 확인했고, 별도 semantics 실행에서 `리마인더` 라벨과 enabled/toggled 상태를 확인했다. 폭 744 picker는 기존 `showAdaptiveSheet`의 Dialog 경로를 검증한다. native audit의 접근성·플랫폼 배선·디자인 토큰·반응형 근거를 직접 점검했으며 실제 OS 발화까지 자동 검증했다고 간주하지 않는다. |
| iOS·Android 실기기 체크리스트와 README 로컬 알림 선택 근거 | 충족 | RELEASE `### 30.`에 당일 취소·다음 날 유지·cold/warm·권한·재부팅·시간대 변경 체크가 있다. README `### 30.`에 로컬 예약의 이유·한계와 수정한 payload diff·delegate·초기 read 순서가 적혀 있다. 사람의 실기기 실행 자체는 이 티켓의 자동 검증 범위가 아니다. |

### 이전 결함 재판정

#### D-30-1 — FIXED (이전 MAJOR)

- 위치: `mobile/lib/notifications/notification_sync.dart:45`, `mobile/lib/notifications/notification_scheduler.dart:31`, `:54`.
- 재현: `cd mobile && flutter test --no-pub test/notifications/notification_controller_test.dart test/notifications/notification_diff_test.dart`의 서울 예약 → 뉴욕 변경 → foreground resume 및 같은 ID/다른 발화 순간 테스트.
- 기대: 겹치는 날짜 ID도 새로운 로컬 20:00으로 OS 예약을 갱신한다. 실제: controller의 예약 호출 목록이 새 계획 전체를 포함하고, diff가 순간이 다르거나 불명인 리마인더를 재예약하는 테스트가 통과했다(전체 Flutter 실행에도 포함).
- 직접 확인: scheduler가 UTC ISO-8601 payload를 쓰고 읽으며, diff가 `isAtSameMomentAs`로 비교한다. 설치된 `flutter_local_notifications 22.3.2`의 Android `pendingNotificationRequests` 및 iOS 동일 메서드가 payload를 반환하는 코드도 확인했다. fake만 순간을 기억하고 실제 adapter는 잊는 구조가 아니다.

#### D-30-2 — FIXED (이전 MAJOR)

- 위치: `mobile/ios/Runner/AppDelegate.swift:20`.
- 재현/검증: iOS warm/cold 알림 탭의 OS 응답 전달 경로를 AppDelegate → Flutter application delegate → 설치된 plugin의 `didReceiveNotificationResponse`까지 대조했다. `test/config/ios_scheduled_notifications_test.dart` 2건과 탭 위젯 테스트가 전체 실행에서 통과했다.
- 기대: notification center delegate가 등록되어 OS 응답이 Dart callback 또는 launch 정보로 연결된다. 실제: launch 메서드 안의 `UNUserNotificationCenter.current().delegate = self`와 `import UserNotifications`를 확인했다. Flutter header의 상속된 protocol 채택과 plugin의 `addApplicationDelegate`, 초기화 여부에 따른 callback/launch 분기까지 확인했다.
- 독립 검증: `xcrun swiftc -typecheck`로 현재 AppDelegate를 설치된 iOS simulator Flutter framework에 대조하여 종료 코드 0을 확인했다. `/tmp`에 만든 GeneratedPluginRegistrant 대역은 등록 심볼만 제공한다. 따라서 이것은 AppDelegate 타입체크이며 전체 iOS 링크/실기기 탭 테스트를 대신하지 않는다.

#### D-30-3 — FIXED (이전 MAJOR)

- 위치: `mobile/lib/notifications/completed_puzzle_dates.dart:96`.
- 재현: `cd mobile && flutter test --no-pub test/notifications/completed_puzzle_dates_test.dart`의 시작 read를 Completer로 대기시킨 뒤 `markCompleted(today)` 호출 → 초기 read가 빈 집합을 반환하도록 해제.
- 기대: 최종 provider와 저장소에 오늘 완료 날짜가 남는다. 실제: 새 회귀 테스트가 두 값을 모두 `{todayKey}`로 확인하며 통과했다(전체 Flutter 실행에도 포함).
- 직접 확인: `await future`로 초기 build/read 및 정리 write가 끝난 후 현재 집합에 날짜를 더한다. 실제 notifier/provider를 사용하고 저장소 응답 시점만 지연시킨 테스트라 기존 덮어쓰기 순서를 검증한다.

### 신규 결함

없음.

### 범위·보안·공유 파일

- 앱 알림 기능 및 관련 UI·문서·테스트 범위다. `app/`, `web/`, `tests/`, `migrations/` 변경은 없다. 인증·CSRF 서버 경계를 변경하지 않았다.
- README/RELEASE는 자기 번호 `### 30.`만 추가했고 스펙 미정 절은 자기 티켓 행만 끝에 추가했다. 기존 다른 티켓 절을 덮어쓰지 않았다.
- diff에서 실제 키·토큰·비밀번호 추가 기록을 발견하지 않았다. 새 payload에는 발화 시각만 담기며 계정 식별자나 인증 정보는 넣지 않는다.
- 리뷰 작업은 이 파일만 변경한다. DB는 지정된 기존 로컬 테스트 자원을 사용하며 새 DB 생성·프로덕션 접근·배포·push는 하지 않았다.

### 참고

- 30분 단위 picker, 안내 문구의 별도 행, 아이콘 선택은 이번 요구 위반으로 올리지 않는다.
- 7일 이후 리마인더 중단은 명세가 허용한 한계다. 실기기 발화·재부팅·cold/warm 탭은 RELEASE의 사람 체크리스트에서 확인해야 한다.

### 직접 실행한 검증

| 명령/대상 | 이번 라운드 결과 |
|---|---|
| `cd mobile && flutter test` | **464 passed**, 종료 코드 0, 35초. 골든 비교 포함. |
| `cd mobile && flutter analyze` | **No issues found**, 종료 코드 0. |
| 수정 회귀 파일 4개 별도 실행 | controller 18 + diff 8 + 완료 날짜 4 + iOS 설정 2 = **32 passed**, 종료 코드 0. |
| `flutter test --no-pub /tmp/t30-review-semantics_test.dart --reporter expanded` | **1 passed**. 리마인더 switch의 라벨·enabled/toggled 상태 확인. |
| 실제 scheduler/plugin Dart → method channel payload 왕복 임시 테스트 | **1 passed**, 종료 코드 0. 뉴욕 예약의 UTC payload·zone 전달, pending에서 같은 순간 복구, 손상 payload의 null 처리 확인. OS 경계만 가짜로 했으며 실제 발화 검증은 아니다. 최초 실행의 plugin 미등록 오류는 임시 harness의 `registerWith()` 누락이었고 제품 결함이 아니었다. |
| iOS AppDelegate simulator Swift 타입체크 | **성공**, 종료 코드 0. 설치된 Flutter framework + `/tmp` GeneratedPluginRegistrant 대역 사용. 전체 iOS 빌드는 미실행. |
| `uv run ruff check .` | **All checks passed**, 종료 코드 0. |
| `uv run flask db heads` | `b1c7d4e0a932 (head)` **한 줄**, 종료 코드 0. 마이그레이션 변경 없음. |
| `git diff --check main...HEAD` 및 리뷰 문서 diff 검사 | 공백 오류 없음. |
| 백엔드 전체 `uv run pytest -q` | **1403 passed in 1988.04s (0:33:08)**, 종료 코드 0. 지정 전용 DB/Redis로 첫 실행 통과. |

백엔드 실행 시 `TEST_DATABASE_URL`은 기존 로컬 **chosung_daily_test_t30**, `TEST_REDIS_URL`은 로컬 **Redis DB 4**, `TEST_MIGRATION_DATABASE_URL`은 기존 로컬 **chosung_daily_test_t30_migrations**를 지정했다. 자격증명은 기록하지 않는다. 접속 성공으로 기본 DB 대체가 필요하지 않았고, 간헐 실패가 없어 재실행하지 않았다. 앱·테스트·설정·`.scratch/`는 수정하지 않았다.

판정: PASS
