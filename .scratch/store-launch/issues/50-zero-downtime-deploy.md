# 50: 무중단 배포 — 빌드·마이그레이션 먼저, app 롤링 교체

**What to build:** 배포해도 플레이어가 502 를 보지 않는다. 새 버전이 뜨지 못하면 옛 버전이 그대로 서비스하고 배포만 빨갛게 끝난다. 사용자가 2026-10-16 에 "1단계(순서 정리) + 2단계(Caddy 롤링) 같이" 로 결정(조사 메모 `.scratch/store-launch/zero-downtime-deploy.md`).

**Blocked by:** None (20 배포 스크립트 위에 얹는다).

**Status:** done (2026-10-16)

- [x] `deploy.sh`: build → 새 이미지로 `db upgrade` → app 롤링(`--scale N+1 --no-recreate` → healthy 대기 → 옛것 stop/rm) → worker/beat → 6개 서비스·/health 확인
- [x] 새 app 이 healthy 가 안 되면 새것만 지우고 실패, 옛 app 유지
- [x] compose: `proxy`(Caddy) 가 호스트 포트, app 은 healthcheck + `stop_grace_period`, gunicorn `graceful_timeout`
- [x] proxy 전환 1회를 스크립트가 스스로 처리(app 이 포트를 잡고 있으면 그때만 재생성)
- [x] ProxyFix 홉 2 (`PROXY_FIX_X_FOR`), 실측 테스트
- [x] NAS 비대화형 셸 PATH 에 docker 없던 문제(Actions 배포 127) 수정
- [x] 테스트: `tests/test_deploy_script.py` 롤링 4건 + 전환 1건 + PATH, `tests/test_proxy_fix_hops.py`
- [x] README 설계 판단 50, RELEASE §50
