# 티켓 36 구현 증거 — 개인정보 안전성 확보조치(백업 덤프 암호화·접속기록 보관·점검)

- 날짜: 2026-10-14
- 브랜치: `dosaem/t36-privacy-safeguards-backup-encryption-access-log` (로컬 `main` = `055b56c` 위로 rebase)
- 환경: macOS (Darwin 25.3.0), Docker 29.8.2, OpenSSL 3.6.5(호스트) / 3.5.8(`mysql:8` 이미지), uv / Python 3.12
- 전용 테스트 자원: DB `chosung_daily_test_t36`, 마이그레이션 DB `chosung_daily_test_t36_migrations`,
  Redis DB 10 (`TEST_DATABASE_URL` / `TEST_MIGRATION_DATABASE_URL` / `TEST_REDIS_URL`) —
  공용 테스트 DB·Redis 는 건드리지 않았다
- 실제 외부 서비스(Slack·Apple·Google·스토어) 호출 없음. 백업 스크립트 테스트는
  `mysqldump`·`curl`·`docker` 를 PATH 스텁으로 바꿔 돌리고, `openssl`·`gzip`·`find` 는 진짜를 쓴다
- **키·비밀값은 이 문서에도, 로그에도 없다.** 검증에 쓴 RSA 키 쌍은 스크래치 디렉터리
  (`/private/tmp/claude-501/t36-manual`)에만 만든 일회용이고 레포에 들어가지 않는다.
  `.env`·`.env.prod*` 실제 값은 건드리지 않았다

## 1. 근거 조문 (워커가 확인해 확정)

**개인정보의 안전성 확보조치 기준** (개인정보보호위원회 고시 **제2023-6호**, 시행 2023. 9. 22.)

| 조문 | 요구 | 이 티켓의 결론 |
|---|---|---|
| **제8조 제1항** (접속기록의 보관) | 접속기록을 **1년 이상** 보관. 다만 ① 5만명 이상 정보주체 ② 고유식별정보·민감정보 처리 ③ 기간통신사업자면 **2년 이상** | 이 서비스는 세 요건 모두 해당하지 않는다 — 수집 항목(방침 `#collection`)에 주민등록번호·여권번호·생체정보 등 고유식별정보나 사상·건강 등 민감정보가 없고, 출시 전이라 정보주체 5만명 미만, 기간통신사업자도 아니다. → **법정 최소 1년 = `ACCESS_LOG_RETENTION_DAYS` 기본값 365** |
| **제8조 제2항** (점검) | 접속기록 등을 **월 1회 이상** 점검 | `flask access-log report --month YYYY-MM` + RELEASE "### 36." 의 월간 사람 체크박스 |
| **제8조 제3항** (위·변조 방지) | 접속기록이 위·변조·도난·분실되지 않도록 안전하게 보관 | 행마다 `hash = sha256(prev_hash + 행 내용)` 해시 체인 + `flask access-log verify`, 모델에 `updated_at` 없음, 리포지토리에 update/delete 없음 |
| **제7조** (개인정보의 암호화) | 인증정보·고유식별정보의 저장·전송 암호화 | 고유식별정보를 처리하지 않고 비밀번호도 없다(OAuth). 암호화 대상은 애플 refresh token(기존)과 **백업 덤프**(이 티켓) |
| **제11조** (재해·재난 대비) | 백업·복구 계획 — 10만명 이상 대기업·중견기업·공공기관 또는 100만명 이상 중소기업 | **적용 대상 아님.** 그래도 매일 백업·복구 리허설을 둔다(티켓 21·36) |

조문 번호 확인 경로: 검색 → 개인정보위 고시 전문(제2023-6호) 정리본. **주의**: 2025-10
개정(보유 규모별 차등화)에서 접속기록 조항이 1년 유예 대상으로 들어갔다고 보도돼 있어
**조 번호가 바뀔 수 있다**(보관 기간 1년/2년 자체는 같다). 출시 전 국가법령정보센터
현행 고시로 §8 번호를 확인하는 체크박스를 `docs/RELEASE.md` "### 36." 에 넣었고,
`docs/legal-checklist.md` "1-1." 절에도 같은 주의를 적었다. 법률 자문이 아니다.

## 2. 티켓이 못 박은 설계와 다르게 한 것 (코디네이터 승인)

| 티켓 문구 | 실제 구현 | 근거 |
|---|---|---|
| `age` 공개키 암호화, `BACKUP_AGE_RECIPIENT` / `BACKUP_AGE_IDENTITY_FILE`, `*.sql.gz.age` | `openssl cms -encrypt`(CMS 봉투, 공개키), `BACKUP_ENCRYPTION_CERT_FILE` / `BACKUP_DECRYPTION_KEY_FILE`, `*.sql.gz.enc` | backup 컨테이너가 재사용하는 `mysql:8`(Oracle Linux 9.8)에 **`age` 바이너리가 없고** 기본 저장소에도 없다(실측 §5.1). 넣으려면 전용 이미지 빌드나 런타임 다운로드가 필요해 "이미지 재사용·네트워크 의존 없음"(README 설계 판단 21)을 깬다. 같은 이미지의 OpenSSL 3.5.8 이 `openssl cms -encrypt -stream` 으로 공개키 봉투 암호화를 스트리밍 지원 — **age 와 같은 성질**(NAS 엔 공개키 인증서만, 개인키는 NAS 밖)을 유지하면서 바이너리 추가가 없다. 티켓의 대칭 대체안(`openssl enc` + 패스프레이즈)보다 안전하다. **코디네이터 `ask` → (A) 승인**(2026-10-14): env 이름도 방식에 맞게 바꾸고 README 설계 판단 36 에 근거를 남기라는 지시. 근거는 README "설계 판단 36." 첫 두 단락 |

