# 티켓 26 최종 리뷰 — 라운드 1

검토일: 2026-10-14. 기준은 로컬 `main` (`24c584d`)과 구현 HEAD `5349e28`의 `git diff main...HEAD`, `git log main..HEAD` 6개 커밋이다. 티켓 26, 스펙 §B.20·21·24 / US 6·9·10·11·20 / 미정 20, SCREENS S2·T2, OVERRIDES, CONTEXT, 구현 증거를 대조했다. 애플리케이션·테스트·설정·스펙은 수정하지 않았다.

## 티켓 체크박스

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient `GET /puzzles/today/stats`, Dio + Fake | 충족 | 인터페이스·Dio·Fake 구현 및 모델 존재. Dio 테스트가 실제 요청 경로·GET·Bearer 헤더와 응답 파싱, 404 예외를 검증한다. |
| S2 성공/실패 헤더, 분포+내 위치, KST 카운트다운, 링크 포함 네이티브 공유, 연결 안내 자리 | 미충족 | 정상 경로의 헤더·분포·공유·카운트다운·닫기 테스트는 통과하지만, 다른 날짜/언어의 분포를 현재 결과에 붙일 수 있다(D-26-1). 연결 동작·1회 플래그는 명시적으로 29 범위이므로 누락으로 세지 않는다. |
| Analytics 인터페이스 / Firebase / no-op, 이벤트 4개, 미정 20 기록 | 충족 | 이벤트 이름·파라미터 순수 함수, Firebase 전달, 초기화 성공/생략별 provider 테스트 통과. `puzzle_complete`는 제출 완료 경로, `share`는 공유 경로에 있다. README `### 26.` 및 미정 항목 끝 자기 티켓 항목만 추가했다. |
| 결과 성공/실패, 공유 텍스트, 이벤트 위젯 테스트 | 충족 | 실제 UI 제출→시트 및 이벤트 파라미터를 검사한다. 공유 테스트는 전달 텍스트·링크·정답 미포함을 검사한다. 무조건 통과하는 테스트는 발견하지 못했다. 다만 날짜/언어 불일치 입력은 빠져 있다. |
| T2 adaptive sheet, 744 다이얼로그 ≤560, 공유·순위 동작 | 충족 | `showAdaptiveSheet` 재사용. 390/744/1024 위젯 테스트 및 744 골든 통과. 744에서 공유 전달과 순위 콜백·시트 닫기를 확인한다. |
| `audit.native` 태블릿 포함, `e2_result` 대조 기록 | 충족 | 증거 §4의 소스 감사·§5 골든 기록 존재. 리뷰에서도 390 라이트/다크·744 골든을 열어 목업과 대조했고, 실제 테스트로 레이아웃을 재검증했다. 아래 검증 한계를 별도로 명시한다. |

## 결함

### D-26-1 — MAJOR — 다른 퍼즐의 통계에 이전 퍼즐의 내 위치를 표시한다

