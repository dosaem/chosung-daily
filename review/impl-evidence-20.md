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

## 수정 라운드 1

최종 리뷰(`review/impl-review-20.md` 라운드 1, FAIL — MAJOR 2 / MINOR 1)의 결함을
고쳤다. 각 결함을 **리뷰에 적힌 재현 방법 그대로 먼저 재현**하고, 그 재현을 실패하는
테스트로 고정한 뒤에 고쳤다. 테스트 자원은 이 티켓 전용(`chosung_daily_test_t20`,
Redis DB 8)을 썼다. NAS 접속·배포·`git push`·외부 서비스 호출은 없다.

### D-20-1 (MAJOR) — CI 통과 커밋과 NAS 빌드 커밋이 연결되지 않음

**원인.** 워크플로가 NAS 에 넘기는 건 대상 하나(`bash -s -- prod`)뿐이었다. 러너의
`actions/checkout` 을 `workflow_run.head_sha` 로 맞춘 건 *러너가 읽어서 ssh 로
흘려보내는 `deploy.sh`* 만 그 커밋으로 고정한다. 정작 빌드 소스는 NAS 의
`git pull --ff-only origin main` 이 가져오는 "지금의 브랜치 끝" 이라, A 의 CI 성공으로
시작한 배포가 그 사이 올라온 B(아직 CI 중이거나 CI 가 실패한 커밋)를 빌드했다.
즉 "CI 통과 선행" 조건이 실질적으로 우회됐다.

**재현(수정 전).** 리뷰대로 임시 로컬 origin 에 A 를 커밋 → 가짜 NAS 디렉터리로
clone → origin 에 B 를 추가 → 가짜 `docker`/`curl`/`sleep` 만 PATH 앞에 두고(**git 은
진짜**) `bash deploy/deploy.sh prod` 실행:

```
A=6010aa840c45651f41668e2dea7a04b8c060f851
B=c5c3a535859c9fdd0b566691498a27472edf8667
deploy exit=0
NAS 작업 디렉터리 HEAD = c5c3a535859c9fdd0b566691498a27472edf8667
빌드된 version 파일 = B
```

**수정.**
- `.github/workflows/deploy.yml`: job env 에 `CI_SHA: ${{ github.event.workflow_run.head_sha }}`
  를 두고 ssh 로 `bash -s -- $TARGET $CI_SHA` 를 넘긴다.
- `deploy/deploy.sh`: 2번째 인자로 sha 를 받는다(`deploy.sh <prod|develop> [<sha>]
  [--dry-run]`, 순서 무관, sha 모양이 아니면 exit 2). `git pull` 을
  `git fetch` + `git merge --ff-only origin/<branch>` 로 쪼개고, fetch 직후
  `git rev-parse origin/<branch>` 가 받은 sha 와 다르면 **아무것도 빌드하지 않고
  중단**한다. merge 뒤에는 `git rev-parse HEAD` == sha 를 한 번 더 확인한다.
- "브랜치가 움직였어도 받은 sha 를 그대로 빌드" 는 일부러 택하지 않았다. B 가 이미
  올라간 뒤에 A 의 배포가 끝나면 운영이 조용히 옛 커밋으로 되돌아간다. 중단하면
  B 는 자기 CI 통과 후 자기 배포로 올라간다. 이유는 README "설계 판단" §20 에 적었다.
- sha 없이 돌리는 경로(NAS 에서 사람이 손으로)는 그대로 브랜치 끝을 올린다.

**증명.** 같은 재현을 수정 후 스크립트로:

```
=== D-20-1 재현 (수정 후): A 의 sha 로 배포, origin 은 B → 중단해야 한다 ===
+ git fetch --quiet origin main
origin/main 가 이미 d518f2b33d30744c5bc9f34e2429531c366342a9 로 움직였다 — CI 를 통과한 d2754a4edf937ff5dcc3b7f1ca0b6743f896b20f 의
배포를 중단한다. d518f2b33d30744c5bc9f34e2429531c366342a9 는 자기 CI 가 통과하면 배포된다.
작업 트리 version = A (A 그대로여야 한다)
docker 호출: 0 번
D-20-1 (옛 sha) exit=1  (기대: 1)
D-20-1 (브랜치 끝 sha) exit=0  (기대: 0)   # 작업 트리 version = B
```

