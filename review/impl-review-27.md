# 티켓 27 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `24c584d`, 구현 HEAD = `518e06d`. `git diff main...HEAD` 및 `git log main..HEAD`의 6개 커밋을 검토했다. `origin/main`은 사용하지 않았다.
- 요구사항: 티켓 27, 스펙 §B.21·US 12~14·16a·16b·47·48, `CONTEXT.md`, SCREENS S3·S4·T3·T4, Hidden Vowels OVERRIDES(우선), 구현 증거 문서.
- 범위: 앱·테스트·설정·`.scratch/`는 변경하지 않았다. 실제 서비스 호출 없이 저장소의 Fake API/저장소 경계와 실제 앱 라우터·provider·화면으로 추가 재현했다.

## 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient의 leaderboard/history, Dio + Fake | 충족 | 두 메서드, 응답 모델·배열 파싱, Bearer 및 limit/days 쿼리를 구현했다. 서버 `app/api/puzzles.py`·`app/api/me.py`와 대조했고 Dio 어댑터 테스트도 실행했다. |
| S3 표시 전용 언어 칩, entries·내 행 강조, 목록 밖 me 고정, 빈 상태 | 미충족 | 최초 응답의 표시는 구현했고 해당 위젯 테스트는 통과한다. 그러나 먼저 순위를 본 뒤 정답을 제출하면 내 순위가 계속 미풀이로 남아 핵심 사용자 흐름을 충족하지 않는다(D-27-1). |
| S4 streak·7일 그리드·설정·담당 번호가 있는 자리 | 미충족 | 설정의 PATCH 후 홈·순위 무효화, 법적 문서 URL, LicensePage·버전, 8개 비활성 자리와 번호 주석을 확인했다. streak 및 이미 읽은 7일 기록은 플레이 결과를 반영하지 않는다(D-27-2). |
| 위젯 테스트: me·빈 상태·7일 그리드·언어 변경 후 재조회 | 충족 | 요구한 개별 사례가 있고 모두 통과했다. 서버 경계 Fake와 실제 컨트롤러를 사용한다. 다만 정답 제출→탭 재진입 사례가 없어 D-27-1·2를 놓친다. |
| 태블릿 T3·T4, 390/744/1024 분기, 자리의 열 고정 | 미충족 | 지정 폭의 표·1/2열·최대 폭·자리 배치 테스트 7개는 통과했다. SCREENS 태블릿 공통 규칙의 폭 변경 후 스크롤 유지가 되지 않는다(D-27-3). |
| audit.native(태블릿 포함), e3/e4·T3/T4 대비 기록 | 미충족 | 구현 증거의 체크리스트와 목업 대비 기록은 존재하며 이미지와 토큰을 직접 대조했다. 그러나 짧은 가로 화면에서 S3 로딩이 넘친다(D-27-4). 셸의 1366 폭 테스트만으로 새 화면 전체의 적응성까지 입증되지는 않는다. |

## 직접 실행한 검증

- `cd mobile && flutter test`: **259개 통과**, exit 0. 기존 골든 4장 및 지정 폭 테스트 포함.
- `cd mobile && flutter analyze`: **No issues found**, exit 0.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: **85 files, 0 changed**, exit 0.
- `uv run ruff check .`: **All checks passed**, exit 0.
- 백엔드: 기존 `chosung_daily_test_t27`, Redis DB 15 및 기존 `chosung_daily_test_t27_migrations`를 `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`로 지정해 `uv run pytest -q` 실행. 새 DB는 만들지 않았으며 기본 DB로 대체하지 않았다. 접속 문자열의 인증 값은 이 문서에 옮기지 않는다. **1110 passed in 663.51s (0:11:03)**, exit 0. 간헐 실패가 없어 재실행하지 않았다.
- `git diff --check main...HEAD`: exit 0.
- `git diff --name-only main...HEAD -- migrations`: 변경 없음. 마이그레이션 추가 티켓이 아니므로 `flask db heads` 요구는 해당 없음.
- 추가 재현은 `/tmp/t27_review_probe_test.dart`, `/tmp/t27_loading_probe_test.dart`를 `flutter test --no-pub <경로> --reporter expanded`로 실행했다. 저장소 테스트는 수정하지 않았다. 첫 재현은 기대한 성공 상태 대신 `DayResult.none`으로 실패했고, 두 번째는 아래 RenderFlex 오류로 실패했다. 아래 입력 순서와 실제 관찰값을 재현의 정본으로 남긴다(임시 파일은 배포 산출물이 아님).
- iOS/APK 빌드는 이 리뷰에서 실행하지 않았다. 구현 증거의 빌드 주장을 독립 검증 결과로 취급하지 않는다. JDK 부재는 제품 결함으로 세지 않았고 실기기·스크린 리더 검증도 수행하지 않았다.