## 3. 변경 파일

| 파일 | 내용 |
|---|---|
| `scripts/backup.sh` | `mysqldump \| gzip -c \| openssl cms -encrypt -stream` 한 줄로 `*.sql.gz.enc` 만 쓴다(평문 중간 파일 없음). `BACKUP_ENCRYPTION_CERT_FILE` 이 없거나 파일이 없으면 **덤프를 뜨지 않고** 실패 + Slack. 보존 정리는 `.sql.gz` 와 `.sql.gz.enc` 둘 다 본다 |
| `scripts/restore.sh` | `-k <개인키>` 옵션 + `BACKUP_DECRYPTION_KEY_FILE`. `.enc` 면 키 유무를 **MySQL 전에** 확인하고, 무결성 검사도 `복호화 \| gzip -t` 로 바꿨다(키 없음·잘못된 키·훼손 모두 MySQL 전에 멈춘다). 평문 `.sql.gz` 는 전환기 동안 그대로 복원 |
| `scripts/rotate-access-log.sh` | **신설.** 접근 로그 일 회전(copytruncate) + gzip + `ACCESS_LOG_RETENTION_DAYS` 만료 삭제, 실패 시 Slack |
| `scripts/backup-cron.sh` | 백업 뒤에 `rotate-access-log.sh` 를 같이 부른다(새 컨테이너 추가 없음) |
| `gunicorn.conf.py` | **신설.** `accesslog = ${LOG_DIR}/access.log`, 사용자 정의 포맷(원격 IP·시각·메서드·경로·상태·크기·UA·응답시간 — Authorization·쿠키·쿼리 제외), `errorlog = "-"` |
| `Dockerfile` | CMD 에 `-c gunicorn.conf.py` (exec 형식 CMD 는 셸을 안 거쳐 `${LOG_DIR}` 치환이 안 되므로 설정 파일로) |
| `docker-compose.prod.yml` | `app`·`backup` 에 `${LOG_DIR:-./logs}:/logs` bind mount, backup 에 `ACCESS_LOG_RETENTION_DAYS` |
| `app/models/access_log.py` | **신설.** `access_log` 모델 — `updated_at` 없음, `hash` 유니크 |
| `app/repositories/access_log_repository.py` | **신설.** INSERT 전용(`append`) + 읽기(`find_ordered`). update/delete 함수 없음. 체인 직렬화는 MySQL 네임드 락 |
| `app/services/access_log_service.py` | **신설.** 해시 규칙·`verify_chain`·`purge_expired_access_logs`(실패 시 `notify_operator`)·`monthly_report` |
| `app/access_log.py` | **신설.** 엔드포인트 → 행위 표 + `after_request` 기록 훅 + `mask_email`·`remember_actor` |
| `app/api/auth.py`, `app/admin.py`, `app/web.py` | 행위자 기록 한 줄(`remember_actor`). 운영자는 **허용 목록 판정 전**에 적어 403 거부도 남는다 |
| `app/tasks/scheduled.py` | `tasks.purge_access_logs` + Beat 매일 04:10(04:00 백업보다 뒤) |
| `app/cli.py` | `flask access-log verify` / `report --month` |
| `app/config.py` | `ACCESS_LOG_RETENTION_DAYS`(기본 365, 빈 문자열이면 기본값) |
| `migrations/versions/b1c7d4e0a932_add_access_log_table.py` | **신설.** `down_revision = d7a1f0ca0a29` |
| `web/templates/legal/privacy.{ko,en}.html` | `#collection`·`#destruction`·`#security` 를 구현된 상태로 + D-16-5("연결 해제") 사실화 |
| `docs/legal-checklist.md` | "1-1." 고시 조문 절 신설(5행), 파기·안전성 확보 조치 행과 8절 구현 대조표 2행을 "구현됨" 으로 |
| `docs/RELEASE.md` | "### 36." 신설(키 생성·보관·교체·리허설·월 1회 점검 체크박스), "### 16." 의 두 체크박스를 36 참조 한 줄로 교체 |
| `README.md` | "설계 판단 36." 신설(공개키 선택·해시 체인·두 겹·보관 기간 근거 + 기록 행위 표), "운영: 백업 / 복구" 에 암호화 단락 |
| `.env.example`, `.env.prod.example`, `.env.develop.example` | `BACKUP_ENCRYPTION_CERT_FILE`·`LOG_DIR`·`ACCESS_LOG_RETENTION_DAYS` + 주석 |
| `CONTEXT.md` | 용어 4개(접속기록·감사 로그·접근 로그·백업 암호화) |
| `.scratch/store-launch/spec.md` | 미정 27 해소, "(티켓 16 수정 라운드 1)" 글머리 ①·②(+③ D-16-5) 갱신 — 티켓이 지시한 자기 항목만 |
| `tests/test_access_log.py` | **신설** 41개 — 기록 지점·마스킹·해시 체인·보관·점검 |
| `tests/test_access_log_file.py` | **신설** 16개 — Gunicorn 설정·포맷·compose 마운트·회전 스크립트 |
| `tests/test_backup_restore.py` | 암호화 기준으로 수정 + 암호화/복호화 테스트 추가(52개) |
| `tests/test_cli.py`, `tests/test_celery_wiring.py`, `tests/test_migrations.py` | CLI 4개·Beat 배선·마이그레이션 왕복 2개 추가 |
| `tests/test_legal_checklist.py`, `tests/test_legal_pages.py` | 미구현을 못 박던 테스트 2개를 구현된 상태 단언으로 뒤집고, D-16-5 회귀 테스트 3개 추가 |