고정한 테스트(`tests/test_deploy_script.py`) — 전부 **진짜 git + 임시 origin**:
`test_deploy_refuses_a_commit_that_is_no_longer_the_branch_tip`(옛 sha → exit≠0,
`docker` 호출 0, 작업 트리 그대로), `test_deploy_builds_exactly_the_commit_that_passed_ci`
(브랜치 끝 sha → 체크아웃 HEAD 가 정확히 그 sha), `test_deploy_refuses_a_commit_from_another_branch`
(develop 커밋을 prod 로 → 중단), `test_deploy_without_a_commit_takes_the_branch_tip`
(사람이 손으로 돌리는 경로 유지). 워크플로 쪽은
`tests/test_deploy_workflow.py::test_deploy_pins_the_nas_build_to_the_ci_commit`
이 `bash -s -- $TARGET $CI_SHA` 순서까지 본다.

### D-20-2 (MAJOR) — `/health` 가 200 이 아니어도 성공 처리

**원인.** `curl -fsS` 의 종료 코드만 봤다. `-f` 는 4xx·5xx 에서만 실패하고 3xx 는
0 으로 끝나기 때문에, `/health` 가 로그인으로 302 리다이렉트되는 설정 사고가
그대로 통과했다. 상태 코드를 비교하는 곳이 없었다.

**재현(수정 전).** 루프백 `http.server` 가 모든 GET 에 `302 + Location: /login` 을
주게 하고, 가짜 docker 의 `FAKE_DOCKER_PORT` 를 그 주소로 두고 **진짜 curl** 로:

```
+ docker compose ... port app 5000
http://127.0.0.1:57562/health →
== prod 배포 완료
deploy exit=0
```

(같은 서버에 직접 쏜 결과: `curl -fsS` exit=0 / `-w '%{http_code}'` → `302`.)

**수정.** `deploy/deploy.sh` 의 health 루프를
`curl -sS --max-time 5 -w '\n%{http_code}'` 로 바꾸고 본문과 상태 코드를 쪼개서
`status == 200` 일 때만 성공으로 끝낸다. 연결 자체가 안 되면 curl 이 `-w` 자리에
`000` 을 찍으므로 같은 비교로 처리된다(재시도 10회·3초 간격은 그대로).
가짜 curl(`tests/fake_nas_bin/curl`)도 실제 curl 처럼 "본문 + 개행 + 상태 코드" 를
찍게 고치고 `FAKE_CURL_STATUS` 를 추가했다.

**증명.** 같은 302 서버로 수정 후:

```
(10/10) http://127.0.0.1:60184/health → HTTP 302 (200 아님)
http://127.0.0.1:60184/health 가 10회 재시도 뒤에도 200 을 주지 않는다 — 배포 실패
D-20-2 (302) exit=1  (기대: 1)
```

고정한 테스트: `test_deploy_fails_when_health_redirects_instead_of_200`(진짜 curl +
302 루프백 서버 → exit≠0, "배포 완료" 없음), `test_deploy_succeeds_when_health_returns_200`
(같은 경로에 200 → exit 0, 항상 실패하는 검사가 아님을 증명),
`test_deploy_fails_when_health_status_is_not_200[301/302/404/500]`(상태별 판정 +
재시도 10회).

### 새 테스트를 수정 전 코드에 돌린 결과 (red 확인)

`deploy/deploy.sh` 와 `.github/workflows/deploy.yml` 만 `git show HEAD:` 로 되돌려
새 테스트를 그대로 돌렸다(그 뒤 원복):

```
FAILED tests/test_deploy_script.py::test_deploy_refuses_a_commit_that_is_no_longer_the_branch_tip
FAILED tests/test_deploy_script.py::test_deploy_refuses_a_commit_from_another_branch
FAILED tests/test_deploy_script.py::test_unknown_third_argument_fails_with_usage
FAILED tests/test_deploy_script.py::test_dry_run_with_a_commit_runs_nothing
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_redirects_instead_of_200
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_status_is_not_200[301]
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_status_is_not_200[302]
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_status_is_not_200[404]
FAILED tests/test_deploy_script.py::test_deploy_fails_when_health_status_is_not_200[500]
FAILED tests/test_deploy_workflow.py::test_deploy_pins_the_nas_build_to_the_ci_commit
10 failed, 3 passed, 28 deselected in 2.33s
```