## 결함 목록

### D-27-1 — MAJOR — 정답 제출 뒤 내 순위를 갱신할 수 없음

- 위치: `mobile/lib/ranking/leaderboard_controller.dart:17`, `mobile/lib/ranking/leaderboard_controller.dart:29`.
- 재현 입력: 미풀이 상태로 앱 시작 → 순위 탭 한 번 열기 → 오늘 탭에서 정답 제출 성공 → 순위 탭으로 복귀. 재현에서는 실제 `ChosungApp`·라우터·`TodayPuzzleNotifier.submit('지하철역')`을 사용하고 Fake API의 새 리더보드 응답을 내 순위 1위로 준비했다.
- 기대: 완료된 오늘 퍼즐의 내 순위/내 행이 표시된다.
- 실제: `아직 안 풀었어요`가 그대로 1개 남는다. `fetchTodayLeaderboardLimits.length == 1`로 두 번째 조회 자체가 없다. 성공/빈 상태에는 수동 새로고침 버튼도 없어서 언어를 바꾸거나 앱을 재시작해야 갱신된다.
- 원인: 일반 AsyncNotifierProvider가 최초 응답을 보관하고, 정답 제출·탭 복귀·날짜 변경과 연결되지 않는다. 재조회는 오류 재시도 또는 언어 변경에만 연결되어 있다. README의 “알려진 제한”은 이미 순위를 확인한 사람이 플레이하는 일반 경로까지 제외할 근거가 되지 않는다.
- 요구/테스트 공백: US 12·16b 및 S3의 내 순위 표시. `ranking_tab_test.dart`는 완료된 응답을 처음부터 주입하므로 플레이 전후 전이를 검증하지 않는다. 최소한 플레이 결과 이후 해당 언어의 내 순위가 새로 읽혀야 한다.

### D-27-2 — MAJOR — 내 기록의 streak·누적·7일 그리드가 플레이 결과를 반영하지 않음

- 위치: `mobile/lib/screens/records_tab.dart:131`, `mobile/lib/records/history_controller.dart:7`.
- 재현 입력: 새 게스트로 시작 → 내 기록에서 0일/0문제·오늘 미플레이 확인 → 오늘 퍼즐 정답 제출 → 내 기록 복귀. 서버 경계의 후속 응답을 현재/최고 1일·누적 1문제, 오늘 `success`로 준비하고 실제 앱 트리에서 실행했다.
- 기대: 현재/최고 1일·누적 1문제 및 오늘 성공 칸으로 바뀐다.
- 실제: 오늘 칸은 `DayResult.none`, 누적은 `0문제`이고 `/me/history`·`/me/stats` 호출 횟수는 각각 1회에 머문다. 최초 로드 후 정답 제출을 했다는 사실을 화면이 반영하지 않는다. 내 기록을 정답 제출 후 **처음** 열어도 streak는 앱 시작 snapshot을 읽으므로 이전 값이다.
- 원인: streak는 `startupStatsProvider`만 읽으며, history는 재시도 버튼 외에 무효화 경로가 없다. `TodayPuzzleNotifier.submit`은 오늘 보드만 바꾼다. 탭을 유지하는 셸에서는 위젯 재진입도 provider 재조회가 아니다.
- 요구/테스트 공백: US 14·16a, S4의 현재 기록. `records_tab_test.dart:39`에서 startup stats를 상수로 덮고 그 값이 보이는지만 검증하므로 이 데이터 수명 문제를 놓친다. 언어별 성공을 합치는 순수 함수는 맞지만 최신 응답을 읽지 않는 문제가 별도로 남는다.

### D-27-3 — MINOR — S4 1열↔2열 전환 시 스크롤 위치 소실

- 위치: `mobile/lib/screens/records_tab.dart:73`, `mobile/lib/screens/records_tab.dart:116`.
- 재현 입력: 실제 앱의 내 기록을 390×844로 열기 → 아래 설정으로 스크롤 → 1024×768로 확대 → 390×844로 복귀.
- 기대: SCREENS “태블릿 레이아웃” 공통 규칙대로 현재 탭과 읽던 스크롤 위치가 유지된다.
- 실제: 동일 재현에서 `ScrollableState.position.pixels`가 **184.0 → 0.0**으로 초기화되어 화면 맨 위로 돌아온다.
- 원인/테스트 공백: 조건 분기가 스크롤 위젯 트리를 교체하지만 지속되는 컨트롤러나 위치 저장 키가 없다. 기존 폭 왕복 테스트는 자리의 존재와 x 좌표만 확인하며 스크롤은 하지 않는다.

