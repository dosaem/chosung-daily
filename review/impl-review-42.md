# 티켓 42 최종 리뷰 — 웹 E2E (Playwright, 실제 스택) · 라운드 1

- 대상: `dosaem/t42-e2e-web` (`3e24a07`, 로컬 `main` `d27417c` 위 커밋 1개, clean 트리).
  `git diff main...HEAD` 28파일 +2892, 전부 추가 — `app/`·`web/`·`migrations/`·`mobile/`·
  `.scratch/` 무변경.
- 증거(`review/impl-evidence-42.md`)를 믿지 않고 직접 돌렸다: `scripts/e2e_web.sh` 한 판 ·
  `uv run ruff check .` · `uv run pytest -q`(전용 DB `chosung_daily_test_t42`, Redis 5) ·
  `flutter analyze` · `flutter test`. 네이티브 변경이 없어 apk 빌드는 하지 않았다.
- 코디네이터 메모(라운드 1 중 수신) 반영: 앱 결함(D-42-1~4)을 가리키는 실패 9건은 의도된
  것이라 티켓 결함으로 세지 않는다. 대신 4건의 재현 여부, "고쳐지면 통과하는가", E2E 가
  놓친 앱 결함, 실제 스택·사람 순서 셀렉터·advance_day 경로·자정 가드·자원 격리·정답 유출을
  봤다.

## 1. 직접 돌린 결과

| 검증 | 결과 |
|---|---|
| `scripts/e2e_web.sh --reporter=line` (2026-10-16 00:56 KST) | **33 통과 / 9 실패 (1.3분)** — 증거와 동일. 실패 9건의 단정은 전부 D-42-1(4)·D-42-2(4)·D-42-3(4)·D-42-4(2) |
| 스택 | gunicorn ×2(5042/5142) + Celery worker/beat 실제 기동, `chosung_daily_e2e_t42` 마이그레이션 11개, Redis 4. `down` 뒤 `status` 프로세스 없음 · DB drop 확인 · Redis 4 `dbsize 0` |
| 산출물 | `e2e-artifacts/web/` 스크린샷 132장 · axe 46회(위반은 `04-backup-restore-*/axe-records.json` 4개뿐, 전부 `label @ #token-display`) · `steps.log` 단계 로그 · gitignore 로 `git status` clean |
| `uv run ruff check .` | All checks passed (`ruff format --check` 는 main 자체가 70파일 미포맷이라 게이트 아님) |
| `uv run pytest -q` (TEST_DATABASE_URL=…/chosung_daily_test_t42, TEST_REDIS_URL=…/5) | **1713 passed in 903.92s (0:15:03)**, exit 0 — `tests/test_e2e_scripts.py` 20개 포함 |
| `flutter analyze` | No issues found (exit 0) |
| `flutter test` | +796 All tests passed |

## 2. 체크박스별 충족 여부

