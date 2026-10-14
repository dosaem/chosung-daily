# 티켓 17 구현 증거 — 웹 플레이 흐름·퍼즐 언어 칩·서버 보드 복원·리더보드·ko/en 문구

- 브랜치: `dosaem/t17-web-play-flow-i18n` (로컬 `main` = `abf3e9a` "Merge 티켓 12" 위로
  rebase). 작업 중 main 이 세 번 움직여서 세 번 rebase 했다 — `d440172`(09) 때
  `app/web.py` 충돌 1건을 손으로 풀었고(아래 §7), `b43567e`(11)·`abf3e9a`(12) 때는
  충돌이 없었다.
- 커밋 4개: 구현 / 문서·스펙 / 공용 토큰·대비 수정 / 이 증거 문서
  (`git log --oneline main..HEAD` 로 확인)
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t17`,
  `TEST_REDIS_URL=redis://127.0.0.1:6379/5`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t17_migrations`.
  공용 테스트 DB(`chosung_daily_test`)·Redis DB 1 은 건드리지 않았다.
  브라우저 확인용 개발 서버는 또 다른 DB(`chosung_daily_web_t17`) + Redis DB 6.
- 마이그레이션 없음(스키마 변경 없음). `flask db heads` = `a5bab2f58a7b` 1줄(12 의 것).
- 프로덕션에 닿는 행동 없음: `git push` 없음, 외부 서비스 호출 없음, `.env*` 미수정,
  시크릿 값 없음.

## 1. 체크박스별 근거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| 언어 칩 → `PATCH /me` → `GET /puzzles/today` 재조회 | `tests/test_web.py::test_language_chips_are_rendered_for_both_puzzle_languages`, `::test_js_changes_puzzle_language_with_patch_me_and_refetches` + 브라우저 §3 [2] (칩 클릭 → 서버 `puzzle_language=en` → 퍼즐이 ko `ㅈㅎㅊㅇ`/4글자 에서 en `HRRYPTTR`/11글자 로 교체) |
| 영어 퍼즐은 `mask` 로 타일 렌더(`r`/`h`/`s`), `chosung` 의존 제거 | `::test_js_renders_tiles_from_mask_not_chosung` (`puzzle.chosung`·`state.chosung` 미사용) + 브라우저 §3 추가확인 (문제 행 `tile revealed/empty` 11개 + `tile-gap` 1개) |
| 보드 복원이 서버 `attempts` 기반, localStorage history 키 제거 | `::test_js_restores_the_board_from_server_attempts` (`saveHistory`/`loadHistory` 없음, `chosung_history_` 는 지우는 코드로만 등장) + 브라우저 §3 [4][5] (409 후 보드가 서버 이력으로 1행 복원, 심어둔 옛 키 0개) |
| 토큰 저장·백업/불러오기 패널 유지 | `::test_backup_and_restore_panel_is_kept` + 브라우저 §3 [5] (`chosung_token` 유지), 추가확인 (`#backup-panel`·`#token-input` 존재) |
| en 보드 복원 시 `s` 위치 간격 재삽입 (미정 13) | `::test_js_reinserts_separator_gaps_from_the_mask` + 브라우저 §3 추가확인: 문제 행과 시도 행의 자리 구성이 완전히 같다 (둘 다 6번째가 `tile-gap`). 서버가 준 `guess`는 `HARRYPITTER`(구분자 없는 11자) |
| 제출에 `puzzle_id` 동봉 | `::test_js_sends_puzzle_id_with_a_guess` + 브라우저 §3 [3] (정상 제출 성공) |
| 409 `PUZZLE_CHANGED` 인라인 메시지 + 재조회 | `::test_js_handles_puzzle_changed_with_an_inline_message_and_refetch`, `::test_js_shows_the_puzzle_changed_notice_after_the_refetch` + 브라우저 §3 [4] (메시지 "새 퍼즐이 있어요" 남음, `puzzleId` 가 2로 복구, 남은 기회 4/5 그대로) |
| 언어 변경·계정 전환·백업 코드 전환 시 로컬 상태 폐기 | `::test_js_discards_local_play_state_on_language_and_account_switch` + 브라우저 §3 [2] (칩 전환 후 보드 0행), [5] (옛 키 제거) |
| 리더보드 섹션 신설 — `entries.display`·`is_me`·`me` | `::test_leaderboard_section_is_rendered`, `::test_js_renders_leaderboard_display_is_me_and_my_rank` + 브라우저 §3 [6]·추가확인 (`게스트 #0005` 익명 표시, 내 행만 `is-me`, 내 순위 카드 `#4 · 2회 · 08:57:45`) |
| 통계 섹션은 `?language=` 명시 | `::test_js_asks_leaderboard_and_stats_for_an_explicit_language` + 브라우저 §3 [6] (시도 분포 1~5회 렌더) |
| UI 문자열 ko/en 사전 + 기기 언어 감지, 기존 문구 전부 사전으로 | `tests/test_ui_strings.py` 9건(키 집합·자리표시자·빈 값·en 에 한글 없음·템플릿/번들이 쓰는 키가 다 있음) + `tests/test_web.py::test_korean_device_gets_korean_ui`, `::test_english_device_gets_english_ui`(**렌더된 HTML 전체에 한글 0자**), `::test_lang_query_param_overrides_the_device_language`, `::test_page_varies_on_accept_language`, `::test_js_reads_strings_from_the_embedded_dictionary` |
| pytest 렌더 테스트 | `tests/test_web.py` 24건 (아래 §2) |
| 수동 체크리스트(README 또는 docs) | README "웹 수동 체크리스트" 8항목 표. `::test_manual_checklist_is_documented` 가 항목이 안 빠졌는지 지킨다 |

