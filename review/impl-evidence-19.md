# 티켓 19 구현 증거 — compose 파라미터화·develop 인스턴스 동시 기동

- 날짜: 2026-10-13
- 브랜치: `dosaem/t19-compose-parametrize-develop-instance`
- 환경: macOS (Darwin 25.3.0), Docker 29.8.2, uv / Python 3.12.14
- 전용 테스트 자원: DB `chosung_daily_test_t19`, Redis DB 7
  (`TEST_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 — 공용 테스트 DB·Redis 는 안 건드렸다)

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `docker-compose.prod.yml` | 최상위 `name:` 제거, 5개 서비스의 `container_name` 제거, 호스트 포트 `${APP_PORT}`, `env_file: ${ENV_FILE:-.env}`, 헤더 주석에 prod/develop 실행법 |
| `.dockerignore` | 신설. `mobile/`·`.scratch/`·`review/`·`.venv/`·`tests/`·`docs/`·`k6/`·`.git/`·`.env*` 등 제외 |
| `.env.prod.example` | `COMPOSE_PROJECT_NAME=chosung-daily-prod`·`APP_PORT=8089`·`ENV_FILE=.env` 추가 |
| `.env.develop.example` | 신설. `chosung-daily-develop`·8090·`ENV_FILE=.env.develop` |
| `docs/RELEASE.md` | 신설. 인스턴스 구성표, prod/develop 첫 배포 체크리스트, 티켓 19 로컬 검증 기록 |
| `README.md` | "설계 판단" 에 `### 19. prod 프로젝트명 유지 이유` 추가 |
| `tests/test_compose_config.py` | 신설. compose/env 예시/`.dockerignore` 계약 테스트 8개 |
| `pyproject.toml`, `uv.lock` | 위 테스트가 compose YAML 을 파싱하므로 dev 그룹에 `pyyaml` 추가 |

마이그레이션은 만들지 않았다(인프라 전용 티켓). `flask db heads` → `9ec267465b4e (head)` 1줄.

## 2. 체크박스별 증거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| `docker-compose.prod.yml` 고정 `container_name`·`name:` 제거 | `tests/test_compose_config.py::test_prod_compose_has_no_fixed_project_name`, `::test_prod_compose_has_no_fixed_container_names` (§3 red→green) + 검증 ① 에서 컨테이너 이름이 `chosung-daily-prod-app-1` 식 compose 기본 네이밍으로 바뀜 (§4.1 4단계) |
| 호스트 포트 `${APP_PORT}` | `::test_app_host_port_is_parametrized` + 실제 기동에서 prod 8089 / develop 8090 (§4.2 2단계) |
| env file 환경별 | `::test_env_file_is_parametrized` + 각 app 컨테이너의 `COMPOSE_PROJECT_NAME` 이 자기 env 파일 값 (§4.3) |
| 볼륨은 compose 프로젝트 기본 네이밍 | `::test_volumes_use_compose_project_naming` + 검증 ① 에서 볼륨 이름 `chosung-daily-prod_mysql-data`/`_redis-data` 동일 (§4.1) |
| 예시 파일: `.env.prod.example` 유지 + `.env.develop.example` 신설, 둘 다 `COMPOSE_PROJECT_NAME`·`APP_PORT` (미정 16) | `::test_env_examples_pin_project_and_port[...]` 2케이스 + §4.3 의 "`-p`·`--env-file` 둘 다 생략" 확인 |
| 실제 `.env`·`.env.prod` 류 미수정, 검증은 예시 파일 임시 복사본 | `git status` 에 `.env*` 실파일 없음(§6). 검증용 env 는 scratchpad 의 `env.prod.local`/`env.develop.local` (예시 파일을 `sed` 로 더미 채운 복사본), 베이스라인용 임시 `.env` 는 검증 후 삭제 — §4.1 1단계·§4.3 |
| `.dockerignore` 신설 (22 의 Flutter 디렉터리 차단) | `::test_dockerignore_excludes_non_backend_paths` + 이미지 안에 `.scratch`/`tests`/`docs`/`k6`/`.github` 없음 (§4.3) |
| 로컬 검증 ①: 볼륨 재부착·기록·토큰 유지, 절차를 `docs/RELEASE.md` 에 기록 | §4.1 + `docs/RELEASE.md` "### 19." |
| 로컬 검증 ②: 동시 기동·이름/포트/볼륨 분리·쓰기 격리 | §4.2 |
| `docs/RELEASE.md` 신설 (프로젝트명/볼륨명 확인, develop 디렉터리, named volume 필수) | `docs/RELEASE.md` — "첫 배포 체크리스트 (prod)" 첫 항목, 인스턴스 구성표, "DB 는 named volume 만" 문단 |
| README "설계 판단" 에 prod 프로젝트명 유지 이유 | `README.md` `### 19. prod 프로젝트명 유지 이유 (compose 파라미터화)` |

## 3. TDD (red → green)

테스트를 먼저 쓰고 돌렸다 — 8개 중 7개 실패(볼륨 네이밍만 이미 통과).

```
$ uv run pytest tests/test_compose_config.py -v
FAILED tests/test_compose_config.py::test_prod_compose_has_no_fixed_project_name
FAILED tests/test_compose_config.py::test_prod_compose_has_no_fixed_container_names
FAILED tests/test_compose_config.py::test_app_host_port_is_parametrized - Ass...
FAILED tests/test_compose_config.py::test_env_file_is_parametrized - Assertio...
FAILED tests/test_compose_config.py::test_env_examples_pin_project_and_port[.env.prod.example-chosung-daily-prod-8089]
FAILED tests/test_compose_config.py::test_env_examples_pin_project_and_port[.env.develop.example-chosung-daily-develop-8090]
FAILED tests/test_compose_config.py::test_dockerignore_excludes_non_backend_paths
========================= 7 failed, 1 passed in 0.24s ==========================
```

구현 후:

```
$ uv run pytest tests/test_compose_config.py -q
........                                                                 [100%]
8 passed in 0.02s
```

이 테스트는 도커를 띄우지 않는다(설정 파일 계약만 본다). 실제 기동·볼륨 재부착은
아래 §4 의 도커 명령으로 검증했고, 사람이 다시 돌릴 절차는 `docs/RELEASE.md`.

## 4. 실제 도커 검증

실제 `.env`·`.env.prod` 는 건드리지 않았다. 검증용 env 는 예시 파일을 scratchpad 로
복사해 빈 값만 더미로 채운 것이고(시크릿 값은 어디에도 기록하지 않는다), 변경 전
compose 는 `env_file: .env` 가 고정이라 베이스라인 동안만 더미 `.env` 를 레포에
두고 검증 직후 지웠다.

### 4.1 검증 ① — 기존 볼륨 재부착, 기록·토큰 유지

1단계. 변경 전 compose 로 기동

```
$ git show HEAD:docker-compose.prod.yml > docker-compose.prod.baseline.yml
$ docker compose -f docker-compose.prod.baseline.yml up -d --build
 Container chosung-daily-app-prod Started
 Container chosung-daily-worker-prod Started
 Container chosung-daily-beat-prod Started

$ docker compose -f docker-compose.prod.baseline.yml ps --format '{{.Name}}\t{{.Service}}\t{{.Ports}}'
chosung-daily-app-prod	app	127.0.0.1:8089->5000/tcp
chosung-daily-beat-prod	beat	5000/tcp
chosung-daily-mysql-prod	mysql	3306/tcp, 33060/tcp
chosung-daily-redis-prod	redis	6379/tcp
chosung-daily-worker-prod	worker	5000/tcp

$ docker volume ls --filter label=com.docker.compose.project=chosung-daily-prod --format '{{.Name}}'
chosung-daily-prod_mysql-data
chosung-daily-prod_redis-data

$ curl -sS http://127.0.0.1:8089/health
{"status":"ok"}
```

2단계. 기록·토큰 만들기

```
$ ... exec -T app uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade e759d7e8d071 -> 9ec267465b4e, replace kakao with apple as oauth provider
$ ... exec -T app uv run flask seed-words data/seed_words.csv
20개 단어 시드 완료
$ ... exec -T app uv run flask schedule-puzzles --days 2
2일치 퍼즐 배정 완료 (이미 있던 날짜는 건너뜀)

$ TOKEN=$(curl -sS -X POST http://127.0.0.1:8089/api/v1/guests | jq -r .token)   # 36자
$ curl -sS -X POST http://127.0.0.1:8089/api/v1/puzzles/today/guesses \
    -H "Authorization: Bearer $TOKEN" -d '{"guess":"포도"}'
{"answer":null,"attempts_left":4,"feedback":[false,false],"hint":null,"is_correct":false}

$ ... exec -T redis redis-cli dbsize
5
$ ... exec -T redis redis-cli save
OK
```

3단계. `down`(**`-v` 없이**) → 새 compose 로 다시 `up`

```
$ docker compose -f docker-compose.prod.baseline.yml down
 Network chosung-daily-prod_default Removed
$ docker volume ls --filter label=com.docker.compose.project=chosung-daily-prod --format '{{.Name}}'
chosung-daily-prod_mysql-data
chosung-daily-prod_redis-data      ← down 해도 볼륨은 남는다

# 베이스라인용 임시 파일 제거 (.env, docker-compose.prod.baseline.yml)
$ docker compose -f docker-compose.prod.yml -p chosung-daily-prod \
    --env-file <scratchpad>/env.prod.local up -d --build
 Container chosung-daily-prod-app-1 Started
```

4단계. 결과 — 볼륨 이름 동일, 컨테이너 이름만 compose 기본 네이밍

```
$ docker compose -p chosung-daily-prod ps --format '{{.Name}}\t{{.Service}}\t{{.Ports}}'
chosung-daily-prod-app-1	app	127.0.0.1:8089->5000/tcp
chosung-daily-prod-beat-1	beat	5000/tcp
chosung-daily-prod-mysql-1	mysql	3306/tcp, 33060/tcp
chosung-daily-prod-redis-1	redis	6379/tcp
chosung-daily-prod-worker-1	worker	5000/tcp

$ docker volume ls --filter label=com.docker.compose.project=chosung-daily-prod --format '{{.Name}}'
chosung-daily-prod_mysql-data        ← 검증 ① 1단계와 동일
chosung-daily-prod_redis-data        ← 동일

$ curl -sS http://127.0.0.1:8089/health
{"status":"ok"}

# 2단계에서 받은 그 토큰 그대로
$ curl -sS http://127.0.0.1:8089/api/v1/puzzles/today -H "Authorization: Bearer $TOKEN"
{"answer":null,"attempts_left":4,"category":"general","chosung":"ㅎㄱ","date":"2026-10-13",
 "hint":null,"length":2,"status":"in_progress"}        ← 토큰 유효 + 시도 1회 소비 상태 유지

$ docker compose -p chosung-daily-prod exec -T mysql mysql -uchosung -p*** chosung_daily -N \
    -e "select 'word',count(*) from word union all select 'guest',count(*) from guest
        union all select 'attempt',count(*) from attempt
        union all select 'daily_puzzle',count(*) from daily_puzzle;"
word	20
guest	1
attempt	1
daily_puzzle	2
```

### 4.2 검증 ② — prod·develop 동시 기동과 분리

1단계. prod 를 띄운 채로 develop 추가

```
$ docker compose -f docker-compose.prod.yml -p chosung-daily-develop \
    --env-file <scratchpad>/env.develop.local up -d --build
 Container chosung-daily-develop-app-1 Started
```

2단계. 컨테이너 이름·포트·볼륨 분리

```
$ docker ps --filter label=com.docker.compose.project=chosung-daily-prod --format '{{.Names}}\t{{.Ports}}'
$ docker ps --filter label=com.docker.compose.project=chosung-daily-develop --format '{{.Names}}\t{{.Ports}}'
chosung-daily-develop-app-1	127.0.0.1:8090->5000/tcp
chosung-daily-develop-beat-1	5000/tcp
chosung-daily-develop-mysql-1	3306/tcp, 33060/tcp
chosung-daily-develop-redis-1	6379/tcp
chosung-daily-develop-worker-1	5000/tcp
chosung-daily-prod-app-1	127.0.0.1:8089->5000/tcp
chosung-daily-prod-beat-1	5000/tcp
chosung-daily-prod-mysql-1	3306/tcp, 33060/tcp
chosung-daily-prod-redis-1	6379/tcp
chosung-daily-prod-worker-1	5000/tcp

$ docker volume ls --format '{{.Name}}' | grep '^chosung' | sort
chosung-daily_mysql_data              ← 로컬 개발용(다른 워커가 쓰는 것). 안 건드림
chosung-daily-develop_mysql-data
chosung-daily-develop_redis-data
chosung-daily-prod_mysql-data
chosung-daily-prod_redis-data

$ curl -sS http://127.0.0.1:8090/health
{"status":"ok"}
```

3단계. 한쪽 쓰기가 다른 쪽에 안 보인다

```
$ # develop 에서 오답 2회 제출 후
$ curl -sS -w ' [http %{http_code}]' http://127.0.0.1:8090/api/v1/puzzles/today -H "Authorization: Bearer $DEV_TOKEN"
{"answer":null,"attempts_left":3,"category":"general","chosung":"ㅈㄴ","date":"2026-10-13",...} [http 200]

$ curl -sS -w ' [http %{http_code}]' http://127.0.0.1:8089/api/v1/puzzles/today -H "Authorization: Bearer $DEV_TOKEN"
{"code":"UNAUTHORIZED","message":"유효하지 않은 토큰입니다."} [http 401]

$ curl -sS -w ' [http %{http_code}]' http://127.0.0.1:8089/api/v1/puzzles/today -H "Authorization: Bearer $PROD_TOKEN"
{"answer":null,"attempts_left":4,"category":"general","chosung":"ㅎㄱ",...} [http 200]

$ curl -sS -w ' [http %{http_code}]' http://127.0.0.1:8090/api/v1/puzzles/today -H "Authorization: Bearer $PROD_TOKEN"
{"code":"UNAUTHORIZED","message":"유효하지 않은 토큰입니다."} [http 401]

prod   : guest=1 attempt=1      ← develop 에서 2회 제출해도 prod 는 1
develop: guest=1 attempt=2
```

같은 날 퍼즐 초성도 달랐다(prod ㅎㄱ / develop ㅈㄴ) — 배정이 인스턴스별로 독립이다.

### 4.3 `COMPOSE_PROJECT_NAME` 안전장치(미정 16), `ENV_FILE` 라우팅, `.dockerignore`

```
--- NAS prod 실제 시나리오: 디렉터리에 .env 만 두고 -p·--env-file 둘 다 생략 (미정 16) ---
project = chosung-daily-prod | app published port = 8089

--- ENV_FILE 라우팅: 각 인스턴스 컨테이너가 자기 env 파일을 읽었다 ---
  (COMPOSE_PROJECT_NAME 은 compose 가 컨테이너에 주입하지 않는 값 — env_file 로만 들어온다)
  prod    app 컨테이너: chosung-daily-prod
  develop app 컨테이너: chosung-daily-develop

--- .dockerignore 효과: 레포에는 있지만 이미지 /srv 에는 없는 디렉터리 ---
  .scratch    repo:있음  image:없음
  tests       repo:있음  image:없음
  docs        repo:있음  image:없음
  k6          repo:있음  image:없음
  .github     repo:있음  image:없음
```

`--env-file` 만 준 경우도 같이 확인했다 (`docker compose -f docker-compose.prod.yml
--env-file <env> config`): prod → `chosung-daily-prod`/8089, develop →
`chosung-daily-develop`/8090.

주의: 이미지 안에 `/srv/.venv` 는 있다. 컨테이너 `CMD` 의 `uv run` 이 런타임에
만드는 것이고, 호스트 `.venv` 가 복사된 게 아니다(`.dockerignore` 에 `.venv/` 있음).
`mobile/` 은 티켓 22 가 만들 디렉터리라 아직 레포에 없다 — 테스트가
`.dockerignore` 항목 존재를 검증해서 22 머지 시점에 바로 적용된다.

### 4.4 정리

```
$ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file <...> down -v
 Volume chosung-daily-prod_redis-data Removed
 Volume chosung-daily-prod_mysql-data Removed
$ docker compose -f docker-compose.prod.yml -p chosung-daily-develop --env-file <...> down -v
 Volume chosung-daily-develop_redis-data Removed
 Volume chosung-daily-develop_mysql-data Removed

$ docker volume ls --format '{{.Name}}' | grep '^chosung'
chosung-daily_mysql_data            ← 공용 개발 볼륨은 그대로
$ docker ps --format '{{.Names}}' | grep chosung
chosung-daily-redis-1               ← 다른 워커가 쓰는 컨테이너도 그대로
chosung-daily-mysql-1
```

## 5. 전체 테스트·린트

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=mysql+pymysql://chosung:***@127.0.0.1:3306/chosung_daily_test_t19?charset=utf8mb4 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/7 \
  uv run pytest -q
........................................................................ [ 84%]
.............                                                            [100%]
85 passed in 44.91s

$ uv run flask db heads
9ec267465b4e (head)
```

로컬 `main` 위로 rebase 한 뒤 위 두 명령을 다시 돌렸다 — §7 참고.

## 6. 안 한 것 / 남은 것

- **NAS 실행은 안 했다.** 프로덕션 접속·배포 금지라, NAS 쪽 실제 프로젝트명·볼륨명
  확인과 `up` 은 `docs/RELEASE.md` 사람 체크리스트로 남겼다(스펙 D3).
- **스펙 `미정 8`(develop 포트 8090)** 은 NAS 실측이 필요한 사람 항목이라 그대로
  두고, 예시 파일·`docs/RELEASE.md` 에 "NAS 실측으로 확정" 주석만 달았다.
- **스펙 `미정 항목` 파일은 수정하지 않았다.** 16 번(`COMPOSE_PROJECT_NAME` 안전장치)은
  코드·예시 파일·README 에 반영했지만, 티켓이 스펙에 결과를 적으라고 명시하지
  않았고 `.scratch/` 수정은 명시적 지시가 있을 때만 하기로 돼 있어서 건드리지 않았다.
- `deploy/deploy.sh`(티켓 27)·백업(28)은 이 티켓 범위 밖이라 손대지 않았다.
- 실패한 테스트·건너뛴 검증 없음.

## 7. rebase 후 재실행

로컬 `main`(`285c804`)은 작업 중 움직이지 않아서 rebase 가 fast-forward 없이 끝났다.

```
$ git rebase main
Current branch dosaem/t19-compose-parametrize-develop-instance is up to date.

$ git log --oneline main..HEAD
57d590c docs/RELEASE.md 신설 + README "설계 판단"에 prod 프로젝트명 유지 이유
49a4a91 compose 파라미터화: prod/develop 두 인스턴스가 한 NAS에서 동시에 돈다
```

rebase 후 재실행:

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=... TEST_REDIS_URL=redis://127.0.0.1:6379/7 uv run pytest -q
........................................................................ [ 84%]
.............                                                            [100%]
85 passed in 45.00s
```
