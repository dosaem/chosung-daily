# 티켓 14 구현 증거 — 계정 삭제·웹 페이지·애플 연결 철회·재시도

- 날짜: 2026-10-14
- 브랜치: `dosaem/t14-account-deletion-apple-revoke` (로컬 `main` = `1e764da` 위로 rebase 완료 — 티켓 15 머지 포함)
- 환경: macOS (Darwin 25.3.0), uv / Python 3.12.14, MySQL 8 · Redis 7 (로컬 compose)
- 전용 테스트 자원: DB `chosung_daily_test_t14`, 마이그레이션 DB
  `chosung_daily_test_t14_migrations`, Redis DB **2**
  (`TEST_DATABASE_URL` / `TEST_MIGRATION_DATABASE_URL` / `TEST_REDIS_URL` 로 지정 —
  공용 테스트 DB·Redis 와 다른 워커의 DB 는 비우지도 지우지도 않았다. 두 DB 는
  `CREATE DATABASE IF NOT EXISTS` + 그 두 DB 에만 GRANT 로 만들었다)
- 외부 호출 0건: **애플·구글·Slack 어디에도 실제 요청을 보내지 않았다.** 애플
  토큰/철회 호출은 `requests.post` 대역으로 받은 인자를 검사하고, 운영자 알림은
  `notify_operator` monkeypatch 로 확인했다.
- 키·토큰·비밀번호를 파일·로그·이 문서에 적지 않았다(설정 **이름**만). `.env`,
  `.env.prod*` 는 열지도 고치지도 않았다. 계정 생성·결제·인증 정보 입력 없음.
- 프로덕션에 닿는 행동 없음: 배포·`git push`·NAS 접속 없음. `.scratch/` 의
  스펙·티켓·디자인 파일은 고치지 않았다.

## 1. 변경 파일

| 파일 | 내용 |
|---|---|
| `app/models/apple_revocation_retry.py` | 신설. `AppleRevocationRetry(id, refresh_token_enc, client_id, created_at)` — `guest_id` 없음(그 시점에 게스트 행이 없다) |
| `app/models/__init__.py` | 새 모델 export |
| `migrations/versions/94a83f12fddb_add_apple_revocation_retry_table.py` | 신설. `apple_revocation_retry` 테이블. `down_revision = dae1b5af0cf7`(티켓 06 머지 리비전) |
| `app/services/account_deletion_service.py` | 신설. `delete_guest_account` — 5개 자식 테이블 + Guest 한 트랜잭션 커밋 → 오늘 리더보드 ZREM(언어별) → 애플 철회 |
| `app/services/apple_revocation_service.py` | 신설. `schedule_revocation`·`complete_scheduled_revocation`(수정 라운드 1 에서 `revoke_or_schedule_retry` 를 쪼갰다 — D-14-3), `retry_pending_revocations`(Beat), `RETRY_MAX_AGE = 7일` |
| `app/clients/apple.py` | `APPLE_REVOKE_URL` + 외부 호출 래퍼 `revoke_refresh_token` 추가 |
| `app/services/puzzle_metrics.py` | `remove_from_leaderboard` (ZREM 한 줄) 추가 |
| `app/api/me.py` | `DELETE /api/v1/me` (Bearer) → 204 |
| `app/web.py` | `GET/POST /account/delete` + `_session_guest` / `_requested_ui_language` 헬퍼 |
| `web/templates/account/_layout.html` | 신설. 페이지 틀(ko/en 공통, `noindex`) |
| `web/templates/account/delete.ko.html` / `delete.en.html` | 신설. 확인 폼 / 안내 두 갈래 문구(언어별 1개씩) |
| `web/static/account.css` | 신설. 삭제 폼·destructive 버튼만 (레이아웃은 09 의 `legal.css`) |
| `web/static/app.js` | `discardDeletedAccountState()` — `?deleted=1` 이면 토큰·보드 기록 버리고 새 게스트 |
| `web/templates/legal/privacy.ko.html` / `.en.html` | §1·§6 h2 에 `id="collection"` / `id="rights"` (삭제 페이지가 가리키는 앵커) |
| `app/tasks/scheduled.py` | `tasks.retry_apple_revocations` + Beat `09:20` (KST) |
| `README.md` | "설계 판단" `### 14.`, API 표 3행, Beat 표 1행 + 수동 트리거 1줄 |
| `docs/RELEASE.md` | `### 14.` — 마이그레이션·Beat 재시작·Play Data safety 삭제 URL·웹 수동 체크리스트 |
| `tests/test_account_deletion.py` | 신설. 삭제 범위·커밋·ZREM·401 (12개) |
| `tests/test_apple_revocation.py` | 신설. 철회 래퍼·발급 client 별 자격증명·재시도·7일 폐기 (17개) |
| `tests/test_account_delete_page.py` | 신설. 웹 페이지 렌더·세션·CSRF·GET 무변경 (23개). 세션은 티켓 15 가 conftest 에 넣은 공용 `web_login` 픽스처로 심는다 |
| `tests/test_celery_wiring.py` | 새 태스크·스케줄·위임 확인 추가 |
| `tests/test_migrations.py` | 새 테이블 왕복 + 외래 키 없음 확인 2개 추가 |
| `tests/test_web.py` | app.js 의 삭제 후 정리 호출 확인 1개 추가 |