### D-27-4 — MINOR — S3 로딩 스켈레톤이 짧은 가로 화면에서 overflow

- 위치: `mobile/lib/screens/ranking_tab.dart:364`.
- 재현 입력: `leaderboardProvider` 응답을 미완료 Future로 유지 → `RankingTab`을 844×390 화면에 표시. 재현은 Scaffold 안의 실제 RankingTab을 사용했다.
- 기대: 가로 방향에서도 사용 가능한 높이에 맞는 스켈레톤이 표시되고 레이아웃 예외가 없다.
- 실제: **`A RenderFlex overflowed by 106 pixels on the bottom.`** 네트워크를 기다리는 동안 고정 높이의 8줄이 화면 하단을 넘는다. rail·배너를 더하지 않은 최소 재현에서도 발생한다.
- 원인/테스트 공백: Column의 고정 내용 높이 464dp에 상하 패딩 32dp가 더해지며, 가용 높이를 제한하거나 스크롤하지 않는다. 기존 로딩 테스트는 390×844만 사용하고 태블릿 분기 테스트는 로드가 끝난 상태만 검증한다. OVERRIDES §7의 로딩 및 SCREENS 회전·적응성 검증에 포함되어야 한다.

## 보안·범위·공유 파일

- 새 API 호출은 기존 Bearer 경로를 사용하고, 토큰이 없으면 전송하지 않는 테스트를 직접 실행했다. CSRF 대상인 웹 쿠키 기반 변경은 이 diff에 없다.
- 리더보드는 서버의 익명 `display`만 사용하며 이메일·계정 정보를 읽는 경로를 추가하지 않았다. 실제 서버 응답 모델과도 대조했다.
- 변경된 앱 경로에 새 비밀값이나 로그 노출을 찾지 못했다. 증거 문서의 로컬 테스트 접속 예시는 운영 시크릿으로 판정하지 않았다.
- 삭제·구독·계정 연결 등은 번호 주석이 붙은 비활성 자리이며 실제 쓰기는 퍼즐 언어 변경뿐이다. 변경 중 재입력 차단 및 세대 비교는 코드로 확인했고 동시 요청 차단 테스트가 통과했다. 다만 구현 증거가 언급한 “늦은 응답을 버리는 테스트”는 5개 컨트롤러 테스트 중 직접적인 재빌드/응답 역전 사례로는 존재하지 않는다(그 주장까지 검증됐다고 인정하지 않음).
- 공유 파일은 README 설계 판단 끝에 `### 27.`만 추가했다. `.env.example`·`docs/RELEASE.md`·`.scratch/`·마이그레이션은 변경하지 않았다. 범위 밖 동작·데이터 파괴 변경을 찾지 못했다.

## 디자인 대조 및 참고

- e3/e4 PNG와 구현 골든을 직접 열어 대조했다. 익명 표시, brand 일반 글자색 배제, 내 행의 brand-subtle 배경, 날짜 칩, T3의 4열 표·하단 me, T4의 좌우 자리 배치는 명세와 맞는다. 목업의 이메일·상단 통계와 다른 것은 상위 명세에 근거한 차이로 결함 처리하지 않았다.
- 골든·위젯 테스트는 실제 기기의 외부 브라우저 실행·음성 낭독·렌더링을 보증하지 않는다. 이 한계 자체를 별도 제품 결함으로 세지 않는다.
- 취향·코드 스타일 제안 없음.

결함 합계: BLOCKER 0 / MAJOR 2 / MINOR 2. D-27-1·2 수정 후 제출 전후와 탭 재진입을 포함한 재검증이 필요하다.

판정: FAIL

## 라운드 2

