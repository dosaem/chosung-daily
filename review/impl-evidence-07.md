# 티켓 07 구현 증거 — 리더보드 익명화·내 순위·최근 7일 기록

- 브랜치: `dosaem/t07-leaderboard-privacy-me-history`, 로컬 `main` = `20d279a`(티켓 10 머지) 위로 rebase
- 커밋 3개: `db0f02d` 리더보드 익명 표시·ZRANK / `2d4bb69` `/me/history` / `427ed99` README
  (+ 이 문서 커밋)
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t07`,
  `TEST_REDIS_URL=redis://localhost:6379/9`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t07_migrations`
  (공용 테스트 DB·Redis DB 1 은 건드리지 않았다. 다른 워커의 컨테이너도 내리지 않았다)
- 마이그레이션 없음 — 스키마를 안 바꿨다(읽기 전용 조회 2개). `flask db heads` 는 그대로 1줄
- UI 변경 없음 — 백엔드 API 티켓이라 `impeccable detect` 는 해당 없다(화면은 앱·웹 티켓 몫).
  디자인 참조는 `design/SCREENS.md` S3·S4 의 **응답 필드 요구**에만 썼다: S3 "내 순위 카드
  고정 — `me` 필드(21위 밖이어도 옴)", "게스트 #a3f1", "내 행은 `is_me` 로 강조";
  S4 "최근 7일 미니 그리드(날짜별 성공/실패/미플레이 점)"

## 실행한 검증

### 1. 전체 테스트 스위트 (두 번째 rebase 후, `main` = `20d279a`)

```
$ uv run ruff check . && uv run pytest -q
All checks passed!
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 70%]
........................................................................ [ 93%]
....................                                                     [100%]
308 passed in 145.53s (0:02:25)
```

실패·skip·xfail 없음. 작업 시작 시점(티켓 03 머지 상태)의 기준선은 `219 passed` 였고,
그 뒤 로컬 `main` 에 머지된 티켓 20·10 을 포함한 현재 베이스 + 이 티켓의 신규 11개가 308 이다.

> rebase 는 두 번 했다. 첫 테스트를 돌리는 동안 `main` 이 `528879b`(티켓 20) → `20d279a`(티켓 10)
> 로 또 움직여서, 새 `main` 위로 다시 rebase 하고 전체 스위트를 다시 돌렸다. 두 번 다 충돌 없음.
> 첫 rebase(`528879b`) 직후 결과도 통과였다: `269 passed in 138.34s`.

### 2. 신규·수정 테스트만 (이름까지)

```
$ uv run pytest tests/test_leaderboard.py tests/test_me_history.py \
    tests/test_puzzle_language_api.py tests/test_redis_failure_fallback.py -v
tests/test_leaderboard.py::test_leaderboard_ranks_fewer_attempts_first PASSED
tests/test_leaderboard.py::test_leaderboard_respects_limit PASSED
tests/test_leaderboard.py::test_leaderboard_entries_do_not_leak_guest_id PASSED
tests/test_leaderboard.py::test_display_name_is_guest_id_in_four_hex_digits PASSED
tests/test_leaderboard.py::test_my_rank_comes_down_even_when_outside_the_page PASSED
tests/test_leaderboard.py::test_me_is_null_when_i_have_not_solved_today PASSED
tests/test_leaderboard.py::test_me_is_filled_even_when_i_am_on_the_page PASSED
tests/test_me_history.py::test_history_returns_seven_kst_days_oldest_first PASSED
tests/test_me_history.py::test_history_marks_each_language_separately PASSED
tests/test_me_history.py::test_history_shows_none_for_a_day_someone_else_played PASSED
tests/test_me_history.py::test_history_days_can_be_widened_up_to_31 PASSED
tests/test_me_history.py::test_history_rejects_days_outside_the_allowed_range PASSED
tests/test_me_history.py::test_history_requires_a_guest_token PASSED
tests/test_puzzle_language_api.py::... (10개) PASSED
tests/test_redis_failure_fallback.py::... (5개) PASSED
============================= 28 passed in 31.86s ==============================
```

