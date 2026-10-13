# 19: compose 파라미터화·develop 인스턴스 동시 기동

**What to build:** 같은 NAS 에서 prod(`chosung-daily-prod`, 8089)와 develop(`chosung-daily-develop`, 8090)이 이름·포트·볼륨이 분리된 채 동시에 돌 수 있다. prod 의 기존 named volume 이 새 compose 설정에서도 그대로 붙어 기록·토큰이 유지된다.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.26, 미정 8·16, D3. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `docker-compose.prod.yml` 에서 고정 `container_name`·`name:` 제거, 호스트 포트 `${APP_PORT}`, env file 환경별(`.env`, `.env.develop`), 볼륨은 compose 프로젝트 기본 네이밍. `.env.example`·`.env.develop.example` 에 `COMPOSE_PROJECT_NAME`·`APP_PORT` 포함(미정 16). 실제 `.env*` 는 수정하지 않는다
- [ ] 로컬 검증 ①: 현행 compose 로 띄운 `chosung-daily-prod` 에 기록을 넣고 새 설정으로 `-p chosung-daily-prod --env-file .env` 로 다시 `up` 했을 때 `docker volume ls` 이름이 같고 기록·토큰이 유지됨 — 절차와 결과를 `docs/RELEASE.md` 에 기록
- [ ] 로컬 검증 ②: `-p chosung-daily-develop --env-file .env.develop` 를 동시에 띄워 컨테이너 이름·포트·DB 볼륨이 분리되고 한쪽 쓰기가 다른 쪽에 안 보임
- [ ] `docs/RELEASE.md` 신설: 첫 배포 체크에 "NAS 의 실제 프로젝트명/볼륨명 확인 후 `up`", develop 체크아웃 디렉터리 `/volume1/docker/chosung-daily-develop`, DB 는 named volume(bind mount 금지 — DSM ACL)
- [ ] README "설계 판단" 에 "prod 프로젝트명 유지 이유" 추가
