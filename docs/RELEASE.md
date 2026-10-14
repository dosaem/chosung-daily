# 릴리스·배포

Synology NAS(Container Manager) 한 대에서 prod 와 develop 두 인스턴스를 돌린다.
compose 파일은 `docker-compose.prod.yml` 하나를 공유하고, 환경별로 달라지는 값은
compose 프로젝트명·호스트 포트·env 파일 세 개뿐이다.

## 인스턴스 구성

| | prod | develop |
|---|---|---|
| 브랜치 | `main` | `develop` |
| 체크아웃 디렉터리 | `/volume1/docker/chosung-daily` | `/volume1/docker/chosung-daily-develop` |
| compose 프로젝트명 | `chosung-daily-prod` | `chosung-daily-develop` |
| 호스트 포트(`APP_PORT`) | 8089 | 8090 (NAS 실측으로 확정, 스펙 미정 8) |
| env 파일(`ENV_FILE`) | `.env` | `.env.develop` |
| 예시 파일 | `.env.prod.example` | `.env.develop.example` |
| DB/Redis 볼륨 | `chosung-daily-prod_mysql-data` · `_redis-data` | `chosung-daily-develop_mysql-data` · `_redis-data` |

```bash
# prod
docker compose -f docker-compose.prod.yml -p chosung-daily-prod \
  --env-file .env up -d --build

# develop
docker compose -f docker-compose.prod.yml -p chosung-daily-develop \
  --env-file .env.develop up -d --build
```

DB 는 **named volume 만** 쓴다. DSM 의 `/volume1` ACL 이 호스트 bind mount 에는
걸려서 mysql 컨테이너(uid 999)가 쓰기 권한 없이 뻗는다 — 도커가 관리하는 volume
에는 안 걸린다. bind mount 로 바꾸지 않는다.

## 첫 배포 체크리스트 (prod)

- [ ] **NAS 의 실제 compose 프로젝트명·볼륨명을 먼저 확인하고 `up`** 한다.
      `docker volume ls | grep chosung` 으로 기존 볼륨 이름을 보고, 그 접두사가
      `-p` 로 줄 프로젝트명과 같은지 맞춘다. 프로젝트명이 다르면 compose 가
      **빈 볼륨을 새로 만들어 붙이고 기존 기록·게스트 토큰이 전부 사라진 것처럼
      보인다**(데이터는 옛 볼륨에 남아 있지만 서비스는 빈 DB 로 뜬다).
- [ ] `.env` 가 `/volume1/docker/chosung-daily/.env` 에 있고 `COMPOSE_PROJECT_NAME`·
      `APP_PORT`·`ENV_FILE` 세 줄이 들어 있는지 확인(`.env.prod.example` 기준).
      compose 가 프로젝트 디렉터리의 `.env` 를 자동으로 읽으므로, `-p` 를 빼고
      `up` 해도 같은 프로젝트에 붙는 안전장치가 된다.
- [ ] `up` 후 `docker compose -p chosung-daily-prod ps` 로 5개 서비스 확인,
      `curl http://127.0.0.1:8089/health` 가 `{"status":"ok"}`.
- [ ] app 컨테이너에서 `uv run flask db upgrade`.
- [ ] Cloudflare Tunnel 이 `http://127.0.0.1:8089` 로 붙는지 확인(앱 포트는
      루프백 바인딩이라 LAN 에서 직접 안 열린다).

## 첫 배포 체크리스트 (develop)

- [ ] 체크아웃 디렉터리 `/volume1/docker/chosung-daily-develop` 생성 후 `develop`
      브랜치 clone.
- [ ] `.env.develop` 작성(`.env.develop.example` 복사). prod 와 **다른** DB
      비밀번호·시크릿을 쓴다.
- [ ] `APP_PORT` 가 prod 와 겹치지 않는지 NAS 에서 확인(기본 8090).
- [ ] `-p chosung-daily-develop --env-file .env.develop` 로 `up` → `docker volume ls`
      에 `chosung-daily-develop_*` 볼륨이 새로 생기고 prod 볼륨은 그대로인지 확인.

## 티켓별 기록

### 19. compose 파라미터화 로컬 검증 (2026-10-13, Docker 29.8.2 / macOS)

NAS 에 올리기 전에 "프로젝트명만 유지하면 기존 볼륨이 그대로 붙는다" 와 "두
인스턴스가 동시에 뜬다" 를 로컬에서 실제로 확인했다. 실제 `.env`·`.env.prod` 는
건드리지 않고, 예시 파일의 임시 복사본을 `--env-file` 로 썼다.

**검증 ① 기존 볼륨 재부착 (기록·토큰 유지)**

1. 변경 전 compose(`git show HEAD:docker-compose.prod.yml`, 고정 `name:`·
   `container_name` 있는 버전)로 `up -d --build` → 컨테이너 `chosung-daily-app-prod`
   등, 볼륨 `chosung-daily-prod_mysql-data` / `_redis-data`.
2. `flask db upgrade` + `seed-words` + `schedule-puzzles --days 2` 후
   `POST /api/v1/guests` 로 게스트 토큰 발급, 오답 1회 제출 → `attempts_left` 4.
3. `down`(**`-v` 없이**) 후 새 compose 로
   `-p chosung-daily-prod --env-file <임시 .env.prod.example 복사본> up -d --build`.
4. 결과: 볼륨 이름이 `chosung-daily-prod_mysql-data` / `_redis-data` 로 **동일**,
   컨테이너 이름만 `chosung-daily-prod-app-1` 식 compose 기본 네이밍으로 바뀜.
   같은 게스트 토큰으로 `GET /api/v1/puzzles/today` 가 200 + `attempts_left` 4 —
   기록·토큰 유지. DB 행: word 20 / guest 1 / attempt 1 / daily_puzzle 2.

**검증 ② prod·develop 동시 기동과 분리**

1. ① 의 prod 를 띄운 채로
   `-p chosung-daily-develop --env-file <임시 .env.develop.example 복사본> up -d --build`.
2. 컨테이너 10개(`chosung-daily-prod-*` 5 + `chosung-daily-develop-*` 5)가 동시에
   뜨고, 포트는 `127.0.0.1:8089` / `127.0.0.1:8090`, 볼륨은
   `chosung-daily-prod_*` / `chosung-daily-develop_*` 로 분리.
3. develop 에서 오답 2회 제출(`attempts_left` 3). prod 는 그대로 4.
   develop 토큰을 8089 에 보내면 401, prod 토큰을 8090 에 보내면 401 — 한쪽 쓰기가
   다른 쪽에 안 보인다. 각 인스턴스 app 컨테이너의 `COMPOSE_PROJECT_NAME` 이
   자기 env 파일 값이라 `ENV_FILE` 라우팅도 확인됨.
4. 두 퍼즐 배정이 서로 독립이라 같은 날 초성도 달랐다(prod ㅎㄱ / develop ㅈㄴ).

검증이 끝난 뒤 두 프로젝트만 `down -v` 로 정리했다. 로컬 개발용 compose 프로젝트
(`chosung-daily`, 볼륨 `chosung-daily_mysql_data`)는 건드리지 않았다.

명령·출력 전문은 `review/impl-evidence-19.md`.

### 21. 매일 백업과 복구 리허설

prod/develop compose 에 `backup` 서비스가 있다. `mysql:8` 이미지를 그대로 써서
(mysqldump·gzip·curl·find 가 다 들어 있다) `TZ=Asia/Seoul` 로 돌고, 매일 04:00
KST 에 `scripts/backup.sh` 를 실행한다 — `mysqldump --single-transaction
--databases chosung_daily --add-drop-database | gzip` → `${BACKUP_DIR}` 에
`chosung_daily-YYYYmmdd-HHMMSS.sql.gz`, 14일치 보존, 실패하면 `SLACK_WEBHOOK_URL`
로 알림.

| | 값 |
|---|---|
| 덤프 위치(호스트) | `${BACKUP_DIR}` → 컨테이너 `/backups` bind mount |
| 보존 | `BACKUP_RETENTION_DAYS` (기본 14) — 오늘 것까지 14개 |
| 실행 시각 | `BACKUP_AT` (기본 04:00, 컨테이너 TZ = KST) |
| 실패 알림 | `SLACK_WEBHOOK_URL` (비우면 알림만 생략, 종료 코드는 그대로 1) |

**NAS 설정 메모**

- `BACKUP_DIR` 은 체크아웃 밖의 공유 폴더를 권장한다(예
  `/volume1/backup/chosung-daily-prod`). 체크아웃 디렉터리를 지워도 덤프는 남는다.
  prod 와 develop 은 **다른 경로**를 준다(기본값이 `./backups` 라 같은 디렉터리에서
  두 인스턴스를 돌리면 덤프가 섞인다).
- **DSM ACL 문제는 해당 없음.** DB 볼륨을 bind mount 로 못 쓰는 이유는 mysql
  컨테이너가 uid 999 로 돌아서 `/volume1` ACL 에 막히기 때문인데, `backup`
  컨테이너는 root(uid 0)로 돌고 쓰는 것도 자기가 만든 덤프 파일뿐이다.
  로컬 검증에서 `id` = `uid=0(root)`, 덤프 소유자 `root:root` 확인.
- 덤프를 꺼낼 때는 컨테이너가 떠 있을 필요가 없다 — DSM File Station 에서
  `BACKUP_DIR` 을 열면 `.sql.gz` 가 그대로 있다.

#### 복구 리허설

운영자가 되돌릴 수 있는지 **실제로 확인하는** 절차다. 사고 전에 한 번 돌려 본다.
`<프로젝트>` 는 `chosung-daily-prod` / `chosung-daily-develop`(docs 위 표).

