# 티켓 04 구현 증거 — 제출 일관성·퍼즐 고정·시도 이력 복원

- 브랜치: `dosaem/t04-guess-consistency-puzzle-pin-attempts` (로컬 `main` = `20d279a`
  "Merge 티켓 10" 위로 rebase, 충돌 없음)
- 커밋 3개: `e4ae48d` 서비스·API·테스트 / `3918e5c` 현행 웹·k6 / `ec51d6e` 문서.
  (+ 이 문서 커밋)
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t04`,
  `TEST_REDIS_URL=redis://localhost:6379/6`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t04_migrations`
  (공용 테스트 DB·Redis DB 1 은 건드리지 않았다)
- 마이그레이션 없음(스키마 변경 없음). `Attempt.guess` 에 저장하는 **값**의 정규화
  규칙만 바뀐다.

## 실행한 검증

### 1. 전체 테스트 스위트 (rebase 후)

```
$ uv run pytest -q
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
.......................                                                  [100%]
311 passed in 173.30s (0:02:53)
```

작업 시작 시점의 기준선은 `205 passed`(+ 당시 다른 워커의 병렬 부하로 생긴 MySQL
`Too many connections` 1 failed / 2 errors)였다. 현재 수는 그 뒤 로컬 `main` 에
머지된 티켓(05·07·08·09·10 등)을 포함한 베이스 + 이 티켓의 신규 14개(퍼즐 고정·이력 13 + 웹 번들 1)다.

> 중간에 한 번 `305 passed, 7 errors` 가 났는데 전부 `(1040, 'Too many connections')`
> 였다 — 내가 전체 스위트와 부분 스위트를 **동시에** 돌려서 공용 MySQL 컨테이너의
> 연결을 넘긴 것이고, 코드와 무관하다. 직렬로 다시 돌린 결과가 위 출력이다.

### 2. 신규·수정 테스트만

```
$ uv run pytest -q tests/test_puzzle_pin_and_attempts.py tests/test_guess_flow.py \
    tests/test_web.py tests/test_streak.py tests/test_rate_limit.py \
    tests/test_leaderboard.py tests/test_stats_endpoint.py \
    tests/test_puzzle_language_api.py tests/test_redis_failure_fallback.py \
    tests/test_concurrency.py
.................................................                        [100%]
49 passed in 31.31s
```

TDD: 신규 파일을 먼저 쓰고 돌려 **10 failed, 3 passed** (RED) 를 확인한 뒤 구현했다.
(통과하던 3개는 `puzzle_id` 가 맞는 경우·en 길이 검증·힌트 규칙처럼 기존 동작으로도
만족되던 케이스다.)

### 3. 린트

```
$ uv run ruff check .
All checks passed!
```

`uv run ruff format` 은 돌리지 않았다 — 이 레포는 원래 포맷터 기준으로 정렬돼 있지
않고(기존 5개 파일이 재포맷 대상), CI 게이트도 `ruff check` 다(`.github/workflows/ci.yml`).

### 4. 마이그레이션 head

```
$ ./scripts/check_migration_heads.sh
f394da7f4d88 (head)
OK: Alembic head 1개
```

### 5. 웹 — `impeccable detect`

```
$ ~/.claude/plugins/cache/impeccable/impeccable/4.5.2/skills/impeccable/scripts/impeccable \
    detect web/templates/index.html web/static/style.css web/static/app.js
impeccable detect: could not read linked stylesheet {{ url_for('static', filename='style.css') }}?v={{ asset_version }}
  (resolved to .../web/templates/{{ url_for(...) }}); color and custom-property rules will be incomplete
exit=0      ← findings 0건
```

이 티켓의 완료 조건에 detect 는 없지만(웹 변경이 제출 바디에 필드 하나를 더하는
JS 한 줄이고 마크업·CSS·화면은 그대로다) 웹 파일을 건드렸으니 돌렸고, 0건이다.
경고 한 줄은 티켓 01 증거에 적힌 것과 같은 Jinja `url_for` 파싱 한계다.

### 6. 작업 트리

```
$ git status --short      # (이 문서 커밋 전)
?? review/impl-evidence-04.md
$ git log --oneline main..HEAD
ec51d6e docs(04): 설계 판단 3건·API 표 갱신, 스펙 미정 12 확정
3918e5c fix(04): 현행 웹·부하 스크립트 제출에 puzzle_id 동봉
e4ae48d feat(04): 퍼즐 고정·제출 일관성·시도 이력 복원
```

## 체크박스별 근거