- 위치: `mobile/lib/widgets/result_sheet.dart:280` (288~291의 `StatBar` 조합), `mobile/lib/puzzle/today_stats_provider.dart:10`, `mobile/lib/api/dio_api_client.dart:92`.
- 원인: 시트는 열 때의 `TodayPuzzle` 스냅숏을 유지하지만 통계는 인자 없이 `/puzzles/today/stats`를 조회한다. 서버 `app/api/puzzles.py:59`는 요청 시점의 KST 날짜와 게스트 선호 언어를 사용한다. `TodayStats`가 날짜·언어를 파싱해도 화면은 둘을 비교하지 않고, 새 통계의 비율에 이전 퍼즐의 `attemptsUsed(puzzle)`를 강조한다. Riverpod의 최신 요청 처리만으로 서로 다른 퍼즐을 같은 퍼즐로 취급하는 문제는 막지 못한다.
- 재현 입력: KST 자정 전에 한국어 퍼즐을 2회에 완료하고 결과 시트의 통계 요청을 실패시킨다. 시트를 유지한 채 다음 날 퍼즐이 준비된 후 통계의 ‘다시 시도’를 누른다. 또는 같은 날 다른 기기에서 같은 게스트의 선호 언어를 영어로 변경한 후 그 재시도를 누른다. 로컬 Fake로 재현할 경우 `solvedPuzzle()`과 함께 `fakeTodayStats(date: DateTime(2026, 10, 14), language: PuzzleLanguage.en, totalSolved: 10, byAttempt: {1: 1, 2: 0})`를 제공하면 된다.
- 기대: 시트의 날짜·언어와 일치하는 통계만 표시하고 내 위치를 강조한다. 일치하지 않으면 분포 표시를 보류하고 새 퍼즐 안내/재조회 등으로 처리한다.
- 실제: 이전 한국어 정답·공유 결과 아래 새 날짜/영어 분포가 표시되고, 풀지 않은 그 퍼즐의 2회 행에 ‘내 결과’를 붙인다. 새 통계의 `totalSolved == 0`이면 자신은 성공한 결과인데도 ‘아직 아무도 못 풀었어요’를 표시한다.
- 확인 수준: 서버 선택 로직→Dio 요청→provider→화면 분기를 직접 추적해 확인했다. 위 경계 입력은 기존 테스트에 없으며, 리뷰의 테스트 수정 금지에 따라 별도 회귀 테스트를 추가하거나 실행했다고 주장하지 않는다. 기존 통계 테스트는 동일 날짜·언어만 사용한다.
- 수정 방향: 조회를 결과 퍼즐의 언어에 고정하고 응답의 날짜·언어를 스냅숏과 대조해야 한다. 날짜가 바뀌었거나 일치하지 않는 늦은 응답/재시도에 대한 회귀 검증이 필요하다.

## 직접 실행한 검증

