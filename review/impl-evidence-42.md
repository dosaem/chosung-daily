# 티켓 42 증거 — 웹 E2E (Playwright, 실제 스택)

- 대상: 로컬 `main`(`d27417c`, 티켓 41 머지 포함) 위로 rebase 된 worktree
  `dosaem/t42-e2e-web` — 커밋 1개, clean 트리.
- 범위: **테스트와 스크립트만 추가했다.** `app/`·`web/`·`migrations/`·`mobile/` 의
  프로덕션 코드는 한 줄도 고치지 않았다(`git status` 가 그대로 보여준다 —
  바뀐 건 `.gitignore`·`README.md` 와 새 파일 `scripts/e2e*`·`tests/e2e/web/`).
- E2E 가 찾은 앱 결함 **4건**은 고치지 않고 §5 에 재현 단계·기대·실제·스크린샷
  경로로 적었다. 그 결함을 가리키는 테스트는 `@skip` 하지 않고 **계속 실패하게**
  뒀다(`expect.soft` + 결함 ID 주석).
- git push·NAS·배포·실제 결제·실제 OAuth·실제 푸시·하위 워커: 하지 않았다.

## 0. 한 줄 요약

mock 없이 실제 스택(gunicorn ×2 + MySQL + Redis + Celery worker/beat)을 전용 스키마로
띄우고 Playwright 로 **10개 시나리오 × ko/en × 데스크톱 1280·모바일 390 = 42개 테스트**를
사람이 누르는 순서대로 돌렸다 — **33개 통과, 9개 실패**이고 **실패 9개는 전부 아래 결함
4건을 가리키는 단정**이다(테스트 자체의 결함이 아니다). 접근성은 46회 axe 검사에서
위반 1종(D-42-2)만 나왔다.

## 1. 무엇을 만들었나

| 파일 | 역할 |
|---|---|
| `scripts/e2e_stack.sh` | **공용 스택**(티켓 43·44 가 재사용) — `up`·`seed`·`advance-day`·`status`·`down` |
| `scripts/e2e/env.sh` | DB 이름·Redis 번호·포트·관리자 계정을 한곳에서. `E2E_TICKET` 하나로 전부 갈린다 |
| `scripts/e2e/seed.py` | 단어 시드 + 오늘·내일·모레 퍼즐 **결정론 배정** + 운영자 계정 + manifest |
| `scripts/e2e/advance_day.py` | "하루 지났다" 를 데이터로 만든다(함수 `advance(days)` 로 43·44 재사용) |
| `scripts/e2e/guard_midnight.py` | KST 자정 ±10분 거부. `--now` 를 받아 pytest 가 같은 판정을 돌린다 |
| `scripts/e2e/words_en.csv` | en 전용 테스트 단어 12개 (E2E 전용, 출시 정답 풀과 무관) |
| `scripts/e2e_web.sh` | **한 번에 끝나는 명령**: down → up → seed → playwright → down |
| `tests/e2e/web/` | Playwright 프로젝트 (설정·공용 라이브러리 4개·시나리오 10개 파일) |
| `tests/test_e2e_scripts.py` | 위 스크립트들의 계약을 pytest 가 지킨다 (20개, §6) |
| `README.md` "E2E (웹 브라우저)" | 띄우기·실행·정리·소요 시간·자원·한계 |

실행:

```bash
scripts/e2e_web.sh                          # 전부
scripts/e2e_web.sh --project=desktop-1280   # 뷰포트 하나
E2E_KEEP=1 scripts/e2e_web.sh ...           # 스택 남기기
```

## 2. 실제 스택이라는 것 — 무엇이 진짜로 돌았나

- **Flask**: `uv run gunicorn -c gunicorn.conf.py -w 2 wsgi:app` 두 벌.
  포트 5042 는 스토어 링크가 **있는** 설정, 5142 는 **비어 있는** 설정이다 — 앱 설치
  배너·CTA 의 "설정 없으면 아예 안 그린다" 규칙은 한 프로세스로는 둘 중 하나만
  볼 수 있어서 인스턴스를 두 개 띄웠다.
- **MySQL**: 전용 스키마 `chosung_daily_e2e_t42` 를 새로 만들고 `flask db upgrade`
  (마이그레이션 11개 전부). `down` 이 drop 한다.
- **Redis**: DB **4**(개발 0, pytest 1 과 갈린다). 캐시·순위 ZSET·통계 해시·rate limit
  카운터가 전부 실제로 쓰인다. `down` 이 flushdb 한다.
- **Celery worker + beat**: 실제 기동(`worker.log` 에 `e2e-t42-marker-worker@… ready.`).
- **Gunicorn 접근 로그**(= 접속기록, 티켓 36)도 `e2e-artifacts/logs/access.log` 로 남는다.
- mock 서버·테스트 전용 엔드포인트·테스트 전용 DOM 속성: **하나도 없다.**

헬스체크 실측:

```
$ curl -s http://127.0.0.1:5042/health
{"apple_secret_expires_at": null, "db": "ok", "redis": "ok", "status": "ok"}
```

### 2.1 사람이 누르는 순서 — 셀렉터 규칙

- **누르는 것**은 전부 역할 + 보이는 이름이다: `getByRole("button", { name: t.submit })`,
  `getByPlaceholder(t.guess_placeholder)`, `getByRole("link", { name: t.footer_privacy })`.
  버튼 이름은 서버 사전(`app/utils/ui_strings.py`)에서 페이지에 심긴 실제 문구라,
  문구가 바뀌면 테스트가 같이 깨진다.
- **읽는 것** 중 역할이 없는 상태 영역(`#attempts-left`·`#board`·`#streak`·`#my-rank`)은
  id 로 집어 **내용을 단정**한다. `<p>`·`<div>` 라서 접근성 역할이 없고, 보이는
  텍스트로 찾으면 검증값 자체가 셀렉터가 되어 무엇을 보는지가 사라진다.
- `data-testid` 같은 테스트 전용 속성은 추가하지 않았다(앱 코드 무변경).
- 내부 상태 조작도 하지 않았다. 운영자 로그인조차 **백업 코드 복원 화면**을 통해 한다
  (§4 시나리오 10).

### 2.2 정답을 어떻게 아는가 — 시드 manifest

자정 배정(`flask schedule-puzzles`)은 단어 풀에서 **무작위로** 고른다. 그러면 브라우저
테스트가 정답을 타이핑할 수 없다. 그래서 시드가 오늘·내일·모레의 (날짜, 언어)별 단어를
못박고 `e2e-artifacts/seed-manifest.json` 하나로 넘긴다 — 테스트는 그 파일만 읽고
DB 를 훑지 않는다. 남은 27일은 평소 경로(`schedule_puzzles`)가 채워서 운영자 배정표·
잔량 화면이 실제 운영과 같은 모양이다.

```json
{ "today": "2026-10-15",
  "puzzles": [ { "date": "2026-10-15", "offset": 0, "language": "ko",
                 "answer": "컴퓨터", "hint": "코딩할 때 쓰는 기계", "length": 3 }, … ] }
```