통과한 3개는 일부러 넣은 비회귀 가드다 —
`test_deploy_builds_exactly_the_commit_that_passed_ci`,
`test_deploy_without_a_commit_takes_the_branch_tip`,
`test_deploy_succeeds_when_health_returns_200`(새 검사가 "항상 실패" 가 아님을 증명).
원복 후 41개 전부 통과.

### D-20-3 (MINOR) — RELEASE.md 공유 파일 번호별 추가 규칙 위반

**원인.** 티켓 공통 규칙은 공유 파일에 `### NN.` 자기 절만 섹션 끝에 덧붙이는
것인데, `## 티켓별 기록` 앞에 번호 없는 `## 자동 배포` / `### GitHub Actions secrets`
/ `### D3. 배포 자동화` 블록을 끼워 넣었다.

**수정.** 세 블록을 그대로(내용 유지) 티켓 20 소유 절 아래로 옮겼다.
`### 20.` 을 `### 20. 자동 배포 (deploy.sh + GitHub Actions)` 로 고치고 그 안에
`#### 무엇이 어떻게 도는가` / `#### GitHub Actions secrets` /
`#### D3. 배포 자동화 — NAS 쪽 사람 작업` / `#### deploy.sh 로컬 검증` 로 넣었다.
번호 없는 소제목은 이제 없다.

**증명.** `grep -n '^#' docs/RELEASE.md` 에서 `## 티켓별 기록` 뒤로 `### 19.`,
`### 20.` 만 있고 그 아래는 전부 `####`. secrets 표·D3 체크리스트를 읽는 기존
테스트(`test_deploy_secrets_are_documented`,
`test_release_doc_has_human_checklist_for_nas_access`)도 그대로 통과한다.

### 리뷰가 지적한 그 외 사항

- **`git diff --check` trailing whitespace** (리뷰에서 결함 미집계): 이 문서 164행의
  공백을 지웠다. 이제 `git diff --check` exit 0.
- 리뷰가 "결함 아님" 으로 본 포트 조회 구현은 그대로 뒀다.
- 미수정 MINOR: 없다.
- 틀렸다고 판단해 고치지 않은 지적: 없다.

### 수정 라운드 1 전체 검증

`git rebase main` **후** 로컬 main 위에서 돌렸다. 리뷰 때의 main(`491418f`)과 달리
이번 rebase 로 티켓 02(언어·마스크)가 들어와서 테스트 수가 늘었다 — 이 티켓 변경과
무관한 증가다.

```
$ git rebase main               # 로컬 main (origin/main 아님), 충돌 없음
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL="mysql+pymysql://chosung:***@127.0.0.1:3306/chosung_daily_test_t20?charset=utf8mb4" \
  TEST_REDIS_URL="redis://127.0.0.1:6379/8" uv run pytest -q
187 passed in 73.54s

$ bash -n deploy/deploy.sh      # exit 0
$ uv run flask db heads
4e72a4045fbc (head)             # 1줄 (이 티켓은 마이그레이션 추가 없음, 티켓 02 의 head)
$ git diff --check              # exit 0
$ git status --short            # 비어 있음 (clean)
```

이 티켓이 추가한 테스트는 14개다(커밋 고정 4 · 인자 검사 2 · `/health` 상태 판정 6 ·
워크플로 sha 전달 1 · fetch/merge 실패 분기 파라미터화 +1). rebase 전 main(`491418f`)
기준으로는 135 → 149 였고, rebase 후 티켓 02 의 테스트까지 합쳐 187 이다.

rebase 로 들어온 `tests/test_migrations.py` 는 별도 DB 를 요구해서(README "실행 방법")
이 티켓 전용 이름으로 한 번 만들었다 — `chosung_daily_test_t20_migrations`
(로컬 개발 compose 의 mysql, README 에 적힌 그 명령). 공용 테스트 DB
(`chosung_daily_test`)와 다른 티켓의 DB 는 건드리지 않았다.

도커를 띄우지 않았고 실제 NAS·GitHub Actions·Tailscale 연결은 여전히
`docs/RELEASE.md` D3 체크리스트의 사람 작업이다.

## 수정 라운드 2