| 항목 | 판정 | 근거 |
|---|---|---|
| 시나리오 1 첫 방문 (오답→정답→결과→공유) | 충족 | `01-first-visit.spec.mjs` ko/en × 2뷰포트. 남은 기회 5→4, 피드백 타일 correct/wrong 혼재, 결과 문구, 순위 섹션의 `#my-rank`(시도·시간)·분포, 클립보드 공유 텍스트에 정답 없음까지 단정. 스크린샷 `01-first-visit-ko/desktop-1280/03-정답-결과.png` 확인 |
| 시나리오 2 실패 5회 → 정답 공개 | 충족 | `02-fail.spec.mjs`. 오답은 정답에서 생성(길이 검증 우회 아님), 폼 사라짐·보드 5행 |
| 시나리오 3 순위표 표기·내 행·복수형 | 충족 | `03-leaderboard.spec.mjs`. 브라우저 2개를 더 열어 실제 제출로 순위 생성, `게스트 #`/`Guest #` + hex 4자리, `1 try`/`3 tries` 리터럴, 정렬, `is-me` 1행 + computed `font-weight` 비교 |
| 시나리오 4 연속 기록 (다음 날 → streak 2, 7일 그리드) | 부분 충족 | `10-streak.spec.mjs` ko 만(D-42-6). streak 1→2 는 `guess_service._record_solve` 의 실제 경로(`last_solved_date == today-1`)를 탄다 — `advance_day.py` 가 `daily_puzzle.puzzle_date`·`guest_stats.last_solved_date`·`daily_stats`·Redis `lb:`/`stats:` 를 하루 내리고 캐시·ratelimit 은 지운다(실측 로그 "DB 76행 시프트, Redis 4키 rename · 23키 삭제"). 7일 그리드는 웹에 없음(`index.html:157` 주석, 앱 S4 몫) → `GET /me/history?days=7` 로 대체. 코디네이터 승인이라고 증거에 적혀 있어 결함으로 세지 않는다 |
| 시나리오 5 백업 코드 → 다른 브라우저 복원 | 충족 (앱 결함 D-42-1·2 로 실패) | `04-backup-restore.spec.mjs`. 빈 컨텍스트에서 복원 후 같은 보드·결과·streak·순위 내 행 |
| 시나리오 6 언어 전환 ko↔en | 충족 | `05-language-switch.spec.mjs`. 퍼즐 언어 칩과 UI 언어(`?lang=`, `Content-Language`, `html[lang]`, 칩 라벨, 순위 접두사)를 분리해서 검증 |
| 시나리오 7 계정 삭제 → 새 게스트 | 충족 (앱 결함 D-42-3 로 실패) | `06-account-delete.spec.mjs`. GET 만으로 미삭제(옛 토큰 200) → 확인 버튼 → 새 토큰·빈 보드 → 옛 토큰 401 |
| 시나리오 8 오프라인/서버 오류 → 복구 | 부분 충족 | `07-offline.spec.mjs` ko 만(D-42-6). `context.setOffline` 실제 차단, 배너 `role=status`, 입력·제출 disabled, 복구 자동 재조회; 500 라우팅 → 인라인 카드 → 재시도 |
| 시나리오 9 배너·CTA 규칙, /privacy·/terms | 충족 | `08-cta-legal.spec.mjs`. 스토어 설정 있는 앱(5042)과 없는 앱(5142)을 각각 — 메타 태그·`.app-cta`·배지 0개까지. 법적 문서는 `?lang=` 유지·h1·연락처 |
| 시나리오 10 관리자 /admin → CSV → 배정 | 충족 (390 은 D-42-4 로 실패) | `09-admin.spec.mjs`. 비로그인 안내 → 백업 코드 복원으로 운영자 → CSV 4갈래(추가 2·중복 1·오류 1) 행별 결과 → 검색 → 배정표(오늘 "교체 불가"·잔량 카드 2) → 먼 날짜 교체 → 확인 |
| 접근성 axe 0 또는 결함 기록 | 충족 | 46회 중 위반 1종(D-42-2)만, `known` 으로 soft 실패·새 위반은 hard. 직접 돌린 axe json 46개 전수 확인 |
| 공용 스택 스크립트 `e2e_stack.sh up\|seed\|down` 소유 | 부분 충족 | up/seed/advance-day/status/down 동작 확인. 그러나 Redis DB 번호가 티켓별로 갈리지 않는다(**D-42-5**) |
| 실제 스택, mock 금지 | 충족 | gunicorn+MySQL+Redis+Celery 실제. `page.route` 는 시나리오 8 의 500 주입 한 곳뿐(브리프가 요구한 "서버 오류 상태") |
| 전용 스키마 + 마이그레이션 + 시드(오늘·내일, ko·en) | 충족 | `chosung_daily_e2e_t42`, `flask db upgrade`, `seed.py` 가 오늘·내일·모레 ko/en 을 못박고 manifest 로 넘김 |
| 시드 단어 `data/seed_words.csv` 만, `word-candidates/` 미사용 | 충족(단서) | `grep -rn word-candidates scripts/ tests/e2e` 0건. en 단어는 새 `scripts/e2e/words_en.csv`(12개) — 브리프 문면과 다르나 증거에 코디네이터 승인이라고 기록. 참고 R-3 |
| 사람 순서 셀렉터, 내부 상태 조작 금지 | 충족 | 누르는 것은 전부 `getByRole`/`getByPlaceholder`/`getByRole("link")`. id 는 상태 영역 읽기에만. `localStorage` 는 읽기만, `page.request` 는 삭제·이력 검증용 API 조회(상태 조작 아님). 운영자 로그인도 복원 화면 경유. 예외: D-42-4 로 탭이 안 될 때 `page.goto(href)` 폴백(결함 기록 뒤 흐름 계속 — 수용) |
| 시계 주입(서버·클라) | 대체 | 주입 안 함. 데이터 시프트(`advance_day.py`) + KST 자정 ±10분 가드(`guard_midnight.py`, up/seed 양쪽 호출). 증거에 코디네이터 결정(2026-10-15 선택지 A)으로 기록 |
| 외부 서비스 금지 (결제·OAuth·푸시) | 충족 | 웹에 결제·광고 없음. OAuth 는 백업 코드·삭제 흐름으로 대체, 실제 왕복은 `docs/RELEASE.md` 실기기 체크리스트(계정 절·690행 웹 로그인→/admin)에 이미 있음. `SLACK_WEBHOOK_URL=""`, 스토어 링크는 가짜 href 만 확인 |
| 스크린샷·단계 로그 `e2e-artifacts/<플랫폼>/<시나리오>/` gitignore | 충족 | `e2e-artifacts/web/<시나리오>/<뷰포트>/NN-*.png` + `steps.log` + `axe-*.json`. 증거 §4.0 대표 이미지 표 |
| 발견한 결함을 고치지 않고 증거에 기록, 테스트는 느슨하게 안 바꿈 | 충족 | D-42-1~4 재현·기대·실제·경로 기록. `expect.soft` + 결함 ID 주석, `skip`/`xfail` 없음, `retries: 0` |
| 한 번에 끝나는 명령 + README "E2E" 절 | 충족 | `scripts/e2e_web.sh`(down→up→seed→test→down), README "E2E (웹 브라우저)" 띄우기·실행·정리·소요(2~3분)·자원 |
| 테스트 자원: DB 이름에 티켓 번호, Redis 번호 지정, 끝나면 정리 | 부분 충족 | DB `…_e2e_t42`·포트 50xx/51xx 는 티켓별. Redis 는 고정 4(D-42-5). `down` 이 프로세스·DB·Redis 정리 — 실측 확인 |
| 금지 사항 (push·NAS·배포·실결제·계정 생성·인증 정보·시크릿·하위 워커) | 충족 | 커밋 1개, push 없음. `env.sh` 의 값은 전부 가짜(example.com·가짜 스토어 URL·고정 테스트 토큰). 시크릿 없음 |
| 완료 조건: rebase·clean·pytest·ruff·flutter analyze/test·E2E 출력 첨부 | 충족 | 위 §1 |

