# 티켓 18 구현 증거 — 웹 디자인 토큰 교체·다크모드·상태 4종·섹션 토글·앱 CTA·Smart App Banner·법적 링크

- 브랜치: `dosaem/t18-web-design-cta-smart-banner`, 로컬 `main` = `055b56c`
  "Merge 티켓 26" 위로 rebase(충돌 없음).
- 커밋 2개: 구현+테스트 / 문서·증거 (`git log --oneline main..HEAD`).
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t18`,
  `TEST_REDIS_URL=redis://localhost:6379/6`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t18_migrations`.
  공용 테스트 DB(`chosung_daily_test`)·Redis DB 1 은 건드리지 않았다. 다른 워커의
  컨테이너도 내리지 않았다(기존 `chosung-daily-mysql-1`·`-redis-1` 을 그대로 썼다).
- 마이그레이션 없음(스키마 변경 없음). `flask db heads` = `d7a1f0ca0a29 (head)` 1줄.
- 프로덕션에 닿는 행동 없음: `git push` 없음, 외부 서비스(Slack·Apple·Google·스토어·
  AdMob) 호출 없음, `.env*` 미수정, 시크릿 값 없음. 스토어 링크·앱 ID 는 검증용
  자리표시자(`id0000000000` 등)만 썼다.
- 디스크: Flutter·네이티브 빌드 산출물을 만들지 않았다(웹 전용 티켓).

## 1. 체크박스별 근거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| 토큰 CSS 로 교체 — `primary-button`·`tile-empty`·`tile-correct` 토큰 이름 그대로, 그림자 없음, 480px 중앙 정렬, 다크모드 자동 | `tests/test_web_design.py::test_style_sheet_has_no_hex_colors_left`(파일 전체 hex 0개), `::test_style_sheet_has_no_shadows`, `::test_style_sheet_does_not_pin_its_own_color_scheme`, `::test_card_width_comes_from_the_shared_token`(`--content-max-width`, `420px` 없음), `::test_token_named_classes_use_the_token_of_the_same_name`(4건 parametrize), `::test_page_loads_the_pretendard_web_font` + §4 detect 라이트/다크 0건 + §5 스크린샷 2장 |
| 상태 4종 — 스켈레톤·인라인 재시도·오프라인 배너(`navigator.onLine` + 요청 실패)·퍼즐 없음 카운트다운, 피드백 타일 색 + 아이콘/굵기 | 마크업: `::test_skeleton_is_rendered_before_the_puzzle_arrives`, `::test_offline_banner_sits_above_the_card`, `::test_inline_state_card_carries_a_retry_button_and_a_countdown_slot`, `::test_feedback_tiles_are_not_distinguished_by_color_alone`. 동작(번들 실행): `tests/test_web_js.py::test_the_skeleton_gives_way_to_the_puzzle`, `::test_a_request_that_cannot_leave_shows_the_banner_and_locks_the_input`, `::test_navigator_online_alone_raises_the_banner_before_any_request`, `::test_the_inline_retry_button_recovers_the_puzzle`, `::test_coming_back_online_reloads_without_asking`, `::test_a_day_without_a_puzzle_counts_down_to_kst_midnight`, `::test_the_countdown_follows_the_clock`, `::test_the_countdown_stops_when_the_puzzle_finally_arrives`, `::test_seconds_until_kst_midnight_is_computed_from_the_kst_day` |
| 상단 "순위 · 내 기록" 섹션 토글, 백업/불러오기 패널 유지, pytest 렌더로 확인 | `::test_section_nav_toggles_three_sections_on_one_page`, `::test_only_the_today_section_is_visible_at_first`, `::test_active_section_link_is_marked_for_assistive_tech`, `::test_backup_and_restore_panels_moved_into_the_records_section` + 동작 `tests/test_web_js.py::test_the_top_links_show_exactly_one_section`, `::test_the_selected_section_is_announced_to_assistive_tech`. 기존 패널 계약은 `tests/test_web.py::test_backup_and_restore_panel_is_kept` 가 그대로 지킨다 |
| 결과 화면 배지 2개 + `<meta name="apple-itunes-app">`, 설정값이 비면 미렌더(테스트 2건), 공유 텍스트에 `?utm_source=share` | `::test_store_badges_and_smart_app_banner_render_when_configured` / `::test_nothing_store_shaped_renders_while_the_app_is_not_on_the_stores` (요구된 2건), 추가로 `::test_each_badge_is_independent_of_the_other_platform`, `::test_the_app_cta_lives_in_the_result_section`. 공유 링크: `tests/test_web_js.py::test_the_share_text_ends_with_the_web_link` |
| 푸터에 `/privacy`·`/terms`·`/account/delete` + 16 의 `legal/_business_info.html` 조각 | `::test_footer_links_the_three_legal_urls`(3건 parametrize), `::test_footer_includes_the_shared_business_info_fragment`, `::test_footer_business_info_follows_the_same_config_as_the_legal_pages`. 조각 자체는 손대지 않았다(`git diff main..HEAD -- web/templates/legal/` 가 비어 있다) |
| 메인 페이지 `impeccable detect` 0건, 다크/라이트 헤드리스 스크린샷 | §4 (6회 스캔 전부 0건, 탐지기 대조군 7건) · §5 (`.scratch/store-launch/design/web-shots/home-light.png`·`home-dark.png`) |
| pytest 렌더 테스트 + 수동 체크리스트(삭제 후 새 게스트 발급 포함) 갱신 | `tests/test_web_design.py` 26건 신규 + `tests/test_web_js.py` 13건 신규. 체크리스트는 README "웹 수동 체크리스트" 20행(12~20 이 이 티켓), `tests/test_web.py::test_manual_checklist_is_documented` 가 "삭제 후 새 게스트 발급" 을 포함한 14개 항목이 빠지지 않는지 지킨다 |

코디네이터 메모(16 → 18 전이 포함)에 대한 답:

| 지시 | 근거 |
|---|---|
| 17 이 남긴 중간 상태(기존 스타일 hex + `color-scheme: light`)를 반드시 해소 | `web/static/style.css` 를 통째로 다시 썼다. hex 0개·`color-scheme` 선언 0개를 테스트가 지킨다. 다크 전용 CSS 규칙은 **한 줄도 없다** — 변수만 쓰면 `tokens.css` 의 `prefers-color-scheme: dark` 가 따라온다 |
| 라이트·다크 둘 다 detect 0건, 대비 4.5:1 | §4. 다크에서 실제로 한 건 잡혔고(입력 placeholder 3.4:1) 고친 뒤 0건이다 |
| 웹 `app.js` 의 비동기 구조(`fetchJson`·세대·`languageWanted` 직렬화)를 깨지 마라 | 티켓 17 의 동작 테스트 26건(`tests/test_web_js.py` D-17-1~5 절)이 수정 없이 그대로 통과한다. `fetchJson` 에는 **세대 검사 뒤에** 네트워크 실패 분기만 더했고, 세대 검사 위치(본문 수신 후)는 그대로다 |
| 푸터 사업자 정보는 16 의 조각 재사용 | `{% include "legal/_business_info.html" %}` 하나. 컨텍스트는 법적 문서와 같은 `app/web.py::_business_info` 가 만든다 |

## 2. 테스트 — 전체 스위트

```
$ TEST_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t18?charset=utf8mb4 \
  TEST_REDIS_URL=redis://localhost:6379/6 \
  TEST_MIGRATION_DATABASE_URL=mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t18_migrations?charset=utf8mb4 \
  uv run pytest -q
1294 passed in 650.05s (0:10:50)        (pytest exit=0)
```

작업 시작 전 같은 명령의 기준선은 rebase **전** base(`45d790c` "Merge 티켓 16") 에서
`1257 passed in 940.70s` 였다. 지금 base 는 `055b56c`(티켓 26 머지)라 그 사이 다른
티켓이 더한 테스트도 1294 안에 들어 있다 — 이 티켓이 더한 건 아래 65건(그중 26 + 13 =
39 건이 신규, 1 건은 아래 표의 사유로 삭제)이다.

**중간에 한 번 77 errors 가 났고, 원인은 내 실수다.** 이 스위트가 도는 동안 같은
테스트 DB 로 `pytest tests/test_web_design.py` 를 또 돌려서 `db.create_all()` 과
`drop_all()` 이 겹쳤다(`(1684, "Table ... was skipped since its definition is being
modified by concurrent DDL statement")`). 다른 워커와 DB 를 나눠 쓴 것과는 무관하고
(내 전용 DB 안에서 내가 두 번 돈 것), 아무도 안 돌 때 다시 돌린 위 결과가 최종이다.

이 티켓이 더한 테스트:

```
$ uv run pytest -q tests/test_web_design.py tests/test_web_js.py
65 passed in 9.85s
```

바꾼 기존 테스트 3건과 이유:

| 바꾼 것 | 이유 |
|---|---|
| `tests/test_web.py::test_new_elements_use_token_variables_not_new_hex` **삭제** | "17 이 새로 만든 선택자에는 hex 가 없다" 였다. 18 이 파일 전체를 토큰으로 옮겼으니 `test_web_design.py::test_style_sheet_has_no_hex_colors_left` 가 더 센 조건으로 대신한다(선택자 9개 → 파일 전체). 삭제 자리에 그 설명을 주석으로 남겼다 |
| `tests/test_web_js.py::test_server_error_messages_are_shown_in_the_ui_language` 의 `today_no_puzzle` 기대값 | 퍼즐 없음 안내가 `#message` 에서 인라인 상태 카드로 옮겨가면서 문구도 `error_no_puzzle_today` → `no_puzzle_heading`("곧 새 퍼즐이 올라와요") 으로 바뀌었다(OVERRIDES §7). D-17-2 의 뜻("서버의 한국어 `message` 가 아니라 사전에서 고른다")은 그대로고, `::test_no_error_message_leaks_korean_into_the_english_ui` 가 계속 지킨다 |
| `tests/js/error_message_language.mjs`·`stale_response_body.mjs` 가 읽는 요소 | 같은 이유로 `#message` → `#puzzle-state-text` |
| `tests/js/harness.mjs` | 새 DOM(섹션 링크·패널, `window.addEventListener`, `navigator.onLine`, `disabled`, 새로 숨은 요소 5개)을 대역에 추가. `setInterval` 은 `unref()` 로 감쌌다 — 안 그러면 "퍼즐 없음" 으로 끝난 시나리오에서 node 가 1초 타이머를 붙들고 종료하지 않아 테스트가 타임아웃한다(실제로 겪음) |

## 3. 린트

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check tests/test_web_design.py tests/test_web_js.py \
    review/detect-snapshot-18.py app/web.py app/utils/ui_strings.py
5 files already formatted
```

`ruff format` 은 CI 가 돌리지 않고(`.github/workflows/ci.yml` 은 `ruff check .` 만 한다)
레포에 이미 29개 파일이 포맷 미적용 상태라, **이 티켓이 새로 쓴 파일만** 포맷했다.
레포 전체 포맷은 티켓 범위 밖이다(티켓 09 증거와 같은 판단).

## 4. `impeccable detect` — 라이트·다크 × ko/en 전부 0건

`detect` 는 Jinja 템플릿 파일을 직접 주면 `url_for` 를 못 풀어 CSS 를 못 읽는다(티켓
01·09 메모). 그래서 개발 서버를 띄우고 **URL 로** 돌렸다.

```
$ FLASK_ENV=testing STORE_URL_IOS=... STORE_URL_ANDROID=... APP_STORE_ID=... \
    uv run flask --app wsgi run --port 5118    # (백그라운드, 테스트 DB + Redis DB 6)

$ impeccable detect "http://127.0.0.1:5118/?lang=ko"                    → exit=0 (출력 없음)
$ impeccable detect "http://127.0.0.1:5118/?lang=en"                    → exit=0
$ impeccable detect --viewport 390x844 "http://127.0.0.1:5118/?lang=ko" → exit=0
```

**숨은 상태와 다크 토큰은 라이브 URL 로는 못 본다.** detect 는 보이는 것만 보고
`prefers-color-scheme` 을 바꿔 주지 않는데, 이 티켓이 만든 것 중 상당수는 JS 가 켜야
보이거나(결과·앱 CTA·상태 카드·오프라인 배너·순위/내 기록 섹션) 다크에서만 색이
바뀐다. 그래서 `review/detect-snapshot-18.py` 가 렌더된 `/` 를 네 벌로 떠 둔다:
`hidden` 클래스를 떼어 숨은 상태를 전부 펼치고, JS 가 그리는 샘플 보드 한 줄
(`tile-correct`/`tile-wrong`/`tile-empty`)을 끼우고, 다크 판은 `tokens.css` 의
`prefers-color-scheme: dark` 블록을 **그 파일에서 읽어** `:root` 에 올린다(값을 스크립트에
베껴 적으면 토큰이 바뀔 때 조용히 어긋난다). 스토어 링크·사업자 정보도 "등록 후" 상태로
채워서 배지·Smart App Banner·운영자 정보 블록까지 스캔 대상에 넣었다.

```
$ uv run python review/detect-snapshot-18.py
wrote web/static/_t18_ko_light.html / _t18_ko_dark.html / _t18_en_light.html / _t18_en_dark.html