새 환경변수·새 의존성은 없다.

## 2. 티켓 체크박스 ↔ 증거

| 티켓 체크박스 | 이걸 증명하는 것 |
|---|---|
| 삭제 서비스 함수 하나가 Attempt·GuestStats·Account·HintUnlock·Subscription·오늘 리더보드 ZREM(언어별)·Guest 를 한 트랜잭션으로 수행하고 커밋 | `tests/test_account_deletion.py::test_deletion_removes_every_row_of_that_guest`(테이블 6개를 각각 0 으로 확인), `::test_deletion_is_committed`(호출 뒤 `rollback()` 해도 되살아나지 않음), `::test_todays_leaderboard_entry_is_removed_for_every_language`(ko·en 각각 `ZSCORE` None), `::test_other_guests_records_are_untouched`, `::test_other_guests_keep_their_leaderboard_entry` |
| 삭제 후 Bearer 요청 401 | `::test_delete_me_returns_no_content_and_invalidates_the_token`(삭제 → 204 → 같은 헤더로 `/puzzles/today` 401 `UNAUTHORIZED`), `::test_delete_me_twice_is_unauthorized_the_second_time` |
| `GET /account/delete`: 세션이면 확인 폼(ko/en, 되돌릴 수 없음·구독 별도 해지, 09 토큰 CSS), 아니면 안내 + 운영자 메일 | `tests/test_account_delete_page.py::test_confirm_form_warns_that_deletion_is_permanent`, `::test_confirm_form_warns_in_english_too`, `::test_page_without_a_session_explains_how_to_delete`(mailto + 폼 없음), `::test_page_without_a_session_still_renders_in_english`, `::test_lang_query_beats_accept_language`, `::test_page_declares_its_language`. 토큰 CSS 는 `_layout.html` 이 `tokens.css`+`legal.css`+`account.css` 를 링크 — §4 의 `impeccable detect` 가 실제로 그 CSS 를 파싱해 0건 |
| `POST`: 세션 없음 401, CSRF 불일치 403, 성공 시 세션 비우고 `/` 리다이렉트 | `::test_post_without_a_session_is_unauthorized`(401), `::test_post_with_a_wrong_csrf_token_is_forbidden` / `::test_post_without_a_csrf_token_is_forbidden`(403 `FORBIDDEN` + 게스트 살아 있음), `::test_submitting_the_form_deletes_the_account_and_sends_the_browser_home`(302 → `/?deleted=1` + 게스트 없음), `::test_session_is_emptied_so_the_next_page_is_a_fresh_visitor`, `::test_post_from_a_second_tab_after_deletion_is_unauthorized`, `::test_replaying_the_form_cannot_delete_a_second_time` |
| GET 은 상태 변경 없음(테스트) | `::test_get_never_deletes_anything`(ko·en GET 두 번 뒤 게스트 그대로), `::test_each_render_issues_a_fresh_token` |
| 애플 revoke: `clients/apple.py` 래퍼 + 저장된 `refresh_token`·`provider_client_id` 에 맞는 client_id·client_secret (iOS=번들 ID, 웹=Services ID; 11 의 공개 접근자) | `tests/test_apple_revocation.py::test_revoke_posts_the_refresh_token_to_apples_revoke_endpoint`(URL·바디·타임아웃), `::test_revoke_raises_when_apple_rejects_the_call`, **`::test_ios_linked_account_is_revoked_with_the_app_bundle_id`** 와 **`::test_web_linked_account_is_revoked_with_the_services_id`** — 두 경우 각각 `client_id` 가 맞고 `client_secret` JWT 의 `sub` 가 그 client_id 임을 디코드해서 확인. `::test_google_account_deletion_never_calls_apple`, `::test_guest_without_any_account_never_calls_apple` |
| revoke 실패 시 삭제는 진행 + `AppleRevocationRetry(refresh_token_enc, client_id, created_at)` 행 생성(마이그레이션, `flask db heads` 1개) | `::test_failed_revoke_still_deletes_the_account_and_records_a_retry`(게스트 없음 + 행 1개, 저장된 값이 **암호문 그대로**이고 평문이 아님), `::test_successful_revoke_leaves_no_retry_row`, `::test_a_token_that_cannot_be_decrypted_does_not_break_deletion`, `::test_apple_account_without_a_stored_client_cannot_be_revoked`. 마이그레이션: `tests/test_migrations.py::test_apple_revocation_retry_table_round_trips`, `::test_apple_revocation_retry_rows_outlive_the_deleted_guest`. `flask db heads` = 1줄 (§5) |
| Beat 매일 재시도, 7일 초과 폐기 + `notify_operator` | `::test_retry_removes_the_row_when_apple_accepts`, `::test_retry_keeps_the_row_while_apple_keeps_failing`, `::test_a_row_older_than_seven_days_is_discarded_and_the_operator_is_told`(폐기 + 알림 1건, 알림 본문에 토큰 없음·client_id 있음), `::test_a_row_at_seven_days_is_still_retried_not_discarded`(경계), `::test_one_bad_row_does_not_stop_the_others`, `::test_nothing_pending_means_no_apple_call`. 배선: `tests/test_celery_wiring.py::test_tasks_are_registered`, `::test_beat_schedule_matches_spec_times`(09:20 매일), `::test_tasks_delegate_to_the_service_functions` |
| 웹 프론트: 삭제 성공 리다이렉트 후 localStorage 토큰 버리고 새 게스트(JS 최소 변경 + 수동 체크리스트) | `tests/test_web.py::test_static_js_discards_the_token_after_account_deletion`(번들에 `params.has("deleted")`·`safeStorageRemove(TOKEN_KEY)`·`discardDeletedAccountState();`). 서버 쪽 신호는 `::test_submitting_the_form_deletes_the_account_and_sends_the_browser_home` 의 `Location: /?deleted=1`. 수동 체크리스트는 `docs/RELEASE.md` "### 14." 5항목 — **브라우저로 직접 눌러본 건 아니다**(§6) |
| 확인 페이지에 삭제되는 데이터 목록(방침 "수집하는 정보" 절과 같은 이름) + 방침 파기·권리 절 링크. 문구는 ko/en 템플릿, 테스트는 핵심 단어만 | `::test_confirm_form_lists_the_data_with_the_privacy_policy_names`(ko 5개·en 5개 이름을 방침에서 그대로 복사해 고정), `::test_confirm_form_links_the_policy_retention_and_rights_sections`(`/privacy?lang=..#collection`·`#rights`), `::test_policy_has_the_anchors_the_delete_page_links_to`(앵커가 방침에 실제로 있음). 핵심 단어만 고정: "되돌릴 수 없"·App Store·Google Play·해지 / "cannot be undone"·cancel |
| `impeccable detect` 0건(`/account/delete`), README "설계 판단" 추가, Play Data safety 삭제 URL 명시 | §4 (URL 4개 + CSS 파일 0건, 대조군 7건으로 탐지기 생존 확인). README `### 14. 계정 삭제 — 한 커밋 · 애플 revoke 재시도`(1177줄~). Play Data safety 삭제 URL = `docs/RELEASE.md` "### 14." 4항 |
| 분할선(세션 모자라면 revoke 재시도를 뒤로 떼기) | **쓰지 않았다** — 재시도 테이블·Beat·7일 폐기까지 이 티켓에서 다 구현했다. 코디네이터에게 알릴 분할 없음 |

