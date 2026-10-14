# 티켓 25 최종 리뷰 — 라운드 1

## 범위와 방법

- 검토 HEAD: `7708e0c`, 로컬 main: `4d83feb`, merge-base: `7df7809`. `git diff main...HEAD`와 `git log main..HEAD`의 구현 커밋 7개를 기준으로 검토했다. origin/main은 사용하지 않았다.
- 티켓 25, spec §B.21·US 1~3·3a·3b·6~8·15, CONTEXT, SCREENS S1/T1, OVERRIDES, e1_home/e7_home_dark HTML 및 구현 골든 PNG 3장을 대조했다.
- 구현 증거 문서를 읽되 검증 결과는 직접 실행한 결과로 구분했다. 아래 결함은 소스의 상태 전이와 재현 입력 순서를 추적한 결과이며, 새 회귀 테스트를 작성하거나 실행했다는 뜻은 아니다. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

## 티켓 체크박스별 판정

| 항목 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient GET today / POST guesses / PATCH me, Dio + Fake | 충족 | `api_client.dart`, `dio_api_client.dart`, Fake의 세 메서드와 API 테스트 확인. 실제 요청 경로·메서드·Bearer·puzzle_id 본문·404/409 매핑을 검사한다. |
| PuzzleBoard / GuessInput / HintCard / StreakBadge / 날짜·칩 | 충족 | r/h/s 처리, 5개 시도 행, 토큰, 카운터, 힌트 유무, flame/숫자 색 확인. 라이트·다크·태블릿 골든을 직접 열어 확인했다. 모션 규칙 누락은 D-25-4. |
| Riverpod 상태·제출·409·en 간격 복원 | 미충족 | 정상 경로와 en `s` 재삽입은 구현·테스트되어 있다. 그러나 겹친 응답이 최신 보드를 덮어쓰며(D-25-1), 오류 후 복구 및 오프라인 상태 조합이 빠졌다(D-25-2/3). |
| 앱 시작·포그라운드 GET 재조회 | 충족 | provider build와 `AppLifecycleListener.onResume`에서 호출. 실제 lifecycle 전이를 사용하는 위젯 테스트 통과. 응답 순서 보장은 D-25-1 별도. |
| Fake 위젯 테스트: 상태·409·완료·다크 | 충족 | 해당 테스트 및 골든 포함 Flutter 전체 187개 통과. 다만 아래 오류 조합·동시 요청은 검증하지 않는다. |
| 태블릿 ReadingWidth / expanded 우측 열 / 타일 유지 / 폭 변경 | 충족 | 실제 AdaptiveScaffold를 사용하는 390/744/1024 테스트, 744→390 입력·보드 유지 및 1024→744 입력 유지 테스트 통과. 1024 골든의 우측 힌트·남은 기회 확인. |
| audit.native 통과·목업 대비 스크린샷 기록 | 미충족 | 골든 기록과 폭 테스트는 존재한다. 그러나 오류/오프라인 동작 결함 및 명시된 모션 누락 때문에 전체 통과 주장은 수용할 수 없다. 실기기/시뮬레이터 확인은 수행하지 않았다. |

## 결함

### D-25-1 — 늦은 조회/제출 응답이 최신 보드와 제출 잠금을 덮어쓴다

