# 티켓 46 증거 — E2E 발견 결함 수정 묶음 1

- 대상: 로컬 `main`(`ee960dd`, 티켓 42 머지 포함) 위의 worktree `dosaem/t46-e2e-fixes-1`.
- 범위: 브리프의 **6개 항목**(D-42-1~4 · D-41-1 · iOS 키체인 확인) + 코디네이터가
  중간에 범위에 넣은 다크 모드 대비 토큰 1건(§7).
- push·NAS·배포·외부 호출·계정/결제/인증 정보 입력·시크릿 기록·하위 워커: 하지 않았다.

## 0. 한 줄 요약

E2E 가 적어 둔 앱 결함 4건과 워크플로 결함 1건을 **전부 고쳤고**, 다섯 건 모두
"다시 나면 실패하는 테스트" 를 함께 넣었다 — 웹 E2E 가 **48/48 통과**(이전 39/48),
전체 pytest 1756개 통과, `impeccable detect` 는 바꾼 화면 전부 0건이다. 6번 항목
(iOS 키체인)은 확인만 했고 법적 문서는 고치지 않았다 — 방침에 빠진 사실을
`docs/RELEASE.md` 사람 확인 항목에 적었다.

## 1. 항목별 결과

| # | 결함 | 고친 자리 | 다시 나면 실패하는 테스트 |
|---|---|---|---|
| 1 | D-42-1 (MAJOR) 복사 버튼 라벨이 `<built-in method copy …>` | `web/templates/index.html` — `{{ t["copy"] }}` | `test_template_never_reaches_a_dict_method_by_attribute` · `test_no_page_renders_a_python_object_repr` · `test_the_copy_button_shows_the_dictionary_word` |
| 2 | D-42-2 백업 코드 칸에 라벨 없음 (axe critical) | `index.html` `aria-label` + 사전 키 `backup_code_label` | `test_the_backup_code_box_has_an_accessible_name` · E2E 의 `expectAxeClean`(known 목록 비움) |
| 3 | D-42-3 (MAJOR) 삭제 완료 안내가 안 보임 | `web/static/app.js` — 안내를 `restart()` **뒤**로 | `test_the_deletion_notice_is_still_on_screen_when_the_first_load_finishes` (하네스 `init` 모드) |
| 4 | D-42-4 390px 에서 배정표 링크를 못 누름 | 운영자 표 5개를 `.admin-table-scroll` 로 감쌈 | E2E `09-admin` 의 문서 폭 단정 + **실제 탭** |
| 5 | D-41-1 ASC `token()` 의 P8 임시 파일 | 워크플로 5개 `try/finally` + 서술 수정 | `test_the_temp_signing_key_is_removed_in_a_finally`(5개) · `…_is_gone_even_when_openssl_blows_up`(실행) |
| 6 | iOS 키체인 게스트 토큰 | **확인만** — 방침·앱 안내에 저장 방식 서술 없음 | — (사람 확인 항목으로 `docs/RELEASE.md` "### 46.") |

각 항목은 **먼저 재현 → 실패하는 테스트로 고정 → 고침** 순서로 했다. 아래 절마다
"고치기 전에 그 테스트가 실제로 실패하는 것" 을 확인한 출력을 적는다.

## 2. D-42-1 — `{{ t.copy }}` 가 사전 키가 아니라 `dict.copy` 를 집는다

**원인.** Jinja 의 속성 접근은 `getattr` 를 먼저 본다. `t` 는 파이썬 `dict` 라서
`t.copy` 는 **메서드 객체**이고, 사전 키 `"copy"` 는 보지도 않는다.

**고친 것.** 키 이름을 바꾸지 않고 첨자로 읽는다 — `{{ t["copy"] }}`. 키 이름을 바꾸면
`#ui-strings` JSON 을 읽는 JS(`t("copy")`)와 `app/utils/ui_strings.py` 도 같이 바꿔야
하는데, 문제는 키가 아니라 **읽는 방법**이다.