## 3. 결함

### D-42-5 (MAJOR) Redis DB 번호가 `E2E_TICKET` 에 따라 갈리지 않는다 — 43·44 와 같은 Redis 4 를 공유한다

- 파일: `scripts/e2e/env.sh:15` (`E2E_REDIS_DB="${E2E_REDIS_DB:-4}"`), 문서 `scripts/e2e/env.sh:3`·
  `README.md:188`·`review/impl-evidence-42.md:26,381` ("`E2E_TICKET` 하나로 전부 갈린다").
- 재현:
  ```
  $ for t in 42 43 44; do E2E_TICKET=$t bash -c 'source scripts/e2e/env.sh; echo "$E2E_DB $(e2e_redis_url) $E2E_PORT"'; done
  chosung_daily_e2e_t42 redis://127.0.0.1:6379/4 5042
  chosung_daily_e2e_t43 redis://127.0.0.1:6379/4 5043
  chosung_daily_e2e_t44 redis://127.0.0.1:6379/4 5044
  ```
  기대: DB·포트처럼 Redis 번호도 티켓별로 다르다. 실제: 셋 다 4.
- 왜 MAJOR 인가: 이 스크립트는 티켓 43·44 가 **같은 머신에서 동시에** 재사용한다(지금도
  `chosung_daily_e2e_t43` 스키마가 떠 있다). Redis 키에는 스키마 구분이 없다 —
  `puzzle:<날짜>:<언어>` 캐시(`app/services/puzzle_cache.py:38`)에 42 스키마의 puzzle id 가
  들어 있으면 43 의 앱이 그 id 를 그대로 내보내 제출이 409/오답이 되고, `lb:`·`stats:` 는
  두 스택의 기록이 섞이며, 한쪽의 `down`(`flushdb`)이 상대의 실행 중 상태를 지운다.
  `tests/test_e2e_scripts.py::test_resources_carry_the_ticket_number` 는 DB·포트만 보고
  Redis 를 빼놓아 이 회귀를 못 잡는다. 문서 세 곳이 반대로 적혀 있어 43·44 가 기본값을
  믿고 그대로 쓸 가능성이 높다.