```
$ uv run flask db heads
b1c7d4e0a932 (head)        # 1줄
```

## 4. 체크박스별 증거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| **백업 암호화** — `*.sql.gz.age`(또는 `.enc`)만, 임시 파일도 평문 아님 | `tests/test_backup_restore.py::test_backup_writes_an_encrypted_dump`, `::test_no_plaintext_dump_is_left_anywhere`, `::test_the_dump_on_disk_is_not_readable_without_the_private_key`(다른 키로는 복호화 실패) + 실제 `mysql:8` 컨테이너 실행 §5.2(평문 `.sql.gz` 0개, `strings` 로 덤프 내용 안 보임) |
| 수신자 키 env 가 비면 **백업을 만들지 않고** Slack 실패 알림 | `::test_backup_refuses_to_run_without_the_recipient_certificate`, `::test_backup_fails_when_the_certificate_file_is_missing`, `::test_backup_fails_when_encryption_fails` (세 경우 모두 종료 코드 ≠ 0, `DUMP_DIR` 비어 있음, curl 스텁에 Slack POST) |
| 보존 삭제가 새 확장자에도 동작 | `::test_backup_keeps_14_days_and_deletes_older`(`.sql.gz.enc` + 전환기 `.sql.gz` 를 섞어 두고 14일 경계 확인, 덤프가 아닌 파일은 안 건드림), `::test_backup_retention_days_is_configurable` |
| **복구** — identity 파일로 복호화 스트림을 `gzip -dc \| mysql` 로 | `::test_restore_decrypts_with_the_key_file_and_pipes_it_into_mysql`, `::test_restore_takes_the_key_as_an_argument_too`, `::test_restore_does_not_write_the_decrypted_dump_to_disk` + 실제 복구 §5.3(상태 A → B → A) |
| 복호화 실패(키 없음·잘못된 키·훼손)는 **MySQL 전에** 멈춘다 | `::test_restore_without_a_key_stops_before_touching_mysql`(docker 호출 0회), `::test_restore_with_the_wrong_key_stops_before_touching_mysql`, `::test_restore_rejects_a_corrupted_encrypted_dump_before_touching_mysql` + 실제 실행 §5.3 |
| 구 평문 `.sql.gz` 덤프도 당분간 복원 가능 + RELEASE 전환기 체크 | `::test_restore_still_accepts_a_legacy_plaintext_dump` + 기존 복구 테스트 전부 통과 + `docs/RELEASE.md` "### 36." 의 "전환기 정리" 체크박스 |
| **키 절차 문서** — 키 생성·공개키 배치·NAS 밖 두 곳 보관·분실 경고·교체 절차·리허설 갱신 | `docs/RELEASE.md` "### 36. (a)" — `openssl req` 생성 명령, `BACKUP_ENCRYPTION_CERT_FILE` 설정, "키 보관(사람)" 3항목(비밀번호 관리자 + 오프라인 사본, **분실 = 복구 불가** 경고), "키 교체 절차" 3항목(구 개인키를 구 덤프 보존 기간까지 유지), "복구 리허설(암호화 기준)" — 21 절 본문은 건드리지 않고 참조만 |
| README "운영: 백업 / 복구" 에 암호화 한 단락 | `README.md` "운영: 백업 / 복구" — 파일 이름 표 행을 `.sql.gz.enc` 로, `-k` 를 쓴 복구 명령, "덤프는 암호화돼 있다" 단락 |
| **감사 로그 테이블·기록 지점** — 마이그레이션 + INSERT 전용 리포지토리 + 기록 헬퍼 | `migrations/versions/b1c7d4e0a932_*.py`(+ `flask db heads` 1줄), `tests/test_migrations.py::test_access_log_table_round_trips`·`::test_access_log_rows_are_insert_only_and_unique_by_hash`, `tests/test_access_log.py::test_the_repository_exposes_no_update_or_delete_path` |
| 기록 행위 목록을 README 표로 고정 + 테스트가 각 행위를 실제로 발생시킨다 | `tests/test_access_log.py::test_the_recorded_actions_match_the_readme_table`(README 표 ↔ `ACTION_BY_ENDPOINT` 동일), `::test_every_admin_route_is_in_the_action_table`(`app.url_map` 의 `admin.*` 엔드포인트가 모두 표에 있다 — 새 운영자 라우트가 기록 없이 들어오는 것을 막는다), `::test_every_admin_route_leaves_a_row_even_when_the_request_fails`(14개 행위 parametrize), `::test_deleting_an_account_through_the_api_is_recorded`, `::test_deleting_an_account_through_the_web_page_is_recorded`, `::test_reading_my_own_history_is_recorded`, `::test_changing_my_puzzle_language_is_recorded`, `::test_linking_an_account_by_token_exchange_is_recorded`, `::test_the_web_oauth_callback_is_recorded` |
| 운영자 403 거부·요청 실패도 행이 남는다 | `::test_a_forbidden_operator_attempt_is_recorded_as_denied`(result=`denied`, status 403), `::test_every_admin_route_leaves_a_row_even_when_the_request_fails`(POST 들이 CSRF 403 으로 떨어져도 행이 남는다) |
| 행위자 마스킹·대상 식별자·시각·IP·결과 | `::test_the_operator_email_is_masked_in_the_actor_column`, `::test_a_guest_actor_is_recorded_by_guest_id`, `::test_each_row_records_who_when_where_and_what`, `::test_the_target_identifier_is_recorded_for_a_single_object` |
| **위변조 검출** — 해시 체인 + `flask access-log verify` 가 끊긴 지점 보고 | `::test_rows_are_chained_by_sha256_of_the_previous_hash`, `::test_verify_accepts_an_untouched_chain`, `::test_verify_reports_the_row_where_the_chain_breaks`(SQL `UPDATE` 로 중간 행 변조), `::test_verify_detects_a_deleted_row_in_the_middle`(SQL `DELETE`), `tests/test_cli.py::test_access_log_verify_exits_nonzero_and_names_the_broken_row` |
| 만료 삭제 후에도 verify 가 동작한다(도구가 죽지 않는다) | `::test_verify_still_passes_after_the_retention_purge`, `::test_verify_still_catches_tampering_in_the_rows_that_remain` — 맨 앞 행의 `prev_hash` 는 이미 지워진 행을 가리키는 게 정상이라 검사하지 않는다(그 대가는 `app/services/access_log_service.py` `verify_chain` 독스트링) |
| 동시 요청이 체인을 두 갈래로 갈라놓지 않는다 | `tests/test_concurrency.py::test_concurrent_access_log_appends_keep_one_chain`(스레드 2개 + `SELECT ... FOR UPDATE`), 모델·마이그레이션의 `prev_hash` 유니크 |
| 모델에 `updated_at` 없음, 리포지토리에 update/delete 없음 | `::test_the_model_has_no_updated_at_column`, `::test_the_repository_exposes_no_update_or_delete_path`(모듈 공개 API 검사), `tests/test_migrations.py::test_access_log_rows_are_insert_only_and_unique_by_hash` |
| **접근 로그** — `--access-logfile ${LOG_DIR}/access.log` + 사용자 정의 포맷 | `gunicorn.conf.py` + `tests/test_access_log_file.py::test_requests_are_logged_to_a_file_under_log_dir`, `::test_the_access_log_format_records_what_the_notice_says`(8개 항목) + 실제 Gunicorn 기동 §5.4 |
| 포맷에 Authorization·쿠키·쿼리 없음 (16 의 테스트를 뒤집는다) | `::test_the_access_log_format_excludes_tokens_cookies_and_query_strings`(+`%(r)s` 금지), `tests/test_legal_checklist.py::test_the_production_entrypoint_configures_an_access_log`(구 `test_the_production_entrypoint_has_no_access_log` 를 뒤집은 것) + 실제 요청 §5.4(쿼리·헤더·쿠키 값이 로그에 0건) |
| compose prod/develop 에 `${LOG_DIR}` bind mount + DSM ACL 메모 | `::test_the_log_directory_is_bind_mounted_like_the_backup_directory[app/backup]`, `::test_the_app_container_knows_the_retention_period` + `docs/RELEASE.md` "### 36. (b) NAS 설정 메모"(DSM ACL 해당 없음 근거) |
| (추가) 접속기록 디렉터리가 커밋·이미지에 들어가지 않는다 | `LOG_DIR` 기본값이 `./logs` 라 덤프(`backups*/`)와 같은 조치가 필요하다 — 접근 로그에는 원격 IP 가 들어 있다. `.gitignore`·`.dockerignore` 에 `logs*/` + `tests/test_access_log_file.py::test_access_logs_are_not_committed_or_baked_into_the_image` |
| **보관·삭제** — `ACCESS_LOG_RETENTION_DAYS`(기본 = 법정 최소) | `tests/test_access_log.py::test_the_default_retention_is_the_legal_minimum_of_one_year`, `::test_an_empty_retention_env_falls_back_to_the_legal_minimum`, `tests/test_legal_checklist.py::test_the_retention_period_in_the_notice_matches_the_setting` |
| 감사 로그 만료 삭제 = Beat 일일 작업(기존 배선 패턴) | `app/tasks/scheduled.py` + `tests/test_celery_wiring.py::test_tasks_are_registered`·`::test_access_log_purge_runs_daily_right_after_the_backup`·`::test_tasks_delegate_to_the_service_functions` |
| 접근 로그 파일 = backup 컨테이너 cron 이 일 회전·gzip·만료 삭제 | `scripts/rotate-access-log.sh` + `tests/test_access_log_file.py::test_rotation_moves_todays_requests_into_a_gzipped_file`, `::test_rotation_does_nothing_when_there_were_no_requests`, `::test_rotation_is_safe_to_run_twice_in_one_day`, `::test_the_backup_container_cron_also_rotates_the_access_log` + 실제 이미지 실행 §5.5 |
| 기간 지난 것은 지워지고 기간 안 것은 남는다, 설정값이 반영된다 | DB: `::test_rows_past_the_retention_period_are_deleted`(경계 ±1분), `::test_the_retention_period_is_configurable` / 파일: `::test_rotated_files_past_the_retention_period_are_deleted`, `::test_the_file_retention_period_is_configurable` + §5.5(366일 전 파일 `pruned`) |
| 삭제 실패 시 Slack(`notify_operator`) | `tests/test_access_log.py::test_a_failed_purge_tells_the_operator`(DB), `tests/test_access_log_file.py::test_a_failed_prune_tells_the_operator`(파일, `find -delete` 실패 주입), `::test_rotation_succeeds_quietly` |
| **점검** — `flask access-log report --month YYYY-MM` 이 월별 행위 수·거부 수·체인 검증 | `tests/test_access_log.py::test_the_monthly_report_counts_actions_denials_and_verifies_the_chain`, `::test_the_monthly_report_only_counts_that_month`, `::test_the_monthly_report_rejects_a_bad_month`, `tests/test_cli.py::test_access_log_report_prints_counts_denials_and_the_chain_result`, `::test_access_log_report_rejects_a_month_it_cannot_parse` + 실제 출력 §5.6 |
| RELEASE 에 "매월 1회 report 실행·결과 보관" 체크박스 | `docs/RELEASE.md` "### 36. (b) 사람이 할 일" 두 번째 체크박스(명령 포함) |
| **법적 문서 동기화** — 방침 `#destruction` 암호화 보관 | `web/templates/legal/privacy.{ko,en}.html` + `tests/test_legal_checklist.py::test_destruction_section_describes_the_real_backup_protection`(필수 문구를 "암호화한 덤프"·"복호화 키는 서버에 두지 않음" 으로, 금지 문구 "암호화하지는 않" 유지), `::test_the_backup_script_encrypts_the_dump_with_a_public_key` |
| 방침 `#collection`·`#security` 접속기록 N일 보관·점검 | `tests/test_legal_checklist.py::test_privacy_states_the_implemented_log_retention`(필수: "1년(365일)"·"월 1회 이상 점검"·"제8조" / 금지: "따로 모아 보관하지 않"·"출시 전에 적용") |
| `LEGAL_EFFECTIVE_DATE` 갱신 | `app/web.py` 의 값이 이미 `2026-10-14`(= 오늘, 16 이 올린 날)라 그대로다 — 같은 날 안의 변경이므로 올릴 날짜가 없다 |
| `docs/legal-checklist.md` 행·대조표 "구현됨" + 보관 기간·조문 번호 | `docs/legal-checklist.md` §1 파기 행·안전성 확보 조치 행, **"1-1." 고시 조문 절 신설**(§8①②③·§7·§11, 1년/2년 요건과 이 서비스의 해당 여부), §8 구현 대조표 2행 → "구현됨" + 근거 코드·테스트 |
| 테스트 2개를 구현된 상태 단언으로 재작성 | `test_destruction_section_describes_the_real_backup_protection`(문구 뒤집기), `test_privacy_does_not_promise_unimplemented_log_retention` → **`test_privacy_states_the_implemented_log_retention`** 으로 재작성, `test_the_backup_script_only_compresses_the_dump` → **`test_the_backup_script_encrypts_the_dump_with_a_public_key`**, `test_the_production_entrypoint_has_no_access_log` → **`test_the_production_entrypoint_configures_an_access_log`** |
| `docs/RELEASE.md` "### 16." 의 두 체크박스 제거 + 36 참조 한 줄 | `docs/RELEASE.md` "### 16." 마지막 체크박스 앞 — "접속기록 보관 구성과 백업 덤프 암호화는 **티켓 36 에서 구현했다**" 한 줄. 16 절의 다른 항목은 그대로 |
| 스펙 미정 항목 ①·②·미정 27 갱신 | `.scratch/store-launch/spec.md` — 미정 27 을 "해소(티켓 36 구현)" 로(방식·보관 기간·조문 포함), "(티켓 16 수정 라운드 1)" 글머리의 ①·② 를 "→ 티켓 36 구현" 으로, ③ 에 D-16-5 수정 추가 |
| `.env.example` 에 3개 + 주석 | `.env.example`(로컬은 불필요하다는 설명 + 키만), `.env.prod.example`·`.env.develop.example`(`### 36.` 소제목, prod `./logs` / develop `./logs-develop`) |
| README 설계 판단 `### 36.` 에 공개키 선택·해시 체인·두 겹·보관 기간 근거 각 한 단락 | `README.md` "### 36. 개인정보 안전성 확보조치" — 공개키 선택(대칭키를 안 쓴 이유 + age 를 안 쓴 이유), 두 겹 표 + 기록 행위 표, `after_request` 한 곳인 이유, 로그 최소화, 해시 체인·네임드 락·초 단위 절단, 보관 기간 365일 근거(§8① + 2년 요건 비해당), copytruncate, 점검은 사람 |
| 기존 `tests/test_backup_restore.py` 전부 통과, ruff 0 | §6 전체 스위트 + ruff 출력 |
| **(추가 지시, 코디네이터 메모)** D-16-5: 방침이 없는 "연결 해제" 기능을 거부 수단으로 안내 | `web/templates/legal/privacy.{ko,en}.html` `#collection` 계정 이메일 보유 기간 + `#overseas` Google 행 거부 방법을 "연결만 끊는 기능은 없다 / 계정 삭제가 유일" 로 수정. `tests/test_legal_pages.py::test_privacy_does_not_offer_an_unlink_feature_that_does_not_exist`, `::test_privacy_says_deletion_is_the_only_way_to_end_email_retention`, `::test_the_google_row_does_not_sell_unlinking_as_an_opt_out` |

