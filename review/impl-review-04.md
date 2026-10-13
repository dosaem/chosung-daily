# 티켓 04 최종 리뷰 — 라운드 1

## 검토 범위

- 구현 HEAD: `1a90240629b72c4b36106f518954f607bf5868af`.
- 로컬 `main`: 검토 시 `0abb1d79d8eea3701893e57313745ad566e19632`; merge-base는 `20d279a256d0f17152ae6ac273f4758c80fbb712`.
- `git diff main...HEAD` 전체와 `git log main..HEAD`의 `e4ae48d`, `3918e5c`, `ec51d6e`, `1a90240`을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 04, 스펙 §A.2·API 표·Testing Decisions·미정 12/13, `CONTEXT.md`, `review/impl-evidence-04.md`를 대조했다.
- `design/SCREENS.md`와 `design-system/hidden-vowels/OVERRIDES.md`를 확인했다. 웹 변경은 퍼즐 ID 저장/전송뿐이며 화면·CSS 변경은 없다.

## 체크박스별 판정

| 티켓 요구 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| ID 누락/다른 날짜·언어의 ID는 409, Attempt·GuestStats 불변 | 충족 | `app/schemas/guess.py:8`, `app/services/guess_service.py:44`에서 잠금·쓰기 전에 거절한다. 신규 테스트의 ID 누락, 어제 퍼즐, 언어 PATCH 후 옛 ID 제출, 정상 ID 케이스가 통과했다. 어제 퍼즐 테스트는 시도 0과 통계 불변도 검사한다. |
| 공백·하이픈 제거, en 대소문자 무시, 길이 오류 시 미소비, 피드백 위치 일치 | 충족 | `app/services/game_rules.py:33`, `app/services/guess_service.py:54`. 실제 HTTP 테스트에서 `Harry Potter`/`harry-potter` 동일 정답 응답, `harry-rotter`의 11자리 피드백, 길이 오류 400과 시도 미소비, ko 구분자 제거를 확인했다. 정답 제출의 `feedback: null`은 스펙 미정 12 확정 내용대로 유지된다. |
| 순서 있는 attempts, hint_unlocked=false, 정답 행 전부 true, 미정 12 기록 | 충족 | `app/services/puzzle_service.py:60`, `:78`, `:86`; repository가 `attempt_no` 순으로 조회한다. 새 test client의 두 행 복원, 정답 행 피드백, 영어 이력 정규화, 빈 이력 테스트가 통과했다. 스펙 끝에 티켓 04 확정 내용이 추가됐다. |
| 3번째 오답 후 GET/POST 모두 hint 제공 | 충족 | `compute_reveal` 공유 및 `app/services/puzzle_service.py:81`, `app/services/guess_service.py:94`. 신규 테스트가 첫 두 오답의 양쪽 null, 세 번째 오답의 양쪽 힌트를 검사한다. |
| 현행 웹 제출에 puzzle_id 최소 동봉 | 충족 | `web/static/app.js:209`, `:357`. 번들 테스트 외에 Node VM에서 실제 `submitGuess` 함수를 실행하여 fetch 요청 바디의 ID·guess를 확인했다. |
| 새 클라이언트 복원·영어 입력 동등성·기존 제출 테스트 수정 | 충족 | `tests/test_puzzle_pin_and_attempts.py`와 수정된 기존 제출/동시성 테스트를 읽고 전체 스위트를 직접 실행했다. 311개 통과. |
| README 설계 판단 두 항목 추가 | 충족 | `README.md:675` 이후 `### 04.` 항목에 퍼즐 고정/409, 서버 이력 반환의 이유가 있다. 별도로 API 표 수정 방식은 아래 D-04-1에 해당한다. |

## 직접 실행한 검증

로컬 전용 MySQL `chosung_daily_test_t04`, Redis DB 6을 `TEST_DATABASE_URL`/`TEST_REDIS_URL`로 지정했다. 마이그레이션 테스트에는 기존 `chosung_daily_test_t04_migrations`를 `TEST_MIGRATION_DATABASE_URL`로 지정했다. 접속 정보는 `.env.example` 형식의 로컬 테스트 설정을 사용했으며 이 문서에는 자격 증명을 기록하지 않는다. 새 DB 생성이나 기본 테스트 DB 폴백은 없었다.