- 검토 HEAD: `f019c0e`, 검토 시작 시 로컬 `main`: `1afeffa`, `main...HEAD`의 merge-base: `45d790c`. `git diff main...HEAD`(38개 파일)와 `git log main..HEAD`(9개 커밋)를 직접 확인했다. 뒤처진 `origin/main`은 사용하지 않았다.
- 기준: 티켓 27의 6개 체크박스, 스펙 §B.21·US 12~14·16a·16b·47·48, `CONTEXT.md`, SCREENS S3·S4·T3·T4, Hidden Vowels MASTER/OVERRIDES(OVERRIDES 우선), 구현 증거의 수정 라운드 1 절 및 이전 리뷰.
- 코드·테스트·설정·`.scratch/`는 수정하지 않았다. 추가 재현은 `/tmp`에만 작성했으며 실제 앱 트리/라우터/provider를 사용하고 API·저장소·버전 경계만 Fake로 대체했다. 운영 접속이나 실제 외부 서비스 API 호출은 하지 않았다.

### 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient leaderboard/history(Dio + Fake) | 충족 | 인터페이스·응답 모델·Dio GET·Fake 구현을 서버 엔드포인트와 대조했다. 경로·limit/days·Bearer·404·토큰 부재 및 배열 파싱 테스트가 통과했다. |
| S3 표시 전용 언어 칩, entries·내 행 강조, 목록 밖 me 고정, 빈 상태 | 충족 | `RankingTab`·`LeaderboardRow`와 번역을 확인했다. 목록 안/밖 me·빈 상태·언어 변경 재조회 및 실제 탭 이동 후 정답 제출 결과 반영 테스트가 통과했다(D-27-1 FIXED). |
| S4 streak·7일 그리드·설정·담당 번호 자리 | 미충족 | 정답 뒤 현재/최고/누적과 성공 칸은 갱신된다(D-27-2의 기존 재현 FIXED). 그러나 내 기록을 먼저 본 뒤 첫 오답을 내면 오늘 칸이 진행 중으로 바뀌지 않는다(D-27-5). PATCH 후 홈 재조회·법적 문서 URL·LicensePage·버전·번호 주석이 있는 비활성 자리 8개는 확인했다. |
| 위젯 테스트: me·빈 상태·7일 그리드·언어 변경 후 재조회 | 충족 | 해당 사례가 실제 위젯/provider를 거치며 전체 269개 테스트에서 통과했다. 다만 추가된 미완료 제출 테스트는 화면 결과 대신 잘못된 미갱신 동작을 기대한다(D-27-5의 테스트 공백). |
| 태블릿 T3·T4, 390/744/1024 분기·열 고정 | 충족 | 표 최대 840·medium 1열 최대 600·expanded 두 열 각 최대 480 및 자리의 열 배치 테스트 통과. 390→1024→390 스크롤 왕복도 통과했다(D-27-3 FIXED). 추가 320·844 가로·1366 실제 셸 레이아웃 확인도 통과했다. |
| audit.native(태블릿 포함), e3/e4·T3/T4 대비 기록 | 충족 | 증거의 대비 기록이 있고, e3/e4 PNG와 골든 4장을 직접 열어 익명명·내 행·토큰·열 배치를 대조했다. 소스의 Semantics·최소 터치 높이·스켈레톤·테마와 위젯 검증 범위에서 확인했다. 844×390 로딩 overflow는 해소됐다(D-27-4 FIXED). 실기기/음성 낭독까지 검증한 것으로 확대하지 않는다. |

### 이전 결함 판정

| ID | 기존 심각도 | 판정 | 직접 확인 |
|---|---|---|---|
| D-27-1 | MAJOR | FIXED | `mobile/lib/puzzle/today_puzzle_controller.dart:106`에서 완료된 제출 뒤 리더보드를 무효화한다. 실제 앱에서 순위 선조회→정답→순위 복귀 시 조회 1→2회, 내 순위 1위·내 행 표시를 확인했다. |
| D-27-2 | MAJOR | FIXED | 기존 **정답 제출** 재현에 대해 `mobile/lib/puzzle/today_puzzle_controller.dart:144`의 history 무효화 및 `mobile/lib/records/my_stats_controller.dart:30`의 재조회가 동작한다. 기록 선조회 여부와 무관하게 1일·1문제 및 성공 칸이 표시된다. 미완료 제출이라는 별도 입력의 잔존 문제는 아래 D-27-5로 구분한다. |
| D-27-3 | MINOR | FIXED | `mobile/lib/screens/records_tab.dart:60`·`:93`·`:127`의 열별 PageStorageKey로 390→1024→390 왕복 후 실제 ScrollPosition이 스크롤 전환 직전 값으로 복원된다. 회귀 테스트는 0보다 큰 offset을 만든 뒤 값의 동일성까지 검사하며 통과했다. |
| D-27-4 | MINOR | FIXED | `mobile/lib/screens/ranking_tab.dart:375`의 Expanded/ListView로 스켈레톤이 남는 높이 안에 제한된다. 기존 844×390 재현의 SkeletonBox 존재 및 Flutter 레이아웃 예외 없음 검사가 통과했다. |

