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
- [ ] 삭제 전 `/api/v1/me/stats` 를 옛 토큰으로 부르면 401 이다(토큰을 미리
      복사해 두고 확인).
- [ ] 애플로 로그인한 게스트를 지운 뒤, **애플 ID 설정 > Apple ID 를 사용하는 앱**
      에서 이 앱이 사라졌는지 확인한다(실제 애플 계정이 필요해서 테스트가 아니라
      사람이 본다). 남아 있으면 `apple_revocation_retry` 테이블에 행이 있는지 보고
      Beat 로그를 확인한다.