| 검증 | 결과 |
|---|---|
| 위 환경변수 설정 후 `uv run pytest -q` | `311 passed in 143.16s (0:02:23)`, exit 0. 간헐 실패가 없어 재실행하지 않았다. |
| `uv run ruff check .` | `All checks passed!`, exit 0 |
| `uv run flask db heads` | `f394da7f4d88 (head)` 한 줄. 이 티켓 자체의 마이그레이션 추가는 없다. |
| `git diff --check main...HEAD` | 출력 없음 |
| Node VM의 웹 제출 함수 실행 | 번들 마지막 자동 `init()` 호출만 메모리에서 제거하고, DOM·fetch 경계를 대역으로 제공했다. `state.puzzleId=42`로 `submitGuess({}, "사과")` 호출 시 요청 바디가 `{puzzle_id:42, guess:"사과"}`임을 assertion으로 확인했다. 외부 요청 없음. |

## 결함 목록

### D-04-1 — README 공유 API 표의 기존 행 직접 수정

- 심각도: **MINOR**
- 위치: `README.md:83` 및 `README.md:84`.
- 요구 근거: 티켓 공통 규칙은 README 설계 판단·API 표 등 공유 절에서 자기 번호 소제목/자기 행만 **섹션 끝에 덧붙이도록** 명시한다.
- 재현 명령: `git diff main...HEAD -- README.md`.
- 기대: 기존 API 행은 보존하고, 티켓 04에 해당하는 변경 설명을 번호가 식별되는 추가 항목으로 절 끝에 덧붙인다.
- 실제: 기존 GET `/api/v1/puzzles/today`, POST `/api/v1/puzzles/today/guesses` 두 행을 삭제·교체했다. 번호 항목을 추가하는 방식이 아니다.
- 영향: 병렬 티켓이 같은 API 표를 갱신할 때 충돌 방지 규칙을 깨뜨린다. 현재 API 설명 자체는 맞으며 런타임 결함이나 데이터 손상은 아니므로 MINOR로 분류한다.
- 수정 방향: 기존 행을 유지하고 `04`로 식별되는 추가 설명을 API 절 끝에 둔다. 리뷰에서는 수정하지 않았다.

## 보안·범위·테스트 품질

- 인증은 기존 Bearer `with_guest` 경로를 유지하고, 이력 조회는 인증된 게스트와 퍼즐 ID로 제한된다. 새 쿠키 인증 쓰기 경로나 CSRF 우회는 추가되지 않았다.
- 추측 입력은 Pydantic 길이/타입 검사와 정규화 후 길이 검사를 거친다. ID 불일치 거절은 Attempt 및 GuestStats 쓰기 전이다. 기존 동시 제출 테스트도 통과했다.
- 변경 diff에서 실제 키·토큰·비밀번호가 파일에 추가된 흔적은 발견하지 못했다.
- 신규 핵심 테스트는 HTTP→실제 MySQL/Redis를 사용하며 내부 서비스를 mock하여 정답을 고정하지 않는다. 웹 번들 문자열 검사는 단독으로는 실행 증거가 약하므로 위 Node VM 실행으로 보완했다. 실제 브라우저 화면 테스트를 했다는 주장은 하지 않는다.
- k6의 ID 동봉은 API 계약 변경에 필요한 호출부 수정이다. 범위 밖 기능 추가는 발견하지 못했다.
- README 설계 판단은 `### 04.`로 추가했고, 스펙 미정 12 확정은 끝에 덧붙였다. 공유 파일 규칙 위반은 D-04-1에 한정한다.

## 참고

- 웹의 서버 attempts 렌더링과 409 후 자동 새로고침은 티켓이 명시한 17·18 범위다. 현행 localStorage 유지 자체는 04 결함으로 세지 않았다.
- `hint_unlocked` 실조회는 티켓 06 범위이고 이번 티켓의 항상 false 요구와 일치한다.
- BLOCKER 0건, MAJOR 0건, MINOR 1건. 취향·스타일 제안은 결함으로 등록하지 않았다.

판정: PASS