- 고치는 방향(참고): 번호를 티켓에서 유도하거나(예: `4 + (E2E_TICKET - 42)`), 최소한 문서를
  "Redis 는 `E2E_REDIS_DB` 를 티켓마다 직접 지정" 으로 바꾸고 테스트에 Redis 비교를 넣는다.
  현재 코디네이터가 pytest 용 번호를 티켓별로 손으로 배정하고 있으므로(42→5, 43→13) 같은
  표에 E2E 용 번호를 두는 것도 방법이다.

### D-42-6 (MINOR) 시나리오 4(연속 기록)·8(오프라인/서버 오류)이 ko 만 돈다

- 파일: `tests/e2e/web/specs/10-streak.spec.mjs:22`, `tests/e2e/web/specs/07-offline.spec.mjs:22,59`
  (`openGame(browser, { lang: "ko" })` 고정, `for (const lang of ["ko","en"])` 없음).
- 브리프 "시나리오 (ko·en 각각, …)". 시나리오 1·2·3·5·7·9 는 둘 다 돌고 6 은 성질상 둘을
  함께 본다. 4 는 en 퍼즐의 streak 경로(`_record_solve` 가 언어 무관인지 — 스펙 US 14)를,
  8 은 en 사전의 `offline_banner`·`puzzle_load_failed`·`retry` 문구를 보지 못한다.
  10 은 운영자 UI 가 ko 전용이라 제외.
- 재현: `scripts/e2e_web.sh specs/10-streak.spec.mjs` → 테스트 1개×2뷰포트뿐.

### D-42-7 (MINOR) 운영자 시나리오의 플레이어 제출이 `"가나다"` 로 고정돼 있다

- 파일: `tests/e2e/web/specs/09-admin.spec.mjs:132` (`await guess(player.page, "가나다")`).
- 정답 길이(지금은 PINNED ko 세 단어가 모두 3글자)에 묶여 있다. `seed.py` 의 `PINNED` 가
  4글자 단어로 바뀌면 서버가 길이 검증(VALIDATION_ERROR)으로 막아 시도가 생기지 않고,
  `guess()` 의 보드 행 수 단정이 먼저 터져 "교체 불가" 검증까지 못 간다. 같은 파일의
  라이브러리가 바로 이 이유로 `wrongGuesses(answer, …)` 를 두고 있다(`lib/game.mjs:46`).
- 재현(사고 실험): `PINNED[KO] = ("냉장고", "지하철", "돈키호테")` 로 두면 mobile-390 2일차
  오늘이 "돈키호테"(4글자) → 운영자 시나리오 실패. 지금 값으로는 통과한다.

## 4. 참고 (결함 아님, 취향·후속)