## 3. 테스트·린트 실행

전용 자원을 환경변수로 지정해서 돌렸다(아래 모든 실행에 공통):

```
TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t14?charset=utf8mb4"
TEST_REDIS_URL="redis://localhost:6379/2"
TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t14_migrations?charset=utf8mb4"
```

### 3.1 전체 스위트 (rebase 후)

```
$ uv run pytest -q
........................................................................ [ 99%]
.                                                                        [100%]
793 passed in 748.40s (0:12:28)
(exit=0)
```

`main`(`1e764da`, 티켓 15 머지) 위로 rebase 한 뒤의 실행이다. 시간이 긴 건 같은 MySQL 인스턴스에
다른 워커 3~4개가 동시에 `create_all`/`drop_all` 을 돌리고 있어서다(테스트 자체는
각자 다른 DB 를 쓴다 — `information_schema.processlist` 로 확인: 각 워커가 자기
`chosung_daily_test_tNN` 에서만 DDL 을 돌리고 서로 잠그고 있지 않다).

### 3.2 이 티켓의 테스트만

아래 4개는 **구현 중**(티켓 15 머지 전 `main` = `148715b` 기준) 실행이다 —
최종 트리의 결과는 §3.1 의 전체 스위트(793 passed)가 덮는다.

```
$ uv run pytest tests/test_account_deletion.py tests/test_apple_revocation.py -q
.........................                                                [100%]
25 passed in 31.50s

$ uv run pytest tests/test_migrations.py -q
..........                                                               [100%]
10 passed in 74.55s (0:01:14)

$ uv run pytest tests/test_celery_wiring.py -q
.....                                                                    [100%]
5 passed in 11.31s

$ uv run pytest tests/test_account_delete_page.py tests/test_web.py tests/test_legal_pages.py -q
........................................................................ [ 57%]
.....................................................                    [100%]
125 passed in 810.51s (0:13:30)
```