### 3. 린트

```
$ uv run ruff check .
All checks passed!
```

`ruff format --check` 는 **돌리지 않았다** — CI(`.github/workflows/ci.yml`)가 `ruff check .` 만
쓰고, `format --check` 는 이 티켓을 건드리기 전에도 이미 13개 파일에서 실패한다(기존 부채).
대신 이 티켓이 **새로 쓴** 코드만 따로 확인해서 전부 format 통과임을 봤다
(`app/api/me.py`, `app/schemas/history.py`, `app/schemas/leaderboard.py`,
`app/services/stats_service.py`, `app/services/game_rules.py`,
`app/repositories/attempt_repository.py`, `tests/test_leaderboard.py`,
`tests/test_me_history.py`, `tests/test_redis_failure_fallback.py` → `9 files already formatted`).
`app/services/puzzle_metrics.py` 와 `tests/test_puzzle_language_api.py` 는 **내가 안 건드린
줄**에서 format 지적이 남아 있고, 범위 밖 재포맷을 피해 그대로 뒀다.

### 4. 마이그레이션 head

```
$ FLASK_APP=wsgi.py uv run flask db heads
f394da7f4d88 (head)
```

1줄. 이 티켓은 마이그레이션을 추가하지 않았다(티켓 10 이 머지한 head 그대로).

### 5. 작업 트리 / 커밋

```
$ git status --short
(출력 없음)

$ git log --oneline main..HEAD
427ed99 docs(07): README API 표 갱신과 설계 판단 07 세 항목
2d4bb69 feat(07): 최근 N일 기록 조회 GET /me/history
db0f02d feat(07): 리더보드 익명 표시와 ZRANK 내 순위
```

## 체크박스별 증거

| 티켓 체크박스 | 증명하는 것 |
|---|---|
| 리더보드 응답이 `entries [{rank, display, attempts, seconds, is_me}]` + `me \| null`(ZRANK), `guest_id`·`solved_in_seconds` 제거 | `tests/test_leaderboard.py::test_leaderboard_entries_do_not_leak_guest_id` — 엔트리의 **키 집합**을 `{rank, display, attempts, seconds, is_me}` 와 정확히 비교해서, 필드 추가는 물론 `guest_id`·`solved_in_seconds` 가 남아 있으면 깨진다. 스키마: `app/schemas/leaderboard.py`(`LeaderboardEntry`, `MyRank`), 조립: `app/services/puzzle_metrics.py::get_today_leaderboard` + `_my_rank`(ZRANK+ZSCORE) |
| `display` = `"게스트 #" + f"{guest.id % 0x10000:04x}"`(충돌 허용) | `test_display_name_is_guest_id_in_four_hex_digits` — `display_name(1) == "게스트 #0001"`, `display_name(0xA3F1) == "게스트 #a3f1"`, `display_name(0x10001) == display_name(1)`(충돌 허용을 테스트로 못 박음). 구현: `puzzle_metrics.display_name` |
| 25명 중 내가 23위일 때 `entries` 20개 + `me.rank == 23` | `test_my_rank_comes_down_even_when_outside_the_page` — 게스트 25명이 실제로 `POST /puzzles/today/guesses` 를 쳐서 리더보드를 만든다(mock 아님). 앞 22명 1회 정답, 나 2회 정답, 뒤 2명 3회 정답 → `len(entries) == 20`, 20개 모두 `is_me is False`, `me.rank == 23`, `me.attempts == 2` |
| 미정답이면 `me == null` | `test_me_is_null_when_i_have_not_solved_today` — 남은 풀었고 나는 안 푼 상태에서 `entries` 1개 + `me is None`. Redis 장애 경로도 같은 분기: `tests/test_redis_failure_fallback.py::test_leaderboard_returns_empty_instead_of_erroring_when_redis_is_down` 에 `me is None` 단정을 추가 |
| 기존 `test_leaderboard.py` 를 새 필드로 수정 | `tests/test_leaderboard.py` 의 기존 2개(`..._ranks_fewer_attempts_first`, `..._respects_limit`)를 `display` 기준으로 고치고 5개를 추가. 같은 필드를 쓰던 `tests/test_puzzle_language_api.py::test_leaderboard_is_separated_per_language` 도 `display_name` 비교로 수정 |
| `GET /me/history?days=7` 이 `[{date, results: {ko, en}}]` 를 KST 날짜로, 값은 success\|fail\|in_progress\|none | `test_history_returns_seven_kst_days_oldest_first`(KST 오늘까지 7일, 오래된 순) · `test_history_marks_each_language_separately`(어제 ko=success/en=fail, 오늘 ko=in_progress/en=none 네 값 전부) · `test_history_shows_none_for_a_day_someone_else_played`(남의 시도가 내 칸을 채우지 않는다). 구현: `app/api/me.py::my_history`, `app/services/stats_service.py::get_my_history`, `app/repositories/attempt_repository.py::summarize_by_date_and_language`, 분류 `app/services/game_rules.py::day_result` |
| days 상한 31 | `test_history_days_can_be_widened_up_to_31`(31 → 200, 31행) · `test_history_rejects_days_outside_the_allowed_range`(`32`·`0`·`-1`·`abc` → 400 `VALIDATION_ERROR`). 상한 상수: `stats_service.MAX_HISTORY_DAYS` |
| README API 표 갱신, "설계 판단" 에 "리더보드 익명 표시" 추가 | `README.md` — API 표에 `/api/v1/me/history?days=7` 행 추가 + 리더보드 행의 응답 필드를 새 모양으로 교체. "설계 판단" 섹션 끝에 `### 07.` 세 항목: "리더보드 익명 표시 — 이메일도 게스트 ID도 안 내려보낸다", "내 순위는 페이지가 아니라 ZRANK 로 따로 읽는다", "최근 7일 기록 — GROUP BY 한 번, 빈 날은 서버가 채운다" |