- R-1 D-42-1~4 는 전부 직접 재현됐다. 코드로도 확인: `web/templates/index.html:175` `{{ t.copy }}`
  (Jinja `getattr` 우선 → `dict.copy`), `:174` `#token-display` 라벨 없음,
  `web/static/app.js:1130→1134→1110→647` (`discardDeletedAccountState` 의 `showMessage` 를
  `restart()`→`discardLocalPlayState()` 의 `showMessage("")` 가 지움), 390 배정표 문서폭 504px.
  고쳐지면 통과하는가: D-42-1·2·4 는 그렇다. D-42-3 은 `#message` 의 `textContent` 를
  **즉시 한 번** 읽는다(`06-account-delete.spec.mjs:52-55`) — 수정이 비동기(퍼즐 로드 뒤 표시)면
  거짓 실패가 날 수 있으니 수정 티켓에서 `toHaveText` 로 바꾸는 편이 안전하다.
- R-2 E2E 가 추가로 보여준 앱 증상(별도 결함으로 세지 않음): D-42-1 의 긴 버튼 라벨 때문에
  `#token-display` 입력칸이 폭 ~24px 로 눌려 **백업 코드가 화면에 보이지 않는다**
  (`04-backup-restore-ko/desktop-1280/01-A-백업코드-복사.png`). D-42-1 수정 뒤 다시 확인할 것.
- R-3 `scripts/e2e/words_en.csv` 는 브리프 문면("`data/seed_words.csv` 만")을 벗어난다. 증거는
  코디네이터 승인이라 적었고 내용은 테스트용 평범한 단어 12개라 유출 위험은 없다 —
  코디네이터가 승인 기록을 확인해 주면 된다.
- R-4 `expectAxeClean` 의 soft 메시지 "`D-42-2 이 고쳐졌다면 이 known 항목을 지워라`" 는
  **위반이 아직 있을 때** 찍힌다(실패 로그에 4회). 고쳐진 경우에는 `hit` 가 null 이라 통과하고
  아무 메시지도 안 난다 — 메시지와 상황이 반대다. 동작엔 문제없고 문구만 헷갈린다.
- R-5 `tests/test_e2e_scripts.py` 의 `advance_day`·가드 호출·실행 순서 테스트는 소스 문자열
  매칭이다. 실제 동작은 E2E 시나리오 10(streak)이 `advance-day` 를 진짜로 부르며 보장하므로
  수용하지만, `_shift_sql` 은 pytest 의 MySQL 로 한 번 실행해 볼 수 있는 자리다.
- R-6 `scripts/e2e_web.sh --reporter=line` 처럼 리포터를 넘기면 설정의 json/html 리포터가
  대체돼 `e2e-artifacts/web/report/results.json` 이 갱신되지 않는다(남은 파일은 이전 판 것).
  README 에 한 줄 적어두면 좋다.
- R-7 실제 OAuth 왕복은 `docs/RELEASE.md` 에 이미 있다(앱 계정 절, 690행 웹 구글 로그인 →
  `/admin`). 이 티켓이 추가로 적을 것은 없었다.

## 5. 판정 근거 요약

- 요구 누락: ko·en 범위 2개 시나리오(MINOR). 스펙과 다른 동작: 없음(시계 주입·7일 그리드·
  en CSV 는 코디네이터 결정으로 기록됨). 검증 안 하는 테스트: 없음(앱 결함 9건은 실제 실패).
  보안·시크릿: 없음. 데이터 손상: **D-42-5** — 동시 실행 시 Redis 공유로 상대 스택 상태를
  오염·삭제. 범위 밖 변경: 없음. 공유 파일(`.gitignore`·`README.md`): 추가만, 기존 절 무변경.

BLOCKER 0 · MAJOR 1 (D-42-5) · MINOR 2 (D-42-6, D-42-7)

판정: FAIL

## 라운드 2

- 대상: `dosaem/t42-e2e-web` `5d0c5f0`(라운드 1 수정 커밋 1개, 로컬 `main` `d27417c` 위 커밋 3개,
  clean 트리). 수정 커밋 diff 10파일 +653/−157 — `scripts/e2e/env.sh`·`seed.py`·`e2e_web.sh`·
  `tests/e2e/web/{lib/game.mjs, specs/07,09,10}`·`tests/test_e2e_scripts.py`·`README.md`·증거.
  `app/`·`web/`·`migrations/`·`mobile/`·`.scratch/` 여전히 무변경.