## 5. 실제 실행 기록

### 5.1 `mysql:8` 이미지에 `age` 가 없고 OpenSSL CMS 가 있다

```
$ docker run --rm --entrypoint sh mysql:8 -c 'command -v age; command -v openssl && openssl version; openssl cms -help | head -3; cat /etc/os-release | head -3'
/usr/bin/openssl
OpenSSL 3.5.8 25 Aug 2026 (Library: OpenSSL 3.5.8 25 Aug 2026)
Usage: cms [options] [cert...]
 -help                      Display this summary
NAME="Oracle Linux Server"
VERSION="9.8"
ID="ol"
```

`command -v age` 가 아무것도 출력하지 않는다(없다). 같은 이미지에서 CMS 왕복도 확인했다.

```
$ docker run --rm -v "$PWD:/work" -w /work --entrypoint bash mysql:8 -c '
    echo "INSERT INTO word VALUES (1, \"사과\");" | gzip -c |
      openssl cms -encrypt -binary -aes-256-cbc -outform DER -stream -recip c.pem > container.enc
    openssl cms -decrypt -binary -inform DER -inkey k.pem -in container.enc | gzip -dc'
INSERT INTO word VALUES (1, "사과");
```

### 5.2 실제 백업 1회 — 암호화 덤프만 남는다 (스텁 아님)