```bash
# 1. 지금 백업 하나 만든다 (04:00 을 기다리지 않는다)
docker compose -f docker-compose.prod.yml -p <프로젝트> --env-file <env> \
  exec backup /scripts/backup.sh
ls -l <BACKUP_DIR>            # chosung_daily-YYYYmmdd-HHMMSS.sql.gz

# 2. 복구
./scripts/restore.sh <BACKUP_DIR>/chosung_daily-...sql.gz <프로젝트>
#    -y 를 주면 확인 프롬프트를 건너뛴다(비대화 실행은 -y 필수)

# 3. Redis 파생 키 정리는 restore.sh 가 직접 한다 — 따로 할 일 없다.
#    출력에 `[restore] deleted N derived keys` 가 찍힌다.
```

`restore.sh` 는 세 단계다.

1. **덤프 검사** — `gzip -t <덤프>` 로 압축을 끝까지 풀어본다. 끝이 잘린 덤프를
   그냥 `gzip -dc | mysql` 로 흘리면 앞쪽의 `DROP DATABASE` 가 먼저 실행돼서
   *복구 실패가 멀쩡하던 DB 를 날린다*. 그래서 MySQL 에 닿기 전에 여기서 멈춘다.
2. **MySQL 복원** — `gzip -dc` 를 `docker compose -p <프로젝트> exec -T mysql` 의
   stdin 으로 넣는다. 비밀번호는 mysql 컨테이너 안의 `$MYSQL_ROOT_PASSWORD` 를
   쓰므로 호스트 쪽에서 시크릿을 읽지 않는다. 덤프에 `DROP DATABASE IF EXISTS`
   가 들어 있어서 복구 시점 이후에 생긴 행은 사라진다.
3. **Redis 파생 키 무효화** — `redis` 컨테이너에서 `puzzle:*`, `stats:*`, `lb:*`
   를 지운다.

**3 이 왜 필요한가.** Redis 는 MySQL 과 같이 되감기지 않는다. 오늘 퍼즐 캐시
`puzzle:<날짜>` 는 TTL 이 26시간이고 `app/services/puzzle_service.py` 는 캐시가
맞으면 DB 를 아예 안 읽는다. 그래서 복구 후에도 **복구 전 퍼즐의 정답으로
채점**하고, 캐시에 든 퍼즐 id 가 복원된 DB 에 없으면 제출이 FK 오류로 깨진다.
`restart app worker beat` 로는 안 지워진다 — Redis 는 별도 컨테이너라 앱 프로세스
수명과 무관하다(실측: 앱을 새로 띄워도 같은 키가 TTL 93600초로 그대로 있었다).
`stats:`·`lb:` 는 되감긴 attempt 행을 세고 있던 카운터라 복원된 DB 보다 앞서
있어서 같이 지운다 — 그 날의 집계는 0 부터 다시 쌓인다(전날까지의 `DailyStats`
는 MySQL 에 있으니 덤프와 함께 복원된다). `FLUSHDB` 는 쓰지 않는다: 같은 Redis
DB 에 celery 브로커 큐가 들어 있고, rate limit 카운터(60초)는 DB 와 무관하다.

**리허설 실측 (2026-10-13, 티켓 21, macOS / Docker 29.8.2)**

NAS 가 아니라 로컬에서 `docker-compose.prod.yml` 을 전용 프로젝트
`chosung-daily-t21`(포트 8097, 임시 env 파일)로 띄워서 확인했다. 실제 `.env`·
`.env.prod` 는 건드리지 않았고, 검증 후 그 프로젝트만 `down -v` 했다.

1. `db upgrade` + `seed-words` + `schedule-puzzles --days 2`, 게스트 발급 후 오답
   1회 → **상태 A**: word 20 / guest 1 / attempt 1 / daily_puzzle 2,
   `attempts_left` 4.
2. `exec backup /scripts/backup.sh` → `backups/chosung_daily-20261013-214939.sql.gz`
   (2.5KB). 덤프 안에 `/*!40000 DROP DATABASE IF EXISTS chosung_daily*/;` 와
   `CREATE DATABASE`·`USE`·테이블 `DROP TABLE IF EXISTS`·INSERT 들이 있다.
3. 데이터 변경 → **상태 B**: 오답 1회 더(`attempts_left` 3), 단어 1건 INSERT,
   `daily_puzzle` 1건 DELETE → word 21 / attempt 2 / daily_puzzle 1.
4. `./scripts/restore.sh -y backups/chosung_daily-20261013-214939.sql.gz
   chosung-daily-t21` → **상태 A 그대로 복원**: word 20 / guest 1 / attempt 1 /
   daily_puzzle 2, 추가했던 단어 0건. 앱을 재시작하지 않고도 같은 게스트 토큰으로
   `GET /api/v1/puzzles/today` 가 200 + `attempts_left` 4.
5. 보존: 컨테이너 안에서 13·14·15·30일 전 mtime 덤프를 만들고 `backup.sh` 실행 →
   14·15·30일 것만 `pruned`, 13·2일 것과 덤프가 아닌 파일은 그대로.
6. 실패 알림: `MYSQL_HOST=no-such-mysql` 로 실행 → `mysqldump: Got error: 2005`,
   종료 코드 1, 부분 덤프(`.partial`) 안 남음, Slack 으로
   `{"text":"[chosung-daily] MySQL backup failed - db=... host=... - mysqldump
   exited non-zero"}` POST. 웹훅이 안 닿는 주소여도 종료 코드는 1 그대로.
7. 스케줄: `BACKUP_AT` 을 2분 뒤로 주고 `backup-cron.sh` 를 돌려 **그 시각
   정각에** 덤프가 떨어지는 걸 확인(`21:52:00+0900`). 컨테이너 기본 로그는
   `daily at 04:00 +0900, next in 22258s`.

명령·출력 전문은 `review/impl-evidence-21.md`.

### 20. 자동 배포 (`deploy.sh` + GitHub Actions)

#### 무엇이 어떻게 도는가

`main` 푸시는 prod, `develop` 푸시는 develop 에 자동으로 올라간다. CI(`ci.yml`)가
그 브랜치에서 성공했을 때만 `deploy.yml` 이 돌고, 배포 자체는 `deploy/deploy.sh`
한 스크립트가 맡는다 — `git fetch` → **CI 를 통과한 커밋이 아직 브랜치 끝인지 확인**
→ ff-only merge → `compose up -d --build` → app 컨테이너 `flask db upgrade` →
5개 서비스 기동 확인 → `/health` 가 **HTTP 200**(3초 간격 최대 10회, 302 같은
리다이렉트는 실패로 센다). 어느 단계든 실패하면 스크립트가 0 이 아닌 코드로 끝나고
워크플로가 빨갛게 멈춘다.

워크플로는 대상(`prod`/`develop`)과 함께 **CI 를 통과한 커밋 sha** 를 넘긴다. 배포가
도는 사이 같은 브랜치에 새 커밋이 올라왔으면 스크립트가 거기서 멈춘다(빨갛게 끝난다)
— 그 커밋은 자기 CI 가 통과하면 자기 배포로 올라간다. 아직 CI 중이거나 CI 가 실패한
커밋이 운영에 올라가지 않게 하는 장치다.

```bash
# NAS 에서 손으로 돌릴 때 (sha 없이 = 브랜치 끝을 올린다)
/volume1/docker/chosung-daily/deploy/deploy.sh prod

# 특정 커밋만 올리고 싶을 때 (브랜치 끝이 그 커밋이 아니면 멈춘다)
/volume1/docker/chosung-daily/deploy/deploy.sh prod <40자 sha>

# 무엇을 실행할지만 보고 싶을 때 (아무 명령도 실행하지 않는다)
./deploy/deploy.sh prod --dry-run
./deploy/deploy.sh develop --dry-run
```

워크플로는 NAS 에 있는 스크립트를 실행하지 않고 **방금 CI 를 통과한 커밋의
스크립트를 ssh 표준입력으로 흘려보낸다**(`ssh nas 'bash -s -- prod <sha>' < deploy/deploy.sh`).
이유는 README "설계 판단" §20.

#### GitHub Actions secrets

| 이름 | 쓰는 곳 | 값 |
|---|---|---|
| `TAILSCALE_AUTHKEY` | `tailscale/github-action` | Tailscale admin → Settings → Keys 에서 만든 **reusable + ephemeral** auth key. 최대 90일이라 만료 전에 교체해야 한다(만료되면 배포만 빨갛게 실패하고 서비스는 그대로 돈다). |
| `NAS_SSH_PRIVATE_KEY` | ssh | 배포용 ed25519 **개인키 전문**(`-----BEGIN ...` 포함). 암호 없는 키를 쓰고, 이 키는 배포에만 쓴다. |
| `NAS_SSH_HOST` | ssh | NAS 의 tailnet 주소(MagicDNS 이름 또는 100.x.y.z). LAN IP·공개 도메인이 아니다. |
| `NAS_SSH_USER` | ssh | NAS 의 배포 계정 이름. |

레포 → Settings → Secrets and variables → Actions 에 넣는다. 값은 레포·로그·문서에
남기지 않는다(워크플로 로그에는 마스킹돼 찍힌다).

#### D3. 배포 자동화 — NAS 쪽 사람 작업

코드로 할 수 없는 부분. 첫 배포 전에 한 번만 한다.

- [ ] NAS 에 **Tailscale** 패키지 설치 후 tailnet 에 로그인(`tailscale status` 로 확인).
      ACL 에서 GitHub Actions 러너가 쓰는 태그가 NAS 의 22 번에 붙을 수 있는지 확인.
- [ ] 배포용 ssh 키쌍을 **로컬에서** 만들어(`ssh-keygen -t ed25519 -C "gh-actions-deploy"`)
      공개키를 NAS 배포 계정의 `~/.ssh/authorized_keys` 에 등록, 개인키는
      `NAS_SSH_PRIVATE_KEY` secret 으로만 올린다.