오답도 **정답에서 만든다**(`nearMiss`·`wrongGuesses`). 적어둔 오답은 시드 단어가 바뀌거나
하루를 넘겨 다음 단어가 오늘이 되면 길이가 어긋나고, 그러면 서버가 길이 검증으로 막아
채점 자체를 안 한다 — "오답 5회" 가 조용히 "제출 실패 5회" 가 된다.

단어 출처는 `data/seed_words.csv`(ko, 20개)와 `scripts/e2e/words_en.csv`(en, 12개)뿐이다.
`data/word-candidates/` 는 **읽지 않는다** — 실제 출시 정답이 테스트 로그·스크린샷으로
샌다. en 용 CSV 를 새로 만든 이유는 `data/seed_words.csv` 에 `language` 열이 없어서
20개가 전부 ko 이고, en 퍼즐을 배정할 단어가 레포에 없었기 때문이다(코디네이터 승인).

### 2.3 시간 — 주입형 시계를 **넣지 않은** 이유와 그 대가

`datetime.now(KST)` 가 서비스 8곳에 흩어져 있다(`puzzle_service`·`puzzle_schedule_service`
×3·`puzzle_maintenance_service`·`account_deletion_service`·`stats_service`·`admin.py`).
주입형 시계를 넣으려면 프로덕션 코드에 테스트 전용 경로를 만들어야 해서, **앱 코드 무변경**
쪽을 골랐다(코디네이터 결정 2026-10-15, 선택지 A).

대신 하루를 넘길 때 **저장된 날짜를 하루 되돌린다**(`scripts/e2e/advance_day.py`):

| 되돌리는 것 | 왜 |
|---|---|
| `daily_puzzle.puzzle_date` | 어제 푼 퍼즐이 어제가 되고 내일 퍼즐이 오늘이 된다. 시도 이력(`/me/history`)·배정표가 전부 이 컬럼에서 날짜를 읽는다 (`attempt` 에는 날짜가 없다) |
| `guest_stats.last_solved_date` | 연속 기록 판정이 `today - 1` 과 비교하는 값 |
| `daily_stats.puzzle_date` | Beat 가 만든 하루치 분포 스냅샷 |
| Redis `lb:<날짜>:<언어>` · `stats:…` | 키 이름에 날짜가 박혀 있다. 순위는 Redis 에만 있어서 지우지 않고 rename 한다 |
| Redis `puzzle:…` · `ratelimit:guess:*` | 캐시·분당 카운터라 옮기지 않고 지운다 |
| `e2e-artifacts/seed-manifest.json` | "어느 날짜에 어느 정답" 의 기록. DB 를 옮겼으면 같이 옮겨야 테스트가 지금 퍼즐의 정답을 찾는다 |

**대가 두 가지 — 숨기지 않고 적는다.**

1. **달력 날짜는 움직이지 않는다.** 서버가 벽시계로 "오늘" 을 계산하므로, 하루를 넘겨도
   화면의 날짜(`#date`)는 그대로 실제 오늘이고 **배정된 단어만** 다음 것으로 바뀐다.
   연속 기록 판정은 `puzzle_date` 와 `last_solved_date` 의 **차이**만 보기 때문에
   (`guess_service._record_solve`) 진짜 코드 경로는 그대로 돈다 — 2일차에
   `last_solved_date == today - 1` 이 되어 `current_streak` 이 1 → 2 로 올라간다.
   그래서 시나리오 4 는 `day2.date === day1.date` 를 단정한다(이 방식의 당연한 결과다).
2. **클라이언트 시계도 고정하지 않았다.** 서버가 실제 벽시계를 쓰는데 브라우저 `Date` 만
   옮기면 둘이 어긋나 거짓 실패가 난다. 대신 **KST 자정 ±10분이면 `up`/`seed` 가 거부**해서
   (`guard_midnight`) 실행 중에 "오늘" 이 바뀌는 경우를 막는다. 한 판이 ~1분 40초라
   이 가드로 충분하다.

### 2.4 외부 서비스에 닿지 않는 경계

| 외부 | 이 E2E 에서 | 실기기 체크리스트로 넘긴 것 |
|---|---|---|
| 결제(App Store / Play) | 웹에 결제 화면이 없어서 **아예 호출하지 않는다**. 스토어 설정값은 전부 비워 둬서, 혹시 호출되면 `STORE_UNAVAILABLE`(503)로 막힌다 | iOS StoreKit Configuration 왕복 — 티켓 43·44 범위 |
| OAuth 로그인 | **하지 않는다.** 계정 이동은 백업 코드 복원으로, 계정 해제는 삭제 흐름으로 대신한다. 운영자 로그인도 "계정이 이미 연결된 게스트" 의 백업 코드 복원이다 | 실제 구글·애플 왕복 (`docs/RELEASE.md`) |
| 푸시 | 서버 푸시가 없는 설계다(기기 로컬 알림) — 보낼 것이 없다 | — |
| Slack 운영자 알림 | `SLACK_WEBHOOK_URL=""` → `app/clients/slack.py` 가 전송을 건너뛴다 | — |
| 광고 | 웹에 광고 슬롯이 없다 | Google 테스트 광고 유닛 — 앱 E2E |
| 스토어 링크 | 형식만 맞는 가짜 URL(`apps.apple.com/app/id6700000042`). href 만 확인하고 누르지 않는다 | — |

## 3. 실행 출력 (실측)

```
$ scripts/e2e_web.sh --reporter=line
[e2e-stack] 프로세스 종료 … DB chosung_daily_e2e_t42 drop … Redis DB 4 flush
[e2e-stack] DB chosung_daily_e2e_t42 준비 (없으면 생성, 권한 부여)
[e2e-stack] flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade  -> 19c8c4591377, add word, daily_puzzle, …
…(마이그레이션 11개)…
[e2e-stack] app 기동 (pid …)   / app-nostore 기동 / worker 기동 / beat 기동
[e2e-stack] 포트 5042 /health 응답 확인
[e2e-stack] 포트 5142 /health 응답 확인
[e2e-stack] 단어·퍼즐·운영자 계정 시드
단어 시드: ko 20개 추가, en 12개 추가
퍼즐 배정: 못박음 6건, 자동 배정 {'ko': 27, 'en': 27}
운영자 게스트: id=1 email=e2e-admin@example.com
[e2e-web] playwright test --reporter=line

  9 failed
    [desktop-1280] › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → 다른 브라우저에서 복원 → 같은 기록 (ko)
    [desktop-1280] › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → 다른 브라우저에서 복원 → 같은 기록 (en)
    [desktop-1280] › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (ko)
    [desktop-1280] › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (en)
    [mobile-390]   › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → 다른 브라우저에서 복원 → 같은 기록 (ko)
    [mobile-390]   › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → 다른 브라우저에서 복원 → 같은 기록 (en)
    [mobile-390]   › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (ko)
    [mobile-390]   › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (en)
    [mobile-390]   › specs/09-admin.spec.mjs › [10] 운영자: 로그인 → CSV 업로드 → 배정표 확인 → 단어 교체
  33 passed (1.4m)
[e2e-stack] app-nostore 종료 … DB drop … Redis flush … down 완료
```

