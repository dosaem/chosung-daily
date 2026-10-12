# 오늘의 초성 (chosung-daily)

하루에 한 문제, 초성을 보고 단어를 맞추는 웹 게임의 백엔드.

> 아직 뼈대만 있는 상태입니다. 아키텍처, API 명세, 설계 판단 등 상세 문서는 이후 Phase에서 채웁니다.

## 실행 방법

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:8000/health
```

로컬에서 직접 실행:

```bash
uv sync
uv run pytest
uv run ruff check .
```

## 설계 판단

### 트랜잭션 경계

**서비스 레이어의 함수 하나 = 커밋 하나.** `app/services/*.py`의 각 함수는 그 안에서 일어나는
모든 DB 변경(여러 테이블, 여러 행)을 끝에서 `db.session.commit()` 한 번으로 묶는다. 중간에
실패하면 그 함수가 만든 변경은 전부 롤백된다 — "하루치만 반영되고 나머지는 빠진" 반쪼가리
상태를 피하려는 목적. Spring의 서비스 메서드 `@Transactional` 기본 동작(메서드 하나 = 트랜잭션
하나)과 같은 결.

API/CLI(`app/api`, `app/cli.py`)는 서비스 함수를 호출만 하고 직접 `db.session`을 만지지 않는다.
예: `schedule_puzzles(days=30)`는 30일치를 전부 배정하거나, 중간에 에러가 나면 이번 실행에서
새로 만든 배정을 전부 롤백한다 (기존에 이미 있던 날짜는 건드리지 않음).

### 동시성: 정답 제출

같은 게스트가 정답을 동시에 두 번 보내도 `Attempt.attempt_no`가 꼬이거나 `GuestStats`의
streak/solved_count가 두 번 올라가면 안 된다. `app/services/guess_service.py`의
`submit_guess`는 가장 먼저 `GuestStats` 행에 `SELECT ... FOR UPDATE`를 건다
(`app/repositories/guest_stats_repository.py`). 같은 게스트의 두 요청 중 뒤에 도착한
쪽은 이 잠금에서 블락되고, 앞 요청이 커밋(또는 롤백)해야 풀린다 — 그래서 attempts를
다시 읽을 때는 항상 앞 요청의 변경까지 반영된 최신 상태를 본다.

`unique(guest_id, puzzle_id, attempt_no)` 제약(DB 레벨 재시도 방식)도 attempt_no 중복은
막아주지만, "이미 정답을 맞췄는지"를 재확인하는 타이밍에 따라 streak 이중 증가까지
완전히 막는다고 보장하기 어려워서 주 메커니즘으로는 고르지 않았다. 이 unique 제약은
혹시 FOR UPDATE 경로를 안 타는 변경이 생겨도 DB가 마지막으로 막아주는 보험으로 남겨뒀다.

**실제로 겪은 함정**: MySQL 기본 격리수준(REPEATABLE READ)에서는 트랜잭션 안의 일반
`SELECT`가 "이 트랜잭션이 맨 처음 뭔가를 읽은 시점"의 스냅샷을 계속 본다. `FOR UPDATE`로
잠금을 걸고 기다려서 받아도, 그 뒤에 나오는 일반 `SELECT`(예: 이 게스트의 attempts 조회)는
잠금을 받은 시점이 아니라 그 스냅샷을 써서 — 방금 다른 트랜잭션이 커밋한 데이터를 못
보는 문제가 실제로 재현됐다 (`tests/test_concurrency.py`가 처음엔 이 문제로 실패했었음).
`app/config.py`의 `SQLALCHEMY_ENGINE_OPTIONS`에 `isolation_level: READ COMMITTED`를
추가해서 모든 문장이 항상 최신 커밋을 보게 해 해결했다. Spring/JPA로 치면
`@Lock(LockModeType.PESSIMISTIC_WRITE)` + 트랜잭션 격리수준을 `READ_COMMITTED`로
낮추는 것과 같은 조합.

### 에러 응답

`app/errors.py`의 `AppError`를 상속하는 도메인 예외를 쓰고, `{code, message}` JSON +
적절한 HTTP status로 통일한다 (Spring의 `@ControllerAdvice` + `@ExceptionHandler` 대응).
정의된 코드: `UNAUTHORIZED`(401, 토큰 없음/무효), `VALIDATION_ERROR`(400, 요청 값 자체가
잘못됨 — 예: 정답과 길이가 다른 guess), `NOT_FOUND`(404), `NO_PUZZLE_TODAY`(404, 오늘
퍼즐이 아직 스케줄 안 됨), `ALREADY_FINISHED`(409, 이미 끝난 퍼즐에 또 제출),
`RATE_LIMITED`(429, 분당 제출 횟수 초과).

### Redis: 캐시 / 랭킹 / 통계 / rate limit

**캐시-어사이드 범위를 "단어 정보"로만 제한했다.** `puzzle:{date}`에 캐시하는 건
`chosung`/`answer`/`hint`/`category`처럼 그날 모든 유저에게 똑같은 값뿐이다.
`attempts_left`/`status`/힌트 공개 여부처럼 게스트마다 다른 값은 절대 캐시하지 않고
항상 DB에서 그 게스트의 attempts를 다시 읽는다 — 안 그러면 한 게스트의 진행 상태가
캐시를 통해 다른 게스트에게 새어나간다. `app/services/puzzle_cache.py`의 `CachedPuzzle`/
`CachedWord`는 `DailyPuzzle`/`Word` ORM과 같은 속성을 노출하는 덕 타이핑으로, 호출부
(`puzzle_service`, `guess_service`)가 캐시 히트/미스를 분기할 필요가 없게 한다. 지금
규모에선 이 구조로 충분하다고 판단했지만, 나중에 `Word`에 필드가 추가되는데 `CachedWord`를
깜빡하고 안 늘리면 캐시 히트 경로에서만 조용히 구버전 데이터가 나가는 위험이 있다 —
캐시 레이어가 더 커지면 `typing.Protocol`로 계약을 명시하는 게 안전하다.

**리더보드 정렬**: "적은 시도 우선, 같으면 빨리 푼 순"을 `lb:{date}` Sorted Set 하나의
점수로 인코딩한다 — `score = attempt_no * 86400 + 자정부터 걸린 초`. 시도 횟수 차이가
걸린 시간(최대 86399초) 차이보다 항상 크기 때문에, ZSET 기본 오름차순 그대로 원하는
순서가 나온다(REV 불필요).

**통계**: `stats:{date}` Hash에 `HINCRBY`로 "1"~"5"(그 시도 횟수에 맞춘 정답)와 "fail"을
누적한다. DB(`DailyStats`)로의 배치 반영은 Celery Beat 몫이라 Phase 4에선 손대지 않았다.

**rate limit은 고정 윈도우(fixed window)다.** 게스트가 "처음" 요청한 시점부터 60초
단위로 카운터가 리셋된다 — 슬라이딩 윈도우보다 구현이 단순하지만, 윈도우 경계에서
짧은 순간(예: 59.9초에 10번 + 60.1초에 또 10번) 분당 10회보다 더 통과할 수 있다. rate
limit의 목적이 "악의적 스팸 방지"라 이 정도 오차는 감수하기로 했다(`app/api/rate_limit.py`
에 근거 기록).

**Redis 장애 격리**: `app/utils/redis_safe.py`의 `safe_redis_call` 하나를 모든 Redis
호출(캐시/통계/랭킹/rate limit)이 거친다. Redis가 없거나 장애면 조용히 `default`를
돌려주고 호출부는 평소처럼 DB 경로로 계속 간다 — "Redis 장애 시 게임 자체(조회/제출)는
DB로 동작하고, 랭킹·통계만 실패"가 이 한 함수로 전부 구현된다. rate limit도 "제출"의
일부로 보고 fail-open(장애 시 그냥 통과)시켰다.

### Celery Beat: 자정 퍼즐 생성 / 00:05 통계 배치

**태스크의 실제 로직은 서비스 레이어에, Celery는 얇은 어댑터로.**
`app/services/puzzle_maintenance_service.py`에 평범한 함수 두 개
(`ensure_today_puzzle_and_warm_cache`, `flush_daily_stats_for_yesterday`)로 로직을
두고, `celery_app.py`/`app/tasks/scheduled.py`는 그 함수를 호출만 한다. 이렇게 나눈
이유는 테스트 가능성 때문이다 — Celery 태스크는 `-A celery_app.celery`로 뜰 자기만의
Flask 앱이 필요한데, pytest의 테스트 앱과 그 앱은 설정(DB/Redis)이 다르다. 서비스
함수로 로직을 빼두면 pytest가 테스트 앱 컨텍스트 안에서 그 함수를 직접 불러 검증할 수
있고(`tests/test_puzzle_maintenance.py`), Celery 쪽은 "배선(태스크 이름, Beat
스케줄, 타임존)만 맞는지"를 가볍게 확인한다(`tests/test_celery_wiring.py`).

**실제로 겪은 함정**: `app/extensions.py`가 처음엔 redis 클라이언트를 모듈 전역
변수 하나에 저장했는데, `celery_app.py`가 자기 몫의 `create_app()`을 모듈
레벨에서 실행하면서 그 전역을 자기 설정(dev Redis, 인덱스 0)으로 덮어써버렸다.
pytest 프로세스 하나에서 테스트 앱과 `celery_app.py`가 둘 다 import되는 순간,
나중에 import된 쪽이 전역을 덮어쓰는 문제였다(지금까지는 테스트 실행 순서 덕에
우연히 안 터졌을 뿐). `db`/`migrate`가 Flask-SQLAlchemy/Flask-Migrate 내부에서
앱마다 따로 상태를 들고 있는 것과 같은 방식으로, redis 클라이언트도
`app.extensions`에 앱별로 저장하도록 고쳤다 — 이제 `get_redis()`는
`current_app.extensions`에서 조회해서, 서로 다른 Flask 앱 인스턴스가 완전히
독립적인 Redis 연결을 갖는다.

**"매일 자정 자동 실행"은 설정값과 스케줄러 계산까지만 확인했다.** `celery.conf.timezone
= "Asia/Seoul"`로 Beat의 crontab이 KST 기준으로 해석되게 했고, `crontab(...).
remaining_estimate(now)`로 다음 실행 예정 시각을 직접 계산해서 23:59:59/00:04:59
(KST)가 나오는 것까지 확인했다 — 이건 Beat가 내부적으로 쓰는 것과 같은 계산 함수라
단순히 설정값을 읽는 것보다는 신뢰도가 높지만, 실제로 자정을 넘기며 beat 컨테이너가
태스크를 큐에 넣는 순간을 지켜본 건 아니다. `celery call`로 두 태스크를 수동
트리거해서 워커가 정상 처리하는 것(태스크 로직 자체의 정확성)은 확인했지만, 이
둘은 서로 다른 수준의 증거라는 걸 구분해 둔다.
