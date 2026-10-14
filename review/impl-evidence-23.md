# 티켓 23 구현 증거 — 운영자 배정표·잔량·점검/최소 버전 토글·Google Books 검색

- 브랜치: `dosaem/t23-admin-schedule-stock-toggles-books`, 로컬 `main` **`7df7809`**
  (티켓 14 머지) 위로 rebase. 충돌 없음, 작업 트리 clean. 작업 중 main 이 티켓
  22·24·14 머지로 세 번 올라가서 마지막 base 에서 전체 검증을 다시 돌렸다(§3.2).
- 테스트 자원(워커 전용): DB `chosung_daily_test_t23` / Redis DB `11` /
  마이그레이션 DB `chosung_daily_test_t23_migrations`
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`). 공용 테스트
  DB·Redis DB 는 건드리지 않았다(다른 워커 컨테이너도 내리지 않았다).
- **마이그레이션 없음** — 새 테이블·컬럼이 없다. 배정 교체는 기존 `daily_puzzle` 행을
  고치고, 토글은 기존 `app_setting` 키·값 테이블(티켓 08)에 쓰고, `GOOGLE_BOOKS_API_KEY`
  는 설정값이다. Alembic head 는 main 그대로 1개.
- 프로덕션에 닿는 행동 없음: `git push` 없음, 외부 서비스 호출 없음(Google Books 는
  테스트·스냅샷 모두 가짜 `requests.get` 으로 대체). 시크릿 값은 이 문서에 없다 —
  키 **이름**만 적는다(`GOOGLE_BOOKS_API_KEY`).

## 1. 바꾼 것

| 파일 | 무엇 |
|---|---|
| `app/services/puzzle_schedule_service.py` | `SCHEDULE_DAYS=30`, `ScheduledDay`, `upcoming_schedule(language, days)`(읽기 전용), `replace_assignment(date, language, word_id)`(시도·지난 날짜·언어 검증 + 캐시 무효화). `schedule_puzzles` 의 `days` 기본값을 같은 상수로 |
| `app/services/app_config_service.py` | `OperatorSettings`, `get_operator_settings()`(DB 직접), `save_operator_settings(...)`(버전 형식·메시지 필수·길이 검증 → 한 커밋 → 캐시 무효화), `invalidate_app_config_cache()`, 빈 점검 메시지는 `/config` 에서 `null` |
| `app/services/book_lookup_service.py` | `search_google_books(query, size)`(카카오와 같은 시그니처), `_pick_isbn`. `search_books`(ko 합성)는 그대로 |
| `app/clients/google_books.py` (신규) | 호출 한 함수 `search_volumes(query, size)` — `intitle:` 제목 검색, `langRestrict=en`, 5초 타임아웃, 키는 선택 |
| `app/services/word_service.py` | `add_word_from_book` 이 `parse_word_input` 으로 검증(제목 50자 초과 거부) |
| `app/repositories/puzzle_repository.py` | `list_in_range(language, start, end)` — 배정표 30일을 쿼리 한 번으로(단어는 `joinedload`) |
| `app/repositories/attempt_repository.py` | `count_by_puzzle(puzzle_ids)` — 퍼즐별 시도 수 GROUP BY 한 번 |
| `app/repositories/app_setting_repository.py` | `save_settings(values)` — 여러 키 upsert 한 커밋 |
| `app/admin.py` | 라우트 7개: `GET /admin/schedule`, `GET·POST /admin/schedule/<date>/replace`, `GET·POST /admin/settings`, `GET·POST /admin/books`. `WEEKDAY_NAMES`, `_read_language`, `_read_schedule_target`(창 밖 404), `_render_settings` |
| `app/config.py` | `GOOGLE_BOOKS_API_KEY`(기본 빈 문자열 = 키 없이 호출) |
| `web/templates/admin/{schedule,schedule_replace,settings,books}.html` (신규) | 운영자 Jinja 페이지 4장 |
| `web/templates/admin/_layout.html` | 메뉴 3개 추가(배정표·책 검색·앱 설정) |
| `web/static/admin.css` | 언어 탭(brand 밑줄), 잔량 카드(+`admin-stock-low`), 날짜 칸, 체크박스 한 줄, 줄글 `max-width: 70ch` |
| `tests/test_admin_schedule.py`(21)·`test_admin_settings.py`(11)·`test_admin_books.py`(11)·`test_google_books.py`(9) (신규) | 52개 테스트 |
| `tests/test_puzzle_schedule_service.py`(+9)·`test_app_config.py`(+8)·`test_word_service.py`(+1) | 서비스 규칙 테스트 18개 추가(배정표 읽기·교체 금지·토글 검증·제목 길이). 이 티켓 전체 **+70** |
| `README.md` | API 표 4행, `## 운영: 배정표 · 잔량 · 점검 토글 · 책 검색 (/admin)` 절, 설계 판단 `### 23.` 4항목 |
| `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" | 자기 번호 블록(`[23]`, `### 23.`, `(티켓 23 반영) 미정 3 확정`) |
| `review/admin-detect-snapshot-23.py` (신규) | `impeccable detect` 용 스냅샷 생성 스크립트(§4) |

