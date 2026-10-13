# 오늘의 초성 (chosung-daily)

하루에 한 문제, 초성을 보고 단어를 맞추는 웹 게임의 백엔드. Flask로 만든
이직용 포트폴리오 프로젝트다 — Java/Spring, TypeScript/NestJS로 6년차
백엔드를 하다가 Flask를 처음 써보면서, 설계 판단마다 "Spring이었다면 어떻게
했을지"를 비교하며 진행했다. Spring 개념 대응표는
[`docs/spring-to-flask.md`](docs/spring-to-flask.md) 참고.

## 기술 스택

- Python 3.12, uv (의존성/가상환경)
- Flask 3 (app factory), Flask-SQLAlchemy, Flask-Migrate(Alembic)
- pydantic v2 (요청 검증·응답 직렬화)
- MySQL 8, Redis 7
- Celery + Celery Beat (broker: Redis)
- Authlib (구글/애플 OAuth 로그인)
- gunicorn, Docker Compose
- pytest(실제 MySQL/Redis 통합 테스트 위주), ruff, k6

## 아키텍처

```mermaid
graph LR
    subgraph Client
        Browser["브라우저<br/>(Jinja 1장 + vanilla JS)"]
    end

    subgraph "Flask App (gunicorn)"
        API["app/api/*<br/>(Blueprint, 요청파싱/응답변환만)"]
        SVC["app/services/*<br/>(비즈니스 로직, 트랜잭션 경계)"]
        REPO["app/repositories/*<br/>(DB 접근)"]
        CLIENTS["app/clients/*<br/>(외부 호출 래퍼, 함수 하나씩)"]
        API --> SVC --> REPO
        SVC --> CLIENTS
    end

    MySQL[("MySQL 8")]
    Redis[("Redis 7<br/>broker + cache")]
    Worker["Celery worker"]
    Beat["Celery beat<br/>(00:00 · 00:05 KST)"]
    Google(["Google OAuth"])
    Apple(["Apple OAuth"])
    Slack(["Slack Webhook"])

    Browser -->|"/ , /api/v1/*"| API
    REPO --> MySQL
    SVC -->|캐시 · 랭킹 · 통계 · rate limit| Redis
    API -.->|로그인 리다이렉트| Google
    API -.->|로그인 리다이렉트| Apple
    CLIENTS -.->|운영자 알림| Slack

    Beat -->|태스크 큐잉| Redis
    Redis --> Worker
    Worker --> MySQL
    Worker --> Redis
```

레이어 구조(Spring의 controller/service/repository/entity에 대응):

```
app/
├── api/            # Blueprint. 요청 파싱, 응답 변환만
├── schemas/        # pydantic 요청/응답 모델 (DTO)
├── services/        # 비즈니스 로직, 트랜잭션 경계
├── repositories/    # DB 접근
├── models/          # SQLAlchemy 모델 (Entity)
├── tasks/           # Celery 태스크 (얇은 어댑터)
├── clients/         # 외부 provider 호출 래퍼 (provider 하나 = 모듈 하나)
├── csrf.py          # 웹 폼 CSRF 토큰 발급 + 검증 데코레이터
├── errors.py        # 도메인 예외 + errorhandler
└── cli.py           # flask 커맨드 (시드, 퍼즐 스케줄링, 책 검색, 알림 테스트)
web/                  # Jinja 템플릿 1장 + vanilla JS
```

## API 목록

| 메서드 | 경로 | 설명 | 인증 |
|---|---|---|---|
| GET | `/health` | 헬스체크 (DB 실패 503, Redis 실패 200 + `degraded`) | - |
| GET | `/` | 게임 화면 (Jinja) | - |
| POST | `/api/v1/guests` | 게스트 토큰 발급 (`{puzzle_language?}`, 기본 `ko`) | - |
| PATCH | `/api/v1/me` | 퍼즐 언어 선호 변경 (`{puzzle_language}`) → `{puzzle_language}` | Bearer |
| GET | `/api/v1/puzzles/today` | 게스트 선호 언어의 오늘 퍼즐(`puzzle_id`/`language`/`mask`/`length`/`chosung`/카테고리/남은시도/상태/힌트), 정답 미포함 | Bearer |
| POST | `/api/v1/puzzles/today/guesses` | 정답 제출 → 판정/피드백/남은시도/(종료 시)정답 | Bearer |
| GET | `/api/v1/puzzles/today/stats?language=` | 시도 횟수별 정답자 비율 (언어별, 기본 게스트 선호) | Bearer |
| GET | `/api/v1/puzzles/today/leaderboard?language=&limit=20` | 랭킹(적은 시도 우선, 같으면 빨리 푼 순, 언어별) | Bearer |
| GET | `/api/v1/me/stats` | 내 퍼즐 언어 · streak · 최대streak · 누적 정답 | Bearer |
| POST | `/api/v1/session/sync` | 이 브라우저=이 게스트를 세션 쿠키에 동기화 (로그인 전 필수) | Bearer |
| GET | `/api/v1/auth/<provider>/login` | 구글/애플 로그인 시작 (리다이렉트) | 세션 쿠키 |
| GET | `/api/v1/auth/<provider>/callback` | OAuth 콜백, 계정 연결 후 `/?login_token=`으로 리다이렉트 | 세션 쿠키 |
| POST | `/api/v1/auth/token-exchange` | 앱 네이티브 로그인 id_token 교환 → 계정 연결/전환 후 `{token}` | Bearer |
| GET | `/api/v1/config` | 앱 설정(최소 앱 버전·점검·지원 언어·스토어 링크), 60초 캐시 | - |

에러 응답은 전부 `{code, message}` + 적절한 HTTP status로 통일 (아래 "에러 응답" 참고).

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

`tests/test_migrations.py` 는 `flask db upgrade/downgrade` 를 **별도 DB** 에서 돌린다
(conftest 의 `create_all` 경로로는 마이그레이션 파일이 검증되지 않는다). 테스트 유저에게
`CREATE DATABASE` 권한이 없어서 한 번은 관리자로 만들어 줘야 한다 — 이름은 테스트 DB 이름
+ `_migrations` 이고, `TEST_MIGRATION_DATABASE_URL` 로 바꿀 수 있다:

```bash
docker compose exec mysql mysql -uroot -proot -e "
  CREATE DATABASE IF NOT EXISTS chosung_daily_test_migrations CHARACTER SET utf8mb4;
  GRANT ALL PRIVILEGES ON \`chosung_daily_test_migrations\`.* TO 'chosung'@'%';"
```

단어 시드 / 퍼즐 스케줄링:

```bash
uv run flask seed-words data/seed_words.csv
uv run flask schedule-puzzles --days 30
uv run flask search-books "데미안" --add 0   # 카카오/알라딘 API 키 필요 (.env)
uv run flask notify-operator-test           # 운영자 Slack 알림 도착 확인 (SLACK_WEBHOOK_URL)
```

## 운영: 백업 / 복구

prod·develop compose 에 `backup` 서비스가 돌면서 매일 **04:00 KST** 에 MySQL 을
덤프한다. 자세한 NAS 설정·리허설 절차는 `docs/RELEASE.md`.

| | |
|---|---|
| 덤프 위치 | 호스트 `${BACKUP_DIR}`(기본 `./backups`) ← 컨테이너 `/backups` bind mount |
| 파일 이름 | `chosung_daily-YYYYmmdd-HHMMSS.sql.gz` (mysqldump + gzip) |
| 보존 | 14일치 (`BACKUP_RETENTION_DAYS`, 오늘 것까지 14개) |
| 실패 알림 | `SLACK_WEBHOOK_URL` 로 POST (비워두면 알림만 생략) |

```bash
# 지금 한 번 백업 (04:00 을 기다리지 않고)
docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env \
  exec backup /scripts/backup.sh

# 복구 — 되돌릴 수 없다. 덤프 시점 이후의 행은 사라진다
./scripts/restore.sh <덤프.sql.gz> chosung-daily-prod      # 확인 프롬프트
./scripts/restore.sh -y <덤프.sql.gz> chosung-daily-prod   # 프롬프트 없이
```

