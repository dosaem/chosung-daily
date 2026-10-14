# 티켓 24 최종 리뷰 — 라운드 1

## 검토 기준

- 검토 대상 HEAD: `9189da34bfba8f7ce31aa5707e2044c96e7e6d4a`.
- 로컬 main: `1e764da6d8ec4710d4ebf945249a6e264bd75f84`. `git diff main...HEAD` 및 `git log main..HEAD`의 구현 커밋 4개를 확인했다. origin/main은 사용하지 않았다.
- 티켓 24, spec §B.19·21 / US 15a / 미정 24, SCREENS 앱 탭 구조·T0~T4, MASTER 및 우선하는 OVERRIDES를 대조했다.
- 구현 증거는 참고 자료로만 사용하고 소스·테스트·실행 결과를 직접 확인했다. 하위 에이전트는 사용하지 않았다.

## 티켓 체크박스별 결과

| 요구사항 | 결과 | 직접 확인한 근거 |
|---|---|---|
| 현재 폭 기반 compact / medium / expanded와 경계 테스트 | 충족 | `mobile/lib/layout/app_breakpoint.dart:23`에서 600/840으로 분기하고 `MediaQuery.sizeOf`를 사용한다. `app_breakpoint_test.dart`가 599/600/839/840 및 320을 검증한다. |
| AdaptiveScaffold, 동일한 3탭·경로, ReadingWidth 6곳 교체 및 기존 테스트 유지 | 충족 | `adaptive_scaffold.dart:43`의 폭 분기, `home_shell.dart:24`의 공통 목적지·goBranch를 확인했다. 여섯 화면의 래퍼가 교체됐으며 기본 600과 사용자 지정 폭을 테스트한다. 시작 분기 테스트 diff에서 기존 iPad 테스트 이외의 기존 테스트 본문은 유지됐다. 834dp에서 rail·콘텐츠 폭을 직접 검증한다. |
| 배너 위치·safe area·폭 노출·높이 예약 | 충족 | `adaptive_scaffold.dart:58,76`에서 태블릿 콘텐츠 하단과 폰 탭 바 아래로 배치한다. `ad_banner_slot.dart:41`의 LayoutBuilder가 실제 슬롯 폭을 builder에 전달한다. 위치·폭·하단 inset 20·예약 높이·배너 제거 테스트가 통과했다. 50/90dp는 코디네이터 후속 메시지로 승인된 잠정값임을 별도 확인했다. |
| showAdaptiveSheet의 바텀시트 / 최대 560dp 중앙 다이얼로그 | 충족 | `adaptive_sheet.dart:22`의 분기와 560dp 제한·상하 48dp inset을 확인했다. 390/600/1024dp에서 위젯 종류와 위치·크기 검증이 통과했다. |
| 390→744→390 상태 유지 및 320dp compact | 충족 | `adaptive_scaffold_test.dart`는 컨트롤러 없는 TextField 입력, 실제 Scrollable offset, 선택 탭을 폭 왕복 전후 비교한다. 앱 시작 테스트에서도 실제 go_router의 선택 분기가 유지된다. `setSurfaceSize` 대신 view의 physicalSize와 DPR을 바꾸지만 요구한 논리 폭 변경과 상태 보존을 실제로 검증한다. |
| 폭별 위젯 테스트·동일 경로·analyze 0·태블릿 audit | 충족 | 390/744/1024/1366 및 834dp의 실제 위젯 테스트와 390/1024dp 경로 검증이 통과했다. analyze 0건. 구현 증거 §4에 744·1024·1366 audit 체크 및 통과 근거가 있고 그 근거 테스트를 재실행했다. 실기기 육안 audit으로 확대 해석하지 않았다. |
| README 태블릿 대응 설명·미정 24 결과 | 충족 | `README.md:1277`의 자기 번호 `### 24.`에 폭 기준·rail·ReadingWidth·T1/T4 폭·320dp 처리와 후속 화면 티켓 책임이 기록됐다. spec 미정 항목 끝에는 자기 티켓 행만 추가됐다. |

## 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| `cd mobile && flutter analyze` | 종료 0, No issues found |
| `cd mobile && flutter test` | 종료 0, 120 passed |
| `cd mobile && dart format --set-exit-if-changed .` | 종료 0, 55 files / 0 changed |
| `cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug` | 종료 0, app-debug.apk 생성, Gradle 53.9초 |
| `uv run ruff check .` | 종료 0, All checks passed |
| `uv run pytest -q` (아래 테스트 환경 지정) | 종료 0, 743 passed in 747.79s (12분 27초), 실패·skip 없음 |
| `FLASK_APP=wsgi.py uv run flask db heads` | 종료 0, `dae1b5af0cf7 (head)` 한 줄 |
| `git diff --check main...HEAD` | 종료 0 |

백엔드는 `TEST_DATABASE_URL`에 로컬 전용 `chosung_daily_test_t24`, `TEST_REDIS_URL`에 로컬 Redis DB 12, `TEST_MIGRATION_DATABASE_URL`에 기존 `chosung_daily_test_t24_migrations`를 지정했다. 접속 문자열의 인증 값은 이 문서에 기록하지 않는다. 새 DB는 만들지 않았고 기본 공용 DB로 대체하지 않았다. 이 티켓에는 마이그레이션 변경이 없다.

Android 검증 후 코디네이터 지시대로 생성물을 `flutter clean`으로 정리했다. iOS 빌드·시뮬레이터·실기기는 실행하지 않았으며, 코디네이터가 iOS 빌드 생략을 명시했다. 프로덕션·NAS·실제 광고/인증/결제 서비스에 접근하지 않았고 push하지 않았다.

## 결함 목록

확인된 결함 없음: BLOCKER 0 / MAJOR 0 / MINOR 0. 결함 ID는 발급하지 않았다.

## 범위·안전성·테스트 신뢰성

- 변경은 태블릿 뼈대·래퍼·배너 슬롯·대응 테스트·자기 티켓 문서에 한정된다. 백엔드 인증·CSRF·입력 검증·데이터 저장 경로 변경이 없으며 diff에서 새 시크릿 값도 발견하지 못했다.
- README 설계 판단에는 자기 번호 소제목을 끝에 추가했고, spec 미정 항목에는 자기 행만 추가했다. 다른 티켓 내용을 덮어쓴 변경은 없다.
- 레이아웃 테스트는 실제 Flutter 위젯을 사용한다. 앱 테스트의 API/토큰 저장소 대역은 외부 의존성을 격리하며 실제 go_router 경로와 화면 전환을 확인한다. 항상 통과하는 단언이나 레이아웃 자체를 mock한 테스트는 발견하지 못했다.

## 참고와 검증 한계

- 화면별 2열 배치와 광고 SDK 실측은 티켓 25~32의 범위다. 현재 placeholder와 승인된 예약 높이를 이 티켓의 누락으로 분류하지 않았다.
- 증거 문서 §2는 Android 빌드 실행을 기록하지만 §5는 네이티브 빌드를 하지 않았다고 써서 서술이 일치하지 않는다. 이번 리뷰의 독립적인 Android 빌드 성공으로 판단했으며 애플리케이션 결함으로 집계하지 않았다.
- `adaptive_sheet_test.dart`의 “어느 쪽이든 닫을 때 같은 값” 테스트는 실제로 1024dp 다이얼로그 반환값만 검사한다. 폰 바텀시트 반환값까지 검증했다는 증거로 사용하지 않았다. 구현은 각 Flutter API의 Future를 직접 반환하며 관찰된 동작 결함은 없다.

판정: PASS