- [ ] DSM 에서 해당 계정의 SSH 접속 허용 + `sudo` 없이 `docker` 를 쓸 수 있는지
      확인(Container Manager 설치 계정이면 보통 docker 그룹에 있다).
- [ ] 러너에서 NAS 로 붙는 경로 확인: 로컬에서 `ssh -i <개인키> <user>@<tailnet 주소>
      'docker ps'` 가 되면 워크플로도 된다.
- [ ] 두 체크아웃 디렉터리가 각자 자기 브랜치에 있는지 확인
      (`git -C /volume1/docker/chosung-daily rev-parse --abbrev-ref HEAD` → `main`,
      develop 디렉터리 → `develop`). 스크립트는 브랜치가 다르면 `git pull` 전에 멈춘다.
- [ ] 위 4개 secret 등록 후 `develop` 에 아무 커밋이나 푸시해서 develop 쪽을 먼저
      통째로 리허설한다(prod 가 아니라 develop 으로 먼저).

#### `deploy.sh` 로컬 검증 (2026-10-14, macOS)

NAS 가 없어도 "대상 인자 하나가 설정을 다 고르는지" 와 "실패하면 거기서 멈추는지"
는 확인할 수 있다. 세 가지로 돌렸다.

1. `--dry-run`: `./deploy/deploy.sh prod --dry-run`, `... develop --dry-run` —
   브랜치(main/develop)·디렉터리·`-p` 프로젝트명·`--env-file` 이 전부 대상별로
   갈리고, 실행되는 명령은 0개(가짜 명령도 안 불린다).
2. 가짜 `git`/`docker`/`curl`/`sleep`(`tests/fake_nas_bin/`)을 PATH 앞에 두고
   **실제 실행**: 단계 순서, 체크아웃 디렉터리 없음·브랜치 불일치·pull 실패·
   마이그레이션 실패·서비스 하나 미기동·`/health` 무응답에서 각각 멈추는지,
   `/health` 가 두 번 실패하고 세 번째에 응답할 때는 통과하는지.
3. **docker 만 가짜로 두고 끝까지**: 임시 디렉터리에 `main`/`develop` 체크아웃을
   clone 해 두고(가짜 NAS), 로컬 Flask 를 8189·8190 에 띄운 뒤 두 인자 모두 실행 →
   진짜 `git pull --ff-only` 와 진짜 `curl`(200 + `{"status":"ok"}`)까지 통과.
   compose 조회 명령(`config --services`·`ps --services --filter status=running`·
   `port app 5000`)의 문법·출력 형식은 로컬에서 돌고 있는 개발 compose 프로젝트에
   **읽기 명령만** 보내서 따로 확인했다(그 프로젝트는 건드리지 않았다).

명령·출력 전문은 `review/impl-evidence-20.md`. NAS 실제 기동은 위 D3 체크리스트.

### 09. 법적 문서 — 출시 전 사람이 채울 값

`/privacy`·`/terms` 의 "운영자 정보" 블록은 설정값에서만 값을 읽는다(코드에 지어 넣은
상호·등록번호가 없다 — `tests/test_legal_pages.py::test_business_info_values_are_not_hardcoded`).
지금은 전부 비어 있어서 **서비스명과 연락처만** 렌더된다. 사업자·통신판매업 등록이
끝나면 운영 `.env` 에 아래 값을 넣고 컨테이너를 재기동한다. 값이 있는 항목만 줄이
늘어나므로, 등록이 단계적으로 끝나도 중간 상태로 올려도 된다.

| 환경변수 | 문서 라벨 (ko / en) | 비고 |
|---|---|---|
| `LEGAL_BUSINESS_NAME` | 상호 / Business name | 사업자등록증의 상호 |
| `LEGAL_REPRESENTATIVE` | 대표자 / Representative | |
| `LEGAL_BUSINESS_REG_NO` | 사업자등록번호 / Business registration number | |
| `LEGAL_MAIL_ORDER_REG_NO` | 통신판매업 신고번호 / Mail-order business registration no. | 선택 — 구독 판매 시 필요 |
| `LEGAL_BUSINESS_ADDRESS` | 주소 / Address | 선택 |
| `LEGAL_CONTACT_EMAIL` | 연락처 / Contact | 비워두면 `hsseo@dosaem.com` |

- [ ] 사업자등록 후 위 값을 `.env`(prod)에 넣고 `/privacy?lang=ko`·`?lang=en`,
      `/terms` 두 언어에서 블록이 나오는지 눈으로 확인.
- [ ] 스토어 콘솔(ASC·Play)·Play Data safety 양식의 연락처가 `LEGAL_CONTACT_EMAIL`
      과 같은 주소인지 확인.
- [ ] 본문 내용이 바뀌면 `app/web.py` 의 `LEGAL_EFFECTIVE_DATE` 도 같이 올린다
      (README "법적 문서" 절의 갱신 트리거).
### 12. 구독 검증 — 배포 전 준비물 (2026-10-14)

`POST /subscriptions/verify` 가 동작하려면 배포 때 아래가 **먼저** 있어야 한다.
없으면 엔드포인트가 `STORE_UNAVAILABLE`(503)을 주고 앱은 구매를 완료 처리하지
못한다(스토어가 결제를 되돌린다 — Play 는 3일 내 acknowledge 미완 시 자동 환불).

1. **마이그레이션**: `flask db upgrade` (리비전 `a5bab2f58a7b`, `subscription`
   테이블 추가). 롤백은 같은 리비전의 `downgrade` 로 테이블만 지운다.
2. **환경변수**(`.env.example` `[12]` 절 참고). 값 자체는 이 레포에 넣지 않는다.
   - Apple: `APP_STORE_BUNDLE_ID`, `APP_STORE_APP_APPLE_ID`(App Store Connect
     앱 정보의 숫자 Apple ID — Production 검증기의 필수 인자다),
     `APP_STORE_ISSUER_ID`, `APP_STORE_KEY_ID`,
     `APP_STORE_PRIVATE_KEY`(.p8), `APP_STORE_ROOT_CERT_PATHS`
   - Google: `PLAY_PACKAGE_NAME`, `PLAY_SERVICE_ACCOUNT_FILE`(서비스 계정 JSON 경로)
   - 공통: `SUBSCRIPTION_PRODUCT_ID`(기본 `adfree_monthly`)
3. **서버에 올려야 하는 파일 2개** — 둘 다 컨테이너 안에서 읽을 수 있어야 한다.
   - Apple Root CA 인증서(`.cer`, DER). https://www.apple.com/certificateauthority/
   - Play 서비스 계정 JSON 키 (Play Console > API 액세스)
4. **스토어 쪽 선행 작업**(사람, 스펙 D2): 양 스토어에 구독 상품 `adfree_monthly`
   등록, App Store Connect 의 In-App Purchase 키 발급, Play 서비스 계정에
   "재무 데이터 보기" 권한 부여. Billing Grace Period 를 켜 두지 않으면 `grace`
   상태가 아예 안 온다.

프로덕션 서버도 Sandbox 영수증을 받아들인다(심사용) — 영수증의 `environment` 를
따르고 프로덕션 조회가 "없음" 이면 Sandbox 로 한 번 재조회한다. 그래서 심사
전에 환경을 바꿔 끼우는 작업은 없다.
### 22. Flutter 앱 골격 (`mobile/`) — 사람이 해야 하는 일

코드 쪽은 Firebase 설정 파일·서명 키·스토어 계정이 **없어도** 돈다(`flutter
analyze`·`flutter test`·디버그 실행 모두). 아래는 실기기·배포로 넘어가기 전에
사람이 콘솔에서 해야 하는 일이다. 서명·워크플로는 티켓 32, 스토어 자산은 33.

- [ ] Firebase 콘솔에서 Android 앱(`com.dosaem.chosung`)·iOS 앱(같은 번들 ID)을
      등록하고 설정 파일을 각각 아래 경로에 둔다(둘 다 gitignore 돼 있다).
      자리표시자 `.example` 파일이 같은 자리에 있으니 이름만 맞춰 바꿔 넣으면 된다.
      - `mobile/android/app/google-services.json`
      - `mobile/ios/Runner/GoogleService-Info.plist`
- [ ] **Xcode 에서 `GoogleService-Info.plist` 를 Runner 타깃에 추가**한다(파일을
      디렉터리에 두는 것만으로는 번들에 안 들어간다). 넣기 전에는 앱이 Firebase
      초기화를 건너뛴 채 그대로 뜬다.
- [ ] 한국어 앱 이름은 사람이 할 일이 아니다 — `ko.lproj/InfoPlist.strings` 가
      Runner 타깃 Resources 에 들어 있고(`mobile/test/config/ios_project_test.dart`
      가 지킨다), Android 는 `values-ko/strings.xml` 에 있다. 실기기에서 한국어로
      "오늘의 초성", 영어로 "Hidden Vowels" 가 보이는지만 확인한다.
- [ ] 실기기·스토어 빌드는 `--dart-define=API_BASE_URL=<서버 주소>/api/v1` 로 넘긴다.
      기본값은 Android 에뮬레이터용 로컬 주소라 그대로 쓰면 실기기에서 안 붙는다.
      Sentry 를 켜려면 `--dart-define=SENTRY_DSN=<DSN>` 을 같이 넘긴다(비어 있으면
      초기화하지 않는다). 값 자체는 이 문서에 적지 않는다 — 이름만 둔다.
- [ ] 앱 아이콘·스플래시는 **임시**다(`mobile/assets/icon/`, OVERRIDES §8 콘셉트를
      그대로 그린 자리표시자). 최종본은 티켓 33 에서 만들고, 그때
      `dart run flutter_launcher_icons` + `dart run flutter_native_splash:create` 를
      다시 돌린다.
