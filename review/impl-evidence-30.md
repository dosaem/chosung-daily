# 티켓 30 구현 증거 — 로컬 알림(일일 반복·7일 리마인더·순수 예약 계획·KST 취소·탭 라우팅·S4 설정)

**브랜치:** `dosaem/t30-app-local-notifications` · **날짜:** 2026-10-15
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 30.` + `docs/RELEASE.md` `### 30.`
+ 스펙 "미정 항목" 에 미정 6 판단 재료 한 줄(공통 규칙대로 자기 행만).
백엔드·웹·마이그레이션은 한 줄도 건드리지 않았다(`app/`·`web/`·`migrations/` 변경 0건 —
§6.4 의 `git diff --stat` 참고).

## 0. 한 줄 요약

플레이어가 고른 로컬 시각(기본 09:00)에 매일 알림이 오고, 그 날(KST 퍼즐 날짜)을 아직 안
풀었으면 20:00 리마인더가 한 번 더 온다. 예약 계획은 **입력 4개짜리 순수 함수**이고 실제
예약은 OS 대기 목록과 **ID diff** 로만 바꾼다. 앱 테스트 458개 통과(이 티켓이 더한 건 64개,
골든 1장 추가·2장 갱신), `flutter analyze` 0건 · `dart format` 변경 없음 ·
백엔드 `ruff check` 통과 · `pytest` 통과(§6).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| 예약 계획 순수 함수((지금, 설정, 완료 KST 날짜, 기기 시간대) → (id, 발화 시각) 집합, 일일=ID 고정 반복 1 + `matchDateTimeComponents: time`, 리마인더=7일치 1회성·ID 날짜 기반, 완료 날짜 제외, 일일과 같은 시각 제외, 총 ≤8) | `test/notifications/notification_plan_test.dart` 17건 — 그룹 "일일 알림"(4)·"리마인더"(8)·"기기 시간대"(3)·"계획의 모양"(2). 반복/1회성·`matchDateTimeComponents` 는 `PluginNotificationScheduler.schedule` 에서 kind 로 갈린다 | §3.1 |
| 단위 테스트: 오늘 제외·내일 유지 / 미주 KST 경계 / 두 언어 중 하나 완료 / 7일 롤링 보충 / 대기 ≤8 / 시간대 변경 재계산 | 같은 파일의 같은 이름 테스트 6건(§3.1 표에 1:1 로 적었다) | §3.1 |
| OS 대기 목록과 diff(취소/추가)하는 동기화 함수를 앱 시작·포그라운드 복귀·퍼즐 완료·알림 탭·설정 변경·22 의 게스트 토큰 Provider 변경에 걸어 호출 | `test/notifications/notification_diff_test.dart`(6) + `notification_controller_test.dart`(17) — 그룹 "앱 시작"(4)·"저장소 고장"(1)·"설정 변경"(3)·"퍼즐 완료"(4)·"게스트 토큰·복귀"(3)·"알림 탭"(2) | §3.2·§3.3 |
| Android `inexactAllowWhileIdle` · exact alarm 권한 매니페스트 미포함 · `timezone` 로컬 존 · 권한 상태는 28 의 결과 사용 | `test/config/android_scheduled_notifications_test.dart`(3, 선언된 권한만 파싱해서 확인) · 로컬 존은 `notification_plan_test.dart` "기기 시간대"(3) + `DeviceTimeZone` 경계 · 권한은 `notification_controller_test.dart` "OS 에 권한 상태를 물어보고…", "권한이 없으면…", "복귀하면 권한도 다시 묻는다" | §3.2·§3.4 |
| 탭 처리: 실행 중 `onDidReceiveNotificationResponse` · 종료 상태 `getNotificationAppLaunchDetails` → go_router 오늘 탭 + `GET /puzzles/today` 재조회 | `test/notifications/notification_tap_test.dart`(2, 실제 앱 트리·라우터) + `notification_controller_test.dart` 그룹 "알림 탭"(2) | §3.3 |
| 27 의 S4 알림 자리를 채움(시각 picker · 리마인더 스위치 · 권한 거부 안내 → 설정 앱 열기), 태블릿은 S4 설정 열 안, 시각 picker 는 `showAdaptiveSheet`(폭 744 위젯 테스트 1건) | `test/screens/records_notifications_test.dart`(10) — "폭 744 에서는 바텀시트가 아니라 다이얼로그로 뜬다" 포함. 열 배치는 기존 `records_tab_test`·`ranking_records_tablet_test` 가 그대로 지킨다 | §3.5 |
| `audit.native`(태블릿 폭 포함) 통과 | §4 체크리스트(5축 19/20) + 태블릿 폭 744·1024·1366 근거 | §4 |
| 목업 `e4_records` 설정 리스트 대비(알림 행은 목업 없음 — 명세+토큰) | §5 골든 3장(`records_light_390` 갱신 · `records_tablet_1024` 갱신 · `records_notification_off_390` 신규) | §5 |
| 실기기 체크리스트(iOS·Android) — `docs/RELEASE.md` 자기 절 | `docs/RELEASE.md` "### 30." 9개 체크박스(실행은 사람) | §2 |
| README Flutter 절에 "서버 푸시 대신 로컬 알림" 근거 | README "### 30. 로컬 알림 — 서버 푸시 대신 기기 예약, 계획은 순수 함수" | §2 |

