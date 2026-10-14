# 37: 개인정보 안전성 확보조치 — 백업 덤프 암호화·복구, 개인정보처리시스템 접속기록 보관·점검

**What to build:** 운영자가 보기에 ① 매일 백업이 암호화된 덤프로만 디스크에 남고(평문 덤프 0개), 복구 스크립트가 지정한 키로만 복호화·복원되며 키 분실은 곧 복구 불가라는 경고와 키 보관 절차가 문서에 있다. ② 운영자 화면(`/admin/*`)과 계정 삭제 같은 개인정보 처리 행위마다 "누가·언제·어디서·무엇을" 접속기록이 남고, 웹 요청 접근 로그가 파일로 모이며, 둘 다 고시가 요구하는 기간 동안 보관된 뒤 자동 삭제되고 위변조를 검출할 수 있다. 개인정보처리방침(ko/en)·`docs/legal-checklist.md`·`docs/RELEASE.md` 의 "미구현 — 출시 전 결정 필요" 가 "구현됨" 으로 바뀐다. 사용자 결정(2026-10-14): "필요할 수 있는 것이니 다 만들자".

**Blocked by:** 16, 21

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.28(백업)·§C.33(이 티켓), §A.15, 미정 27. 근거 기준: **개인정보의 안전성 확보조치 기준(개인정보보호위원회 고시)** — 접속기록의 보관 및 점검, 개인정보의 암호화, 접근 통제, 재해·재난 대비(백업). 현행: `scripts/backup.sh`(`mysqldump | gzip`, `BACKUP_RETENTION_DAYS`), `scripts/restore.sh`(`gzip -t` → `gzip -dc | mysql`), `scripts/backup-cron.sh`, `docker-compose.prod.yml` backup 서비스(`${BACKUP_DIR}` bind mount), `tests/test_backup_restore.py`(스텁 기반), `Dockerfile` CMD 의 Gunicorn(접근 로그 없음), `app/admin.py`(`admin_required` 가 `g.admin_email` 설정), `app/services/account_deletion_service.py`, 16 이 만든 `docs/legal-checklist.md`·`tests/test_legal_checklist.py`·방침 절 `#collection`·`#security`·`#destruction`·`docs/RELEASE.md` "### 16.". 용어는 `CONTEXT.md`.

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