실패 9개의 단정 메시지를 모으면 **결함 4건뿐**이다:

```
   4     Error: D-42-1: 복사 버튼 라벨이 Jinja dict.copy 메서드로 렌더된다
   4     Error: D-42-2 이 고쳐졌다면 이 known 항목을 지워라   (axe label @ #token-display)
   4     Error: D-42-3: 삭제 완료 안내가 restart() 에 지워진다
   1     Error: D-42-4: 390px 뷰포트에서 배정표가 가로로 넘친다 (문서 504px)
   1     Error: D-42-4: 390px 에서 교체/배정 링크를 탭할 수 없다
```

**소요 시간**: 스택 기동 ~25초 · 시드 ~5초 · 브라우저 42개 테스트 1분~2분 30초 ·
정리 ~5초 = **2~3분**(실측 1.1분 / 1.4분 / 2.2분 / 2.5분 — 머신 부하에 따라 벌어진다).

**날짜가 바뀌어도, 여러 번 돌려도 같다**: KST 자정을 넘긴 뒤(2026-10-16 00:15·00:36)
다시 돌려 시드가 새 "오늘" 로 다시 못박고 같은 결과(33 통과 / 9 실패, 결함 4건)가
나오는 것을 확인했다 — 전날 데이터가 남아 있어도 `down` 이 DB 를 지우고 시작한다.
`advance-day` 도 매번 같은 일을 한다(실측: DB 76~93행 시프트 · Redis 4~8키 rename ·
23~24키 삭제 · manifest 6건 시프트).

## 4. 시나리오별 결과

파일 번호는 **실행 순서**, `[n]` 은 브리프의 시나리오 번호다. 시나리오 4(연속 기록)가
저장된 날짜를 하루 되돌리므로 그 파일이 마지막(10)이다.

| 파일 | 브리프 | 무엇을 확인했나 | 결과 |
|---|---|---|---|
| `01-first-visit` | [1] | 게스트 발급 → 가림 타일·글자 수·남은 기회 → 오답 1회(기회 4, 피드백 타일이 맞은/틀린 자리 섞임) → 정답 → 결과 문구 → 순위 섹션의 내 순위(`#1 · 2회 · 22:26:40`)·시도 분포 → 공유 텍스트 클립보드 복사. **정답이 화면·공유 텍스트에 평문으로 없는 것**까지 | 통과 (ko/en × 2뷰포트) |
| `02-fail` | [2] | 오답 5회 → 기회 0 → 실패 결과에 정답 공개 → 제출 폼 사라짐(6번째 불가) → 보드 5행 | 통과 |
| `03-leaderboard` | [3] | 브라우저 2개를 더 열어 **실제로 풀게** 해서(1회·3회) 순위표를 만든 뒤: 모든 행이 `게스트 #xxxx`/`Guest #xxxx` + 16진수 4자리, `@` 없음 · en 복수형 `1 try`/`3 tries` · 정렬(적은 시도 → 빠른 시간) · 내 행이 딱 하나이고 `font-weight` 가 실제로 굵다 · 분포 5줄 | 통과 |
| `04-backup-restore` | [5] | 풀고 백업 코드 복사 → **빈 다른 브라우저**에서 복원 → 같은 보드·같은 결과·같은 연속 기록·순위표의 내 행 | **실패 — D-42-1, D-42-2** (흐름 자체는 끝까지 통과) |
| `05-language-switch` | [6] | ko UI 로 en 퍼즐 풀기(두 언어가 독립) → 순위 접두사가 ko → `?lang=en` 으로 UI 만 전환(`Content-Language: en`, `html[lang]`, 칩 라벨 `Korean`) → 퍼즐 언어 선호는 서버가 들고 있어 그대로 → 순위 접두사가 `Guest #` 로 → 칩으로 ko 로 돌아오면 보던 문제 복귀 | 통과 |
| `06-account-delete` | [7] | 푸터 "계정 삭제" → 확인 페이지 → **GET 만으로는 안 지워진다**(옛 토큰 `me/stats` 200) → 확인 버튼 → 새 게스트(빈 보드·새 토큰) → 옛 토큰 401 | **실패 — D-42-3** (삭제·새 게스트·401 은 통과) |
| `07-offline` | [8] | 오프라인 배너(`role=status`) + **입력·제출 비활성** → 연결 복구 시 재시도 버튼 없이 자동 재조회 | 통과 |
| `07-server-error` | [8] | `/puzzles/today` 만 500 → 인라인 상태 카드(토스트 아님) + 오프라인 배너는 안 뜸 → 재시도 버튼으로 복구 | 통과 |
| `08-cta` | [9] | 스토어 링크 **있는** 앱: `apple-itunes-app` 메타 + 결과 안에만 CTA + 두 배지 href | 통과 |
| `08-cta-nostore` | [9] | 스토어 링크 **없는** 앱(포트 5142): 메타 태그 0개 · `.app-cta` 0개 · 배지 0개(안내 문구까지 통째로 없음) | 통과 |
| `08-legal` | [9] | 푸터 링크의 `?lang=` 유지 → `/privacy`·`/terms` 가 UI 언어로 열리고 h1·연락처 표시 | 통과 |
| `09-admin` | [10] | 비로그인 `/admin` → 홈 + 안내(403 아님) → 백업 코드 복원으로 운영자 → 단어 목록 → CSV 업로드(새 2 · 중복 1 · 카테고리 오류 1 → 행별 결과 표의 줄 번호·사유) → 목록 검색으로 찾기 → 배정표(오늘은 시드 단어 + "시도 1건 (교체 불가)", 잔량 카드 2개) → 먼 날짜 단어 교체 → 배정 확인 | 데스크톱 통과 / **모바일 실패 — D-42-4** |
| `10-streak` | [4] | 1일차 정답 → `연속 1일 · 최고 1일 · 누적 1문제` → `advance-day` → 재방문 시 **다음 단어**가 오늘(어제 보드는 어제에 남고 빈 보드) → 연속은 아직 1 → 정답 → **`연속 2일 · 최고 2일 · 누적 2문제`** → `GET /me/history?days=7` 이 7일, 마지막 두 칸이 `success`, 그 앞은 `none` | 통과 |

### 4.0 대표 이미지 (실행하면 같은 자리에 다시 생긴다)

시나리오마다 단계별 PNG + `steps.log` + `axe-*.json` 이 같은 폴더에 있다
(이번 판: 132장 · 46개 axe 결과 · 총 284파일 / 67MB). 먼저 볼 것:

| 무엇 | 경로 (`e2e-artifacts/web/` 아래) |
|---|---|
| 첫 방문 → 정답 → 결과 | `01-first-visit-ko/desktop-1280/03-정답-결과.png` |
| 피드백 타일(맞은/틀린 자리) | `01-first-visit-ko/desktop-1280/02-오답1회-피드백타일.png` |
| 공유 텍스트 (단계 로그에 전문) | `01-first-visit-ko/desktop-1280/steps.log` |
| 실패 결과·정답 공개 | `02-fail-en/desktop-1280/02-실패결과-정답공개.png` |
| 순위표 `Guest #` · `1 try`/`3 tries` · 내 행 강조 | `03-leaderboard-en/desktop-1280/01-순위표.png` |
| 다른 브라우저에서 복원된 같은 기록 | `04-backup-restore-ko/desktop-1280/03-B-복원-같은기록.png` |
| ko UI 로 en 퍼즐 · `?lang=en` 전환 | `05-language-switch/desktop-1280/02-koUI-en퍼즐.png` · `…/04-enUI-en퍼즐.png` |
| 오프라인 배너 + 입력 잠김 | `07-offline/desktop-1280/02-오프라인-입력잠김.png` |
| 서버 오류 인라인 카드 | `07-server-error/desktop-1280/01-서버오류-인라인카드.png` |
| 앱 CTA 배지 2개 / 설정 없을 때 없음 | `08-cta-ko/desktop-1280/01-CTA-배지2개.png` · `08-cta-nostore-ko/desktop-1280/01-CTA없음.png` |
| 운영자 CSV 행별 결과 · 배정표 | `09-admin/desktop-1280/05-CSV-행별결과.png` · `…/07-배정표-오늘과잔량.png` |
| 모바일 390 에서 streak 2 | `10-streak/mobile-390/03-2일차-정답-streak2.png` |

### 4.1 브리프의 "7일 그리드" — 웹 범위 밖

`web/templates/index.html` 의 주석대로 7일 그리드는 **앱 화면(S4)의 몫**이다(티켓 27).
웹 "내 기록" 섹션에는 계정 연결과 백업 코드만 있다. 코디네이터 승인에 따라 결함으로
올리지 않고, 연속 기록 배지 + 그리드의 **원천 데이터**인 `GET /me/history?days=7`
응답으로 대체 검증했다(시나리오 10). 단계 로그에도 같은 문장을 남겼다.

### 4.2 접근성 (axe)

WCAG 2.1 A/AA 태그로 **46회** 검사했다(홈·순위·실패 결과·내 기록·오프라인·서버 오류·
결과+CTA·개인정보·약관·삭제 확인·운영자 목록·CSV 업로드·배정표 × 뷰포트·언어).
위반은 **1종뿐**이다 — D-42-2(`#token-display` 라벨 없음). 나머지 45회는 0건.

결과는 시나리오마다 `axe-*.json` 으로 남는다. 이미 기록한 결함은 `expectAxeClean(…, known)`
의 `known` 에 두어 **soft** 로 실패하고(결함이 가려지지 않는다), 기록에 없는 새 위반은
그 자리에서 hard 로 끊는다. 결함이 고쳐지면 `known` 항목을 지우라는 단정도 같이 있다.

## 5. 발견한 결함

고치지 않았다. 재현 단계·기대·실제·증거 경로 순이다. 스크린샷 경로는 모두
`e2e-artifacts/` 아래이고 gitignore 다(실행하면 같은 자리에 다시 생긴다).

### D-42-1 (MAJOR) 백업 코드 "복사" 버튼 라벨이 파이썬 객체 문자열로 나온다

- 재현: `/` → "내 기록" → "내 기록 백업". ko·en 둘 다. 브라우저 무관(서버 렌더다).
- 기대: 버튼 라벨이 `복사` / `Copy`.
- 실제: `<built-in method copy of dict object at 0x10cc43fc0>`.
- 원인: `web/templates/index.html:175` 의 `{{ t.copy }}`. Jinja 의 속성 접근은
  `getattr` 를 먼저 보고, `t` 는 파이썬 `dict` 라서 **`dict.copy` 메서드**가 잡힌다.
  사전 키 `"copy"` 는 보지 못한다. `{{ t["copy"] }}` 또는 키 이름 변경이 필요하다.
  (JS 쪽은 `#ui-strings` JSON 에서 읽어서 영향이 없다 — 그래서 서버 렌더 한 자리만 깨진다.)
- 템플릿 전수 확인: `dict` 와 이름이 겹치는 접근은 이 한 곳뿐이다
  (`copy|keys|values|items|get|pop|clear|update|setdefault` 전부 grep).
  `pagination.items`(운영자 목록·교체 폼)는 SQLAlchemy `Pagination.items` 라 정상이다.
- 왜 지금까지 안 잡혔나: `tests/test_ui_strings.py` 는 **사전**을 보고
  `tests/test_web.py` 는 번들 문자열을 본다 — 렌더된 HTML 의 그 버튼을 보는 테스트가 없다.
- 증거: `e2e-artifacts/web/04-backup-restore-ko/desktop-1280/01-A-백업코드-복사.png`,
  그리고 실패한 테스트의 접근성 트리 덤프
  (`e2e-artifacts/web/test-output/04-backup-restore…/error-context.md` 의
  `button "<built-in method copy of dict object at …>"`).
- 실패하는 단정: `tests/e2e/web/specs/04-backup-restore.spec.mjs` (D-42-1 주석).

### D-42-2 (MINOR, 접근성 critical) 백업 코드 입력칸에 라벨이 없다

- 재현: 같은 화면. axe `label` 규칙 (impact: critical), 대상 `#token-display`.
- 기대: 읽기 전용이라도 그 칸이 무엇인지 스크린리더가 읽을 수 있어야 한다.
- 실제: `<input id="token-display" type="text" readonly />` — `label`·`aria-label`·
  `aria-labelledby`·`title`·`placeholder` 가 전부 없다. 바로 아래 복원 입력칸
  (`#token-input`)은 `placeholder` 가 있어서 걸리지 않는다.
- 증거: `e2e-artifacts/web/04-backup-restore-ko/desktop-1280/axe-records.json`.
- 실패하는 단정: 같은 파일의 `expectAxeClean(…, [{ id: "label", target: "#token-display" }])`.

### D-42-3 (MAJOR) 계정 삭제 완료 안내가 한 번도 보이지 않는다

- 재현: 기록을 만든 뒤 푸터 "계정 삭제" → 확인 버튼 → `/?deleted=1` 로 돌아온 홈.
- 기대: `계정과 기록을 삭제했어요. 새 기록으로 다시 시작합니다.`
  (`account_deleted`)가 보인다 — 되돌릴 수 없는 작업의 유일한 확인이다.
- 실제: `#message` 가 빈 문자열이다(10초 동안 14번 확인). 토큰 폐기·새 게스트 발급은
  정상이라 **기능은 됐는데 사용자는 됐다는 걸 모른다**.
