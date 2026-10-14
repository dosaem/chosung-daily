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
| `app/services/apple_revocation_service.py` | 신설. `revoke_or_schedule_retry`, `retry_pending_revocations`(Beat), `RETRY_MAX_AGE = 7일` |
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