**설계 결정(워커가 바꾸려면 근거를 README 설계 판단에):**
- 백업 암호화는 **공개키 방식**(`age` 권장: 백업 컨테이너에는 수신자 공개키 `BACKUP_AGE_RECIPIENT` 만 env 로 두고, 개인키(identity)는 NAS prod 호스트에 두지 않는다 — 복구할 때만 `BACKUP_AGE_IDENTITY_FILE` 로 넘긴다). 백업 이미지에 `age` 를 넣을 수 없으면 `openssl enc -aes-256-cbc -pbkdf2`(대칭, 패스프레이즈 env 파일) 로 대체하되 "NAS 가 뚫리면 덤프도 열린다" 는 한계를 RELEASE 에 적는다. 레포에는 키·패스프레이즈 어떤 것도 없다.
- 접속기록은 두 겹: **(1) 개인정보 처리 행위 감사 로그**는 DB 테이블(예 `access_log`: 시각(UTC)·행위자(운영자는 이메일 마스킹 `h***@dosaem.com`, 게스트는 `guest.id`)·원격 IP·행위(`admin.word.create`, `admin.schedule.replace`, `admin.settings.save`, `admin.csv.import`, `account.delete`, `me.history.read` 등)·대상 식별자·결과(성공/403/오류)·`prev_hash`·`hash`(SHA-256 해시 체인) — INSERT 만 하는 리포지토리, UPDATE/DELETE 경로 없음, 만료 삭제만 Beat 작업이 한다. **(2) 웹 요청 접근 로그**는 Gunicorn `--access-logfile` 을 `${LOG_DIR}`(compose bind mount, `BACKUP_DIR` 와 같은 방식) 의 파일로, 사용자 정의 포맷에서 Authorization·쿠키·쿼리스트링을 제외(토큰·백업 코드가 URL 에 오지 않지만 포맷에서 명시적으로 뺀다). 일 단위 회전 + gzip + 보관 기간 지나면 삭제는 backup 컨테이너의 cron 이 함께 돈다(새 컨테이너 추가 금지).
- 보관 기간은 **워커가 고시 조문(접속기록의 보관 및 점검)을 확인해 확정**하고 조문 번호·기간을 `docs/legal-checklist.md` 행과 README 설계 판단에 적는다(이 서비스 규모·처리 항목 기준의 최소 기간; 예상 1년, 고유식별정보·민감정보는 처리하지 않으므로 상향 요건 없음을 함께 적는다). 기간은 설정값(`ACCESS_LOG_RETENTION_DAYS`)으로, 기본값 = 확정한 법정 최소 기간.
- 로그에 비밀값·토큰·전체 이메일·백업 코드를 남기지 않는다(감사 로그 행위자 마스킹, 접근 로그 포맷 제외, 기존 "로그 최소화" 원칙 유지).

- [ ] **백업 암호화**: `scripts/backup.sh` 가 `mysqldump | gzip | 암호화` 로 `*.sql.gz.age`(또는 `.enc`)만 최종 디렉터리에 쓰고, 임시 파일도 평문으로 남기지 않는다. 테스트(스텁): 실행 후 `BACKUP_DIR` 와 tmp 에 `*.sql.gz`(평문) 0개, 암호화 파일 1개; 수신자 키 env 가 비어 있으면 **백업을 만들지 않고** Slack 실패 알림(평문으로 조용히 떨어지지 않는다); 보존 삭제(`BACKUP_RETENTION_DAYS`)가 새 확장자에도 동작
- [ ] **복구**: `scripts/restore.sh` 가 identity 파일(`BACKUP_AGE_IDENTITY_FILE` 또는 인자)로 복호화한 스트림을 `gzip -dc | mysql` 로 넘기고, 복호화 실패(키 없음·잘못된 키·훼손)는 MySQL 을 건드리기 전에 멈춘다. 테스트(스텁): 키 없이 실패 + MySQL 호출 0회, 올바른 키로 성공, 구 평문 `.sql.gz` 덤프도 당분간 복원 가능(전환기 — RELEASE 에 "암호화 전 덤프가 보존 기간 지나 사라지면 평문 경로 제거" 체크)
- [ ] **키 절차 문서**: `docs/RELEASE.md` "### 37." 에 키 생성(`age-keygen`), 공개키를 prod `.env` 에 넣기, **identity 는 NAS 밖 두 곳**(운영자 비밀번호 관리자 + 오프라인 사본)에 보관, "identity 를 잃으면 모든 백업을 복구할 수 없다" 경고, 키 교체 절차(새 수신자로 백업 시작 후 구 identity 는 구 덤프 보존 기간까지 유지), 복구 리허설을 암호화 덤프 기준으로 다시 실행한 기록(21 의 "복구 리허설" 절 갱신 — 자기 절에서 참조만, 21 절 본문은 건드리지 않는다). `README` "운영: 백업 / 복구" 절에 암호화 한 단락
- [ ] **감사 로그 테이블·기록 지점**: 마이그레이션(머지 직전 `flask db heads` 1개) + 리포지토리(INSERT 전용) + 기록 헬퍼. 기록되는 행위 목록을 README 설계 판단 `### 37.` 에 표로 고정하고 테스트가 그 표의 각 행위를 실제로 발생시켜 행이 남는지 확인: `/admin` 전 라우트(조회 포함 — 운영자 화면 열람도 접속기록), 운영자 403 거부, `DELETE /me`·`POST /account/delete`, `GET /me/history`(개인정보 열람), `POST /auth/token-exchange`·웹 OAuth 콜백(계정 연결), `PATCH /me`. 요청이 실패해도(오류·403) 행이 남는다
- [ ] **위변조 검출**: 각 행의 `hash = sha256(prev_hash + 행 내용)`, `flask access-log verify` CLI 가 체인을 검증해 끊긴 지점을 보고(테스트: 중간 행을 SQL 로 바꾸면 verify 가 실패를 찍는다). 감사 로그 모델에 `updated_at` 없음, 리포지토리에 update/delete 함수 없음(테스트가 모듈 공개 API 를 확인)
- [ ] **접근 로그**: `Dockerfile` CMD(또는 `gunicorn.conf.py` 신설)에 `--access-logfile ${LOG_DIR}/access.log` + 사용자 정의 포맷(원격 IP·시각·메서드·경로(쿼리 제외)·상태·응답 크기·UA·응답 시간; Authorization·쿠키 없음). compose prod/develop 에 `${LOG_DIR}` bind mount(backup 과 같은 방식, DSM ACL 메모). 테스트: 포맷 문자열에 `%({authorization}i)s`·`%(q)s`·쿠키 변수가 없고 `access-logfile` 이 설정돼 있다 — 16 의 `test_the_production_entrypoint_has_no_access_log` 를 "접근 로그가 설정돼 있다" 로 뒤집는다
- [ ] **보관·삭제**: `ACCESS_LOG_RETENTION_DAYS`(기본 = 확정한 법정 최소 기간). 감사 로그 만료 삭제는 Beat 일일 작업(`subscription_recheck`·revoke 재시도와 같은 배선 패턴), 접근 로그 파일은 backup 컨테이너 cron 이 일 회전·gzip·만료 삭제(`scripts/rotate-access-log.sh`). 테스트: 기간 지난 행/파일은 지워지고 기간 안 것은 남는다, 기간 설정값이 반영된다, 삭제 실패 시 Slack(`notify_operator`)
- [ ] **점검**: `flask access-log report --month YYYY-MM` 이 월별 행위 수·거부 수·체인 검증 결과를 출력(고시의 "정기 점검" 을 사람이 할 수 있게). RELEASE "### 37." 에 "매월 1회 report 실행·결과 보관" 체크박스(실행은 사람)
- [ ] **법적 문서 동기화(16 산출물 갱신)**: 방침 ko/en `#destruction`("덤프 자체를 암호화하지는 않고" → 암호화 보관), `#collection`·`#security`("따로 모아 보관하지 않음 / 출시 전 적용 예정" → 접속기록을 N일/년 보관·점검) 문구를 실제 구현대로 고치고 `LEGAL_EFFECTIVE_DATE` 갱신; `docs/legal-checklist.md` 의 파기·안전성 확보 조치 행과 구현 대조표 2행을 "구현됨" 으로, 보관 기간·조문 번호 기입; `tests/test_legal_checklist.py` 의 `test_destruction_section_describes_the_real_backup_protection`·`test_privacy_does_not_promise_unimplemented_log_retention` 을 구현된 상태를 단언하도록 재작성; `docs/RELEASE.md` "### 16." 의 "접속기록 보관 구성"·"백업 덤프 암호화 여부 결정" 체크박스 제거(대신 "### 37." 참조 한 줄); 스펙 미정 항목의 "(티켓 16 수정 라운드 1)" 글머리 ①·② 와 미정 27 을 "티켓 37 구현" 으로 갱신(그 글머리는 16 브랜치에서 들어오므로 이 티켓이 머지된 main 기준으로 고친다)
- [ ] `.env.example` 에 `BACKUP_AGE_RECIPIENT`·`LOG_DIR`·`ACCESS_LOG_RETENTION_DAYS` + 주석, README 설계 판단 `### 37.` 에 공개키 선택·해시 체인·DB+파일 두 겹·보관 기간 근거(조문) 각 한 단락. 기존 `tests/test_backup_restore.py` 전부 통과(수정 허용), ruff 0

## 리뷰 노트 (plan-add r2)

- 사용자 결정 "필요할 수 있는 것이니 다 만들자"(2026-10-14) 로 추가. 16 의 원칙("미구현 보호조치는 고지하지 않는다") 은 그대로 두고, 이 티켓이 구현한 뒤 방침·체크리스트·RELEASE 를 "구현됨" 으로 바꾼다
- (a)·(b) 를 한 장으로 둔 근거: (a) 는 셸 스크립트 2개 + 스텁 테스트 확장 + 문서(작음), (b) 는 모델 1개·리포지토리·기록 헬퍼·Beat 작업·CLI 2개·Gunicorn 설정·회전 스크립트(중간). 둘 다 같은 문서 3종(방침·체크리스트·RELEASE "### 16.")을 고치므로 나누면 그 문서를 두 번 건드려 충돌한다. 설계 결정을 위에 못 박아 워커의 탐색 비용을 줄였다. 크기 판단 상세는 `review/plan-add-r2-response.md`
- Blocked by 16: 고칠 문서·테스트가 16 산출물. 21: 백업 스크립트·테스트·RELEASE 절(머지됨). 36 이 RELEASE 통합에서 이 티켓 절을 포함하므로 36 Blocked by 에 추가