- 원인: `web/static/app.js` `init()` 의 순서 —
  `discardDeletedAccountState()` 가 `showMessage(t("account_deleted"))` 로 적은 직후
  `restart()` → `discardLocalPlayState()` → `showMessage("")` 가 지운다.
- 증거: `e2e-artifacts/web/06-account-delete-ko/desktop-1280/03-삭제후-새게스트.png`,
  `.../steps.log`.
- 실패하는 단정: `tests/e2e/web/specs/06-account-delete.spec.mjs` (D-42-3 주석).

### D-42-4 (MINOR) 390px 폭에서 운영자 배정표의 교체 링크를 누를 수 없다

- 재현: 390×844(모바일 에뮬레이션)로 `/admin/schedule?language=ko` → 표의 마지막 행
  "관리" 열의 `교체`/`배정` 링크를 탭.
- 기대: 탭하면 교체 폼으로 간다.
- 실제: 문서 폭이 **504px**(뷰포트 390px)로 넘쳐 가로 스크롤이 생기고, 링크를 가운데로
  밀어도 다른 행의 칸(`td.admin-cell-answer`, 옆 행의 `a.admin-link`)이 그 자리의 포인터
  이벤트를 가로챈다 — Playwright 의 trial 클릭이 3초 안에 성립하지 않는다.
  데스크톱 1280 에서는 정상이다.
- 맥락: 운영자 화면 폭이 디자인 시스템 §10 을 의도적으로 벗어난다는 결정이 있다
  (README "15. 운영자 화면의 폭은 디자인 시스템 §10 을 벗어난다"). 그 결정의 결과가
  폰에서 "누를 수 없는 버튼" 이라서 결함으로 적는다 — 고칠지(표를 가로 스크롤 컨테이너로
  감싸기 등) 그냥 둘지는 코디네이터 판단이다. 운영은 데스크톱이라 MINOR 로 본다.
- 증거: `e2e-artifacts/web/09-admin/mobile-390/steps.log`
  (`배정표 폭: 문서 504px · 표 … · 뷰포트 390px`, `D-42-4 링크를 가로채는 요소: …`),
  `e2e-artifacts/web/09-admin/mobile-390/07-배정표-오늘과잔량.png`.
- 실패하는 단정: `tests/e2e/web/specs/09-admin.spec.mjs` (D-42-4 주석 2개 —
  넘침 자체와 탭 가능 여부). 나머지 흐름은 주소로 들어가 끝까지 검증한다.

## 6. 전체 검증 (실제 출력)

```
$ uv run ruff check .
All checks passed!

$ uv run pytest -q
   (TEST_DATABASE_URL=…/chosung_daily_test_t42, TEST_REDIS_URL=…/5)
........................................................................ [ 95%]
.....................................................................    [100%]
1713 passed in 916.73s (0:15:16)

$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 2.5s)          ← exit 0 (info 포함)

$ cd mobile && flutter test
00:38 +796: All tests passed!            ← exit 0
```

전부 **rebase 된 최종 트리**(티켓 41 머지 포함)에서 돌렸다.
`pytest` 1713개는 이 티켓이 추가한 `tests/test_e2e_scripts.py` **20개**를 포함한 수다
(그 파일을 빼면 1693개). 그 20개가 보는 것:

- 스크립트 3개가 `bash -n` 을 통과하고 실행 권한이 있다
- `E2E_TICKET` 하나만 바꾸면 DB 이름·포트가 전부 갈린다(43·44 가 42 의 DB 를 drop 하지
  않는다), Redis 번호가 개발(0)·pytest(1)와 안 겹친다, 운영자 이메일이 실제 계정이 아니다
- **자정 가드가 실제로 동작한다**: `scripts/e2e/guard_midnight.py --now` 로 23:55·00:05 는
  거부, 23:45·12:00 은 통과. 판정 사본을 테스트에 적지 않으려고 가드를 파일로 뺐다
  (레포 관례 — `tests/test_store_screenshot_script.py` 의 "함수 사본을 두지 않는다")
- `e2e_web.sh` 가 down → up → seed → test 순서다(시나리오 10·4 가 빈 DB 를 전제한다)
- `seed.py` 의 `PINNED` 가 시드 CSV 에 실제로 있는 단어이고 날짜마다 다르다
- `words_en.csv` 가 운영자 업로드와 같은 규칙(`parse_word_input`)을 통과하고 전부 en 이다
- `advance_day` 가 세 테이블 + Redis 키 두 종류를 빠뜨리지 않는다. 겹침 처리까지 본다:
  SQL 은 `ORDER BY puzzle_date ASC`(유니크 키), Redis 는 오래된 날짜부터 rename
  (`RENAME` 은 대상 키를 조용히 덮어써서, 두 번 넘기면 어제 순위표가 사라진다)
- 산출물이 gitignore 다, README 에 실행법이 있다, Playwright 가 두 뷰포트 × 직렬 ×
  재시도 0 이다

## 7. 테스트 자원 정리

- MySQL: `chosung_daily_e2e_t42` 는 `down` 이 drop 한다(마지막 실행 뒤 남아 있지 않다).
  pytest 는 다른 워커와 겹치지 않게 `chosung_daily_test_t42`(+`_migrations`)로 돌렸고,
  이 두 개는 **남겨 뒀다** — 레포의 다른 티켓 DB(`chosung_daily_test_t01`…`_t43`)와 같은
  관례이고, 리뷰어가 pytest 를 다시 돌릴 때 다시 만들 필요가 없다.
- Redis: E2E 는 DB 4, 이 티켓의 pytest 는 DB 5 — 개발(0)·공용 pytest(1)와 안 겹친다.
  `down` 이 flushdb 한다.
- 프로세스: `down` 이 pid 파일로 종료하고, 남은 자식은 argv 표식(`e2e-t42-marker`)으로
  거둔다. 실행 후 `scripts/e2e_stack.sh status` 로 확인했다.
- 산출물: `e2e-artifacts/`(67MB, 284파일)와 `tests/e2e/web/node_modules/` 는 gitignore 다.
  Chromium 은 `~/Library/Caches/ms-playwright`(~90MB, 레포 밖)에 있다.
- 디스크: 작업 전후 여유 60GB대 유지(요구 ~13GB 이상). Chromium 89.7MB 는
  `~/Library/Caches/ms-playwright` 로 레포 밖이다.

## 8. 남은 것 / 다음 티켓에 넘기는 것

- **결함 4건의 수정 티켓**: D-42-1·D-42-3 은 한 줄 수정이고 둘 다 사용자에게 바로 보이는
  자리다. D-42-2 는 라벨 추가, D-42-4 는 운영자 표의 반응형 결정이 필요하다.
- **회귀 방지**: D-42-1 같은 "렌더된 HTML" 결함은 pytest 에 템플릿 렌더 단정 하나로도
  잡힌다(`t.copy` 가 들어간 버튼의 텍스트). 어느 쪽 테스트에 둘지는 수정 티켓에서 정할 일이다.