- 심각도: **MAJOR**
- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:43`, `:62`, `:69`, `:77`
- 재현 입력/응답 순서: 퍼즐 A를 로드 → 답 제출 POST 응답을 지연 → 백그라운드/포그라운드 복귀로 GET 실행 → GET이 퍼즐 B를 반환 → A의 POST 응답을 마지막에 반환한다. 기대: B가 유지되고 A의 응답은 B의 보드에 영향을 주지 않는다. 실제: 제출 시작 시 캡처한 `puzzle` A에 `applyGuess`를 적용하여 B를 A로 되돌린다. POST 오류 catch도 캡처한 A를 다시 쓴다.
- 같은 퍼즐에서도 재현된다: 제출 전 이력을 읽은 GET 응답을 지연 → POST 성공으로 새 행 표시 → GET 응답 도착. 기대: 성공한 행·남은 기회 유지. 실제: GET의 이전 이력으로 행이 사라지고 기회가 되돌아간다. 반대로 POST 대기 중 GET이 먼저 끝나면 `_load()`가 `submitting: false`인 상태를 만들어 중복 제출도 다시 허용한다.
- 원인: 조회·제출·409 재조회 어느 경로에도 요청 세대/현재 퍼즐 검증 또는 상호 순서 보장이 없다. 서버의 puzzle_id 검증은 잘못된 퍼즐에 쓰는 것을 막지만 클라이언트의 상태 역행과 중복 시도는 막지 않는다. US 3a/3b 및 서버 이력 정본 요구에 어긋난다.
- 테스트 공백: 현재 Fake의 POST는 지연 없이 반환하며, 컨트롤러 테스트는 조회와 제출을 각각 순차적으로만 완료한다. 지연된 POST·GET 및 역순 응답을 다루는 회귀 검증이 필요하다. 아직 호출자가 없는 PATCH 언어 변경의 순서 문제는 이 티켓 결함으로 추정하여 추가하지 않았다.

### D-25-2 — 보드가 있는 상태의 네트워크 실패에는 재시도 경로가 없다

- 심각도: **MAJOR**
- 위치: `mobile/lib/screens/today_tab.dart:59`, `:111`, `:134`; `mobile/lib/puzzle/today_puzzle_controller.dart:88`
- 재현 입력: 정상 보드 로드 → 제출을 `NetworkApiException`으로 실패시킴 → 앱을 포그라운드에 그대로 둔 채 연결 복구. 기대: 인라인 재시도로 다시 조회하고 입력을 사용할 수 있다(US 8, OVERRIDES §7). 실제: `TodayNotice.offline`이 유지되어 입력·제출이 계속 비활성이고 보드에는 재시도 버튼이 없다. 연결 변경 구독도 없어 앱을 내렸다 올리거나 다시 시작해야 복구된다.
- 조회 실패도 빠져 있다: 정상 보드 로드 → 포그라운드 GET을 서버 오류로 실패시킴. Riverpod 3.3.2의 `AsyncError.copyWithPrevious`가 이전 값을 유지하므로 `hasError`보다 앞의 Ready 분기가 선택된다. `_Board`에는 오류 자체가 전달되지 않아 오류 카드·재시도 없이 이전 화면이 정상처럼 남는다. 409 뒤 재조회 실패도 같은 분기를 타며 이전 `submitting: true`까지 남을 수 있다.
- 테스트 공백: 최초 로딩 오류에서의 재시도만 테스트하며, 제출 오프라인 테스트는 비활성까지 확인하고 연결 복구를 확인하지 않는다.

### D-25-3 — 이전 안내 메시지가 있으면 재조회 오프라인 오류를 무시한다

- 심각도: **MAJOR**
- 위치: `mobile/lib/screens/today_tab.dart:63`
- 재현 입력: 제출 409 → 재조회 성공으로 `TodayNotice.puzzleChanged` 표시 → 이후 포그라운드 GET을 `NetworkApiException`으로 실패시킴. 기대: 기존 보드 위 OfflineBanner 표시 및 입력 비활성. 실제: 이전 Ready 값과 notice가 유지되고 `ready.notice?.blocksInput`이 **false**이므로 `?? _isOffline(state.error)`의 오른쪽은 평가되지 않는다. 오프라인인데 배너가 없고 입력/제출이 활성 상태다. `submitFailed` 안내 뒤에도 동일하다.
- D-25-2의 재시도 버튼 누락과 별개의 판정 오류다. 이전 notice 유무와 현재 네트워크 오류를 함께 다루는 검증이 필요하다.

### D-25-4 — 명시된 타일 피드백 전환 모션이 없다

- 심각도: **MINOR**
- 위치: `mobile/lib/widgets/puzzle_board.dart:33`, `:127`
- 재현 입력: 모션 감소 설정을 끈 상태에서 유효한 답 제출 → 응답 수신. 기대: OVERRIDES §7의 타일 뒤집기 350ms/행 stagger 60ms, 모션 감소 시 즉시 표시. 실제: StatelessWidget의 Container 색·텍스트가 즉시 바뀌고 애니메이션 경로가 없다.
- 구현 증거 §4도 이를 후속 폴리시로 넘겼지만 티켓 25가 참조하는 디자인 규칙에는 그러한 유예가 없다. 취향 제안이 아니라 명시 요구 누락이며, 플레이 자체는 가능하므로 MINOR로 분류한다.

## 직접 실행한 검증

- `uv run ruff check .`: **All checks passed**, exit 0.
- `cd mobile && flutter analyze`: **No issues found**, exit 0.
- `cd mobile && flutter test`: **187 passed**, exit 0. 골든 3장 포함.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **69 files, 0 changed**, exit 0. 리뷰 중 파일 변경을 피하려고 출력만 검사했다.
- `cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug`: **assembleDebug 성공**, exit 0. 생성된 `mobile/build`와 `mobile/android/.kotlin`은 제거했다.
- 백엔드 전체 `uv run pytest -q`: **800 passed in 671.94s (0:11:11)**, exit 0. `TEST_DATABASE_URL`은 지정된 기존 로컬 DB `chosung_daily_test_t25`, `TEST_REDIS_URL`은 `redis://127.0.0.1:6379/13`, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t25_migrations`로 지정했다. 새 DB 생성이나 기본 DB 폴백은 하지 않았고, 간헐 실패가 없어 재실행하지 않았다. 접속 문자열의 인증 부분은 기록하지 않는다.
- 변경에 마이그레이션 파일이 없으므로 티켓별 `flask db heads` 검사는 해당 없음.