추가로 지킨 것(코디네이터 지시):

| 지시 | 근거 |
|---|---|
| 웹 UI 티켓은 09 의 `tokens.css` 를 재사용 (범위는 `ask` 로 (A) 확정) | `::test_page_links_the_shared_token_stylesheet`, `::test_new_elements_use_token_variables_not_new_hex` (17 이 만든 선택자 9개에 hex 리터럴 0개) |
| 메인 페이지 `impeccable detect` 라이트 0건 | 아래 §4 |

## 2. 실행한 검증

### 전체 테스트 + ruff + 마이그레이션 head (rebase 후)

```
# main = abf3e9a Merge 티켓 12: 구독 DB·영수증 검증 엔드포인트·상태 정규화
$ uv run ruff check .
All checks passed!
ruff exit=0

$ ./scripts/check_migration_heads.sh
a5bab2f58a7b (head)
OK: Alembic head 1개
heads exit=0

$ uv run pytest -q
........................................................................ [ 10%]
........................................................................ [ 20%]
........................................................................ [ 30%]
........................................................................ [ 41%]
........................................................................ [ 51%]
........................................................................ [ 61%]
........................................................................ [ 72%]
........................................................................ [ 82%]
........................................................................ [ 92%]
...................................................                      [100%]
699 passed in 351.74s (0:05:51)
pytest exit=0
```

작업 시작 시점(`main` = `8115301`, 티켓 04 머지 직후)의 기준선은 `387 passed` 였다.
699 는 그 뒤 로컬 `main` 에 머지된 티켓 09(법적 문서·토큰 CSS)·11(애플 secret)·
12(구독)의 테스트 + 이 티켓의 신규 31건을 합한 수다. 09 rebase 전 기준(main=`b43567e`)
으로 돌린 중간 결과는 `586 passed` 였고, 둘 다 실패 0건이다.

> 중간에 전체 스위트를 돌리면서 부분 스위트를 **동시에** 띄워서 `23 errors` 를 본 적이
> 있다 — 둘 다 같은 테스트 DB 에 `create_all`/`drop_all` 을 하기 때문이고 코드와
> 무관하다. 위 출력은 단독으로 돌린 결과다.

새로 만든 테스트 파일/테스트:

```
$ uv run pytest tests/test_ui_strings.py tests/test_web.py tests/test_token_css.py -q
........................................................................ [ 82%]
...............                                                          [100%]
87 passed in 10.40s
```

- `tests/test_ui_strings.py` — 신규 9건
- `tests/test_web.py` — 기존 3건 중 2건 유지(`test_index_page_renders`, `test_static_js_is_served`),
  04 가 남긴 `test_static_js_sends_puzzle_id_with_a_guess` 는 같은 내용의
  `test_js_sends_puzzle_id_with_a_guess` 로 이름만 바꿔 이어받았다. 나머지 신규.
- `tests/test_token_css.py` — 09 의 `test_main_page_style_is_untouched` 를
  `test_tokens_css_declares_variables_only` 로 교체했다(§7).

### 왜 JS 단위 테스트가 없는가

스펙 "미정 항목" 5(Playwright E2E in CI — 보류)에 따라 **CI 에 브라우저·JS 러너를
들이지 않았다**. 그래서 이 티켓의 검증은 세 겹이다.