리뷰 라운드 2(`review/impl-review-20.md` "## 라운드 2")의 열린 결함 2건을 고쳤다.
MAJOR 1(D-20-4) · MINOR 1(D-20-5). 미수정 MINOR 는 없다. 리뷰어 지적이 틀렸다고
본 항목도 없다 — 두 건 다 리뷰의 재현 방법 그대로 재현됐다.

### D-20-4 (MAJOR) — `compose exec -T` 가 SSH 로 넘긴 스크립트 뒷부분을 먹음

**원인.** bash 는 표준입력에서 읽는 스크립트를 "읽으면서 실행" 한다. 그 표준입력은
자식 프로세스에 그대로 물려지고, `docker compose exec -T` 는 `-T` 로 TTY 만 끄고
표준입력은 컨테이너로 흘려보낸다. 그래서 `flask db upgrade` 한 줄이 **bash 가 아직
안 읽은 스크립트 뒷부분**(서비스 기동 확인 + `/health` 루프)을 통째로 소비하고,
bash 는 읽을 게 없어진 자리에서 **조용히 exit 0** 한다. 워크플로의 실제 진입 경로가
`ssh nas 'bash -s -- prod <sha>' < deploy/deploy.sh` 라서 운영에서 늘 이 경로다.

bash 자체 동작으로 먼저 최소 재현했다(배포 스크립트와 무관하게 성립한다):

```text
$ cat s.sh
echo one
cat > /dev/null
echo two
echo three

$ bash s.sh < /dev/null        # 파일 인자
one
two
three
$ bash -s < s.sh; echo "exit=$?"   # 표준입력
one
exit=0
```

`two`/`three` 가 사라지고 종료 코드는 0 이다 — 결함의 모양과 정확히 같다.

**리뷰의 재현 그대로(진짜 docker).** 리뷰 §D-20-4 의 스크립트를 그대로 돌렸다
(`exec -T app` 만 이미 돌고 있는 로컬 개발 Redis 컨테이너의 `sleep 0.2` 로 바꿔치고
나머지는 가짜 NAS 명령 — 실제 배포·DB 변경 없음):

```text
수정 전
file  exit 0 health called True  completed True
stdin exit 0 health called False completed False

수정 후
file  exit 0 health called True  completed True
stdin exit 0 health called True  completed True
```

**고치기 전에 테스트로 고정.** 두 군데를 바꿔 결함을 테스트로 묶었다.

1. `tests/fake_nas_bin/docker` — 진짜처럼 `exec -T` 에서 stdin 을 끝까지 읽는다
   (`cat > /dev/null`). 리뷰가 지적한 "가짜 docker 는 stdin 을 소비하지 않아서
   결함을 놓친다" 는 공백을 메운다. 부르는 쪽이 stdin 을 반드시 닫거나 넘기도록
   `FakeNas.deploy()` 와 `run_dry()` 에 `stdin=subprocess.DEVNULL` 을 넣고
   `tests/fake_nas_bin/README.md` 에 적었다.
2. `FakeNas.deploy_via_stdin()` — 워크플로와 같은 `bash -s -- <args>` + 스크립트를
   표준입력으로. 새 테스트 4개가 이 경로를 쓴다.

red (수정 전, `tests/test_deploy_script.py -k stdin`):

```text
FAILED tests/test_deploy_script.py::test_deploy_via_stdin_runs_the_same_steps_as_a_file
FAILED tests/test_deploy_script.py::test_deploy_via_stdin_still_checks_health
FAILED tests/test_deploy_script.py::test_deploy_via_stdin_fails_when_health_is_not_200
FAILED tests/test_deploy_script.py::test_deploy_via_stdin_fails_when_a_service_is_not_running
4 failed, 29 deselected in 2.12s
```

실패 출력의 마지막 줄이 `... exec -T app uv run flask db upgrade` 이고 종료 코드가
0 이다 — 리뷰가 적은 증상과 같다.