## 범위·보안·증거 신뢰성

- 변경은 mobile 구현/테스트/번역과 README의 자기 번호 `### 25.`, 구현 증거 문서로 한정된다. 다른 티켓 소제목 내용, `.env.example`, `.scratch/`, 백엔드 및 마이그레이션 변경은 없다. 테마의 버튼 글꼴 보완은 이 화면의 지정 글꼴 요구에 해당한다.
- 추가된 인증 요청은 Bearer를 사용하며 토큰이 없으면 요청하지 않는다. 쿠키 기반 웹 쓰기를 추가하지 않아 새 CSRF 경계가 생기지 않았다. 길이 검증과 puzzle_id 동봉을 확인했고, 변경 파일에 실제 비밀번호·키·토큰을 기록한 흔적은 발견하지 못했다. 테스트의 고정 토큰 문자열은 Fake 값이다.
- 새 테스트는 API 경계만 Fake로 두고 실제 위젯/컨트롤러를 검사한다. 항상 참인 테스트로 보이지는 않지만 D-25-1~3의 조합을 누락하여 전체 녹색만으로 상태 안전성을 입증할 수 없다.
- 보상형 힌트 버튼과 결과 시트 연결은 티켓에서 각각 31/26으로 명시적으로 넘겼으므로 비활성 버튼 자체는 결함으로 세지 않았다. 스크린샷은 테스트 렌더러 증거이며 실기기 IME/스크린리더 검증을 대신하지 않는다.

## 참고

취향·스타일 제안은 결함에 포함하지 않았다. 테스트·빌드 통과와 별개로 MAJOR 3건, MINOR 1건, BLOCKER 0건이다.

판정: FAIL

## 라운드 2

### 범위와 방법

