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

---

## 수정 라운드 1

`review/impl-review-17.md` "라운드 1" 의 결함 2건(BLOCKER 0 / MAJOR 2 / MINOR 0)을
고쳤다. 리뷰어의 지적은 둘 다 사실이었다 — 재현부터 똑같이 재현됐다(아래 "수정 전"
출력). 미수정 MINOR 는 없다(리뷰가 MINOR 0 건).

- 기준점이 바뀌었다: 리뷰는 로컬 `main` = `abf3e9a`(12) 위에서 봤고, 이 라운드는
  **`main` = `bf287f6` "Merge 티켓 06" 위로 rebase** 했다(충돌 없음, 7 커밋).
  그래서 아래 전체 테스트 수치는 리뷰의 699 가 아니라 **722** 다.
- 전용 테스트 자원은 그대로다: `TEST_DATABASE_URL=...chosung_daily_test_t17`,
  `TEST_REDIS_URL=redis://127.0.0.1:6379/5`. 공용 테스트 DB·Redis DB 1 은 안
  건드렸다. 접속 URL 의 자격 증명은 이 문서에 적지 않는다.
- 마이그레이션은 여전히 17 이 추가한 게 없다. `uv run flask db heads` →
  `dae1b5af0cf7 (head)` 1줄, exit 0 (06 이 들어와 리비전 ID 가 `a5bab2f58a7b` 에서
  바뀌었다).
- 리뷰 파일(`review/impl-review-17.md`)은 수정하지 않았다.

### 재현 테스트를 어디에 뒀는가

리뷰가 정확히 짚었다 — 기존 JS 검증은 **번들 문자열 어서션**(`tests/test_web.py`)이라
"함수가 있다"까지만 본다. 두 결함은 모두 *실행* 결과라서 그 방식으로는 잡히지 않는다.
그래서 번들을 실제로 돌리는 테스트를 새로 넣었다:

| 파일 | 역할 |
|---|---|
| `tests/js/harness.mjs` | `web/static/app.js` 를 node `vm` 에서 실행하는 최소 대역. DOM(요소·classList·innerHTML 비우기)·`localStorage`·`fetch` 도착 순서만 제공하고, **검사 대상 함수는 작업 트리의 번들 그대로** 쓴다. 번들 끝의 `init();` 한 줄만 뗀다(없으면 바로 throw 해서 조용히 통과하지 않는다). |
| `tests/js/stale_submit_response.mjs` | D-17-1 시나리오 3개(오답 stale / 정답 stale / 전환 없는 대조군) |
| `tests/js/error_message_language.mjs` | D-17-2 시나리오 6개(VALIDATION_ERROR·ALREADY_FINISHED·RATE_LIMITED·UNAUTHORIZED·매핑 없는 code·today 의 NO_PUZZLE_TODAY) |
| `tests/test_web_js.py` | 위 시나리오를 돌리고 판정한다. 사전은 `UI_STRINGS[language]` 를 그대로 넘겨서, 문구 키가 없으면 테스트가 먼저 터진다. |

Playwright 는 그대로 안 들였다(스펙 "미정 항목" 5) — 브라우저 없이 번들만 돌린다.
그래서 **레이아웃·실제 HTTP 왕복은 이 테스트가 대신하지 못한다**. README "웹 수동
체크리스트" 에 9·10 번 항목(제출 중 언어 전환 / 영어 UI 오류 문구)을 추가했다.
`node` 가 없는 환경에서는 `pytest.mark.skipif` 로 건너뛴다(CI 의 `ubuntu-latest` 에는
node 가 있다).

#### 수정 전 (red) — 리뷰의 재현이 그대로 재현된다

수정 전 번들로 되돌려 같은 테스트를 돌렸다:

```
$ git checkout 669caf0 -- web/static/app.js
$ uv run pytest tests/test_web_js.py -q
FAILED tests/test_web_js.py::test_stale_wrong_guess_response_does_not_touch_the_new_puzzle
FAILED tests/test_web_js.py::test_stale_correct_guess_response_does_not_finish_the_new_puzzle
FAILED tests/test_web_js.py::test_server_error_messages_are_shown_in_the_ui_language
FAILED tests/test_web_js.py::test_an_unmapped_error_code_falls_back_to_the_generic_ui_string
FAILED tests/test_web_js.py::test_no_error_message_leaks_korean_into_the_english_ui
5 failed, 1 passed in 0.28s
```

통과한 1건은 대조군(`test_a_submit_without_a_switch_still_updates_the_board`)이다 —
테스트가 그냥 다 빨간 게 아니라, 깨진 두 경로만 집어낸다는 뜻이다.

같은 시나리오의 원시 출력(수정 전):

```
stale_wrong   : {"puzzleId":2,"puzzleLanguage":"en","attempts":[{"guess":"사과","feedback":[true,false]}],"attemptsLeft":4,"boardRows":1,"attemptsLeftText":"남은 기회 4/5",...}
stale_correct : {"puzzleId":2,"puzzleLanguage":"en","attempts":[{"guess":"사과","feedback":[true,true]}],"attemptsLeft":4,"finalStatus":"success","boardRows":1,"guessFormHidden":true,"resultHidden":false}
guess_validation / already_finished / rate_limited / unauthorized / unknown / today_no_puzzle
  → "정답은 5글자입니다." / "이미 정답을 맞춘 퍼즐입니다." / "제출이 너무 많습니다. …" /
    "인증이 필요합니다." / "서버 오류가 발생했습니다." / "오늘의 퍼즐이 아직 준비되지 않았습니다."
```

