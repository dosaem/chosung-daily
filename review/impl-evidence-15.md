# 티켓 15 구현 증거 — 운영자 페이지(인증·단어 CRUD·CSV 업로드)

- 브랜치: `dosaem/t15-admin-auth-words-csv`, 로컬 `main` **`abf3e9a`**(티켓 12 머지) 위로 rebase
- 테스트 자원(워커 전용): DB `chosung_daily_test_t15` / Redis DB `3` /
  마이그레이션 DB `chosung_daily_test_t15_migrations`
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`). 공용 테스트
  DB·Redis DB 는 건드리지 않았다.
- 마이그레이션 **없음**(새 테이블·컬럼이 없다 — `ADMIN_EMAILS` 는 설정이고 단어 CRUD 는
  기존 `word` 테이블을 쓴다). Alembic head 는 main 그대로 1개.
- 프로덕션에 닿는 행동 없음: `git push` 없음, 외부 서비스 호출 없음(운영자 알림·구글·애플을
  건드리는 코드 경로를 추가하지 않았다). 시크릿 값은 이 문서에 없다 — 키 **이름**만 적는다.

## 1. 바꾼 것

| 파일 | 무엇 |
|---|---|
| `app/config.py` | `ADMIN_EMAILS` (기본값 없음, 쉼표 구분, 소문자 정규화) |
| `app/admin.py` (신규) | `/admin` 블루프린트 + `admin_required` 가드 + 단어 CRUD·CSV 업로드 뷰 |
| `app/__init__.py` | `register_admin(app)` |
| `app/services/word_service.py` | `parse_word_input`·`missing_csv_columns`·`import_word_rows`·`search_words`·`create_word`·`update_word`·`delete_word`. `seed_words_from_csv` 는 같은 적재 규칙을 쓰도록 다시 씀 |
| `app/repositories/word_repository.py` (신규) | 목록 조회(필터·페이지네이션)·중복 조회·배정 날짜 조회·LIKE 이스케이프 |
| `web/templates/admin/{_layout,words,word_form,import}.html` (신규) | 운영자 Jinja 페이지 4장 |
| `web/static/admin.css` (신규) | 운영자 레이아웃. 09 의 `tokens.css` 변수만 사용 |
| `web/templates/index.html`, `web/static/style.css` | 서버 안내(flash) 블록 — 로그인 전 `/admin` 진입을 `/` 로 돌려보낼 때 쓰는 자리 |
| `tests/conftest.py` | `web_login`·`admin_session` 픽스처(스펙 §C 가 이름을 정한 것) |
| `tests/test_admin_auth.py`·`test_admin_words.py`·`test_admin_csv_upload.py`·`test_admin_css.py` (신규) | 40개 테스트 |
| `tests/test_word_service.py` | 행 리스트 적재 테스트 9개 추가 |
| `README.md` | API 표 `/admin/*` 5행, "운영: 단어 CSV 업로드" 절, "설계 판단 ### 15." 3항목 |
| `.env.example`, `docs/RELEASE.md` | 자기 번호 블록(`[15]`, `### 15.`) |
| `review/admin-detect-snapshot-15.py` (신규) | `impeccable detect` 용 스냅샷 생성 스크립트(아래 §4) |

## 2. 티켓 체크박스 ↔ 증거

| 체크박스 | 무엇이 증명하나 | 결과 |
|---|---|---|
| `ADMIN_EMAILS` 설정(기본값 없음), `.env.example` 에 두 운영자 이메일 주석 | `app/config.py` `ADMIN_EMAILS`(env 없으면 빈 tuple) · `.env.example` `[15]` 블록(`dosaem90@gmail.com,hsseo@dosaem.com` 주석) · `tests/test_admin_auth.py::test_nobody_is_an_admin_when_admin_emails_is_unset` | pass |
| 판정 경로 세션 → Guest → `Account.email ∈ ADMIN_EMAILS` | `app/admin.py::admin_required` (세션 `current_guest_id` → `account_repository.find_by_guest`) · 픽스처가 `POST /api/v1/session/sync` 를 실제로 통과한다(`tests/conftest.py::web_login`) | pass |
| **테스트 3종**: 운영자 통과 / 다른 이메일 403 / 세션 없음은 `/` 안내 | `test_admin_email_can_open_the_words_page` · `test_other_email_is_forbidden`(403 `FORBIDDEN`) · `test_request_without_a_session_is_sent_to_the_home_page`(302 → `/`, 본문에 "구글 로그인"·"/admin") | 3/3 pass (+ 계정 미연결·설정 없음·대소문자 4종 추가) |
| 모든 `/admin` POST 가 01 의 CSRF 데코레이터를 거친다 (토큰 없으면 403) | `app/admin.py` 의 `@csrf_protected` 4곳(추가·수정·삭제·업로드) · 테스트 `test_create_word_without_a_csrf_token_is_forbidden`, `test_update_word_...`, `test_delete_without_...`, `test_upload_without_a_csrf_token_is_forbidden` | 4/4 pass |
| 단어 목록(언어·카테고리·검색어 필터, 페이지네이션) | `test_words_page_lists_registered_words`, `..._filters_by_language`, `..._filters_by_category`, `..._filters_by_keyword_over_answer_and_hint`, `test_keyword_wildcards_are_matched_literally`, `test_words_page_paginates`(20개/쪽), `test_pagination_keeps_the_current_filter` | 7 pass |
| 추가·수정·삭제 Jinja 페이지, 09 의 토큰 CSS 사용 | 템플릿 4장이 `tokens.css` + `admin.css` 만 링크(`test_admin_pages_link_the_shared_token_stylesheet`) · `admin.css` 에 색 리터럴 없음(`test_admin_css_defines_no_colors_of_its_own`) | pass |
| 저장 시 `mask` 재계산 (02 의 순수 함수) | `test_create_word_saves_the_word_and_its_mask`(`지하철역` → `ㅈㅎㅊㅇ`) · `test_update_word_recalculates_the_mask`(ko→en 바꾸면 `h r r r h`) — 계산은 `Word` 의 before_insert/update 이벤트가 `build_mask` 를 호출 | 2 pass |
| 이미 퍼즐로 배정된 단어 삭제 차단 | `test_delete_is_blocked_for_a_word_already_assigned_to_a_puzzle` (단어·퍼즐 둘 다 남고, 사유에 "배정" 이 뜬다) · `word_service.delete_word` 가 배정 날짜를 사유에 적는다 | pass |
| CSV: UTF-8(BOM 허용) | `test_upload_accepts_a_utf8_bom`(`utf-8-sig` 바이트) · `test_upload_rejects_a_file_that_is_not_utf8`(cp949 → "UTF-8" 안내, 0건 적재) | 2 pass |
| CSV: 헤더 검증 | `test_upload_rejects_a_header_that_lacks_a_column`(빠진 열 이름을 그대로 보여주고 적재 0건) · `test_missing_csv_columns_lists_what_the_header_lacks`(순서·공백 무시) | 2 pass |
| CSV: 행별 결과(추가/중복/오류+사유) 표 | `test_upload_adds_rows_and_shows_the_result_table`, `test_upload_marks_duplicates_without_adding_them`, `test_upload_marks_a_row_repeated_inside_the_same_file_as_duplicate`, `test_upload_shows_the_reason_of_a_broken_row_and_keeps_the_good_ones` | 4 pass |
| 서비스 함수는 파일 객체가 아닌 **행 리스트**를 받는다 | `word_service.import_word_rows(rows)` — 파일/인코딩/헤더는 호출부(`app/admin.py`, `seed_words_from_csv`)의 일. `tests/test_word_service.py` 의 9개 테스트가 임시 파일 없이 규칙만 검증 | 9 pass |
| 운영자 페이지 `impeccable detect` 0건 | 아래 §4 — 화면 7개 × (1280x800, 일부 390x844) **전부 0건**, 대조군 2개로 탐지기 생존 확인 | 0건 |
| README "설계 판단" 에 "운영자 인증 = 기존 OAuth + 이메일 허용 목록" | `README.md` `### 15. 운영자 인증 = 기존 OAuth + 이메일 허용 목록` (+ `### 15. 운영자 화면의 폭...`, `### 15. 단어 삭제는 막고...`) | pass |
| README 운영 절에 CSV 포맷·LLM 생성 가이드 한 단락 | `README.md` `## 운영: 단어 CSV 업로드 (/admin)` — 헤더·열 표·예시 CSV + LLM 프롬프트 골자(ko/en) | pass |

## 3. 실행 출력 (로컬 `main` `abf3e9a` 위로 rebase 한 뒤)

```
$ git rebase main
Rebasing (1/1)Successfully rebased and updated refs/heads/dosaem/t15-admin-auth-words-csv.

$ git log --oneline main..HEAD
<커밋 2개: 구현 + 증거>

$ git status --short
(clean)
```

rebase 충돌은 1건이었다 — `tests/conftest.py` 에 티켓 11 이 `offline_provider_metadata`
픽스처를, 이 티켓이 `web_login`·`admin_session` 을 각각 파일 끝에 추가해서 생긴 추가-추가
충돌. 양쪽 픽스처와 import 를 모두 남기는 쪽으로 직접 해소했다(지운 것 없음).

```
$ uv run ruff check .
All checks passed!
exit=0

$ ./scripts/check_migration_heads.sh
a5bab2f58a7b (head)
OK: Alembic head 1개
exit=0

$ uv run pytest -q
........................................................................ [ 90%]
.....................................................................    [100%]
717 passed in 378.80s (0:06:18)
exit=0
```

참고 수치: 이 브랜치를 시작할 때(main `d440172`) 536 passed → 이 티켓으로 **+49**
(585) → rebase 로 다른 티켓 테스트가 합쳐져 717. 실패·skip·xfail 0.

이 티켓 테스트만:

```
$ uv run pytest tests/test_admin_auth.py tests/test_admin_words.py \
    tests/test_admin_csv_upload.py tests/test_admin_css.py tests/test_word_service.py -q
60 passed in 24.99s
```

(test_admin_auth 7 · test_admin_words 20 · test_admin_csv_upload 9 · test_admin_css 4 ·
test_word_service 27 중 신규 9)

## 4. `impeccable detect` — 운영자 화면 7개 0건

운영자 페이지는 **로그인 세션이 필요해서 detect 가 URL 을 직접 열 수 없다**(detect 의
브라우저는 쿠키가 없다 — `--header`/`--cookie` 옵션도 없다). 그래서 티켓 09 처럼 개발
서버에 URL 로 붙이는 대신, `review/admin-detect-snapshot-15.py` 가

1. 운영자 세션을 태운 **Flask 테스트 클라이언트로 실제 응답 HTML** 을 받고,
2. 링크된 스타일시트 경로(`/static/x.css?v=...`)만 같은 디렉터리의 복사본으로 바꿔 저장하고,
3. 그 디렉터리를 정적 서버로 띄워 detect 가 **URL 모드(실제 브라우저 + 실제 CSS)** 로 보게 한다.

템플릿을 그냥 스캔하면 Jinja `url_for` 를 못 풀어 CSS 를 못 읽는다(티켓 01 이 남긴 메모) —
이 방식은 그 문제를 피하면서 09 와 같은 URL 모드 강도를 유지한다.

```
$ FLASK_ENV=testing uv run python review/admin-detect-snapshot-15.py <snapshot-dir>
words.html ← /admin/
words_filtered.html ← /admin/?language=ko&q=사
words_empty.html ← /admin/?q=없는단어
word_new.html ← /admin/words/new
word_edit.html ← /admin/words/1/edit
import.html ← /admin/words/import
import_result.html ← POST /admin/words/import
tokens.css (복사) / admin.css (복사)

$ (cd <snapshot-dir> && python3 -m http.server 5117 &)

$ impeccable detect "http://127.0.0.1:5117/<각 화면>.html"
detect words            [] exit=0
detect words_filtered   [] exit=0
detect words_empty      [] exit=0
detect word_new         [] exit=0
detect word_edit        [] exit=0
detect import           [] exit=0
detect import_result    [] exit=0
```

출력이 비고 exit=0 이면 findings 0건이다(티켓 01·09 증거와 같은 해석).

모바일 폭도 같이 돌렸다 — 운영 도구라 데스크톱 기준이지만 표가 좁은 화면에서 깨지는지
보려고:

```
$ impeccable detect --viewport 390x844 "http://127.0.0.1:5117/{words,word_new,import_result}.html"
detect words            (390x844) exit=0
detect word_new         (390x844) exit=0
detect import_result    (390x844) exit=0
```

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님을 대조군 2개로 확인했다.**

```
# 대조군 1 — 폐기된 V2 목업, 파일 모드 (TOOLS.md 에 7건으로 기록된 파일)
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b   (×4)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.

# 대조군 2 — 같은 파일을 위 정적 서버에 올려 URL 모드로 (운영자 화면과 완전히 같은 경로)
$ impeccable detect "http://127.0.0.1:5117/control_v2.html"
  [undersized-ui-text] 10px functional text "광고" (below 11px floor)
  ...
6 anti-patterns found.
```

### 디자인 파일과 다르게 구현한 점 (1건)

목업이 없는 화면이다(`design/SCREENS.md` "목업 파일 매핑" 에서 운영자 화면은 표에 없고,
티켓도 "목업 없음 — 명세+토큰"). 그래서 디자인 시스템 토큰으로만 만들었고, **한 가지를
의도적으로 벗어났다**: OVERRIDES §10 의 웹 폭 규칙(481px 이상에서 480px 고정)을 쓰지
않고 1040px 까지 쓴다. §10 은 플레이어가 보는 게임·문서 페이지 규칙이고, 운영자 화면은
6열 표(언어·카테고리·정답·가림·힌트·관리)와 필터 한 줄이 있어서 480px 에 넣으면 표가
잘려 쓸 수 없다. 나머지는 그대로 지켰다 — §2 색 역할(brand 는 면 채움 금지,
`primary-button` 검정/흰 하나만 면), §3 타이포 스케일·Pretendard, §4 간격·모서리·44px
터치 타깃·그림자 없음, §9 다크 모드 시스템 추종. 근거는 커밋 메시지와 README
"설계 판단 15. 운영자 화면의 폭은 디자인 시스템 §10 을 벗어난다" 에 남겼고,
`tests/test_admin_css.py` 가 색 리터럴·brand 면 채움을 기계로 막는다.

## 5. 직접 확인하지 않은 것 / 남은 것

- **실제 구글 로그인 왕복은 못 돌려봤다.** `.env` 에 실제 GCP 키가 없고(콘솔 등록은 D0
  사람 작업), 외부 호출은 금지라서다. 테스트가 보증하는 건 "세션에 게스트가 심어진 뒤의
  판정" 까지다. 두 운영자 계정으로 실제 진입하는 확인은 `docs/RELEASE.md` "### 15." 체크리스트.
- **사람 눈으로 본 스크린샷은 없다.** 헤드리스 브라우저 드라이버를 프로덕션 의존성으로
  들이지 않기로 한 레포 결정(티켓 09 증거)을 따라, 위 `impeccable detect` URL 모드(실제
  브라우저가 CSS 를 계산한다)와 `tests/test_admin_css.py` 의 구조 검사로 대신했다.
- **배정표·잔량·토글·Books 는 이 티켓이 아니다**(티켓 16). 삭제가 막히는 사유 문구가
  "배정표에서 그 날짜의 단어를 먼저 바꿔라" 를 가리키지만, 그 화면은 아직 없다.
- 운영자 페이지는 ko 전용이다(운영자 두 명, 둘 다 한국어). 법적 문서처럼 언어별 템플릿을
  두지 않았다 — 스펙에 운영자 화면의 영어 요구가 없다.
- 목록의 삭제 폼들은 한 쪽에 렌더된 CSRF 토큰 하나를 공유한다(01 의 토큰은 1회용이라
  화면당 하나다). 삭제 한 번 뒤에는 목록이 다시 그려지며 새 토큰을 받으므로 정상 흐름은
  막히지 않지만, 탭 두 개를 열어두고 양쪽에서 삭제하면 나중 탭이 403 이 된다 — 운영자
  두 명 규모에서 폼별 토큰 보관을 만들 이유가 없다고 봤다(01 의 같은 판단을 따른다).