### 3.3 ruff

```
$ uv run ruff check .
All checks passed!
```

`ruff check` 가 CI 게이트다(`.github/workflows/ci.yml`). `ruff format --check .` 는
이 레포에서 게이트가 아니고 기존 파일 12개가 이미 안 맞는다 — 내가 새로 만들거나
고친 파일만 맞춰 뒀다:

```
$ uv run ruff format --check app/web.py app/services/account_deletion_service.py \
    app/services/apple_revocation_service.py app/models/apple_revocation_retry.py \
    app/api/me.py app/clients/apple.py app/tasks/scheduled.py \
    tests/test_account_deletion.py tests/test_apple_revocation.py \
    tests/test_account_delete_page.py
10 files already formatted
```

`app/services/puzzle_metrics.py` 는 **포맷을 건드리지 않았다** — `ruff format` 이
고치려는 줄이 내가 추가한 줄이 아니라 기존 `record_leaderboard` 본문이라, 티켓
범위 밖의 포맷 변경을 커밋에 섞지 않았다.

## 4. `impeccable detect` — `/account/delete` 0건

`detect` 는 Jinja 템플릿을 직접 스캔하면 `url_for` 를 못 풀어 CSS 를 못 읽는다
(티켓 01·09 가 남긴 메모). 그래서 **개발 서버를 띄우고 URL 로** 돌렸다. 로그인된
확인 폼은 세션이 필요해서 detect 가 직접 못 보므로, 렌더된 HTML 을 `web/static/`
아래에 임시로 떠서 같은 서버의 URL 로 스캔했다(ko/en × 안내/확인 폼 4개).