`stale_correct` 는 리뷰가 적은 것보다 한 발 더 나간 상태까지 보여준다 — 새 en 퍼즐의
입력 폼이 숨고(`guessFormHidden:true`) 결과 패널이 열려(`resultHidden:false`) **ko
정답으로 완료** 표시된다.

### D-17-1 — MAJOR — 전환 이전 요청의 응답이 새 퍼즐 상태를 오염시킨다

**원인.** `submitGuess` 가 응답을 받은 시점에 "이 응답이 지금 화면의 퍼즐 것인가" 를
묻지 않는다. `fetch` 를 기다리는 동안 언어 칩(제출 중에도 눌린다)·409 재조회·계정·
백업 전환이 끝나면 `state` 는 이미 **다른 퍼즐**인데, 응답 처리부는 그걸 모르고
`state.attempts.push(...)`·`renderAttemptsLeft(...)`·`showResult(...)` 를 지금 상태에
그대로 쓴다. 증상(보드에 한 줄)이 아니라 이 "응답 ↔ 상태 불일치" 가 원인이다.

**수정 내용.** `web/static/app.js` `submitGuess`:

```js
const requestedPuzzleId = state.puzzleId;
const res = await fetch(`${API_BASE}/puzzles/today/guesses`, {
  …, body: JSON.stringify({ puzzle_id: requestedPuzzleId, guess }),
});
const data = await res.json();

if (state.puzzleId !== requestedPuzzleId) return;
```

- 요청을 보낸 퍼즐 ID 를 들고 있다가, 응답 시점에 화면이 그 퍼즐이 아니면 **응답을
  통째로 버린다** — 409 재조회도, 오류 안내도 하지 않는다. 이미 폐기한 퍼즐의 이야기다.
- 같은 ID 를 요청 본문의 `puzzle_id` 로도 쓴다(전에는 `state.puzzleId` 를 직접 읽었다).
  요청 조립 시점엔 값이 같지만, "요청이 말한 퍼즐" 과 "응답을 검사하는 기준" 이 한
  변수에서 나오는 게 맞다.
- `discardLocalPlayState()` 가 `state.puzzleId = null` 로 두기 때문에, 전환이 아직
  새 퍼즐을 못 받은 중간 상태(`null`)에서도 가드가 걸린다.
- **칩을 제출 중에 비활성화하는 쪽은 고르지 않았다.** 자정 경과나 다른 기기의 언어
  변경처럼 칩을 안 눌러도 퍼즐이 갈리는 경로가 있어서, 막을 곳은 입력이 아니라 응답
  반영 지점이다. README "### 17. 늦게 온 제출 응답은 버린다" 에 적었다.

**증명.** 수정 후 같은 시나리오:

```
stale_wrong   : {"puzzleId":2,"puzzleLanguage":"en","attempts":[],"attemptsLeft":5,"finalStatus":null,
                 "boardRows":0,"attemptsLeftText":"남은 기회 5/5","guessFormHidden":false,"resultHidden":true}
stale_correct : {"puzzleId":2,"puzzleLanguage":"en","attempts":[],"attemptsLeft":5,"finalStatus":null,
                 "boardRows":0,"attemptsLeftText":"남은 기회 5/5","guessFormHidden":false,"resultHidden":true}
fresh_wrong   : {"puzzleId":1,"puzzleLanguage":"ko","attempts":[{"guess":"사과","feedback":[true,false]}],
                 "attemptsLeft":4,"boardRows":1,"attemptsLeftText":"남은 기회 4/5"}   ← 대조군: 평소대로 반영
```

`tests/test_web_js.py::test_stale_wrong_guess_response_does_not_touch_the_new_puzzle`,
`::test_stale_correct_guess_response_does_not_finish_the_new_puzzle`,
`::test_a_submit_without_a_switch_still_updates_the_board` 가 이걸 고정한다.

**리뷰어의 독립 재현 명령으로도 확인.** `review/impl-review-17.md` 의 node 명령을
그대로 돌리면(사전 stub 에 `error_guess_length` 키 한 개만 더 넣어야 한다 — 아래
D-17-2 가 그 키를 쓴다):

```
{"puzzleId":2,"language":"en","attempts":[],"left":5}
The answer is 5 letters.
```

전: `{"puzzleId":2,"language":"en","attempts":[{"guess":"사과",…}],"left":4}` / `정답은 5글자입니다.`

### D-17-2 — MAJOR — 영어 UI 의 일반 오류가 한국어로 출력된다

**원인.** `data.message || t("generic_error")`(제출)·`body.message || t("puzzle_load_failed")`
(today 조회)가 **서버 message 를 사전보다 먼저** 쓴다. 그런데 API 오류 message 는
한국어 한 벌뿐이다(`app/errors.py`) — API 는 기기 언어를 모르고, 앱(Flutter)도 같은
응답을 받는다. 그래서 "정상적인 오류 응답" 에서는 번역된 fallback 이 아예 안 쓰인다.
리뷰가 "우선순위 문제" 라고 쓴 게 정확하다.

**수정 내용.**