- `uv run ruff check .`: `All checks passed!`.
- `cd mobile && flutter analyze`: `No issues found!`.
- `cd mobile && flutter test --reporter compact`: **256 passed**, 골든 포함.
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: **85 files, 0 changed**. 읽기 전용 옵션으로 수행했다.
- `cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug`: **성공**, `app-debug.apk` 생성. 코디네이터 지시에 따라 검증 후 `mobile/build`를 삭제했다.
- `uv run pytest -q`: **1110 passed in 654.11s (0:10:54)**, exit 0. `TEST_DATABASE_URL`은 로컬 기존 DB `chosung_daily_test_t26`, `TEST_REDIS_URL`은 로컬 Redis DB 14, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t26_migrations`를 가리키도록 지정했다. 새 DB 생성·기본 DB 대체·간헐 실패 재실행은 없었다. 접속 비밀번호는 문서에 남기지 않는다.
- 마이그레이션 diff가 없으므로 `flask db heads` 확인 대상은 아니다.
- `git diff --check main...HEAD`: 통과.

## 보안·범위·검증 한계

- 분석 이벤트는 퍼즐 언어·성공 1/0·시도 수만 담으며 토큰·이메일·정답을 담지 않는다. 개인정보 처리방침의 앱 사용 집계 이벤트 설명과 일치한다. 설정 파일이 없으면 Firebase 초기화 생략 결과에 따라 no-op이 선택된다.
- 신규 API는 기존 인증 전달 경로를 사용한다. 백엔드 쓰기·스키마 변경이 없고 새 인증/CSRF 우회, 데이터 손상 경로, 새 시크릿 값 기록은 발견하지 못했다.
- 공유 텍스트에는 가림·피드백·결과·지정된 UTM 링크만 들어간다. 실제 OS 공유창 및 Firebase 서버 수신은 확인하지 않았다. 외부 서비스·프로덕션에 접근하지 않았다.
- 공유 위젯 테스트의 provider 대체는 전달 텍스트와 이벤트까지 검증하며 OS 플러그인 실행을 증명하지 않는다. 설치된 `share_plus 13.3.1`의 iOS 구현은 origin이 없으면 iPad 중앙 앵커를 제공하므로 과거 버전의 origin 필수 제약을 결함으로 올리지 않았다.
- README·스펙 공유 파일은 자기 번호 항목만 끝에 추가했다. 범위 밖 변경과 병렬 티켓의 기존 내용 덮어쓰기는 발견하지 못했다.
- 목업 대비 더 진한 타인 분포 막대, Lucide 아이콘, 실제 시도 수의 타일, 태블릿 중앙 다이얼로그는 OVERRIDES 및 T2와 일치한다. 취향·스타일 제안은 결함으로 기록하지 않았다.

결함 수: BLOCKER 0 / MAJOR 1 / MINOR 0. D-26-1 수정과 경계 조건 회귀 검증이 남는다.

판정: FAIL

## 라운드 2

검토일: 2026-10-14. 로컬 `main` (`45d790c`) 대비 구현 HEAD `9427057`의 `git diff main...HEAD` 및 `git log main..HEAD` 9개 커밋을 확인했다. 이전 리뷰와 구현 증거의 수정 라운드 1, 티켓 체크박스, 스펙 §A' 통계 API·§B.20/21/24·US 6/9/10/11/20·미정 20, SCREENS S2/T2, OVERRIDES, CONTEXT를 대조했다. 아래 결과는 증거 문서의 성공 주장을 복사하지 않고 직접 코드·테스트·빌드·골든을 확인한 결과다.

### 티켓 체크박스

| 체크박스 | 판정 | 근거 |
|---|---|---|
| ApiClient `GET /puzzles/today/stats`, Dio + Fake | 충족 | `api_client.dart:37`, `dio_api_client.dart:89`에서 언어를 필수로 받고 GET 쿼리와 기존 Bearer 인증에 전달한다. Fake도 같은 인터페이스를 구현하며 Dio 테스트가 경로·메서드·헤더·`language=en`·파싱·404 매핑을 직접 검사한다. |
| S2 성공/실패 헤더, 분포+내 위치, KST 카운트다운, 링크 포함 공유, 연결 안내 자리 | 충족 | `result_sheet.dart`의 렌더·재시도·분포·공유 테스트 통과. `TodayStats.isFor` 검사로 다른 퍼즐의 통계를 숨기므로 D-26-1은 FIXED다. 공유에 지정 URL이 포함되고 정답은 빠진다. 연결 동작·1회 플래그는 티켓에서 명시적으로 29 소유다. |
| Analytics 인터페이스·Firebase·no-op, 이벤트 4개 및 미정 20 기록 | 충족 | 이름·파라미터 생성과 전송 서비스가 분리돼 있고 초기화 결과에 따라 구현을 선택한다. 완료 제출에서 `puzzle_complete`, 공유 후 `share`를 호출한다. 나머지 두 이벤트는 32 발화 대상으로 정의돼 있다. 미정 20에 자기 티켓 항목만 추가했다. |
| 결과 성공/실패, 공유 텍스트, 이벤트 위젯 테스트 | 충족 | 실제 제출→결과 시트와 이벤트 이름·파라미터를 검사한다. 공유는 외부 플랫폼 접점만 Fake로 바꾸고 전달 텍스트와 이벤트를 확인한다. D-26-1 회귀 테스트는 실제 시트에서 `StatBar` 부재·안내 문구를 검증한다. |
| T2 adaptive sheet, 744 다이얼로그 ≤560, 공유·순위 동작 | 충족 | `showAdaptiveSheet` 재사용. 390/744/1024 테스트에서 시트 종류·폭·중앙·상하 여백과 744 공유 전달·순위 콜백·닫기를 확인한다. |
| `audit.native` 태블릿 포함, `e2_result` 대조 기록 | 충족 | 증거 §4에 5축 감사와 목업 대비 기록이 있다. 리뷰에서 `e2_result.png`와 라이트·다크 390 및 744 골든을 직접 열어 대조했고 전체 테스트에서 골든을 재검증했다. 정상 결과의 토큰·레이아웃은 유지되며 새 불일치 안내는 기존 보조 텍스트 스타일을 사용한다. 실기기 검증 한계는 아래와 같다. |

### 이전 결함 판정

#### D-26-1 — FIXED (이전 MAJOR)

- 위치: `mobile/lib/api/dio_api_client.dart:89`, `mobile/lib/puzzle/today_stats_provider.dart:15`, `mobile/lib/api/api_models.dart:399`, `mobile/lib/widgets/result_sheet.dart:263`.
- 재현 입력: 2026-10-13 한국어 성공 결과에 2026-10-14 통계, 또는 같은 날짜 영어 통계를 제공한다. 별도로 다음 날짜의 `totalSolved: 0` 응답을 제공한다.
- 기대: 결과 퍼즐의 언어로 조회하며 날짜·언어가 다른 분포와 내 위치를 표시하지 않는다. 다른 날 0명 집계로 이전 성공 결과를 ‘아직 아무도 못 풀었어요’라고 표시하지 않는다.
- 현재 실제: provider가 결과 언어를 Dio `language` 쿼리로 전달한다. 응답의 연·월·일과 언어를 `isFor`로 대조하고, 불일치 분기가 빈 집계 분기보다 먼저 실행되어 안내만 표시한다. 정상 성공 헤더는 유지된다.
- 직접 확인: 전체 Flutter 테스트에서 해당 회귀 위젯 4개, `isFor` 단위 4개, Dio 요청 검증이 통과했다. 기존 오류→재시도 테스트도 통과한다. 새 불일치 위젯 테스트는 재시도 타이밍 자체를 재현하지 않고 불일치 응답을 직접 주입한다는 범위는 구분했다. 응답 처리 분기가 최초 조회·재시도에 공통이므로 이 차이는 결함으로 보지 않는다.

### 신규 결함

없음. 활성 결함 **BLOCKER 0 / MAJOR 0 / MINOR 0**, 이전 D-26-1 **FIXED**, REPEAT 0.

### 직접 실행한 검증

- `uv run ruff check .`: `All checks passed!` (exit 0).
- `cd mobile && flutter analyze`: `No issues found!` (exit 0).
- `cd mobile && flutter test --reporter compact`: **264 passed**, 골든 포함 (exit 0).
- `cd mobile && dart format --output=none --set-exit-if-changed lib test`: **85 files, 0 changed** (exit 0).
- `cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug`: 성공, `app-debug.apk` 생성 (exit 0). 코디네이터 요청대로 생성된 `mobile/build`를 제거했다.
- `uv run pytest -q`: **1257 passed in 829.69s (0:13:49)** (exit 0). `TEST_DATABASE_URL`은 로컬 기존 `chosung_daily_test_t26`, `TEST_REDIS_URL`은 로컬 Redis DB 14, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t26_migrations`로 지정했다. 새 DB 생성·기본 DB 대체·간헐 실패 재실행은 없었다. 접속 비밀번호는 기록하지 않는다.
- 마이그레이션 변경이 없으므로 `flask db heads` 확인 대상은 아니다.