**수정 내용.** `deploy/deploy.sh` 본문 전체를 `main()` 안으로 넣고 파일 맨 끝에서
`main "$@" < /dev/null` 로 부른다. 어떤 자식도 스크립트 본문을 표준입력으로
물려받지 않는다. 명령마다 `< /dev/null` 을 붙이는 대신 본문을 한 번에 끊은 이유는,
나중에 입력을 읽는 명령이 하나 더 들어와도 같은 사고가 다시 나지 않게 하기
위해서다. 함수 정의는 bash 가 본문 실행 **전에** 끝까지 읽으므로 그 자리에서
표준입력을 끊어도 안전하다(아래 bash 3.2/5.2 실측). 증상(검사 생략)을 가리는 게
아니라 "자식이 스크립트 본문을 물려받는다" 는 원인을 끊는다.

변수에 `local` 을 붙인 것 말고 단계·분기·메시지·종료 코드는 그대로다.
`.github/workflows/deploy.yml` 과 README §20 에는 왜 이렇게 부르는지만 적었다
(README §20 의 "배포 스크립트가 입력을 받을 일은 없어서 걸리는 게 없다" 는 문장이
바로 이 결함을 만든 추론이라 그 문단을 고쳐 적었다).

green:

```text
$ uv run pytest tests/test_deploy_script.py -q
.................................                                        [100%]
33 passed in 4.18s
```

**bash 버전.** 로컬 bash 는 3.2(macOS)라 NAS·러너의 bash 5 에서도 같은지 확인했다.
받아둔 로컬 이미지의 bash 5.2.37 로 표준입력 실행:

```text
$ docker run --rm -i -v "$PWD:/repo:ro" --entrypoint bash chosung-daily-app:latest -c '...
  bash -s -- prod < /repo/deploy/deploy.sh'
GNU bash, version 5.2.37(1)-release (aarch64-unknown-linux-gnu)
== prod 배포: main → /tmp/docker/chosung-daily (chosung-daily-prod / .env)
+ git fetch --quiet origin main
+ git merge --ff-only origin/main
+ docker compose ... up -d --build
+ docker compose ... exec -T app uv run flask db upgrade
+ docker compose ... config --services
+ docker compose ... ps --services --filter status=running
+ docker compose ... port app 5000
http://127.0.0.1:8089/health → 200 {"status":"ok"}
== prod 배포 완료
exit=0
```

같은 이미지에서 수정 전 모양(`bash -s < s.sh`)은 bash 5.2 에서도 `one` 만 찍고 0 으로
끝났다 — 결함도, 수정도 두 버전에서 같이 재현된다.

```text
$ docker run --rm -v "$PWD:/mnt:ro" -w /mnt koalaman/shellcheck:stable deploy/deploy.sh
shellcheck exit=0
$ bash -n deploy/deploy.sh   # exit 0
```

### D-20-5 (MINOR) — README `### 20.` 이 공유 절 중간에 있었음

**원인.** 라운드 1 시점의 로컬 main 에서는 `### 20.` 이 `설계 판단` 절 끝이었는데,
그 뒤 main 에 티켓 02 의 두 절이 들어오면서 중간 삽입이 됐다. rebase 때 위치를
다시 보지 않았다.

**수정 내용.** `### 20.` 블록을 `설계 판단` 절 맨 끝(두 `### 02.` 절 뒤,
`## 부하 테스트 요약` 앞)으로 옮겼다. 이번 rebase 로 main 에 티켓 21 의 `### 21.`
절도 들어왔는데, 그 절은 티켓 21 소유라 건드리지 않고 그 뒤로 갔다.

```text
$ rg -n '^### ' README.md | tail -4
415:### 21. 백업: cron 데몬 대신 sleep 루프, 덤프는 bind mount
452:### 02. 퍼즐 언어 모델 — expand–contract 대신 마이그레이션 1개
477:### 02. 가림(mask) 포맷 — 언어마다 다른 렌더링 코드를 만들지 않기
505:### 20. 배포 스크립트를 ssh 표준입력으로 흘려보내는 이유

$ git diff main..HEAD --stat -- README.md
 README.md | 51 +++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 51 insertions(+)
```

삭제 0줄 — 공유 파일에 자기 번호 절만 끝에 덧붙인 상태다. `docs/RELEASE.md` 도
이번 rebase 에서 티켓 21 절 뒤로 밀렸고, 여전히 모든 추가가 파일 끝 `### 20.`
아래에 있다(D-20-3 유지).

### 전체 검증 (로컬 main `72a2a3c` 위로 rebase 후)