## 티켓·스펙에 답이 없어 내가 정한 것 (README "설계 판단" 07 에 근거를 적었다)

1. **상위 20위 안에 있어도 `me` 를 채운다.** 스펙은 `me … | null` 의 null 조건을 "ZRANK" 로만
   적어서, 멤버가 있으면(= 풀었으면) 항상 채우는 쪽으로 읽었다. 클라이언트가 "`entries` 에서
   `is_me` 를 찾아보고 없으면 `me`" 라는 분기를 안 만들게 된다.
   테스트: `test_me_is_filled_even_when_i_am_on_the_page`
2. **`/me/history` 는 오래된 날짜부터**(오늘이 마지막). S4 미니 그리드가 한 주를 왼쪽→오른쪽으로
   읽는 순서라 클라이언트가 뒤집지 않아도 된다. 스펙에 정렬 지정이 없다
3. **`days` 범위 밖은 400**(조용히 31로 자르지 않음). 60일을 요청했는데 31일이 오면 상한에
   걸린 건지 그 앞엔 기록이 없는 건지 구분할 수 없다. `abc` 처럼 정수가 아닌 값도 400 이다 —
   `request.args.get(type=int)` 에 맡기면 조용히 기본값 7로 떨어진다
4. **퍼즐이 없던 날·언어도 `none`.** "시도가 0개면 미플레이" 하나로 처리했다. 그날 그 언어의
   퍼즐이 아예 없었던 경우와 퍼즐은 있었지만 안 푼 경우를 기록 화면에서 구분할 이유가 없다
5. **`day_result` 를 `get_today_puzzle_view` 의 status 분기와 합치지 않았다.** 값이 겹치지만
   시도 0개의 해석이 다르다(오늘 = `in_progress`, 지난 날 = `none`)

## 실패·건너뛴 것

- 실패한 테스트 없음. skip·xfail 없음
- `ruff format --check` 미실행(위 3번에 이유와 대체 확인 기록)
- 프로덕션에 닿는 행동 없음: `git push`·배포·NAS·외부 서비스 호출 없음. 외부 호출을 하는 코드
  경로를 이 티켓은 건드리지 않았다