사용 바이너리: `/Users/saem/.impeccable/bin/0.1.14/impeccable`.

```
$ FLASK_ENV=testing uv run flask --app wsgi run --port 5114     # (백그라운드)

$ impeccable detect "http://127.0.0.1:5114/account/delete?lang=ko"           → exit=0
$ impeccable detect "http://127.0.0.1:5114/account/delete?lang=en"           → exit=0
$ impeccable detect "http://127.0.0.1:5114/static/_t14_form_ko.html"         → exit=0
$ impeccable detect "http://127.0.0.1:5114/static/_t14_form_en.html"         → exit=0
$ impeccable detect "http://127.0.0.1:5114/static/_t14_anon_ko.html"         → exit=0
$ impeccable detect "http://127.0.0.1:5114/static/_t14_anon_en.html"         → exit=0
$ impeccable detect web/static/account.css                                   → exit=0
```

출력이 비고 exit=0 이면 findings 0건이다(티켓 01·09 증거와 같은 해석).
임시 스냅샷 4개(`web/static/_t14_*.html`)는 확인 직후 지웠고 커밋에 없다
(`git status` clean — §5).

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 대조군으로 확인했다** — 폐기된
V2 목업(`TOOLS.md` 에 7건으로 기록된 파일):

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b     (×4)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.
exit=2
```

### 4.1 destructive 버튼 글자색 — 대비 계산

OVERRIDES §2 는 destructive 색만 정하고 "그 면 위 글자색" 은 정하지 않는다. 새 토큰을
만들지 않고 `--color-on-primary-button`(라이트 `#ffffff` / 다크 `#141a26`)을 썼다 —
WCAG AA(4.5:1) 를 양쪽에서 넘기는 유일한 조합이다:

| 모드 | 면 | 글자 | 대비 | 판정 |
|---|---|---|---|---|
| 라이트 | `#dc2626` | `#ffffff` | 4.83:1 | 통과 |
| 다크 | `#ef4444` | `#ffffff` | 3.76:1 | **미달 — 쓰지 않음** |
| 다크 | `#ef4444` | `#141a26` | 4.83:1 | 통과 |

다크에서 밝은 면 위에 어두운 글자를 쓰는 건 이 디자인 시스템의 기존 규칙과 같다
(`--color-tile-text-on-correct: #052e16`). 계산식과 값은 `web/static/account.css`
주석에 그대로 적어 뒀다.

## 5. 마이그레이션·리베이스·작업 트리

```
$ flask db heads        # DATABASE_URL = chosung_daily_test_t14_migrations
94a83f12fddb (head)

$ flask db upgrade      # dae1b5af0cf7 -> 94a83f12fddb
$ flask db downgrade dae1b5af0cf7   # 되돌림 확인
$ flask db upgrade                  # 다시 적용 확인
```

```
$ git rebase main    # 두 번 돌렸다 — 148715b, 그리고 티켓 15 머지 후 1e764da. 둘 다 충돌 없음
Successfully rebased and updated refs/heads/dosaem/t14-account-deletion-apple-revoke.

$ git log --oneline main..HEAD    # 커밋 5개 (해시는 rebase 로 바뀌므로 제목만)
docs(14): 구현 증거 — 체크박스별 근거·전체 스위트·detect 0건
test(14): 삭제 페이지 세션 픽스처를 공용 web_login 으로 바꿔 중복 제거
docs(14): README 설계 판단·API 표, RELEASE 배포 준비물·수동 체크리스트
feat(14): 웹 /account/delete 확인 페이지 — 세션·CSRF·삭제 후 새 게스트
feat(14): 계정 삭제 서비스·DELETE /me·애플 연결 철회와 재시도

$ git status --short
(출력 없음 — clean. 이 문서를 담는 마지막 커밋 뒤 기준)
```