- [ ] 점검·강제 업데이트 화면(S7)은 서버 `app_setting` 토글로 켠다(티켓 08·16).
      실기기에서 한 번은 `maintenance_enabled` 와 `min_app_version_*` 를 올려
      두 화면이 실제로 뜨는지 확인한다.

### 15. 운영자 페이지 — 출시 전 사람이 채울 값

`/admin` 은 기존 구글 로그인 세션의 **연결된 이메일**로만 판정하고, 허용 목록은
`ADMIN_EMAILS` 설정에만 있다(기본값 없음 — 비워두면 전부 403). 코드에 운영자
이메일이 박혀 있지 않다.

- [ ] 운영 `.env` 에 `ADMIN_EMAILS=dosaem90@gmail.com,hsseo@dosaem.com` 을 넣고
      컨테이너를 재기동한다.
- [ ] 두 계정으로 각각 웹(`https://<도메인>/`)에서 구글 로그인 → `/admin` 진입 확인.
      로그인 전에 `/admin` 으로 들어가면 `/` 로 돌아가며 안내가 뜬다(정상).
- [ ] 운영자 아닌 계정으로 로그인한 브라우저에서 `/admin` 이 403 인지 확인.
- [ ] D0 단어 CSV 를 `/admin/words/import` 로 올려 추가/중복/오류 행 수를 확인한다
      (CSV 포맷·LLM 프롬프트는 README "운영: 단어 CSV 업로드").
### 14. 계정 삭제 — 배포 전 준비물과 수동 확인 (2026-10-14)

1. **마이그레이션**: `flask db upgrade` (리비전 `94a83f12fddb`,
   `apple_revocation_retry` 테이블 추가). 롤백은 같은 리비전의 `downgrade` 로
   테이블만 지운다.
2. **새 환경변수 없음.** 애플 철회는 로그인이 이미 쓰는 값
   (`APPLE_TEAM_ID`·`APPLE_KEY_ID`·`APPLE_PRIVATE_KEY`·`APPLE_CLIENT_ID`·
   `APPLE_APP_BUNDLE_ID`)으로 자격증명을 서명한다 — 비어 있으면 철회를 건너뛰고
   재시도 행만 남는다(7일 뒤 Slack 알림).
3. **Celery Beat 재시작 필요.** 새 스케줄 `retry-apple-revocations`(매일 09:20 KST)
   가 Beat 프로세스에 로드돼야 한다.
4. **Play Data safety 의 "계정 삭제 URL" = `https://chosung.dosaem.com/account/delete`**
   (웹 삭제 URL). 앱 내 삭제 경로는 설정 화면의 "계정 삭제"(`DELETE /api/v1/me`,
   티켓 29). 두 값을 Play Console 의 데이터 삭제 섹션에 그대로 적는다. App Store
   심사(가이드라인 5.1.1(v))도 같은 URL 과 앱 내 경로를 본다.

**수동 체크리스트 (웹, 배포한 환경에서 1회)**

- [ ] `/account/delete` 를 **로그인/방문 기록 없는 브라우저**(시크릿 창)로 열면
      삭제 버튼이 없고 안내 + 운영자 메일만 보인다.
- [ ] 같은 창에서 `/` 를 한 번 열고(게스트 발급 + 세션 동기화) 다시
      `/account/delete` 로 가면 확인 폼이 보인다. ko/en 전환(`?lang=`)도 확인.
- [ ] 삭제를 누르면 `/` 로 돌아오고, **새 게스트로 시작한다**: 보드가 비어 있고
      개발자 도구 Application > Local Storage 의 `chosung_token` 이 새 값이며
      `chosung_history_*` 가 지워져 있다. 주소창에 `?deleted=1` 이 남지 않는다.
- [ ] 삭제 **뒤** `/api/v1/me/stats` 를 옛 토큰으로 부르면 401 이다(삭제 전에
      토큰을 복사해 두고 확인). 삭제 전에는 정상적으로 200 이다.
- [ ] 멀쩡한 게스트로 플레이하던 창에서 주소창에 `/?deleted=1` 을 직접 넣어 열면
      `chosung_token` 과 `chosung_history_*` 가 **그대로** 남는다(외부 링크로
      들어온 가짜 신호 — 삭제가 확인되지 않으면 아무것도 버리지 않는다).
- [ ] `/account/delete` 확인 폼을 열어 둔 채 다른 탭에서 백업 코드로 다른 게스트를
      복원한 뒤 옛 탭의 삭제 버튼을 누르면 403 이고 아무 계정도 지워지지 않는다.
- [ ] 애플로 로그인한 게스트를 지운 뒤, **애플 ID 설정 > Apple ID 를 사용하는 앱**
      에서 이 앱이 사라졌는지 확인한다(실제 애플 계정이 필요해서 테스트가 아니라
      사람이 본다). 남아 있으면 `apple_revocation_retry` 테이블에 행이 있는지 보고
      Beat 로그를 확인한다.

### 23. 배정표·잔량·점검 토글·책 검색 — 출시 전 사람이 확인할 것

- [ ] `/admin/schedule` 에서 ko/en 탭이 각각 30일을 보여주고, 빈 날짜가 "자정에 배정"
      으로 뜨는지 본다. 자정 Beat 가 한 번 돈 뒤면 대부분 채워져 있어야 정상이다.
- [ ] 잔량 카드가 14일치 미만일 때 경고로 바뀌는지 확인하고, 그 상태에서 Slack 잔량
      알림도 오는지(같은 임계값) 같이 본다.
- [ ] 내일 날짜의 단어를 한 번 교체해보고, 앱·웹에서 그 날짜 퍼즐이 바뀐 단어로
      나오는지 본다(캐시 무효화 확인). 오늘 날짜는 시도가 있으면 교체 버튼이 없다.
- [ ] `/admin/settings` 에서 점검 모드를 켜고 `GET /api/v1/config` 를 바로 호출해
      `maintenance.enabled=true` 와 메시지가 즉시 보이는지 확인한 뒤 **반드시 끈다**.
      최소 앱 버전도 올려 S7 강제 업데이트 화면을 한 번 확인하고 되돌린다.
- [ ] `GOOGLE_BOOKS_API_KEY` 는 선택이다. 키 없이 `/admin/books` 검색이 되는지 먼저
      보고, 쿼터 오류(429)가 나기 시작하면 그때 GCP 에서 키를 만들어 운영 `.env` 에
      넣고 재기동한다(값은 이 문서에 적지 않는다 — 이름만 둔다).
- [ ] 책 검색으로 넣은 en `book_title` 단어가 일요일 라운드에 실제로 뽑히는지
      (`flask schedule-puzzles --language en`) 한 번 확인한다.
### 34. 앱 배포 (`.github/workflows/flutter.yml` + 서명)

`develop` 푸시는 Android APK 를 **Firebase App Distribution**, iOS 를 **TestFlight** 로
보내고, `main` 푸시는 Android AAB 를 **Play internal 트랙**, iOS 를 **TestFlight** 로
보낸다. App Store·Play 프로덕션 승격은 콘솔 버튼(사람)이다. 분석·테스트는
`flutter-ci.yml`(ubuntu-latest)이 그대로 맡고, 이 워크플로는 서명·업로드만 한다 —
러너가 사용자 맥 한 대(`self-hosted`)라서 PR 마다 그 맥을 묶지 않으려고 나눴다.
구조는 BASELINE(`~/Code/Habitopia` 의 하위 디렉터리 레포 변형 + BuildUrPalace 의
AAB 검증)을 복사해 식별자만 바꿨다.

| | develop 푸시 | main 푸시 |
|---|---|---|
| Android 산출물 | APK (`flutter build apk --release`) | AAB (`flutter build appbundle --release`) |
| Android 대상 | Firebase App Distribution, 그룹 `testers` | Play **internal** 트랙 (`com.dosaem.chosung`) |
| iOS 대상 | TestFlight (`xcrun altool`) | TestFlight |
| 서버 주소 | `API_BASE_URL_DEV` (develop 인스턴스, 8090) | `API_BASE_URL_PROD` |

`workflow_dispatch` 로 손으로 돌릴 수도 있고, `platform` 입력으로 한쪽 플랫폼만
고를 수 있다. 사람이 맥에서 직접 올릴 때는 fastlane lane 을 쓴다 —
`mobile/android/fastlane`(`beta`=internal 초안, `release`=production 초안),
`mobile/ios/fastlane`(`beta`=TestFlight, `release`=App Store). 메타데이터·스크린샷
(`fastlane/metadata/`)은 티켓 35 가 넣는다.

#### GitHub Actions secrets

레포 → Settings → Secrets and variables → **Secrets**. 값은 레포·로그·문서에
남기지 않는다(이름만 둔다).