$ impeccable detect "http://127.0.0.1:5118/static/_t18_ko_light.html"   → exit=0
$ impeccable detect "http://127.0.0.1:5118/static/_t18_ko_dark.html"    → exit=0
$ impeccable detect "http://127.0.0.1:5118/static/_t18_en_light.html"   → exit=0
$ impeccable detect "http://127.0.0.1:5118/static/_t18_en_dark.html"    → exit=0
$ impeccable detect --viewport 390x844 ".../static/_t18_ko_dark.html"   → exit=0
```

스냅샷 4개는 확인 직후 `--clean` 으로 지웠다(커밋에 없다). 스크립트는 남겼다 — 다음
웹 티켓이 같은 방식으로 다시 돌릴 수 있어야 한다.

**처음부터 0건이었던 게 아니다.** 다크 판 첫 스캔에서 실제로 한 건 잡혔다:

```
  [low-contrast] placeholder "정답을 입력하세요" 3.4:1 (need 4.5:1) — text #757575 on #1c2433
1 anti-pattern found.   (exit=2)
```

브라우저 기본 placeholder 색이 다크 면 위에서 AA 미달이었다. `::placeholder` 를
`--color-muted-foreground` 로 올려 고쳤다(라이트 `#57534e` on `#ffffff` ≈ 7.4:1 /
다크 `#94a3b8` on `#1c2433` ≈ 6.4:1). 같은 명령이 그 뒤로 0건이다.

**detect 가 안 보는 것을 디자인 훅이 하나 더 잡았다.** `impeccable` 의 편집 훅이
`web/templates/index.html` 에 `flat-type-hierarchy` 를 올렸다 — 제목 24 / 섹션 제목 20
/ 본문 16 이라 단계마다 1.25 배가 안 됐다. 제목을 스케일 맨 위(`--font-size-2xl`, 32)로
올려 1.6 배 / 1.25 배로 벌렸다. 법적 문서 페이지의 `.doc-title` 과 같은 토큰이고,
OVERRIDES §3 스케일(12/14/16/20/24/32) 안이다. 위 스크린샷은 고친 뒤의 것이다.

**"출력이 비었다" 가 "탐지기가 안 돌았다" 가 아님**을 대조군으로 확인했다 — 폐기된 V2
목업(TOOLS.md 에 7건으로 기록된 파일):

```
$ impeccable detect .scratch/store-launch/design/archive/v2_softdark_home.html
  [low-contrast] 2.8:1 (need 4.5:1) — text #f1f5f9 on #3fa66b   (×4)
  [low-contrast] 2.5:1 (need 4.5:1) — text #f1f5f9 on #f0795a
  [cramped-padding] <div> "flex": children flush against bg on all sides (no inset)
  [overused-font] Primary font: inter
7 anti-patterns found.   (exit=2)
```

운영자 페이지(`/admin`) detect 는 이 티켓 범위가 아니다(계획 리뷰 r1 P1-05 — 15·16 이
각자 책임).

## 5. 다크모드 — 헤드리스 스크린샷 (사람 확인 아님)

```
$ "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
    --remote-debugging-port=9333 --user-data-dir=<temp> about:blank &
$ node review/web-shots-18.mjs http://127.0.0.1:9333 "http://127.0.0.1:5118/?lang=ko" \
    .scratch/store-launch/design/web-shots
wrote .scratch/store-launch/design/web-shots/home-light.png (50053 bytes)
wrote .scratch/store-launch/design/web-shots/home-dark.png (50220 bytes)
```

스크립트는 **먼저 한 번 열어 `localStorage.clear()` 를 하고 다시 연다.** 저장된 게스트
토큰이 남아 있으면 그 게스트로 이어지는데, 테스트 DB 는 스위트가 끝날 때 비워지므로 죽은
토큰이면 홈이 아니라 "기록을 확인할 수 없어요 + 다시 시도" 오류 카드가 찍힌다 — 실제로 한
번 그렇게 찍혀서 고쳤다(인라인 오류 카드가 다크에서 제대로 렌더된다는 건 그때 같이 봤다).

`prefers-color-scheme` 은 CDP `Emulation.setEmulatedMedia` 로 바꿨다 — 크롬 플래그
`--force-dark-mode` 는 브라우저가 색을 **임의로 반전**시키는 기능이라 우리 다크 토큰을
보는 게 아니다. 뷰포트 1000×1200, 전체 페이지 캡처.

두 장에서 확인되는 것: 배경·글자·헤어라인·칩·주 버튼·푸터가 전부 토큰을 따라 바뀌고
(라이트 `#FAFAF9`/`#0F172A` → 다크 `#141A26`/`#F1F5F9`, 주 버튼은 검정 면 → 밝은 면 +
어두운 글자), 카드 폭이 두 모드 모두 480px 중앙 정렬이고, 활성 섹션 링크의 brand 밑줄과
스트릭 불꽃(Lucide `flame`)만 오렌지다. 수동 토글 UI 는 없다(OVERRIDES §9).

## 6. 테스트가 실제로 잡는지 — 역변이 확인 5건

테스트를 먼저 쓴 쪽(`tests/test_web_design.py` 의 토큰·마크업 계약)과, 번들을 돌려
동작을 고정한 쪽(`tests/test_web_js.py` 의 상태 전환)이 섞여 있다. 어느 쪽이든
"구현을 되돌리면 빨개지는가" 를 직접 확인했다 — 아래는 구현을 일부러 망가뜨리고 해당
테스트만 돌린 결과다(전부 원상복구, `git status` clean).