## 6. 안 한 것 / 한계 (숨기지 않음)

1. **브라우저로 직접 눌러보지 않았다.** 삭제 폼 제출·리다이렉트·localStorage 정리는
   서버 응답(`Location: /?deleted=1`)과 번들 내용으로만 검증했다. JS 테스트 러너가
   레포에 없고(기존 `tests/test_web.py` 도 같은 방식), 실제 클릭 경로는
   `docs/RELEASE.md` "### 14." 의 수동 체크리스트로 넘겼다.
2. **애플에 실제 철회 요청을 보내지 않았다.** 요청 URL·바디·자격증명(client_id 와
   그 client_id 로 서명된 secret)까지는 테스트가 고정하지만, 애플이 그 조합을
   실제로 받아주는지는 실제 Apple 계정·키가 필요해서 사람이 확인할 몫이다
   (같은 체크리스트 마지막 항목).
3. **`ruff format --check .` 는 레포 전체로는 실패한다** — 내 파일 때문이 아니라
   기존 12개 파일 때문이고, 이 레포는 그걸 게이트로 쓰지 않는다(§3.3).
4. **커밋 뒤 정리의 잔여 위험을 남겨 뒀다.** 커밋 직후 Redis 가 죽어 있으면 오늘
   리더보드에 지워진 게스트의 익명 항목이 남는다(`safe_redis_call` 이 삼킨다).
   삭제를 막는 쪽보다 이쪽이 싸다고 판단한 근거는 README "설계 판단 14" 2항에 적었다.
5. **스펙 "미정 11"(7일 폐기 정책 적절성)은 열어 뒀다.** 운영 데이터 보고 결정할
   항목이라 스펙 파일을 고치지 않았고, 코드에서는 `RETRY_MAX_AGE` 상수 하나만
   바꾸면 되도록 해뒀다.
6. **삭제 데이터 목록 문구의 법 기준 점검은 하지 않았다** — 티켓 16 의 범위다.
   그래서 문구는 템플릿에만 두고 테스트는 핵심 단어만 고정했다(티켓 지시대로).
7. **`provider_client_id` 가 없는 애플 계정은 철회를 건너뛴다**(재시도 행도 안
   만든다). 티켓 10·11 이후의 연결은 항상 두 값을 같이 저장하므로 실제로는 안
   생기는 상태지만, 옛 행이 있다면 애플 쪽 연결이 남는다 —
   `::test_apple_account_without_a_stored_client_cannot_be_revoked` 가 그 동작을
   고정하고 로그에 경고를 남긴다.

## 수정 라운드 1

최종 리뷰(`review/impl-review-14.md` 라운드 1, 판정 FAIL)의 MAJOR 3건을 고쳤다.
BLOCKER·MINOR 는 없었다. 각 결함을 **리뷰에 적힌 재현 방법 그대로 먼저 재현하고,
그 재현을 실패하는 테스트로 고정한 뒤** 고쳤다. 테스트 자원은 라운드 1 과 같다
(`TEST_DATABASE_URL` = `chosung_daily_test_t14`, `TEST_REDIS_URL` = Redis DB 2).

### D-14-1 — 임의 `?deleted` 링크로 살아 있는 게스트의 토큰·기록이 지워졌다

- **원인**: `discardDeletedAccountState()`(web/static/app.js)가 **쿼리 키의 존재만**
  보고 `chosung_token` 과 `chosung_history_*` 를 지웠다. 그 신호는 서버 삭제의
  증거가 아니다 — 외부 사이트가 보낸 `/?deleted=1` 링크로도 붙고, 삭제 POST 의
  CSRF 방어를 거치지 않는다. 증상(지워짐)이 아니라 "증거 없이 지운다" 가 원인이다.