1. **서버가 책임지는 부분은 진짜 요청으로** — 문구 사전, 기기 언어 판정, 섹션 마크업은
   Flask 테스트 클라이언트로 실제 HTTP 응답을 본다(`Accept-Language` 헤더까지).
2. **JS 계약은 번들 내용으로 회귀만** — 04 가 남긴 방식 그대로. 동작을 증명하진
   못하고, "이 줄이 사라지면 걸린다" 수준이다. 숨기지 않고 적는다.
3. **실제 동작은 헤드리스 크롬으로 한 번 손으로** — §3. 재현 스크립트를
   `review/web-smoke-17.mjs` 에 남겼다(CI 아님).

## 3. 브라우저 실동작 확인 (헤드리스 Chrome + CDP)

전용 DB(`chosung_daily_web_t17`)·Redis DB 6 에 ko(`지하철역`)·en(`Harry Potter`,
구분자가 든 책 제목) 퍼즐을 하나씩 배정하고 개발 서버를 8017 에 띄운 뒤,
`review/web-smoke-17.mjs` 로 실제 페이지를 조작했다.

```
$ node review/web-smoke-17.mjs http://127.0.0.1:9222 http://127.0.0.1:8017/
[1] 처음 상태
  lang= ko
  chips= ["ko:true","en:false"]
  mask= ㅈㅎㅊㅇ
  caption= 4글자
[2] 퍼즐 언어 칩 'en' 클릭 → PATCH /me → 재조회
  chips= ["ko:false","en:true"]
  mask= HRRYPTTR
  caption= 11글자
  board rows= 0
  puzzle_language on server= en
[3] 오답 1회 제출
  board= HARRYPITTER
  attempts-left= 남은 기회 4/5
[4] puzzle_id 를 낡은 값으로 바꿔 409 PUZZLE_CHANGED 유도
  message= 새 퍼즐이 있어요
  puzzleId 복구= 2
  attempts-left(안 깎임)= 남은 기회 4/5
  board rows(서버 이력으로 복원)= 1
[5] 옛 localStorage history 키 제거 확인
  남은 history 키= 0
  토큰은 유지= true
[6] 콘솔 에러 없음 확인용 정답 제출 + 리더보드
  result= 정답은 "Harry Potter"였어요!
  my-rank= #4 · 2회 · 08:57:45
  leaderboard= #1 | 게스트 #0005 · 2회 · 08:39:34 | ... | #4 | 게스트 #000c · 2회 · 08:57:45
  stats= 1회 0% | 2회 100% | 3회 0% | 4회 0% | 5회 0%
  share= "오늘의 초성 2026-10-14\nH_RRY P_TT_R (11글자)\n2/5 성공\n\n🟩🟩🟩🟩🟩🟩⬜🟩🟩🟩🟩\n🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩"
```

추가 확인:

```
is_me 강조 행 = leaderboard-entry :: #1 … || … || leaderboard-entry is-me :: #4 게스트 #000c · 2회 · 08:57:45
result 섹션 보임 = true
제출 폼 숨김 = true
백업 패널 존재 = true
mask 행 타일/간격 = tile revealed,tile empty,tile revealed,tile revealed,tile revealed,tile-gap,
                   tile revealed,tile empty,tile revealed,tile revealed,tile empty,tile revealed
시도 행 타일/간격 = tile correct,tile correct,tile correct,tile correct,tile correct,tile-gap,
                   tile correct,tile wrong,tile correct,tile correct,tile correct,tile correct
```

마지막 두 줄이 미정 13 의 핵심이다 — 서버가 준 `guess` 는 `HARRYPITTER`(구분자 없는
11자)인데, 시도 행이 문제 행과 **똑같은 자리에** `tile-gap` 을 갖는다.

ko UI + en 퍼즐도 같이 확인했다(`--accept-lang=ko-KR` + 퍼즐 언어 en): 문구는 한국어,
타일은 영어. UI 언어와 퍼즐 언어가 따로 논다는 뜻이다.

### 이 과정에서 잡은 버그 2개 (수정 후 재확인)

처음 돌렸을 때 두 가지가 틀렸고, 둘 다 pytest 로는 못 잡았을 것이다.