| 망가뜨린 것 | 결과 |
|---|---|
| `style.css` 의 `background: var(--color-background)` → `#fafaf9` | `test_style_sheet_has_no_hex_colors_left` **FAILED** |
| 템플릿의 `{% if app_store_id %}` 가드 제거 | `test_nothing_store_shaped_renders_while_the_app_is_not_on_the_stores` **FAILED** |
| `fetchJson` 의 `.catch(() => null)` + `offline: true` 분기 제거 | `test_a_request_that_cannot_leave_shows_the_banner_and_locks_the_input` **ERROR**(시나리오가 던진다 = 지금 코드가 그 예외를 막고 있다는 뜻) |
| `buildShareText` 의 `lines.push("", SHARE_URL)` 제거 | `test_the_share_text_ends_with_the_web_link` **FAILED** |
| `showSection` 이 모든 패널을 보이게 | `test_the_top_links_show_exactly_one_section` **FAILED** |

## 7. 설계 판단 (요약 — 본문은 README "### 18.")

- **다크 전용 CSS 를 한 줄도 쓰지 않는다.** 변수만 쓰면 `tokens.css` 의 다크 블록이
  따라온다. 다크 규칙을 따로 쓰기 시작하면 라이트/다크가 두 벌로 갈라진다.
- **클래스 이름 = 토큰 이름.** `tile-empty`/`tile-correct`/`primary-button`. 마크업만
  보고 어느 토큰인지 안다. 대가는 `app.js` 와 CSS 를 같이 고쳐야 한다는 것.
- **상태 카드는 하나.** 오류와 "퍼즐 없음" 은 문구·카운트다운만 다르다. 카드를 나누면
  "지금 어느 카드가 떠 있나" 를 양쪽에서 지워야 하고 둘이 겹치는 조합이 생긴다.
- **오프라인은 `navigator.onLine` 과 요청 실패를 둘 다 본다.** `onLine` 은 죽은 Wi-Fi 도
  `true` 고, 요청 실패는 서버 문제일 수도 있다. 플레이어가 할 일은 같아서 한 배너로 묶고,
  복구는 `online` 이벤트(자동 재조회)와 재시도 버튼 둘 다 둔다.
- **`fetchJson` 이 네트워크 실패를 삼킨다.** 던지면 부른 쪽마다 `try` 를 달아야 하고,
  안 달면 스켈레톤이 멈춘 화면이 된다 — 그 상태를 보여주는 게 US 8 이다.
- **카운트다운은 고정 오프셋.** KST 는 서머타임이 없어 `(지금 + 9h) % 24h` 하나면 된다.
- **섹션 토글은 버튼 + `aria-pressed`.** 주소가 안 바뀌므로 링크가 아니고, 색·굵기를 못
  봐도 선택이 읽힌다.
- **스토어 값이 비면 아무것도 안 그린다.** 빈 `app-id=` 는 Safari 가 "앱 없음" 배너를
  그리고, 없는 앱을 권하는 CTA 는 심사에서 문제가 된다.

## 8. 범위에서 뺀 것 · 사람 몫

- **"내 기록" 섹션에 7일 그리드를 넣지 않았다.** SCREENS S4 의 7일 그리드는 앱 화면이고,
  웹에 들이려면 `/me/history` 조회를 새로 붙여야 한다 — 티켓 체크박스가 요구한 건
  "섹션 토글 + 백업/불러오기 패널 유지" 다. 연속 기록 숫자는 머리말 StreakBadge 가 늘
  보여주고 있어 섹션에서 다시 적지도 않았다.
- **스토어 배지는 아직 텍스트 버튼이다.** Apple/Google 의 공식 배지 이미지는 각 사의
  마케팅 가이드라인(크기·여백·언어별 파일)에 묶여 있어 레포에 임의로 그려 넣지 않았다.
  교체 체크박스는 `docs/RELEASE.md` "### 18." 에 있다. "설정값이 비면 안 그린다" 규칙은
  교체 후에도 그대로다.
- **타일 크기 규칙(5글자 이하 48 / 6~8글자 40, OVERRIDES §4)은 17 이 둔 그대로다.**
  이 티켓은 색·간격·폭의 토큰 전환이고, 글자 수에 따른 타일 크기는 레이아웃 규칙이라
  건드리지 않았다. 지금은 문제 행이 48, 시도 행이 40 이다.
- **브라우저로 손으로 돌려본 왕복은 없다.** 헤드리스 스크린샷 2장과 detect 6회가
  이 티켓의 시각 근거고, Slow 3G·DevTools Offline·iOS Safari Smart App Banner 같은
  실제 왕복은 README "웹 수동 체크리스트" 12~20 행으로 남겼다.
- **출시 전 사람이 채울 값**: `docs/RELEASE.md` "### 18."(`STORE_URL_IOS`/
  `STORE_URL_ANDROID`/`APP_STORE_ID`, 공식 배지 아트워크, 공유 링크 도메인 확인).

## 수정 라운드 1 — 최종 리뷰(`review/impl-review-18.md` 라운드 1) 결함 수정

- 기준: 로컬 `main` = `055b56c`. `git merge-base --is-ancestor main HEAD` 가 참이라 rebase 는
  no-op 였다(새 커밋 없음, 충돌 없음). `origin/main` 은 쓰지 않았다.
- 전용 테스트 자원 그대로: `chosung_daily_test_t18` / Redis DB 6. 공용 테스트 DB·Redis DB 1 은
  건드리지 않았다. 마이그레이션 없음(`git diff --name-only main..HEAD -- migrations` 비어 있음),
  `flask db heads` = `d7a1f0ca0a29 (head)` 1줄.
- `review/impl-review-18.md` 는 고치지 않았다.
- 각 결함은 **리뷰의 재현 방법 그대로 먼저 재현**하고(아래 출력), 그 재현을 실패하는 테스트로
  고정한 뒤 고쳤다. 증상이 아니라 원인을 적었다.

### D-18-1 (MAJOR) — 최초 게스트 발급 실패가 새 오류 UI 전체를 건너뛴다

**재현.** 기존 node 대역(`tests/js/harness.mjs`)으로 `navigator.onLine=false` + 모든 fetch reject
상태에서 `init()` 을 그대로 돌렸다. 애플리케이션 함수는 하나도 mock 하지 않았다.

```
D-18-1 { "rejected": "TypeError: Failed to fetch",
         "skeletonShown": true, "bannerShown": false,
         "retryCardShown": false, "retryListeners": 0 }
```

리뷰가 적은 네 값과 같다.

**원인.** 증상은 "스켈레톤 고착" 이지만 원인은 두 가지가 겹친 것이다.

1. `ensureToken()` 이 발급 실패를 `throw` 로 올렸다.
2. `init()` 이 그 호출을 `bindEvents()`·`renderOffline()` **앞**에 두었다.