- `web/static/app.js`: `code → 사전 키` 표와 그걸 쓰는 한 줄짜리 함수를 넣고, 두
  호출 지점을 바꿨다.

```js
const ERROR_STRING_KEYS = {
  VALIDATION_ERROR: "error_guess_length",
  ALREADY_FINISHED: "error_already_finished",
  RATE_LIMITED: "error_rate_limited",
  NO_PUZZLE_TODAY: "error_no_puzzle_today",
  UNAUTHORIZED: "error_unauthorized",
};

function errorText(body, fallbackKey) {
  const key = ERROR_STRING_KEYS[body.code];
  return key ? t(key, { length: state.length }) : t(fallbackKey);
}
```

  - `showMessage(errorText(data, "generic_error"))` (제출), `showMessage(errorText(body, "puzzle_load_failed"))` (today).
  - **서버 message 는 더 이상 화면에 안 쓴다.** 매핑에 없는 code(`INTERNAL_ERROR` 등)는
    부른 쪽이 준 기본 문구로 눕는다.
- `app/utils/ui_strings.py`: ko/en 각각 5개 추가 — `error_guess_length`
  (`"정답은 {length}글자예요."` / `"The answer is {length} letters."`),
  `error_already_finished`, `error_rate_limited`, `error_no_puzzle_today`,
  `error_unauthorized`.
- `{length}` 는 서버 message 를 파싱하지 않고 화면이 이미 들고 있는 `state.length` 에서
  온다. 웹에서 닿는 `VALIDATION_ERROR` 는 길이 불일치 하나다 — 빈 답은 `handleSubmit`,
  50자 초과는 입력창 `maxLength` 가 미리 막는다(`app/schemas/guess.py`).
- **API 를 기기 언어별로 번역하는 쪽은 고르지 않았다.** 모든 엔드포인트가
  `Accept-Language` 를 받아야 하고 앱 클라이언트의 계약도 바뀐다. 17 범위가 아니다
  (스펙 §A.16 은 UI 문구 ko/en 만 요구한다). README "### 17. 서버 오류 문구는 `code` 로
  사전에서 고른다" 에 적었다.