1. **보드에 타이핑한 글자가 그대로 그려졌다** (`harrypitte` — 공백 때문에 한 칸씩
   밀리고 소문자). 서버는 정규화한 `HARRYPITTER` 를 저장하는데 제출 응답이 그 값을
   안 돌려줘서 생긴 차이다. `normalizeGuess`(구분자 제거 + en 대문자)를 넣어 **제출과
   보드가 같은 글자열**을 쓰게 고쳤다. 같이, 입력창 `maxLength` 를 타일 수가 아니라
   `mask` 길이(구분자 포함)로 바꿨다 — 그 전엔 `harry-potter` 를 칠 수조차 없었다.
   회귀 테스트: `::test_js_submits_the_same_letters_it_draws_on_the_board`.
2. **409 안내가 화면에 안 남았다.** 메시지를 띄운 뒤 재조회를 불렀는데, 재조회의
   `discardLocalPlayState()` 가 `#message` 를 비웠다. 재조회 **뒤**에 띄우도록 순서를
   바꿨다. 회귀 테스트: `::test_js_shows_the_puzzle_changed_notice_after_the_refetch`.

## 4. `impeccable detect` — 라이트 0건

`detect` 는 Jinja 의 `url_for` 를 못 풀어서 템플릿 파일 스캔으로는 CSS 를 못 읽는다
(09 증거와 같은 이유). 개발 서버를 띄우고 URL 로 돌렸다.

```
$ impeccable detect "http://127.0.0.1:8017/"
exit=0

$ impeccable detect "http://127.0.0.1:8017/?lang=en"
exit=0
```

탐지기가 살아 있다는 대조군(TOOLS.md 에 7건으로 기록된 폐기 목업):

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b   (×4)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.  exit=2
```

**처음엔 0건이 아니었다.** `[low-contrast] 3.6:1 — text #ea580c on #ffffff` 가 하나
나왔다 — 기존 `.streak` 이 brand 를 글자색으로 쓰고 있었고, OVERRIDES §2 가 정확히
그걸 금지한다("스트릭 숫자는 `foreground`"). 17 이 손댄 **유일한 기존 규칙**이다.
대비 위반이라 18 까지 미루지 않았다. 불꽃을 Lucide `flame` 아이콘으로 바꾸는 건
OVERRIDES §8, 티켓 18.

## 5. 디자인 파일 대조

`design/SCREENS.md` "웹" 절 + `design-system/hidden-vowels/OVERRIDES.md` 기준.

| 지킨 것 | 어디 |
|---|---|
| 가림 타일 `r` 글자 / `h` 빈 타일(면만, 테두리 없음) / `s` 간격, 캡션 "N글자" | `.tile.revealed`(면 없음 — OVERRIDES §1 "면 채움은 제출 버튼 하나"), `.tile.empty`=`--color-tile-empty`, `.tile-gap`, `#length-caption` |
| 게임 피드백 색을 brand 와 분리 | `--color-tile-correct`/`--color-tile-wrong`/`--color-tile-text-on-correct` |
| brand 는 선택 칩 테두리에만, 글자색·면 채움 금지 | `.chip[aria-pressed="true"]` (테두리 `--color-brand` + 배경 `--color-brand-subtle`), `.streak` 을 `--color-foreground` 로 |
| 1~3위 순위 숫자만 굵게(brand 색 글자 금지) | `.rank.top` (`font-weight: 700`, 색은 `--color-foreground`) |
| 리더보드 익명 표시 + 내 행 강조 + 내 순위 카드 + 빈 상태 문구 | `#leaderboard-section`, `.is-me`, `#my-rank`, `leaderboard_empty` |
| 409 면 "새 퍼즐이 있어요" 인라인 | `t("puzzle_changed")` |
| 모서리·간격은 토큰 스케일 | `--radius-tile`, `--space-*` |

**의도적으로 안 한 것(티켓 18 범위)**: 기존 규칙(body/.card/header/panel/form)의 토큰
전환, 다크모드, 480px 카드, 그림자 제거, 스켈레톤·오프라인·퍼즐 없음 상태, "순위 ·
내 기록" 섹션 토글, 앱 CTA·Smart App Banner·푸터 링크, 🔥 → Lucide `flame`.
17 은 `#leaderboard-section` 을 토글 없이 그냥 쌓아 둔다 — 18 이 토글 뒤로 넣는다.

## 6. 알려진 중간 상태 / 한계