기존 ID 4건의 지정 재현은 모두 FIXED이며 REPEAT는 없다. 신규 결함은 다음 번호부터 기록한다.

### 신규 결함

#### D-27-5 — MAJOR — 첫 오답 뒤 7일 그리드가 진행 중으로 갱신되지 않음

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:106`, `mobile/lib/puzzle/today_puzzle_controller.dart:138`, `mobile/test/screens/play_result_refresh_test.dart:182`·`:202`.
- 요구: 티켓 S4 체크박스 및 US 16a는 **성공/실패/진행 중/미플레이**를 표시하도록 요구한다. 서버 `app/services/game_rules.py:34`의 `day_result`는 0시도를 `none`, 1~4회 오답을 `in_progress`로 분류한다. `tests/test_me_history.py:69`·`:77`도 첫 오답을 낸 오늘의 history가 `in_progress`임을 검증한다.
- 재현 입력: 미플레이 게스트로 앱 시작 → 내 기록에서 오늘의 미플레이 칸을 한 번 읽음 → 오늘 탭으로 이동 → 4글자 오답 `지하촌역` 1회 제출(남은 기회 4) → 내 기록으로 돌아옴.
- 기대: 오늘 칸이 **진행 중** 고리 및 접근성 레이블로 바뀐다. 순위·streak 재조회 여부와는 별개로 history의 `none→in_progress` 전이가 반영되어야 한다.
- 실제: 오늘 칸은 **`DayResult.none`** 그대로이고 `fetchMyHistoryDays.length == 1`이다. 성공한 최초 조회에는 재시도 버튼도 없어 퍼즐을 끝내거나 앱을 재시작하기 전까지 해당 흐름에서 진행 중을 볼 수 없다.
- 직접 재현: `mobile/test/screens/play_result_refresh_test.dart`를 `/tmp/t27-r2-progress-probe_test.dart`로 복사하고 상대 import만 저장소의 절대 경로로 바꿨다. 마지막 테스트의 첫 오답 전에 Fake API의 7일 history 마지막 날을 `{ko: DayResult.inProgress, en: DayResult.none}`으로 준비하고, 제출 후 내 기록을 탭해 마지막 `DayCell.result == DayResult.inProgress`를 검증했다. 실제 앱·라우터·컨트롤러는 그대로이며 기대 결과로 provider를 덮지 않았다.
- 실행: `cd mobile && flutter test --no-pub /tmp/t27-r2-progress-probe_test.dart --reporter expanded` → **3 passed / 1 failed**, exit 1. 실패 출력은 `Expected: DayResult:<DayResult.inProgress>` / `Actual: DayResult:<DayResult.none>`이다. 앞의 정답 제출 회귀 3개는 같은 실행에서도 통과했다.
- 원인/테스트 문제: 기록 무효화를 `played.status.isFinished`에 묶었고, “7일 칸도 끝난 뒤에 바뀐다”는 주석·README 설명은 서버 계약과 다르다. 새 테스트는 오답 이후 history를 갱신하지 않는 호출 횟수 1을 정답으로 고정하고 그 뒤 화면 상태를 확인하지 않아 결함을 통과시킨다. 첫 미완료 제출의 history 전이를 검증하는 회귀가 필요하다. 데이터 손상이나 서버 기록 누락은 아니지만 명시된 상태를 정상 플레이 흐름에서 잘못 보여주므로 MAJOR다.

### 직접 실행한 검증

- `cd mobile && flutter test --no-pub --reporter expanded`: **269 passed**, exit 0. 골든 4장·원래 D-27-1~4 회귀·언어 쓰기 직렬화/늦은 응답 테스트 포함.
- `cd mobile && flutter analyze`: **No issues found**, exit 0.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: **88 files, 0 changed**, exit 0.
- `uv run ruff check .`: **All checks passed**, exit 0.
- `cd mobile && flutter build apk --debug`: **Built build/app/outputs/flutter-apk/app-debug.apk**, exit 0(Gradle 67.8초). 코디네이터 요청대로 검증 후 `mobile/build`를 삭제했다. 이번 리뷰에서 iOS 빌드는 실행하지 않았다.
- `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`을 지정한 `uv run pytest -q`: **1257 passed in 977.05s (0:16:17)**, exit 0. 기존 `chosung_daily_test_t27`·Redis DB 15·기존 `chosung_daily_test_t27_migrations`를 재사용했다. 접속에 성공하여 기본 DB 대체나 새 DB 생성은 하지 않았고 간헐 실패가 없어 재실행하지 않았다. 인증 값은 문서에 기록하지 않았다.
- 추가 경합 확인: `cd mobile && flutter test --no-pub /tmp/t27-r2-race-probe_test.dart --reporter expanded` → **3 passed**, exit 0. ① 정답 제출 중 refresh 2회는 제출 뒤 오늘 보드 재조회 1회로 합쳐지고 순위/history도 각각 추가 1회만 읽음, 중복 제출 거부 ② provider 재빌드 뒤 늦게 도착한 이전 세대 정답은 순위/history/stats 재조회를 유발하지 않음 ③ 늦은 stats 응답은 최신 재조회나 재빌드된 시작 snapshot을 덮지 않음. 기존 티켓 25의 `_generation`·`_submitting`·`_refreshQueued` 흐름을 유지함을 코드와 테스트로 확인했다.
- 추가 적응성 확인: `cd mobile && flutter test --no-pub /tmp/t27-r2-width-probe_test.dart --reporter expanded` → **6 passed**, exit 0. 실제 AdaptiveScaffold 안에서 S3/S4 각각 **320×568, 844×390, 1366×1024**를 검사했고 레이아웃 예외가 없으며 고정 me 행/7일 칸이 유지됐다. 저장소의 390/744/1024 테스트를 보완한다.
- `git diff --check main...HEAD`: exit 0. `git diff --name-only main...HEAD -- migrations`: 출력 없음. 마이그레이션 변경이 없으므로 조건부 `flask db heads` 검사는 해당 없음.
- 추가 재현 코드는 `/tmp`에만 있고 커밋 대상이 아니다. D-27-5의 입력·기대·관찰값은 위 결함 절에 남겼다.

### 보안·범위·공유 파일·참고

- 인증: 두 GET은 기존 Bearer 경로를 사용한다. 토큰 부재 시 전송하지 않는 어댑터 테스트가 통과했고, 개인정보 대신 서버의 익명 display/is_me만 그린다. 새 웹 쿠키 변경/CSRF 경로는 없다.
- 설정: 퍼즐 언어는 enum 값만 PATCH하며 쓰기 중 행 비활성·후속 요청 차단·재빌드 후 늦은 응답 폐기를 확인했다. 법적 문서 URL은 기존 API base와 고정 문서 경로로 구성한다. 계정/구독/삭제 자리는 비활성이라 실제 데이터 변경을 추가하지 않는다.
- 새 운영 키·토큰·비밀번호 기록이나 로그 노출은 발견하지 못했다. 증거의 테스트 접속 예시는 `.env.example`의 로컬 개발 형식이며 운영 시크릿으로 판정하지 않았다. 이 리뷰에는 인증 값을 복사하지 않았다.
- 공유 파일은 README 설계 판단 끝의 `### 27.`만 추가했다. `.env.example`·`docs/RELEASE.md`·`.scratch/` 및 다른 번호 절 변경이 없으며, S1의 stats 구독 변경과 제출 후 무효화는 D-27-1·2 수정에 필요한 범위다. 데이터 파괴·범위 밖 기능 추가는 발견하지 못했다.
- 목업의 이메일 대신 익명명, brand 일반 글자색 대신 foreground, 참가자 수 생략은 상위 스펙과 OVERRIDES에 근거한다. 실기기 음성 낭독·외부 브라우저 실행은 이 리뷰의 검증 범위 밖이며 취향/스타일 제안은 결함으로 올리지 않았다.