- **티켓 43·44**: `scripts/e2e_stack.sh` 와 `scripts/e2e/advance_day.py` 의 `advance(days)`
  를 그대로 쓰면 된다. `E2E_TICKET=43` 으로 DB 이름·Redis 번호·포트가 전부 갈린다.
- **실기기로 넘긴 것**: 실제 구글·애플 OAuth 왕복, 실제 결제, iOS Safari 실기기 레이아웃
  (이 티켓의 모바일은 Chromium 390 에뮬레이션이다 — `devices["iPhone 13"]` 프리셋은
  WebKit 을 끌고 와서 브라우저 한 벌을 더 받아야 하고, 이 티켓이 보는 건 폭이다).

---

## 수정 라운드 1

리뷰 라운드 1(`review/impl-review-42.md`) 판정 FAIL — MAJOR 1건(D-42-5)·MINOR 2건
(D-42-6·D-42-7). 세 건 모두 **리뷰 재현대로 먼저 재현 → 실패하는 테스트로 고정 → 원인
수정** 순서로 처리했다. 리뷰가 "참고" 로 남긴 R-4·R-6 도 한 줄짜리라 같이 고쳤다.
앱 결함 D-42-1~4 는 이 티켓이 고치지 않는다(수정 티켓 몫) — 여전히 9건이 실패한다.

### D-42-5 (MAJOR) — Redis DB 번호가 티켓별로 갈리지 않았다

**원인.** `scripts/e2e/env.sh` 가 `E2E_REDIS_DB="${E2E_REDIS_DB:-4}"` 로 **한 숫자를
기본값**으로 박아 뒀다. DB 이름(`chosung_daily_e2e_t${E2E_TICKET}`)과 포트(`50${…}`)는
티켓 번호에서 **만들어지는데** Redis 번호만 상수였다. Redis 키에는 스키마 구분이 없어서
43·44 가 같은 머신에서 같이 뜨면 `puzzle:` 캐시가 남의 스키마의 퍼즐 id 를 내보내고,
`lb:`·`stats:` 는 두 스택 기록이 섞이고, 한쪽의 `down`(flushdb)이 상대의 실행 중 상태를
지운다. 문서 세 곳("`E2E_TICKET` 하나로 전부 갈린다")이 반대로 적혀 있어 43·44 가 기본값을
믿고 쓸 수 있었다.

**재현(수정 전).**

```
$ for t in 42 43 44 99; do E2E_TICKET=$t bash -c 'source scripts/e2e/env.sh; echo "t='$t' $E2E_DB $(e2e_redis_url) $E2E_PORT"'; done
t=42 chosung_daily_e2e_t42 redis://127.0.0.1:6379/4 5042
t=43 chosung_daily_e2e_t43 redis://127.0.0.1:6379/4 5043
t=44 chosung_daily_e2e_t44 redis://127.0.0.1:6379/4 5044
t=99 chosung_daily_e2e_t99 redis://127.0.0.1:6379/4 5099
```

DB·포트는 갈리는데 Redis 는 넷 다 4 다. 같은 시각 `redis-cli info keyspace` 로 티켓 43 의
스택이 **실제로 떠 있는 것**(`db13:keys=7`)도 확인했다.

**실패하는 테스트로 고정.** `tests/test_e2e_scripts.py` 에 3개를 넣었고(+기존 1개 확장),
수정 전에 넷 다 빨갰다:

| 테스트 | 무엇을 막는가 |
|---|---|
| `test_resources_carry_the_ticket_number` | 기존 테스트에 `t42["redis_db"] != t43["redis_db"]` 추가 — 리뷰가 지적한 "DB·포트만 보고 Redis 를 빼놓은" 구멍 |
| `test_every_ticket_gets_its_own_redis_db` | 배정표 전체(42·43·44)가 **서로 다르고**, 예약 번호(0 개발 · 1 pytest 기본 · 5 pytest 티켓 42)를 피하고, 0–15 범위인지 |
| `test_unassigned_ticket_refuses_instead_of_sharing_a_redis_db` | 표에 없는 티켓이 기본값으로 떨어지지 않고 **거부**하는지. `E2E_REDIS_DB` 를 직접 주면 돌아가는지도 같이 |
| `test_redis_url_carries_the_assigned_db` | `e2e_redis_url`(앱이 보는 것)과 `E2E_REDIS_DB`(`down` 의 `redis-cli -n` 이 보는 것)가 어긋나지 않는지 |

**수정.** `scripts/e2e/env.sh` 에 **배정표 한 곳**을 만들었다 — 번호를 티켓에서 산술로
유도(`4 + (티켓 - 42)`)하지 않은 이유는 코디네이터가 이미 손으로 배정한 번호(티켓 43 의
E2E 13, 티켓 42 의 pytest 5)가 있어서 산술이 그 값과 어긋나기 때문이다. pytest 번호까지
같은 표에 적어 둬야 `down` 의 flushdb 가 돌고 있는 남의 판을 지우지 않는다.

```bash
e2e_redis_db_for_ticket() {
  case "$1" in
    42) echo 4 ;;
    43) echo 13 ;;
    44) echo 12 ;;
    *) return 1 ;;
  esac
}

if [ -z "${E2E_REDIS_DB:-}" ]; then
  E2E_REDIS_DB="$(e2e_redis_db_for_ticket "$E2E_TICKET")" || { …; return 1 2>/dev/null || exit 1; }
fi
```

표(주석)에 적힌 전체 배정: `0` 로컬 개발 · `1` pytest 기본(`TestingConfig`) ·
**`4` E2E 티켓 42** · `5` pytest 티켓 42 · `12` E2E 티켓 44 · `13` E2E 티켓 43.

**증명(수정 후).**

```
$ for t in 42 43 44; do E2E_TICKET=$t bash -c 'source scripts/e2e/env.sh; echo "t='$t' $E2E_DB $(e2e_redis_url) $E2E_PORT"'; done
t=42 chosung_daily_e2e_t42 redis://127.0.0.1:6379/4 5042
t=43 chosung_daily_e2e_t43 redis://127.0.0.1:6379/13 5043
t=44 chosung_daily_e2e_t44 redis://127.0.0.1:6379/12 5044

$ bash -c 'E2E_TICKET=99 source scripts/e2e/env.sh'; echo "exit=$?"
e2e/env.sh: 티켓 99 의 Redis DB 번호가 배정표에 없다 — 위 표(e2e_redis_db_for_ticket)에
  한 줄을 더하거나 E2E_REDIS_DB 를 직접 줘라.
exit=1

$ E2E_TICKET=99 bash scripts/e2e_stack.sh status      # set -euo pipefail 경로도 막힌다
e2e/env.sh: 티켓 99 의 Redis DB 번호가 배정표에 없다 — …
exit=1

$ E2E_TICKET=99 E2E_REDIS_DB=9 bash -c 'source scripts/e2e/env.sh; echo "$(e2e_redis_url)"'
redis://127.0.0.1:6379/9                              # 직접 주면 표 밖에서도 쓸 수 있다
```