| 티켓 체크박스 | 구현 | 증명하는 테스트/명령 |
|---|---|---|
| `{puzzle_id, guess}` 에서 `puzzle_id` 가 없거나 "KST 오늘 × 게스트 현재 언어" 퍼즐과 다르면 409 `PUZZLE_CHANGED`, 시도 행·GuestStats 불변 (자정 경과·언어 변경) | `app/schemas/guess.py`(`puzzle_id: int \| None`), `app/services/guess_service.py`(퍼즐 조회 직후·`lock_for_guest` **전에** 검사), `app/errors.py`(`PuzzleChangedError` 409) | `tests/test_puzzle_pin_and_attempts.py` 4개 — `test_guess_without_puzzle_id_is_rejected_as_puzzle_changed`(409 + `Attempt.query.count() == 0`), `test_guess_for_yesterdays_puzzle_is_rejected_without_consuming_an_attempt`(**어제 날짜의 진짜 DailyPuzzle 행**을 만들어 그 id 로 제출 → 409 + 시도 0 + `GuestStats(0, 0, None)`), `test_guess_for_other_language_puzzle_is_rejected`(`PATCH /me` 로 en 전환 후 ko 퍼즐 id 제출 → 409 + 시도 0), `test_matching_puzzle_id_is_accepted`(정상 경로 200) |
| 정답 비교: 공백·하이픈 제거 → `s` 제외 정답과 비교, en 대소문자 무시; 길이 불일치는 `VALIDATION_ERROR` 로 시도 미소비; `feedback` 길이 = `length` | `app/services/game_rules.py`(`normalize_for_compare`, `compare_letters`), `app/services/guess_service.py` | `tests/test_puzzle_pin_and_attempts.py::test_english_guess_ignores_separators_and_case`(`Harry Potter` 와 `harry-potter` 의 **응답 JSON 이 완전히 동일**, 둘 다 정답), `::test_english_wrong_guess_feedback_maps_to_separator_free_positions`(`harry-rotter` → `len(feedback) == 11`, 6번째만 False = `length` 와 일치), `::test_english_length_is_checked_after_removing_separators`(`harry potte` → 400 + 시도 0 + `attempts_left == 5`), `::test_korean_guess_ignores_separators`(`해리 포터` 퍼즐에 `해리포터` 정답 처리), 회귀: `tests/test_guess_flow.py::test_length_mismatch_is_rejected_without_consuming_attempt` |
| `GET /puzzles/today` 에 순서 있는 `attempts: [{guess, feedback}]` 와 `hint_unlocked`(항상 false), 정답 행 `feedback` 전부 true (미정 12 확정 + 스펙 기록) | `app/schemas/puzzle.py`(`AttemptView`, `attempts`, `hint_unlocked`), `app/services/puzzle_service.py`(`_attempt_views`) | `tests/test_puzzle_pin_and_attempts.py::test_today_restores_attempts_for_a_fresh_client`(**새 `app.test_client()`** 로 조회해 두 행이 순서대로 같은 `guess`·`feedback`), `::test_solved_attempt_row_feedback_is_all_true`(정답 행 `[True, True]` + `status == "success"`), `::test_attempts_are_empty_before_any_guess`(`[]` + `hint_unlocked is False`), `::test_english_attempt_history_stores_separator_free_guesses`(`Harry-Rotter` → 저장·응답 모두 `HARRYROTTER`). 스펙 기록: `.scratch/store-launch/spec.md` "미정 항목" 끝 `12. **확정(티켓 04)**` 줄 |
| `hint` 는 `show_hint`(3번째 오답 후)일 때 `GET /puzzles/today` 와 제출 응답 둘 다에 채워짐 | `app/services/puzzle_service.py`(`hint if (show_hint or hint_unlocked)`, `hint_unlocked` 는 06 에서 HintUnlock 조회로 교체), `app/services/game_rules.py::compute_reveal`(기존) | `tests/test_puzzle_pin_and_attempts.py::test_hint_is_filled_in_both_responses_after_third_wrong_guess`(1·2번째 오답에선 양쪽 다 `None`, 3번째 오답 응답과 그 직후 `GET` 둘 다 힌트 문자열), 회귀: `tests/test_guess_flow.py::test_hint_revealed_after_third_wrong_guess` |
| 현행 웹 `app.js` 제출에 `puzzle_id` 동봉(최소 변경) | `web/static/app.js`: `state.puzzleId` 추가 → `init()` 에서 `puzzle.puzzle_id` 저장 → `submitGuess` 가 `{puzzle_id, guess}` 전송. 3줄, 다른 웹 로직 불변 | `tests/test_web.py::test_static_js_sends_puzzle_id_with_a_guess`(서빙되는 번들에 두 줄이 있는지 확인 — JS 러너가 없어서 번들 내용으로 본다), `impeccable detect` 0건(위 §5) |
| 테스트: 시도 2회 후 새 client 조회 동일 `attempts` / en `Harry Potter`·`harry-potter` 동일 / 기존 제출 테스트가 `puzzle_id` 동봉으로 통과 | 신규 `tests/test_puzzle_pin_and_attempts.py` 13개 + `tests/test_web.py` 1개 + 기존 8개 파일 수정 | 위 두 칸의 테스트 + 전체 스위트(§1). 수정한 기존 파일: `test_guess_flow`, `test_streak`, `test_rate_limit`, `test_leaderboard`, `test_stats_endpoint`, `test_puzzle_language_api`, `test_redis_failure_fallback`, `test_concurrency`(서비스 직접 호출이라 `submit_guess(guest, puzzle_id, guess)`) |
| README "설계 판단" 에 "puzzle_id 고정과 409", "시도 이력을 서버가 돌려주는 이유" 추가 | `README.md` `### 04. puzzle_id 고정과 409 PUZZLE_CHANGED`, `### 04. 시도 이력을 서버가 돌려주는 이유`, `### 04. 제출 일관성 — 구분자와 대소문자`(세 번째는 같은 티켓의 판단이라 함께) + API 표 두 행 갱신 | `git diff main..HEAD -- README.md` |

