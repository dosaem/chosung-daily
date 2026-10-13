# 티켓 21 구현 증거 — MySQL 매일 백업 컨테이너·14일 보존·복구 스크립트

- 날짜: 2026-10-13
- 브랜치: `dosaem/t21-backup-restore` (로컬 `main` = `feb2553` 위)
- 환경: macOS (Darwin 25.3.0), Docker 29.8.2, uv / Python 3.12
- 전용 테스트 자원: DB `chosung_daily_test_t21`, Redis DB 9
  (`TEST_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 — 공용 테스트 DB·Redis 는 안 건드렸다)
- 로컬 도커 검증은 전용 compose 프로젝트 `chosung-daily-t21`(포트 8097, 임시 env
  파일)로만 했고 검증 후 그 프로젝트만 `down -v` 했다. 다른 워커가 쓰는
  `chosung-daily` 프로젝트(3306/6379)는 건드리지 않았다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `scripts/backup.sh` | 신설. 덤프 1회: `mysqldump --single-transaction --quick --add-drop-database --databases` → gzip → `${DUMP_DIR}/chosung_daily-YYYYmmdd-HHMMSS.sql.gz`, 보존 정리, 실패 시 Slack |
| `scripts/backup-cron.sh` | 신설. backup 컨테이너 entrypoint. 매일 `BACKUP_AT`(기본 04:00, 컨테이너 TZ=KST)에 `backup.sh` 실행. `--print-next` 로 다음 실행 시각 출력 |
| `scripts/restore.sh` | 신설. `restore.sh [-y] <덤프.sql.gz> [compose 프로젝트명]` — gzip 해제 → `docker compose -p <프로젝트> exec -T mysql` stdin |
| `docker-compose.prod.yml` | `backup` 서비스 추가(`mysql:8`, TZ=Asia/Seoul, `./scripts:/scripts:ro`, `${BACKUP_DIR:-./backups}:/backups`, `depends_on: mysql service_healthy`) |
| `.env.prod.example` | `### 21.` 소제목으로 `BACKUP_DIR=./backups`, `SLACK_WEBHOOK_URL=` 추가 |
| `.env.develop.example` | `### 21.` 소제목으로 `BACKUP_DIR=./backups-develop`, `SLACK_WEBHOOK_URL=` 추가 |
| `.gitignore` | `backups*/` |
| `.dockerignore` | `backups*/` (덤프가 `COPY . .` 로 이미지에 구워지는 것 차단) |
| `tests/test_backup_restore.py` | 신설. 셸 스크립트를 실제로 실행하는 테스트 26개 |
| `docs/RELEASE.md` | `### 21. 매일 백업과 복구 리허설` — 설정표, NAS 메모(DSM ACL 해당 없음), `#### 복구 리허설` 절차 + 실측 |
| `README.md` | `## 운영: 백업 / 복구`(위치·보존·복구 명령) + `### 21.` 설계 판단 |

마이그레이션은 만들지 않았다(인프라 전용 티켓).

```
$ uv run flask db heads
9ec267465b4e (head)        # 1줄
```

실제 `.env`·`.env.prod*` 는 건드리지 않았다. 검증용 env 는 `.env.prod.example` 을
베껴 로컬 전용 더미 값만 채운 임시 파일(`.env.t21.tmp`)이고 검증 직후 삭제했다 —
값은 이 문서에도, 로그에도 남기지 않는다.

## 2. 체크박스별 증거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| compose 에 독립 백업 서비스(mysqldump, cron 04:00 KST, gzip, 보존 14일 정리) | `tests/test_backup_restore.py::test_backup_service_reuses_the_mysql_image`·`::test_backup_service_runs_the_cron_loop`·`::test_backup_service_env`·`::test_backup_service_waits_for_mysql` + 실제 기동 §4.1(컨테이너 로그 `daily at 04:00 +0900, next in 22258s`) + gzip 덤프 §4.2 + 예약 시각 정각 실행 §4.6 |
| 덤프 디렉터리 = `${BACKUP_DIR}` bind mount(기본 `./backups`), 예시 env 에 추가 | `::test_backup_dumps_go_to_a_bind_mounted_host_directory`, `::test_env_examples_document_backup_dir_and_webhook[.env.prod.example / .env.develop.example]` + §4.2 에서 호스트 `backups/` 에 파일이 보임 |
| 보존 14일 정리 | `::test_backup_keeps_14_days_and_deletes_older`, `::test_backup_retention_days_is_configurable` + 실제 이미지(GNU find)에서 13/14/15/30일 mtime 실측 §4.5 |
| 컨테이너가 root 로 쓰므로 DSM ACL 문제 해당 없음 → RELEASE.md 메모 | §4.7 `id` = `uid=0(root)`, 덤프 소유자 `root:root` + `docs/RELEASE.md` "NAS 설정 메모" 두 번째 항목 |
| 실패 시 Slack webhook 알림(쉘 curl, `SLACK_WEBHOOK_URL` 재사용) | `::test_backup_notifies_slack_on_failure`, `::test_backup_without_webhook_is_silent_but_still_fails`, `::test_backup_succeeds_quietly`, `::test_backup_failure_leaves_no_partial_dump` + 실제 이미지에서 POST 페이로드 확인 §4.4 |
| `scripts/restore.sh <dump>` 가 지정 덤프를 지정 compose 프로젝트 MySQL 에 복원 | `::test_restore_pipes_dump_into_the_project_mysql`, `::test_restore_defaults_project_to_compose_project_name`, `::test_restore_without_project_refuses`, `::test_restore_requires_a_dump_argument`, `::test_restore_rejects_missing_dump`, `::test_restore_requires_confirmation_when_not_interactive`, `::test_restore_reads_password_inside_the_container` + 실제 복원 §4.3 |
| 로컬 검증: 백업 1회 → 데이터 변경 → `restore.sh` → 원복 확인, 절차·결과를 `docs/RELEASE.md` "복구 리허설" 절에 기록 | §4.2 → §4.3 (상태 A → B → A) + `docs/RELEASE.md` `#### 복구 리허설` |
| README 운영 절에 백업 위치·보존·복구 명령 | `README.md` `## 운영: 백업 / 복구` (표 + 명령 블록) |
| 리뷰 노트 P1-23: 덤프 위치 `${BACKUP_DIR}` bind mount 확정 | compose `backup.volumes` 의 `${BACKUP_DIR:-./backups}:/backups` + 위 bind mount 테스트 |

## 3. TDD (red → green)

테스트 26개를 먼저 쓰고 돌렸다 — 전부 실패(21 failed + 5 error, error 는 compose 에
`backup` 서비스가 없어 모듈 픽스처가 `KeyError: 'backup'`).

```
$ uv run pytest tests/test_backup_restore.py -q
FAILED tests/test_backup_restore.py::test_restore_rejects_missing_dump - File...
FAILED tests/test_backup_restore.py::test_restore_pipes_dump_into_the_project_mysql
FAILED tests/test_backup_restore.py::test_restore_reads_password_inside_the_container
FAILED tests/test_backup_restore.py::test_restore_defaults_project_to_compose_project_name
FAILED tests/test_backup_restore.py::test_restore_without_project_refuses - F...
FAILED tests/test_backup_restore.py::test_restore_requires_confirmation_when_not_interactive
FAILED tests/test_backup_restore.py::test_env_examples_document_backup_dir_and_webhook[.env.prod.example]
FAILED tests/test_backup_restore.py::test_env_examples_document_backup_dir_and_webhook[.env.develop.example]
FAILED tests/test_backup_restore.py::test_backups_directory_is_not_committed
ERROR tests/test_backup_restore.py::test_backup_service_reuses_the_mysql_image
ERROR tests/test_backup_restore.py::test_backup_service_runs_the_cron_loop - ...
ERROR tests/test_backup_restore.py::test_backup_dumps_go_to_a_bind_mounted_host_directory
ERROR tests/test_backup_restore.py::test_backup_service_env - KeyError: 'backup'
ERROR tests/test_backup_restore.py::test_backup_service_waits_for_mysql - Key...
21 failed, 5 errors in 0.74s
```

(위 red 출력의 `test_backups_directory_is_not_committed` 는 `.dockerignore` 검사를
같이 넣으면서 `test_dumps_are_not_committed_or_baked_into_the_image` 로 이름을 바꿨다.)

구현 후:

```
$ uv run pytest tests/test_backup_restore.py -q
..........................                                               [100%]
26 passed in 2.45s
```

테스트가 흉내가 아닌 이유: `mysqldump`·`curl`·`docker` 만 PATH 앞의 스텁으로
바꿔(인자와 stdin 을 파일로 기록) 셸 스크립트를 **실제로 실행**하고, gzip·find·date
는 진짜를 쓴다. 그래서 "gzip 덤프가 떨어진다", "14일 지난 파일이 지워진다",
"실패하면 Slack 으로 쏜다", "비밀번호가 명령줄에 안 나온다" 를 스크립트가 한 일로
확인한다. 도커를 띄우는 end-to-end 는 아래 §4.

## 4. 실제 도커 검증 (프로젝트 `chosung-daily-t21`)

```
$ docker compose -f docker-compose.prod.yml -p chosung-daily-t21 --env-file .env.t21.tmp config --services
mysql
redis
beat
worker
app
backup
```

### 4.1 기동 — backup 컨테이너가 04:00 KST 를 기다린다

```
$ docker compose ... up -d --build
 Container chosung-daily-t21-backup-1 Started
 Container chosung-daily-t21-worker-1 Started
 Container chosung-daily-t21-app-1 Started
 Container chosung-daily-t21-beat-1 Started

$ docker compose ... ps --format '{{.Service}}\t{{.State}}'
app	running
backup	running
beat	running
mysql	running
redis	running
worker	running

$ docker compose ... logs backup | tail -1
backup-1  | [backup-cron] daily at 04:00 +0900, next in 22258s      # 21:49 → 다음 04:00

$ curl -s http://127.0.0.1:8097/health
{"status":"ok"}
```

### 4.2 백업 1회 (상태 A)

```
$ docker compose ... exec -T app uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade e759d7e8d071 -> 9ec267465b4e, replace kakao with apple as oauth provider
$ docker compose ... exec -T app uv run flask seed-words data/seed_words.csv
20개 단어 시드 완료
$ docker compose ... exec -T app uv run flask schedule-puzzles --days 2
2일치 퍼즐 배정 완료 (이미 있던 날짜는 건너뜀)

$ TOKEN=$(curl -s -X POST http://127.0.0.1:8097/api/v1/guests | ... .token)   # 36자
$ curl -s -X POST http://127.0.0.1:8097/api/v1/puzzles/today/guesses -H "Authorization: Bearer $TOKEN" -d '{"guess":"포도"}'
{"answer":null,"attempts_left":4,"feedback":[false,false],"hint":null,"is_correct":false}

# 상태 A: word / guest / attempt / daily_puzzle
$ docker exec chosung-daily-t21-mysql-1 sh -c 'mysql ... -N -e "select ..."'
20	1	1	2

$ docker compose ... exec -T backup /scripts/backup.sh
[backup] 2026-10-13 21:49:39+0900 dumping chosung_daily from mysql -> /backups/chosung_daily-20261013-214939.sql.gz
[backup] 2026-10-13 21:49:39+0900 wrote 4.0K /backups/chosung_daily-20261013-214939.sql.gz
[backup] 2026-10-13 21:49:39+0900 done (1 dumps kept)
exit=0

# 호스트의 bind mount 폴더에 그대로 보인다
$ ls -l backups/
-rw-rw-rw-@ 1 saem  staff  2521 Oct 13 21:49 chosung_daily-20261013-214939.sql.gz

$ gzip -dc backups/chosung_daily-20261013-214939.sql.gz | grep -i "drop database\|drop table" | head -3
22:/*!40000 DROP DATABASE IF EXISTS `chosung_daily`*/;
32:DROP TABLE IF EXISTS `account`;
62:DROP TABLE IF EXISTS `alembic_version`;
$ gzip -dc backups/... | wc -l
258
```

### 4.3 데이터 변경(상태 B) → `restore.sh` → 원복 확인

```
# 오답 1회 더
$ curl -s -X POST .../guesses -H "Authorization: Bearer $TOKEN" -d '{"guess":"수박"}'
{"answer":null,"attempts_left":3,...}
# 단어 1건 INSERT + daily_puzzle 1건 DELETE
$ docker exec chosung-daily-t21-mysql-1 sh -c 'mysql ... -e "insert into word ...; delete from daily_puzzle ...;"'

# 상태 B
21	1	2	1

# 비대화 실행에서 -y 없이 → 거부
$ ./scripts/restore.sh backups/chosung_daily-20261013-214939.sql.gz chosung-daily-t21 </dev/null
비대화 실행에서는 -y 를 줘야 한다 (대상: chosung-daily-t21)
exit=1

$ ./scripts/restore.sh -y backups/chosung_daily-20261013-214939.sql.gz chosung-daily-t21
[restore] backups/chosung_daily-20261013-214939.sql.gz -> project=chosung-daily-t21 (docker-compose.prod.yml)
mysql: [Warning] Using a password on the command line interface can be insecure.
[restore] 완료. 앱이 캐시를 들고 있으니 필요하면 app/worker/beat 를 재시작한다:
  docker compose -f docker-compose.prod.yml -p chosung-daily-t21 restart app worker beat
exit=0

# 복원 후: 상태 A 그대로 (마지막 열 = 추가했던 단어 건수)
20	1	1	2	0

# 앱 재시작 없이도 같은 게스트 토큰으로 attempts_left 가 4 로 돌아왔다
$ curl -s http://127.0.0.1:8097/api/v1/puzzles/today -H "Authorization: Bearer $TOKEN"
{"answer":null,"attempts_left":4,"category":"general","chosung":"ㅂㄷ","date":"2026-10-13","hint":null,"length":2,"status":"in_progress"}
```

경고 한 줄(`Using a password on the command line interface can be insecure`)은
**컨테이너 안에서** `mysql -p"$MYSQL_ROOT_PASSWORD"` 를 쓰기 때문에 나온다. 호스트
스크립트는 비밀번호를 모르고(`exec ... sh -c 'exec mysql -u root -p"$MYSQL_ROOT_PASSWORD"'`
를 홑따옴표로 넘겨 컨테이너 안에서 전개된다), 덤프를 뜨는 `backup.sh` 쪽은
`--defaults-extra-file` 이라 이 경고가 없다.

### 4.4 실패 → Slack 알림 (실제 이미지의 curl)

페이로드를 보려고 컨테이너 안 `/tmp/bin/curl` 스텁을 PATH 앞에 두고 실행했다.

```
$ docker compose ... exec -T backup bash -c 'PATH=/tmp/bin:$PATH MYSQL_HOST=no-such-mysql SLACK_WEBHOOK_URL=https://hooks.example.test/T/B/XYZ /scripts/backup.sh'
[backup] 2026-10-13 21:50:26+0900 dumping chosung_daily from no-such-mysql -> /backups/chosung_daily-20261013-215026.sql.gz
mysqldump: Got error: 2005: Unknown MySQL server host 'no-such-mysql' (-2) when trying to connect
[backup] 2026-10-13 21:50:26+0900 FAILED: mysqldump exited non-zero
exit=1

$ docker compose ... exec -T backup cat /tmp/curl.args
-sS
-m
10
-X
POST
-H
Content-type: application/json
--data
{"text":"[chosung-daily] MySQL backup failed - db=chosung_daily host=no-such-mysql - mysqldump exited non-zero"}
https://hooks.example.test/T/B/XYZ

# 부분 덤프가 남지 않는다 (실패 전 만든 1개만 있다)
$ ls -l backups/
-rw-rw-rw-@ 1 saem  staff  2521 Oct 13 21:49 chosung_daily-20261013-214939.sql.gz

# 웹훅이 안 닿아도 종료 코드는 1 (진짜 curl)
$ docker compose ... exec -T backup bash -c 'MYSQL_HOST=no-such-mysql SLACK_WEBHOOK_URL=http://127.0.0.1:9/hook /scripts/backup.sh'
...
curl: (7) Failed to connect to 127.0.0.1 port 9: Connection refused
exit=1
```

외부로 실제 요청을 보내지 않았다 — 주소는 `hooks.example.test`(스텁 curl) 과
`127.0.0.1:9`(연결 거부)다.

### 4.5 보존 14일 (실제 이미지, GNU find/touch)

```
$ docker compose ... exec -T backup bash -c 'cd /backups; for d in 30 15 14 13 2; do f="chosung_daily-aged-${d}d.sql.gz"; : > "$f"; touch -d "$d days ago" "$f"; done; : > keep-me.txt; touch -d "99 days ago" keep-me.txt; ls; /scripts/backup.sh; ls'
--- 백업 전 ---
chosung_daily-20261013-214939.sql.gz
chosung_daily-aged-13d.sql.gz
chosung_daily-aged-14d.sql.gz
chosung_daily-aged-15d.sql.gz
chosung_daily-aged-2d.sql.gz
chosung_daily-aged-30d.sql.gz
keep-me.txt
--- backup.sh (보존 14일) ---
[backup] 2026-10-13 21:50:37+0900 wrote 4.0K /backups/chosung_daily-20261013-215037.sql.gz
[backup] 2026-10-13 21:50:37+0900 pruned /backups/chosung_daily-aged-30d.sql.gz
[backup] 2026-10-13 21:50:37+0900 pruned /backups/chosung_daily-aged-14d.sql.gz
[backup] 2026-10-13 21:50:37+0900 pruned /backups/chosung_daily-aged-15d.sql.gz
[backup] 2026-10-13 21:50:37+0900 done (4 dumps kept)
--- 백업 후 ---
chosung_daily-20261013-214939.sql.gz
chosung_daily-20261013-215037.sql.gz
chosung_daily-aged-13d.sql.gz
chosung_daily-aged-2d.sql.gz
keep-me.txt
```

14·15·30일 것만 지워지고 13·2일 것은 남는다(= 오늘 것까지 14개). 덤프가 아닌
`keep-me.txt` 는 99일이 지났어도 그대로다.

### 4.6 스케줄 — 예약 시각 정각에 덤프가 떨어진다

04:00 을 기다릴 수 없으니 `BACKUP_AT` 을 2분 뒤로 주고 루프를 돌렸다.

```
$ docker compose ... exec -T backup bash -c 'at=$(date -d "+2 minutes" +%H:%M); BACKUP_AT=$at timeout 150 /scripts/backup-cron.sh'
컨테이너 현재 21:50 (TZ=KST +0900), BACKUP_AT=21:52 로 루프 테스트
[backup-cron] daily at 21:52 +0900, next in 75s
[backup] 2026-10-13 21:52:00+0900 dumping chosung_daily from mysql -> /backups/chosung_daily-20261013-215200.sql.gz
[backup] 2026-10-13 21:52:00+0900 wrote 4.0K /backups/chosung_daily-20261013-215200.sql.gz
[backup] 2026-10-13 21:52:00+0900 done (3 dumps kept)
```

`21:52:00+0900` 정각 — 컨테이너 TZ 가 KST 라 04:00 설정이 04:00 KST 다.

### 4.7 root 로 쓴다 (DSM ACL 해당 없음)

```
$ docker compose ... exec -T backup bash -c 'id; stat -c "%U:%G %a %n" /backups/*.sql.gz | head -3'
uid=0(root) gid=0(root) groups=0(root)
root:root 666 /backups/chosung_daily-20261013-214939.sql.gz
root:root 666 /backups/chosung_daily-20261013-215037.sql.gz
root:root 666 /backups/chosung_daily-20261013-215200.sql.gz
```

(권한 `666` 은 macOS 바인드 마운트 변환 결과다. 중요한 건 쓰는 주체가 root 라서
mysql 컨테이너의 uid 999 를 막던 `/volume1` ACL 문제가 없다는 것.)

### 4.8 정리

```
$ docker compose -f docker-compose.prod.yml -p chosung-daily-t21 --env-file .env.t21.tmp down -v
 Volume chosung-daily-t21_mysql-data Removed
 Volume chosung-daily-t21_redis-data Removed
 Network chosung-daily-t21_default Removed
$ rm -f .env.t21.tmp; rm -rf backups

$ docker ps --format '{{.Names}}'          # 다른 워커가 쓰는 공용 컨테이너는 그대로
chosung-daily-redis-1
chosung-daily-mysql-1
$ docker volume ls --format '{{.Name}}' | grep chosung
chosung-daily_mysql_data
```

## 5. 전체 테스트 · 린트

```
$ TEST_DATABASE_URL=...chosung_daily_test_t21... TEST_REDIS_URL=redis://127.0.0.1:6379/9 uv run pytest -q
........................................................................ [ 64%]
.......................................                                  [100%]
111 passed in 38.13s

$ uv run ruff check .
All checks passed!

$ uv run flask db heads
9ec267465b4e (head)
```

셸 스크립트도 검사했다.

```
$ bash -n scripts/backup.sh scripts/backup-cron.sh scripts/restore.sh   # 각각 ok
$ docker run --rm -v "$PWD:/mnt" koalaman/shellcheck:stable scripts/*.sh
shellcheck exit=0        # 출력 없음
```

`uv run ruff format --check .` 는 이 레포에서 원래 9개 파일이 걸린다(CI 는 `ruff
check` 만 돈다). 새로 추가한 `tests/test_backup_restore.py` 는 `ruff format` 을
적용해서 통과 상태다.

## 6. 안 한 것 / 남은 것

- **NAS 실행은 하지 않았다.** 프로덕션 금지 제약대로 로컬 전용 compose 프로젝트에서만
  검증했다. NAS 쪽 사람 체크리스트는 `docs/RELEASE.md`(백업 폴더 경로 지정, 첫
  `up` 후 `logs backup` 으로 다음 실행 시각 확인).
- **Slack 실제 전송 없음.** 페이로드는 컨테이너 안 스텁 curl 로, 실패 시 종료 코드는
  닿지 않는 주소로 확인했다. 실제 webhook 발급은 스펙 D1(사람 작업).
- `SLACK_WEBHOOK_URL` 은 `.env.prod.example`·`.env.develop.example` 에만 추가했다.
  `.env.example`(로컬 개발용)은 티켓 01 이 `app/clients/slack.py` 와 함께 추가하는
  파일이라 건드리지 않았다 — 로컬 compose(`docker-compose.yml`)에는 backup 서비스가
  없다(NAS 전용).
- `scripts/` 를 `.dockerignore` 에 넣지 않았다. backup 컨테이너는 호스트 폴더를
  bind mount 로 읽지만, 앱 이미지에 스크립트 3개(5KB)가 들어가는 건 해로울 게 없고
  이미지 안에서도 같은 스크립트로 수동 덤프를 뜰 수 있다.

---

## 수정 라운드 1

- 날짜: 2026-10-14
- 대상: `review/impl-review-21.md` 라운드 1 의 MAJOR 3건(D-21-1·2·3). BLOCKER·REPEAT·MINOR 는 없었다.
- 로컬 `main` = `491418f`(티켓 01 머지) 위로 rebase 했다. 충돌 2건(`.gitignore`,
  `README.md` 설계 판단 절)은 양쪽 티켓이 각자 덧붙인 독립 항목이라 둘 다 남겼다.
- 전용 테스트 자원은 그대로 — DB `chosung_daily_test_t21`, Redis DB 9,
  도커 검증은 전용 compose 프로젝트 `chosung-daily-t21`(포트 8097, 임시 env).

### D-21-1 — 파일시스템 실패가 Slack 알림 없이 종료됨

**원인.** `fail()` 은 mysqldump 파이프라인과 크기 검사 두 곳에서만 불린다.
`mkdir`·`mv`·보존 정리는 그냥 명령이라 실패하면 `set -e` 가 그 줄에서 셸을
끝내버리고, EXIT trap 은 임시 파일만 지운다. 알림이 "실패 지점마다 수동으로
붙이는 것" 이라서 빠진 지점이 생긴 구조적 문제다.

**수정** (`scripts/backup.sh`).

- `set -Eeuo pipefail` + `trap 'fail "unexpected error at ...:$LINENO (exit $?)"' ERR`
  — 미처 손으로 감싸지 않은 실패도 전부 `fail()` 을 거친다. `-E` 는 함수
  안에서도 trap 을 받게 한다.
- `fail()` 에 `notified` 가드를 넣어 ERR trap 과 명시적 `fail` 이 겹쳐도 Slack 은 한 번만.
- 운영자가 원인을 바로 알 수 있게 세 지점에 메시지를 직접 달았다:
  `mkdir -p ... || fail "cannot create dump dir ..."`,
  `mv ... || fail "cannot move dump into place: ..."`,
  보존 정리는 `if ! find ... ; then fail "retention prune failed in ..."; fi`.
  정리 실패는 덤프가 떴어도 알린다 — 디스크가 차면 다음 백업부터 통째로 실패한다.

**증명.** 리뷰의 재현 코드를 그대로 다시 돌렸다.

```
$ uv run python <리뷰 §"D-21-1 / D-21-2 안전 재현 코드">
mkdir failure: 1 slack called: True          # 수정 전: slack called: False
```

실제 `mysql:8` backup 컨테이너(스텁 curl 을 `/tmp/bin` 에 두고 PATH 앞):

```
$ ... exec -T backup bash -c 'PATH=/tmp/bin:$PATH DUMP_DIR=/backups/a-regular-file/dumps ... /scripts/backup.sh'
mkdir: cannot create directory '/backups/a-regular-file': Not a directory
[backup] 2026-10-14 06:30:10+0900 FAILED: cannot create dump dir /backups/a-regular-file/dumps
exit=1
--- curl 호출 ---
... --data {"text":"[chosung-daily] MySQL backup failed - db=chosung_daily host=mysql - cannot create dump dir /backups/a-regular-file/dumps"}
https://hooks.example.test/T/B/XYZ

# mv 실패 (스텁 mv)
exit=1
{"text":"[chosung-daily] MySQL backup failed - db=chosung_daily host=mysql - cannot move dump into place: /backups/chosung_daily-20261014-063035.sql.gz"}
--- .partial 잔여물 ---        # 없다
chosung_daily-20261014-062405.sql.gz
chosung_daily-20261014-063023.sql.gz

# 보존 정리 실패 (-delete 일 때만 실패하는 스텁 find)
[backup] ... FAILED: retention prune failed in /backups (dump /backups/chosung_daily-20261014-063023.sql.gz is written)
exit=1
retention prune failed in /backups (dump ... is written)      # Slack 페이로드

# 정상 백업은 그대로 (ERR trap 오작동 없음)
[backup] 2026-10-14 06:30:23+0900 done (2 dumps kept)
exit=0
```

**고정한 테스트** — `tests/test_backup_restore.py`:
`test_backup_notifies_slack_when_the_dump_dir_cannot_be_created`,
`test_backup_notifies_slack_when_the_dump_cannot_be_moved_into_place`,
`test_backup_notifies_slack_when_retention_prune_fails`. 셋 다 수정 전엔 실패한다.

### D-21-2 — 손상된 압축 덤프가 검증 전에 기존 DB를 파괴할 수 있음

**원인.** `gzip -dc "$dump" | docker compose exec -T mysql ...` 는 스트리밍이다.
gzip 은 끝부분 CRC/길이를 다 읽어야 손상을 알 수 있는데, 그때는 이미 앞쪽
`DROP DATABASE` / `CREATE DATABASE` 가 mysql 클라이언트에 닿아 실행된 뒤다.
pipefail 이 종료 코드 1 을 돌려줘도 DB 는 이미 날아갔다.

**수정** (`scripts/restore.sh`). 복원 파이프라인에 들어가기 전에 — 확인 프롬프트보다도
앞에서 — `gzip -t "$dump"` 로 압축 전체를 풀어 검사하고, 실패하면
"MySQL 은 건드리지 않았다" 를 찍고 종료한다.

**증명.** 리뷰 재현 코드:

```
truncated dump: 1 SQL passed to mysql: <nothing - docker never ran>
덤프가 깨졌다(gzip 무결성 검사 실패) — MySQL 은 건드리지 않았다: .../corrupt.sql.gz
```

수정 전은 같은 자리에서 `SQL passed to mysql: DROP DATABASE IF EXISTS chosung_daily;
CREATE DATABASE chosung_daily;` 였다. 실제 스택에서도 — 진짜 덤프를 절반(1251/2503
바이트)으로 자르고 돌린 뒤 DB 를 확인했다:

```
$ COMPOSE_FILE=docker-compose.prod.yml ./scripts/restore.sh -y <잘린 덤프> chosung-daily-t21
gzip: ...truncated.sql.gz: unexpected end of file
덤프가 깨졌다(gzip 무결성 검사 실패) — MySQL 은 건드리지 않았다: ...
exit=1
$ ... select count(*) from word;  select ... where puzzle_date="2026-10-14";
20
1	컴퓨터            # 그대로
```

**고정한 테스트**: `test_restore_rejects_a_truncated_dump_before_touching_mysql`,
`test_restore_rejects_a_file_that_is_not_a_dump` (둘 다 docker 가 아예 안 불린 걸 본다).

### D-21-3 — 복구 후 캐시 정리 안내가 Redis의 복구 전 데이터를 남김

**원인.** 복구는 MySQL 만 덤프 시점으로 되감는다. Redis 는 별도 컨테이너
(`redis-data` 볼륨)라 앱·워커를 재시작해도 그대로 살아 있고, 앱 시작 경로 어디에도
캐시를 비우는 코드가 없다(`app/extensions.py:17` 은 새 연결만 만든다).
`puzzle:<날짜>` 는 TTL 26시간(`app/services/puzzle_cache.py:11`)이고
`app/services/puzzle_service.py` 는 캐시가 맞으면 DB 를 안 읽는다. 그래서 문서가
안내하던 `restart app worker beat` 는 "캐시 정리" 가 아니다.

**실제 스택에서 재현** (전용 프로젝트 `chosung-daily-t21`). 상태 A = 오늘 퍼즐
id 1 `ㅋㅍㅌ/컴퓨터` → 백업 → 상태 B = 퍼즐 행 교체(id 3 `ㅈㅈㄱ/자전거`)하고
API 로 B 를 캐시에 올림 → **MySQL 만 복원 + 문서대로 재시작**:

```
--- 복원된 DB ---
1	ㅋㅍㅌ	컴퓨터                      # DB 는 A 로 돌아왔다
--- redis (재시작 후) ---
{"id": 3, ... "answer": "자전거" ...}       # 캐시는 B 그대로
--- API 오늘 퍼즐 ---
{'chosung': 'ㅈㅈㄱ', ...}                  # 복구 전 퍼즐을 계속 내놓는다
--- 정답 제출 ---
{"code":"INTERNAL_ERROR", ...}  HTTP 500
```

앱 로그가 원인을 그대로 보여준다 — 캐시에 든 퍼즐 id 가 복원된 DB 에 없다:

```
sqlalchemy.exc.IntegrityError: (pymysql.err.IntegrityError) (1452, 'Cannot add or update
a child row: a foreign key constraint fails (`chosung_daily`.`attempt`,
CONSTRAINT `attempt_ibfk_2` FOREIGN KEY (`puzzle_id`) REFERENCES `daily_puzzle` (`id`))')
[parameters: {'guest_id': 1, 'puzzle_id': 3, 'guess': '자전거', ...}]
```

**수정.** `restore.sh` 가 MySQL 복원 **뒤에** 대상 프로젝트의 Redis 파생 키
(`puzzle:*`, `stats:*`, `lb:*`)를 직접 지운다. 지우기에 실패하면 "복구 전 캐시를
내보낼 수 있다" 와 수동 확인 명령을 찍고 종료 코드 1 이다. `FLUSHDB` 는 쓰지
않는다 — 같은 Redis DB(`redis://redis:6379/0`)에 celery 브로커 큐가 살고,
rate limit 카운터(60초)는 DB 와 무관하다. `stats:`·`lb:` 를 같이 지우는 이유는
그 카운터가 되감긴 attempt 행을 세고 있던 값이라 복원된 DB 보다 앞서 있어서다
(전날까지의 집계는 `DailyStats` 로 MySQL 에 있어 덤프와 함께 복원된다 —
그 날 것만 0 부터 다시 쌓인다). README·RELEASE 의 `restart app worker beat`
안내는 걷어내고 실제 동작으로 바꿨다.

**증명.** 같은 상태에서 고친 `restore.sh` 로 복구:

```
$ COMPOSE_FILE=docker-compose.prod.yml ./scripts/restore.sh -y backups/chosung_daily-20261014-062405.sql.gz chosung-daily-t21
[restore] backups/... -> project=chosung-daily-t21 (docker-compose.prod.yml)
[restore] Redis 파생 키 정리 (puzzle:/stats:/lb:)
[restore] deleted 1 derived keys
[restore] 완료 — MySQL 은 덤프 시점으로, Redis 파생 키는 비워졌다.

--- redis puzzle 키 ---          # 비어 있다
--- API 오늘 퍼즐 (앱 재시작 없이) ---
{'chosung': 'ㅋㅍㅌ', 'date': '2026-10-14', ...}       # 복원된 퍼즐
--- 정답 제출 ---
{"answer":"컴퓨터","attempts_left":4,"is_correct":true}   HTTP 200
```

선택적으로 지운다는 것(= celery 브로커를 날리지 않는다):

```
=== 복구 직전 Redis ===                    === 복구 직후 ===
_kombu.binding.celery.pidbox               _kombu.binding.celery.pidbox
puzzle:2026-10-14                          ratelimit:guess:1
stats:2026-10-14                           _kombu.binding.celery
ratelimit:guess:1                          _kombu.binding.celeryev
_kombu.binding.celery
_kombu.binding.celeryev
lb:2026-10-14
                                           [restore] deleted 3 derived keys
```

**고정한 테스트**: `test_restore_invalidates_derived_redis_keys_after_the_database`
(복원 다음 호출이 같은 프로젝트의 `redis` 서비스를 치고 세 패턴을 모두 포함),
`test_restore_does_not_wipe_the_celery_broker`(FLUSHDB/FLUSHALL 금지),
`test_restore_leaves_redis_alone_when_the_database_restore_fails`,
`test_restore_docs_do_not_sell_an_app_restart_as_cache_cleanup[README.md / docs/RELEASE.md]`,
그리고 뿌리를 박아두는 `test_restarting_the_app_does_not_clear_the_puzzle_cache`
(앱을 새로 만들어도 캐시가 TTL 93600초로 그대로 남는 걸 본다).

테스트 하네스도 같이 고쳤다 — `restore.sh` 가 docker 를 두 번 부르게 돼서
docker 스텁이 호출마다 따로 기록하도록 바꿨다(`docker.<n>.args` /
`docker.<n>.stdin`, `Stub.call_args` / `Stub.call_stdin`). 안 바꾸면 뒤 호출이 앞
호출의 stdin 기록을 덮어써서 기존 테스트가 거짓 초록이 된다.

### TDD (red → green)

고치기 전에 테스트 9개를 먼저 넣고 돌렸다.

```
$ TEST_... uv run pytest tests/test_backup_restore.py -q
FAILED ...::test_backup_notifies_slack_when_the_dump_dir_cannot_be_created
FAILED ...::test_backup_notifies_slack_when_the_dump_cannot_be_moved_into_place
FAILED ...::test_backup_notifies_slack_when_retention_prune_fails
FAILED ...::test_restore_rejects_a_truncated_dump_before_touching_mysql
FAILED ...::test_restore_rejects_a_file_that_is_not_a_dump
FAILED ...::test_restore_invalidates_derived_redis_keys_after_the_database
FAILED ...::test_restore_does_not_wipe_the_celery_broker
FAILED ...::test_restore_docs_do_not_sell_an_app_restart_as_cache_cleanup[README.md]
FAILED ...::test_restore_docs_do_not_sell_an_app_restart_as_cache_cleanup[docs/RELEASE.md]
9 failed, 28 passed in 8.80s
```

고친 뒤 `37 passed`.

### 전체 테스트 · 린트 (rebase 후)

```
$ TEST_DATABASE_URL=...chosung_daily_test_t21... TEST_REDIS_URL=redis://127.0.0.1:6379/9 uv run pytest -q
........................................................................ [ 49%]
........................................................................ [ 99%]
.                                                                        [100%]
145 passed in 52.63s

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check tests/test_backup_restore.py
1 file already formatted

$ uv run flask db heads
9ec267465b4e (head)        # 1줄, 이 티켓은 마이그레이션을 만들지 않았다

$ bash -n scripts/backup.sh scripts/backup-cron.sh scripts/restore.sh     # ok
$ docker run --rm -v "$PWD:/mnt" koalaman/shellcheck:stable scripts/*.sh
shellcheck exit=0
```

티켓 01 이 `main` 에 들어오면서 ruff 규칙이 늘어(`PL`, `RUF`, `SIM`, `PT`)
`tests/test_backup_restore.py` 가 8건 걸렸다 — `subprocess.run(check=False)`
명시, `and` 로 묶인 assert 분리(PT018), 함수 안 import 를 모듈 상단으로(PLC0415).
동작은 그대로다.

### 리뷰 지적 중 고치지 않은 것

없다. MAJOR 3건 모두 고쳤고 MINOR 는 제기되지 않았다.

리뷰가 "증거 부족" 으로 남긴 **복구 왕복 재검증**은 이번에 다시 했다 — 위 D-21-3
의 A → B → 복원 → A 가 그 왕복이고, 전용 프로젝트 `chosung-daily-t21` 로만
돌린 뒤 `down -v` + 임시 env·`backups/` 삭제까지 했다. 공용 `chosung-daily`
컨테이너(3306/6379)와 볼륨은 건드리지 않았다:

```
$ docker ps --format '{{.Names}}'
chosung-daily-redis-1
chosung-daily-mysql-1
$ docker volume ls --format '{{.Name}}' | grep chosung
chosung-daily_mysql_data
```

리뷰가 공용 테스트 DB 로 전체 테스트를 돌려 겪은 실패(`guest_stats` 테이블 부재,
재실행마다 다른 분포)는 티켓 21 의 회귀가 아니다 — 전용 자원
(`chosung_daily_test_t21` / Redis DB 9)으로 돌리면 위와 같이 145개가 전부 통과한다.

### 안 한 것

- NAS·프로덕션 실행, 실제 Slack 전송, `git push` 는 하지 않았다(제약 그대로).
  Slack 페이로드는 전부 스텁 curl 과 `hooks.example.test` 로만 확인했다.
- 결함 범위 밖의 리팩토링·기능 추가는 하지 않았다. `review/impl-review-21.md`
  는 건드리지 않았다.