- 증거(`review/impl-evidence-42.md` "수정 라운드 1")를 믿지 않고 전부 직접 돌렸다. 네이티브 변경이
  없어 apk 빌드는 하지 않았다.

### 1. 직접 돌린 결과 (2026-10-16 01:45~ KST)

| 검증 | 결과 |
|---|---|
| `scripts/e2e_web.sh --reporter=line` | **39 통과 / 9 실패 (1.6분)**, 48개(42→48, +6) — 증거와 동일. 실패 9건의 단정은 전부 앱 결함: D-42-1 ×4 · D-42-2 ×4 · D-42-3 ×4 · D-42-4 ×2(한 테스트). 새로 깨진 것 없음 |
| 스택 | gunicorn ×2(5042/5142) + Celery worker/beat 기동, `chosung_daily_e2e_t42` 마이그레이션 11개, Redis **4**. `down` 뒤 `status` 프로세스 없음 · e2e 스키마 0개 · Redis keyspace 에 db4 없음(비어 있음) · `git status` 0줄 |
| 산출물 | `e2e-artifacts/web/` 폴더 24개(언어별 분리: `07-offline-{ko,en}`·`07-server-error-{ko,en}`·`10-streak-{ko,en}` 포함), 스크린샷 160장, axe json 50개 — 위반은 `04-backup-restore-{ko,en}/*/axe-records.json` 4개뿐, 전부 `label`(D-42-2) |
| `uv run ruff check .` | All checks passed |
| `uv run pytest -q -p no:cacheprovider` (TEST_DATABASE_URL=…/chosung_daily_test_t42, TEST_REDIS_URL=…/5, TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t42_migrations) | **1734 passed in 788.45s (0:13:08)**, exit 0 — `tests/test_e2e_scripts.py` 41개 포함(계약 테스트 +21) |
| `flutter analyze` | No issues found (exit 0) |
| `flutter test` | +796 All tests passed (exit 0) |

### 2. 이전 결함 판정

| ID | 판정 | 근거(직접 확인) |
|---|---|---|
| D-42-5 (MAJOR) Redis 번호 티켓별 미분리 | **FIXED** | `for t in 42 43 44` → `redis://…/4`·`/13`·`/12`, 포트 5042/5142·5043/5143·5044/5144. `E2E_TICKET=99` 는 `source` 와 `scripts/e2e_stack.sh status` 양쪽에서 "배정표에 없다" 로 exit 1(`set -euo pipefail` 경로도 막힘). `E2E_REDIS_DB=9` 직접 지정은 `/9`. `redis()`(flushdb)와 `e2e_redis_url`(앱)이 같은 `E2E_REDIS_DB` 를 읽는다(`env.sh:83`, `e2e_stack.sh:30`). 계약 테스트 4개(`test_resources_carry_the_ticket_number`+Redis, `test_every_ticket_gets_its_own_redis_db`, `test_unassigned_ticket_refuses…`, `test_redis_url_carries_the_assigned_db`) 가 pytest 전체 판에 포함돼 통과. README·`env.sh` 머리말 문구 수정 확인. 단서: 배정표의 **내용**(43→13)은 아래 D-42-8 |
| D-42-6 (MINOR) 시나리오 4·8 ko 전용 | **FIXED** | `07-offline.spec.mjs:24`·`10-streak.spec.mjs:26` 가 `for (const lang of ["ko","en"])`. 실측 48개 중 +6 전부 통과. en 이 실제로 돈 증거: `10-streak-en/desktop-1280/steps.log` 의 `/me/history` 응답이 `{"en":"success","ko":"none"}` ×2일 + `none` (언어별 칸을 `results[lang]` 로 봄), `07-offline-en/*/steps.log` 3단계·`07-server-error-en` 2단계. 한 판에 `advance-day` 4회(desktop ko·en, mobile ko·en) → 끝난 manifest 가 offset −4…0 으로 ko 5·en 5 전부 소진, 마지막 판 오늘 = `지하철`/`bicycle` — `PINNED` 5개가 정확히 필요한 수. `test_pinned_words_cover_every_day_the_streak_scenario_advances` 가 스펙 언어 수 × 설정 뷰포트 수(+1)로 이를 지킨다 |
| D-42-7 (MINOR) 운영자 시나리오 `"가나다"` 하드코딩 | **FIXED** | `09-admin.spec.mjs:137-139` 가 `todaysPuzzle` → `nearMiss(answer,"ko")`. 실측에서 mobile-390 의 09-admin 은 desktop streak 2회 뒤라 오늘 ko = **`어린왕자`(4글자)** 였고(manifest offset −2 = 어린왕자), 제출이 채점돼 `07-배정표-오늘과잔량`("교체 불가" 단정) 을 지나 `09-교체-배정확인` 까지 갔다 — 남은 실패는 D-42-4 soft 2건뿐. `test_no_spec_types_a_hardcoded_answer` 가 14곳의 `guess(` 호출을 전부 보고 리터럴 0건 |
| D-42-1 ~ D-42-4 (앱 결함) | 변동 없음(이 티켓 범위 아님) | 9건 재현 그대로. 수정 티켓 몫 — REPEAT 로 세지 않는다(라운드 1 §3 과 같은 기준) |