- `ALREADY_FINISHED` 의 서버 message 두 가지("이미 정답을 맞춘" / "이미 기회를 모두
  사용한")는 사전 문구 하나("이미 끝난 퍼즐이에요.")로 합쳤다. 화면에서 할 일이 같다.

**증명.** 수정 후, en 사전을 넘겨 실제 `submitGuess`·`loadToday` 를 돌린 `#message`:

```
guess_validation       : The answer is 5 letters.
guess_already_finished : You've already finished this puzzle.
guess_rate_limited     : Too many guesses. Please try again in a moment.
guess_unauthorized     : We couldn't check your record. Please reload.
guess_unknown          : Something went wrong.          ← 매핑 없는 code 는 generic_error
today_no_puzzle        : Today's puzzle isn't ready yet.
```

`tests/test_web_js.py::test_server_error_messages_are_shown_in_the_ui_language`,
`::test_an_unmapped_error_code_falls_back_to_the_generic_ui_string`,
`::test_no_error_message_leaks_korean_into_the_english_ui`(출력에 한글이 한 자라도
있으면 실패) 가 고정한다.

`t(변수)` 는 기존 `test_bundle_only_uses_keys_that_exist` 의 정규식(`t("키"`)에 안
걸린다. 그래서 `tests/test_ui_strings.py::test_api_error_codes_map_to_keys_that_exist`
를 더해 매핑의 값이 전부 사전에 있는지 본다 — 키 이름을 잘못 적으면 그 오류에서만
`undefined` 가 뜨는 걸 막는다.

### 같이 바꾼 것 (수정 범위 안)

- `tests/test_web.py::test_js_sends_puzzle_id_with_a_guess`: 어서션을
  `"puzzle_id: state.puzzleId"` → `"const requestedPuzzleId = state.puzzleId;"` +
  `"puzzle_id: requestedPuzzleId"` 로 갱신했다. 뜻("제출은 그릴 때 받은 퍼즐 ID 를
  들고 간다")은 그대로고 표현만 바뀌었다.
- `tests/test_web.py`·`tests/test_ui_strings.py` 머리말의 "JS 테스트 러너가 없어서"
  문장이 더 이상 사실이 아니라서 고쳤다(번들 실행 테스트가 생겼다 / Playwright 는
  여전히 없다).
- README "웹 수동 체크리스트" 머리말도 같은 이유로 고쳤고, 9·10 번 항목을 추가했다.
- 기능 추가·리팩토링은 하지 않았다. 서버 코드는 `app/utils/ui_strings.py` 의 문구
  10줄(ko/en 5쌍)만 늘었다 — API·스키마·마이그레이션 변경 없음.

### 전체 검증 (rebase 후)

```
$ git rebase main                      # main = bf287f6 "Merge 티켓 06"
Successfully rebased and updated refs/heads/dosaem/t17-web-play-flow-i18n.

$ uv run pytest -q
722 passed in 493.98s (0:08:13)        # exit 0

$ uv run ruff check .
All checks passed!                      # exit 0

$ uv run flask db heads
dae1b5af0cf7 (head)                     # 1줄, exit 0 (17 은 마이그레이션 없음)

$ git diff --check main...HEAD
                                        # 출력 없음, exit 0
```

`git status` 는 clean 이고 브랜치는 로컬 `main`(`bf287f6`) 바로 위에 있다.
`origin/main` 은 쓰지 않았고 `git push` 도 하지 않았다.

### 남은 것 / 이 라운드가 못 한 것

- **브라우저 재확인은 안 했다.** 이번 수정은 JS 로직 두 지점이고 CSS·마크업을
  건드리지 않아서 `impeccable detect` 를 다시 돌리지 않았다(라이트 0건 주장은 라운드
  이전 그대로다). 다크 OS 중간 상태도 그대로 티켓 18 범위다(§6).
- 수동 체크리스트 9·10 번은 **문서로만 추가**했다. 실제 Slow 3G 전환 조작은 node
  대역의 응답 보류로 대신했다 — 같은 순서를 만들지만 실제 브라우저·네트워크는 아니다.
- 미수정 MINOR 없음(리뷰 MINOR 0건).

---

## 수정 라운드 2

`review/impl-review-17.md` "라운드 2" 의 활성 결함 2건(BLOCKER 0 / MAJOR 2 / MINOR 0)을
고쳤다. 둘 다 리뷰어 말이 맞았다 — 리뷰의 재현 명령을 그대로 돌려 같은 출력을
받고 시작했다(아래 "수정 전"). 미수정 MINOR 는 없다(리뷰 MINOR 0건).
리뷰 파일은 수정하지 않았다.

- 기준점: 이 라운드 작업 중 로컬 `main` 이 두 번 움직여 두 번 rebase 했다
  (`148715b` → `1e764da` "Merge 티켓 15", 둘 다 충돌 없음, 11 커밋). 리뷰는
  `bf287f6` 위에서 봤다. 코디네이터가 말한 `008a35a`(티켓 22)는 `1e764da` 에 들어 있다.
- 전용 테스트 자원 그대로: `TEST_DATABASE_URL=...chosung_daily_test_t17`,
  `TEST_REDIS_URL=redis://127.0.0.1:6379/5`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t17_migrations`.
  공용 테스트 DB·Redis DB 1 은 건드리지 않았다. 접속 URL 의 자격 증명은 적지 않는다.
- 마이그레이션 없음(스키마 변경 없음). 서버 코드 변경 없음 — 이번 수정은
  `web/static/app.js` 한 파일과 테스트뿐이다.

### 공통 원인 — "같은 ID 로 돌아오는" 순간

두 결함은 증상이 다를 뿐 원인이 하나다. **지금 화면이 어느 상태인지를 퍼즐 ID 로
구분하려 한 것**이다.

- 라운드 1 의 수정은 제출 응답을 `state.puzzleId !== requestedPuzzleId` 로 걸렀다.
  ko→en 단방향은 막히지만 ko→en→ko 왕복이면 ID 가 **다시 같아진다**. 그 사이
  보드는 서버 `attempts` 로 복원됐으므로, 늦게 온 응답을 다시 반영하면 같은 시도가
  두 번 그려진다(D-17-1 REPEAT).
- 조회 응답(`/me/stats`·순위·오늘 통계·`GET today`·`PATCH /me`)에는 그 비교조차
  없었다. 전환 전에 시작한 `/me/stats` 의 `puzzle_language` 가 지금 고른 언어를
  덮어써 칩과 퍼즐이 어긋나고, 다음 칩 클릭이 `language === state.puzzleLanguage`
  에 걸려 통째로 무시된다(D-17-3).

그래서 응답마다 조건을 덧대지 않고 **세대(generation) 하나**로 막았다. 상태를
통째로 폐기하는 단 한 지점(`discardLocalPlayState`)에서 `state.generation` 을 1
올리고, 비동기 요청은 전부 같은 경로로 거른다:

```js
function sinceGeneration() {
  const generation = state.generation;
  return () => state.generation !== generation;
}
```

`discardLocalPlayState` 는 언어 전환·409 재조회(자정 경과 포함)·백업 코드 전환이
모두 거쳐 가는 길목이라, 세대 증가 지점도 하나다.

### 비동기 요청별 — 늦은 응답을 어떻게 막는가

| 요청 | 거르는 지점 | 늦은 응답이 그대로 들어오면 | 고정한 테스트 |
|---|---|---|---|
| `POST /puzzles/today/guesses` (submitGuess) | `isStale() \|\| state.puzzleId !== requestedPuzzleId` | 왕복 후 복원된 시도를 한 번 더 그려 보드·공유 그리드가 중복 | `test_a_submit_response_from_before_a_round_trip_is_discarded` (+ 라운드 1 의 단방향 2건) |
| `GET /me/stats` (loadStats) | `if (!isStale()) renderLanguageChips(...)` | 지난 선호 언어가 칩을 되돌려 다음 전환이 막힘 | `test_a_stats_response_from_before_a_switch_does_not_revert_the_language` |
| `GET /puzzles/today` (loadToday) | `if (isStale()) return null;` | 먼저 보낸 재조회가 나중 언어의 퍼즐을 덮어씀 | `test_a_today_response_from_an_earlier_switch_does_not_replace_the_newer_puzzle` |
| `PATCH /me` (handleLanguageChange) | `if (isStale()) return;` | 409 재조회로 갈아끼운 화면 위에 전환을 또 얹어 퍼즐이 한 번 더 바뀜 | `test_a_language_patch_that_resolves_after_a_refetch_is_dropped` |
| `GET /puzzles/today/leaderboard` | `if (isStale()) return;` | 전 언어 퍼즐의 순위·내 순위가 지금 화면에 남음 | `test_leaderboard_and_today_stats_from_before_a_switch_are_discarded` |
| `GET /puzzles/today/stats` | `if (isStale()) return;` | 전 언어 퍼즐의 시도 분포가 지금 화면에 남음 | 같은 테스트 |

세대를 **안 보는** 비동기 요청과 그 이유:

| 요청 | 왜 거르지 않는가 |
|---|---|
| `POST /guests` (ensureToken) | 토큰 발급은 `init()` 의 첫 단계다 — 아직 그릴 상태도, 폐기할 상태도 없다. |
| `POST /session/sync` (syncSession) | 응답으로 화면을 그리지 않는다(쿠키만 심는다). |
| `GET /me/stats` (handleRestoreSubmit 의 코드 검증) | 성공하면 `discardLocalPlayState()` + `location.reload()` 로 페이지가 통째로 다시 뜬다. 실패하면 `#restore-message` 한 줄뿐이고, 이건 플레이 상태가 아니라 그 패널의 것이다. |
| `loadStats` 의 연속 기록·연결 계정 | 퍼즐이 아니라 **게스트**의 정보라 언어 전환과 무관하게 최신이다. 전환했다고 비워두면 "기록이 0일인가?" 로 헷갈린다 — 그래서 같은 응답에서도 선호 언어 칩만 거른다(`test_a_stale_stats_response_still_updates_the_guest_scoped_summary`). |

### 결함별 — 원인 / 수정 / 증명

#### D-17-1 (REPEAT, MAJOR) — 왕복 후 폐기한 제출 응답이 복원 이력을 중복시킨다

- **원인**: `web/static/app.js` 의 제출 가드가 퍼즐 ID 비교뿐이었다. ko→en→ko 면
  ID 가 1 로 되돌아와 "같은 퍼즐" 로 판정된다. 그 사이 `applyPuzzle` 이 서버
  `attempts` 로 그 시도를 이미 복원해뒀으므로 한 번 더 `state.attempts.push` 된다.
- **수정**: `submitGuess` 가 요청 직전 세대를 `sinceGeneration()` 으로 집어두고,
  응답에서 `isStale() || state.puzzleId !== requestedPuzzleId` 면 통째로 버린다.
  ID 비교는 남겼다 — 폐기 없이 `applyPuzzle` 만 도는 경로(`init()`)까지 덮는다.
- **증명**: `tests/js/stale_state_generation.mjs` 시나리오 (A) — ko 제출 보류 →
  en 전환 → ko 복귀(서버가 1행 복원) → 보류했던 응답 도착.

```
수정 전: {"puzzleId":1,"attempts":[{"guess":"사자",...},{"guess":"사자",...}],"attemptsLeft":4,"boardRows":2}
수정 후: {"puzzleId":1,"attempts":[{"guess":"사자","feedback":[true,false]}],"attemptsLeft":4,"boardRows":1}
```

#### D-17-3 (신규, MAJOR) — 늦은 내 기록 조회가 퍼즐 언어를 되돌려 전환을 막는다

- **원인**: `loadStats` 가 `renderLanguageChips(stats.puzzle_language)` 를 무조건
  불렀다. 그 응답은 전환 **전** 상태의 것이라 선호 언어가 ko 다. 칩만 ko 로
  되돌아가고 퍼즐은 en 인 어긋난 상태가 되며, 다음 한국어 클릭은
  `language === state.puzzleLanguage` 로 즉시 반환돼 요청이 0건이 된다
  (= en 퍼즐에서 못 빠져나온다). `normalizeGuess` 의 en 대문자 처리도 같이 잃는다.
- **수정**: 같은 세대의 응답일 때만 칩을 그린다. 퍼즐이 없는 날에도 칩은 선호
  언어를 가리켜야 하므로 "퍼즐이 있나" 가 아니라 "세대가 같나" 로 판단한다.
  연속 기록·연결 계정은 게스트의 것이라 그대로 반영한다.
- **증명**: 시나리오 (B) — ko 에서 `loadStats()` 보류 → en 전환 → 보류 응답 도착
  → 이어서 한국어 칩 클릭.

```
수정 전: {"puzzleId":2,"puzzleLanguage":"ko","chips":{"ko":"true","en":"false"},"normalizedLatin":"ab"}  ko click requests: 0
수정 후: {"puzzleId":2,"puzzleLanguage":"en","chips":{"ko":"false","en":"true"},"normalizedLatin":"AB"}  ko click requests: 4
```

#### 같은 원인의 나머지 경로 (리뷰가 지적하지 않았지만 같이 막았다)

코디네이터 지시("응답마다 개별 조건을 덧대지 말고 원인을 한 번에 막아라")에 따라
남은 비동기 요청도 같은 경로로 묶었다. 각각 시나리오 (D)(E)(F) 로 고정했다.

```
순위·오늘 통계 (D)  수정 전: {"entryRows":1,"myRank":"#9 · 3회 · 00:01:30","statsText":"1회 50%2회 0%..."}
                    수정 후: {"entryRows":0,"myRank":"아직 안 풀었어요","statsText":"아직 정답자가 없어요"}
GET today    (E)   수정 전: {"puzzleId":2,"puzzleLanguage":"en"}   ← 마지막 클릭은 한국어였다
                    수정 후: {"puzzleId":1,"puzzleLanguage":"ko"}
PATCH /me    (F)   수정 전: refetchesAfterReload 1  (409 재조회 뒤 퍼즐이 또 바뀐다)
                    수정 후: refetchesAfterReload 0
```

### 수정 전 (red) → 수정 후 (green)

수정 전 번들(`1e24303:web/static/app.js`)로 되돌려 새 테스트만 돌렸다:

```
$ git show 1e24303:web/static/app.js > web/static/app.js
$ uv run pytest tests/test_web_js.py -q
FAILED tests/test_web_js.py::test_a_submit_response_from_before_a_round_trip_is_discarded
FAILED tests/test_web_js.py::test_a_stats_response_from_before_a_switch_does_not_revert_the_language
FAILED tests/test_web_js.py::test_leaderboard_and_today_stats_from_before_a_switch_are_discarded
FAILED tests/test_web_js.py::test_a_today_response_from_an_earlier_switch_does_not_replace_the_newer_puzzle
FAILED tests/test_web_js.py::test_a_language_patch_that_resolves_after_a_refetch_is_dropped
5 failed, 8 passed in 0.42s

$ git checkout web/static/app.js        # 수정본 복구
$ uv run pytest tests/test_web_js.py -q
13 passed in 1.05s
```

통과한 8건에는 대조군 2건이 들어 있다 — 전환이 없으면 제출 응답도(`fresh_wrong`),
stats 의 선호 언어도(`fresh_stats`) 평소처럼 반영된다. 즉 "늦은 응답을 다 버린다"
가 아니라 "폐기 이전 세대만 버린다" 를 고정한다.

### 전체 검증 (rebase 후)

```
$ git rebase main                      # main = 1e764da "Merge 티켓 15"
Successfully rebased and updated refs/heads/dosaem/t17-web-play-flow-i18n.

$ uv run pytest -q
788 passed in 1173.14s (0:19:33)       # exit 0
                                        # 이번 라운드가 더한 건 JS 실행 테스트 7건
                                        # (새 결함 5 + 대조군·게스트 요약 2).
                                        # 722 → 729 가 그 7건이고, 729 → 788 은
                                        # 재rebase 로 들어온 티켓 15(운영자 CRUD) 몫이다.

$ uv run ruff check .
All checks passed!                      # exit 0

$ uv run flask db heads
dae1b5af0cf7 (head)                     # 1줄, exit 0 (17 은 마이그레이션 없음)

$ git diff --check main...HEAD
                                        # 출력 없음, exit 0
```

`148715b` 위에서도 같은 수치를 받았다(`729 passed`, exit 0). 20~27분이 걸린 건
같은 머신에서 다른 워크트리 5개가 같은 시각에 전체 테스트를 돌려서다(라운드 1 은
8분). 테스트 자원은 겹치지 않는다 — 이 라운드는 `chosung_daily_test_t17` +
Redis DB 5 만 썼다.

`git status` 는 clean 이고 브랜치는 로컬 `main`(`1e764da`) 바로 위에 있다.
`origin/main` 은 쓰지 않았고 `git push` 도 하지 않았다.

### 리뷰어 지적 중 틀렸다고 본 것

없다. 두 결함 모두 리뷰의 재현 명령을 그대로 돌려 같은 출력을 받았다.

### 남은 것 / 이 라운드가 못 한 것

- **브라우저 재확인은 안 했다.** 수정은 `web/static/app.js` 의 비동기 경계 6곳이고
  CSS·마크업·DOM 구조를 건드리지 않아서 `impeccable detect` 를 다시 돌리지 않았다
  (라이트 0건 주장은 그대로다). 다크 OS 중간 상태도 그대로 티켓 18 범위다(§6).
- node 대역은 **응답 도착 순서**를 만들 뿐 실제 브라우저·네트워크가 아니다. 실제
  Slow 3G 에서의 연타는 README "웹 수동 체크리스트" 9번이 계속 담당한다.
- 미수정 MINOR 없음(리뷰 MINOR 0건).

---

## 수정 라운드 3

`review/impl-review-17.md` "라운드 3" 의 활성 결함 1건(BLOCKER 0 / MAJOR 1 / MINOR 0,
D-17-4)을 고쳤다. 리뷰어 말이 맞았다 — 리뷰의 독립 재현 명령을 그대로 돌려 리뷰에
적힌 출력과 **똑같은** 결과를 받고 시작했다(아래 "수정 전"). 미수정 MINOR 는 없다
(리뷰 MINOR 0건). 리뷰 파일은 수정하지 않았다.

- 기준점: 로컬 `main` = `b8f63cc`("Merge 티켓 24"). 작업 뒤 그 위로 rebase 했다
  (13 커밋, 충돌 없음). `origin/main` 은 쓰지 않았고 `git push` 도 하지 않았다.
- 전용 테스트 자원 그대로: `TEST_DATABASE_URL=...chosung_daily_test_t17`,
  `TEST_REDIS_URL=redis://127.0.0.1:6379/5`. 공용 테스트 DB·Redis DB 1 은 건드리지
  않았다. 접속 URL 의 자격 증명은 적지 않는다.
- 마이그레이션 없음(스키마 변경 없음). 서버 코드 변경 없음 — `web/static/app.js`
  한 파일과 테스트·README 뿐이다.

### D-17-4 — 응답 본문 대기 중 전환하면 이전 조회가 새 퍼즐·순위·통계를 덮어쓴다

#### 원인 — 세대를 **너무 이른 경계**에서 봤다

라운드 2 가 세운 "비동기 요청은 전부 세대 하나로 거른다" 는 맞는 설계였는데, **그
검사를 거는 지점**이 틀렸다. `await fetch()` 가 끝난 시점은 **헤더까지**고, 본문
읽기(`await res.json()`)는 또 하나의 비동기 경계다. 라운드 2 의 코드는 그 사이에서
세대를 봤다:

```js
const res = await fetch(url, …);   // ← 헤더 도착
if (isStale()) return;             // ← 여기서는 아직 최신일 수 있다
…
renderLeaderboard(await res.json()); // ← 본문을 기다리는 동안 전환되면 검사는 무효
```

본문을 기다리는 사이에 언어 칩·409 재조회가 `discardLocalPlayState()` 로 세대를
올려도, 이미 통과한 `isStale()` 은 다시 묻지 않는다. 그래서 본문이 다 오면 **검사
없이** 화면에 반영됐다. 제출(`POST .../guesses`)과 `/me/stats` 는 우연히 본문을 먼저
읽고 검사해서 이 경로에 해당하지 않았다 — 즉 "어느 경계에서 보는가" 가 호출 지점마다
제각각이었던 것이 진짜 원인이다.

#### 수정 — fetch + 본문 읽기를 한 곳에 묶고, 쓰기 직전에 한 번만 본다

`web/static/app.js` 에 `fetchJson()` 하나를 두고, **본문을 다 읽은 뒤**에 세대를
확인해 돌려준다. 부른 쪽은 `stale` 만 보면 되니 경계를 다시 틀릴 자리가 없다.

```js
async function fetchJson(url, options) {
  const isStale = sinceGeneration();
  const res = await fetch(url, options);
  const body = await res.json().catch(() => null);
  return { stale: isStale(), ok: res.ok && body !== null, body: body ?? {} };
}
```

여섯 요청이 전부 이 경로를 쓴다: `GET /puzzles/today`, `PATCH /me`, `GET /me/stats`,
`GET /puzzles/today/leaderboard`, `GET /puzzles/today/stats`,
`POST /puzzles/today/guesses`. (`POST /guests`·`POST /session/sync`·백업 코드 검증은
퍼즐 상태를 쓰지 않거나 페이지를 통째로 새로 고치는 경로라 세대와 무관하다.)

유지한 예외 하나: `loadStats` 의 연속 기록·연결 계정은 퍼즐이 아니라 **게스트**의
것이라 전환과 무관하게 최신이다 — 전처럼 폐기 여부와 상관없이 갱신하고, 세대로
거르는 건 칩(`puzzle_language`)뿐이다(D-17-3 의 기준 그대로). 이 구분이 깨지지 않게
테스트로 고정했다.

곁다리로 생긴 동작 변화 하나: 본문을 한 곳에서 읽게 되면서 200 인데 JSON 이 아닌
본문(프록시가 끼워넣은 HTML 등)이 **던지지 않고** 불러오기 실패 안내로 눕는다.
수정 전에는 `SyntaxError` 가 그대로 올라왔다(아래 출력). 이것도 테스트로 고정했다.

#### 증명 — 수정 전(빨강)

리뷰의 독립 재현 명령(`review/impl-review-17.md` "D-17-4 독립 재현 명령")을 그대로
실행한 결과. 리뷰에 적힌 출력과 같다:

```text
today {"id":1,"language":"ko"}  empty
leaderboard {"id":2,"language":"en"} #1old-ko-player empty
stats {"id":2,"language":"en"}  1:1002:03:04:05:0
```

같은 순서를 회귀 테스트로 옮겨 수정 전 번들(`HEAD~1`)에 돌린 결과 — 여섯 요청 중
넷이 빨강이었다:

```text
late_today_body    {"puzzleId": 1, "puzzleLanguage": "ko", …}            # 기대 2/en
late_patch_body    {…, "refetchesAfterReload": 1}                        # 기대 0
late_submit_body   {"puzzleId": 2, "attempts": [], "attemptsLeft": 5}    # 이미 초록
late_stats_body    {"chips": {"ko":"false","en":"true"}, "streak": "🔥 연속 3일 …"}  # 이미 초록
```

```text
# 200 + 비 JSON 본문 (새 시나리오 H) — 수정 전에는 그대로 던졌다
SyntaxError: Unexpected token '<', "<html>502</html>" is not valid JSON
    at async reloadPuzzle (app.js:393:18)
```

pytest 로는 5건 실패였다:

```text
FAILED tests/test_web_js.py::test_a_today_body_that_arrives_after_a_switch_does_not_replace_the_new_puzzle
FAILED tests/test_web_js.py::test_the_same_holds_in_the_other_direction
FAILED tests/test_web_js.py::test_a_leaderboard_body_that_arrives_after_a_switch_is_discarded
FAILED tests/test_web_js.py::test_a_today_stats_body_that_arrives_after_a_switch_is_discarded
FAILED tests/test_web_js.py::test_a_language_patch_body_that_arrives_after_a_refetch_is_dropped
5 failed, 15 passed in 0.22s
```

#### 증명 — 수정 후(초록)

리뷰의 같은 재현 명령. 세 경로 모두 마지막 선택(en, ID 2)을 유지하고 늦게 온 ko
본문을 버린다:

```text
today {"id":2,"language":"en"} "" "empty"
leaderboard {"id":2,"language":"en"} "" "empty"
stats {"id":2,"language":"en"} "" "empty"
```

```text
$ uv run pytest tests/test_web_js.py tests/test_ui_strings.py -q
31 passed in 0.24s                      # exit 0
```

#### 추가한 재현 테스트

`tests/js/stale_response_body.mjs` + `tests/test_web_js.py` 의 8건. 기존
`stale_state_generation.mjs` 는 **fetch Promise 자체**를 붙잡아서 "헤더는 왔는데 본문은
아직" 인 창을 못 만든다(리뷰 지적 그대로다). 그래서 대역을 더 짜지 않고 node 의 실제
`Response` + `ReadableStream` 으로 **본문 도착만** 늦췄다(`harness.mjs` 의
`heldBodyResponse`).

| 시나리오 | 보류시킨 본문 | 기대 |
|---|---|---|
| A `late_today_body` | ko `GET today` | 마지막 선택 en(ID 2) 유지 |
| B `late_today_body_reverse` | en `GET today` | 반대 방향도 같다 — ko(ID 1) 유지 |
| C `late_leaderboard_body` | ko 순위 | 전 언어 순위·내 순위가 안 뜬다 |
| D `late_today_stats_body` | ko 오늘 통계 | 전 언어 분포가 안 뜬다 |
| E `late_patch_body` | `PATCH /me` | 409 재조회 뒤 그 전환은 접는다(재조회 0회) |
| F `late_stats_body` | `GET /me/stats` | 칩은 안 따라가고, 게스트의 연속 기록은 갱신 |
| I `late_submit_body` | 제출 | 새 보드에 이전 퍼즐의 시도가 안 생긴다 |
| G `fresh_leaderboard_body` | (대조군) 전환 없음 | 늦게 온 본문도 평소처럼 반영 |
| H `unparsable_body` | 200 + HTML | 던지지 않고 불러오기 실패 안내 |

코디네이터 지시대로 **여섯 요청 전부** "본문 수신 중 전환" 으로 고정했다 — 수정 전
초록이던 제출(I)·`/me/stats`(F) 도 같은 기준이 유지되는지 보게 포함했다.

### 리뷰어 지적 중 틀렸다고 본 것

없다. 리뷰의 재현 명령을 그대로 돌려 리뷰에 적힌 출력과 같은 결과를 받았고, 지적한
네 위치(`:140/:146`→`:396`, `:218`→`:224`, `:515`→`:521`, `:563`→`:566`)가 전부 같은
원인이었다. "제출과 `/me/stats` 는 본문을 읽은 뒤 검사하므로 대상이 아니다" 는 단서도
실제 실행으로 확인했다(위 수정 전 출력의 I·F).

### 검증 출력

로컬 `main`(`b8f63cc`, "Merge 티켓 24") 위로 rebase 한 뒤 전부 다시 돌렸다.

```text
$ git rebase main                      # main = b8f63cc "Merge 티켓 24", 13 커밋
Successfully rebased and updated refs/heads/dosaem/t17-web-play-flow-i18n.

$ uv run pytest -q
797 passed in 641.75s (0:10:41)        # exit 0
                                        # 788 → 797 중 9건이 이번 라운드가 더한
                                        # JS 실행 테스트(새 결함 5 + 제출·게스트
                                        # 요약·대조군·파싱 실패 4)다.

$ uv run pytest tests/test_web_js.py tests/test_ui_strings.py -q
31 passed in 0.24s                      # exit 0 (node 설치돼 있어 skip 없음)

$ uv run ruff check .
All checks passed!                      # exit 0

$ uv run flask db heads
dae1b5af0cf7 (head)                     # 1줄, exit 0 (17 은 마이그레이션 없음)

$ git diff --check main...HEAD
                                        # 출력 없음, exit 0
```

`git status` 는 clean 이고 브랜치는 로컬 `main`(`b8f63cc`) 바로 위에 있다.
`origin/main` 은 쓰지 않았고 `git push` 도 하지 않았다.

### 남은 것 / 이 라운드가 못 한 것

- **브라우저 재확인은 안 했다.** 수정은 `web/static/app.js` 의 비동기 경계뿐이고
  CSS·마크업·DOM 구조를 건드리지 않아서 `impeccable detect` 를 다시 돌리지 않았다
  (라이트 0건 주장은 그대로다). 다크 OS 중간 상태도 그대로 티켓 18 범위다(§6).
- node 대역은 **응답 도착 순서**(이번엔 본문 도착 시점까지)를 만들 뿐 실제 브라우저·
  네트워크가 아니다. 실제 Slow 3G 에서의 연타는 README "웹 수동 체크리스트" 9번이
  계속 담당한다.
- 200 + 비 JSON 본문은 실제로 겪은 사례가 아니라 수정 과정에서 드러난 경로다 —
  테스트로만 고정했고 수동 체크리스트에는 넣지 않았다.
- 미수정 MINOR 없음(리뷰 MINOR 0건).
