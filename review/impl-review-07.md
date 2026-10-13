# 티켓 07 최종 리뷰 — 라운드 1

## 범위와 기준

- 기준: 로컬 `main` = `20d279a256d0f17152ae6ac273f4758c80fbb712`, 구현 HEAD = `5ad8552`.
- 직접 확인: `git diff main...HEAD`, `git log main..HEAD`의 `db0f02d`, `2d4bb69`, `427ed99`, `5ad8552`와 구현 증거 문서.
- 요구사항: `.scratch/store-launch/issues/07-leaderboard-privacy-me-history.md`, 스펙 §A' 및 US 13·16a·16b, `CONTEXT.md`.
- UI 파일 변경 없음. `design/SCREENS.md` S3·S4와 `design-system/hidden-vowels/OVERRIDES.md`를 대조해 API가 내 순위·익명 표시·최근 기록 화면에 필요한 값을 제공하는지 확인했다.
- 코드·테스트·설정·`.scratch/` 수정 없음. 하위 에이전트, 프로덕션/NAS 접근, 배포, push 및 실제 외부 서비스 호출 없이 로컬 검증했다.

## 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 리더보드 새 필드, 익명 display, ZRANK 기반 me, 기존 guest_id·solved_in_seconds 제거 | 충족 | `app/schemas/leaderboard.py:8`의 필드 집합, `app/services/puzzle_metrics.py:21`의 4자리 소문자 16진 표시, 같은 파일 `:90`의 entries 및 `:118`의 별도 ZRANK/ZSCORE 조회를 확인했다. 응답 키 집합 검사, 표시 충돌·패딩 검사, 페이지 안 내 행 검사가 통과했다. |
| 25명 중 23위: entries 20개 + me.rank 23, 미정답 null, 기존 테스트 수정 | 충족 | `tests/test_leaderboard.py:85`부터 실제 POST 정답 제출로 25명을 구성한다. 서비스나 Redis 순위를 mock하지 않고 페이지 밖 순위와 시도 수를 검사한다. 미정답 null 및 기존 정렬·limit 테스트, 언어별 리더보드 회귀 테스트가 통과했다. |
| GET /me/history: KST 최근 7일, ko/en 네 상태, days 상한 31 | 충족 | `app/api/me.py:33`의 정수/1..31 검증과 Bearer 인증, `app/services/stats_service.py:47`의 KST 날짜 생성, `app/repositories/attempt_repository.py:38`의 guest/date 필터 및 언어별 GROUP BY, `app/services/game_rules.py:28`의 네 상태 분기를 확인했다. 실제 MySQL 기록을 통한 상태·언어 분리·다른 게스트 격리·31일·잘못된 days·미인증 테스트가 통과했다. |
| README API 표 갱신 및 설계 판단에 리더보드 익명 표시 추가 | 충족 | `README.md:86`, `:88`에 응답 계약과 history가 있고 `:676`부터 `### 07.` 설계 판단 세 항목이 있다. 다만 공유 API 표의 편집 방식은 아래 D-07-1에 해당한다. |

## 직접 실행한 검증

테스트 프로세스의 `TEST_DATABASE_URL`은 localhost의 기존 `chosung_daily_test_t07` DB로, `TEST_REDIS_URL`은 localhost Redis DB 9로 지정했다. 접속 문자열의 인증 부분은 이 문서에 기록하지 않는다. 마이그레이션 테스트는 기본 파생 규칙으로 기존 `chosung_daily_test_t07_migrations`를 사용했다. 신규 DB 생성 및 기본 테스트 DB 폴백은 없었다.

| 명령 | 결과 |
|---|---|
| 위 테스트 환경변수 지정 후 `uv run pytest -q` | 종료 코드 0, `308 passed in 160.18s (0:02:40)`; 실패·skip·xfail 없음, 재실행 불필요 |
| `uv run ruff check .` | 종료 코드 0, `All checks passed!` |
| `FLASK_APP=wsgi.py uv run flask db heads` | 종료 코드 0, `f394da7f4d88 (head)` 한 줄 |
| `git diff --check main...HEAD` | 종료 코드 0, 출력 없음 |

이 티켓은 마이그레이션을 추가하지 않았다. 구현 증거의 308개 통과 주장을 독립적으로 재확인했다. history 테스트는 결과를 mock하지 않고 DB 행을 심어 API와 SQL 집계를 실행한다. Redis 장애 테스트만 의도적으로 장애 대역을 사용한다.

## 결함 목록

### D-07-1 — 공유 API 표의 끝에만 덧붙이기 규칙 위반

- 심각도: **MINOR**
- 위치: `README.md:86`, `README.md:88`
- 근거: 티켓 공통 규칙은 README API 표를 포함한 공유 절에 자기 번호 소제목/자기 행만 **섹션 끝에 덧붙이기**를 요구한다.
- 재현: `git diff main...HEAD -- README.md`를 실행한다.
- 기대: 기존 공유 행은 보존하고 티켓 07의 변경 계약/history 행을 API 표 끝에 추가한다.
- 실제: 기존 leaderboard 행을 직접 교체했고 새 history 행을 표 중간의 `/me/stats` 바로 아래에 삽입했다. 설계 판단의 `### 07.` 항목들은 절 끝에 추가되어 이 문제에 해당하지 않는다.
- 영향: 실행 동작은 정상이나 병렬 티켓의 공유 표 편집을 안전하게 합치기 위한 명시적 통합 규칙을 어긴다. 사용자 기능이나 데이터 손상으로 이어지는 증거는 없어 MINOR로 분류한다.

## 보안·범위·참고

- 신규 history는 `with_guest`를 거치고 SQL 조회를 요청자의 guest ID로 제한한다. 읽기 전용 Bearer GET이므로 새로운 세션 기반 상태 변경/CSRF 경로는 없다.
- leaderboard 응답 스키마에서 원본 guest ID와 기존 시간 필드가 제거되었다. 표시용 ID의 가역성·충돌은 티켓이 지정한 규칙이므로 별도 결함으로 올리지 않았다.
- 변경 diff에서 실제 키·토큰·비밀번호의 추가 기록, 관련 없는 기능 변경, 데이터 쓰기/삭제 경로의 신규 위험을 발견하지 못했다.
- 기존 leaderboard limit 입력 처리와 다른 티켓의 puzzle_id 요구는 이번 diff의 신규 결함으로 취급하지 않았다.
- 날짜 경계 고정 테스트는 없지만 구현의 KST 사용과 날짜 범위를 직접 확인했다. 현재 테스트는 시스템 시각에 의존한다는 검증 한계가 있으며, 이것만으로 기능 결함을 판정하지 않는다.

총 결함: BLOCKER 0, MAJOR 0, MINOR 1. 중대 결함이 없으므로 티켓 판정 규칙에 따라 PASS다.

판정: PASS