로컬 `mysql:8` 컨테이너(`chosung-daily-mysql-1`)에 이 검증 전용 DB
`chosung_daily_t36_manual`(word 2행: 사과·포도)을 만들고, `backup` 컨테이너와 같은
이미지로 `scripts/backup.sh` 를 돌렸다. 공용 DB·다른 워커의 컨테이너는 건드리지 않았고
검증 후 이 DB 만 `DROP` 했다.

```
$ docker run --rm --network chosung-daily_default -v "$PWD/scripts:/scripts:ro" -v "$S:/work" \
    -e DUMP_DIR=/work/dumps -e MYSQL_HOST=mysql -e MYSQL_DATABASE=chosung_daily_t36_manual \
    -e MYSQL_ROOT_PASSWORD=*** -e BACKUP_ENCRYPTION_CERT_FILE=/work/cert.pem \
    --entrypoint bash mysql:8 /scripts/backup.sh
[backup] 2026-10-14 07:13:23+0000 dumping chosung_daily_t36_manual from mysql -> /work/dumps/chosung_daily_t36_manual-20261014-071323.sql.gz.enc (encrypted)
[backup] 2026-10-14 07:13:24+0000 wrote 4.0K /work/dumps/chosung_daily_t36_manual-20261014-071323.sql.gz.enc
[backup] 2026-10-14 07:13:24+0000 done (1 dumps kept)

$ ls -l $S/dumps
-rw-r--r--  1 saem  wheel  1285 Oct 14 16:13 chosung_daily_t36_manual-20261014-071323.sql.gz.enc
$ find $S/dumps -name '*.sql.gz' | wc -l
0                                  # 평문 덤프 0개
$ strings "$D" | grep -i "insert|사과|CREATE TABLE" | head -3
                                   # 출력 없음 — 덤프 내용이 파일에서 안 보인다
```

