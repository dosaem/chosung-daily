# 21: MySQL 매일 백업 컨테이너·14일 보존·복구 스크립트

**What to build:** MySQL 이 매일 04:00 KST 에 덤프되고 14일치가 보존되며, 실패하면 Slack 으로 알림이 온다. 운영자는 문서대로 로컬에서 복구 리허설을 할 수 있다. 덤프는 NAS 폴더에 bind mount 돼 컨테이너가 죽어도 꺼낼 수 있다.

**Blocked by:** 19

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.28, US 62·63. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] compose 에 독립 백업 서비스(mysqldump, cron 04:00 KST, gzip, 보존 14일 정리) 추가 — 덤프 디렉터리는 `${BACKUP_DIR}` bind mount(기본 `./backups`, 예시 env 에 추가). 컨테이너가 root 로 쓰므로 DSM ACL 문제는 해당 없음을 RELEASE.md 에 메모
- [ ] 실패 시 Slack webhook 으로 알림(쉘에서 curl, `SLACK_WEBHOOK_URL` 재사용)
- [ ] `scripts/restore.sh <dump>` 가 지정 덤프를 지정 compose 프로젝트의 MySQL 에 복원
- [ ] 로컬 검증: 백업 1회 생성 → 데이터 변경 → `restore.sh` → 원복 확인. 절차·결과를 `docs/RELEASE.md` "복구 리허설" 절에 기록
- [ ] README 운영 절에 백업 위치·보존·복구 명령 기록

## 리뷰 노트 (plan-review r1)

- P1-23: 덤프 위치를 `${BACKUP_DIR}` bind mount 로 확정