### 3. 체크박스 재점검 (라운드 1 에서 "부분 충족" 이었던 것만)

| 항목 | 라운드 2 | 근거 |
|---|---|---|
| 시나리오 4 연속 기록 ko·en | 충족 | 위 D-42-6. 7일 그리드는 웹에 없어 `/me/history` 대체(코디네이터 승인, 라운드 1 과 동일) |
| 시나리오 8 오프라인/서버 오류 ko·en | 충족 | 위 D-42-6 |
| 공용 스택 스크립트 소유(43·44 재사용) | 충족(단서 D-42-8) | Redis 번호가 티켓별로 갈리고 표 밖 티켓은 거부. 배정표 내용은 코디네이터 확인 필요 |
| 테스트 자원: DB·Redis 티켓별, 끝나면 정리 | 충족 | DB `…_e2e_t42`·Redis 4·포트 50xx/51xx. `down` 정리 실측 |

나머지 체크박스는 수정 커밋이 건드리지 않았고 라운드 1 판정이 그대로다(E2E 결과·산출물·셀렉터 규칙·외부
서비스 경계·금지 사항 재확인: push 없음, 시크릿 없음, 공유 파일 `.gitignore`·`README.md` 는 추가만).

### 4. 결함

### D-42-8 (MINOR) 배정표가 "pytest 번호까지 둔다" 고 하면서 티켓 43 의 pytest 번호(13)를 빼놓아, E2E 43 → 13 이 그 번호와 겹친다

- 파일: `scripts/e2e/env.sh:20-28,36`(`43) echo 13`), `tests/test_e2e_scripts.py:84`(`RESERVED_REDIS_DBS = {"0","1","5"}`),
  `README.md:191-193`, 증거 `review/impl-evidence-42.md:415-416`("티켓 43 의 스택이 실제로 떠 있는 것(`db13:keys=7`)").
- 사실(이 리뷰 중 직접 관찰, 2026-10-16 01:45 KST): 같은 머신에서 티켓 43 워커의 **pytest** 가
  `TEST_REDIS_URL=redis://127.0.0.1:6379/13` 로 돌고 있었다(`pgrep -fl pytest`, DB `chosung_daily_test_t43`).
  라운드 1 리뷰 D-42-5 본문도 "코디네이터가 pytest 용 번호를 … 손으로 배정(42→5, **43→13**)" 이라고 적었다.
  즉 13 은 티켓 43 의 pytest 번호인데, 수정은 그 13 을 **E2E 티켓 43** 에 배정했고 예약 집합에는 42 의 pytest(5)만 넣었다.
  증거가 `db13:keys=7` 을 "43 의 E2E 스택" 으로 읽은 것도 이 pytest 였을 가능성이 높다.