| 이름 | 쓰는 곳 | 값 |
|---|---|---|
| `KEYSTORE_BASE64` | Android 서명 | 업로드 keystore(`.jks`)를 `base64` 로 인코딩한 전문. 없으면 워크플로가 빌드 전에 멈춘다(디버그 키로 서명된 APK 가 스토어로 가는 걸 막는다). |
| `KEYSTORE_PASSWORD` | Android 서명 | keystore 비밀번호 |
| `KEY_ALIAS` | Android 서명 | 키 별칭(예 `upload`) |
| `KEY_PASSWORD` | Android 서명 | 키 비밀번호 |
| `GOOGLE_PLAY_KEY_JSON` | Play 업로드 | Play Console 서비스 계정 JSON **전문**. "앱 출시 관리" 권한 필요. |
| `FIREBASE_APP_ID` | App Distribution | Firebase 콘솔 Android 앱의 App ID (`1:...:android:...`) |
| `FIREBASE_SERVICE_ACCOUNT` | App Distribution | Firebase 서비스 계정 JSON 전문(`firebaseappdistro.admin`) |
| `GOOGLE_SERVICES_JSON_BASE64` | Android 빌드 | `google-services.json`(D0)을 base64 로. **없으면 경고만 내고 Firebase 없이 빌드한다**(Gradle 플러그인·런타임 초기화 모두 건너뛰는 경로). |
| `GOOGLE_SERVICE_INFO_PLIST_BASE64` | iOS 빌드 | `GoogleService-Info.plist`(D0)을 base64 로. Runner 타깃에 파일을 추가하는 것은 사람(위 "22.")이고, 추가한 뒤에는 파일이 없으면 Xcode 빌드가 죽으므로 CI 는 이 secret 으로 파일을 만든다. |
| `APP_STORE_CONNECT_API_KEY` | match·altool | ASC API 키 JSON(`key_id`/`issuer_id`/`key`). `key` 는 `.p8` 전문. |
| `MATCH_PASSWORD` | fastlane match | match 저장소 암호화 비밀번호 |
| `MATCH_GIT_BASIC_AUTHORIZATION` | fastlane match | `match-certs` 레포를 읽을 PAT 를 `user:token` 으로 base64 인코딩한 값 |
| `FLUTTER_SENTRY_DSN` | 빌드 | 앱용 Sentry DSN(`--dart-define=SENTRY_DSN`). 비워 두면 앱이 Sentry 를 초기화하지 않는다. |

인증서·프로파일 저장소는 **`github.com/dosaem/match-certs`**(`mobile/ios/fastlane/Matchfile`)
이고, CI 는 `fastlane match appstore --readonly` 로만 읽는다 — 인증서를 새로 만드는
것(`match appstore` 쓰기)은 사람이 로컬에서 한 번 한다. App Distribution 테스터
그룹 이름은 `testers` 로 고정이라 Firebase 콘솔에 **같은 이름의 그룹**이 있어야 한다.

#### GitHub Actions variables

같은 화면의 **Variables** 탭. 앱 바이너리에 그대로 들어가는 공개 식별자라 secret
으로 두지 않는다(마스킹해도 APK 를 뜯으면 보인다). 서버 주소가 비어 있으면 빌드가
멈춘다 — 빈 주소로 빌드된 앱은 테스터 손에서만 깨지기 때문이다.

| 이름 | 값 |
|---|---|
| `API_BASE_URL_PROD` | prod 서버의 API 루트 — `https://chosung.dosaem.com/api/v1` |
| `API_BASE_URL_DEV` | develop 인스턴스(8090)의 API 루트. NAS DNS·터널 작업(D3) 뒤에 정해지므로 워크플로에 하드코딩하지 않았다. |
| `GOOGLE_SERVER_CLIENT_ID` | GCP **웹** 클라이언트 ID(`serverClientId`, D0). Android `google_sign_in` 과 `POST /auth/token-exchange` 가 같은 값을 본다. |
| `ADMOB_BANNER_AD_UNIT_ID_ANDROID` | AdMob Android 앱의 배너 유닛 ID |
| `ADMOB_INTERSTITIAL_AD_UNIT_ID_ANDROID` | 〃 전면 유닛 ID |
| `ADMOB_REWARDED_AD_UNIT_ID_ANDROID` | 〃 보상형 유닛 ID |
| `ADMOB_BANNER_AD_UNIT_ID_IOS` | AdMob iOS 앱의 배너 유닛 ID |
| `ADMOB_INTERSTITIAL_AD_UNIT_ID_IOS` | 〃 전면 유닛 ID |
| `ADMOB_REWARDED_AD_UNIT_ID_IOS` | 〃 보상형 유닛 ID |

#### 빌드에 넘어가는 `--dart-define`

워크플로가 잡별로 `DART_DEFINES` 를 만들어 모든 `flutter build` 에 넘긴다. 광고
유닛은 플랫폼마다 다른 값이지만 **앱이 읽는 이름은 한 벌**이라, 자기 플랫폼 변수만
그 이름으로 넘긴다(Dart 코드에 플랫폼 분기가 생기지 않는다). 광고·로그인 티켓
(31·29)은 아래 이름을 그대로 읽는다.

| dart-define | 출처 | 읽는 곳 |
|---|---|---|
| `API_BASE_URL` | 브랜치별 variable | `mobile/lib/config/app_env.dart` |
| `SENTRY_DSN` | secret | `mobile/lib/config/app_env.dart` |
| `GOOGLE_SERVER_CLIENT_ID` | variable | 티켓 29 (계정 연결) |
| `ADMOB_BANNER_AD_UNIT_ID` | 플랫폼별 variable | 티켓 31 (광고) |
| `ADMOB_INTERSTITIAL_AD_UNIT_ID` | 플랫폼별 variable | 티켓 31 |
| `ADMOB_REWARDED_AD_UNIT_ID` | 플랫폼별 variable | 티켓 31 |

손으로 fastlane lane 을 돌릴 때는 Actions 가 넘기던 값을 **환경변수로 직접** 줘야
한다 — 이름은 위 표의 dart-define 과 같다. 하나라도 비어 있으면 lane 이 빌드 전에
멈춘다(빈 주소·빈 광고 ID 로 빌드된 바이너리가 스토어로 가는 걸 막는다). 광고 유닛은
**올리려는 플랫폼의 값**을 그 이름으로 넣는다(위 variables 표의 `..._ANDROID` /
`..._IOS` 중 하나). `SENTRY_DSN` 만 비워 둘 수 있다.

```sh
cd mobile/android   # iOS 는 mobile/ios
API_BASE_URL=https://chosung.dosaem.com/api/v1 \
GOOGLE_SERVER_CLIENT_ID=... \
ADMOB_BANNER_AD_UNIT_ID=... \
ADMOB_INTERSTITIAL_AD_UNIT_ID=... \
ADMOB_REWARDED_AD_UNIT_ID=... \
  fastlane beta
```

Android lane 은 빌드 전에 이전 `app-release.aab` 를 지우고, 빌드 뒤 새 AAB 를
`mobile/tool/verify_appbundle.py` 로 검사한다(온전한 zip + 배포 lib 스트립 확인).
`flutter build appbundle` 이 스트립 오탐으로 exit 1 을 줘도 넘기기 때문에, 그 검사가
없으면 진짜 빌드 실패 뒤 **지난 빌드의 AAB** 가 스토어로 올라간다. 검사는 `python3`
를 쓴다. Actions 의 AAB 스텝도 같은 스크립트를 쓴다.

#### D2. 앱 배포 — 사람이 해야 하는 일

코드로 할 수 없는 부분이다. 이 티켓의 워커가 확인한 것은 **D0·D2 산출물이 없는
상태에서 `flutter build apk --debug` 가 되는 것**까지다(Firebase 스킵 경로,
`review/impl-evidence-34.md`). 아래가 끝나기 전에는 `--release`·`build ipa` 와
실제 업로드가 돌지 않는다.

- [ ] **업로드 keystore 생성**(사람, 로컬): `keytool -genkey -v -keystore
      upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`.
      `.jks` 와 비밀번호는 레포에 넣지 않고 위 4개 secret 으로만 올린다.
      잃어버리면 Play 업로드 키 재설정(구글 문의)이 필요하다.
- [ ] Firebase 콘솔에서 Android·iOS 앱 등록 후 설정 파일 2개를 base64 로 secret 에
      등록(위 "22." 의 로컬 파일과 같은 내용). App Distribution 에 **`testers`**
      그룹을 만들고 본인 계정을 넣는다.
- [ ] Play Console 에 앱 생성 + 서비스 계정 초대. **첫 AAB 는 콘솔에 손으로 한 번
      올려야** API 업로드가 열린다(패키지가 등록되기 전에는 API 가 404 를 준다).
- [ ] App Store Connect 앱 생성(번들 ID `com.dosaem.chosung`), ASC API 키 발급,
      `match-certs` 레포 접근 권한 확인 후 로컬에서 `fastlane match appstore` 로
      인증서·프로파일을 **한 번 생성**(CI 는 `--readonly`).
- [ ] 이 레포에 self-hosted 러너 등록(`Settings → Actions → Runners`). 러너 맥에
      Xcode·CocoaPods·fastlane·`jq`·`python3`·Node(npx)가 있어야 한다.
- [ ] 위 secrets·variables 등록 후 **`develop` 에 먼저 푸시**해서 App Distribution·
      TestFlight 경로를 리허설한다(`main` 이 아니라 develop 으로 먼저).
- [ ] TestFlight·Play internal 에 본인을 테스터로 추가. 스토어 제출·출시 버튼은
      스크린샷·메타데이터(티켓 35)와 앱 콘텐츠 설문(D3) 뒤에.
- [ ] 버전은 `mobile/pubspec.yaml` 의 `version:` 하나에서 온다(`1.0.0+1`). 같은
      빌드 번호를 두 번 올리면 TestFlight·Play 가 거부하므로 올릴 때마다 `+N` 을
      올린다(자동 증가는 넣지 않았다 — 레포의 값과 스토어의 값이 갈라지지 않게).
### 16. 출시 전 사람이 확인할 법적 항목 (2026-10-14)

`docs/legal-checklist.md` 가 조문 → 문서 절 → 테스트를 묶어 두지만, **법률 판단은
테스트가 못 한다.** 아래는 사람이 출시 전에 확인·결정할 항목이다. 워커(에이전트)가
조문을 읽고 매핑한 결과라는 점을 전제로 본다.

**사용자 확인 결과 (2026-10-14, 스펙 미정 21)**