(mysqldump 실패 경로도 실측됐다: 처음에 활성 테스트 DB 를 대상으로 돌렸더니 테스트가
테이블을 바꾸는 중이라 `mysqldump: Couldn't execute 'show create table account'` 로 실패했고,
**`DUMP_DIR` 에 반쪽 파일이 하나도 남지 않았다**(`total 0`) — `.partial` → `mv` 설계가 실제로 동작.)

### 5.3 실제 복구 — 상태 A → B → A, 키 없으면 MySQL 전에 멈춘다

```
$ docker exec ... mysql -e "USE chosung_daily_t36_manual; DELETE FROM word WHERE id=2; INSERT INTO word VALUES (3,'딸기'); SELECT GROUP_CONCAT(answer) FROM word;"
state_b
사과,딸기                           # 상태 B (백업 이후 변경)

$ BACKUP_DECRYPTION_KEY_FILE="" ./scripts/restore.sh -y "$D" chosung-daily
암호화된 덤프다 — 복호화 개인키가 필요하다: -k <개인키.pem> 또는 BACKUP_DECRYPTION_KEY_FILE
                                   # 종료 코드 1, docker/mysql 호출 전에 멈춘다

$ openssl cms -decrypt -binary -inform DER -inkey $S/key.pem -in "$D" | gzip -dc | docker exec -i chosung-daily-mysql-1 mysql -u root -p***
$ docker exec ... mysql -e "USE chosung_daily_t36_manual; SELECT GROUP_CONCAT(answer ORDER BY id) FROM word;"
restored
사과,포도                           # 상태 A 로 복원됨
```