- 왜 문제인가: pytest 의 `app` 픽스처가 **테스트마다** `flushdb`(`tests/conftest.py:29`)를 한다. 티켓 43 이 pytest 전체
  판(13~15분)과 E2E 스택을 같은 시간에 띄우면(완료 조건이 둘 다다) 픽스처가 E2E 스택의 `puzzle:`/`lb:`/`stats:` 를
  지우고, 반대로 `down` 의 flushdb 가 pytest 의 Redis 를 지운다 — D-42-5 가 막으려던 것과 같은 모양이다.
  배정표가 스스로 "유일한 배정 기록 … pytest 번호까지 같은 표에 둔다 — flushdb 가 돌고 있는 남의 판을 지우지 않게"
  라고 선언하므로, 표에 43 의 pytest 13 이 빠진 것은 그 계약 위반이고 `test_every_ticket_gets_its_own_redis_db` 도 못 잡는다.
- MAJOR 가 아닌 이유: 이 티켓의 스택(Redis 4)은 0·1·5·13 어느 것과도 겹치지 않아 **이 티켓의 격리는 성립**한다.
  겹침은 티켓 43 쪽 자원이고 43 의 자체 스크립트(`t43-e2e-ios/scripts/e2e_ios.sh:30`, `E2E_REDIS_DB:-13`)가
  이미 같은 13 을 쓰고 있어 이 수정이 새로 만든 충돌은 아니다. 번호의 최종 주인은 코디네이터 배정이다.
- 고치는 방향(참고): 코디네이터가 "13 = 43 의 pytest" 를 확인하면 `env.sh` 표에 `13 pytest 티켓 43` 을 추가하고 E2E 43 을
  비는 번호로 옮기고(43 의 `e2e_ios.sh` 기본값도 같이), `RESERVED_REDIS_DBS` 에 13 을 넣는다. 티켓 43 이 `e2e_stack.sh` 로
  갈아타기 전(43 스크립트 NOTE)에 맞추면 된다.

### 5. 참고 (결함 아님)

- R-8 `test_no_spec_types_a_hardcoded_answer` 의 정규식 `guess\([^,]+,\s*["']` 은 `guess(page, "…")` 꼴만 잡는다.
  템플릿 리터럴(`` ` ``)이나 `const w = "가나다"; guess(page, w)` 는 통과한다. 지금 14곳은 전부 `answer`/`nearMiss`/
  `wrongGuesses` 에서 오므로 실해는 없다.
- R-9 `_lang_loop`·`test_pinned_words_cover_…` 도 소스 문자열 매칭이다(R-5 와 같은 성질). 실제 보장은 E2E 한 판이
  manifest 를 끝까지 소진하며 통과한 것으로 확인했다.
- R-10 증거 §1 표(`impl-evidence-42.md:26`)와 §8(`:381`)의 "`E2E_TICKET` 하나로 … Redis 번호 … 전부 갈린다" 는
  수정 후에도 남아 있다(구현자가 "수정 라운드 1" 절이 정확하다고 명시). 43·44 가 §1 만 읽으면 옛 문장을 본다 —
  한 줄 고치면 좋다.
- R-2(백업 코드 입력칸 24px)는 D-42-1 수정 뒤 재확인 대상 그대로. R-3(`words_en.csv`)·R-7 변동 없음.
- 수정 커밋의 `Co-Authored-By` 모델명은 이 리뷰 범위가 아니다.

### 6. 판정 근거 요약

라운드 1 의 MAJOR 1·MINOR 2 는 전부 FIXED 이고 직접 재현으로 확인했다. 요구 누락 없음(ko·en 범위 완결),
스펙과 다른 동작 없음, 검증 안 하는 테스트 없음(실패 9건은 실제 앱 결함), 보안·시크릿 없음, 범위 밖 변경 없음.
새 결함은 배정표 내용 1건(MINOR, 코디네이터 확인 사항).

BLOCKER 0 · MAJOR 0 · MINOR 1 (D-42-8) · REPEAT 0 — D-42-5·6·7 FIXED

판정: PASS
