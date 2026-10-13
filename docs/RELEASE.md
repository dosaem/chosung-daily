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