## 2. 티켓 체크박스 ↔ 증거

| 체크박스 | 무엇이 증명하나 | 결과 |
|---|---|---|
| 배정표 페이지: 언어 탭 | `test_admin_schedule.py::test_the_language_tab_switches_the_table`(ko 탭에 en 단어 없음·그 반대), `::test_an_unknown_language_falls_back_to_korean` | 2 pass |
| 오늘부터 30일, 05 의 `schedule_puzzles(language, days)` 재사용 | `::test_the_schedule_page_shows_thirty_days`(오늘·+29일 있고 +30일 없음) · 같은 모듈의 `SCHEDULE_DAYS` 를 `schedule_puzzles` 기본값과 `upcoming_schedule` 이 함께 쓴다 · `test_puzzle_schedule_service.py::test_upcoming_schedule_lists_every_day_of_the_window`(창 전체가 한 줄씩) | 2 pass |
| 각 날짜의 단어, 미배정은 "자정에 배정" | `::test_the_schedule_page_shows_the_assigned_word`, `::test_a_day_without_an_assignment_says_it_is_filled_at_midnight`, 서비스 쪽 `::test_upcoming_schedule_lists_every_day_of_the_window`(배정 여부 `[True, True, False, False, False]`) | 3 pass |
| 교체 폼 | `::test_the_replace_page_lists_candidate_words_of_that_language`(그 언어만), `::test_the_replace_page_can_be_searched`, `::test_replacing_a_future_day_swaps_the_word`(302 + DB + 배정표 반영), `::test_replacing_an_unassigned_day_assigns_the_word` | 4 pass |
| 교체 시 `puzzle:{date}:{lang}` 캐시 무효화 | `::test_replacing_today_drops_the_puzzle_cache` — **읽기 경로로 캐시를 먼저 채운 뒤** 교체하고, `get_today_puzzle_or_404` 가 새 단어를 주는지 본다(티켓 15 D-15-1 과 같은 함정) · 서비스 쪽 `test_replace_assignment_swaps_the_word_and_drops_the_cache` | 2 pass |
| 이미 시도가 있는 날짜(오늘·과거)는 교체 금지(테스트) | `::test_replacing_a_day_that_has_attempts_is_refused`(사유에 "시도", 단어 그대로), `::test_a_day_with_attempts_offers_no_replace_link`(링크 없음 + "교체 불가"), `::test_a_date_outside_the_window_is_not_found`(지난 날짜·30일 뒤 404), `::test_a_malformed_date_is_not_found` · 서비스 쪽 `test_replace_assignment_is_blocked_once_the_day_has_attempts`, `test_replace_assignment_rejects_a_past_date` | 6 pass |
| (교체 폼 CSRF·언어 불변식) | `::test_a_replacement_without_a_csrf_token_is_forbidden`(403 + 단어 그대로), `::test_a_word_of_the_other_language_is_refused`(사유에 "언어", 배정 0건) · 서비스 쪽 `test_replace_assignment_rejects_a_word_of_another_language`, `::_rejects_an_unknown_word` | 4 pass |
| 잔량 카드: 05 의 서비스 함수 재사용 | `::test_the_stock_card_counts_unused_words_per_language`(ko 2일치·en 1일치), `::test_an_assigned_word_leaves_the_stock`(배정된 단어는 잔량에서 빠진다 = `remaining_days_by_language` 규칙) — 뷰는 그 함수를 그대로 부른다(`app/admin.py`) | 2 pass |
| 14일 미만은 경고 색 | `::test_a_stock_under_two_weeks_is_marked_low`(`admin-stock-low` 클래스 + 임계값 문구), `::test_a_healthy_stock_is_not_marked_low`(14일치씩이면 안 붙는다). 임계값은 Slack 알림과 같은 `LOW_WORD_POOL_THRESHOLD_DAYS` | 2 pass |
| 점검 모드(on/off + 메시지)·최소 앱 버전 토글 → `AppSetting` 갱신 | `test_admin_settings.py::test_the_four_keys_are_the_ones_config_reads`(쓴 키 4개 = `/config` 가 읽는 키 4개), `::test_turning_maintenance_off_again_is_stored`(끄면 `false`, 메시지는 남는다), `test_app_config.py::test_saving_operator_settings_writes_the_rows`, `::test_saving_twice_updates_the_same_rows`(행이 늘지 않는다) | 4 pass |
| → `GET /config` 캐시 무효화(테스트: 토글 직후 `/config` 반영) | `test_admin_settings.py::test_turning_maintenance_on_shows_up_in_config_right_away` 와 `::test_raising_the_minimum_app_version_shows_up_in_config_right_away` — **먼저 `/config` 를 불러 캐시를 채운 뒤** 토글하고 같은 요청에서 새 값이 보이는지 본다 · `test_app_config.py::test_saving_drops_the_config_cache_so_apps_see_it_now` | 3 pass |
| (토글 검증·CSRF) | `::test_a_broken_version_is_refused_and_nothing_is_saved`, `::test_maintenance_without_a_message_is_refused`, `::test_a_refused_save_keeps_what_the_operator_typed`, `::test_saving_without_a_csrf_token_is_forbidden` · 서비스 쪽 `test_a_version_that_is_not_three_numbers_is_rejected`, `::test_maintenance_cannot_be_turned_on_without_a_message`, `::test_a_message_longer_than_the_column_is_rejected`, `::test_an_empty_maintenance_message_is_sent_as_null` | 8 pass |
| `clients/google_books.py` 래퍼(함수 하나) | `test_google_books.py::test_the_wrapper_searches_titles_only_and_asks_for_english_books`(URL·`intitle:`·`maxResults`·`langRestrict`·타임아웃), `::test_an_empty_result_set_comes_back_as_an_empty_list`, `::test_an_http_error_is_raised_to_the_caller` | 3 pass |
| 카카오 책 검색과 같은 서비스 함수 시그니처 | `search_google_books(query, size=5) -> list[BookSearchResult]` · `::test_results_are_mapped_to_the_same_shape_as_the_kakao_search`(ISBN_13 우선·`source="google_books"`), `::test_an_isbn_10_is_used_when_there_is_no_isbn_13`, `::test_missing_fields_become_none`, `::test_a_volume_without_a_title_is_skipped`, `::test_the_kakao_and_aladin_search_is_left_alone`(ko 합성에 안 섞인다) | 5 pass |
| 검색 결과에서 선택 → en 단어 추가(가림 자동) | `test_admin_books.py::test_choosing_a_result_adds_an_english_book_title_word`(en·`book_title`·힌트 `저자, 출판사`), `::test_the_mask_is_computed_when_the_word_is_added`(`Dune` → `r h r h` 모음 가림), `::test_adding_the_same_book_twice_does_not_duplicate_it`, `::test_a_book_without_an_author_gets_a_fallback_hint`, `::test_a_title_longer_than_the_answer_column_is_refused`, `::test_adding_without_a_csrf_token_is_forbidden` | 6 pass |
| (검색 화면) | `::test_the_books_page_opens_without_a_search`(검색어 없으면 구글 호출 0), `::test_a_search_lists_the_results`, `::test_a_search_with_no_result_says_so`, `::test_a_google_failure_is_shown_as_a_reason`(200 + 사유, 500 아님), `::test_the_books_page_needs_an_admin_session` | 5 pass |
| `GOOGLE_BOOKS_API_KEY` 선택 설정(미정 3) | `::test_the_api_key_is_sent_only_when_it_is_configured`(비면 `key` 파라미터 없음, 있으면 붙는다) · `app/config.py` 기본값 빈 문자열 · `.env.example` `[23]` 블록 · 스펙 "미정 항목" 에 `(티켓 23 반영) 미정 3 확정` 한 줄 | pass |
| `impeccable detect` 0건 | §4 — 새 화면 10개(배정표 ko/en·잔량 경고/정상·교체·교체 빈 결과·설정·설정 거부·책 검색 3종) 전부 0건, 모바일 폭 4개도 0건, 티켓 15 화면 7개 회귀 0건, 대조군으로 탐지기 생존 확인 | 0건 |
| README 운영 절 갱신 | `README.md` `## 운영: 배정표 · 잔량 · 점검 토글 · 책 검색 (/admin)` (배정표·교체 규칙·잔량 임계·토글·책 검색 네 단락) + API 표 4행 + 설계 판단 `### 23.` 4항목 | pass |