**전수 검색.** 템플릿 18개의 모든 속성 접근(`{{ }}`·`{% %}` 안)을 뽑아
`dir(dict)` 와 대조했다. 걸리는 것은 이 한 곳뿐이었다:

```
$ grep -rhoE '\{\{[^}]*\}\}|\{%[^%]*%\}' web/templates/ \
    | grep -oE '[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*' | sort -u
…  pagination.items  …  stock.items  …  t.copy  …
```

- `pagination.items` 는 SQLAlchemy `Pagination.items`(정상).
- `stock.items()` 는 **일부러 메서드를 부르는 것**이다(`{% for … in stock.items() %}`).
- 남는 건 `t.copy` 하나. 그래서 고친 자리도 한 곳이다.

**재발 방지 둘.**

1. `tests/test_ui_strings.py::test_template_never_reaches_a_dict_method_by_attribute`
   — `web/templates/**/*.html` 전부에서 `t.<이름>` 을 뽑아 `dir(dict)` 와 겹치면
   실패한다. 사전에 `copy` 라는 키가 있는 것 자체는 막지 않는다(막아야 할 것은 읽는
   방법이다).
2. `tests/test_web.py::test_no_page_renders_a_python_object_repr` — `/`·`/privacy`·
   `/terms`·`/account/delete` × ko/en 8장을 실제로 렌더해 `<built-in method`·
   `<bound method`·`<function `·` object at 0x` 가 없는지 본다. **이 결함이 지금까지
   안 잡힌 이유가 "렌더된 HTML 을 보는 테스트가 없었다" 라서**, 같은 종류를 통째로 막는다.

같은 파일의 `test_template_only_uses_keys_that_exist` 는 `t.key` 만 보던 정규식이라
첨자로 바꾸면 그 키를 놓친다 — `t["key"]` 도 같이 세도록 넓혔다.

**고치기 전에 실패하는 것을 확인했다**(주석 안의 `t.copy` 가 먼저 걸려서 주석 문구도
같이 고쳤다):

```
$ uv run pytest tests/test_ui_strings.py -q
AssertionError: 첨자(t["키"])로 읽어야 한다: ['web/templates/index.html: t.copy']
```

## 3. D-42-2 — 백업 코드 칸의 접근 가능한 이름

읽기 전용이라 값이 늘 채워져 `placeholder` 를 쓸 수 없다(바로 아래 복원 칸은
placeholder 가 라벨 역할을 해서 axe 에 안 걸렸다). 사전에 `backup_code_label`
(ko "내 백업 코드" / en "My backup code")을 더하고 `aria-label` 로 붙였다.

E2E 의 `expectAxeClean(…, known)` 에서 D-42-2 항목을 지웠다 — 그 헬퍼는 known 에
적힌 위반이 **사라지면** "고쳐졌으면 known 에서 지워라" 로 실패하므로, 항목을 남겨
두면 수정 자체가 실패로 보인다.

## 4. D-42-3 — 삭제 완료 안내가 한 번도 안 보인다

**원인.** `init()` 의 순서다. `discardDeletedAccountState()` 가
`showMessage(t("account_deleted"))` 로 적은 직후 `restart()` →
`discardLocalPlayState()` → `showMessage("")` 가 지운다.

**고친 것.** 그 함수는 이제 **"안내를 띄워야 한다" 만 돌려주고**(`true`/`false`),
`init()` 이 `restart()` **뒤에** 띄운다. 같은 규칙이 이미 `PUZZLE_CHANGED` 안내에
쓰이고 있었다(`handleSubmit` 의 "화면을 비운 뒤에 띄운다" 주석) — 그 규칙을 삭제
경로에도 맞춘 것이다.

**테스트.** 기존 Node 하네스(`tests/fixtures/js/deleted_state_harness.mjs`)는
`discardDeletedAccountState()` → `ensureToken()` 을 **따로** 불러서, 순서 결함을
구조적으로 못 본다. 그래서 하네스에 `init` 모드를 더했다 — 파일 끝의 그 `init()` 을
통째로 돌리고, 거쳐 간 문구 목록이 아니라 **마지막에 화면에 남은 문구**
(`finalMessage`)를 돌려준다. 첫 화면 한 벌(`/me/stats`·`/puzzles/today`·순위·통계)이
실제로 조회되므로 모양만 맞는 최소 응답을 대역에 더했다.

