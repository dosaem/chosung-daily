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