```text
$ git log --oneline main..HEAD
c85a1f9 fix(20) 라운드 2: 배포 본문을 stdin 없이 돌려 exec -T 가 스크립트를 먹지 않게
bb5c1c4 review: 티켓 20 최종 리뷰 라운드 2
519c090 fix(20) 라운드 1: NAS 빌드 커밋을 CI 통과 커밋에 고정 + /health 를 HTTP 200 으로 판정
b98dc42 review: 티켓 20 최종 리뷰 라운드 1
87e2b99 티켓 20 구현 증거 기록
8798bff deploy.yml: CI 가 통과한 커밋만 Tailscale ssh 로 NAS 에 배포
99052f3 deploy.sh: 인자 하나로 prod/develop 배포 + 가짜 NAS 명령으로 실제 실행 검증

$ git status --short     # (출력 없음)

$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL="mysql+pymysql://chosung:***@127.0.0.1:3306/chosung_daily_test_t20?charset=utf8mb4" \
  TEST_REDIS_URL="redis://127.0.0.1:6379/8" uv run pytest -q
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                          [100%]
231 passed in 94.05s (0:01:34)

$ uv run flask db heads
4e72a4045fbc (head)

$ git diff --check main..HEAD    # 출력 없음, exit 0

$ git diff --stat main..HEAD -- migrations/   # 출력 없음 — 마이그레이션 변경 없음
```

187 → 231 은 rebase 로 들어온 티켓 21 의 테스트 + 이번 회귀 테스트 4개다. 테스트
자원은 계속 이 티켓 전용(`chosung_daily_test_t20` / Redis DB 8,
`chosung_daily_test_t20_migrations`)이고 공용 테스트 DB 는 건드리지 않았다.
접속 정보 실값은 이 문서에 적지 않는다.

`review/impl-review-20.md` 는 고치지 않았다(`git log main..HEAD --` 로 확인: 리뷰
커밋 2개만 그 파일을 만진다). 실제 NAS·GitHub Actions·Tailscale 연결과 운영 컨테이너
재기동은 여전히 금지 범위라 실행하지 않았고 `docs/RELEASE.md` D3 체크리스트의 사람
작업으로 남아 있다. 위 Docker 사용은 (1) 이미 돌고 있는 로컬 개발 Redis 컨테이너의
`sleep 0.2`, (2) 받아둔 로컬 이미지로 bash 5.2·shellcheck 확인뿐이고 이미지 빌드·
`up`·`down` 은 없다.

## 수정 라운드 3

라운드 3 리뷰(Codex)는 FAIL, 신규 MAJOR 1건(D-20-6), 이전 5건 전부 FIXED 유지,
REPEAT·BLOCKER·MINOR 0건이다. 미수정 MINOR 없음.

### D-20-6 (MAJOR) — PR/fork CI 성공도 배포 잡을 열었다

**원인.** 배포 잡의 게이트가 `workflow_run` 의 **브랜치 이름**(트리거의
`branches: [main, develop]`)과 `conclusion == 'success'` 둘뿐이었다. 그런데
`ci.yml` 은 `pull_request` 에서도 돈다(`.github/workflows/ci.yml:6`). 브랜치 이름은
PR 의 소스 브랜치도 쓸 수 있으므로, 이름이 `main`/`develop` 인 PR 의 CI 가 성공하면
그 `workflow_run` 이 이름 필터를 통과해 배포 잡을 연다. 열리면 러너가 이벤트의
`head_sha`(= PR 커밋)를 checkout 하고(`deploy.yml:30`), **그 커밋의**
`deploy/deploy.sh` 를 배포 secret 으로 연 NAS 로 흘려보낸다(`deploy.yml:62`).
스크립트 안의 승인 SHA 검사(D-20-1 수정분)는 같은 PR 이 같이 고칠 수 있는 코드라
신뢰 경계를 대신하지 못한다. fork PR CI 를 실행·승인하는 설정이면 남의 저장소
커밋도 같은 경로를 탄다. 리뷰의 지적은 타당하다 — 반박 없음.

**수정.** 증상(스크립트 안 검사 강화)이 아니라 원인(잡을 여는 조건)을 고쳤다.
`.github/workflows/deploy.yml` 의 잡 `if` 에 선행 CI 의 **출처** 검사를 추가해,
checkout·secret 사용·NAS 연결보다 **앞에서** 막는다.