미해결 결함 합계: **BLOCKER 0 / MAJOR 1 / MINOR 0**. 기존 4건 FIXED, 신규 D-27-5 수정 및 첫 오답→내 기록 복귀 검증이 남는다.

판정: FAIL

## 라운드 3

- 검토 HEAD: `529acfe`, 로컬 `main`: `2087b48`, merge-base: `1afeffa`. `git log main..HEAD`의 13개 커밋과 `git diff main...HEAD`의 38개 파일을 확인했다. `origin/main`은 사용하지 않았다.
- 기준: 티켓 27의 6개 체크박스, 스펙 §B.21·US 12~14·16a·16b·47·48, CONTEXT, SCREENS S3·S4·T3·T4, Hidden Vowels MASTER/OVERRIDES(OVERRIDES 우선), 이전 리뷰 두 라운드와 구현 증거의 수정 라운드 2.
- 앱·테스트·설정·`.scratch/`는 수정하지 않았다. 운영 환경이나 실제 외부 서비스 API에 접속하지 않았다. 검증용 API/저장소/플랫폼 경계는 Fake를 사용했다.

### 체크박스별 확인

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient leaderboard/history(Dio + Fake) | 충족 | 인터페이스·모델·Dio GET과 서버 `app/api/puzzles.py`·`app/api/me.py` 계약을 대조했다. limit=20/days=7, Bearer, 토큰 부재 시 미전송, 최상위 history 배열 파싱 테스트가 통과했다. |
| S3 표시 전용 언어 칩, entries·내 행 강조, 목록 밖 me 고정, 빈 상태 | 충족 | `ranking_tab.dart`의 표시 전용 칩과 `LeaderboardRow.isMe`, 목록과 분리된 pinned me 행, 지정 빈 문구를 확인했다. 20명 목록 밖 23위·목록 안 내 행·빈 상태·정답 제출 후 순위 갱신 테스트가 통과했다. |
| S4 streak·7일 그리드·설정·담당 번호 자리 | 충족 | 서버 day_result의 none/in_progress/fail/success와 앱 모델·합성 규칙을 대조했다. 첫 오답 뒤 진행 중, 정답 뒤 성공·현재/최고/누적 갱신이 실제 앱 테스트에서 확인됐다. PATCH 후 홈 재조회, 법적 문서 URL, LicensePage·버전, 담당 번호 주석과 비활성 자리 8개도 확인했다. |
| 위젯 테스트: me·빈 상태·7일 그리드·언어 변경 후 재조회 | 충족 | 각 사례를 포함한 전체 Flutter 332개 테스트가 통과했다. D-27-5 회귀는 실제 라우터·제출 버튼·provider를 사용하고 마지막 DayCell의 결과까지 확인하므로 호출 횟수만 확인하던 이전 공백을 메운다. |
| 태블릿 T3·T4, 390/744/1024 분기, 자리의 열 고정 | 충족 | 4열 표·840 최대 폭, 600 읽기 폭·2열 최대 480, 지정 자리의 좌우 배치를 코드와 테스트로 확인했다. 폭 왕복 스크롤 복원 회귀도 통과했다. |
| audit.native(태블릿 포함), e3/e4·T3/T4 대비 기록 | 충족 | 증거의 감사·목업 차이 기록을 확인하고 e3/e4 PNG와 구현 골든을 직접 열어 대조했다. 토큰·행 Semantics·색 외 결과 구분·44dp 설정 행·스켈레톤을 확인했다. 골든 4장과 추가 320/844/1366 폭 재현을 실행했다. 실제 기기 감사까지 검증했다는 의미는 아니다. |