그래서 예외 하나가 나머지 초기화를 통째로 건너뛴다 — 배너도, 재시도 핸들러도,
`online`/`offline` 이벤트 등록도 없다. 게다가 유일한 재시도 경로인 `handleRetry` 가
퍼즐 조회 전용 `reloadPuzzle()` 을 불렀으므로, 버튼이 붙어 있었더라도 **토큰이 없는 화면은
발급을 다시 시도할 수 없었다**.

**수정** (`web/static/app.js`)

1. `ensureToken()` 이 던지지 않고 `boolean` 을 돌려준다. 실패는 조회 실패와 **같은** 인라인
   상태 카드(`showPuzzleState`)로 눕히고, 요청이 아예 못 나간 경우에만 배너를 같이 올린다.
   `fetch` 직접 호출을 `fetchJson` 으로 바꿔 "못 나감(offline)" 과 "나갔지만 실패(!ok)" 를
   구분한다. 성공하면 `state.token` 과 `syncSession()` 까지 여기서 맡는다.
2. `init()` 이 **`bindEvents()` → `renderOffline()` 을 맨 앞**에 둔다. 첫 요청보다 복구 수단이
   먼저 살아 있어야 한다.
3. 첫 화면 한 벌(발급 → 통계 → 퍼즐 → 순위·오늘 통계)을 `restart()` 하나로 묶고,
   `handleRetry`·`handleOnline` 이 `reloadPuzzle()` 대신 이것을 부른다. 퍼즐 재조회 전용인
   `reloadPuzzle()`(언어 전환·409 PUZZLE_CHANGED 경로)은 그대로 뒀다.
4. 카드에 재시도 버튼이 생겼으니 `guest_issue_failed` 문구에서 "새로고침해서" 를 뺐다
   (`app/utils/ui_strings.py`, ko/en).

**증명.** `tests/js/web_states_and_sections.mjs` 에 `init()` 을 그대로 돌리는 시나리오를 넣고
`tests/test_web_js.py` 가 판정한다.

| 테스트 | 확인하는 값 |
|---|---|
| `test_a_first_visit_whose_guest_issue_cannot_leave_does_not_stay_on_the_skeleton` | `threw=None`, 스켈레톤 걷힘, 배너 보임, 카드 보임, 재시도 핸들러 1개 |
| `test_the_retry_button_issues_the_guest_token_the_first_visit_never_got` | 재시도 한 번에 `state.token`·localStorage = `issued-token`, 퍼즐·폼 보임, 배너 내려감, 입력 잠금 해제, 못 받았던 통계(`연속 0일 · 최고 0일 · 누적 0문제`)까지 따라옴 |
| `test_coming_back_online_also_retries_the_guest_issue` | `online` 이벤트도 발급부터 이어감 |
| `test_a_guest_issue_that_fails_with_5xx_also_offers_a_retry` | HTTP 5xx 발급 실패도 같은 카드 + 재시도(요청은 나갔으므로 배너는 없다) |

수정 전 코드에 이 테스트를 붙이면 첫 번째가 `threw != None` 으로 실패한다.

### D-18-2 (MAJOR) — 제출 요청 실패 뒤 입력을 잠그지만 재시도 경로를 표시하지 않는다

**재현.** `navigator.onLine=true` 를 유지한 채 `POST /puzzles/today/guesses` 만 reject:

```
D-18-2 { "online": true, "inputDisabled": true, "bannerShown": true,
         "puzzleStateShown": false,
         "message": "연결이 불안정해요. 다시 시도해주세요.",
         "inputValueKept": "사과" }
```

리뷰의 네 값(`online=true`, `disabled=true`, `bannerVisible=true`, `retryVisible=false`)과 같다.

**원인.** `submitGuess()` 의 `offline` 분기가 `renderOffline(true)` 로 입력·제출을 잠그면서
안내는 `#message` 에만 남겼다. 복구 수단 두 개가 모두 닿지 않는다 — `online` 이벤트는
`navigator.onLine` 이 계속 true 라 오지 않고, 재시도 버튼은 숨어 있는 `#puzzle-state` 안에 있다.
**"잠그는 쪽" 과 "푸는 쪽" 이 서로 다른 화면 상태에 걸려 있던 것**이 원인이다.