고치기 전 동작을 하네스로 직접 재현했다(수정본에서 `showMessage` 를 옛 자리로
되돌려 1회 실행):

```
REGRESSION finalMessage= ''   messages= ['계정과 기록을 삭제했어요. …', '']
```

수정본:

```
init token-is-dead      finalMessage= '계정과 기록을 삭제했어요. 새 기록으로 다시 시작합니다.'
init token-is-alive     finalMessage= ''            ← 가짜 신호에는 안내가 없다
init probe-unreachable  finalMessage= ''  search='?deleted=1'
```

기존 세 테스트(D-14-1 가짜 신호·오프라인 확인 실패)는 `steps` 모드로 그대로 돈다.
`token-is-dead` 의 `assert out["messages"]` 한 줄만 새 `init` 모드 테스트로 옮겼다 —
문구가 더 이상 그 함수 안에서 나오지 않기 때문이고, 그게 바로 이 수정의 요점이다.

## 5. D-42-4 — 390px 에서 배정표 링크를 못 누른다

**원인.** 표가 **페이지째로** 넘쳐(문서 504px / 뷰포트 390px) 문서에 가로 스크롤이
생겼고, 마지막 열의 링크를 가운데로 밀어도 옆 행의 칸(`td.admin-cell-answer` 등)이
그 자리의 포인터 이벤트를 가로챘다.

**고친 것.** 운영자 표 **5개 전부**(`schedule`·`words`·`books`·`import`·
`schedule_replace`)를 `.admin-table-scroll`(`overflow-x: auto`, `tabindex="0"`)로
감쌌다. 운영자 화면 폭이 디자인 시스템 §10 을 의도적으로 벗어난다는 결정
(README "15.")은 **그대로다** — 표는 제 폭(487px)을 지키고, 넘치는 쪽이 페이지가
아니라 표의 상자다. `tabindex="0"` 은 키보드로도 밀 수 있게 둔 것이다
(axe `scrollable-region-focusable`; `import` 결과표처럼 안에 포커스 가능한 자식이
없는 표가 있다).

**실측**(E2E 09-admin mobile-390 의 `steps.log`):

```
배정표 폭: 문서 390px · 표 487px · 상자 358px · 뷰포트 390px
```

문서가 뷰포트와 같고(가로 스크롤 없음), 표는 상자 안에서 민다. E2E 는 이제 우회
(`page.goto(href)`) 없이 **실제로 링크를 탭**하고 교체 화면까지 간다.

## 6. D-41-1 — ASC `token()` 의 P8 임시 파일

**원인.** `openssl dgst -sign` 이 **파일 경로만** 받아서 P8 를
`NamedTemporaryFile(delete=False)` 로 쓰는데, `os.unlink` 가 정상 경로에만 있었다.
`openssl` 이 없거나 죽으면 `subprocess.run` 이 던지고 그 줄에 닿지 못한다 —
self-hosted 러너는 잡이 끝나도 사용자 맥이 남아서 `/tmp/*.p8` 가 쌓인다.

**고친 것.** 같은 `token()` 을 쓰는 **워크플로 5개 전부**(`asc-status`·`asc-submit`·
`asc-diagnose`·`asc-build-compliance`·`testflight-tester`)에서 서명을 `try/finally`
로 감쌌다.

**서술도 사실대로.** 머리말과 `docs/RELEASE.md` `#### 41.3` 이 "키를 파일로
떨어뜨리지 않는다 / 지울 필요가 없는 쪽" 이라고 적고 있었는데, P8 임시 파일은 분명히
디스크에 쓴다. "fastlane 용 `api_key.json` 은 만들지 않는다. JWT 서명용 P8 임시
파일은 서명 직후 `try/finally` 로 지운다" 로 고쳤다(5개 워크플로 + RELEASE).