## 3. 실행 출력 (로컬 `main` `b8f63cc` 위로 rebase 한 뒤)

```
$ git rebase main
Rebasing (1/1)Successfully rebased and updated refs/heads/dosaem/t23-admin-schedule-stock-toggles-books.

$ git status --short
(출력 없음)

$ git log --oneline main..HEAD
<커밋 2개: 구현 + 이 증거 문서>
```

rebase 충돌은 없었다(두 번 모두). 시작 시점 main 은 `1e764da`(티켓 15 머지)였고,
작업 중 티켓 22·24 머지로 `b8f63cc`, 이어 티켓 14 머지로 `7df7809` 가 됐다. 아래는
`b8f63cc` 기준 출력이고, 최종 base `7df7809` 에서 다시 돌린 결과는 §3.2 다.

```
$ uv run ruff check .
All checks passed!
exit=0

$ FLASK_ENV=testing uv run flask --app wsgi db heads
dae1b5af0cf7 (head)
exit=0        ← 한 줄(= head 1개). 이 티켓은 마이그레이션을 만들지 않았다.

$ uv run pytest -q
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 61%]
........................................................................ [ 70%]
........................................................................ [ 79%]
........................................................................ [ 88%]
........................................................................ [ 97%]
.....................                                                    [100%]
813 passed in 479.34s (0:07:59)
exit=0
```

