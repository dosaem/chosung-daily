# 20: 자동 배포 — `deploy.sh <prod|develop>` + GitHub Actions(Tailscale ssh)

**What to build:** `main` 푸시가 NAS prod 에, `develop` 푸시가 NAS develop 에 자동 배포된다. 배포는 git pull → compose up --build → 마이그레이션 → 재기동 확인 → `/health` 까지 한 스크립트가 맡고, 실패하면 워크플로가 빨갛게 멈춘다.

**Blocked by:** 19

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.27, US 64·65. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `deploy/deploy.sh <prod|develop>` 가 브랜치·디렉터리·포트·env file·프로젝트명을 고르고 `git pull` + `compose up -d --build` + app 컨테이너 `flask db upgrade` + 컨테이너 재기동 확인 + `/health` 200 검사. 로컬에서 두 인자 모두로 dry-run/실행 검증(테스트 절차 RELEASE.md)
- [ ] `.github/workflows/deploy.yml`: `main`/`develop` 푸시에 대해 기존 `ci.yml` 성공을 선행 조건으로(`workflow_run` 또는 같은 워크플로의 `needs`), Tailscale GitHub Action 으로 접속 후 `ssh nas 'deploy.sh …'`. 기존 `ci.yml` 은 push 브랜치에 `develop` 추가 외에 손대지 않는다(ruff+pytest+서비스 컨테이너는 이미 있음)
- [ ] 필요한 secrets 목록(TS auth key, ssh key, host) 을 RELEASE.md 표로. NAS 쪽 사람 작업(ssh 키 등록, Tailscale)은 RELEASE.md D3 체크리스트로 분리. `git push` 는 이 티켓에서 하지 않는다

## 리뷰 노트 (plan-review r1)

- P1-11/P3-13: ci.yml 이 이미 요구를 충족하므로 "develop 브랜치 추가 + deploy 선행 조건" 으로 범위를 좁힘