### 이전 결함 판정

| ID | 기존 심각도 | 판정 | 위치 및 입력 → 기대/실제 |
|---|---|---|---|
| D-27-1 | MAJOR | FIXED | `mobile/lib/puzzle/today_puzzle_controller.dart:152`. 순위 선조회 → 정답 제출 → 순위 복귀: 기대한 조회 1→2회·내 순위 1위·내 행 표시가 실제로 확인됐다. |
| D-27-2 | MAJOR | FIXED | `mobile/lib/puzzle/today_puzzle_controller.dart:149`·`:155`, `mobile/lib/records/my_stats_controller.dart:30`. 기록 선조회 → 정답 → 복귀: 기대한 1일·1문제·오늘 성공 칸이 표시됐다. 정답 후 기록을 처음 여는 별도 입력도 통과했다. |
| D-27-3 | MINOR | FIXED | `mobile/lib/screens/records_tab.dart:60`·`:93`·`:127`. 실제 스크롤 후 390→1024→390 왕복: 기대한 기존 offset 복원이 확인됐다. 단순 자리 존재 검사뿐 아니라 0보다 큰 offset의 동일성을 검사한다. |
| D-27-4 | MINOR | FIXED | `mobile/lib/screens/ranking_tab.dart:375`. 미완료 로딩 응답을 844×390에 표시: 스켈레톤이 존재하며 기대한 레이아웃 예외 없음이 확인됐다. Expanded 안의 ListView가 가용 높이를 제한한다. |
| D-27-5 | MAJOR | FIXED | `mobile/lib/puzzle/today_puzzle_controller.dart:148`, `mobile/test/screens/play_result_refresh_test.dart:204`. 내 기록에서 오늘 미플레이 선조회 → 오늘 탭 → `지하촌역` 첫 오답(남은 기회 4) → 내 기록 복귀: 기대한 `DayResult.inProgress` 및 history 조회 1→2회가 실제로 확인됐다. 두 번째 오답은 조회 2회를 유지하며 순위·stats는 각각 1회인 별도 검사도 통과했다. |