문서도 같이 고쳤다: `scripts/e2e/env.sh` 머리말, `README.md` 의 "쓰는 자원" 항목(배정표
전문 + "표에 없는 티켓 번호로는 스택이 뜨지 않는다"). 리뷰가 지적한 증거 문서의 문장
("`E2E_TICKET` 하나로 전부 갈린다")은 §1 표에 그대로 두되 이 절이 정확한 동작이다 —
**DB 이름·포트는 번호에서 만들고, Redis 번호는 배정표에서 가져온다.**

### D-42-6 (MINOR) — 시나리오 4·8 이 ko 만 돌았다

**원인.** `10-streak.spec.mjs:22`·`07-offline.spec.mjs:22,59` 가 `openGame(browser,
{ lang: "ko" })` 로 고정이고 다른 시나리오가 쓰는 `for (const lang of ["ko","en"])` 가 없었다.
그래서 en 사전의 `offline_banner`·`puzzle_load_failed`·`retry` 문구와 en 퍼즐의 연속 기록
경로(`guess_service._record_solve` 가 언어 무관인지 — 스펙 US 14)를 아무도 보지 않았다.

**재현(수정 전).** `scripts/e2e_web.sh specs/10-streak.spec.mjs` → 테스트 1개 × 2뷰포트 = 2개.
전체 한 판은 42개.

**실패하는 테스트로 고정.** `test_scenario_runs_in_both_languages` — ko·en 둘 다 돌아야 하는
스펙 8개를 파라미터로 돌려 `for (const lang of ["ko", "en"])` 를 확인한다. 수정 전
`07-offline`·`10-streak` 2건이 빨갰다(운영자 화면은 ko 전용이라 `09-admin` 은 제외,
`05-language-switch` 는 한 테스트가 두 언어를 함께 본다).

**수정 ①** 두 스펙을 언어 루프로 감쌌다. 산출물 폴더·axe json 이름도 언어별로 갈랐다
(`07-offline-ko` / `07-offline-en` / `07-server-error-{lang}`, `10-streak-{lang}`).
streak 의 `/me/history` 단정은 칸이 언어별이라 `results.ko` → `results[lang]` 로 바꿨다.

**수정 ②(같은 결함의 숨은 절반).** 연속 기록 시나리오는 **한 판마다 하루를 넘긴다**
(`stack("advance-day")`). 언어를 추가하면 한 판에 넘기는 횟수가 2번 → 4번
(ko·en 2개 * 뷰포트 2개)이 된다. k 번째 판은 `PINNED[k-1]`(1일차)과 `PINNED[k]`(2일차)를
쓰고 날짜 시프트는 **언어를 가리지 않으므로**, 언어마다 못박은 날이 5개여야 한다.
3개로 두면 마지막 판이 "manifest 에 오늘 퍼즐이 없다" 로 깨진다. `scripts/e2e/seed.py` 의
`PINNED` 를 5개로 늘렸고, 그 산수를
`test_pinned_words_cover_every_day_the_streak_scenario_advances` 가 **스펙의 언어 수 ×
설정의 뷰포트 수**를 읽어 계산해 지킨다(언어나 뷰포트를 더하면 테스트가 먼저 깨진다).

```python
PINNED = {
    PuzzleLanguage.KO: ("컴퓨터", "자전거", "어린왕자", "냉장고", "지하철"),
    PuzzleLanguage.EN: ("apple", "school", "coffee", "window", "bicycle"),
}
```

**증명.** 전체 한 판이 42개 → **48개**(+6: offline 2 · server-error 2 · streak 2)로 늘고,
새로 추가된 6개 전부 통과. 실패는 그대로 9건(앱 결함 D-42-1~4)이다. 출력은 아래 §"재검증".
en 쪽이 실제로 돈 증거: `e2e-artifacts/web/07-offline-en/*/steps.log`,
`10-streak-en/*/steps.log`(`advance-day: 1일 전진: DB 60행 시프트 …`).

### D-42-7 (MINOR) — 운영자 시나리오의 플레이어 제출이 `"가나다"` 로 고정

**원인.** `09-admin.spec.mjs:132` 이 제출 문자열을 적어 뒀다. 서버는 길이가 다른 제출을
채점하지 않고 `VALIDATION_ERROR` 로 막으므로(그래서 같은 파일이 `wrongGuesses(answer, …)`
를 두고 있다), 시드가 못박은 ko 단어가 3글자가 아니게 되는 순간 시도가 **아예 생기지 않고**
`guess()` 의 보드 행 단정이 먼저 터져 "시도가 있는 날짜는 교체 불가" 검증까지 못 간다.

**재현.** 리뷰는 사고 실험으로 남겼지만, D-42-6 을 고치며 `PINNED` 를 늘리는 자리였으므로
**ko 에 4글자(`어린왕자`)를 실제로 섞어** 재현했다 — 뷰포트 2개가 같은 스택을 쓰고
desktop 판의 streak 가 하루를 2번 넘기므로, `어린왕자` 는 **mobile-390 판의 "오늘"** 이 된다.

```
$ bash scripts/e2e_stack.sh down; up; seed; advance-day; advance-day
오늘 배정: [('ko', '어린왕자'), ('en', 'coffee')]

$ npx playwright test specs/09-admin.spec.mjs --project=mobile-390     # 하드코딩 상태
  Error: expect(locator).toHaveCount(expected) failed
    Expected: 1 / Received: 0
    waiting for locator('#board .tile-row')  — 14 × locator resolved to 0 elements
      at lib/game.mjs:141  (guess → 09-admin.spec.mjs:138)
  1 failed
```

보드 행이 생기지 않아 `guess()` 에서 멈췄다 — 리뷰의 예측과 정확히 같다.

**실패하는 테스트로 고정.** `test_no_spec_types_a_hardcoded_answer` — 모든 스펙 파일에서
`guess(<무엇>, "<리터럴>")` 꼴을 금지한다. 수정 전 `09-admin.spec.mjs` 만 빨갰다.

**수정.** 오늘 정답에서 만든다. 맞히면 안 되고(시도만 필요하다) 길이는 같아야 하므로
`nearMiss` 를 쓴다 — 같은 파일의 라이브러리가 바로 이 용도로 있던 것이다.

```js
const player = await openGame(browser, { lang: "ko" });
const playerPuzzle = await todaysPuzzle(player.page, "ko");
await guess(player.page, nearMiss(playerPuzzle.answer, "ko"));
```

**증명.** 같은 상태(오늘 ko = `어린왕자`, 깨끗한 DB, 하루 2번 넘김)에서 다시 돌리면 제출이
채점되고 시나리오가 끝까지 간다 — 남은 실패는 **D-42-4 soft 2건뿐**이다(앱 결함).