| 항목 | 결정 | 구현 |
|---|---|---|
| 사업장 주소(자택) 공개 범위 | **(b) 시·구까지만 표시 + "상세 주소는 요청 시 이메일로 제공"** | `LEGAL_BUSINESS_ADDRESS` 에 사람이 축약한 값을 넣는다(코드가 자르지 않음). 값이 있을 때만 조각이 안내 문구를 함께 렌더 |
| 공개용 전화번호 | **(b) 설정값 자리만 두고 나중에 채움** | `LEGAL_BUSINESS_PHONE` — 비면 그 행을 렌더하지 않음 |
| 개인정보 보호책임자 표기 | **(b) 직책 "운영자" + 이메일** | `privacy#officer`. 성명을 공개하려면 `LEGAL_PRIVACY_OFFICER` 만 채운다 |

**체크박스**

- [ ] **통신판매업 신고 대상 여부** (구독 판매 전). 면제 기준(직전년도 통신판매 거래
      횟수·간이과세자 여부 등)을 관할 시·군·구 또는 공정위 안내로 확인한다. 신고하면
      신고번호를 prod `.env` 의 `LEGAL_MAIL_ORDER_REG_NO` 에 넣는다 — 비어 있으면
      그 행은 렌더되지 않는다(스펙 미정 22).
- [ ] **축약 주소 표시의 적법성 확인.** 전자상거래법 제10조 제1항 제2호는 "영업소가
      있는 곳의 주소" 를 요구하고 축약을 허용하는 규정이 없다. 또 스토어(Apple/Google)가
      결제·판매 주체인 구조에서 운영자를 제13조의 "통신판매업자" 로 볼지에 해석 여지가
      있고, 그 해석에 따라 표시 의무 범위가 달라진다. 위 (b) 결정은 이 전제 아래 둔 것이라
      출시 전에 확인이 필요하다.
- [ ] **개인정보 보호책임자 지정.** 1인 사업자는 지정하지 않으면 사업주가 보호책임자가
      된다(개인정보 보호법 제31조 제6항). 현재 문서는 직책 "운영자" + 이메일로 표기한다 —
      그대로 갈지, 성명을 공개할지 확인한다.
- [ ] **필요 시 전문가 검토** (변호사·행정사). 최소한 위 두 항목(통신판매업 신고,
      주소 표시)과 국외 이전 고지 방식(별도 동의 없이 처리방침 공개로 가는
      제28조의8 제1항 제3호 경로)을 함께 본다.
- [ ] **ASC EULA 설정.** Apple 표준 EULA 를 쓰기로 결정했으므로(미정 9 해소)
      App Store Connect 의 "라이선스 계약" 에 **아무것도 입력하지 않는다** — 커스텀
      약관을 넣으면 그게 표준을 대체한다. 약관 `#eula` 절이 표준 EULA 를 링크한다.
- [ ] **Play Data safety 답안과 방침 일치.** 수집 항목(게스트 토큰·계정 이메일·시도
      기록·구독 식별자·광고 ID·오류 로그), 삭제 URL(`/account/delete`), 데이터 공유
      대상(Google·Apple·AdMob·Firebase·Sentry)이 `/privacy` 의 `#collection`·
      `#third-parties`·`#processors`·`#overseas` 절과 같은지 한 줄씩 대조한다.
- [ ] **스토어 구독 고지 일치.** ASC·Play 콘솔의 구독 설명과 약관 `#subscription` 절의
      가격·결제 주기·자동 갱신·해지 경로가 같은지 확인한다(Apple 3.1.2(a),
      Google Play 구독 정책).
- 접속기록 보관 구성과 백업 덤프 암호화는 **티켓 36 에서 구현했다** — 사람이 할 일(키 생성·
      보관, 월 1회 점검, `LOG_DIR`·`BACKUP_ENCRYPTION_CERT_FILE` 설정)은 아래 "### 36." 에 있다.
- [ ] 위 값을 채운 뒤 `/privacy?lang=ko|en`·`/terms?lang=ko|en` 에서 "운영자 정보"
      블록을 눈으로 확인하고, 본문을 고쳤으면 `app/web.py` 의 `LEGAL_EFFECTIVE_DATE`
      를 올린다.

### 36. 개인정보 안전성 확보조치 — 백업 암호화 키와 접속기록 점검

근거: **개인정보의 안전성 확보조치 기준**(개인정보보호위원회 고시 제2023-6호) 제8조
(접속기록의 보관 및 점검)·제7조(개인정보의 암호화). 조문 → 문서 절 → 테스트 매핑은
`docs/legal-checklist.md` "1-1." 절. 구현 근거는 README "설계 판단 36.".

#### (a) 백업 덤프 암호화 — 키 생성·보관·교체

덤프는 `mysqldump | gzip | openssl cms -encrypt` 로 **공개키(CMS 봉투) 암호화**해서
`chosung_daily-YYYYmmdd-HHMMSS.sql.gz.enc` 로만 떨어진다. 평문 덤프는 임시 파일로도
안 남고, `BACKUP_ENCRYPTION_CERT_FILE` 이 비어 있으면 **백업을 만들지 않고 실패한다**
(Slack 알림). `age` 를 쓰지 않은 이유는 README "설계 판단 36.".

```bash
# 1. 키 쌍을 만든다 — NAS 가 아니라 운영자 로컬(또는 오프라인 머신)에서 한다.
openssl req -x509 -newkey rsa:4096 -nodes -days 7300 \
  -keyout chosung-backup-key.pem -out chosung-backup-cert.pem \
  -subj "/CN=chosung-daily backup $(date +%Y)"

# 2. 공개키 인증서만 NAS 로 올린다 (BACKUP_DIR 안에 둔다 — 이미 bind mount 돼 있다).
#    scp chosung-backup-cert.pem nas:/volume1/backup/chosung-daily-prod/backup-cert.pem
#    prod .env:
#      BACKUP_ENCRYPTION_CERT_FILE=/backups/backup-cert.pem

# 3. 개인키(chosung-backup-key.pem)는 NAS 에 두지 않는다. 아래 "키 보관" 참고.

# 4. 확인: 덤프를 하나 만들고 복호화해 본다(복구 리허설 전 최소 확인).
docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env \
  exec backup /scripts/backup.sh
openssl cms -decrypt -binary -inform DER -inkey chosung-backup-key.pem \
  -in <덤프>.sql.gz.enc | gzip -dc | head -5
```

**키 보관 (사람)**

- [ ] 개인키를 **NAS 밖 두 곳**에 둔다: ① 운영자 비밀번호 관리자(파일 첨부) ② 오프라인
      사본(암호화한 USB 또는 인쇄). 레포·NAS·Slack·메일에 올리지 않는다.
- [ ] **개인키를 잃으면 모든 백업을 복구할 수 없다.** 암호화된 덤프는 다른 어떤 방법으로도
      열리지 않는다 — 이 경고를 두 보관처에 메모로 같이 남긴다.
- [ ] 공개키 인증서(`backup-cert.pem`)는 공개 정보다. 잃어버리면 같은 개인키로 다시 만들
      수 있으므로 백업 대상이 아니다.

**키 교체 절차 (사람)**

- [ ] 새 키 쌍을 만들고 새 공개키를 `BACKUP_ENCRYPTION_CERT_FILE` 로 바꾼 뒤 `backup`
      컨테이너를 재시작한다. 그 시점부터 새 덤프는 새 키로 암호화된다.
- [ ] **구 개인키는 구 덤프의 보존 기간(`BACKUP_RETENTION_DAYS`, 기본 14일)이 끝날 때까지
      유지한다.** 그 전에 버리면 그 기간의 덤프가 복구 불가가 된다.
- [ ] 교체 후 복구 리허설을 한 번 더 돌린다(아래).

**복구 리허설 (암호화 기준)**

"### 21. 매일 백업과 복구 리허설" 의 절차를 그대로 쓰되, 2번 복구 단계에 개인키를 준다.
그 절의 실측 기록(2026-10-13)은 평문 덤프 기준이므로, 아래로 한 번 더 돌린 결과를 남긴다.

```bash
./scripts/restore.sh -y -k chosung-backup-key.pem \
  <BACKUP_DIR>/chosung_daily-...sql.gz.enc <프로젝트>
# 또는 BACKUP_DECRYPTION_KEY_FILE=... ./scripts/restore.sh -y <덤프> <프로젝트>
```

- [ ] 암호화 덤프로 복구 리허설을 1회 수행하고 결과를 이 절에 적는다(상태 A → 변경 →
      복구 → 상태 A). 키 없이 돌리면 **MySQL 을 건드리기 전에** 멈추는 것도 같이 확인한다.
- [ ] **전환기 정리.** 암호화 전에 뜬 평문 `.sql.gz` 덤프도 `restore.sh` 가 당분간 복원한다.
      그 덤프가 보존 기간이 지나 사라지면(= `BACKUP_DIR` 에 `.sql.gz` 가 0개) `restore.sh`
      의 평문 경로와 `backup.sh` 보존 정리의 `.sql.gz` 패턴을 뺀다.

#### (b) 접속기록 — 설정과 월 1회 점검

| | 값 |
|---|---|
| 접근 로그 파일 | 호스트 `${LOG_DIR}`(기본 `./logs`) ← 컨테이너 `/logs`, `gunicorn.conf.py` 가 `access.log` 로 기록 |
| 감사 로그(DB) | `access_log` 테이블 — 개인정보 처리 행위만(README "설계 판단 36." 의 표) |
| 보관 기간 | `ACCESS_LOG_RETENTION_DAYS` (기본 **365** = 고시 제8조 제1항의 법정 최소 1년) |
| 만료 삭제 | DB: Beat 매일 04:10 (`tasks.purge_access_logs`) / 파일: backup 컨테이너 cron 이 일 회전·gzip 후 같은 기간으로 삭제 |
| 점검 | `flask access-log report --month YYYY-MM` · `flask access-log verify` |
| 실패 알림 | `SLACK_WEBHOOK_URL` (DB 삭제 실패는 `notify_operator`, 파일 회전 실패는 스크립트가 직접) |