- 검토 HEAD `42333e7`, 로컬 `main` 및 merge-base `82e59ea`. `git diff main...HEAD`, `git log main..HEAD`의 11개 커밋을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 25와 spec §B.21·US 1~3·3a·3b·6~8·15, CONTEXT, SCREENS S1/T1, OVERRIDES, 구현 증거 §8 및 이전 리뷰를 대조했다. 골든 PNG 3장을 직접 열었고 관련 API·컨트롤러·위젯·레이아웃 테스트를 읽고 실행했다.
- 하위 에이전트 없이 검토했다. 소스 추적으로 확인한 결함과 실행한 기존 테스트를 구분한다. 새 테스트나 애플리케이션·설정·`.scratch/` 수정은 하지 않았다.

### 티켓 체크박스별 판정

| 항목 | 판정 | 근거 |
|---|---|---|
| ApiClient GET today / POST guesses / PATCH me, Dio + Fake | 충족 | Dio 어댑터 테스트가 실제 메서드·경로·Bearer·puzzle_id·언어 본문 및 404/409 매핑을 확인한다. 토큰 없는 요청 차단도 확인했다. |
| PuzzleBoard / GuessInput / HintCard / StreakBadge / 날짜·칩 | 충족 | r/h/s, 시도 5행, correct 체크/오답 취소선, 길이 카운터, 잠김/열림 힌트, flame/숫자 색과 날짜·칩을 확인했다. 뒤집기와 모션 감소도 구현됐다. |
| Riverpod 상태·제출·409·en 간격 복원 | 충족 | 보드 유무별 오류 복구, 제출 잠금, 세대 검사, 409 재조회, 완료 버튼, 퍼즐 없음 카드, en 구분자 재삽입을 소스 및 통과한 테스트로 확인했다. D-25-1~3 FIXED. |
| 앱 시작·포그라운드 GET 재조회 | 충족 | build 및 AppLifecycleListener.onResume 경로, 실제 lifecycle 전이 테스트 확인. 제출 중 복귀는 제출 뒤 재조회하도록 직렬화한다. |
| Fake 위젯 테스트: 상태·409·완료·다크 | 충족 | Flutter 전체 202개 통과. 오프라인 복구·재조회 서버 오류·기존 안내 이후 오프라인과 모션 회귀 테스트가 추가됐다. |
| 태블릿 ReadingWidth / expanded 우측 열 / 타일 유지 / 폭 변경 | 미충족 | 보드·입력 600 이하, 우측 320 이하, 390/744/1024 분기와 744→390 입력·보드 유지 및 1024→744 입력 유지는 충족. 참조 명세 T1의 상태 UI 왼쪽 열 배치는 D-25-5로 미충족이다. |
| audit.native·목업 대비 스크린샷 기록 | 미충족 | 라이트·다크·태블릿 골든 3장 존재 및 재검증 통과. 소스·위젯 수준 접근성/테마/폭 검증은 확인했으나 T1 상태 배치 누락으로 완전 충족으로 보지 않는다. 실기기 IME·스크린리더 확인은 이 실행에서 하지 않았다. |

### 이전 결함 재판정

| ID | 이전 심각도 | 판정 | 현재 근거 |
|---|---|---|---|
| D-25-1 | MAJOR | **FIXED** | `today_puzzle_controller.dart:63`의 제출 중 재조회 큐, `:70`의 초기 로딩 중 중복 조회 차단, `:91`의 제출 세대 증가, `:134`의 공통 반영 조건으로 늦은 응답을 버린다. `:42`의 build 세대 증가도 확인. 컨트롤러 테스트 241/274/297/312/335행이 응답 순서를 제어하며 상태·호출 수·잠금을 검사하고 모두 통과했다. |
| D-25-2 | MAJOR | **FIXED** | `_commitLoad`가 보드를 보존하면서 offline/refreshFailed 안내와 해제된 제출 잠금으로 바꾼다. `today_tab.dart:140`, `:153`, `:307` 및 `offline_banner.dart:41`의 재시도는 refresh를 호출한다. 위젯 테스트에서 실제 재시도 버튼을 누른 뒤 배너 제거·입력 활성·GET 호출 수를 확인한다. 409 뒤 GET 실패 테스트도 잠금 해제를 확인한다. |
| D-25-3 | MAJOR | **FIXED** | `today_tab.dart:73`은 notice와 네트워크 오류를 OR로 판정하며, `_commitLoad`가 이전 puzzleChanged 안내를 새 offline 안내로 교체한다. 409 성공→복귀 GET 네트워크 실패 순서의 컨트롤러/위젯 테스트가 배너·보드 유지·입력 및 제출 비활성을 확인한다. |
| D-25-4 | MINOR | **FIXED** | `puzzle_board.dart:66`의 350ms/60ms 값, `_FlipIn`의 행별 Interval·회전, `:99`의 disableAnimations 즉시 완료 경로 확인. 위젯 테스트가 진행 중 Transform, 완료 후 제거, 모션 감소 시 애니메이션 없음을 검증한다. |