실패·skip·xfail **0**. 이 브랜치 시작 시점(main `1e764da`) 743 passed → 이 티켓
**+70** → 중간에 머지된 티켓 22·24 테스트가 합쳐져 813.

이 티켓 테스트만:

```
$ uv run pytest tests/test_admin_schedule.py tests/test_admin_settings.py \
    tests/test_admin_books.py tests/test_google_books.py \
    tests/test_puzzle_schedule_service.py tests/test_app_config.py \
    tests/test_word_service.py -q
(위 전체 실행에 포함 — 파일별 개수: admin_schedule 21 · admin_settings 11 ·
 admin_books 11 · google_books 9 · puzzle_schedule_service 18(+9) ·
 app_config 15(+8) · word_service 24(+1))
```

### 3.2 최종 base (`main` = `7df7809`, 티켓 14 머지) 재검증

```
$ git rebase main          # 충돌 없음
Rebasing (1/2)Rebasing (2/2)Successfully rebased and updated refs/heads/dosaem/t23-admin-schedule-stock-toggles-books.

$ uv run ruff check .
All checks passed!
exit=0

$ FLASK_ENV=testing uv run flask --app wsgi db heads
94a83f12fddb (head)
exit=0        ← 한 줄. 티켓 14 가 가져온 head 이고, 이 티켓은 마이그레이션이 없다.

$ uv run pytest -q
870 passed in 821.91s (0:13:41)
exit=0

$ git status --short
(출력 없음)

$ git log --oneline main..HEAD
5fb47c1 증거 23: 체크박스별 근거·테스트 출력·impeccable detect 0건
10c2746 티켓 23: 운영자 30일 배정표·잔량·점검/최소 버전 토글·Google Books 검색
```

(커밋 해시는 이 문서를 담은 커밋을 다시 쓰면서 바뀐다 — 내용은 위 두 커밋 그대로다.
`impeccable detect` 는 템플릿·CSS 가 이 rebase 로 바뀌지 않았으므로 §4 결과가 그대로
유효하다.)

### 3.1 red → green (TDD)

새 규칙은 **먼저 실패하는 테스트**로 고정한 뒤 구현했다. 수집 단계에서 빨간 것이
확인된 지점:

```
$ uv run pytest tests/test_puzzle_schedule_service.py -q     # 구현 전
ImportError: cannot import name 'replace_assignment' from 'app.services.puzzle_schedule_service'

$ uv run pytest tests/test_google_books.py -q                # 구현 전
ImportError: cannot import name 'google_books' from 'app.clients'
```

그 뒤 구현 → `18 passed` / `9 passed`. 교체·토글·책 등록의 HTTP 테스트도 같은
순서로 썼고(라우트가 없으면 404/405), 구현 후 전부 통과한다. 구현 중 **빨갛게 잡힌
실제 결함 2건**:

| 무엇 | 어떻게 드러났나 | 고친 것 |
|---|---|---|
| 언어 불일치 사유 문구에 "언어" 가 없었다 | `test_replace_assignment_rejects_a_word_of_another_language` 가 사유 정규식에서 실패(`'ko 퍼즐에는 ko 단어만...'`) | 사유를 "퍼즐과 단어의 언어가 다릅니다 — ..." 로 바꿔 운영자가 원인을 바로 읽게 했다 |
| 후보가 0건이면 교체 화면에 CSRF 토큰이 없다 | `test_a_word_of_the_other_language_is_refused` 가 토큰을 못 찾아 실패 | 결함이 아니라 테스트 설계 문제였다(폼이 없으면 토큰도 없다) — 후보 1개를 두고 "손으로 고친 요청" 을 재현하도록 테스트를 고쳤다. 코드는 그대로 |

## 4. `impeccable detect` — 새 화면 10개 0건

운영자 페이지는 **로그인 세션이 필요해서 detect 가 URL 을 직접 열 수 없다**(detect 의
브라우저에는 쿠키가 없고 `--header`/`--cookie` 옵션도 없다 — 티켓 15 증거와 같은 제약).
그래서 `review/admin-detect-snapshot-23.py` 가 티켓 15 와 같은 방식으로