- **수정**: 신호를 받으면 **저장된 토큰이 정말 죽었는지 서버에 먼저 확인한다** —
  `guestTokenIsGone(token)` 이 옛 토큰으로 `GET /api/v1/me/history?days=1` 를 불러
  401 이면 true, 2xx 면 false, 확인 자체를 못 했으면(오프라인·5xx) null. true 일
  때만 토큰·보드 기록을 버린다. false 면 주소창의 신호만 지우고 저장소는 그대로
  두고, null 이면 아무것도 지우지 않고 신호도 남겨 다음 로드에서 다시 확인한다
  ("모른다" 와 "지워졌다" 를 섞으면 네트워크가 끊겼을 때 멀쩡한 토큰을 버린다).
  `init()` 이 `await` 로 부른다 — 확인이 끝나기 전에 `ensureToken()` 이 돌면
  순서가 뒤집힌다.
- **재현·증명**: 리뷰와 같은 방식(실제 `web/static/app.js` 를 Node `vm` 에서 실행,
  대역은 localStorage·DOM·fetch·location 뿐)을 테스트 자원으로 만들었다 —
  `tests/fixtures/js/deleted_state_harness.mjs` + `tests/test_web.py` 3개.
  수정 전 실행(살아 있는 토큰 시나리오)에서 재현됐다:

```
tests/test_web.py::test_deleted_signal_in_a_link_cannot_discard_a_living_guests_token
>       assert out["originalTokenRetained"] is True
E       assert False is True
tests/test_web.py::test_deleted_signal_keeps_the_token_when_the_check_cannot_reach_the_server
>       assert out["originalTokenRetained"] is True
E       assert False is True
2 failed, 1 passed
```

  수정 후:

```
$ uv run pytest tests/test_web.py -k deleted_signal -v
tests/test_web.py::test_deleted_signal_discards_the_token_only_after_the_server_confirms_deletion PASSED
tests/test_web.py::test_deleted_signal_in_a_link_cannot_discard_a_living_guests_token PASSED
tests/test_web.py::test_deleted_signal_keeps_the_token_when_the_check_cannot_reach_the_server PASSED
3 passed, 4 deselected in 0.18s
```

- 리뷰가 지적한 "기존 검증의 빈틈"(번들 문자열만 보는 `tests/test_web.py`)을 이
  하네스가 메꾼다: 이제 그 분기의 **동작** 이 테스트 대상이다. Node 가 없는
  환경에서는 세 테스트가 `skip` 된다(레포는 런타임에 Node 를 쓰지 않는다).

### D-14-2 — 폼을 그린 뒤 계정을 전환하면 전환 **후** 게스트가 지워졌다

- **원인**: 확인 폼이 "누구를 지우는 폼인가" 를 들고 있지 않았다. CSRF 토큰은
  "이 폼을 우리가 그려줬다" 만 증명하고 세션 전환 뒤에도 유효한데, POST 가
  삭제 대상을 **제출 시점의** `current_guest_id` 로 다시 조회해서 대상이 바뀌었다.
- **수정**: 폼을 그릴 때 CSRF 토큰과 **삭제 대상 게스트 id** 를 같은 자리에서
  심고(`_issue_form_for`, 세션 키 `delete_target_guest_id`), POST 는 세션 게스트가
  그 대상과 같을 때만 지운다. 다르면 `403 FORBIDDEN` — 화면을 다시 받아야 한다.
  순서는 그대로 세션(401) → 대상 일치(403) → CSRF(403) 다.
- **재현·증명**: `tests/test_account_delete_page.py` 2개. 수정 전:

```
tests/test_account_delete_page.py::test_a_form_rendered_for_another_guest_is_refused_after_a_session_switch
>       assert res.status_code == 403
E       assert 302 == 403
E        +  where 302 = <WrapperTestResponse streamed [302 FOUND]>.status_code
```

  수정 후(전환 뒤 화면을 다시 받으면 정상 삭제되는 것까지 같이 고정):

```
$ uv run pytest tests/test_account_delete_page.py -k switch -v
...::test_a_form_rendered_for_another_guest_is_refused_after_a_session_switch PASSED
...::test_the_switched_guest_can_delete_itself_from_a_freshly_rendered_form PASSED
2 passed, 22 deselected in 3.45s
```

