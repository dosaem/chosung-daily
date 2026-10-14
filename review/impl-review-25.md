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