1. 운영자 세션을 태운 **Flask 테스트 클라이언트로 실제 응답 HTML** 을 받고,
2. 링크된 스타일시트 경로(`/static/x.css?v=...`)만 같은 디렉터리의 복사본으로 바꾸고,
3. 그 디렉터리를 정적 서버로 띄워 detect 가 **URL 모드(실제 브라우저 + 실제 CSS)** 로
   보게 한다.

구글 책 검색은 스냅샷에서도 가짜 응답이다 — 스냅샷을 뽑을 때 외부 API 를 부르지 않는다.

```
$ FLASK_ENV=testing uv run python review/admin-detect-snapshot-23.py <snapshot-dir>
schedule_low.html ← /admin/schedule (잔량 경고)
schedule_en.html ← /admin/schedule?language=en
schedule_replace.html ← /admin/schedule/2026-10-15/replace
schedule_replace_empty.html ← 교체 화면 (검색 결과 없음)
settings.html ← /admin/settings
settings_error.html ← POST /admin/settings (거부)
books.html ← /admin/books?q=tolkien (결과 3건)
books_form.html ← /admin/books (검색 전)
books_empty.html ← /admin/books (결과 없음)
schedule_ok.html ← /admin/schedule (잔량 정상)
tokens.css (복사) / admin.css (복사)

$ (cd <snapshot-dir> && python3 -m http.server 5123 &)
$ npx impeccable detect --json --viewport <폭> "http://127.0.0.1:5123/<화면>.html"

detect schedule_low             1280x800  []  exit=0
detect schedule_ok              1280x800  []  exit=0
detect schedule_en              1280x800  []  exit=0
detect schedule_replace         1280x800  []  exit=0
detect schedule_replace_empty   1280x800  []  exit=0
detect settings                 1280x800  []  exit=0
detect settings_error           1280x800  []  exit=0
detect books                    1280x800  []  exit=0
detect books_form               1280x800  []  exit=0
detect books_empty              1280x800  []  exit=0
detect schedule_low             390x844   []  exit=0
detect schedule_replace         390x844   []  exit=0
detect settings                 390x844   []  exit=0
detect books                    390x844   []  exit=0
```

`[]` + exit=0 이면 findings 0건이다(티켓 01·09·15 증거와 같은 해석). CLI 는
`npx impeccable`(3.5.0).

**처음에는 0건이 아니었다** — 고친 2건을 그대로 적는다:

| 규칙 | 무엇이 떴나 | 고친 것 |
|---|---|---|
| `em-dash-overuse` (advisory) | 배정표에서 "32 em-dashes in body text" — 미배정 행마다 쓴 `—` 와 "시도 N건 — 교체 불가" 가 30행에 반복돼 밀도 임계를 넘었다 | 빈 카테고리 칸을 비우고, 문구를 "시도 N건 (교체 불가)" · "14일치 미만. CSV 를 올려 채워주세요" 로 바꿨다(표시 정보는 그대로) |
| `line-length` | 책 검색·설정 화면의 안내 문단이 "~142 chars/line (aim for <80)" | 줄글 클래스(`.admin-meta`·`.admin-empty`·`.admin-error`·`.admin-flash`·캡션)에 `max-width: 70ch`. 표는 1040px 를 계속 쓴다 |

**티켓 15 화면 회귀 없음** — 공유 CSS(`admin.css`)와 레이아웃 메뉴를 건드렸으니 15 의
스냅샷도 다시 뽑아 같은 방식으로 검사했다.

```
detect words / words_filtered / words_empty / word_new / word_edit / import /
       import_result   (1280x800)   전부 []  exit=0
```

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 대조군으로 확인했다.**

```
$ npx impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b   (×2)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.
```

### 디자인 파일과 다르게 구현한 점

운영자 화면은 **목업이 없다**(`design/SCREENS.md` "목업 파일 매핑" 에 운영자 화면이
없고, 디자인 부족 항목도 "웹 전체" 를 명세+토큰 구현으로 둔다). 그래서 디자인 시스템
토큰(`tokens.css` = OVERRIDES 표)만 쓰고 레이아웃은 `admin.css` 에 뒀다. 티켓 15 가
기록한 **의도적 이탈 한 가지를 그대로 따른다**: OVERRIDES §10 의 웹 폭 규칙(481px
이상에서 480px 고정) 대신 1040px 를 쓴다 — 30행 5열 배정표가 480px 에서는 잘린다.
나머지는 지켰다: §2 색 역할(brand 는 면 채움 금지 — 언어 탭 선택 표시는 brand **밑줄**,
잔량 경고는 destructive **테두리 + 문구**로 색만으로 구분하지 않는다), §3 타이포
스케일·Pretendard, §4 간격·모서리·44px 터치 타깃·그림자 없음, §9 다크 모드 추종.