### 보안·범위·검증 한계 및 참고

- 신규 서버 쓰기·스키마 변경이 없고 인증은 기존 Bearer 경로를 사용한다. 이벤트는 언어·성공 여부·시도 수만 포함한다. 이번 diff에서 신규 시크릿 값 기록, 인증/CSRF 우회, 데이터 손상 경로는 발견하지 못했다.
- 공유 파일은 README `### 26.`과 스펙 미정 항목 끝의 티켓 26 기록만 추가했다. 카운트다운 추출과 다이얼로그 테마는 해당 화면 구현에 필요한 변경이다.
- 네이티브 공유 UI 실기기 표시와 Firebase 실제 수신은 검증하지 않았다. 플랫폼 접점 Fake는 텍스트/이벤트 전달까지만 보장한다. 고정 의존성 `share_plus 13.3.1`의 로컬 iOS 구현은 origin 미지정 시 iPad 중앙의 유효한 사각형으로 보완하므로 origin 생략만을 태블릿 결함으로 올리지 않았다.
- 참고: `git diff --check main...HEAD`는 `review/impl-evidence-26.md:396: new blank line at EOF`로 exit 2였다. 기능 결함이 아닌 문서 끝 공백이므로 결함 ID를 부여하지 않았고 소유권 밖 문서를 수정하지 않았다.
- 이번 리뷰는 애플리케이션·테스트·설정·`.scratch/`를 수정하지 않았으며, 운영 환경이나 실제 외부 서비스에는 접근하지 않았다.

판정: PASS