### 구현 증거의 경합 표 직접 대조

| 표 행 | 실제 검증 및 판단 |
|---|---|
| #1 제출→복귀, 새 퍼즐 | `today_puzzle_controller_test.dart:241`: POST gate를 잡고 퍼즐을 41→42로 바꾼 뒤 refresh. GET이 아직 안 떠났고 이전 보드/잠금이 유지되며, POST 완료 후 GET으로 42가 되는 것을 검사한다. 통과. |
| #2 제출→복귀, 같은 퍼즐/잠금 | #1과 같은 테스트에서 `submitting == true` 및 GET 호출 수를 검사한다. 별도 같은-ID 데이터 사례나 두 번째 submit 호출 검증은 없지만 큐 분기는 ID와 무관하고 submit의 잠금 검사도 확인했다. 증거 표가 같은 테스트를 가리키는 설명은 정확하다. |
| #3 재조회→제출→늦은 GET | `:274`: Fake GET은 호출 시점 보드를 캡처하고 gate로 지연한다. POST 후 GET을 풀어도 새 행 1개·기회 4가 유지된다. 통과. |
| #4 재조회→더 최신 재조회 | `:335`: 첫 응답 기회 4를 붙잡고 두 번째 응답 기회 3을 먼저 완료한다. 늦은 응답 이후에도 3 유지. 통과. |
| #5 첫 build→복귀 | `:297`: 첫 GET gate 중 refresh를 호출해 GET이 1회인지 검사한 후 첫 응답을 완료한다. 통과. |
| #6 409→재조회 실패 | `:430`: POST 409 뒤 GET 서버 오류로 보드 41·refreshFailed·submitting false를 검사한다. 통과. |
| #7 retry 재빌드→이전 POST | `:312`: POST를 붙잡고 invalidateSelf로 다시 build한 뒤 POST를 완료하여 false 반환·행 없음·잠금 해제를 검사한다. 통과. notifier를 새 객체로 교체한다는 테스트 주석은 부정확하지만, 실제 코드는 동일 notifier의 build에서 세대를 올려 응답을 무효화한다. |
| #8 언어 PATCH→조회 | 현재 앱 호출자가 없어 이 티켓 범위 밖이다. 코디네이터의 범위 확인과 일치하며 검증 완료로 세지 않는다. |

Fake는 API 경계에만 있고 실제 notifier/위젯을 실행한다. GET의 호출 시점 응답 캡처 덕분에 늦은 옛 응답이 실제로 만들어지며 항상 통과하도록 새 값을 읽는 mock이 아니다. 모션 테스트는 정확한 350/60ms 경계값 각각을 단언하지 않으므로 그 수치는 소스 검토 근거로 구분한다.

### 새 결함

#### D-25-5 — expanded 상태 UI가 T1의 왼쪽 열을 따르지 않는다