이번에 한 가지를 더했다: 줄글(`.admin-meta`·`.admin-empty`·캡션·알림)에만
`max-width: 70ch` 를 걸었다. 표는 1040px 를 다 쓰지만 줄글이 그 폭을 쓰면 한 줄이
140자가 돼서 `impeccable detect` 의 `line-length` 가 떴다(실제로 떴고, 그래서 고쳤다).
`tests/test_admin_css.py` 의 기존 가드(색 리터럴 없음·brand 면 채움 없음·터치 타깃)는
새 CSS 에도 그대로 적용된다.

## 5. 직접 확인하지 않은 것 / 남은 것

- **실제 Google Books API 왕복은 하지 않았다.** 외부 호출 금지 제약이라 요청 모양
  (URL·파라미터·타임아웃)과 응답 매핑만 가짜 응답으로 고정했다. 실제 키·쿼터 확인은
  `docs/RELEASE.md` "### 23." 체크리스트로 넘겼다. 응답 필드명은 Google Books API v1
  의 `items[].volumeInfo.{title,authors,publisher,industryIdentifiers}` 를 기준으로 썼다.
- **사람 눈으로 본 스크린샷은 없다.** 레포 결정(헤드리스 브라우저 드라이버를 의존성으로
  들이지 않는다 — 티켓 09)을 따라 `impeccable detect` URL 모드(실제 브라우저가 CSS 를
  계산한다)와 CSS 구조 테스트로 대신했다.
- **같은 단어를 30일 안에 두 번 배정하는 것은 막지 않았다.** 후보 목록에 "이미 배정됨"
  만 붙인다 — 운영자가 일부러 같은 단어를 다시 낼 수도 있고(두 번 쓰는 기념일 단어),
  막으면 그 선택을 빼앗는다. 티켓에 요구가 없어 표시까지만 했다.
- **점검 모드를 켤 때 메시지를 필수로 했다.** 스펙은 `maintenance.message` 를 nullable
  로 두지만, 앱 점검 화면(S7)이 보여줄 문구가 그것뿐이라 빈 화면이 되는 조합을 막았다
  (끌 때는 메시지를 비워도 된다 — 켤 때만 요구한다). README "### 23." 에 근거를 남겼다.
- 교체 화면의 후보 폼들은 한 쪽에 렌더된 CSRF 토큰 하나를 공유한다(티켓 01·15 와 같은
  구조). 한 번 교체하면 배정표로 돌아가며 새 토큰을 받으므로 정상 흐름은 막히지 않지만,
  탭 두 개를 열어두고 양쪽에서 교체하면 나중 탭이 403 이다 — 운영자 두 명 규모에서
  폼별 토큰 보관을 만들 이유가 없다고 봤다(15 와 같은 판단).
- 운영자 페이지는 계속 ko 전용이다(운영자 두 명, 둘 다 한국어).

## 수정 라운드 1 (리뷰 라운드 1 FAIL 대응)