**테스트 둘.**

1. `test_the_temp_signing_key_is_removed_in_a_finally`(5개 파라미터) — 글자가 아니라
   **AST** 를 본다. `token()` 안의 `Try.finalbody` 에 `os.unlink` 호출이 있어야 한다.
   들여쓰기·줄바꿈이 달라져도 같은 계약을 지키는지 알 수 있다.
2. `test_the_temp_signing_key_is_gone_even_when_openssl_blows_up` — `asc-build-compliance`
   의 Python 스텝을 **실제로 돌린다**. `tempfile.tempdir` 를 `tmp_path` 로 돌리고
   (`/tmp` 는 안 건드린다) `openssl dgst` 만 `FileNotFoundError` 로 터뜨린 뒤, 그
   디렉터리에 `*.p8` 가 남지 않는 것을 본다. 정상 경로용 짝(`…_after_a_normal_run`)도 같이.

`test_no_helper_writes_the_api_key_to_disk` 는 **실행되는 코드**(heredoc 안 Python)만
보도록 좁혔다 — 머리말이 "`api_key.json` 은 만들지 않는다" 라고 그 이름을 말해야
하는데, 파일 전체를 보던 기존 단정이 그 **말**에 걸렸다. 말은 파일을 만들지 않는다.

**고치기 전에 실패하는 것을 확인했다**(`asc-build-compliance` 의 `try/finally` 만
되돌려 1회 실행):

```
FAILED …::test_the_temp_signing_key_is_removed_in_a_finally[asc-build-compliance.yml]
FAILED …::test_the_temp_signing_key_is_gone_even_when_openssl_blows_up
```

## 7. 범위에 들어온 추가 1건 — 다크 모드 `--color-destructive` 대비

