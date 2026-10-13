# 티켓 05 최종 리뷰 — 라운드 1

## 범위와 기준

- 검토 HEAD: `72899fd1add6a6a0c617f62e9c2f3adb0d54c70d`.
- 로컬 `main`: `0abb1d79d8eea3701893e57313745ad566e19632`, merge-base: `20d279a256d0f17152ae6ac273f4758c80fbb712`.
- `git diff main...HEAD`와 `git log main..HEAD`로 구현 커밋 `dad1997`, `a2469ab`, `2fdfeb2`, 증거 커밋 `72899fd`를 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 05, 스펙 §A.1·§A.12·Testing Celery, `CONTEXT.md`, README 규칙을 대조했다. 구현 증거 문서의 결과를 재사용하지 않고 테스트와 린트를 직접 실행했다.
- UI 변경 및 신규 마이그레이션 없음. 애플리케이션·테스트·설정·`.scratch/` 수정, 프로덕션 접근, 실제 외부 서비스 호출은 하지 않았다.

## 티켓 체크박스별 충족 여부

| 항목 | 결과 | 직접 확인한 근거 |
|---|---|---|
| `schedule_puzzles(language, days)`·CLI `--language`·언어별 통계 flush | 충족 | `puzzle_schedule_service.py:14`의 언어 인자와 모든 후보 경로의 언어 필터, `app/cli.py:22`의 허용 언어 검증, `puzzle_maintenance_service.py:85`의 통계 키 순회를 확인했다. 스케줄·CLI·통계 테스트가 실제 DB/Redis에서 언어 분리와 잘못된 언어 거부를 검증한다. 기존 최근 14일 회피·부족 시 재사용 정책은 유지된다. |
| 언어 하나의 배정·캐시·커밋, 한 언어 실패 알림 후 계속 | 충족 | `puzzle_maintenance_service.py:17`이 단일 언어를 배정·커밋하고 캐시를 채운다. `:50`의 순회는 실패 시 rollback·알림 후 계속한다. 태스크 `scheduled.py:14`가 이 순회를 호출한다. `test_one_language_failing_does_not_block_the_others`에서 en 단어 0개, ko 배정 유지, en 실패 알림 1건을 검증한다. |
| 언어별 미사용 단어 수→잔량, 매일 14일 미만 Slack 알림 | 충족 | `word_pool_service.py:21`의 배정 이력 제외 집계와 `:40`의 엄격한 `<14` 조건을 확인했다. 서비스 테스트는 0개·언어별 수량·배정 후 차감·14일 경계를 검증하고, Celery 테스트는 서비스 호출 배선과 매일 09:00 등록을 검증한다. |
| `puzzle:{date}:{lang}` 캐시와 Redis 장애 시 DB 폴백 | 충족 | `puzzle_cache.py`의 언어 포함 키·`safe_redis_call`, 자정 배정의 commit 후 캐시 호출을 확인했다. 언어별 캐시 내용 및 Redis 장애 배정 테스트, 기존 `test_redis_failure_fallback.py`의 API 조회 폴백 테스트를 확인했다. |
| KST Beat 등록 및 README 운영 절 | 충족 | `celery_app.py:15`의 `Asia/Seoul`, `scheduled.py:35`의 00:00/00:05/09:00 등록, README 운영 표를 대조했다. 선택 항목인 모듈별 스케줄 병합도 구현됐다. 별도 프로세스에서 두 import 순서 모두 스케줄 3개가 등록됨을 확인했다. |
| README 설계 판단에 언어별 커밋·부분 실패 허용 추가 | 충족 | `README.md:699`의 `### 05.` 절에 요구한 판단·근거가 있다. 다만 기존 공통 절 수정은 별도 규칙 위반 D-05-1이다. |

## 실행 검증

기존 로컬 전용 DB `chosung_daily_test_t05`, Redis DB 7, 기존 마이그레이션 테스트 DB `chosung_daily_test_t05_migrations`를 환경 변수로 지정했다. 접속 문자열의 인증 값은 이 문서에 기록하지 않는다. 새 DB 생성이나 서버 설정 변경은 하지 않았다. Slack 설정은 비우고 전송 테스트는 기존 mock을 사용했다.

- `uv run pytest -q`: 종료 코드 0, **314 passed in 148.51s (0:02:28)**. 전용 DB 접속 성공으로 기본 테스트 DB 폴백은 사용하지 않았고, 간헐 실패나 재실행도 없었다.
- `uv run ruff check .`: 종료 코드 0, `All checks passed!`.
- `FLASK_APP=wsgi.py uv run flask db heads`: 종료 코드 0, `f394da7f4d88 (head)` 1줄.
- `git diff --check main...HEAD`: 종료 코드 0.
- 독립 Python 프로세스에서 `import celery_app` 선행 및 `from app.tasks import scheduled` 선행: 각각 `len(celery.conf.beat_schedule) == 3` 통과.

## 결함 목록

### D-05-1 — README 공통 설계 판단의 덧붙이기 전용 규칙 위반

- 심각도: **MINOR**
- 위치: `README.md:199`
- 근거: 티켓 공통 규칙과 `README.md:186`은 설계 판단을 자기 번호 소제목으로 절 끝에 덧붙이도록 명시한다.
- 재현: `git diff main...HEAD -- README.md` 실행 → `### 트랜잭션 경계`의 기존 예시 문장이 직접 교체된 hunk를 확인한다.
- 기대: 기존 공통 문장은 유지하고 언어 인자에 관한 설명은 `### 05.` 안에 추가한다.
- 실제: 기존 `schedule_puzzles(days=30)` 예시를 `schedule_puzzles(ko, days=30)` 예시로 교체했다. 병렬 티켓 간 충돌을 피하려는 소유 범위 규칙을 위반한다. 런타임 영향은 없어 MINOR로 판정한다.

## 보안·범위·검증 한계

- 변경된 실행 경로에 신규 HTTP 인증/CSRF 경계는 없다. CLI 언어 입력은 `click.Choice`로 제한된다. 변경 파일에서 실제 외부 서비스 키·토큰·운영 비밀번호는 발견하지 못했다. 증거 문서의 로컬 테스트 접속 예시는 `.env.example`의 개발 기본값과 같다.
- 서비스 테스트가 배정·통계·잔량을 실제 DB/Redis로 검증하고 Slack 전송 경계만 대체한다. 태스크 배선 테스트의 서비스 mock은 서비스 직접 테스트와 함께 읽었으며, 항상 통과하는 테스트는 발견하지 못했다.
- 실제 Beat 프로세스의 자정 큐 발행과 실제 Slack 수신은 검증 범위 밖이다. 요구된 서비스 직접 호출·설정·배선 검증과 구분한다.
- BLOCKER 0건, MAJOR 0건, MINOR 1건. 기능상 출시를 막는 결함은 확인하지 못했다.

판정: PASS