### 5.4 실제 Gunicorn 접근 로그 — 포맷이 돌고 비밀값이 안 새어 나간다

```
$ LOG_DIR=$L uv run gunicorn -c gunicorn.conf.py -b 127.0.0.1:8137 wsgi:app &
$ curl "http://127.0.0.1:8137/privacy?lang=ko&secret=should-not-be-logged" \
    -H "Authorization: Bearer super-secret-token" -H "Cookie: session=abc123"
$ curl "http://127.0.0.1:8137/nope"
$ cat $L/access.log
127.0.0.1 [14/Oct/2026:16:14:07 +0900] "GET /privacy" 200 25965 "curl/8.7.1" 0.016168
127.0.0.1 [14/Oct/2026:16:14:07 +0900] "GET /nope" 404 126 "curl/8.7.1" 0.000647
$ grep -c "super-secret-token|abc123|should-not-be-logged" $L/access.log
0                                   # 토큰·쿠키·쿼리스트링 0건
```

경로는 `/privacy` 로만 남고 `?lang=ko&secret=...` 은 포맷에서 빠진다. 오류·기동 로그는
그대로 표준 출력(`errorlog = "-"`).

### 5.5 실제 접근 로그 회전 — `mysql:8` 이미지에서

```
$ docker run --rm -v "$PWD/scripts:/scripts:ro" -v "$L:/logs" -e LOG_DIR=/logs -e TZ=Asia/Seoul \
    --entrypoint bash mysql:8 /scripts/rotate-access-log.sh
[rotate-access-log] 2026-10-14 16:13:51+0900 rotated -> /logs/access.log-20261014.gz (4.0K)
[rotate-access-log] 2026-10-14 16:13:51+0900 pruned /logs/access.log-20240901.gz   # 보관 기간(365일) 지난 파일
[rotate-access-log] 2026-10-14 16:13:51+0900 done (1 files kept)

$ ls -l $L
-rw-r--r--  1 saem  wheel    0 Oct 14 16:13 access.log          # copytruncate — 원본은 남고 0 바이트
-rw-r--r--  1 saem  wheel  118 Oct 14 16:13 access.log-20261014.gz
$ gzip -dc $L/access.log-*.gz
127.0.0.1 [14/Oct/2026:04:00:00 +0900] "GET /privacy" 200 1234 "Mozilla/5.0" 0.012
```

### 5.6 실제 점검 CLI 출력 (행 내용 + 위변조 검출)

이 검증 전용 DB `chosung_daily_t36_cli` 에 `flask db upgrade` 로 스키마를 만들고(모델
`create_all` 이 아니라 마이그레이션 경로) 행 3개를 넣고 돌렸다. 검증 후 DROP 했다.

```
$ uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade d7a1f0ca0a29 -> b1c7d4e0a932, add access log table

$ docker exec ... mysql -e "SELECT id, occurred_at, actor, remote_ip, action, result, status_code,
                                   LEFT(prev_hash,12), LEFT(hash,12) FROM access_log"
id  occurred_at          actor             remote_ip      action           result   status  prev          hash
1   2026-10-14 07:17:35  h***@dosaem.com   203.0.113.9    admin.word.list  success  200     000000000000  170bfe0b626c
2   2026-10-14 07:17:35  guest.41          198.51.100.7   me.history.read  success  200     170bfe0b626c  cc654018158f
3   2026-10-14 07:17:35  x***@example.com  203.0.113.77   admin.word.list  denied   403     cc654018158f  63d2aa0bf0fa
```