- **다크 OS 에서 새 요소만 다크다.** 17 이 만든 요소는 `tokens.css` 변수를 쓰고 그
  변수는 `prefers-color-scheme: dark` 에서 다크 값으로 바뀌는데, 기존 규칙은 아직
  하드코딩 라이트 hex 다. CDP 로 `prefers-color-scheme: dark` 를 걸고 실측한 값:
  `body` `rgb(244,244,245)`·`.card` `rgb(255,255,255)`(라이트 그대로) 위에 빈 타일
  `rgb(37,48,68)`·순위 구분선 `rgb(42,52,71)`·선택 칩 테두리 `rgb(249,115,22)`(다크 값).
  **대가가 색만은 아니다**: `--color-muted-foreground` 가 다크값 `#94a3b8` 로 바뀌면서
  아직 흰 카드 위에 올라가 약 **2.6:1** 이 된다(AA 미달). `.length-caption`·`.rank`·
  `.leaderboard-message`·`.stats-empty` 가 해당한다. 18 이 `body`/`.card` 를 토큰으로
  바꾸는 순간 같이 해소된다. 코디네이터가 "배포되지 않는 중간 상태"로 받기로 했고
  (17·18 은 연달아 머지, 로컬 main 은 push 안 됨), `impeccable detect` 는 라이트 기준
  0건이다. **18 은 이걸 반드시 같이 확인해야 한다.**
- **다크 모드 스크린샷 없음.** `--force-prefers-color-scheme=dark` 가 이 헤드리스
  빌드에서 안 먹어서(라이트와 바이트 단위로 같은 PNG) 스크린샷 대신 위 CDP 실측값으로
  확인했다. 다크 스크린샷은 18 의 완료 조건이다.
- **JS 단위 테스트 없음** — §2 참고. 번들 문자열 어서션은 동작이 아니라 회귀만 막는다.
- **Chrome 확장(claude-in-chrome)으로는 로컬 페이지를 못 열었다** —
  `Frame with ID 0 is showing error page` 로 3번 실패(09 증거와 같은 증상). 헤드리스
  Chrome + CDP 로 대신했다.
- 리더보드 `seconds` 는 "KST 자정부터 몇 초" 라서 화면에 `08:57:45` 처럼 나온다.
  SCREENS 의 예시(`00:03:41`)와 같은 의미다(자정 직후에 푼 사람). 바꾸지 않았다.
- `favicon.ico` 404 는 그대로다(아이콘은 18·33 범위).

## 7. 공유 파일에 손댄 곳

- `README.md` — "설계 판단" 끝에 `### 17.` 3개, "웹 수동 체크리스트" 절 신설(공통 규칙대로
  자기 번호 소제목만 덧붙였고 다른 번호의 절은 안 건드렸다). API 표는 **안 건드렸다** —
  API 변경이 없다(`/` 응답 헤더에 `Content-Language`·`Vary` 가 붙은 것뿐).
- `.scratch/store-launch/spec.md` — "미정 항목" 에 **미정 13 확정** 줄 하나만 덧붙였다
  (티켓이 명시적으로 시킨 것).
- `app/web.py` — rebase 충돌 1건. 09 가 같은 파일에 법적 문서 라우트를 넣어서, 내가
  쓰던 자체 언어 판정(`pick_ui_language`)을 버리고 **09 의 `resolve_ui_language` 로
  갈아탔다**. 09 의 유틸이 docstring 에 "이후 웹 프론트도 같은 규칙을 쓴다"고 적어둔
  대로다. 덤으로 09 가 문서화한 버그를 피했다 — werkzeug `best_match` 는
  `en-US,ko;q=0.1` 에서 완전 일치하는 q=0.1 의 ko 를 고른다. `?lang=` 오버라이드와
  `Content-Language` 헤더도 같이 따라왔다.
- `tests/test_token_css.py` — 09 의 `test_main_page_style_is_untouched`
  (= `style.css` 에 `var(--color-` 가 없어야 한다)를 지우고
  `test_tokens_css_declares_variables_only` 로 바꿨다. 그 테스트의 뜻은 "09 가 메인
  페이지를 안 건드렸다" 였는데, 코디네이터 결정으로 17 이 새 요소에 토큰을 쓰게 되면서
  성립하지 않는다. 대신 (a) `tokens.css` 가 변수만 두는지(파일 머리말의 약속)를 새로
  보고, (b) "17 의 새 요소가 색을 직접 정하지 않는지" 는 `tests/test_web.py` 로 옮겼다.
- `.env.example`·`docs/RELEASE.md` — 손대지 않았다(설정값 추가 없음).

## 8. 남은 것

없다. 티켓 체크박스 전부 구현·검증했고, 위 "알려진 중간 상태"는 티켓 18 범위로
넘어가는 항목이다.