### D-14-3 — 삭제 커밋과 철회 의무 저장이 분리돼 자격증명이 유실될 수 있었다

- **원인**: 순서가 "삭제 커밋 → 애플 호출 → (실패하면) 재시도 행 INSERT + 커밋"
  이었다. 그 사이에서 DB·프로세스가 죽으면 계정만 지워지고 유일한 철회 자격증명
  (암호문 refresh token + 발급 client)이 사라진다 — 게스트 행이 없어 아무도 다시
  만들어낼 수 없고, 같은 Bearer 의 재요청도 401 이다.
- **수정**: 철회 **의무를 삭제와 같은 커밋**에 넣었다. `revoke_or_schedule_retry`
  를 둘로 쪼갰다: `schedule_revocation()` 은 `AppleRevocationRetry` 행을 세션에
  더하고 **커밋하지 않으며**(삭제 트랜잭션이 같이 커밋한다),
  `complete_scheduled_revocation()` 은 커밋 뒤에 애플 호출을 한 번 하고 성공하면
  그 행을 지운다. 실패하면 행이 남아 Beat 가 매일 재시도한다(기존 동작 그대로).
  남는 대가는 Beat 가 "방금 삭제돼 아직 철회 중인" 행을 집어 올 수 있다는 것뿐이고,
  같은 토큰에 철회가 두 번 가도 애플 쪽 결과는 같다(코드 주석·README §14 4항).
- **재현·증명**: `tests/test_apple_revocation.py` 2개. 리뷰의 재현(커밋 두 번째
  호출을 `OperationalError` 로 막기)을 그대로 쓴 쪽과, 커밋 직후 프로세스가 죽는
  쪽(`_revoke` 가 예외) 둘 다 고정했다. 수정 전 둘 다 실패했고(전자는
  `revoke_or_schedule_retry` 의 `db.session.commit()` 에서 터지고 재시도 행이
  남지 않았다), 수정 후:

```
$ uv run pytest tests/test_apple_revocation.py -k "duty or outage" -v
...::test_the_revocation_duty_is_committed_together_with_the_deletion PASSED
...::test_a_failed_revoke_survives_a_db_outage_after_the_deletion_commit PASSED
2 passed, 16 deselected in 3.64s
```

- 기존 경계 동작은 그대로다: `provider_client_id` 가 없으면 행을 만들지 않고
  (`::test_apple_account_without_a_stored_client_cannot_be_revoked`), 복호화 실패는
  행을 남긴다(`::test_a_token_that_cannot_be_decrypted_does_not_break_deletion`).

### 틀렸다고 판단해 고치지 않은 지적

없다. MAJOR 3건 모두 재현됐다. 리뷰 "참고" 의 두 항목은 아래처럼 처리했다.

- `docs/RELEASE.md` §14 수동 체크리스트의 "삭제 전 … 옛 토큰 … 401" 문구가
  헷갈린다는 지적(결함 아님)은 한 줄로 고쳤다: "삭제 **뒤** … 401, 삭제 전에는
  200". 같은 체크리스트에 D-14-1·D-14-2 의 수동 확인 두 줄을 추가했다.
- Redis ZREM 이 DB 트랜잭션 밖이라는 지적은 설계대로다(README §14 2항, 위 §6-4).
  이번 라운드에서 바꾸지 않았다.

### 안 한 것 (이 라운드)

- 브라우저 클릭 E2E 와 실제 애플 철회 수락은 여전히 사람 몫이다
  (`docs/RELEASE.md` §14). D-14-1 은 이제 실제 `app.js` 를 실행해 검증하지만,
  브라우저 엔진이 아니라 Node `vm` 이다.
- `impeccable detect` 는 다시 돌리지 않았다 — 이 라운드에서 템플릿·CSS 를 한
  글자도 바꾸지 않았다(변경 파일: `app/web.py`, `app/services/*`,
  `web/static/app.js`, 테스트·문서).