D-42-4 를 확인하려고 운영자 화면에 `impeccable detect` 를 돌리다 **이 티켓과 무관한
기존 결함**을 찾았다: 다크 모드의 `--color-destructive`(#ef4444)가 카드(#1c2433) 위
**4.1:1** 로 WCAG AA(4.5:1) 미달이다 — 단어 목록의 "삭제" 버튼 3건, 배정표 잔량 경고
문구 2건. 생성된 스냅샷에서 내 래퍼 `div` 만 지우고 다시 돌려도 같은 3건이 그대로
나오는 것으로 **내 변경과 무관함**을 확인했다.

코디네이터에게 물었고(`orca orchestration ask`, 2026-10-16) **"출시 품질·접근성이라
이 티켓에서 같이 고쳐라"** 는 답을 받아 고쳤다.

- 글자 전용 토큰 `--color-destructive-text` 를 더했다 — 라이트 `#dc2626`(기존과 같음),
  다크 `#f87171`.
- **면 색은 그대로 둔다.** `account.css` 의 삭제 버튼이 `--color-destructive` 를
  **배경**으로 쓰고 흰 글자를 얹어서, 면을 밝히면 그쪽 대비가 반대로 나빠진다.
- 글자 쓰임 **네 곳**만 옮겼다: `admin.css` 의 `.admin-button-danger`·`.admin-tag-error`·
  `.admin-stock-low .admin-stock-note`, `style.css` 의 `.message`. 테두리 쓰임
  (`.admin-error`·`.admin-stock-low`·`.admin-tag-error` 의 border)은 그대로다 —
  비텍스트 요소 기준 3:1 을 #ef4444(4.1:1)가 이미 넘는다.

실측 대비(직접 계산):

| | 카드 | 배경 | muted |
|---|---|---|---|
| 라이트 `#dc2626` | 4.83 | 4.62 | 4.43 |
| 다크 `#ef4444` (전) | **4.14** | 4.63 | — |
| 다크 `#f87171` (후) | **5.63** | 6.30 | 4.79 |

(라이트 muted 4.43 은 기준 미달이지만 **글자 쓰임이 없는 조합**이다 — `.admin-error`
만 muted 배경이고 그 안의 글자는 destructive 가 아니다.)

디자인 시스템 문서(`.scratch/store-launch/design-system/…/OVERRIDES.md`)는 `.scratch`
라 고치지 않았다 — 코디네이터 지시대로 근거를 README "### 46." 에 적었다.

## 8. 6번 항목 — iOS 키체인의 게스트 토큰 (확인만)

**사실.** 앱의 게스트 토큰은 `flutter_secure_storage` 로 iOS Keychain /
Android EncryptedSharedPreferences 에 들어간다
(`mobile/lib/guest/guest_token_store.dart`, `accessibility: first_unlock`).
iOS Keychain 은 **앱을 지워도 남아서** 재설치하면 같은 기록이 이어진다. 레포는 이미
그 성질을 알고 쓰고 있다 — 온보딩 완료 플래그는 일부러 `shared_preferences` 에 둔다
(`mobile/lib/onboarding/onboarding_store.dart`, README "완료 플래그는
`shared_preferences`, 게스트 토큰은 Keychain").

**사용자 결정(2026-10-16): 의도된 동작으로 유지.**

**방침·안내 확인 결과 — 빠져 있다.**

| 본 자리 | 적혀 있는 것 | 빠진 것 |
|---|---|---|
| `/privacy` `#automatic-collection` (ko·en) | 게스트 토큰은 **브라우저 localStorage** 에 저장, 사이트 데이터 삭제로 지울 수 있다 | 앱의 저장 위치(기기 보안 저장소), 앱 삭제 후에도 남는다는 사실 |
| `/privacy` `#collection` "게스트 토큰" | "첫 방문·첫 실행 때 … 기기에 저장합니다" | 어디에 어떻게, 지우는 방법 |
| 앱 문구 `mobile/assets/translations/{ko,en}.json` | `account.delete_body` 등 삭제 **결과**만 | 저장 방식 안내 자체가 없음 (`account.*`·`records.*`·`onboarding.*` 전수 확인) |

**법적 문서는 고치지 않았다**(브리프 지시). `docs/RELEASE.md` 의 사람 확인 항목
"### 16." 에 `- [ ] **방침에 추가 필요: …**` 체크박스를 더하고, 상세를 새 절
"### 46." 에 적었다.

## 9. 검증 (실제 출력)

### 9.1 웹 E2E — 48/48

```
$ E2E_TICKET=46 scripts/e2e_web.sh --reporter=line
[e2e-stack] DB chosung_daily_e2e_t46 준비 … flask db upgrade … (마이그레이션 11개)
[e2e-stack] app 기동 / app-nostore 기동 / worker 기동 / beat 기동
[e2e-stack] 포트 5046 /health 응답 확인 · 포트 5146 /health 응답 확인
단어 시드: ko 20개 추가, en 12개 추가
퍼즐 배정: 못박음 10건, 자동 배정 {'ko': 25, 'en': 25}
…
  48 passed (1.1m)
[e2e-stack] DB chosung_daily_e2e_t46 drop · Redis DB 14 flush · down 완료
```

이전 판(티켓 42)은 **39 통과 / 9 실패**였고, 실패 9개가 전부 D-42-1~4 를 가리키는
단정이었다. 그 단정들은 이제 `expect.soft` 가 아니라 **보통 단정**이다 — 결함이
돌아오면 시나리오가 그 자리에서 끊긴다.

axe 는 50회 검사에서 위반 **0건**이다(이전 46회 중 D-42-2 1종). `expectAxeClean` 의
known 목록은 이제 비어 있다.

### 9.2 전체 pytest · ruff · Flutter

```
$ uv run ruff check .
All checks passed!

$ uv run pytest -q
   (TEST_DATABASE_URL=…/chosung_daily_test_t46, TEST_REDIS_URL=…/6)
1756 passed in 1030.58s (0:17:10)

$ cd mobile && flutter analyze
No issues found! (ran in 3.8s)          ← exit 0 (info 포함)

$ cd mobile && flutter test
00:35 +796: All tests passed!            ← exit 0
```

### 9.3 `impeccable detect` — 바꾼 화면 전부 0건

스냅샷 생성 스크립트를 레포에 남겼다: **`review/detect-snapshots-46.py`**
(플레이어 "내 기록" 섹션 ko/en × light/dark + 운영자 단어 목록·CSV 결과표).
운영자의 나머지 표는 티켓 23 의 `review/admin-detect-snapshot-23.py` 가 이미 뽑고,
리더보드는 티켓 38 의 `review/web-detect-snapshots-38.py` 가 뽑는다 — 셋 다 돌렸다.

```
$ uv run python review/detect-snapshots-46.py <디렉터리> && (cd <디렉터리> && python3 -m http.server 9446 &)
$ for p in records-{ko,en}-{light,dark} admin-words admin-import; do
    ~/.impeccable/bin/0.1.14/impeccable detect --json http://127.0.0.1:9446/$p.html
  done
records-ko-light: 0   records-ko-dark: 0   records-en-light: 0   records-en-dark: 0
admin-words:      0   admin-import:     0

$ # 티켓 23 운영자 스냅샷 10장 (회귀)
schedule_low: 0  schedule_en: 0  schedule_replace: 0  schedule_replace_empty: 0
settings: 0  settings_error: 0  books: 0  books_form: 0  books_empty: 0  schedule_ok: 0

$ # 티켓 38 리더보드 스냅샷 4장 (회귀 — style.css 의 .message 가 바뀌었다)
ko-light: 0  ko-dark: 0  en-light: 0  en-dark: 0

$ impeccable detect --viewport 390x844  (records ko/en·다크 · admin-words · admin-import
                                          · schedule_low · schedule_replace · books)
EXIT390=0
$ impeccable detect --viewport 320x844  (records-ko-light · admin-words · schedule_low)
EXIT320=0
$ impeccable detect --viewport 1280x900 (admin-words · schedule_low)
EXIT1280=0
```

§7 의 토큰을 고치기 **전**에는 `admin-words` 3건 · `schedule_low` 2건 ·
`schedule_en` 2건이었다(전부 `low-contrast`). 지금은 0건이다.

## 10. 테스트 자원

- MySQL: pytest 는 `chosung_daily_test_t46`(+`_migrations`)로 돌렸다 — 레포의 다른
  티켓 DB 와 같은 관례로 **남겨 뒀다**(리뷰어가 다시 만들 필요 없게). E2E 스키마
  `chosung_daily_e2e_t46` 은 `down` 이 drop 했다.
- Redis: E2E 는 **14**, 이 티켓의 pytest 는 **6**. 배정표(`scripts/e2e/env.sh` 의
  `e2e_redis_db_for_ticket`)와 README 에 두 줄을 더했고,
  `tests/test_e2e_scripts.py` 의 `E2E_TICKETS`·`RESERVED_REDIS_DBS` 도 같이 넓혔다 —
  그래야 `test_every_ticket_gets_its_own_redis_db` 가 46 을 본다.
- **D-42-8(열린 MINOR)은 이 티켓이 고치지 않았다** — E2E 티켓 43 의 번호 13 이 티켓
  43 의 pytest 번호와 겹치는 건이다. 범위 밖이라 배정표에 주의 한 줄만 적었다.
- 산출물(`e2e-artifacts/`)·`tests/e2e/web/node_modules/` 는 gitignore 다.

## 11. 남은 것 / 넘기는 것

- **법적 문서 문안**: §8 의 "방침에 추가 필요" 1건. 사람이 정해
  `/privacy` ko·en 에 넣고 `LEGAL_EFFECTIVE_DATE` 를 올린다
  (`docs/RELEASE.md` "### 16." 체크박스 · "### 46.").
- **D-42-8**: E2E 43 ↔ pytest 43 의 Redis 13 겹침. 티켓 43 쪽 자원이라 코디네이터 몫.
- **디자인 시스템 문서**: `--color-destructive-text` 는 `.scratch/` 의 OVERRIDES 표에
  없다(§7). `.scratch` 수정 금지라 README "### 46." 이 근거를 들고 있다 — 표를
  갱신할지는 코디네이터 판단이다.