- 대상: `review/impl-review-23.md` "라운드 1" 의 BLOCKER 0 / **MAJOR 1(D-23-1)** / MINOR 0.
- base: 로컬 `main` **`a520223`** (티켓 17 머지). 리뷰 때의 base 는 `7df7809` 였고
  이 라운드 작업 중에 main 이 티켓 13 머지(`4d83feb`) → 티켓 17 머지(`a520223`) 로 두
  번 올라가서, 마지막 base 위로 다시 rebase 하고 전체 검증을 다시 돌렸다(§"최종 base
  재검증"). 충돌은 `4d83feb` rebase 때 1건뿐이었다: `.scratch/store-launch/spec.md`
  "미정 항목" 에 티켓 13 줄과 티켓 23 줄이 같은 자리에 붙어서 생긴 추가·추가 충돌 —
  두 줄을 모두 남겼다. `a520223` rebase 는 충돌 없음.
- 테스트 자원은 라운드 0 과 같다(DB `chosung_daily_test_t23`, Redis DB 11,
  `TEST_DATABASE_URL`·`TEST_REDIS_URL`). 공용 테스트 DB·Redis 는 건드리지 않았다.
- 틀렸다고 판단해 고치지 않은 지적: **없다**. D-23-1 은 재현됐고 원인도 리뷰가 지적한
  지점이 맞았다.

### D-23-1 (MAJOR) — 시도 없음 검사와 교체가 원자적이지 않음

**원인.** `replace_assignment` 이 `count_by_puzzle` 로 "시도 0건" 을 읽고 `word_id` 를
UPDATE 할 때까지 퍼즐 행에 잠금이 없었다. 제출(`submit_guess`)은 `GuestStats` 행만
잠그고 퍼즐 행은 캐시 또는 잠금 없는 SELECT 로만 읽어서, 두 트랜잭션이 서로를 전혀
막지 않았다. 그래서 (a) 검사 후 UPDATE 전에 제출이 커밋되는 순서, (b) 제출 도중에
교체가 커밋되는 순서 **둘 다** 양쪽이 성공했다 — 옛 정답으로 판정된 `Attempt` 행이
새 정답을 가리키고, `solved_count`·리더보드에는 옛 정답의 성공이 남는다. 증상(캐시)이
아니라 이 "검사와 쓰기 사이의 창" 이 원인이다.

**수정.** 두 경로가 같은 `daily_puzzle` 행을 잠그게 해서 검사-쓰기 창을 닫았다.

| 파일 | 무엇 |
|---|---|
| `app/repositories/puzzle_repository.py` | `lock_by_date(date, language)` — `SELECT ... FOR UPDATE`. `lock_shared_answer(puzzle_id)` — `word` 조인 + `LOCK IN SHARE MODE` 로 현재 정답을 읽는다 |
| `app/services/puzzle_schedule_service.py` | `replace_assignment` 이 `find_by_date` → `lock_by_date` 로 바꿔, **잠근 뒤에** 시도를 센다 |
| `app/services/guess_service.py` | `_hold_the_puzzle_answer(puzzle, answer)` — `GuestStats` 잠금 뒤 퍼즐 행을 공유 잠금으로 잡고 정답이 그대로인지 재확인. 바뀌었으면 캐시를 지우고 `PuzzleChangedError`(409 `PUZZLE_CHANGED`) |
| `README.md` | 설계 판단 `### 23.` 에 잠금 설계와 "제출 쪽을 FOR UPDATE 로 하지 않은 이유" 추가 |

제출 쪽을 배타 잠금으로 하지 않은 이유: 같은 퍼즐을 푸는 모든 제출이 한 줄로 서게
된다. 공유 잠금은 제출끼리 서로를 막지 않으면서 교체의 `FOR UPDATE` 만 막는다.
실제로 나가는 SQL:

```
lock_by_date:        SELECT daily_puzzle.id, ... FROM daily_puzzle
                     WHERE daily_puzzle.puzzle_date = %s AND daily_puzzle.language = %s FOR UPDATE
lock_shared_answer:  SELECT word.answer FROM word
                     INNER JOIN daily_puzzle ON daily_puzzle.word_id = word.id
                     WHERE daily_puzzle.id = %s LOCK IN SHARE MODE
```

그래서 어느 쪽이 먼저 와도 뒤에 온 쪽이 앞의 결과를 보고 멈춘다:

- 제출이 퍼즐 행을 먼저 잡으면 → 교체가 그 커밋을 기다렸다가 "시도 1건" 으로 거부.
- 교체가 먼저 잡으면 → 제출이 교체 커밋까지 기다렸다가 바뀐 정답을 읽고
  `PUZZLE_CHANGED`. 시도 행도 통계도 남지 않는다(= 리뷰의 "새 퍼즐 기준 재검증").

**재현 테스트.** `tests/test_concurrency.py` 에 두 순서를 각각 고정한 테스트를 더했다
(기존 파일의 패턴 그대로 — 실제 MySQL 두 세션 + 스레드, 가짜 값 없음. 잠금 순서는
`threading.Event` 로 못 박아서 간헐 실패가 없다).

- `test_replacement_that_wins_the_lock_turns_the_submission_away` — 교체가 "시도 0건"
  을 읽은 직후 제출이 들어오는 순서(리뷰의 재현과 같은 순서).
- `test_submission_that_wins_the_lock_blocks_the_replacement` — 제출이 정답을 잡은
  도중에 교체가 들어오는 반대 순서(리뷰가 "반대 순서의 경합이 남을 수 있다" 고 적은 쪽).

둘 다 "둘 중 하나만 성공" 을 확인하고, 복원된 보드까지 본다 — 성공으로 복원된 보드의
정답 행은 글자가 전부 맞아야 한다(모순된 보드를 그대로 잡는 조건).

구현 **전**(HEAD~1 의 세 파일로 되돌려서) 두 테스트가 실제로 실패하는 것을 먼저 봤다 —
양쪽이 다 성공하는 게 결함의 모양이다:

```
$ git checkout HEAD~1 -- app/repositories/puzzle_repository.py \
    app/services/guess_service.py app/services/puzzle_schedule_service.py
$ uv run pytest tests/test_concurrency.py -k "wins_the_lock" -q
>           assert submit_outcome == ("error", "PuzzleChangedError"), submit_outcome
E           AssertionError: ('ok', True)          ← 교체가 이긴 순서인데 제출도 성공
>           assert replace_outcome == ("error", "ValidationError"), replace_outcome
E           AssertionError: ('ok',)               ← 제출이 이긴 순서인데 교체도 성공
FAILED tests/test_concurrency.py::test_replacement_that_wins_the_lock_turns_the_submission_away
FAILED tests/test_concurrency.py::test_submission_that_wins_the_lock_blocks_the_replacement
2 failed, 3 deselected in 4.34s
exit=1
```

수정 **후**(세 파일 복구):

```
$ uv run pytest tests/test_concurrency.py -v
tests/test_concurrency.py::test_concurrent_correct_guesses_do_not_double_count PASSED
tests/test_concurrency.py::test_hint_unlock_and_guess_are_serialized PASSED
tests/test_concurrency.py::test_concurrent_hint_unlocks_insert_one_row PASSED
tests/test_concurrency.py::test_replacement_that_wins_the_lock_turns_the_submission_away PASSED
tests/test_concurrency.py::test_submission_that_wins_the_lock_blocks_the_replacement PASSED
5 passed
exit=0
```

영향 범위(제출·조회·캐시·리더보드·배정표·운영자 교체 라우트):

```
$ uv run pytest tests/test_concurrency.py tests/test_puzzle_schedule_service.py \
    tests/test_admin_schedule.py tests/test_guess_flow.py tests/test_puzzle_api.py \
    tests/test_puzzle_cache.py tests/test_hint_unlock.py tests/test_leaderboard.py -q
74 passed in 91.63s (0:01:31)
exit=0
```

### 이 라운드의 전체 검증 (base = 로컬 `main` `4d83feb`, 티켓 13 머지)

```
$ git rebase main                  # 충돌 1건(spec.md "미정 항목") 해결, 그 외 깨끗
$ git status --short               # 출력 없음 = clean
$ uv run ruff check .
All checks passed!
exit=0

$ FLASK_ENV=testing uv run flask --app wsgi db heads
d7a1f0ca0a29 (head)
exit=0        ← 한 줄. 이 수정도 마이그레이션을 만들지 않았다(잠금은 스키마 변경이 아니다).

$ uv run pytest -q
937 passed in 799.41s (0:13:19)
exit=0
```

실패·skip·xfail **0**. 라운드 0 의 870 → **937**: main 이 티켓 13 머지로 올라가며
따라온 테스트(+65)와 이 라운드의 재현 테스트 **+2**.

### 최종 base 재검증 (base = 로컬 `main` `a520223`, 티켓 17 머지)

위 검증 직후 main 이 티켓 17 머지로 또 올라갔다. 그 위로 다시 rebase 하고(충돌 없음)
전체를 다시 돌렸다 — 보고하는 상태는 이 base 다.

```
$ git rebase main                  # 충돌 없음
Successfully rebased and updated refs/heads/dosaem/t23-admin-schedule-stock-toggles-books.

$ git status --short               # 출력 없음 = clean
$ git diff --check main...HEAD     # 출력 없음, exit=0

$ uv run ruff check .
All checks passed!

$ FLASK_ENV=testing uv run flask --app wsgi db heads
d7a1f0ca0a29 (head)
exit=0        ← 한 줄

$ uv run pytest -q
996 passed in 686.02s (0:11:26)
exit=0
```

937 → **996**(+59)은 티켓 17 이 가져온 테스트다. 이 라운드가 더한 테스트는 그대로 2개
(`tests/test_concurrency.py`), 실패·skip·xfail **0**.

### 이 라운드에서 하지 않은 것

- **UI 를 건드리지 않았다.** 템플릿·CSS·정적 파일 diff 가 0 이므로(`git diff --stat
  HEAD~1 -- web/` 비어 있음) `impeccable detect` 를 다시 돌리지 않았다. 리뷰가 적은
  detect 조건의 한계(CDN 폰트 `<link>` 를 지운 폴백 환경에서 본 `line-length` 3건)는
  이 라운드의 변경과 무관하게 그대로 남아 있는 관찰이다 — 리뷰도 그걸 결함으로
  집계하지 않았다.
- **미수정 MINOR 없음.** 리뷰 라운드 1 의 MINOR 는 0건이었다.
- **배정표가 `schedule_puzzles(language, days)` 를 직접 부르지 않는 점**은 리뷰가
  결함 목록에 올리지 않은 관찰이라 그대로 뒀다. 근거는 README 설계 판단 `### 23.`
  (GET 조회가 배정을 만들면 운영자가 화면을 열어보는 것만으로 단어 풀이 줄어든다).
  두 함수는 같은 모듈에서 같은 날짜 창 상수(`SCHEDULE_DAYS`)를 공유한다.
- 프로덕션·배포·NAS·실제 외부 API 접근 없음, `git push` 없음, 하위 워커 없음. 시크릿
  값은 이 문서에 없다(키 **이름**만).
