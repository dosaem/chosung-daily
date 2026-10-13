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