**NAS 설정 메모**

- `LOG_DIR` 은 `BACKUP_DIR` 과 같은 방식으로 체크아웃 밖의 공유 폴더를 권장한다(예
  `/volume1/backup/chosung-daily-prod-logs`). prod·develop 에 **다른 경로**를 준다.
- **DSM ACL 문제는 해당 없음** — app 컨테이너는 root 로 돌고(`Dockerfile` 에 `USER` 가
  없다) backup 컨테이너도 root 다(§21 메모와 같은 이유).
- `LOG_DIR` 이 쓰기 불가면 Gunicorn 이 **기동하면서 죽는다**(접속기록이 조용히 빠지는
  쪽보다 배포 시점에 멈추는 쪽을 골랐다). 첫 배포 때 `docker compose logs app` 으로
  확인한다.
- `.env` 의 `LOG_DIR` 은 **호스트 경로 전용**이다. 컨테이너 안에서 Gunicorn·회전
  스크립트가 보는 경로는 compose 의 `environment:` 가 `/logs`(마운트 target)로 고정한다
  — 호스트 경로가 컨테이너까지 흘러가면 Gunicorn 이 WORKDIR(`/srv`) 기준 상대 경로에
  써서 마운트 밖에 쌓인다.

**사람이 할 일**

- [ ] prod·develop `.env` 에 `LOG_DIR` 을 넣고 그 폴더를 만든다(`ACCESS_LOG_RETENTION_DAYS`
      는 비워 두면 365).
- [ ] 첫 배포 직후 **호스트 쪽** `LOG_DIR` 에 `access.log` 가 실제로 생겼는지 본다.
      컨테이너 안에만 있으면 마운트 밖에 쌓이는 것이라 보관·회전이 전부 안 걸린다.

      ```bash
      docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env \
        exec app sh -c 'echo $LOG_DIR; ls -l /logs'   # /logs 와 access.log
      ls -l "$LOG_DIR"                                 # 호스트에서도 같은 파일이 보인다
      ```
- [ ] **매월 1회 점검** — 지난달 보고서를 돌리고 결과(총 건수·거부 건수·체인 검증)를
      운영 기록에 보관한다. 고시 제8조 제2항이 요구하는 "월 1회 이상 점검" 이다.
      거부 건수가 평소와 다르거나 체인이 끊겼으면 원인을 확인한다.

      ```bash
      docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env \
        exec app uv run flask access-log report --month 2026-10
      docker compose -f docker-compose.prod.yml -p chosung-daily-prod --env-file .env \
        exec app uv run flask access-log verify
      ```
- [ ] **정보주체 5만명을 넘기면** `ACCESS_LOG_RETENTION_DAYS=730` 으로 올리고 방침
      `#collection`·`#security` 의 "1년(365일)" 문구와 `docs/legal-checklist.md` "1-1." 을
      같이 고친다(고시 제8조 제1항 단서). 고유식별정보·민감정보를 처리하기 시작하면
      규모와 무관하게 2년이다.
- [ ] **현행 고시 조 번호 확인.** 위 번호는 고시 제2023-6호(시행 2023. 9. 22.) 기준이다.
      2025-10 개정에서 접속기록 조항이 유예 대상으로 들어가 조 번호가 바뀔 수 있다 —
      출시 전에 국가법령정보센터 현행 고시로 §8 번호를 확인하고, 바뀌었으면 방침·
      `docs/legal-checklist.md`·README 의 인용을 갱신한다(보관 기간 1년/2년은 같다).
### 18. 웹 메인 페이지 — 출시 전 사람이 채울 값

메인 페이지의 앱 설치 CTA(App Store / Google Play 배지)와 iOS Smart App Banner 는
**설정값이 비어 있으면 아예 렌더되지 않는다**(`app/web.py` 의 `index`, `web/templates/index.html`).
스토어에 앱을 올린 뒤 `.env` 에 채운다 — 코드 변경은 필요 없다.

- [ ] `STORE_URL_IOS` — App Store 제품 페이지 URL. 비면 iOS 배지 없음.
- [ ] `STORE_URL_ANDROID` — Play 스토어 제품 페이지 URL. 비면 Android 배지 없음.
- [ ] `APP_STORE_ID` — App Store 숫자 ID. 비면 `<meta name="apple-itunes-app">` 를
      내보내지 않는다(빈 `app-id=` 를 내면 Safari 가 "앱 없음" 배너를 그린다).
- [ ] **공식 배지 아트워크로 교체.** 지금 배지는 스토어 이름을 적은 텍스트 버튼이다 —
      Apple/Google 의 배지 이미지는 각 사의 마케팅 가이드라인(크기·여백·언어별 파일)에
      묶여 있어서 레포에 임의로 그려 넣지 않았다. 출시 때 공식 배지를 받아
      `web/static/` 에 두고 `.store-badge` 안의 텍스트를 `<img>` 로 바꾼다.
      교체해도 "설정값이 비면 안 그린다" 규칙은 그대로 둔다.
- [ ] 공유 텍스트의 링크(`https://chosung.dosaem.com/?utm_source=share`,
      `web/static/app.js` 의 `SHARE_URL`)가 실제 운영 도메인과 같은지 확인한다.

### 30. 로컬 알림 — 실기기 체크리스트 (사람이 실행)

알림은 **OS 가 예약을 들고 있다가 앱이 꺼져 있을 때 띄우는 것**이라 위젯 테스트로는
여기까지 못 본다(테스트는 플러그인 경계를 가짜로 바꾼다). 예약 계획·취소 규칙·diff 는
`mobile/test/notifications/` 가 덮고, 아래는 **실제 기기에서 눈으로** 확인한다.
iOS·Android 각각 한 번씩. 기기 시계를 당기지 말고(예약이 밀린다) 설정 시각을 당겨서 본다.

- [ ] **일일 알림이 온다.** 온보딩에서 알림을 허용하고, S4 "일일 알림" 을 **다음 30분
      눈금**(목록이 30분 단위다 — 지금이 14:12 면 14:30)으로 바꾼 뒤 앱을 **종료**한다.
      그 시각에 "오늘 퍼즐 풀었어요?" 가 뜬다(Android 는 inexact 라 몇 분 늦을 수
      있다 — 10분까지는 정상이다).
- [ ] **정답을 맞힌 날은 20:00 리마인더가 없다.** 퍼즐을 풀고(또는 5회 소진) S4 에서
      "일일 알림" 을 **20:30** 으로 바꿔 두 알림의 차이를 본다 — 20:00 리마인더는 안 오고
      20:30 일일 알림만 온다. (그 날짜의 리마인더만 취소되는지가 핵심이다. 일일 알림을
      20:00 으로 맞추면 리마인더가 아예 안 걸리니 이 확인에는 쓰지 않는다.)
- [ ] **다음 날 20:00 리마인더는 그대로 온다.** 위 상태로 하루를 넘겨 다음 날
      20:00 에 "아직 안 풀었어요" 가 오는지 본다(그 날 퍼즐을 풀지 않은 채로 둔다).
- [ ] **앱 종료 상태에서 탭(cold).** 앱을 완전히 종료한 뒤 알림을 탭하면 오늘 탭이
      열리고 보드가 **그 날짜 퍼즐**로 뜬다(전날 보드가 남아 있지 않다).
- [ ] **백그라운드에서 탭(warm).** 내 기록 탭을 열어 둔 채 홈으로 나갔다가 알림을
      탭하면 오늘 탭으로 옮겨가고 퍼즐을 다시 읽는다.
- [ ] **권한을 끄면 안내가 뜬다.** 시스템 설정에서 이 앱의 알림을 끄고 앱으로
      돌아오면 S4 "일일 알림" 아래에 "알림 꺼짐 — 시스템 설정에서 켜기" 가 뜨고,
      누르면 **이 앱의 알림 설정 화면**이 열린다(iOS: 설정 > 오늘의 초성,
      Android: 앱 알림 설정). 다시 켜고 돌아오면 안내가 사라지고 예약이 복구된다.
- [ ] **재부팅 후에도 예약이 남는다.** 기기를 재부팅하고 앱을 **열지 않은 채** 다음
      일일 알림 시각을 기다린다(`RECEIVE_BOOT_COMPLETED` + 플러그인 부트 리시버).
- [ ] **시간대를 옮기면 따라온다.** 기기 시간대를 미국 동부 등으로 바꾸고 앱을 한 번
      열었다 닫으면, 알림이 **새 시간대의** 설정 시각에 온다. 이때 "그 날 풀었음"
      판정은 KST 날짜 기준이라, 로컬 20:00 이 KST 로 다음 날인 지역에서는 그 다음 날
      퍼즐을 푼 뒤에 리마인더가 사라진다(의도된 동작).
- [ ] **대기 개수는 최대 8개**(일일 1 + 리마인더 7). Android 는
      `adb shell dumpsys alarm | grep com.dosaem.chosung`, iOS 는 Xcode 디버거에서
      `pendingNotificationRequests()` 로 확인할 수 있다(선택).
### 29. 앱 계정 연결(구글·애플) — 콘솔 등록과 사람이 채울 값

코드는 다 들어갔고(티켓 29), 아래는 **개발자 콘솔에 앱을 등록해야 채워지는 값**과
그때 한 번 해야 하는 설정이다. 비어 있으면 앱은 정상으로 뜨고 계정 연결 버튼만
"로그인하지 못했어요" 로 떨어진다(설정 누락이 조용한 통과가 되지 않게 한 선택).

