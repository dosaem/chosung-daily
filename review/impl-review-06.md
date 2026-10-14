# 티켓 06 최종 리뷰 — 라운드 1

## 검토 범위

- 기준: 로컬 `main` = `b43567ef37b53615db4744f1ac5bcf52b216e0ba`, 검토 HEAD = `3147a7d`.
- `git diff main...HEAD` 전체와 `git log main..HEAD`의 5개 커밋(`c8796f0`, `f4d841c`, `6ad2053`, `8c124ec`, `3147a7d`)을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 `.scratch/store-launch/issues/06-hint-unlock-rewarded.md`, 스펙 §A.2·§A.5·§A′·Testing Decisions, `CONTEXT.md`, `review/impl-evidence-06.md`를 대조했다.
- UI 변경이 없는 백엔드 티켓이므로 디자인 화면 검증은 해당 없음. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다.

## 티켓 체크박스별 판정

| 요구사항 | 판정 | 직접 확인한 근거 |
|---|---|---|
| HintUnlock 모델·복합 PK 마이그레이션, head 1개 | 충족 | `app/models/hint_unlock.py:16`의 두 PK 및 필수 시각, `migrations/versions/dae1b5af0cf7_add_hint_unlock_table_for_early_hint.py:24`의 테이블·FK·PK를 확인했다. `tests/test_migrations.py:307`의 upgrade/downgrade/upgrade 및 `:319`의 실제 SQL 중복 INSERT 거절 테스트가 통과했다. 직접 실행한 heads 출력은 `dae1b5af0cf7 (head)` 한 줄이다. |
| POST 경로, GuestStats FOR UPDATE, 세 가지 409, 구독 여부 무관 | 충족 | `app/api/puzzles.py:49`에서 Bearer 인증 후 요청을 검증한다. `app/services/hint_service.py:26`에서 퍼즐 확인 → 동일 게스트 잠금 → 시도·열림 상태 확인 → 행 삽입·커밋 순서다. `app/repositories/guest_stats_repository.py:5`의 실제 `with_for_update()`를 사용한다. 성공·중복·정답 완료·5회 소진·누락 ID·어제 ID 테스트가 통과했고 구독/광고 검증 분기는 없다. |
| GET·제출 hint OR 규칙, hint_unlocked 및 새 client 재조회 | 충족 | `app/services/puzzle_service.py:59`와 `app/services/guess_service.py:84`에서 저장된 열림 여부를 읽어 OR 규칙에 사용한다. 조회 응답에 `hint_unlocked`가 내려온다(스펙 §A′의 제출 응답에는 별도 필드 추가 요구 없음). `tests/test_hint_unlock.py:67`, `:77`과 기존 세 번째 오답 회귀 테스트가 통과했다. 별도 수동 실행에서도 요청 사이 앱/DB 세션 컨텍스트를 닫고 새 client로 조회하여 유지됨을 확인했다. |
| 시도 수·solved_in_seconds·리더보드 영향 없음 테스트 | 충족 | `tests/test_hint_unlock.py:171`, `:182`, `:193`이 실제 시도 행·잔여 기회·게스트 통계·Redis 기반 리더보드 값을 검사하며 통과했다. 스펙 §A′에 따라 기존 `solved_in_seconds`의 응답 이름은 `seconds`다. 해제 서비스에는 시도·통계·랭킹 쓰기가 없으며, 추가 실행에서도 해제 직후 Attempt 0행 및 `lb:*` 키 없음을 확인했다. |
| 힌트 미리 보기와 제출 동시성 | 충족 | `tests/test_concurrency.py:60`은 실제 별도 스레드·DB 세션으로 제출과 해제를 동시에 실행하고 선행 요청에 따른 결과 및 최종 행·통계를 확인한다. `:113`은 동시 해제 중 하나만 성공하고 나머지는 HINT_ALREADY_UNLOCKED임을 확인한다. 둘 다 전체 테스트에서 통과했다. 서비스 둘이 같은 잠금을 사용하며 격리 수준은 READ COMMITTED다. |
| README 공정성·AdMob SSV 미사용 근거 | 충족 | `README.md:1030`의 `### 06.`에 복합 PK, 시도·순위 미변경, 잠금 공유, SSV 미사용 이유를 설명한다. API 표는 `README.md:96`에 자기 행만 끝에 추가했다. |