- 심각도: **MINOR**
- 위치: `mobile/lib/screens/today_tab.dart:153`, `:334`, `:430`
- 요구: SCREENS T1은 “상태 4종(스켈레톤·오프라인 배너·퍼즐 없음·완료)은 왼쪽 열 안에서 폰과 같은 자리”라고 명시한다.
- 재현 입력: 폭 1024dp의 AdaptiveScaffold에서 (1) 정상 보드를 받은 뒤 GET을 NetworkApiException으로 실패시키거나, (2) 최초 GET을 지연하거나, (3) NO_PUZZLE_TODAY로 응답한다.
- 기대: 배너·스켈레톤·퍼즐 없음 카드가 보드와 같은 왼쪽 열(최대 600dp) 위치에 놓인다. 실제: (1)은 두 열을 만드는 Row 밖 상위 Column에 배너가 있어 우측 힌트 열까지 걸치며, (2)/(3)은 expanded 분기 없이 ReadingWidth로 전체 콘텐츠 중앙에 놓인다. 완료 버튼만 보드의 왼쪽 열 안에 있다.
- 확인 방법: 위 위치의 부모/자식 배치와 ReadingWidth의 Center 동작을 직접 추적했다. 새로운 화면 재현 테스트를 실행한 것은 아니다. 기존 태블릿 테스트는 정상 보드 배치만 검증하고 상태별 좌표를 검사하지 않는다.
- 영향: 오류 복구나 플레이 데이터는 정상이고 지정된 태블릿 상태 배치만 어긋나므로 MINOR다. 취향 제안이 아닌 명시된 배치 요구 누락이다.

### 직접 실행한 검증

- `uv run ruff check .`: **All checks passed**, exit 0.
- `cd mobile && flutter analyze`: **No issues found**, exit 0.
- `cd mobile && dart format --output=none --set-exit-if-changed .`: **69 files, 0 changed**, exit 0. 파일을 쓰는 format 옵션은 사용하지 않았다.
- `cd mobile && flutter test`: **202 passed**, exit 0, 골든 3장 포함.
- `cd mobile && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug`: **assembleDebug 44.9s, APK 생성 성공**, exit 0. 실행이 만든 `mobile/build`와 `mobile/android/.kotlin`은 제거했다.
- 백엔드 전체 `uv run pytest -q`: **996 passed in 707.63s (0:11:47)**, exit 0. `TEST_DATABASE_URL`은 기존 로컬 `chosung_daily_test_t25`, `TEST_REDIS_URL`은 `redis://127.0.0.1:6379/13`, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t25_migrations`를 지정했다. 새 DB 생성·기본 DB 폴백·간헐 실패 재실행은 없었다. 접속 문자열의 인증 부분은 기록하지 않는다.
- 변경 파일에 마이그레이션이 없어 티켓별 `flask db heads` 검사는 해당 없음.
- `git diff --check main...HEAD`: exit 0.

### 범위·보안·참고

- 변경된 인증 API는 Bearer를 사용하고 토큰 부재 시 요청을 차단한다. 제출에는 puzzle_id와 정규화된 답을 동봉하고 길이·완료·제출 중 상태를 검사한다. 새 쿠키 쓰기 경로가 없으므로 CSRF 경계를 추가하지 않는다. 서버 저장 규칙 변경이나 데이터 손상 경로, 실제 시크릿을 추가한 흔적은 발견하지 못했다.
- README는 자기 번호 `### 25.` 내용만 추가하며 다른 티켓 본문은 고치지 않는다. `.env.example`, `.scratch/`, 백엔드·마이그레이션은 diff에 없다. 이번 리뷰의 추적 파일 변경은 이 문서 하나뿐이다.
- 결과 시트/광고 힌트 버튼 연결은 각각 26/31 소관이므로 비활성 자체를 결함으로 세지 않았다. 실기기/시뮬레이터 증거는 골든으로 대체됐다고 주장하지 않는다. 취향·스타일 제안은 추가하지 않았다.
- 미해결 결함: **BLOCKER 0 / MAJOR 0 / MINOR 1**. 기존 4건 FIXED, REPEAT 0건. 새 D-25-5만 남는다.

판정: PASS
