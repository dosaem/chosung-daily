# 21: MySQL 매일 백업 컨테이너·14일 보존·복구 스크립트

**What to build:** MySQL 이 매일 04:00 KST 에 덤프되고 14일치가 보존되며, 실패하면 Slack 으로 알림이 온다. 운영자는 문서대로 로컬에서 복구 리허설을 할 수 있다.

**Blocked by:** 19

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.28, US 62·63. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] compose 에 독립 백업 서비스(mysqldump, cron 04:00 KST, gzip, 보존 14일 정리) 추가 — prod/develop 모두 프로젝트별 볼륨에 저장
- [ ] 실패 시 Slack webhook 으로 알림(쉘에서 curl, `SLACK_WEBHOOK_URL` 재사용)
- [ ] `scripts/restore.sh <dump>` 가 지정 덤프를 지정 compose 프로젝트의 MySQL 에 복원
- [ ] 로컬 검증: 백업 1회 생성 → 데이터 변경 → `restore.sh` → 원복 확인. 절차·결과를 `docs/RELEASE.md` "복구 리허설" 절에 기록
- [ ] README 운영 절에 백업 위치·보존·복구 명령 기록