```yaml
    if: >-
      github.event.workflow_run.conclusion == 'success'
      && github.event.workflow_run.event == 'push'
      && github.event.workflow_run.head_repository.full_name == github.repository
```

`event == 'push'` 가 PR CI 를 떨어뜨리고, `head_repository.full_name` 비교가
같은 이름의 브랜치를 가진 fork 를 떨어뜨린다(push 는 원래 자기 저장소에서만 나지만,
둘 중 하나가 빠져도 경로가 다시 열리므로 같이 둔다). 왜 스크립트 안이 아니라
워크플로의 `if` 여야 하는지는 README "설계 판단" §20 마지막 문단에 적었다.

**증명하는 테스트.** `tests/test_deploy_workflow.py` 에 회귀 테스트 4개를 넣었다.
`if` 문자열을 눈으로 비교하지 않고, `workflow_run` 페이로드를 만들어 **식을 실제로
평가**한다(`_allows` 는 게이트가 쓰는 `&&`·`==` 만 해석하고 그 밖의 연산자가 들어오면
조용히 통과시키지 않고 실패한다).

| 테스트 | 검사 |
|---|---|
| `test_deploy_runs_for_push_ci_on_deploy_branches` | main/develop **push** CI 성공은 통과(게이트가 과하게 막지 않음) |
| `test_deploy_blocks_pull_request_ci` | 이름이 main/develop 인 **PR** CI 성공은 차단 |
| `test_deploy_blocks_ci_from_a_forked_head_repository` | **fork** 출처는 차단 |
| `test_deploy_blocks_failed_push_ci` | push CI 실패는 차단(기존 조건 회귀 방지) |

수정 전(red) — 리뷰의 재현 조건 그대로 실패한다:

```text
$ uv run pytest tests/test_deploy_workflow.py -q
FAILED tests/test_deploy_workflow.py::test_deploy_blocks_pull_request_ci - as...
FAILED tests/test_deploy_workflow.py::test_deploy_blocks_ci_from_a_forked_head_repository
2 failed, 15 passed in 0.07s
```

수정 후(green):

```text
$ uv run pytest tests/test_deploy_workflow.py -q
.................                                                        [100%]
17 passed in 0.03s
```

리뷰가 실은 재현 명령(`deploy.yml` 을 읽어 조건을 대조)도 현재 YAML 로 다시 돌렸다.
외부 호출 없이 로컬 파일만 읽는다.

```text
$ uv run python -I - <<'PY'   # 리뷰 D-20-6 재현 스크립트를 새 조건에 맞춰 평가
push base True
pull_request base False
pull_request fork False
${{ github.event.workflow_run.head_sha }}
```

### 라운드 3 전체 검증

```text
$ TEST_DATABASE_URL=mysql+pymysql://chosung:***@127.0.0.1:3306/chosung_daily_test_t20?charset=utf8mb4 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/8 uv run pytest -q
236 passed in 83.56s (0:01:23)

$ uv run ruff check .
All checks passed!            (exit 0)

$ bash -n deploy/deploy.sh    (exit 0)

$ uv run flask db heads
4e72a4045fbc (head)

$ git diff --check main...HEAD   (출력 없음, exit 0)
```

231 → 236 은 이번 회귀 테스트 5개(`test_deploy_runs_for_push_ci_on_deploy_branches`
가 main/develop 로 parametrize 돼 2개로 센다)다. 테스트 자원은 계속 이 티켓 전용
(`chosung_daily_test_t20` / Redis DB 8)이고 공용 테스트 DB 는 건드리지 않았다.
접속 정보 실값은 이 문서에 적지 않는다.

`git rebase main`(로컬 `main` `72a2a3c`) 은 "up to date" — 이미 그 위라 재적용할
커밋이 없었고, 작업 트리는 clean 이다. 마이그레이션 변경 없음(head 는 라운드 2 와
같은 한 줄). `review/impl-review-20.md` 는 고치지 않았다. 실제 GitHub Actions·
Tailscale·NAS 연결과 배포 실행은 여전히 금지 범위라 하지 않았고 `docs/RELEASE.md`
D3 체크리스트의 사람 작업으로 남아 있다. 이번 라운드에 추가로 실행한 Docker 명령은
없다.
