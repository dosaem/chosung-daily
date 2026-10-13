# 티켓 20 구현 증거 — 자동 배포(`deploy.sh` + GitHub Actions/Tailscale)

- 날짜: 2026-10-14
- 브랜치: `dosaem/t20-auto-deploy-actions-tailscale` (로컬 `main` = `491418f` 위로 rebase)
- 환경: macOS (Darwin 25.3.0), Docker 29.8.2, uv / Python 3.12, bash 3.2(시스템)
- 전용 테스트 자원: DB `chosung_daily_test_t20`, Redis DB 8
  (`TEST_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 — 공용 테스트 DB·Redis 는 안 건드렸다)
- 프로덕션 미접촉: NAS 접속·배포·`git push` 없음. 실제 `.env`/`.env.prod*` 미수정.
  시크릿은 이름만 적었고 값은 어디에도 없다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `deploy/deploy.sh` | 신설. `deploy.sh <prod|develop> [--dry-run]` — 대상별 설정 + git pull → compose up --build → `flask db upgrade` → 서비스 기동 확인 → `/health` 200 |
| `.github/workflows/deploy.yml` | 신설. `workflow_run`(CI 성공) → Tailscale → `ssh nas 'bash -s -- <target>' < deploy/deploy.sh` |
| `.github/workflows/ci.yml` | `push.branches: [main]` → `[main, develop]` **한 줄만** 변경 |
| `tests/test_deploy_script.py` | 신설. 스크립트 계약 테스트 16개(dry-run 설정 + 가짜 NAS 명령으로 실제 실행) |
| `tests/test_deploy_workflow.py` | 신설. 워크플로 계약 테스트 11개(트리거·선행 조건·대상 매핑·secret 문서화) |
| `tests/fake_nas_bin/{git,docker,curl,sleep}` + `README.md` | 신설. PATH 앞에 둬서 스크립트를 로컬에서 실제로 끝까지 돌리는 가짜 명령 |
| `docs/RELEASE.md` | "자동 배포" 절 + "GitHub Actions secrets" 표(4개) + "D3. 배포 자동화 — NAS 쪽 사람 작업" 체크리스트 + "### 20." 로컬 검증 기록 |
| `README.md` | "설계 판단" 끝에 `### 20. 배포 스크립트를 ssh 표준입력으로 흘려보내는 이유` |

마이그레이션은 만들지 않았다(인프라 전용 티켓). `./scripts/check_migration_heads.sh`
→ `9ec267465b4e (head)` / `OK: Alembic head 1개` (§5).

## 2. 체크박스별 증거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| `deploy.sh <prod\|develop>` 가 브랜치·디렉터리·env file·프로젝트명을 고른다 | `test_deploy_script.py::test_dry_run_picks_target_settings[prod-…]`·`[develop-…]`, `::test_dry_run_does_not_touch_the_other_instance` + §4.1 dry-run 출력 2개 |
| 포트를 고른다 | **의도적으로 다르게 구현**: 스크립트에 8089/8090 을 적지 않고 `docker compose port app 5000` 으로 실제 발행 포트를 읽는다(이유는 §6). `::test_deploy_uses_the_port_compose_actually_published`(develop→8090) + §4.3 에서 진짜 curl 이 8189/8190 으로 감 |
| `git pull` | `::test_deploy_runs_steps_in_order`(1단계 `git pull --ff-only origin main`), `::test_deploy_fails_when_pull_fails`, `::test_deploy_aborts_when_checkout_is_on_another_branch` + §4.3 의 **진짜 git pull** |
| `compose up -d --build` | `::test_deploy_runs_steps_in_order` 2단계 + §4.2 가짜 docker 호출 기록 |
| app 컨테이너 `flask db upgrade` | `::test_deploy_runs_steps_in_order` 3단계(`exec -T app uv run flask db upgrade`), `::test_deploy_fails_when_migration_fails`(실패 시 `/health` 안 봄) |
| 컨테이너 재기동 확인 | `::test_deploy_fails_when_a_service_is_not_running`(worker 빠지면 중단) + §4.4 에서 실제 compose 가 `ps --services --filter status=running` 로 "running 인 것만" 돌려주는 것 확인 |
| `/health` 200 검사 | `::test_deploy_retries_health_until_it_answers`(2번 실패 후 3번째 성공), `::test_deploy_fails_when_health_never_answers`(10회 뒤 실패, 무한 재시도 없음) + §4.3 진짜 curl 200 `{"status":"ok"}` |
| 두 인자 모두로 dry-run/실행 검증, 절차는 RELEASE.md | §4.1(dry-run 2개) + §4.3(prod·develop 실제 실행) + `docs/RELEASE.md` "### 20." |
| `deploy.yml`: main/develop 푸시, `ci.yml` 성공이 선행 조건 | `test_deploy_workflow.py::test_deploy_waits_for_ci_on_the_two_branches`, `::test_deploy_only_runs_when_ci_succeeded`, `::test_deploy_maps_branch_to_target`, `::test_deploy_checks_out_the_commit_that_passed_ci` |
| Tailscale 접속 후 `ssh nas 'deploy.sh …'` | `::test_deploy_joins_tailnet_before_ssh`(순서), `::test_deploy_pipes_the_script_over_ssh` |
| `ci.yml` 은 develop 추가 외 무수정 | `::test_ci_runs_on_both_deploy_branches`, `::test_ci_still_lints_and_tests_with_service_containers` + §5 의 `git diff` 1줄 |
| secrets 목록(TS auth key, ssh key, host)을 RELEASE.md 표로 | `::test_deploy_secrets_are_documented`(워크플로가 쓰는 secret ⊆ 표), `::test_deploy_secrets_cover_tailscale_ssh_and_host` + `docs/RELEASE.md` "### GitHub Actions secrets" |
| NAS 쪽 사람 작업을 D3 체크리스트로 분리 | `::test_release_doc_has_human_checklist_for_nas_access` + `docs/RELEASE.md` "### D3. 배포 자동화 — NAS 쪽 사람 작업" 6항목 |
| `git push` 안 함 | §5 `git log` 는 로컬 브랜치뿐, 이 레포에 `origin` push 없음. 워크플로도 로컬에서 YAML 로만 검증했다(§6 "검증 못 한 것") |

## 3. TDD (red → green)

테스트를 먼저 쓰고 빨간 걸 확인한 뒤 구현했다.

```
# red 1 — deploy/deploy.sh 가 없는 상태에서 tests/test_deploy_script.py
$ uv run pytest tests/test_deploy_script.py -q
...
FAILED tests/test_deploy_script.py::test_dry_run_picks_target_settings[prod-main-/volume1/docker/chosung-daily-chosung-daily-prod-.env]
FAILED tests/test_deploy_script.py::test_deploy_runs_steps_in_order - Asserti...
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_never_answers
15 failed, 1 passed in 0.17s

# green 1 — deploy/deploy.sh 작성 후
$ uv run pytest tests/test_deploy_script.py -q
................                                                         [100%]
16 passed in 1.75s

# red 2 — .github/workflows/deploy.yml 이 없는 상태에서 tests/test_deploy_workflow.py
$ uv run pytest tests/test_deploy_workflow.py -q
ERROR tests/test_deploy_workflow.py::test_deploy_only_runs_when_ci_succeeded
ERROR tests/test_deploy_workflow.py::test_deploy_pipes_the_script_over_ssh - ...
2 failed, 1 passed, 8 errors in 0.38s

# green 2 — deploy.yml + ci.yml(develop) 작성 후 → 문서 2개만 빨간 상태
$ uv run pytest tests/test_deploy_workflow.py -q
FAILED tests/test_deploy_workflow.py::test_deploy_secrets_are_documented - As...
FAILED tests/test_deploy_workflow.py::test_release_doc_has_human_checklist_for_nas_access
2 failed, 9 passed in 0.05s

# green 3 — RELEASE.md secrets 표 + D3 체크리스트 작성 후
$ uv run pytest tests/test_deploy_workflow.py -q
...........                                                              [100%]
11 passed in 0.02s
```

## 4. 실행 검증

### 4.1 dry-run (아무것도 실행하지 않는다)

```
$ bash deploy/deploy.sh prod --dry-run
== prod 배포: main → /volume1/docker/chosung-daily (chosung-daily-prod / .env)
+ git pull --ff-only origin main
+ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env up -d --build
+ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env exec -T app uv run flask db upgrade
+ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env config --services
+ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env ps --services --filter status=running
+ docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env port app 5000
+ curl -fsS --max-time 5 <APP_PORT 로 만든 /health URL> (최대 10회)
== dry-run 끝 — 실제로 실행한 명령은 없다
exit=0

$ bash deploy/deploy.sh develop --dry-run
== develop 배포: develop → /volume1/docker/chosung-daily-develop (chosung-daily-develop / .env.develop)
+ git pull --ff-only origin develop
+ docker compose -f docker-compose.prod.yml -p chosung-daily-develop --env-file .env.develop up -d --build
+ docker compose -f docker-compose.prod.yml -p chosung-daily-develop --env-file .env.develop exec -T app uv run flask db upgrade
... (조회 3개 생략)
+ curl -fsS --max-time 5 <APP_PORT 로 만든 /health URL> (최대 10회)
== dry-run 끝 — 실제로 실행한 명령은 없다
exit=0

$ bash deploy/deploy.sh staging --dry-run
사용법: deploy.sh <prod|develop> [--dry-run]
exit=2
```

### 4.2 가짜 NAS 명령으로 실제 실행 (pytest)

`tests/fake_nas_bin/` 의 `git`/`docker`/`curl`/`sleep` 을 PATH 앞에 두고 스크립트를
그대로 실행한다. 분기·순서·실패 처리는 전부 진짜로 지나가고, 호출된 명령만 가짜가
기록한다. `sleep` 도 가짜라 재시도 테스트가 느려지지 않는다.

- 단계 순서(`::test_deploy_runs_steps_in_order`): pull → up --build → db upgrade →
  config --services → ps --filter status=running → port app 5000 → curl /health
- 멈추는 지점: 체크아웃 디렉터리 없음 / 브랜치 불일치 / pull 실패 /
  마이그레이션 실패 / 서비스 하나 미기동 / `/health` 10회 무응답 — 각각 exit≠0 이고
  **그 뒤 단계의 명령은 호출되지 않는다**(가짜 호출 기록으로 확인)
- 브랜치 불일치를 진짜 git 으로도 확인:

```
$ git -C <가짜NAS>/chosung-daily checkout -b hotfix-test
$ bash deploy/deploy.sh prod            # DEPLOY_BASE_DIR=<가짜NAS>
== prod 배포: main → <가짜NAS>/chosung-daily (chosung-daily-prod / .env)
<가짜NAS>/chosung-daily 가 main 가 아니라 hotfix-test 에 있다 — 중단
exit=1
docker 호출: 0
```

### 4.3 docker 만 가짜로 두고 끝까지 (진짜 git pull + 진짜 curl)

가짜 NAS 체크아웃 2개(`main`/`develop` clone)와 로컬 Flask(8189·8190)를 띄우고,
`docker` 만 가짜로 둔 상태로 두 인자를 실행했다. rebase 후 다시 돌린 결과다.

```
$ PATH=<가짜docker만>:$PATH DEPLOY_BASE_DIR=<가짜NAS> FAKE_DOCKER_PORT=127.0.0.1:8189 \
    bash deploy/deploy.sh prod
== prod 배포: main → <가짜NAS>/chosung-daily (chosung-daily-prod / .env)
+ git pull --ff-only origin main
From /Users/saem/orca/projects/chosung-daily
 * branch            main       -> FETCH_HEAD
Already up to date.
+ docker compose ... up -d --build
+ docker compose ... exec -T app uv run flask db upgrade
+ docker compose ... config --services
+ docker compose ... ps --services --filter status=running
+ docker compose ... port app 5000
http://127.0.0.1:8189/health → {"status":"ok"}
== prod 배포 완료
prod exit=0

$ ... FAKE_DOCKER_PORT=127.0.0.1:8190 bash deploy/deploy.sh develop
== develop 배포: develop → <가짜NAS>/chosung-daily-develop (chosung-daily-develop / .env.develop)
+ git pull --ff-only origin develop
 * branch            develop    -> FETCH_HEAD
Already up to date.
+ docker compose -f docker-compose.prod.yml -p chosung-daily-develop --env-file .env.develop up -d --build
... 
http://127.0.0.1:8190/health → {"status":"ok"}
== develop 배포 완료
develop exit=0
```

`/health` 는 진짜 curl + 진짜 Flask 응답이다. 같은 URL 을 따로 확인:

```
$ curl -fsS --max-time 5 http://127.0.0.1:8189/health
{"status":"ok"} curl-exit=0
$ curl -o /dev/null -s -w '%{http_code}\n' http://127.0.0.1:8189/health
200
```

### 4.4 compose 조회 명령은 실제 docker 로 확인 (읽기만)

스크립트가 쓰는 조회 3개의 문법·출력 형식은 가짜로는 증명이 안 되므로, 로컬에서
이미 돌고 있는 개발 compose 프로젝트에 **읽기 명령만** 보냈다(`up`/`down` 안 함).
그 프로젝트는 mysql·redis 만 띄워둔 상태라서, 스크립트가 잡아야 하는 "서비스 일부
미기동" 상황이 그대로 재현됐다.

```
$ docker --version
Docker version 29.8.2, build 7fc2dff

$ docker compose -f docker-compose.yml -p chosung-daily config --services
mysql
redis
app
beat
worker

$ docker compose -f docker-compose.yml -p chosung-daily ps --services --filter status=running
mysql
redis
exit=0            # → 스크립트라면 "기동하지 않은 서비스: app beat worker" 로 중단

$ docker compose -f docker-compose.yml -p chosung-daily port mysql 3306
0.0.0.0:3306      # 스크립트의 ${published##*:} → 3306
exit=0

$ docker compose -f docker-compose.yml -p chosung-daily port app 5000
service "app" is not running
exit=1            # port 는 서비스가 떠 있어야 답한다 → 기동 확인을 먼저 하는 순서가 맞다
```

### 4.5 셸 문법

```
$ bash -n deploy/deploy.sh
bash -n deploy/deploy.sh: ok
$ sh -n tests/fake_nas_bin/{git,docker,curl,sleep}
sh -n tests/fake_nas_bin/git: ok
sh -n tests/fake_nas_bin/docker: ok
sh -n tests/fake_nas_bin/curl: ok
sh -n tests/fake_nas_bin/sleep: ok
```

## 5. 전체 테스트·린트·마이그레이션 (로컬 main 위로 rebase 후)

```
$ git rebase main          # main = 491418f (티켓 01 머지), README 충돌 1건 직접 해소
Successfully rebased and updated refs/heads/dosaem/t20-auto-deploy-actions-tailscale.

$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=mysql+pymysql://chosung:chosung@127.0.0.1:3306/chosung_daily_test_t20?charset=utf8mb4 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/8 uv run pytest -q
........................................................................ [ 53%]
...............................................................          [100%]
135 passed in 37.54s

$ FLASK_APP=wsgi.py ./scripts/check_migration_heads.sh
9ec267465b4e (head)
OK: Alembic head 1개

$ git diff 491418f -- .github/workflows/ci.yml
-    branches: [main]
+    branches: [main, develop]

$ git status --short
(clean)
$ git log --oneline main..HEAD
<커밋 3개: deploy.sh / deploy.yml+문서 / 이 증거 파일>
```

rebase 때 `README.md` "설계 판단" 에서 티켓 01 의 `### 01.` 세 절과 내 `### 20.` 이
같은 자리에 들어가 충돌했다 — 공통 규칙대로 둘 다 살리고 `### 20.` 을 섹션 끝으로
보내서 해소했다. 티켓 01 이 켠 새 ruff 규칙(`PL`)에서 `subprocess.run` 의
`check` 인자 누락(PLW1510) 3건이 잡혀서 `check=False` 를 명시했다.

## 6. 설계 판단·검증하지 못한 것 (숨기지 않음)

- **포트를 스크립트에 적지 않았다.** 티켓 체크박스는 "포트를 고른다" 지만,
  `docker compose port app 5000` 으로 실제 발행된 포트를 읽는다. 포트의 진실은 env
  파일의 `APP_PORT` 라서 스크립트에 8089/8090 을 또 적으면 둘이 갈라진다. 이유는
  커밋 메시지와 README "설계 판단" §20 에 적었다.
- **워크플로는 실제로 돌려보지 못했다.** `git push` 가 금지돼 있고 secrets 도
  없다 — YAML 계약 테스트 11개와 눈으로 본 것뿐이다. 러너→tailnet→NAS ssh 경로는
  `docs/RELEASE.md` D3 체크리스트의 사람 작업이고, 첫 리허설은 prod 가 아니라
  `develop` 푸시로 하도록 체크리스트에 적었다.
- **`actionlint`·`shellcheck` 미설치**: 둘 다 로컬에 없어서 못 돌렸다
  (`command -v actionlint` → 없음). 대신 `bash -n`/`sh -n` 과 YAML 파싱
  (`yaml.safe_load`, 계약 테스트)로 대체했다.
- **`ssh -o StrictHostKeyChecking=accept-new`**: 첫 접속에서 NAS 호스트 키를 그대로
  받는다. tailnet 안에서만 닿는 주소라 중간자 가능성이 낮다고 보고 known_hosts
  secret 을 하나 더 두지 않았다 — 더 엄격하게 가려면 `NAS_SSH_KNOWN_HOSTS` 를
  추가하는 게 다음 단계다.
- **`ruff format` 은 이 티켓에서 돌리지 않았다.** CI 는 `ruff check` 만 쓰고,
  `ruff format --check .` 은 내 변경과 무관한 기존 파일 8개에서도 깨진다
  (`app/models/account.py` 등). 내가 추가한 파일 2개는 `--check` 를 통과한다.
- Celery/앱 코드·마이그레이션·UI 는 건드리지 않았다(인프라 전용 티켓).