## 설계 판단 메모 (티켓·스펙에 답이 없어 내가 정한 것)

1. **`puzzle_id` 누락도 400 이 아니라 409 `PUZZLE_CHANGED`.** 티켓 문장("없거나 …
   다르면 409")을 그대로 따랐고, pydantic 필수 필드로 두면 400 이 나오므로
   `int | None` 으로 받고 서비스가 판정한다. 클라이언트가 할 일은 두 경우 모두
   "새로고침" 하나다. (`app/schemas/guess.py` 주석)
2. **en 의 `Attempt.guess` 는 대문자로 저장한다.** 구분자 제거는 스펙 미정 13 이
   전제하는 바인데 대소문자는 스펙에 없다. `mask` 의 보이는 타일이 이미 대문자로
   통일돼 있어서(`_english_tile`), 보드를 복원했을 때 이력 글자와 문제 타일의 모양이
   섞이지 않도록 같은 기준을 썼다. 비교가 대소문자 무시라 정보 손실은 없다.
3. **`feedback` 은 저장하지 않고 조회 때 다시 계산한다.** 같은 비교 규칙이 두 벌로
   생기는 걸 피하려는 것이고, 덕분에 "정답 행은 전부 true"(미정 12)가 규칙의 결과로
   자연히 나온다. 대신 `compare_letters` 는 길이를 **정답 기준**으로 맞춘다 —
   구분자 규칙이 지금과 달랐던 옛 행(prod 에 이미 있는 ko 시도)도 `length` 길이의
   보드로 안전하게 그려진다.
4. **k6 부하 스크립트도 한 줄 고쳤다**(`k6/midnight_spike.js`). 티켓에 없지만 안 고치면
   `POST .../guesses` 가 전부 409 로 걸러져서 `docs/perf.md` 가 근거로 삼는 측정이
   판정 경로를 못 탄다. 범위를 넓히는 변경이 아니라 같은 API 변경의 뒷정리로 봤다.

## 남은 것 / 다음 티켓에 넘기는 것

- `hint_unlocked` 는 지금 항상 `false` 이고 `hint = show_hint OR hint_unlocked` 의
  OR 자리만 비워 뒀다. 티켓 06 은 `app/services/puzzle_service.py` 의
  `hint_unlocked = False` 한 줄을 HintUnlock 조회로 바꾸면 된다.
- 웹은 아직 서버 `attempts` 로 보드를 그리지 않는다(여전히 `localStorage`). 409
  `PUZZLE_CHANGED` 를 받으면 현행 코드는 에러 메시지만 띄운다 — 자동 새로고침과
  "새 퍼즐이 있어요" 배너는 티켓 17·18 범위다.
- 스펙 미정 13(클라이언트가 `mask` 의 `s` 위치로 간격을 다시 끼우는 규칙)은 티켓 17
  에서 확정한다. 서버 쪽 전제(구분자 없는 `guess`)는 이 티켓에서 갖춰 놨다.

## 머지 준비 rebase

Codex 최종 리뷰(PASS) 이후 로컬 `main` 이 `1b990e7`("Merge 티켓 05") 로 앞서가서 이
브랜치를 그 위로 재배치했다. `git rebase main` → `git merge-base main HEAD` ==
`1b990e7` == `git rev-parse main`.

### 충돌 파일과 해결 방식

| 파일 | 충돌 | 해결 |
|---|---|---|
| `app/services/game_rules.py` | 양쪽이 **파일 끝에 함수를 덧붙였다** — main(티켓 07)은 `day_result`, 이 티켓은 `normalize_for_compare`·`compare_letters` | 둘 다 보존. main 의 `day_result` 를 먼저 두고 그 뒤에 이 티켓의 두 함수를 붙였다. 이 티켓이 파일 머리에 넣은 import 3줄(`unicodedata`, `PuzzleLanguage`, `SEPARATOR_CHARS`)은 자동 머지됐다. 어느 함수도 서로를 참조하지 않아 섞일 지점이 없다 |

나머지 공유 파일은 전부 자동 머지됐고, 결과가 "양쪽 줄이 다 남은" 상태인지 직접 확인했다.

- **`README.md`** — API 표는 main 의 네 변경(`/health` 등급, `/leaderboard` 응답
  형태, 신규 `/me/history`·`/api/v1/config` 행)과 이 티켓의 두 행 갱신
  (`/puzzles/today` 의 `attempts`·`hint_unlocked`, `POST .../guesses` 의
  `{puzzle_id, guess}`·409)이 모두 남았다. "설계 판단" 은 덧붙이기 규칙대로
  `### 05.` 절 뒤에 `### 04.` 세 절이 붙었다 — main 의 `### 08.`·`### 07.`·`### 05.`
  절은 한 줄도 건드리지 않았다.
- **`.scratch/store-launch/spec.md`** — 이 티켓이 "미정 항목" 끝에 추가한
  `12. **확정(티켓 04)**` 한 줄만 남고 다른 티켓의 줄은 그대로다.
- **`tests/test_puzzle_language_api.py`, `tests/test_redis_failure_fallback.py`** —
  main 이 바꾼 단정(`display` 필드, `me is None`)과 이 티켓이 바꾼 제출 본문
  (`puzzle_id` 동봉)이 서로 다른 줄이라 그대로 합쳐졌다.
- `.env.example`, `docs/RELEASE.md` 는 이 티켓이 건드리지 않은 파일이라 main 쪽
  내용이 그대로다.

### 리뷰 이후 코드 변경

**동작(프로덕션 코드) 변경은 없다.** `app/`·`web/`·`k6/` 의 변경 집합이 rebase 전후
바이트 단위로 같은지 파일별로 비교해 확인했다(`app/api/puzzles.py`, `app/errors.py`,
`app/schemas/guess.py`, `app/schemas/puzzle.py`, `app/services/game_rules.py`,
`app/services/guess_service.py`, `app/services/puzzle_service.py`,
`web/static/app.js`, `k6/midnight_spike.js` 전부 동일). 문서·스펙·신규 테스트 파일도
동일하다.

달라진 건 **`tests/test_leaderboard.py` 한 파일**이다. main 의 티켓 07 이 이 파일에
테스트 4개를 새로 추가했는데, 전부 이 파일의 지역 헬퍼 `_guess(client, token, text)`
를 쓴다. 이 티켓이 그 헬퍼를 `_guess(client, token, puzzle, text)` 로 바꿔
`puzzle_id` 를 동봉하게 했으므로, 새 테스트의 호출 9곳에 `today_puzzle` 인자를
끼웠다. 안 끼우면 `puzzle_id` 없는 제출이 409 `PUZZLE_CHANGED` 로 걸러져
리더보드가 비는 실패가 난다. 네 테스트 모두 이미 `today_puzzle` 픽스처를 받고 있어서
인자 추가만으로 끝났고, 단정은 한 줄도 바꾸지 않았다.

### 마이그레이션

이 티켓은 마이그레이션을 추가하지 않는다(스키마 변경 없음). main 이 가져온
`ff06a1bf5afc`(`app_setting` 테이블) 하나가 그대로 head 다 — `down_revision` 을
다시 걸 대상이 없다.

```
$ FLASK_APP=wsgi.py DATABASE_URL="...chosung_daily_test_t04_migrations" uv run flask db heads
ff06a1bf5afc (head)
```

왕복(upgrade → 데이터 → downgrade → upgrade)은 `tests/test_migrations.py` 가 별도
`chosung_daily_test_t04_migrations` DB 에 `flask db` 서브프로세스로 돌리며, 아래
전체 스위트에 포함돼 통과했다.

### rebase 후 재실행

```
$ uv run ruff check .
All checks passed!
```

```
$ uv run pytest -q
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 141.76s (0:02:21)
```

rebase 전 311 → 360 (+49). 늘어난 49개는 main 에 새로 들어온 티켓 05·07·08 의
테스트다. 실패·에러 0, MySQL `Too many connections` 도 없었다.