`restore.sh` 는 MySQL 에 손대기 전에 `gzip -t` 로 덤프를 통째로 검사하고(깨진
덤프로 DB 를 날리지 않는다), 복원이 끝나면 **Redis 의 파생 키(`puzzle:` 오늘
퍼즐 캐시, `stats:`·`lb:` 카운터)를 직접 지운다**. Redis 는 MySQL 과 같이
되감기지 않아서, 안 지우면 앱이 복원된 DB 대신 복구 전 퍼즐을 계속 내놓는다
(TTL 26시간). 앱·워커를 재시작해도 안 지워진다 — Redis 는 별도 컨테이너다.
celery 브로커 큐와 rate limit 카운터는 DB 와 무관해서 건드리지 않는다.

## 운영: 업타임 모니터

`/health` 를 5분마다 보는 모니터는 [UptimeRobot](https://uptimerobot.com) 에
**사람이 한 번 등록**한다(서버 코드로는 못 하는 일, 스펙 §C.29). 등급별 응답은
아래 "설계 판단 08. 헬스체크 등급" 참고.

- 모니터 타입 **HTTP(s)**, URL `https://<배포 도메인>/health`, 간격 5분
- **"Keyword" 모니터로 `"status": "ok"` 를 보지 않는다.** Redis 만 죽은
  `degraded`(200) 상태에서도 알람이 울려버린다. HTTP 상태코드만 보게 두면
  DB 장애(503)만 알람이 된다 — 등급을 나눈 이유가 이것이다.
- 알림 채널은 운영자 메일. Slack 알림은 서버가 직접 보내는 운영자 알림
  (단어 잔량·배정 실패·백업 실패)과 섞지 않는다.

## 설계 판단

> 아래 `트랜잭션 경계`~`퍼즐 카테고리 비중` 은 초기 구현 때 쓴 항목이다. 스토어 출시
> 작업부터는 **티켓 번호를 붙인 `### NN. 제목`** 으로 이 절 끝에 덧붙인다 — 티켓이
> 병렬로 돌아가서, 같은 자리를 고치면 충돌한다.

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
`RATE_LIMITED`(429, 분당 제출 횟수 초과), `ACCOUNT_ALREADY_LINKED`(409, 이미 다른
계정이 연결된 게스트), `OAUTH_PROVIDER_UNAVAILABLE`(503, 콘솔 등록 전인 로그인 방식).

### Redis: 캐시 / 랭킹 / 통계 / rate limit

**캐시-어사이드 범위를 "단어 정보"로만 제한했다.** `puzzle:{date}:{lang}`에 캐시하는 건
`chosung`/`answer`/`hint`/`category`/`mask`처럼 그날 그 언어의 모든 유저에게 똑같은 값뿐이다.
`attempts_left`/`status`/힌트 공개 여부처럼 게스트마다 다른 값은 절대 캐시하지 않고
항상 DB에서 그 게스트의 attempts를 다시 읽는다 — 안 그러면 한 게스트의 진행 상태가
캐시를 통해 다른 게스트에게 새어나간다. `app/services/puzzle_cache.py`의 `CachedPuzzle`/
`CachedWord`는 `DailyPuzzle`/`Word` ORM과 같은 속성을 노출하는 덕 타이핑으로, 호출부
(`puzzle_service`, `guess_service`)가 캐시 히트/미스를 분기할 필요가 없게 한다. 지금
규모에선 이 구조로 충분하다고 판단했지만, 나중에 `Word`에 필드가 추가되는데 `CachedWord`를
깜빡하고 안 늘리면 캐시 히트 경로에서만 조용히 구버전 데이터가 나가는 위험이 있다 —
캐시 레이어가 더 커지면 `typing.Protocol`로 계약을 명시하는 게 안전하다.

**리더보드 정렬**: "적은 시도 우선, 같으면 빨리 푼 순"을 `lb:{date}:{lang}` Sorted Set 하나의
점수로 인코딩한다 — `score = attempt_no * 86400 + 자정부터 걸린 초`. 시도 횟수 차이가
걸린 시간(최대 86399초) 차이보다 항상 크기 때문에, ZSET 기본 오름차순 그대로 원하는
순서가 나온다(REV 불필요).

**통계**: `stats:{date}:{lang}` Hash에 `HINCRBY`로 "1"~"5"(그 시도 횟수에 맞춘 정답)와 "fail"을
누적한다. DB(`DailyStats`)로의 배치 반영은 Celery Beat가 매일 00:05 KST에 한다.

**rate limit은 고정 윈도우(fixed window)다.** 게스트가 "처음" 요청한 시점부터 60초
단위로 카운터가 리셋된다 — 슬라이딩 윈도우보다 구현이 단순하지만, 윈도우 경계에서
짧은 순간(예: 59.9초에 10번 + 60.1초에 또 10번) 분당 10회보다 더 통과할 수 있다. rate
limit의 목적이 "악의적 스팸 방지"라 이 정도 오차는 감수하기로 했다(`app/api/rate_limit.py`
에 근거 기록).

**Redis 장애 격리**: `app/utils/redis_safe.py`의 `safe_redis_call` 하나를 모든 Redis
호출(캐시/통계/랭킹/rate limit)이 거친다. Redis가 없거나 장애면 조용히 `default`를
돌려주고 호출부는 평소처럼 DB 경로로 계속 간다 — "Redis 장애 시 게임 자체(조회/제출)는
DB로 동작하고, 랭킹·통계만 실패"가 이 한 함수로 전부 구현된다. rate limit도 "제출"의
일부로 보고 fail-open(장애 시 그냥 통과)시켰다. `docs/perf.md`에서 Redis를 아예 내리고
부하 테스트를 돌려서 이 폴백이 실제로 동작하는 것까지 확인했다.

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

**"매일 자정 자동 실행"은 설정값과 스케줄러 계산까지만 확인했다.** `celery.conf.timezone
= "Asia/Seoul"`로 Beat의 crontab이 KST 기준으로 해석되게 했고, `crontab(...).
remaining_estimate(now)`로 다음 실행 예정 시각을 직접 계산해서 23:59:59/00:04:59
(KST)가 나오는 것까지 확인했다 — 이건 Beat가 내부적으로 쓰는 것과 같은 계산 함수라
단순히 설정값을 읽는 것보다는 신뢰도가 높지만, 실제로 자정을 넘기며 beat 컨테이너가
태스크를 큐에 넣는 순간을 지켜본 건 아니다. `celery call`로 두 태스크를 수동
트리거해서 워커가 정상 처리하는 것(태스크 로직 자체의 정확성)은 확인했지만, 이
둘은 서로 다른 수준의 증거라는 걸 구분해 둔다.

### 계정 연결 (구글/애플 OAuth)

원래 스펙(Phase 1~8)엔 없던 기능이다. 게스트 토큰이 브라우저 localStorage에만
있어서 기기를 바꾸면 기록이 끊기는 문제 때문에, 구글/애플 계정에 게스트를
연결해서 어느 기기에서 로그인해도 같은 기록으로 이어지게 하는 기능을 추가했다.
처음엔 카카오 로그인으로 만들었다가, "구글이랑 애플만 하자"는 결정으로 바꿨다
— 책 검색(`flask search-books`)에 쓰는 카카오 REST API 키와는 완전히 별개다.
아직 구글/애플 개발자 콘솔에 실제 앱을 등록 안 해서(`GOOGLE_CLIENT_ID` 등이
비어있으면 `app/extensions.py`의 `init_oauth`가 그 provider를 아예 등록 안 하고
503을 돌려줌) 실제 로그인 왕복은 한 번도 못 해봤다 — 등록 후 가장 먼저
확인해야 할 지점. 애플은 client_secret이 고정값이 아니라 `APPLE_PRIVATE_KEY`로
서명한 JWT라(`_apple_client_secret`), 구글보다 설정값이 하나 더 필요하다
(`.env.example` 참고). Apple Developer Program 멤버십은 이미 BuildUrPalace(iOS
출시작) 때 가입해둬서 추가 비용 없이 Services ID만 새로 만들면 된다.

**설계**: `Account` 테이블(게스트 1명당 계정 0~1개, `unique(provider,
provider_user_id)`)로 Guest를 건드리지 않고 위에 얹었다. 같은 provider 계정으로
다른 기기에서 로그인하면 기존에 연결된 게스트로 "전환"되고(처음 보는 provider
계정이면 지금 쓰던 게스트에 새로 연결), 이미 다른 provider가 연결된 게스트는
추가 연결을 거부한다(1게스트:1계정, `app/services/account_service.py`).

**진짜로 겪은 보안 버그 (로그인 CSRF)**: 처음 구현은 `/auth/<provider>/login`이
"어느 게스트에 연결할지"를 쿼리파라미터(`?token=<게스트 토큰>`)로 받았다.
문제는 그 파라미터를 아무나 원하는 값으로 채워서 링크를 만들 수 있다는
것 — 공격자가 **자기** 게스트 토큰을 넣은 로그인 링크를 피해자에게 보내고,
이미 구글/애플에 로그인돼 있는 피해자가 그 링크를 눌러 동의 화면만 넘기면,
피해자의 진짜 계정이 **공격자의 게스트**에 영구 연결돼버린다(unique 제약 때문에
한 번 묶이면 피해자가 나중에 자기 기기에서 다시 로그인해도 계속 공격자
게스트로 "전환"됨). 지금은 익명 게임 기록이라 피해가 제한적이지만, 나중에
결제/구독을 이 Account에 붙이기로 돼 있어서 그대로 뒀으면 계정 탈취급 문제가
될 뻔했다(보안 리뷰로 발견, 실제 콘솔 등록 전에 수정함).

고친 방법: "현재 브라우저가 어느 게스트인지"를 더 이상 클라이언트가 주는
값으로 안 믿는다. 대신 `POST /api/v1/session/sync`(Authorization 헤더로
인증)를 프론트가 페이지 로드마다 호출해서, Flask의 서명된 세션 쿠키
(`SESSION_COOKIE_SAMESITE=Lax`)에 `current_guest_id`를 심어두고,
`/auth/<provider>/login`은 그 쿠키만 본다. 공격자가 보낸 링크를 피해자가
눌러도 그 요청엔 피해자 자신의 세션 쿠키가 실리지, 공격자 것은 못 실린다
(SameSite 쿠키는 다른 사이트/출처에서 강제로 못 심음). `tests/test_oauth_routes.py`
의 `test_login_csrf_cannot_be_forged_via_query_param`이 이 수정을 검증한다.

**진짜로 겪은 버그 하나 더 (멀티 앱 오염, redis와 같은 패턴 재발)**: Authlib의
`OAuth()` 객체를 db/migrate처럼 "라이브러리가 앱별로 알아서 관리해준다"고
믿고 모듈 전역 하나로 썼는데, Authlib 소스를 보면 등록된 클라이언트가
**인스턴스 자신**에 영구 캐싱돼서 redis_client 때와 똑같은 문제였다(여러 Flask
앱이 같은 프로세스에 있으면 먼저 등록한 설정이 고정됨). 앱마다 새
`OAuth()` 인스턴스를 만들어서 `app.extensions`에 저장하는, redis 때와 동일한
해법으로 고쳤다. `tests/test_extensions_isolation.py`에 redis/OAuth 둘 다
회귀 테스트를 남겨뒀다 — 같은 실수를 또 하지 않으려고.

### 퍼즐 카테고리 비중 (book_title은 일요일만)

실제로 플레이해보고 나온 피드백: 책 제목이 일반 단어랑 비슷한 빈도로 섞이니까 안
읽어본 사람한텐 그냥 모르는 단어고, 여러 단어짜리 제목은 초성도 길어서 체감
난이도가 들쭉날쭉했다. `app/services/puzzle_schedule_service.py`의 `_pick_word`가
날짜의 요일을 보고 "오늘 원하는 카테고리"를 먼저 정한다 — 일요일(`BOOK_TITLE_WEEKDAY
= 6`)만 책 제목을 후보로 넣고, 나머지 요일은 일반 단어만 본다. 원하는 카테고리에
후보가 없으면(예: 일요일인데 최근에 안 쓴 책 제목이 없음) 카테고리 제한을 풀고
다시 찾아서, 빈 날짜가 생기진 않는다.

### 19. prod 프로젝트명 유지 이유 (compose 파라미터화)

같은 NAS 에서 prod 와 develop 을 동시에 돌리려고 `docker-compose.prod.yml` 에서
고정 `container_name` 과 최상위 `name:` 을 지우고, 호스트 포트·env 파일을
`${APP_PORT}`·`${ENV_FILE:-.env}` 로 뺐다. 프로젝트명은 `-p` 로 준다.

여기서 바꾸지 **않은** 게 하나 있다 — prod 의 compose 프로젝트명은 기존
`chosung-daily-prod` 를 그대로 쓴다. compose 의 named volume 실제 이름은
`<프로젝트명>_<볼륨키>` 라서, 프로젝트명을 "더 깔끔하게" 바꾸는 순간 기존
`chosung-daily-prod_mysql-data` 가 아니라 **빈 볼륨이 새로 생겨서 붙는다**.
서비스는 정상적으로 뜨고 `/health` 도 ok 인데 DB 만 비어 있어서, 퍼즐 기록과
게스트 토큰이 전부 날아간 것처럼 보인다(데이터는 옛 볼륨에 남아 있지만 아무도
안 본다). 이름 한 줄이 데이터 손실처럼 보이는 사고로 이어지는 구조라, 이름은
건드리지 않고 `docs/RELEASE.md` 첫 배포 체크에 "NAS 의 실제 프로젝트명·볼륨명
확인 후 `up`" 을 넣었다.

같은 이유로 `.env`/`.env.develop` 에 `COMPOSE_PROJECT_NAME` 을 넣어 둔다.
compose 는 프로젝트 디렉터리의 `.env` 를 자동으로 읽기 때문에, 누가 `-p` 를 빼고
`docker compose -f docker-compose.prod.yml up -d` 만 쳐도 디렉터리 이름에서
프로젝트명을 추측하지 않고 같은 프로젝트(= 같은 볼륨)에 붙는다.

### 01. 외부 호출 래퍼와 도메인 판정 함수의 분리

외부 provider(Slack, Apple, App Store, Play, Google Books) 호출은 `app/clients/<provider>.py`
의 **함수 하나**로만 둔다. 그 함수는 요청을 보내고 결과를 돌려주는 일만 하고, "이 상태면
광고를 끌 수 있는가", "어떤 문구로 알릴 것인가" 같은 판단은 `app/services/` 의 순수 함수에
남긴다.

이렇게 자른 이유는 테스트 경계다. provider 호출을 서비스 함수 안에 섞어두면 구독 권한 판정
하나를 확인하려고 매번 네트워크를 가짜로 만들어야 하고, 그 가짜가 실제 응답과 달라지는 순간
테스트가 거짓 초록이 된다. 래퍼가 함수 하나면 테스트는 **그 함수만** monkeypatch 하고
(`tests/test_operator_alert_service.py`), 판정 로직은 입력 → 출력으로 직접 검증된다
(네트워크 없음). 래퍼 자체의 테스트는 "실패해도 예외를 안 올리는가" 같은 경계 동작만 본다
(`tests/test_slack_client.py`).

### 01. Slack Webhook 선택 근거

운영자 알림(단어 잔량 부족, 퍼즐 배정 실패, 백업 실패)은 **Slack Incoming Webhook** 으로
보낸다. 받는 사람이 운영자 한 명이라 수신자 관리가 필요 없고, Webhook 은 URL 하나를 `.env`
에 넣으면 끝나서 OAuth 토큰·스코프·갱신이 없다. 이메일(SMTP)은 발신 도메인·스팸 평판을
챙겨야 하고, 봇 토큰 방식은 앱 등록·권한 승인 단계가 늘어난다 — 알림 하나에 그만한 설정을
들일 이유가 없다.

대신 Webhook 은 "URL 을 아는 사람은 누구나 그 채널에 글을 쓸 수 있는" 비밀값이라
`SLACK_WEBHOOK_URL` 은 커밋하지 않고 `.env.example` 에 빈 칸으로만 둔다. 값이 비어 있으면
`app/clients/slack.py` 가 전송을 건너뛰기 때문에 개발·테스트에서는 아무 설정 없이 돌아가고,
운영자는 값을 넣은 뒤 `uv run flask notify-operator-test` 로 도착을 한 번 확인한다.

전송 실패는 **호출자에게 예외를 올리지 않고 경고 로그만 남긴다**(타임아웃 3초). 호출자가
자정 퍼즐 배정이나 매일 백업이라, Slack 이 죽었다고 그 작업이 깨지면 알림을 붙인 쪽이
손해다 — Redis 장애 때 게임을 DB 로 계속 돌리는 것과 같은 판단이다.

그 경고 로그에는 **예외 타입과 HTTP 상태 코드만** 넣는다. `requests` 예외는 메시지
(`... for url: <URL>`)와 traceback 양쪽에 요청 URL 을 담는데, 여기서 URL 은 곧 비밀값이다 —
`exc_info=True` 로 두면 운영 실패 한 번에 Webhook 비밀이 로그 수집기로 복제되고, 로그는
회수할 수 없다. 노출 회귀는 `tests/test_slack_client.py` 가 가짜 응답에 URL 을 붙여서 잡는다.

### 01. CSRF 토큰 방식

웹 폼(계정 삭제, 운영자 화면)은 쿠키 세션만으로 인증하므로, 다른 사이트가 만든 POST 에도
쿠키가 실려서 "본인 의도 없이 삭제" 가 가능하다. 그래서 `app/csrf.py` 가 폼을 그릴 때 세션에
**1회용 토큰**(`secrets.token_urlsafe(32)`)을 심고, `@csrf_protected` 가 폼 hidden 값과
비교해 다르면 403 `FORBIDDEN` 을 낸다.

`SameSite` 쿠키만으로 막지 않는 이유가 있다. 애플 로그인 콜백이 cross-site top-level POST
(`response_mode=form_post`)로 들어와서 프로덕션 세션 쿠키가 `SameSite=None` 으로 풀려 있다
(`app/config.py` 의 `ProductionConfig`). 즉 이 서비스에서는 쿠키 속성이 CSRF 방어선이 못 된다.

토큰은 Flask-WTF 같은 확장을 붙이지 않고 직접 만들었다. 필요한 건 "세션에 난수를 심고
폼 값과 상수 시간 비교" 뿐이고, 폼 검증·필드 렌더링까지 딸려오는 확장을 들이면 면접에서
설명할 코드보다 설명할 라이브러리 동작이 많아진다.

설계상 세 가지를 의도적으로 정했다.

- **"1회용" 은 세션이 아니라 Redis 가 보장한다.** Flask 의 기본 세션은 서명된 쿠키라서 상태가
  전부 클라이언트에 있다. `session.pop` 은 응답 `Set-Cookie` 를 바꿀 뿐이라, 브라우저나
  중간 프록시가 들고 있던 **옛 쿠키를 그대로 다시 보내면 세션 안의 토큰이 되살아난다**
  (새로고침 연타·더블 클릭이 만드는 동시 제출은 애초에 전부 같은 옛 쿠키를 들고 온다).
  그래서 검증을 통과한 토큰은 해시를 키로 `SET csrf:used:<sha256> NX` 로 Redis 에
  기록한다 — `NX` 가 왕복 한 번의 원자적 연산이라 동시 제출 중 하나만 통과한다. TTL 은
  `PERMANENT_SESSION_LIFETIME`: Flask 가 세션 쿠키를 풀 때 이 값을 `max_age` 로 검사하므로
  그보다 오래된 쿠키는 애초에 세션이 안 열리고, 소비 기록을 더 들고 있을 이유가 없다.
  기록을 못 남기면(Redis 없음·장애) 통과시키지 않고 403 이다 — 랭킹·통계와 달리 여기서는
  "실행 못 함" 보다 **"계정 삭제가 두 번 실행됨"** 이 비싸서 폴백하지 않는다.
- **성공한 토큰만 폐기한다.** 틀린 값을 던진 요청이 세션 토큰을 지워버리면, 아무나 잘못된
  POST 를 한 번 보내서 사용자가 열어둔 폼을 무효화할 수 있다. 검증을 통과한 다음에만 토큰을
  버려서, 새로고침 재전송(같은 삭제가 두 번)은 막고 실패 요청은 폼을 건드리지 않는다.
- **비교는 bytes 로 한다.** `secrets.compare_digest` 는 비 ASCII 문자가 든 `str` 을 받으면
  `TypeError` 를 낸다 — 한글이 섞인 아무 값을 폼에 넣으면 403 이어야 할 요청이 500 이 된다.
  양쪽을 `encode()` 해서 넘긴다.
### 21. 백업: cron 데몬 대신 sleep 루프, 덤프는 bind mount

백업은 앱이 아니라 **독립 컨테이너**다(`docker-compose.prod.yml` 의 `backup`).
app/worker 가 뻗어 있어도 백업은 돌아야 하고, 반대로 백업 스크립트가 터져도 서비스는
살아 있어야 한다. Celery Beat 안에 넣지 않은 것도 같은 이유다 — Beat 가 죽으면
퍼즐 배정과 백업이 한꺼번에 멈춘다.

이미지는 **`mysql:8` 을 재사용**한다. `mysqldump`·`gzip`·`curl`·GNU `find`·`date` 가
전부 들어 있고, NAS 가 이미 당겨 둔 이미지라 추가로 받을 게 없다(실측으로 확인).

그 안에서 **cron 데몬을 쓰지 않고** `backup-cron.sh` 가 "다음 04:00 까지 자고
일어나서 덤프" 를 반복한다. `mysql:8` 에는 cron 이 없어서 쓰려면 컨테이너가 뜰
때마다 패키지를 받아와야 하고(NAS 의 네트워크에 매번 의존), crond 가 죽으면 백업만
조용히 멈춘다 — 아무 로그도 없이. sleep 루프는 PID 1 이라 죽으면 compose 의
`restart: unless-stopped` 가 바로 다시 띄우고, 컨테이너 로그에 다음 실행 시각이
찍힌다. 시각 계산은 `date -d` 같은 GNU 확장 없이 "하루 안의 초" 로만 해서(KST 는
DST 가 없다) macOS 에서도 같은 스크립트를 테스트할 수 있다.

**덤프만 bind mount 한다.** DB 볼륨은 DSM 의 `/volume1` ACL 때문에 named volume
이어야 하지만(§19), 덤프는 반대로 호스트 폴더에 있어야 백업이다 — 컨테이너와 볼륨이
날아간 상황에서 꺼내야 하니까. `backup` 컨테이너는 root 로 돌아서 mysql(uid 999)을
막던 ACL 문제가 없다.

덤프 옵션은 `--single-transaction`(04:00 에 누가 플레이해도 테이블을 잠그지 않고 한
시점을 뜬다) + `--databases ... --add-drop-database`(덤프 안에 DROP/CREATE DATABASE
가 들어가서 복구가 "그 시점 그대로" 가 된다 — 복구 후에 덤프 이후 행이 남지 않는다).
비밀번호는 `--defaults-extra-file` 로 넘긴다. `-p<비밀번호>` 로 주면 같은 호스트의
`ps` 출력에 그대로 보이고, `restore.sh` 는 아예 비밀번호를 모른다(mysql 컨테이너 안의
env 를 쓴다).

**테스트는 셸 스크립트를 실제로 실행한다**(`tests/test_backup_restore.py`).
`mysqldump`·`curl`·`docker` 만 PATH 앞의 스텁으로 바꿔 인자와 stdin 을 기록하고,
gzip·find·date 는 진짜를 쓴다. 그래서 "gzip 덤프가 떨어지는지", "14일 지난 파일이
지워지는지", "실패하면 Slack 으로 쏘는지", "비밀번호가 명령줄에 안 나오는지" 를
흉내가 아니라 스크립트가 한 일로 본다. 컨테이너를 띄우는 복구 리허설은
`docs/RELEASE.md` "복구 리허설" 절에 실측으로 남겼다.

### 02. 퍼즐 언어 모델 — expand–contract 대신 마이그레이션 1개

단어·오늘의 퍼즐·게스트에 퍼즐 언어(ko/en)를 넣는 변경은 보통 expand–contract 3단계
(새 컬럼 추가 → 양쪽에 쓰기 → 옛 컬럼 제거)로 한다. 여기서는 **마이그레이션 하나 +
코드 변경 하나**로 끝냈다. 이 서비스의 쓰기 트래픽은 운영자 한 명(CLI·관리자 화면)이고
읽기도 하루 한 문제라, 무중단 전환으로 얻는 값보다 "3단계가 다 끝날 때까지 두 스키마를
동시에 지탱하는" 비용이 크다. 전환은 컨테이너 재시작 한 번으로 끝난다.

대신 세 가지를 지켰다.

- **기존 행은 전부 `ko`.** 세 컬럼 모두 `server_default='ko'` 로 추가해서, 마이그레이션이
  도는 순간 기존 데이터가 한국어 퍼즐로 남는다. 코드에도 기본값이 있어 언어를 안 적는
  옛 호출부가 그대로 돈다.
- **`chosung` 컬럼을 지우지 않았다.** 기존 클라이언트가 읽는 응답 필드라서, 모두 `mask`
  로 옮겨간 뒤에 따로 지운다. 여기까지는 "컬럼을 더한다" 뿐이라 되돌리기가 싸다.
- **왕복을 테스트로 묶었다.** `tests/test_migrations.py` 가 별도 DB 에서
  `upgrade → 데이터 삽입 → downgrade → upgrade` 를 `flask db` 서브프로세스로 돌려
  ko 데이터가 그대로 조회되는지 본다. 다른 테스트는 `db.create_all()` 로 스키마를 만들어서
  마이그레이션 파일을 한 줄도 실행하지 않는다 — 그 구멍을 메우는 테스트다.

`daily_puzzle` 의 유니크 키는 `(puzzle_date)` 에서 `(puzzle_date, language)` 로 넓혔다.
자정 배정이 언어별로 따로 돌아서(한 언어가 실패해도 다른 언어는 배정된다) DB 제약도
"날짜당 하나" 가 아니라 "날짜·언어당 하나" 가 맞다. `daily_stats` 도 같은 이유로 PK 를
`(puzzle_date, language)` 로 바꿨다.

### 02. 가림(mask) 포맷 — 언어마다 다른 렌더링 코드를 만들지 않기

한국어는 초성, 영어는 모음 빈칸이라 화면에 찍히는 모양이 다르다. 클라이언트(웹·앱)가
언어별 분기를 갖지 않도록, 서버가 **타일 목록 하나**로 내려준다.

```json
[{"t": "h", "c": ""}, {"t": "r", "c": "P"}, {"t": "s", "c": " "}]
```

- `r` (revealed) 보이는 타일 — `c` 가 그대로 찍힌다 (ko 는 초성, en 은 자음)
- `h` (hidden) 빈 타일 — `c` 는 **항상 빈 문자열**이다
- `s` (separator) 구분자(공백·하이픈) — 타일이 아니라 타일 사이 간격이고, 길이에 안 들어간다

설계상 정한 것들.

- **빈 타일에 정답 글자를 담지 않는다.** `{"t":"h","c":"a"}` 로 내려주면 응답만 열어봐도
  정답이 보인다. 그래서 `c` 는 빈 문자열이고, 테스트가 이걸 직접 지킨다
  (`test_english_hidden_tile_never_carries_the_answer_letter`).
- **구분자를 타일이 아니라 간격으로 뺐다.** `"harry potter"` 의 공백을 빈 타일로 두면
  플레이어가 공백을 입력해야 하는지 헷갈리고 길이도 틀리게 보인다. `length` 는 `s` 를
  제외한 글자 수다.
- **영어는 보이는 글자를 대문자로 통일한다.** 정답 비교가 대소문자를 무시하니 화면도
  통일돼야 한다 — 운영자가 CSV 에 `Apple` 로 넣든 `apple` 로 넣든 같은 문제가 된다.
- **계산은 저장 시 한 번.** `app/utils/mask.py` 의 `build_mask(언어, 정답)` 은 순수 함수고,
  `Word` 의 `before_insert`/`before_update` 이벤트가 결과를 `mask` 컬럼에 넣는다. 단어를
  저장하는 경로가 여러 개(CLI 시드·책 등록·관리자 CRUD)라서, 각 호출부가 가림 계산을
  기억하게 두는 대신 모델 한 곳에 모았다. 응답마다 다시 계산하지 않으니 캐시도 그대로다.

### 03. 연속 기록은 퍼즐 언어와 무관하다

같은 날 ko 와 en 퍼즐이 따로 있으니, "연속 기록(streak)을 언어별로 따로 세는" 선택도
가능했다. 그렇게 하지 않았다. 플레이어가 느끼는 연속 기록은 "매일 들어왔는지" 하나이고,
언어별로 쪼개면 중간에 언어를 바꾼 사람의 기록이 둘로 갈려 둘 다 끊긴 것처럼 보인다.

그래서 `GuestStats` 는 언어 컬럼을 갖지 않고, 정답 기록 함수(`guess_service._record_solve`)
가 이렇게 판정한다.

- `last_solved_date == 오늘` → streak 은 손대지 않는다 (그 날 이미 이어졌다)
- `last_solved_date == 어제` → +1
- 그 밖 → 1 로 리셋

`solved_count` 만 예외로 매번 올린다 — 이건 "푼 퍼즐 수"라서 같은 날 ko·en 을 둘 다
맞추면 2 가 맞다. 이 두 규칙이 한 함수 안에서 갈리는 게 헷갈릴 수 있어서, "같은 날
ko → en 정답" 케이스를 테스트로 박아뒀다
(`tests/test_streak.py::test_solving_both_languages_on_the_same_day_keeps_streak_and_counts_twice`).

### 03. 캐시 키는 언어로 갈리고, rate limit 키는 안 갈린다

퍼즐 캐시 `puzzle:{date}:{lang}`, 통계 `stats:{date}:{lang}`, 리더보드 `lb:{date}:{lang}`
— 같은 날짜에 언어마다 다른 퍼즐이 있으니 캐시·집계는 언어를 키에 넣어야 한다. 안 넣으면
en 플레이어가 ko 퍼즐 캐시를 받아 가고 리더보드가 두 언어의 점수를 섞는다.

반대로 rate limit 키는 `ratelimit:guess:{guest_id}` 로 언어가 없다. 이 카운터의 목적은
"한 사람이 분당 몇 번 제출하는가"(스팸 방지)이고, 언어를 키에 넣으면 언어를 번갈아
바꾸는 것만으로 제한이 두 배가 된다 — 보호 장치에 공짜 우회로를 만드는 셈이다. 언어를
바꿔도 카운터가 이어지는 걸 테스트가 지킨다
(`tests/test_rate_limit.py::test_rate_limit_counter_survives_a_language_change`).

### 03. 언어 인지 응답 — `chosung` 을 어떻게 채우는가

`GET /puzzles/today` 는 신규 클라이언트용 `mask` 와 함께 ko 호환 필드 `chosung` 을
계속 내려준다. ko 는 `Word.chosung` 컬럼의 **현행 값 그대로**다 — 돌고 있는 웹
클라이언트가 보는 문자열이 한 글자도 바뀌지 않아야 한다. en 은 그 컬럼이 자리표시자
(`_____`)뿐이라 쓸 수 없어서, `mask` 의 보이는 글자로 같은 모양의 문자열을 만든다
(`mask_to_text`, 예: `apple` → `_PPL_`). 이 필드를 en 에서 `null` 로 둘 수도 있었지만,
타입이 언어에 따라 바뀌면 옛 클라이언트가 `null` 을 그대로 그려서 깨진다.

`length` 는 `mask` 기준(구분자 제외) 글자 수다 — 같은 응답 안의 `mask` 와 숫자가
안 맞으면 클라이언트가 타일을 몇 개 그릴지 알 수 없다. 제출 쪽 길이 검증(공백·하이픈
제거 후 비교)은 티켓 04 에서 같은 기준으로 합류한다.

통계·리더보드는 `?language=` 로 언어를 명시할 수 있고(기본 게스트 선호), 응답에
`language` 가 들어간다. 퍼즐 조회는 반대로 선호 언어 하나만 돌려준다 — 플레이 중인
퍼즐이 요청 파라미터에 따라 달라지면 "오늘 내 퍼즐" 이라는 개념이 흔들린다.
### 20. 배포 스크립트를 ssh 표준입력으로 흘려보내는 이유

`main`/`develop` 푸시가 NAS 에 자동 배포된다. 워크플로가 NAS 에 붙어서 하는 일은
한 줄이다 — `ssh nas 'bash -s -- prod' < deploy/deploy.sh`.

처음엔 당연히 `ssh nas '/volume1/docker/chosung-daily/deploy/deploy.sh prod'` 였다.
그런데 그 스크립트가 하는 첫 일이 `git pull` 이다. bash 는 스크립트 파일을 한 번에
읽어두지 않고 실행하면서 필요한 만큼 읽기 때문에, **실행 중인 스크립트 파일이 pull
로 바뀌면 bash 가 바뀐 파일의 엉뚱한 바이트 위치에서 다음 명령을 읽는다**. 스크립트
길이가 바뀌는 커밋에서만, 그것도 배포 중에만 터지는 종류의 버그다. 스크립트를
NAS 체크아웃 밖(`/volume1/docker/deploy.sh`)에 따로 설치해 두는 방법도 있지만,
그러면 "레포의 스크립트" 와 "NAS 에서 실제로 도는 스크립트" 가 갈라져서 사람이
복사하는 걸 잊는 순간 조용히 옛 절차로 배포된다.

표준입력으로 보내면 둘 다 안 생긴다. 러너가 읽는 파일은 방금 CI 를 통과한 커밋의
것이고(ssh 로 보낸 뒤로는 NAS 의 git 이 뭘 하든 상관없다), NAS 에는 설치할 것도
없다.

**대신 본문 전체를 `main()` 에 넣고 `main "$@" < /dev/null` 로 부른다.** 표준입력
자리에 스크립트가 들어와 있으면 "스크립트가 입력을 안 받으니 괜찮다" 로 끝나지
않는다 — 자식 프로세스가 그 표준입력을 그대로 물려받기 때문이다. `docker compose
exec -T` 는 `-T` 로 TTY 만 끄고 표준입력은 컨테이너로 흘려보내므로, 마이그레이션
한 줄이 **bash 가 아직 안 읽은 스크립트 뒷부분**(서비스 기동 확인·`/health` 루프)을
통째로 먹는다. bash 는 읽을 게 없어진 자리에서 조용히 0 으로 끝나고, 서비스도
`/health` 도 확인하지 않은 배포가 Actions 에서 초록색이 된다. 명령마다
`< /dev/null` 을 붙이는 대신 본문을 함수로 묶어 한 번에 끊은 건, 나중에 입력을
읽는 명령을 하나 더 추가해도 같은 사고가 다시 안 나게 하기 위해서다. 함수 정의는
bash 가 본문 실행 전에 끝까지 읽으므로 표준입력을 끊어도 안전하다.

같은 이유로 배포 대상은 인자 하나(`prod`/`develop`)로만 받는다. 브랜치·체크아웃
디렉터리·compose 프로젝트명·env 파일이 그 하나에서 갈린다. 호스트 포트는 예외로,
스크립트에 적지 않고 `docker compose port app 5000` 으로 **compose 가 실제로 발행한
포트**를 물어본다 — 포트의 진실은 env 파일의 `APP_PORT` 라서, 스크립트에 8089/8090
을 또 적으면 두 군데가 갈라질 수 있다.

`/health` 200 만 보지 않고 `compose ps` 로 5개 서비스가 다 running 인지 따로
확인한다. `/health` 는 app 컨테이너만 보기 때문에 worker·beat 가 뻗어도 초록색이
나오고, 그러면 퍼즐 배정이 멈춘 걸 며칠 뒤에 알게 된다. 그 200 도 `curl -f` 의
종료 코드로 보지 않고 `-w '%{http_code}'` 로 상태 코드를 직접 비교한다 — `-f` 는
4xx·5xx 에서만 실패해서, `/health` 가 로그인으로 302 리다이렉트되는 설정 사고를
초록색으로 통과시킨다.

**대상과 함께 "CI 를 통과한 커밋 sha" 도 넘긴다.** 러너의 `checkout` 을 `head_sha`
로 맞춰도 그건 러너가 읽는 `deploy.sh` 만 정한다 — NAS 는 자기 git 으로 브랜치를
가져오기 때문에, A 의 CI 로 시작한 배포가 그 사이 올라온 B(아직 CI 중이거나 CI 가
실패한 커밋)를 빌드할 수 있다. 그래서 스크립트가 `git fetch` 뒤에 브랜치 끝이 아직
그 sha 인지 보고, 아니면 배포를 중단한다. B 는 자기 CI 가 통과하면 자기 배포로
올라간다. 반대로 "브랜치가 움직였어도 받은 sha 를 그대로 빌드" 하면, B 가 이미 올라간
뒤에 A 의 배포가 끝나면서 운영이 조용히 옛 커밋으로 되돌아갈 수 있어서 그렇게 하지
않았다.

**그 sha 검사는 스크립트 안에 있으니 신뢰 경계가 못 된다.** 배포 잡을 여는 조건이
`workflow_run` 의 브랜치 이름과 성공 여부뿐이면, `ci.yml` 이 `pull_request` 에서도
도는 탓에 **이름이 `main`/`develop` 인 PR 브랜치의 CI** 도 배포를 연다. 그러면 러너가
그 커밋을 checkout 해서 **그 커밋의 `deploy.sh`** 를 배포 secret 으로 연 NAS 에 흘려
보낸다 — 스크립트 안의 어떤 검사도 같은 PR 이 같이 고칠 수 있으니 소용없다. 그래서
잡의 `if` 에서 **선행 CI 가 이 저장소의 `push` 였는지**(`workflow_run.event == 'push'`,
`head_repository.full_name == github.repository`)를 checkout·secret 사용 전에 본다.
### 10. 앱 로그인은 id_token 교환 (ADR 0002 요약)

웹은 리다이렉트 + 세션 쿠키로 계정을 연결하지만, 앱은 같은 흐름을 WebView 에 태우지
않는다 — 구글이 임베디드 WebView OAuth 를 차단하고, 시스템 브라우저로 열면 위의 로그인
CSRF 방어(세션 쿠키)가 깨져서 PKCE 식 상태 저장을 따로 만들어야 한다. 대신 앱이 네이티브
SDK 로 받은 `id_token` 을 **게스트 Bearer 토큰과 함께** `POST /api/v1/auth/token-exchange`
로 보내고, 서버가 JWKS 로 서명과 `aud` 를 검증한 뒤 웹과 **같은** `link_or_switch_account`
로 연결한다. 연결 요청 자체가 Bearer 로 인증되니 로그인 CSRF 가 구조적으로 성립하지 않는다
— 웹에서 실제로 겪은 그 버그가 앱 경로에는 아예 없다.

**aud 매트릭스**: 서버는 요청만 보고 플랫폼을 알 수 없어서, provider 별로 받아들일 `aud`
집합을 설정으로 고정한다(`app/services/app_login_service.py` 의 `allowed_audiences`).

| provider | 플랫폼 | 앱이 쓰는 값 | 서버가 받는 `aud` | 설정값 |
|---|---|---|---|---|
| google | iOS | iOS 클라이언트 ID | iOS 클라이언트 ID | `GOOGLE_IOS_CLIENT_ID` |
| google | Android | `serverClientId` = 웹 클라이언트 ID | 웹 클라이언트 ID | `GOOGLE_WEB_CLIENT_ID` |
| apple | iOS | `sign_in_with_apple` | 앱 번들 ID | `APPLE_APP_BUNDLE_ID` |
| apple | Android | 지원 안 함 | — | — |

Android 의 구글 클라이언트 ID 는 APK 서명(SHA-1) 검증용이라 `aud` 에 나오지 않는다 —
`serverClientId` 로 넘긴 웹 클라이언트 ID 가 들어온다. 설정값이 비어 있으면 받아들일
`aud` 집합이 빈 집합이 되는데, 이때 검증을 건너뛰지 않고 **거부**한다. 설정 누락이
"아무 토큰이나 통과" 로 조용히 바뀌는 쪽이 훨씬 위험하다. 같은 이유로 허용 알고리즘을
`RS256` 하나로 고정했다(JWKS 는 공개 정보라, 알고리즘을 토큰 헤더에 맡기면 공개키를 HMAC
비밀로 쓴 위조 토큰이 통과한다 — `tests/test_id_token_verify.py` 가 직접 만든 위조 토큰으로
이 둘을 고정한다).

**애플 토큰을 보관하는 이유**: 애플은 계정 삭제 시 연결 철회(revoke)를 요구하는데, revoke
API 가 받는 건 `id_token` 이 아니라 **refresh/access token** 이다. 그래서 앱은 로그인마다
`authorization_code` 도 함께 보내고, 서버가 그걸 애플 토큰 엔드포인트에서 교환해 받은
`refresh_token` 을 `Account.provider_refresh_token` 에 **Fernet 암호화**(SECRET_KEY 파생 키,
`app/utils/crypto.py`)해서 넣는다. 평문으로 두면 DB 유출 한 번이 "애플 계정 연결까지 넘어감"
이 되고, 키를 설정값으로 하나 더 늘리는 대신 SECRET_KEY 에서 파생한다(이 값의 수명은
SECRET_KEY 와 어차피 같다). 발급 client 도 `Account.provider_client_id` 에 같이 남긴다 —
애플 revoke 는 "그 토큰을 발급한 client" 의 자격증명으로만 받아주고, 웹은 Services ID,
앱은 번들 ID 로 발급되기 때문이다. 웹 콜백(`/auth/apple/callback`)도 같은 두 컬럼에 저장해서
삭제 경로가 "웹으로 연결했는지 앱으로 연결했는지" 를 구분할 필요가 없게 했다(실제 revoke
호출은 계정 삭제 티켓).

판단 두 가지를 더 적어둔다.

- **애플인데 `authorization_code` 가 없으면 400 으로 거절한다.** 요청 스키마에서 이 필드가
  선택인 건 구글이 안 보내기 때문이고, 애플에서 빠지면 "연결은 됐는데 나중에 철회할 수단이
  없는 계정" 이 생긴다 — 그건 애플 심사 요구사항(계정 삭제 시 연결 철회)을 못 지키는 상태라
  아예 만들지 않는다.
- **교환으로 받은 `id_token` 의 `sub` 를 앱이 보낸 `id_token` 의 `sub` 와 비교한다.** 안 하면
  남의 `authorization_code` 를 끼워 넣어 그 사람의 refresh token 을 내 계정에 붙일 수 있다.
  교환 응답의 토큰도 앱이 보낸 것과 똑같이 서명·`aud` 를 검증한다.

JWKS 는 provider 가 키를 교체할 때만 바뀌는 공개 정보라 프로세스 안에 1시간 캐시한다.
redis 클라이언트·Authlib 레지스트리와 달리 앱 설정과 무관한 값이어서(어느 Flask 앱이 물어도
같은 공개키) `app.extensions` 가 아니라 모듈 전역에 둬도 "멀티 앱 오염" 이 생기지 않는다.
다만 **캐시에 없는 `kid` 를 보면 TTL 을 기다리지 않고 그 자리에서 공개키를 다시 받는다** —
provider 가 키를 교체하면 새 `kid` 로 서명된 정상 토큰이 들어오는데, 캐시가 따뜻한 프로세스가
TTL 끝까지(최대 1시간) 그 로그인을 전부 거부해버린다. 다시 받아도 없는 `kid`·틀린 서명은 그대로
거부고, 모르는 `kid` 를 박은 토큰으로 provider JWKS 엔드포인트를 때리지 못하게 이 갱신은
provider 당 `JWKS_REFRESH_MIN_INTERVAL_SECONDS`(60초)에 한 번으로 제한한다.

애플 client_secret(JWT)을 만드는 함수는 이 티켓에서 `app/extensions.py` 의
`apple_client_secret(app, client_id)` 로 바뀌었다(웹 Services ID 와 앱 번들 ID 를 모두 서명할 수
있게 인자화 + 공개). 위 "설계 판단"·"알려진 제한사항" 의 기존 항목에 나오는 `_apple_client_secret`
은 같은 함수의 예전 이름이다 — 공유 절은 덧붙이기만 하는 규칙이라 그 줄들은 건드리지 않았다.
### 08. 점검·최소 버전을 서버 설정으로 (`app_setting` + `/api/v1/config`)

스토어에 올라간 앱은 고칠 수가 없다. 서버만 내려야 하는 점검 시간이 생겼거나,
특정 버전 이하에서 더 못 쓰게 막아야 할 때(예: 응답 포맷이 바뀜) **앱을 새로 심사
받지 않고** 끄고 켜야 한다. 그래서 두 값을 코드·환경변수가 아니라 DB 행에 둔다 —
환경변수면 값을 바꿀 때 재배포가 필요하고, 그때 서버가 재시작한다.

- **키·값 테이블 하나**(`app_setting`: `setting_key`, `value`, `updated_at`)로 끝낸다.
  설정이 네 개(최소 버전 iOS/Android, 점검 on/off·메시지)뿐이라 컬럼을 하나씩 가진
  "설정 한 줄 테이블" 을 만들면 항목이 늘 때마다 마이그레이션을 또 해야 한다. 값은
  전부 문자열로 받고 의미(불리언·버전 문자열)는 읽는 쪽인
  `app/services/app_config_service.py` 가 정한다. Spring 의 `@ConfigurationProperties`
  대신 DB 를 보는 셈 — 운영자가 바꿔야 하는 건 코드 설정이 아니다.
- **기본값은 코드에만 둔다.** 마이그레이션이 기본값 행을 심지 않는다. 두 곳에
  기본값이 있으면 어긋나고, 빈 테이블로도 `/config` 가 정상 응답해야 한다. 최소
  버전 기본값은 첫 릴리스인 `1.0.0` 이라 아무도 강제 업데이트에 걸리지 않는다.
- **점검 플래그는 꺼진 쪽으로 기운다.** `value` 가 `"true"`/`"1"` 일 때만 켜고, 그
  밖의 값(빈 문자열·오타)은 전부 꺼진 것으로 읽는다. 실수로 켜져서 전체 유저가
  점검 화면을 보는 쪽이 반대보다 훨씬 비싸다.
- **캐시 60초.** 앱이 시작할 때마다 부르는 엔드포인트라 매번 DB 를 때릴 이유가 없고,
  반대로 점검을 켠 뒤 퍼지는 데 1분 넘게 걸리면 운영자가 답답하다. 캐시는 Redis 고,
  Redis 가 죽으면 DB 에서 다시 만들어 응답한다(아래 "헬스체크 등급" 과 같은 원칙).
- **경로는 `/api/v1/config`, 헬스체크는 루트 `/health`.** 앱이 `API_BASE_URL` 하나로
  모든 JSON API 를 부르니 설정도 같은 prefix 에 둔다. 반면 `/health` 는 앱이 아니라
  배포 스크립트·업타임 모니터가 보는 운영용 엔드포인트라 버전 prefix 없이 루트에
  둔다 — 배포 경로를 바꾸면 모니터 설정도 같이 바꿔야 한다.
- **스토어 링크는 환경변수**(`STORE_URL_IOS`, `STORE_URL_ANDROID`, `APP_STORE_ID`).
  운영자가 수시로 바꾸는 값이 아니고 앱을 올릴 때 한 번 정해지는 값이라 DB 행으로
  둘 이유가 없다. 아직 스토어에 등록 전이면 비어 있고, 그때 응답은 `null` 이다.
  `APP_STORE_ID` 는 웹 Smart App Banner 메타 태그 전용이라 `/config` 응답 필드에는
  넣지 않았다(스펙 §A' 의 응답 필드 네 개를 그대로 지킨다).

### 08. 헬스체크 등급 (503 / 200 + degraded)

업타임 모니터는 "사람을 깨울 상태" 만 실패로 봐야 한다. 이 서비스에서 DB 와 Redis 는
무게가 다르다 — 퍼즐·시도 기록은 DB 에 있어서 DB 가 죽으면 게임 자체가 안 되지만,
Redis 는 캐시·랭킹·통계·rate limit 용이고 전부 폴백이 있다(위 "Redis" 절). 그래서
`/health` 가 둘을 한 덩어리로 묶지 않고 등급을 나눈다.

| 상태 | HTTP | `status` | 뜻 |
|---|---|---|---|
| 정상 | 200 | `ok` | 둘 다 응답 |
| Redis 장애 | 200 | `degraded` | 랭킹·통계는 빈 값, 게임은 DB 로 그대로 돌아감 |
| DB 장애 | 503 | `down` | 퍼즐을 못 읽는다 — 깨워야 한다 |

Redis 장애를 503 으로 올리면 "게임은 되는데 알람이 울리는" 상태가 되고, 반대로 DB
장애를 200 으로 숨기면 모니터가 못 잡는다. `apple_secret_expires_at` 은 애플
client_secret(JWT) 만료 시각 자리로, 요청 경로 갱신을 넣는 티켓에서 채운다(지금은
`null`). 응답 본문에 버전·호스트명 같은 정보는 넣지 않는다 — 인증 없이 열려 있다.

Sentry 는 `SENTRY_DSN` 이 있을 때만 켠다(`app/observability.py`). 초기화 지점을
`create_app()` 한 곳으로 모아 Flask·Celery 통합을 같이 등록했다 — 워커·Beat 도
`celery_app.py` 에서 같은 `create_app()` 을 거치기 때문에, 웹과 워커가 환경·릴리스
태그를 따로 관리하지 않는다.

**Sentry 로 무엇을 보내지 않는지는 `data_collection` 으로 못 박는다.** 처음엔
`send_default_pii=False` 만 명시해두고 "요청 쿠키·바디는 안 따라간다" 고 적었는데,
최종 리뷰에서 그게 틀린 걸 재현으로 잡았다 — 그 옵션은 쿠키·유저 식별자만 끄고 요청
**본문**은 PII 설정과 무관하게 기본 수집이다. OAuth 콜백이 한 번 500 이 나면 애플이
보낸 인증 코드(`code`)와 최초 로그인 `user` JSON(이메일·이름)이 그대로 이벤트에
실린다. 기본 스크러버도 `code`/`user` 는 민감어 목록에 없어서 못 막는다. 그래서
`app/observability.py` 의 `SENTRY_DATA_COLLECTION` 에서 요청 본문·쿼리스트링·쿠키·
유저 식별자(IP)·SQL 바인드 파라미터·Celery task 인자를 범주별로 끈다. 지역 변수도
껐다 — `flask/app.py:wsgi_app` 프레임의 `environ` 에 `?code=...` 와 `HTTP_COOKIE` 가
통째로 들어 있고, 이름 기준 필터는 그 안쪽을 못 본다. 남는 건 예외·스택·소스
컨텍스트·메서드·경로·환경·릴리스다(운영에서 원인 찾기엔 충분했다).

함정: 이런 보장은 `sentry_sdk.init` 인자를 mock 으로 보는 테스트로는 검증이 안 된다.
`tests/test_sentry.py` 뒤쪽은 실제 SDK 를 켜고 Transport 만 메모리로 바꿔서 완성된
이벤트 payload 에 민감값이 없는지 본다. 설정을 손대면 이 테스트가 잡아준다.

## 부하 테스트 요약

자정 트래픽 스파이크(0→50 VU, `GET /puzzles/today` + 30% `POST .../guesses`)로
캐시 적용 전/후를 비교했다. 캐시는 코드를 안 건드리고 Redis 컨테이너를 내려서
"미적용" 상태를 만들었다 — Redis 장애 폴백이 실제로 동작하는지도 같이 확인한
셈이다.

| 지표 | 캐시 미적용 | 캐시 적용 | 개선 |
|---|---|---|---|
| 전체 `http_req_duration` p95 | 65.31ms | 21.66ms | 약 3.0배 |
| `GET /puzzles/today` p95 | 62.39ms | 19.76ms | 약 3.2배 |
| `POST .../guesses` p95 | 69.53ms | 24.28ms | 약 2.9배 |
| 에러율 | 0% | 0% | - |

50 VU·분당 10회 rate limit·게스트별 `FOR UPDATE` 락이 같이 걸린 상태에서도
에러 0%였다. 방법론, RPS가 거의 안 변한 이유(닫힌 모델 테스트의 한계) 등
자세한 내용과 원본 수치는 [`docs/perf.md`](docs/perf.md) 참고.

## 알려진 제한사항 / 남은 작업

- **구글/애플 OAuth 미등록**: 개발자 콘솔에 앱을 아직 안 만들어서 실제 로그인
  왕복을 못 해봤다 (`.env`에 `GOOGLE_CLIENT_ID`/`APPLE_*` 채우면 바로 켜짐). 구글은
  `http://localhost:8000/...`를 리디렉션 URI로 공식 지원해서 로컬에서 바로
  테스트할 수 있지만, **애플은 Return URL이 HTTPS + 실제 등록된 도메인이어야
  해서 `localhost`를 아예 못 쓴다**(ngrok/Cloudflare Tunnel로 임시 터널을 뚫지
  않는 이상). 구글만 먼저 로컬로 테스트할 수도 있었지만, 두 provider를 다른
  방식으로 다루지 않으려고 **구글도 애플과 똑같이 실제 배포(NAS) 도메인이
  생긴 뒤에 같이 등록·테스트하기로 함** — 그때까지 OAuth 로그인은 코드만
  준비된 상태로 둔다.
- **애플 client_secret(JWT)은 앱 시작 시점에 한 번만 만든다**(`_apple_client_secret`,
  유효기간 150일). 재배포나 재시작 없이 앱 프로세스가 150일보다 오래 떠 있으면
  애플 로그인만 조용히 실패하기 시작한다 — 지금은 주기적 재배포로 자연스럽게
  갱신되는 걸 전제로 둔 단순화고, 그 전제가 깨지면(예: 오래 안 건드리고 방치)
  Beat 태스크로 주기적 재발급하는 식으로 바꿔야 한다.
- **책 검색 API 키: 카카오만 발급, 알라딘은 보류**: `flask search-books`가
  알라딘 쪽은 TTBKey 없이는 빈 결과만 돌려준다(의도적으로 나중으로 미룸).
  카카오 쪽은 실제로 테스트 완료 — `add_word_from_book`에 중복 체크가 없어서
  같은 책을 `--add`로 두 번 넣으면 Word가 중복 생기는 버그를 그 과정에서
  발견해 고쳤다(`seed_words_from_csv`와 같은 (answer, category) 기준 중복
  방지). 다만 **철자/띄어쓰기가 다르면 다른 단어로 취급**한다 — 예를 들어
  수동 시드 CSV의 "어린왕자"와 카카오 API가 주는 실제 제목 "어린 왕자"(띄어쓰기
  있음)는 서로 다른 Word로 남는다. 코드 버그는 아니고 단어 풀을 수동 시드와
  API 등록을 섞어 쓸 때 생기는 콘텐츠 큐레이션 이슈라, 자동으로 고치진
  않았다 — 등록 전에 `flask search-books`로 먼저 검색해서 철자를 확인하는
  걸 권장.
- **rate limit 고정 윈도우**: 분당 10회가 윈도우 경계에서 최대 2배까지 샐 수
  있음 (의도된 단순화, 위 "Redis" 절 참고).
- **k6 테스트는 닫힌 모델**이라 RPS가 아니라 지연시간 비교에만 쓸 수 있음
  (`docs/perf.md` 참고).