## 직접 실행한 검증

구현 증거의 성공 문구를 대신 인용하지 않고 아래 명령을 직접 실행했다. 로컬 테스트 설정의 연결 형식을 사용하되 접속 자격 값은 문서에 기록하지 않는다.

- `TEST_DATABASE_URL`: 로컬의 기존 `chosung_daily_test_t06` DB.
- `TEST_MIGRATION_DATABASE_URL`: 로컬의 기존 `chosung_daily_test_t06_migrations` DB.
- `TEST_REDIS_URL`: `redis://localhost:6379/8`.
- 새 DB를 생성하지 않았고 기본 테스트 DB로의 폴백도 없었다. 외부 알림 설정은 비웠으며 NAS·프로덕션·실제 외부 서비스는 호출하지 않았다.

| 명령 | 실제 결과 |
|---|---|
| 위 테스트 환경변수를 지정한 `uv run pytest -q` | `571 passed in 404.43s (0:06:44)`, 종료 코드 0. 실패·skip 없음, 재실행 불필요. |
| `uv run ruff check .` | `All checks passed!` |
| `FLASK_ENV=testing uv run flask --app wsgi.py db heads` | `dae1b5af0cf7 (head)` — head 1개 |
| `git diff main...HEAD --check` | 출력 없음, 종료 코드 0 |

추가로 같은 전용 DB/Redis에서 `uv run python -`으로 Flask test client를 사용해 아래 요청과 DB 상태를 검증했다. 검증 후 테스트 테이블과 Redis DB 8을 정리했다.

| 입력/재현 순서 | 기대 및 실제 |
|---|---|
| 인증 헤더 없이 또는 유효하지 않은 Bearer로 POST hint-unlock | 모두 401 |
| 유효 게스트로 `puzzle_id`에 `"abc"`, `[]`, `{}`, `1.5`를 각각 전송 | 모두 400 |
| 게스트 A로 해제 → 요청 컨텍스트 종료 → 새 client GET today | `hint_unlocked: true`, 저장된 힌트 반환 |
| 같은 퍼즐을 게스트 B로 GET today | `hint_unlocked: false`, `hint: null` |
| 해제 직후 DB·Redis 확인 | HintUnlock 1행, Attempt 0행, 리더보드 키 없음 |
| 해제 후 정답 제출 → 새 client GET today | 제출에도 힌트 반환, 조회는 success 및 hint_unlocked true와 힌트 유지 |

## 결함 목록

없음. BLOCKER 0건 / MAJOR 0건 / MINOR 0건. 재현 가능한 결함이 없어 D-06-* ID를 발급하지 않는다.

## 보안·데이터·범위 검토

- 인증 주체의 `guest.id`만 사용하므로 요청 본문으로 다른 게스트의 힌트를 해제할 수 없다. 이 API는 세션 쿠키가 아닌 명시적 Bearer 인증 경로이며 스펙의 인증 방식과 일치한다.
- 입력은 Pydantic 검증과 현재 퍼즐 ID 비교를 거친다. 조회는 ORM 바인딩을 사용하고, 중복은 잠금과 복합 PK가 함께 방지한다.
- 신규 테스트는 DB·Redis 동작을 mock으로 대체하지 않는다. 동시성 검증도 실제 DB 세션을 사용한다.
- 마이그레이션은 새 테이블만 추가하고 기존 데이터를 변형하지 않는다. 계정 삭제 시 HintUnlock 정리는 별도 티켓 07 범위이며 현재 기준 코드에는 삭제 서비스가 없다.
- 공유 파일은 README 자기 번호 소제목 및 API 행만 덧붙였다. 변경 파일에 실제 키·토큰·비밀번호를 기록한 내용이나 티켓 범위 밖 수정은 발견하지 못했다.

## 참고

마이그레이션 head 1개 확인은 위 로컬 main/HEAD 기준이다. 이후 다른 마이그레이션이 먼저 병합되면 실제 병합 직전에 다시 확인해야 한다. 앱의 광고 SDK·구독 UI·실기기 광고 시청 흐름은 이 백엔드 티켓의 검증 범위가 아니다.

판정: PASS
