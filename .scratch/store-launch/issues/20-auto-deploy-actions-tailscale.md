# 20: 자동 배포 — `deploy.sh <prod|develop>` + GitHub Actions(Tailscale ssh)

**What to build:** `main` 푸시가 NAS prod 에, `develop` 푸시가 NAS develop 에 자동 배포된다. 배포는 git pull → compose up --build → 마이그레이션 → 재기동 확인 → `/health` 까지 한 스크립트가 맡고, 실패하면 워크플로가 빨갛게 멈춘다.

**Blocked by:** 19

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.27, US 64·65. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `deploy/deploy.sh <prod|develop>` 가 브랜치·디렉터리·포트·env file·프로젝트명을 고르고 `git pull` + `compose up -d --build` + app 컨테이너 `flask db upgrade` + 컨테이너 재기동 확인 + `/health` 200 검사. 로컬에서 두 인자 모두로 dry-run/실행 검증(테스트 절차 RELEASE.md)
- [ ] `.github/workflows/deploy.yml`: `main`/`develop` 푸시 트리거, Tailscale GitHub Action 으로 접속 후 `ssh nas 'deploy.sh …'`. 필요한 secrets 목록(TS auth key, ssh key, host) 을 RELEASE.md 표로
- [ ] ci.yml 이 PR 에서 ruff + pytest(MySQL/Redis 서비스 컨테이너) 를 돌리고 deploy 는 CI 성공 후에만
- [ ] NAS 쪽 사람 작업(ssh 키 등록, 러너·Tailscale)은 RELEASE.md D3 체크리스트로 분리. `git push` 는 이 티켓에서 하지 않는다