**수정.** 같은 분기에서 조회 실패와 **같은** 인라인 카드(`showPuzzleState(t("network_error"))`)를
띄운다. 재시도 버튼이 보이고, 그 재시도는 `restart()` → 서버의 오늘 퍼즐·시도 이력을 다시
받는다. fetch 가 죽은 사이에 제출이 실제로 서버에 **닿았을 수도** 있으므로, 화면을 로컬에서
되살리지 않고 서버 상태와 다시 맞추는 쪽을 골랐다(리뷰의 "복구 과정은 서버 상태와 다시 맞아야
한다"). 같은 문장을 두 군데 띄우지 않게 `#message` 는 비운다.

**증명** (`tests/test_web_js.py`)

- `test_a_submit_that_cannot_leave_shows_a_retry_not_just_a_locked_input`
  → `online=True`, `inputDisabled=True`, 배너 보임, **카드 보임**, `#message` 비어 있음
- `test_the_retry_after_a_failed_submit_resyncs_with_the_server`
  → 서버가 그 시도를 받아둔 상태로 재시도하면 `attempts=[{"guess":"사과","feedback":[True,False]}]`,
    `boardRows=1`, `attemptsLeft=4`, 퍼즐·폼 복귀, 입력 잠금 해제

수정 전 코드에서는 첫 번째가 `stateHidden=True` 로 실패한다.

### D-18-3 (MINOR) — 320px 영어 화면의 머리말이 카드와 뷰포트를 벗어난다

**재현.** 현재 템플릿을 실제 Flask 로 렌더하고 현재 두 CSS 를 인라인한 로컬 스냅샷을 헤드리스
Chrome 155.0.8059.41 의 CDP 로 320×844 에서 측정했다. 외부 폰트 CDN 은 제거해 선언된 시스템
fallback 으로 렌더했다(리뷰와 같은 조건).

```
수정 전 320px /en: innerWidth=369 docScrollWidth=369 cardRight=320 streakRight=369.09375
```

리뷰의 `scrollWidth=369`·스트릭 오른쪽 끝 `369.09375` 와 같다. 360px 에서도 같은 값으로 넘친다.

**원인.** `.header` 가 `flex-wrap` 없는 한 줄 flex 라, 줄바꿈 금지(`white-space: nowrap`)인
`.streak` 와 제목의 최소 단어 폭이 한 행에 고정된다. flex 는 그 둘의 min-content 합이 컨테이너를
넘어도 줄을 바꾸지 않고 그대로 넘긴다.

**수정** (`web/static/style.css`): `.header` 에 `flex-wrap: wrap`, 줄이 나뉘었을 때 위아래가
붙지 않게 `gap` 을 `var(--space-1) var(--space-3)` 로 나눴다. `.streak` 의 nowrap 은 그대로 둔다 —
풀면 `· best 0 ·` 가 아무데서나 쪼개진다.

```
수정 후 320px /en  "0-day streak · best 0 · 0 solved"      → docScrollWidth=320  streakRight=249.28
수정 후 320px /ko  "연속 365일 · 최고 365일 · 누적 1200문제"  → docScrollWidth=320  streakRight=276.27
수정 후 320px /en  "365-day streak · best 365 · 365 solved" → docScrollWidth=320  streakRight=304.09
360 / 390px 도 모두 docScrollWidth == innerWidth (넘침 0)
```

`impeccable detect`(로컬 `0.1.14`)를 수정 후 스냅샷에 다시 돌렸다 — ko/en 기본 뷰포트와
`--viewport 320x844` ko/en 모두 exit 0·출력 없음. 320px 머리말 렌더는
`.scratch/store-launch/design/web-shots/header-320-en-{light,dark}.png` 에 남겼다.

**증명.** `tests/test_web_design.py::test_the_header_lets_the_streak_drop_to_its_own_line` —
`.header` 에 `flex-wrap: wrap` 이 있고 `.streak` 의 nowrap 이 유지되는지를 본다. 레포에 브라우저
러너가 없어서(스펙 "미정 항목" 5) 픽셀 측정 자체는 테스트로 고정하지 못했고, 위 CDP 수치와
detect 출력이 근거다.

**남은 한계(솔직히).** 4자리가 섞인 극단값(`1000-day streak · best 1000 · 2000 solved`)은 320px
에서 여전히 ~9px 넘친다(`docScrollWidth=329`). 현실적 상한인 3자리까지는 16px 여유로 들어간다.
세그먼트별 줄바꿈은 마크업 변경이 필요해 이번 수정 범위에서 뺐다.

### 추가 1건 (코디네이터 지시) — 테스트 픽스처의 MySQL 유휴 연결 누적

**원인.** `tests/conftest.py` 의 function-scope `app` 픽스처는 테스트마다 `create_app()` →
새 엔진 → 새 커넥션 풀을 만드는데, teardown 이 `db.session.remove()`·`db.drop_all()` 만 하고
풀을 닫지 않았다. 버려진 엔진의 풀은 GC 로 닫히지 않으므로 연결이 **프로세스가 끝날 때까지**
MySQL 에 `Sleep` 으로 남는다.

**수정.** teardown 끝에 `db.engine.dispose()` 한 줄. 동작 테스트는 바꾸지 않았고, `app.js` 의
비동기 구조(`fetchJson`·세대·`languageWanted`)도 건드리지 않았다.

**측정.** `information_schema.PROCESSLIST` 를 매 테스트 teardown 후 읽는 **읽기 전용** pytest
플러그인으로 쟀다. 관측 엔진은 `NullPool` 이라 측정 자체가 유휴 연결을 남기지 않고, 관측용
Query 연결 1개는 뺐다. 플러그인은 레포에 넣지 않고 스크래치패드에서 `-p` 로 붙였다.

| 대상 | 테스트 수 | 실행 중 최대 Sleep | 세션 종료 직후 |
|---|---:|---:|---:|
| 수정 전 — `test_web`+`test_guest_api`+`test_guess_flow`+`test_leaderboard` | 43 | **28** | 21 |
| 수정 후 — 같은 집합 | 43 | **1** | 0 |
| 수정 후 — **전체 스위트** | 1301 | **3** | 0 |

요청한 "일정 수준(예: 10 이하)" 을 전체 스위트에서 만족한다.

**같은 시각 다른 워커와의 대조(우연히 잡힌 직접 증거).** 이 전체 스위트가 도는 동안 수정 전
conftest 를 쓰는 다른 워크트리(t36)의 스위트가 병렬로 돌고 있었다. 같은 MySQL 을 1초 간격으로
세 번 찍은 값:

```
17:29:04  t36 Sleep=38  t36 Query=1   t18 Sleep=0  t18 Query=2
17:30:11  t36 Sleep=77  t36 Query=1   t18 Sleep=0  t18 Query=2
17:32:43  t36 Sleep=69  t36 Query=1   t18 Sleep=0  t18 Query=2
```

같은 부하에서 수정 전 워크트리는 70~80개를 들고 있고 수정한 쪽은 0개다.

**정정 1건.** 지시문의 `max_connections=151` 은 이 MySQL 에서는 **500** 이다
(`SHOW VARIABLES LIKE 'max_connections'` → `500`, 관측 시점 `Threads_connected=85`). 누수 자체와
수정은 그대로 유효하지만, 지금 당장 고갈 직전이었다고는 말하지 않는다.

**속도.** 같은 43개 집합을 번갈아 4회씩 쟀다 — 있음 33.5 / 32.9 / 36.7 / 27.1s, 없음
26.6 / 29.7 / 24.6 / 37.6s 로 분포가 겹친다. `Engine.dispose()` 자체에 든 시간은 38회 합계
**0.03s** 였다(호출을 감싸 측정). 의미 있는 회귀로 보지 않는다.

### 미수정 MINOR · 리뷰에 동의하지 않은 항목

없다. 리뷰의 세 결함을 모두 고쳤다. 리뷰 "참고" 의 세 항목(텍스트형 스토어 배지, 글자 수별 타일
크기, 사람이 해야 할 iOS Safari 왕복)은 결함 판정이 아니라 범위 밖 기록이라 그대로 뒀다.

### 전체 검증

```
$ uv run pytest -q            # TEST_DATABASE_URL=...chosung_daily_test_t18, TEST_REDIS_URL=...6
1301 passed in 1034.61s (0:17:14)
[conn-probe] db=chosung_daily_test_t18 tests=1301 max_sleep=3 last_sleep=1 after_session=0

$ uv run ruff check .
All checks passed!
```

- 1294 → 1301: 이번 라운드가 더한 테스트 7개(JS 동작 6 + CSS 계약 1).
- `git diff --check main..HEAD` → exit 0. 작업 트리 clean, 로컬 `main`(`055b56c`) 위.
- 프로덕션 접근·배포·`git push`·외부 서비스 호출 없음. 시크릿 값은 이 문서에 없다.
- 이번 라운드에서 바꾼 파일: `web/static/app.js`, `web/static/style.css`,
  `app/utils/ui_strings.py`, `tests/conftest.py`, `tests/fixtures/js/deleted_state_harness.mjs`,
  `tests/js/web_states_and_sections.mjs`, `tests/test_web_js.py`, `tests/test_web_design.py`,
  `review/impl-evidence-18.md`, `.scratch/store-launch/design/web-shots/header-320-en-*.png`.
- `tests/fixtures/js/deleted_state_harness.mjs` 는 `ensureToken()` 의 반환 계약이 토큰 → boolean
  으로 바뀌어 발급된 토큰을 `state.token` 에서 읽도록 두 줄 고쳤다. D-14-1 테스트 3개가 보는
  내용은 그대로다.

## 수정 라운드 2 — 최종 리뷰(`review/impl-review-18.md` 라운드 2) 결함 수정

- 라운드 2 판정은 FAIL, 미해결 **BLOCKER 0 / MAJOR 1 / MINOR 0** 이었다. 그 MAJOR 한 건
  (D-18-4)만 고쳤다. 라운드 1 의 D-18-1·2·3 은 모두 FIXED 로 재판정됐고 REPEAT 은 없다.
- 기준: 로컬 `main`. 작업 도중 `main` 이 `055b56c` → **`1afeffa`**(티켓 36 머지)로 전진해서
  이번 rebase 는 no-op 이 아니었다 — 커밋 후 `git rebase main` 을 돌려 6개 커밋을 충돌 없이
  다시 얹었다. `origin/main` 은 쓰지 않았다.
- 전용 테스트 자원 그대로: `chosung_daily_test_t18` / Redis DB 6 / `..._t18_migrations`. 공용
  테스트 DB·Redis DB 1 은 건드리지 않았다.
- 마이그레이션 없음(`git diff --name-only main...HEAD -- migrations` 비어 있음).
  `flask db heads` = `b1c7d4e0a932 (head)` 1줄.
- `review/impl-review-18.md` 는 고치지 않았다. 리팩토링·기능 추가는 없다.
- 리뷰의 재현 방법 그대로 먼저 재현하고, 그 재현을 실패하는 테스트로 고정한 뒤 고쳤다.

### D-18-4 (MAJOR) — 저장된 토큰으로 시작하면 세션 동기화가 생략돼 다른 계정이 삭제된다

**재현.** 리뷰가 적은 방법 그대로 — 기존 node 대역(`tests/js/harness.mjs`)으로 실제 번들을
읽고, `localStorage` 에 토큰만 심고 fetch 경계에서 요청 URL 을 모은 뒤 `init()` 을 돌렸다.
`init`·`ensureToken`·`syncSession` 은 mock 하지 않았다. 리뷰가 적은 기대 1 / 실제 0 과 같다.

```
# 수정 전 (HEAD=22a76f0 의 web/static/app.js)
$ uv run pytest -q tests/test_web_js.py
FAILED tests/test_web_js.py::test_starting_from_a_stored_token_also_syncs_the_session
FAILED tests/test_web_js.py::test_a_backup_restore_syncs_the_session_with_the_restored_guest
FAILED tests/test_web_js.py::test_the_oauth_callback_syncs_the_session_with_the_new_token
3 failed, 47 passed
    assert sync["count"] == 1
E   assert 0 == 1
```

대조군(첫 방문, 삭제 후 재발급)은 수정 전에도 통과했다 — 둘 다 발급 분기를 지나기 때문이다.
즉 실패하는 건 "발급을 **건너뛴**" 경로뿐이고, 이게 결함의 모양과 정확히 일치한다.

**원인.** 라운드 1 의 D-18-1 수정이 `syncSession()` 호출을 `init()` 에서 **새 게스트 발급
성공 분기 안으로** 옮겼다(`web/static/app.js`). `ensureToken()` 은 `localStorage` 에 토큰이
있으면 그 위에서 바로 반환하므로, 첫 방문이 아닌 초기화는 `/session/sync` 를 한 번도 보내지
않는다. 서버는 세션 쿠키(`session["current_guest_id"]`)로 OAuth 연결 대상과 **계정 삭제
대상**을 고른다(`app/api/oauth.py` `sync_session`, `app/web.py` `account_delete`). 그래서
백업 코드로 게스트 B 를 복원하면 화면·API 는 B 인데 세션은 A 로 남고, 삭제 페이지가 A 로
폼을 발급해 폼 대상 검사와 CSRF 를 **둘 다 통과시킨 뒤** A 를 지운다. 증상(삭제 대상이
틀리다)이 아니라 원인(토큰이 바뀌는 경로가 동기화를 안 거친다)을 고쳤다.

**수정.** `ensureToken()` 이 "토큰 확보" 와 "세션 게스트 맞추기" 를 **같이** 책임진다. 토큰이
바뀌는 길은 전부 이 함수를 지나므로, 경로마다 동기화를 흩지 않고 한 지점에서 한다 — 조기
반환을 없애고 발급 분기를 `else` 로 내린 뒤, 마지막에 한 번 동기화한다.

- `state.syncedToken` 에 심어둔 토큰을 기억한다. 같은 토큰으로 두 번 보내지 않고
  (`online`·재시도는 둘 다 `restart()` → `ensureToken()` 으로 돌아온다), 못 심은 것만 다시
  보낸다. 동기화 조건이 `state.token !== null` 조기 반환 **아래**에 있는 이유가 이것이다.
- `syncSession()` 이 fetch 거부를 받는다. 실패하면 `syncedToken` 을 되돌려 "아직 못 심었다"
  로 남긴다(낙관적으로 먼저 적어서 중복 요청은 막는다).

**중간에 드러난 두 번째 결함(같은 수정 안).** 첫 수정본은 `syncSession()` 의 거부를 아무도
받지 않았다. 저장된 토큰이 있는 오프라인 재방문은 발급 요청 없이 **곧장** 동기화로 오는데,
부르는 쪽은 응답을 기다리지 않으므로 거부가 받아줄 사람 없는 rejection 이 된다. 기존
테스트가 바로 이걸 잡았다 — 내 추측이 아니라 실행 출력이다.

```
$ uv run pytest -q tests/test_web.py
FAILED tests/test_web.py::test_deleted_signal_keeps_the_token_when_the_check_cannot_reach_the_server
  TypeError: network error
      at fetchStub (tests/fixtures/js/deleted_state_harness.mjs:112:44)
      at syncSession (app.js:938:9)
      at Object.ensureToken (app.js:216:3)
```

`try/catch` + 재시도까지 넣은 뒤 이 테스트도 통과한다. 이 경로도 아래 표의 (2b) 로 고정했다.

**증명하는 테스트.** 토큰이 바뀌는 경로 **6개**를 한 표로 묶어
`tests/js/web_states_and_sections.mjs` + `tests/test_web_js.py` 에 넣었다. 경로마다 두 가지를
센다 — `/session/sync` 가 **정확히 1회** 나갔는지, 그 Authorization 이 화면이 실제로 쓰는
토큰(`/me/stats` 의 Authorization)과 **같은지**. 둘이 같으면 삭제 폼의 대상(세션 게스트)과
화면의 게스트가 어긋날 수 없다. 함수를 손으로 부르지 않고 `init()`·실제 버튼 핸들러를 돌린다.

| # | 경로 | 테스트 | 수정 전 |
|---|---|---|---|
| 1 | 첫 발급(저장 토큰 없음) | `test_a_first_visit_syncs_the_session_with_the_issued_guest` | 통과(대조군) |
| 2 | 저장 토큰으로 시작(복원 후 새로고침·쿠키만 없는 재방문) | `test_starting_from_a_stored_token_also_syncs_the_session` | **실패** |
| 2b | 저장 토큰 + 오프라인 재방문 → `online` 재시도 | `test_a_sync_that_cannot_leave_is_retried_when_the_connection_returns` | **실패(하니스 crash)** |
| 3 | 백업 코드 복원(실제 복원 버튼 → 새로고침 → 다음 로드) | `test_a_backup_restore_syncs_the_session_with_the_restored_guest` | **실패** |
| 4 | OAuth 복귀(`?login_token=`) | `test_the_oauth_callback_syncs_the_session_with_the_new_token` | **실패** |
| 5 | 계정 삭제 후 재발급(`?deleted=1`, 옛 토큰 401) | `test_a_fresh_guest_after_account_deletion_syncs_the_emptied_session` | 통과(대조군) |

(3) 은 복원 버튼 핸들러를 실제로 눌러 `location.reload()` 호출 1회와 저장소가 B 로 바뀐 것을
보고, 그 다음 로드를 (2) 와 같은 길로 한 번 더 실제로 돌려서 B 로 동기화되는지 본다. 대역의
`location.reload()` 는 아무것도 하지 않기 때문이다.

**역변이 확인(테스트가 정말 잡는지).** 수정 전 번들로 되돌려 돌리면 (2)(3)(4) 가 실패하고,
`syncSession()` 의 `try/catch` 만 떼면 (2b) 가 하니스 crash 로 실패한다(위 두 출력).

**삭제 대상이 화면의 게스트인지 — 서버 쪽 절반.** 이건 이미 서버 테스트가 덮고 있어서 새로
더하지 않았다: `tests/test_account_delete_page.py` 의
`test_a_form_rendered_for_another_guest_is_refused_after_a_session_switch` 와
`test_the_switched_guest_can_delete_itself_from_a_freshly_rendered_form` 가 실제
`POST /api/v1/session/sync` 로 세션을 심어 "전환된 게스트가 자기를 지운다" 를 본다. 빠진
고리는 **프론트가 그 요청을 보내는가** 하나였고, 위 6개 테스트가 그걸 고정한다.

### 전체 검증 (라운드 2 수정 후, 로컬 `main` = `1afeffa` 위)

```
$ uv run pytest -q   # TEST_DATABASE_URL=...chosung_daily_test_t18, TEST_REDIS_URL=...6
1403 passed in 1193.43s (0:19:53)

$ uv run ruff check .
All checks passed!
```

- `uv run pytest -q --collect-only` → **1403 tests collected**. 수는 전부 통과한 수와 같다.
  1403 = 티켓 36 머지로 늘어난 `main` 의 수 + 티켓 18 이 더한 테스트. 이번 라운드가 더한 건
  6개(경로 1·2·2b·3·4·5)이고, 기존 테스트가 빠지거나 skip 으로 바뀐 건 없다.
- 첫 두 번의 전체 실행은 **고아 pytest 프로세스가 같은 테스트 DB 를 잡고 있어** 픽스처가
  대량 ERROR 로 죽었다(2시간 50분 교착). 코디네이터가 양쪽을 종료한 뒤 단독으로 한 번 돌린
  결과가 위 출력이다. 결함이 아니라 실행 환경 경합이었다 — 같은 커밋으로 `tests/test_web_js.py`
  (51 passed)·`tests/test_web.py`·`tests/test_web_design.py`(합계 106 passed)는 교착 중에도
  정상 통과했다.
- `git diff --check main...HEAD` → exit 0. 작업 트리 clean, 로컬 `main`(`1afeffa`) 위.
  rebase 는 충돌 없이 6개 커밋을 다시 얹었다(`Successfully rebased and updated`).
- 디자인 재검증은 이번 라운드에서 다시 돌리지 않았다 — 바꾼 파일이 `web/static/app.js` 와
  테스트뿐이고, CSS·템플릿은 한 줄도 건드리지 않았다. 리뷰의 `impeccable detect` 입력은
  실행 스크립트를 제거한 정적 HTML + 인라인 CSS 라서 `app.js` 는 애초에 검사 대상이 아니다.
- 이번 라운드에서 바꾼 파일 3개: `web/static/app.js`, `tests/js/web_states_and_sections.mjs`,
  `tests/test_web_js.py`(+ 이 문서). 애플리케이션 변경은 `app.js` 한 파일이다.
- 미수정 MINOR: **없다**(라운드 2 의 미해결은 MAJOR 1건뿐이었다). 리뷰어 지적이 틀렸다고
  본 항목도 없다 — D-18-4 는 재현됐고, 리뷰가 적은 기대/실제 값과 같았다.
- 프로덕션 접근·배포·`git push`·외부 서비스 호출 없음. 공용 테스트 DB·Redis DB 1 은 건드리지
  않았다. 시크릿 값은 이 문서에 없다.