마이그레이션을 만들지 않았으므로 `flask db heads` 는 그대로 1개다(§6.3 에 실행 출력).

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/lib/notifications/notification_plan.dart` | 예약 계획 **순수 함수** + ID·KST 날짜 규칙(`NotificationPlan`) |
| `mobile/lib/notifications/notification_sync.dart` | 계획 ↔ OS 대기 목록 **diff 순수 함수**(`diffPendingNotifications`) |
| `mobile/lib/notifications/notification_settings.dart` | 알림 설정 값 + 저장소 경계(기기 로컬) |
| `mobile/lib/notifications/notification_settings_controller.dart` | `notificationSettingsProvider`(시각·리마인더 on/off 쓰기) |
| `mobile/lib/notifications/completed_puzzle_dates.dart` | 이 기기에서 끝낸 KST 퍼즐 날짜 집합(저장소 + 정리 순수 함수) |
| `mobile/lib/notifications/notification_scheduler.dart` | OS 예약 경계 + `flutter_local_notifications` 구현(inexact·채널·문구 번역) |
| `mobile/lib/notifications/notification_bootstrap.dart` | 시작 초기화(tz DB·로컬 존·플러그인·탭 통로·`available`), 기기 시간대 경계 |
| `mobile/lib/notifications/notification_controller.dart` | 동기화 컨트롤러 — 6개 사건 구독 → `sync()` → diff 적용, 알림 탭 라우팅 |
| `mobile/lib/notifications/system_notification_settings.dart` | OS 알림 설정 화면 열기(`app_settings`) |
| `mobile/test/notifications/*`(7개) · `test/screens/records_notifications_test.dart` · `test/config/android_scheduled_notifications_test.dart` · `test/fakes/fake_notifications.dart` | §3 |
| `mobile/test/golden/records_notification_off_390.png` | 권한 꺼짐 S4 골든 |

**고친 것**

| 파일 | 변경 |
|---|---|
| `mobile/lib/screens/records_tab.dart` | S4 알림 두 줄 구현(`_NotificationRows`·`_ReminderPicker`·`_NotificationsOffNotice`), `RecordsSlot.notificationOff`·`reminderPicker` 키 추가 |
| `mobile/lib/widgets/settings_row.dart` | 선택 `trailing`(리마인더 스위치 자리) |
| `mobile/lib/permissions/notification_permission.dart` | 경계에 `current()` 추가(OS 에 지금 상태 묻기) + `NotificationPermissionNotifier.refresh()` — 티켓 28 이 30 에 넘긴 항목 |
| `mobile/lib/main.dart`·`lib/app.dart` | 시작 순서에 알림 초기화 추가 + `notificationBootstrapProvider` 주입, `ChosungApp` 이 동기화를 살려 둔다 |
| `mobile/android/app/src/main/AndroidManifest.xml` | `RECEIVE_BOOT_COMPLETED` + 플러그인 리시버 2개 |
| `mobile/assets/translations/{ko,en}.json` | `notification` 사전 + `records` 3줄 |
| `mobile/pubspec.yaml`·`pubspec.lock` | `timezone`·`flutter_timezone`·`app_settings`(7.x 고정) |
| `mobile/test/golden/ranking_records_golden_test.dart` | 알림 설정 저장소·권한 override + 권한 꺼짐 골든 1장 |
| `mobile/test/screens/records_tab_test.dart`·`test/l10n/localization_bootstrap_test.dart`·`test/fakes/fake_permissions.dart` | 새 동작에 맞춰 갱신(§3.6) |
| `README.md`·`docs/RELEASE.md` | 자기 번호 절(`### 30.`)만 덧붙임 |
| `.scratch/store-launch/spec.md` | "미정 항목" 끝에 미정 6 판단 재료 한 줄(공통 규칙대로 자기 행만) |

## 3. 테스트 (64건)

### 3.1 예약 계획 순수 함수 — `test/notifications/notification_plan_test.dart` (17)

| 티켓이 요구한 경우 | 테스트 |
|---|---|
| 오늘 제외·내일 유지 | "완료한 KST 날짜의 리마인더만 빠지고 다음 날 것은 그대로다" |
| 미주 시간대 KST 경계 | "미주 사용자의 20:00 은 KST 로 다음 날이라 그 날짜로 걸러진다"(뉴욕 10-15 20:00 EDT = 서울 10-16 09:00) |
| 두 언어 중 하나 완료 | "두 언어 중 하나만 완료해도 그 날짜는 빠진다"(집합의 열쇠가 날짜 하나뿐) |
| 7일 롤링 보충 | "오늘 20:00 이 지났으면 내일부터 7일치다", "3일 뒤에 다시 계산하면 지난 것은 빠지고 뒤로 3일이 보충된다"(겹치는 날짜의 ID 가 같은 것까지 확인) |
| 대기 ≤8 | "앞으로 7일치를 20:00 에 하나씩 잡고 전체는 8개를 넘지 않는다" |
| 시간대 변경 재계산 | "같은 순간이어도 기기 시간대가 바뀌면 발화 순간이 다시 계산된다", "DST 가 끝나는 주에도 리마인더는 매일 로컬 20:00 이다"(EDT→EST 전이가 한 창에 들어간다 — offset `{-4, -5}`) |
| 일일 = 고정 ID 1개 | "아직 안 지난 오늘 시각이면 오늘 발화한다"(ID 고정 확인), "오늘 시각이 지났으면 내일 발화한다", "고른 시각이 바뀌면 발화 시각도 바뀐다" |
| 일일과 같은 시각 제외 | "일일 알림이 20:00 이면 리마인더는 전부 빠진다" |
| 리마인더 ID = 날짜 | "ID 는 발화 날짜로 정해져 다시 계산해도 같다" |
| 그 밖 | "이미 푼 날짜여도 일일 알림은 그대로다", "스위치를 끄면 리마인더가 하나도 없다", "발화 순서대로 돌려주고 ID 가 겹치지 않는다", "이 앱이 거는 ID 만 우리 것으로 센다" |

### 3.2 diff 순수 함수 — `notification_diff_test.dart` (6)

"대기 목록이 비어 있으면 계획 전부를 새로 건다", "이미 걸려 있는 리마인더는 다시 걸지
않는다", **"일일 알림은 이미 걸려 있어도 다시 건다"**(대기 목록이 시각을 안 알려주므로),
"계획에서 빠진 우리 알림은 취소한다", "우리가 걸지 않은 ID 는 건드리지 않는다"(다른 SDK
보호), "계획이 비면 우리 알림을 전부 취소한다".

### 3.3 동기화 컨트롤러 — `notification_controller_test.dart` (17)

실제 provider 로 돌리고 **OS 경계(예약기·저장소·시간대·권한)만** 가짜로 바꿨다.

- **앱 시작(4)**: OS 에 권한을 물어보고 그 결과로 예약 / 권한 없으면 전부 취소하고 아무것도
  안 건다 / 이미 걸려 있는 리마인더는 다시 안 건다(일일만 다시) / 저장된 설정의 시각으로 건다
- **설정 변경(3)**: 시각 변경 → 일일 재예약 / 리마인더 off → 7개 취소 / 다시 on → 7개 복구
- **퍼즐 완료(4)**: 그 날짜만 취소·다음 날 유지 / 두 언어 중 하나만 끝내도 완료로 기록 /
  안 끝난 퍼즐은 기록 안 함 / 다시 켜도 저장된 완료 날짜가 걸러진다
- **게스트 토큰·복귀(3)**: 토큰 교체 시 재계산(22 의 Provider 만 구독) / 복귀 시 기기
  시간대 재조회 후 재계산(서울→뉴욕) / 복귀 시 권한 재조회(설정에서 켜고 돌아온 경우)
- **알림 탭(2)**: 실행 중 탭 → 재조회 / 종료 상태 launch → 시작 조회 1번으로 충분(중복 조회 없음)
- **저장소 고장(1)**: 설정·완료 날짜를 못 읽어도 기본값(09:00·리마인더 on)으로 8개를
  건다 — 여기서 멈추면 알림이 **조용히 통째로 멈춘다**

### 3.4 완료 날짜·문구·네이티브 설정 (9)

`completed_puzzle_dates_test.dart`(3): 퍼즐 날짜 열쇠 포맷, KST 오늘 이전 날짜 정리.
`notification_text_test.dart`(3): ko·en 사전에 종류별 title/body + 채널 이름·설명이 다
있는지(열쇠를 이름으로 조립하므로 analyze 가 못 잡는다), 채널 ID 고정.
`android_scheduled_notifications_test.dart`(3): `RECEIVE_BOOT_COMPLETED` + 부트 리시버,
예약 리시버, **exact alarm 권한 미선언**(주석이 아니라 실제 `uses-permission` 만 파싱).

### 3.5 S4 화면 — `records_notifications_test.dart` (10)

저장된 시각이 행에 보인다 / picker 에서 고른 시각이 저장되고 예약이 따라간다(동기화까지
실제로 돈다) / 같은 시각을 다시 골라도 안 쓴다 / **폭 744 에서는 다이얼로그**(`showAdaptiveSheet`)
/ 리마인더 스위치 off → 저장 + 리마인더 7개 취소 / 스위치는 저장된 값으로 그려진다 /
권한 허용이면 안내 없음 / 거부면 안내 + 누르면 시스템 알림 설정 열기 / 아직 안 물어본
상태도 같은 안내 / 영어 UI.

### 3.6 기존 테스트 변경 (3파일)

- `records_tab_test.dart`: "29·31·32 가 채울 자리는…" — 일일 알림 행은 이제 눌린다(채운 자리
  목록에 추가). 알림 설정 저장소 override 추가.
- `l10n/localization_bootstrap_test.dart`: 시작 순서에 알림 초기화 추가(국제화 **뒤** —
  예약할 때 문구를 번역한다).
- `golden/ranking_records_golden_test.dart`: 알림 설정·권한 override + 골든 1장 추가.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

22·24·25·26·27·28 과 같은 방식이다 — 브라우저 도구·`impeccable detect` 는 HTML/CSS 용이라
쓰지 않고, 소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매긴다. 폭
확인은 눈이 아니라 위젯 테스트(390·744)와 골든 3장이다.

| # | 축 | 28 | 30 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | 알림 행은 라벨 + 값 + 화살표로 읽히고(`SettingsRow`), 리마인더는 `Switch` 라 스크린 리더가 on/off 를 그대로 읽는다. 권한 안내는 **색이 아니라 아이콘(종에 사선) + 문장**이고 터치 타깃 44 이상(`ConstrainedBox(minHeight: SettingsRow.minHeight)`). picker 는 `RadioListTile` 목록이라 항목마다 선택 상태가 읽힌다(휠을 쓰지 않은 이유 중 하나) |
| 2 | Performance | 3 | 3 | picker 는 `itemExtent` 가 고정된 `ListView.builder`(48칸)라 보이는 줄만 만든다. 동기화는 한 번에 하나만 돌고(겹치면 한 번으로 묶는다) OS 호출은 **차이만** 보낸다 — 평소 동기화는 `pendingIds` 1회 + 일일 재예약 1회다 |
| 3 | Appearance & Theming | 4 | 4 | 새 UI 전부 `AppColors` 토큰만 쓴다(raw hex 는 여전히 `app_colors.dart` 한 파일뿐). 안내 줄은 면 없이 헤어라인과 여백으로만 구분(OVERRIDES §4), brand 는 쓰지 않았다. 권한 꺼짐은 오류가 아니라 상태라 `destructive` 를 쓰지 않고 본문색 + `muted-foreground` 아이콘이다 |
| 4 | Platform Conformance | 3 | 4 | 스위치는 `Switch.adaptive`(iOS 는 Cupertino 모양). Android 는 `inexactAllowWhileIdle` + **exact alarm 권한 미선언**(Play 정책), `RECEIVE_BOOT_COMPLETED` + 플러그인 리시버 2개 선언(없으면 재부팅에 예약이 사라진다). iOS 는 반복 트리거의 날짜 소실을 피해 리마인더를 1회성으로 깐다. 권한은 초기화가 아니라 **사전 안내 뒤**에만 묻는다(28 과 한 벌) |
| 5 | Adaptivity | 4 | 4 | 알림 두 줄은 27 이 정한 S4 설정 열(T4 오른쪽) 안에 그대로 들어가고 열 배치를 바꾸지 않는다. picker 는 폭 <600 바텀시트 / ≥600 다이얼로그(`showAdaptiveSheet`, 폭 744 테스트 1건). 안내 문장은 `Expanded` 라 긴 문장·큰 글자에서 줄바꿈된다 |
| **합계** | | **18/20** | **19/20** | **Excellent** |

**추가 항목 "태블릿 폭(744·1024·1366) 포함": 통과.** 744 는 이 티켓의 picker 테스트가,
1024 는 골든 `records_tablet_1024`(갱신)과 27 의 `ranking_records_tablet_test` 가 덮는다.
1366·834·320 은 24 의 셸 테스트가 덮고, **알림 두 줄에는 폭 분기가 없다** — `SettingsRow`
하나라서 744 와 1366 에서 달라지는 것은 picker 의 시트/다이얼로그 분기뿐이고 그 경계(600)는
744 테스트가 넘어가 있다.

### 디자인 파일과 다르게 구현한 곳 / 판단 (커밋 메시지에도 적는다)

1. **시각 표기는 "09:00" 고정이 아니라 OS 형식이다.** SCREENS T4 와이어는 `09:00 ›` 로
   그려져 있지만 `MaterialLocalizations.formatTimeOfDay` 를 썼다 — 기기의 12/24시 설정과
   언어를 따른다(ko "오전 9:00", en "9:00 AM"). 시각 표기는 앱이 고집할 것이 아니라 OS
   설정을 따르는 쪽이 맞고, 와이어의 `09:00` 은 자리 스케치다.
2. **리마인더 행 아래에 보조 한 줄을 뒀다**("그 날 안 풀었으면 저녁 8시에 한 번 더").
   SCREENS 에 없는 줄이다. 리마인더가 **20:00** 이라는 사실이 화면 어디에도 없으면 스위치를
   켜고 끄는 근거가 없다.
3. **권한 꺼짐 안내는 설정 행 안이 아니라 그 아래 별도 줄이다.** SCREENS S4 문장은 한 행
   안에 들어가는 것처럼 읽히지만, 한 행에 시각 값과 안내 문장을 같이 넣으면 둘 다 잘린다.
   누를 수 있는 한 줄로 분리하고 화살표로 "어딘가로 간다" 를 같이 알린다.
4. **시각 picker 는 30분 단위 목록이다**(OVERRIDES §6 `ReminderPicker`). 목업이 없는
   자리라 코디네이터에게 입력 방식(목록 / 휠 / `showTimePicker`)을 물었고(`msg_3efbf7008191`),
   **답을 받지 못해 추천안인 목록으로 진행했다**. 근거는 ① 티켓이 `showAdaptiveSheet` 를
   요구한다(`showTimePicker` 는 자기 다이얼로그를 띄운다) ② 퍼즐 언어 picker 와 같은 모양이라
   설정 안에서 조작이 한 가지로 보인다 ③ 접근성·테스트가 그냥 통과한다. 분 단위가 필요하면
   `_ReminderPicker._stepMinutes` 한 곳이다.
5. **리마인더는 행이 아니라 스위치만 누른다.** 행과 스위치가 같은 일을 하면 "껐는데 다시
   켜졌다" 가 생긴다(`SettingsRow.trailing` 이 들어오면 행 `onTap` 은 비운다).

## 5. 목업 대비 기록 (골든 3장)

`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`.

| 골든 | 대조 대상 | 결과 |
|---|---|---|
| `records_light_390.png`(갱신) | `design/stitch/e4_records.png` + SCREENS S4 설정 리스트 | 퍼즐 언어 다음에 "일일 알림 오전 9:00 ›" → "리마인더 [on]" → 보조 한 줄 → 광고 개인정보(준비 중) 순. 목업의 "준비 중" 자리 두 개가 실제 값으로 바뀐 것 외에는 행 높이·헤어라인·여백이 그대로다 |
| `records_tablet_1024.png`(갱신) | SCREENS T4 와이어 | 오른쪽 설정 열 안에서 같은 두 줄. 왼쪽 열(기록·계정·구독·백업 코드)은 그대로 — 27 이 정한 열 배치를 건드리지 않았다 |
| `records_notification_off_390.png`(신규) | 목업 없음(SCREENS S4 문장 + OVERRIDES 토큰) | 일일 알림 행 아래에 종에 사선 아이콘 + "알림 꺼짐 — 시스템 설정에서 켜기" + 화살표 한 줄이 끼어든다. 나머지 줄은 위 골든과 같다 |

### 남은 결함 / 의도된 이탈

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | 실기기 | **실제 기기에서 알림이 뜨는 건 이 티켓의 테스트로 증명할 수 없다** — 위젯 테스트는 플러그인 경계를 가짜로 바꾸고, 골든은 테스트 렌더러다. OS 예약·부트 리시버·탭 cold start 는 사람이 본다 | `docs/RELEASE.md` "### 30." |
| P3 | 네이티브 빌드 | `flutter build`(apk/ios)는 돌리지 않았다 — 디스크 여유 제약(워커 공통). 새 플러그인 2개의 네이티브 연결은 pod 요구 버전 검사(`ios_project_test.dart`)와 매니페스트 검사까지만 확인했다 | 티켓 34 |
| P2 | 리마인더 | 7일 넘게 앱을 안 열면 리마인더가 멈춘다(예약을 7일치만 미리 건다). 스펙 §A.9 가 수용한 한계이고, 앱을 열면 다시 채워진다 | — (의도) |
| P3 | Android 알림 아이콘 | 런처 아이콘(`@mipmap/ic_launcher`)을 쓴다. Android 는 상태바용 **흰 실루엣** 아이콘을 따로 두는 게 권장이라, 지금은 상태바에서 사각형으로 보일 수 있다 | 티켓 35(아이콘 제작) |
| P3 | 권한 3상태 | Android 는 "아직 안 물어봄" 과 "거부" 가 구분되지 않는다(`areNotificationsEnabled` 는 bool). 두 경우 모두 같은 안내를 쓴다 — 사용자가 할 수 있는 일이 같다 | — (의도) |
| P3 | 설정 쓰기 실패 | 기기 저장소 **쓰기**가 실패하면 화면에 알리지 않는다(퍼즐 언어 행에는 인라인 안내가 있다). 읽기 실패는 기본값으로 떨어뜨려 알림이 멈추지 않게 했다(§3.3 "저장소 고장"). 쓰기는 서버 왕복이 아니라 로컬 저장소라 실패 모드가 "기기 고장" 수준이고, 온보딩 완료 플래그(티켓 28)도 같은 수준으로 다룬다 | — (의도) |
| P3 | picker 단위 | 알림 시각은 30분 단위다. 분 단위가 필요하면 `_ReminderPicker._stepMinutes` 한 곳 | 위 "다르게 구현한 곳" 4 |
| P2 | 코디네이터 질문 | picker 입력 방식 질문(`msg_3efbf7008191`)에 답을 받지 못했다. 추천안(목록)으로 진행했고 바꾸려면 위젯 한 곳이다 | 코디네이터 |

## 6. 검증 (실제 실행 명령과 출력)

### 6.1 앱 테스트 (전체)

```
$ cd mobile && flutter test
00:53 +458: All tests passed!
```

이 티켓이 더한 테스트 파일 9개 = **64건**이고, 기존 골든 파일에 1장
(`records_notification_off_390`)을 더했다. 나머지 기존 테스트 3개 파일은 새 동작에 맞춰
**고친** 것이다(§3.6). 파일별로 따로 돌린 결과:

```
test/notifications/notification_plan_test.dart              -> +17
test/notifications/notification_controller_test.dart        -> +17
test/notifications/notification_diff_test.dart              -> +6
test/notifications/completed_puzzle_dates_test.dart         -> +3
test/notifications/notification_bootstrap_test.dart         -> +3
test/notifications/notification_text_test.dart              -> +3
test/notifications/notification_tap_test.dart               -> +2
test/screens/records_notifications_test.dart                -> +10
test/config/android_scheduled_notifications_test.dart       -> +3
```

### 6.2 정적 검사·포맷 (CI 와 같은 명령, `.github/workflows/flutter-ci.yml`)

```
$ cd mobile && dart format --set-exit-if-changed lib test
Formatted 140 files (0 changed) in 0.36 seconds.

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 8.5s)
```

### 6.3 마이그레이션

마이그레이션을 만들지 않았다(`migrations/` 변경 0건).

```
$ uv run flask db heads
b1c7d4e0a932 (head)
```

1줄이다.

### 6.4 백엔드 (CI 와 같은 명령, `.github/workflows/ci.yml`)

이 티켓은 Python 을 한 줄도 건드리지 않았지만(아래 `git diff --stat`) 전체 스위트를
돌렸다. 다른 워커와 MySQL 을 공유하므로 **전용 DB·Redis** 를 썼다
(`chosung_daily_test_t30`, Redis DB 4, 마이그레이션 왕복은
`chosung_daily_test_t30_migrations`).

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=mysql+pymysql://…/chosung_daily_test_t30 \
  TEST_REDIS_URL=redis://localhost:6379/4 \
  TEST_MIGRATION_DATABASE_URL=mysql+pymysql://…/chosung_daily_test_t30_migrations \
  uv run pytest -q
........................................................................ [ 97%]
...................................                                      [100%]
1403 passed in 1172.03s (0:19:32)
```

(첫 실행은 61% 에서 외부 요인으로 종료돼 다시 돌렸다. 워커 3개가 같은 MySQL 에
스키마를 매 테스트마다 만들고 지워서 평소보다 오래 걸렸다 — 19분 32초.)

**백엔드·웹 변경 0건** 확인:

```
$ git diff --name-only main...HEAD | grep -E "^(app|web|migrations|tests)/" | wc -l
       0
```

### 6.5 작업 트리

```
$ git log --oneline main..HEAD
b82ede3 문서 30: 설계 판단·실기기 체크리스트·구현 증거
da7a94a 구현 30: 기기 저장소가 고장나도 알림은 기본값으로 간다
b9487bb 구현 30: Android 예약 알림 배선 — 부트 리시버와 예약 리시버 선언
bb241bd 구현 30: S4 알림 두 줄 — 시각 picker · 리마인더 스위치 · 권한 꺼짐 안내
a0f5e32 구현 30: 동기화 컨트롤러 — 여섯 사건을 구독해 계획을 다시 맞춘다
7213f9d 구현 30: 로컬 알림 예약 계획과 OS diff 를 순수 함수로

$ git status --short
(clean)
```

로컬 `main`(= `8ddc8fd`) 위에 그대로 올라가 있어 `git rebase main` 은 no-op 이다
(`git merge-base --is-ancestor main HEAD` 성공).