```
$ npx playwright test specs/09-admin.spec.mjs --project=mobile-390     # 수정 후
  Error: D-42-4: 390px 뷰포트에서 배정표가 가로로 넘친다 (문서 497px)
  Error: D-42-4: 390px 에서 교체/배정 링크를 탭할 수 없다
  1 failed          ← 두 soft 단정만. guess 는 통과했다.

$ cat e2e-artifacts/web/09-admin/mobile-390/steps.log
…
05-CSV-행별결과
06-단어목록-검색
07-배정표-오늘과잔량                        ← "교체 불가" 단정을 지났다
NOTE 배정표 폭: 문서 497px · 표 481px · 뷰포트 390px
NOTE D-42-4 링크를 가로채는 요소: {"link":"374,971 24x44","hit":"A.admin-link"}
08-교체-단어검색
09-교체-배정확인
NOTE 2026-11-14 ko 배정을 '빗자루' 으로 교체 확인      ← 끝까지 갔다
```

### 리뷰 "참고" 중 같이 고친 것

- **R-4** `expectAxeClean` 의 soft 메시지가 상황과 반대였다("고쳐졌다면 지워라" 가
  **아직 위반이 있을 때** 찍힌다). 문구만 바꿨다 — "`<결함>` 의 접근성 위반이 아직 남아
  있다 — 고쳐졌으면 known 에서 지워라". 동작은 그대로다.
- **R-6** 리포터를 직접 넘기면(`--reporter=line`) 설정의 html/json 리포터가 대체되어
  `report/results.json` 이 갱신되지 않는다 — README "산출물" 항목에 한 줄 적었다.

### 고치지 않은 것 (근거)

- **D-42-1 ~ D-42-4** 는 앱 결함이고 이 티켓의 범위가 아니다(코디네이터 메모: 이들을
  가리키는 실패 9건은 의도된 것). 수정 티켓에서 R-1 의 조언(`#message` 를 `toHaveText` 로)
  을 함께 보면 된다.
- **R-3**(`scripts/e2e/words_en.csv` 가 브리프 문면을 벗어남)·**R-5**(`_shift_sql` 을
  pytest 의 MySQL 로 실행)·**R-7** 은 결함이 아니고 코디네이터 확인/후속 사항이라 손대지
  않았다. R-2(백업 코드 입력칸이 24px 로 눌림)는 D-42-1 수정 뒤 다시 볼 일이다.

### 재검증 (로컬 `main` 위, 실제 출력)

`git rebase main` 은 **no-op** 이었다 — 이 브랜치의 베이스가 이미 로컬 `main`(`d27417c`)이다.

```
$ git log --oneline -1 main
d27417c docs(plan): user-todo 14·18 에 티켓 41 사람 항목(TESTFLIGHT_TESTER_EMAIL·수출규정 확인) 반영
$ git merge-base --is-ancestor main HEAD && echo "main 은 HEAD 의 조상"
main 은 HEAD 의 조상
$ git status --short        # 커밋 뒤 clean
```

**① 웹 E2E 한 판 (2026-10-16 01:40 KST)**

```
$ scripts/e2e_web.sh
[e2e-stack] … DB chosung_daily_e2e_t42 drop … Redis DB 4 flush … up … 포트 5042/5142 /health 확인
단어 시드: ko 20개 추가, en 12개 추가
퍼즐 배정: 못박음 10건, 자동 배정 {'ko': 25, 'en': 25}     ← 못박음 6건 → 10건 (언어마다 5일)
운영자 게스트: id=1 email=e2e-admin@example.com

  9 failed
    [desktop-1280] › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → … (ko) / (en)
    [desktop-1280] › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (ko) / (en)
    [mobile-390]   › specs/04-backup-restore.spec.mjs › [5] 백업 코드 → … (ko) / (en)
    [mobile-390]   › specs/06-account-delete.spec.mjs › [7] 계정 삭제 → 새 게스트로 시작 (ko) / (en)
    [mobile-390]   › specs/09-admin.spec.mjs › [10] 운영자: 로그인 → CSV 업로드 → 배정표 확인 → 단어 교체
  39 passed (1.3m)
[e2e-stack] … 종료 … DB drop … Redis DB 4 flush … down 완료
```

**42개 → 48개**(+6), 실패는 **그대로 9건**이고 전부 앱 결함 4건의 단정이다 — 새로 깨진 것이
없고, 고친 세 건이 가린 실패도 없다:

```
   4   Error: D-42-1: 복사 버튼 라벨이 Jinja dict.copy 메서드로 렌더된다
   4   Error: D-42-2 의 접근성 위반이 아직 남아 있다 — 고쳐졌으면 known 에서 지워라   (R-4 로 문구만 바뀜)
   4   Error: D-42-3: 삭제 완료 안내가 restart() 에 지워진다
   1   Error: D-42-4: 390px 뷰포트에서 배정표가 가로로 넘친다
   1   Error: D-42-4: 390px 에서 교체/배정 링크를 탭할 수 없다
```

en 쪽이 실제로 돈 증거(`e2e-artifacts/web/10-streak-en/desktop-1280/steps.log`) — 언어별
칸이 갈려 찍힌다:

```
NOTE advance-day: 1일 전진: DB 77행 시프트, Redis 8키 rename · 4키 삭제, manifest 10건 시프트
NOTE GET /me/history?days=7 → [ … {"date":"2026-10-15","results":{"en":"success","ko":"none"}},
                                 {"date":"2026-10-16","results":{"en":"success","ko":"none"}}]
```

산출물 폴더도 언어별로 갈렸다: `07-offline-ko` · `07-offline-en` · `07-server-error-ko` ·
`07-server-error-en` · `10-streak-ko` · `10-streak-en`.

**② pytest 전체**

```
$ TEST_DATABASE_URL=…/chosung_daily_test_t42 TEST_REDIS_URL=…/5 uv run pytest -q
1734 passed in 775.83s (0:12:55)        ← exit 0  (1713 → 1734, 새 계약 테스트 +21개)
```

`tests/test_e2e_scripts.py` 는 20개 → **41개**다. 위 전체 판 뒤에 `BILINGUAL_SPECS` 를
"예외만 적고 나머지는 디렉터리에서 읽기" 로 바꿨고(새 스펙이 생기면 자동으로 ko·en 을
요구한다) 그 파일만 다시 돌려 41 passed 를 확인했다 — 테스트 수·대상은 같다.

**③ ruff · Flutter**

```
$ uv run ruff check .
All checks passed!

$ cd mobile && flutter analyze
No issues found! (ran in 7.1s)           ← exit 0

$ cd mobile && flutter test
00:43 +796: All tests passed!             ← exit 0
```

(`ruff format --check` 는 `main` 자체가 미포맷이라 이 티켓의 게이트가 아니다 — 리뷰 §1 과 동일.)

**④ 자원 정리**

```
$ scripts/e2e_stack.sh status
프로세스   없음
$ redis-cli info keyspace          # db4(E2E 42) 가 목록에 없다 = 비어 있다
db0:keys=19,expires=0,avg_ttl=0,subexpiry=0            (db0 = 로컬 개발)
$ git status --short               # 추적 안 되는 파일 0개 (e2e-artifacts/ 는 gitignore)
```