기존 5건 모두 FIXED, REPEAT 0건. 신규 결함은 발견하지 못했다.

### 직접 실행한 검증

- `cd mobile && flutter test --no-pub`: **332 passed**, exit 0. 골든 4장·기존 5건 회귀·설정 쓰기 직렬화/늦은 응답 검사 포함.
- `cd mobile && flutter analyze`: **No issues found**, exit 0.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: **104 files, 0 changed**, exit 0.
- `uv run ruff check .`: **All checks passed**, exit 0.
- `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`을 지정한 `uv run pytest -q`: **1353 passed in 933.54s (0:15:33)**, exit 0. 기존 `chosung_daily_test_t27`·Redis DB 15·`chosung_daily_test_t27_migrations`를 재사용했다. 새 DB 생성이나 기본 DB 대체는 하지 않았고, 간헐 실패가 없어 재실행하지 않았다. 최초 백그라운드 실행 시도는 프로세스가 유지되지 않아 출력 없이 종료되어, 이후 관리되는 세션에서 전체 검사를 다시 시작해 위 결과를 얻었다. 인증 값은 기록하지 않는다.
- `cd mobile && flutter test --no-pub /tmp/t27-r2-width-probe_test.dart /tmp/t27-r2-race-probe_test.dart --reporter expanded`: **9 passed**, exit 0. 이전 리뷰의 임시 재현 코드를 직접 읽고 현 HEAD에서 다시 실행했다. 실제 AdaptiveScaffold 안의 S3/S4 각각 320×568·844×390·1366×1024에서 예외 없음과 me/7일 칸 유지(6개), 제출 중 중복 refresh 합치기·이전 세대 제출 응답 폐기·stats 응답 역전 및 재빌드 경합(3개)을 확인했다. 이 임시 파일은 커밋 대상이 아니다.
- `git diff --check main...HEAD`: exit 0. `git diff --name-only main...HEAD -- migrations`: 출력 없음. 마이그레이션 변경이 없으므로 조건부 `flask db heads` 검사는 해당 없음.
- 이번 라운드에서 APK/iOS 빌드·실기기 스크린 리더·외부 브라우저 실행은 검증하지 않았다. 이전 증거의 해당 주장을 이번 실행 결과로 대신하지 않았다.

### 보안·범위·공유 파일

- 두 GET은 기존 Bearer 인증 경로를 쓰며 토큰 부재 시 요청하지 않는다. 새 쿠키 기반 변경/CSRF 경로는 없다. 화면은 서버의 익명 display/is_me를 사용한다.
- 설정 입력은 PuzzleLanguage enum이며 쓰기 중 재입력을 막고 재빌드 후 늦은 응답을 버린다. 계정·구독·삭제는 비활성 자리라 데이터 변경을 추가하지 않는다. 법적 문서 링크는 기존 API base와 고정 문서 경로를 사용한다.
- README 공유 변경은 자기 번호 `### 27.` 추가뿐이며 다른 번호 절을 수정하지 않았다. `.env.example`·`docs/RELEASE.md`·`.scratch/`·마이그레이션 변경은 없다. S1 stats 구독 변경과 제출 후 무효화는 기존 D-27-1·2·5 수정에 필요한 범위다.
- 변경 파일에서 새 운영 키·토큰·비밀번호 노출이나 데이터 파괴 경로를 발견하지 못했다. 증거 문서의 기존 테스트 연결 예시는 `.env.example`과 같은 로컬 개발 접속 형식이며 이 리뷰에 인증 값을 복사하지 않았다.

### 참고

- 익명명, 상위 순위의 foreground 굵은 글자, brand-subtle 내 행, T4 좌우 자리 배치를 목업·상위 명세와 대조했다. 목업의 이메일·참가자 수를 그대로 사용하지 않은 이유는 스펙 우선순위와 티켓 범위로 설명된다.
- 실기기 렌더링·음성 낭독은 자동 위젯/골든 검사의 보장 범위를 벗어난다. 취향·스타일 제안은 결함으로 올리지 않았다.

미해결 결함 합계: **BLOCKER 0 / MAJOR 0 / MINOR 0**. 기존 D-27-1~5 모두 FIXED, REPEAT 및 신규 결함 없음.

판정: PASS