운영자 이메일이 마스킹돼 있고(`h***@dosaem.com`), 거부된 접근이 `denied`/403 으로 남고,
각 행의 `prev_hash` 가 앞 행의 `hash` 다(첫 행은 genesis `0*64`).

```
$ uv run flask access-log report --month 2026-10
[2026-10] 접속기록 총 3건, 거부 1건
  admin.word.list 2
  me.history.read 1
체인 검증(3행) — 이상 없음

$ uv run flask access-log verify
접속기록 3행 검증 — 이상 없음
$ echo $?
0
```

앱을 거치지 않고 SQL 로 2번 행의 `actor` 를 바꾼 뒤:

```
$ docker exec ... mysql -e "UPDATE access_log SET actor='guest.999' WHERE id=2"
$ uv run flask access-log verify
접속기록 체인이 끊겼습니다: id=2 (2행까지 검증)
$ echo $?
1
```

## 6. 테스트·린트·빌드

### 6.1 TDD (red → green)

접속기록은 테스트를 먼저 썼다. 첫 실행에서 모델·리포지토리·서비스·배선이 없어 전부 실패.

```
$ uv run pytest tests/test_access_log.py -x -q
...   (ImportError: cannot import name 'AccessLog' from 'app.models')
```

백업 암호화도 같다 — 암호화 테스트 11개를 먼저 쓰고 돌렸다.

```
$ uv run pytest tests/test_backup_restore.py -q
FAILED tests/test_backup_restore.py::test_backup_writes_an_encrypted_dump
FAILED tests/test_backup_restore.py::test_the_dump_on_disk_is_not_readable_without_the_private_key
FAILED tests/test_backup_restore.py::test_no_plaintext_dump_is_left_anywhere
FAILED tests/test_backup_restore.py::test_backup_refuses_to_run_without_the_recipient_certificate
FAILED tests/test_backup_restore.py::test_backup_fails_when_the_certificate_file_is_missing
FAILED tests/test_backup_restore.py::test_backup_fails_when_encryption_fails
FAILED tests/test_backup_restore.py::test_backup_keeps_14_days_and_deletes_older
FAILED tests/test_backup_restore.py::test_backup_retention_days_is_configurable
FAILED tests/test_backup_restore.py::test_restore_decrypts_with_the_key_file_and_pipes_it_into_mysql
FAILED tests/test_backup_restore.py::test_restore_takes_the_key_as_an_argument_too
FAILED tests/test_backup_restore.py::test_restore_without_a_key_stops_before_touching_mysql
11 failed, 41 passed in 10.16s
```

구현 후 green:

```
$ uv run pytest tests/test_backup_restore.py -q
52 passed in 8.31s

$ uv run pytest tests/test_access_log.py -q
41 passed in 27.02s

$ uv run pytest tests/test_access_log_file.py -q
16 passed in 1.70s

$ uv run pytest tests/test_migrations.py -q -k access_log
2 passed, 12 deselected in 6.59s
```

### 6.2 전체 스위트

(§FULL_SUITE)

### 6.3 ruff

```
$ uv run ruff check .
All checks passed!
```

### 6.4 마이그레이션 head

```
$ uv run flask db heads
b1c7d4e0a932 (head)
```

## 7. 하지 않은 것 · 남은 것

- **`impeccable detect` / `audit.native` 를 돌리지 않았다** — 이 티켓은 UI 를 건드리지 않는다.
  법적 문서 템플릿의 **본문 문장만** 고쳤고(절 구조·id·마크업·CSS 변경 없음) 디자인 토큰·
  레이아웃은 그대로다. 티켓 완료 조건에도 detect 가 없다.
- **NAS 실측·배포는 하지 않았다**(프로덕션 금지). 키 생성·보관, `LOG_DIR` 생성, 암호화
  기준 복구 리허설, 월 1회 점검, 현행 고시 조 번호 확인은 `docs/RELEASE.md` "### 36." 의
  사람 체크박스다.
- **복구 리허설 실측을 RELEASE "### 21." 본문에 쓰지 않았다** — 티켓이 "21 절 본문은
  건드리지 말고 자기 절에서 참조만" 이라고 지정했다. §5.3 의 왕복은 `restore.sh` 의 compose
  경로가 아니라 `openssl | gzip | docker exec mysql` 로 했다: `restore.sh` 를 끝까지 돌리면
  공용 dev Redis(DB 0)의 `puzzle:*`·`stats:*`·`lb:*` 를 지우는데, 다른 워커와 공유하는
  자원이라 건드리지 않았다. `restore.sh` 자체의 전 구간은 docker 스텁 테스트 20개가 본다.
- **감사 로그 기록 실패는 응답을 깨지 않는다**(로그만 ERROR → Sentry). 이미 커밋된 계정
  삭제를 500 으로 되돌리는 쪽이 더 거짓이라고 판단했다 — 근거는 `app/access_log.py` 주석.
- 전환기 평문 경로(`restore.sh` 의 `.sql.gz`, `backup.sh` 보존 정리의 `.sql.gz` 패턴)는
  **일부러 남겼다**. 제거 시점은 RELEASE "### 36." 의 "전환기 정리" 체크박스.