**1) 구글 — iOS 클라이언트 ID**

1. Google Cloud 콘솔 > 사용자 인증 정보에서 **iOS** 용 OAuth 클라이언트를 만든다
   (번들 ID `com.dosaem.chosung`).
2. `mobile/ios/Flutter/Secrets.xcconfig.example` 을 `Secrets.xcconfig` 로 복사하고
   - `GOOGLE_IOS_CLIENT_ID` = 그 클라이언트 ID
   - `GOOGLE_IOS_URL_SCHEME` = 역방향 클라이언트 ID(`com.googleusercontent.apps.…`)
   를 채운다. 이 파일은 gitignore 다(값 자체는 앱 번들에 들어가므로 비밀은 아니지만,
   콘솔 등록 전 자리표시자가 커밋돼 잘못된 빌드가 나가는 걸 막으려고 뺐다).
3. 서버 `.env` 의 `GOOGLE_IOS_CLIENT_ID` 에도 **같은 값**을 넣는다 — 서버가 `aud`
   로 검증한다(티켓 10).
4. CI/수동 빌드가 쓰는 iOS 머신에도 같은 `Secrets.xcconfig` 가 있어야 한다.
   GitHub Actions 는 서명 파일과 같은 방식으로 내려받거나 `vars` 에서 써 넣는다.

**2) 구글 — Android serverClientId(= 웹 클라이언트 ID)**

- GitHub repository **variable** `GOOGLE_SERVER_CLIENT_ID` 에 **웹** 클라이언트 ID
  를 넣는다(`.github/workflows/flutter.yml` 이 `--dart-define` 으로 넘긴다).
  수동 fastlane 빌드는 같은 이름의 환경변수를 export 한다 — 비면 빌드가 멈춘다.
- Google Cloud 콘솔에 **Android** 클라이언트도 만들어 릴리스 키스토어 SHA-1 을
  등록한다. Android 클라이언트 ID 는 `aud` 로 오지 않지만(서명 검증용) 없으면
  로그인 자체가 안 된다. 서버 `.env` 의 `GOOGLE_WEB_CLIENT_ID` = 위 웹 ID.

**3) 애플 — Sign in with Apple capability**

- Apple Developer > Identifiers > App ID `com.dosaem.chosung` 에서 **Sign in with
  Apple** 을 켠다. 앱 쪽 `ios/Runner/Runner.entitlements` 는 이미 커밋돼 있으므로,
  capability 를 켠 뒤 **프로비저닝 프로파일을 다시 받아야**(`match` 재실행) 서명이
  맞는다. 안 그러면 빌드는 되고 로그인만 오류 1000 으로 떨어진다.
- 서버 `.env` 의 `APPLE_APP_BUNDLE_ID` = `com.dosaem.chosung`(티켓 10·14).

**4) 사람이 실기기에서 확인할 것**

- [ ] iOS: 구글 연결 → 홈·내 기록이 그 계정 기록으로 바뀐다
- [ ] iOS: 애플 연결 → 같은 확인. 이메일 가리기를 고르면 카드에 `…@privaterelay.appleid.com`
      이 마스킹돼 보인다
- [ ] iOS: 이미 다른 기기에서 쓰던 계정으로 로그인 → "이 계정의 기록으로 전환됐어요"
- [ ] Android: 구글 연결, 그리고 **애플 버튼이 없는지**(Out of Scope, US 18a)
- [ ] Android: 웹 "내 기록 백업" 코드를 붙여넣어 애플 계정 기록으로 전환
- [ ] 양쪽: 설정 > 계정 삭제 → 다이얼로그 → 삭제 후 새 게스트로 시작하고,
      온보딩은 다시 뜨지 않는다. 같은 토큰으로는 더 이상 조회되지 않는다(401)
- [ ] 애플 계정을 지운 뒤 iOS 설정 > Apple 계정 > 로그인 암호에서 앱이 사라졌는지
      (서버 revoke, 티켓 14)

**5) 남은 디자인 작업**

- 연결 버튼은 지금 Lucide 아이콘 없는 텍스트 버튼이다. 구글 브랜드 가이드라인과
  Apple HIG 는 각자의 **공식 로그인 버튼 에셋**을 요구한다(애플은 심사 항목).
  콘솔 등록과 함께 `sign_in_with_apple` 의 `SignInWithAppleButton` 과 구글 공식
  에셋으로 교체하고, 교체 뒤 골든(`records_light_390`)을 다시 찍는다.
### 35. 스토어 자산·메타데이터 — 출시 전 사람이 할 일

아이콘·스플래시·스크린샷·스토어 텍스트·심사 노트는 레포에 있고, **업로드는 수동
디스패치 워크플로**가 한다. 아래는 에이전트가 대신할 수 없는 것들이다.

#### 업로드 순서 (D3)

```sh
# 1) 스크린샷을 다시 찍어야 할 때만 (레포에 커밋된 PNG 를 덮어쓴다)
./scripts/store_screenshots.sh both

# 2) App Store: 메타데이터 + 스크린샷 (바이너리 제외)
gh workflow run appstore-metadata.yml -f app_version=1.0.0

# 3) App Store: 가격·연령등급·개인정보 라벨·심사 노트·빌드 첨부·제출
gh workflow run asc-submit.yml -f dry_run=true     # 먼저 제출 직전까지
gh workflow run asc-submit.yml -f build_number=<n> # 확인 후 진짜 제출

# 4) Play: 메타데이터·이미지·스크린샷은 fastlane supply 가 AAB 와 같이 올린다
cd mobile/android && bundle exec fastlane release
```

스크린샷 스크립트는 iOS 시뮬레이터(6.9"/6.5"/iPad 13")와 Android 에뮬레이터를 쓴다.
없는 iOS 기기는 `xcrun simctl create` 로 **스크립트가 만든다**. Android 는 AVD 가
있어야 하고(`ANDROID_AVD`, 기본 `Medium_Phone_API_36.1`), 없으면 그 단계만 건너뛴다.

#### GitHub Actions secrets (34 의 표에 더해서)

| 이름 | 쓰는 곳 | 값 |
|---|---|---|
| `ASC_REVIEW_CONTACT_FIRST_NAME` | `asc-submit.yml` | 심사 연락처 이름. **비워 두면 그 필드를 보내지 않고 ASC 콘솔 값을 유지한다** |
| `ASC_REVIEW_CONTACT_LAST_NAME` | 〃 | 심사 연락처 성 |
| `ASC_REVIEW_CONTACT_PHONE` | 〃 | 심사 연락처 전화번호. 레포에 적지 않는다 |
| `ASC_REVIEW_CONTACT_EMAIL` | 〃 | 심사 연락처 이메일 |

#### 체크박스

- [ ] **ASC 앱 이름**: "Hidden Vowels" 가 이미 쓰이고 있으면 **"Hidden Vowels: Daily Word"**
      로 바꾼다(스펙 미정 4). 바꾸면 `mobile/ios/fastlane/metadata/en-US/name.txt`,
      `mobile/android/fastlane/metadata/android/en-US/title.txt`,
      `tests/test_store_metadata.py` 의 `APP_NAMES` 세 곳을 같이 고친다.
- [ ] **Sandbox 테스터**: ASC 에서 테스터를 만들고, 심사 노트의
      `<SANDBOX_TESTER_EMAIL>`·`<SANDBOX_TESTER_PASSWORD>` 자리에 들어갈 값을
      **ASC 콘솔의 App Review Information 에 직접** 넣는다(레포에는 넣지 않는다).
      레포의 노트는 "콘솔에 넣어 둔 계정을 쓰라" 고 안내한다.
- [ ] **심사 연락처 secret 4개**를 넣는다. 안 넣으면 콘솔 값이 그대로 쓰인다.
- [ ] **Play 데이터 보안 설문**을 `docs/play-data-safety.md` 대로 콘솔에 입력하고,
      "미리보기" 요약이 그 문서의 표와 같은지 비교한다.
- [ ] **ASC 개인정보 라벨**: `asc-submit.yml` 이 iris API 로 시도하지만 팀 키는
      401 이 날 수 있다. 로그에 `privacy labels: SKIPPED` 가 보이면 콘솔에서
      `mobile/ios/fastlane/app_privacy_details.json` 대로 직접 넣는다.
- [ ] **콘텐츠 권리**: 워크플로가 `DOES_NOT_USE_THIRD_PARTY_CONTENT` 로 선언한다.
      단어 풀에 책 제목(카카오·Google Books 검색 결과)이 들어가는데 제목 자체는
      사실 표기라는 판단이다 — 제출 전에 한 번 확인한다.
- [ ] **방침 "수집 항목" 에 앱 사용 이벤트(Firebase) 추가 여부**: 지금 방침은 그
      전송을 `privacy#overseas` 에만 적고 3절 항목 목록에는 두지 않았다. 스토어
      라벨에는 신고한다(실제로 보내므로). 개보법 §30①3("처리하는 개인정보의 항목")
      기준으로 3절에도 한 줄 넣을지는 법적 문서 쪽 결정이라 여기 남긴다 —
      근거와 영향 범위는 `docs/legal-checklist.md` "스토어 라벨 > 차이 3번".
- [ ] **iPad 스크린샷**: `mobile/ios/fastlane/screenshots/{ko,en-US}/ipad13_*.png`
      5장씩이 있는지 확인한다. iPad 지원 앱이 iPad 스크린샷 없이 제출하면 심사가
      막힌다(BASELINE 1.0.0 반려 원인).
- [ ] **Play 폰 스크린샷**: 에뮬레이터가 없어 비어 있으면 Play 스토어 등록이
      막힌다. AVD 를 만들고 `./scripts/store_screenshots.sh both` 를 다시 돌린다.
