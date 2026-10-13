# 티켓 06 구현 증거 — 힌트 미리 보기(HintUnlock) 엔드포인트

- 브랜치: `dosaem/t06-hint-unlock-rewarded` (로컬 `main` = `b43567e` "Merge 티켓 11"
  위로 rebase, 충돌 없음. 작업 중 `main` 이 09 → 11 로 두 번 움직여 두 번 rebase
  했고, 아래 수치는 전부 마지막 rebase 뒤에 다시 돌린 것이다)
- 커밋 3개: `c8796f0` 모델·마이그레이션 / `f4d841c` 서비스·API·테스트 /
  `6ad2053` 문서. (+ 이 문서 커밋)
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t06`,
  `TEST_REDIS_URL=redis://localhost:6379/8`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t06_migrations`
  (공용 테스트 DB·Redis DB 1 은 건드리지 않았다)
- UI 변경 없음 — 백엔드 엔드포인트 하나다. 웹은 광고가 없어 이 경로를 쓰지 않고
  (`CONTEXT.md` "웹"), 앱 화면은 Flutter 티켓 몫이라 `impeccable detect` /
  `audit.native` 는 이 티켓의 완료 조건에 없다.

## 실행한 검증

### 1. 전체 테스트 스위트 (rebase 후)

```
$ uv run pytest -q
........................................................................ [ 12%]
...(생략)...
........................................................................ [ 75%]
........................................................................ [ 88%]
...................................................................      [100%]
571 passed in 484.72s (0:08:04)
```

571 = rebase 후 베이스(`main` = `b43567e`, 티켓 11 까지 머지됨) 555 + 이 티켓의
신규 16개(`tests/test_hint_unlock.py` 12 + `tests/test_concurrency.py` 2 +
`tests/test_migrations.py` 2). 삭제·비활성화한 테스트는 없다. 같은 코드를 중간
베이스에서 돌린 값도 적어둔다 — `main` = `8115301` 일 때 `376 passed`,
`main` = `d440172`(티켓 09) 일 때 `552 passed`. 차이는 전부 그 티켓들이 들고 온
테스트다.

### 2. 신규 테스트만

```
$ uv run pytest -q tests/test_hint_unlock.py tests/test_concurrency.py \
    tests/test_migrations.py
.......................                                                  [100%]
23 passed in 34.59s
```

TDD: `tests/test_hint_unlock.py` 를 먼저 쓰고 돌려
`ImportError: cannot import name 'HintUnlock' from 'app.models'` (RED) 를 확인한
뒤 모델 → 레포지토리 → 서비스 → 라우트 순으로 구현했다.

동시성 테스트는 스레드 인터리빙에 따라 두 갈래(미리 보기 선행 / 제출 선행)가
나올 수 있어서 `tests/test_concurrency.py` 만 6회 연속 돌려 둘 다 일관된 상태로
끝나는지 확인했다 — 6회 모두 `3 passed`.

### 3. 린트

```
$ uv run ruff check .
All checks passed!
```

`uv run ruff format` 은 돌리지 않았다 — 레포가 포맷터 기준으로 정렬돼 있지 않고
(기존 23개 파일이 재포맷 대상), CI 게이트도 `ruff check` 다
(`.github/workflows/ci.yml`).

### 4. 마이그레이션 head

```
$ ./scripts/check_migration_heads.sh
dae1b5af0cf7 (head)
OK: Alembic head 1개
```

새 리비전 `dae1b5af0cf7` 의 `down_revision` 은 `ff06a1bf5afc`(설정 테이블)이다.
`main` 에 머지된 티켓 09·11 은 마이그레이션이 없어서 두 번의 rebase 뒤에도 head
가 하나다. 머지 순서가 바뀌어 앞에 다른 마이그레이션이 들어오면 이 한 줄만
그 리비전으로 다시 가리키면 된다.

### 5. 작업 트리

```
$ git status --short      # (이 문서 커밋 전)
?? review/impl-evidence-06.md
$ git log --oneline main..HEAD
6ad2053 docs(06): README 설계 판단 "힌트 미리 보기 공정성·AdMob SSV 미사용" · API 표 행
f4d841c feat(06): POST /puzzles/today/hint-unlock 과 힌트 표시 규칙 완성
c8796f0 feat(06): HintUnlock 테이블 — 힌트 미리 보기 기록
```

## 체크박스별 근거

| 티켓 체크박스 | 구현 | 증명하는 테스트/명령 |
|---|---|---|
| `HintUnlock(guest_id, puzzle_id, unlocked_at)` PK(guest_id, puzzle_id) 마이그레이션. 머지 직전 `flask db heads` 1개 | `app/models/hint_unlock.py`(PK 두 컬럼 + `unlocked_at`, 플래그 컬럼 없음), `migrations/versions/dae1b5af0cf7_add_hint_unlock_table_for_early_hint.py`(`down_revision = 'ff06a1bf5afc'`) | `tests/test_migrations.py::test_hint_unlock_table_round_trips`(별도 DB 에서 `flask db upgrade` → 테이블 존재 → `downgrade ff06a1bf5afc` → 사라짐 → 다시 `upgrade` → 존재), `::test_hint_unlock_rows_are_one_per_guest_and_puzzle`(ORM 없이 같은 (guest, puzzle) 를 두 번 INSERT → `IntegrityError`, 행 1개), `./scripts/check_migration_heads.sh`(위 §4) |
| `POST /puzzles/today/hint-unlock {puzzle_id}` 가 `GuestStats FOR UPDATE` 경로로 들어가 행을 넣고 `{hint}` 를 돌려준다. 끝난 퍼즐 409 `ALREADY_FINISHED`, 이미 열림 409 `HINT_ALREADY_UNLOCKED`, 퍼즐 불일치 409 `PUZZLE_CHANGED`. 구독자·비구독자 구분 없음 | `app/services/hint_service.py::unlock_hint`(퍼즐 조회 → `puzzle_id` 확인 → `lock_for_guest`(= `SELECT ... FOR UPDATE`) → 잠금 안에서 시도 이력·열림 여부 조회 → `HintUnlock` INSERT → commit), `app/api/puzzles.py::hint_unlock`, `app/errors.py::HintAlreadyUnlockedError`(409), `app/schemas/puzzle.py`(`HintUnlockRequest.puzzle_id: int \| None`, `HintUnlockResponse.hint`). 구독·광고 시청 여부를 보는 분기가 코드에 없다 | `tests/test_hint_unlock.py` 7개 — `test_unlock_returns_the_hint_and_records_one_row`(200 + 바디가 정확히 `{"hint": ...}` + `HintUnlock` 행 존재), `test_second_unlock_is_rejected`(409 `HINT_ALREADY_UNLOCKED` + 행 1개), `test_unlock_on_a_solved_puzzle_is_rejected`(409 `ALREADY_FINISHED` + 행 0), `test_unlock_after_every_attempt_is_used_is_rejected`(5회 오답 후 409 `ALREADY_FINISHED` + 행 0), `test_unlock_without_a_puzzle_id_is_rejected_as_puzzle_changed`(409 `PUZZLE_CHANGED` + 행 0), `test_unlock_for_yesterdays_puzzle_is_rejected_as_puzzle_changed`(**어제 날짜의 진짜 `DailyPuzzle` 행**을 만들어 그 id 로 호출 → 409 + 행 0), `test_unlock_is_separate_per_puzzle`(ko 를 연 뒤 en 으로 바꿔 조회 → `hint_unlocked false`) |
| `hint` 채움 규칙이 `show_hint OR hint_unlocked` 로 완성돼 `GET /puzzles/today`·제출 응답 둘 다 반영, `hint_unlocked` 가 true 로 내려온다(테스트: 열고 새 client 로 조회) | `app/services/puzzle_service.py::get_today_puzzle_view`(상수 `False` 자리를 `is_unlocked(guest.id, puzzle.id)` 로 교체), `app/services/guess_service.py::submit_guess`(잠금 안에서 `is_unlocked` 를 읽어 `hint=word.hint if (show_hint or hint_unlocked)`), `app/repositories/hint_unlock_repository.py::is_unlocked`(존재 여부만 읽는 쿼리) | `tests/test_hint_unlock.py::test_unlocked_hint_comes_back_on_a_new_client`(**새 `app.test_client()`** 로 `GET /puzzles/today` → `hint_unlocked is True` + `hint == "빨간 과일"`), `::test_unlocked_hint_is_filled_in_the_guess_response`(열기 전 오답 응답 `hint is None` → 연 뒤 오답 응답에 힌트), 회귀: `tests/test_puzzle_pin_and_attempts.py::test_hint_is_filled_in_both_responses_after_third_wrong_guess`(미리 보기 없이 3번째 오답 경로도 그대로), `::test_attempts_are_empty_before_any_guess`(`hint_unlocked is False` 기본값) |
| 힌트 열림이 시도 수·`solved_in_seconds`·리더보드에 영향 없음을 테스트로 고정 | `unlock_hint` 가 `Attempt` 도 `GuestStats` 도 쓰지 않는다 — 잠금만 잡고 `HintUnlock` 한 행만 INSERT 한다. 리더보드 점수(`app/services/puzzle_metrics.py`: 시도 횟수 × 86400 + 걸린 초)는 제출 경로에서만 쓰인다 | `tests/test_hint_unlock.py::test_unlock_does_not_consume_an_attempt`(연 뒤에도 `attempts_left == 5`, `attempts == []`, `Attempt.query.count() == 0`), `::test_unlock_does_not_touch_guest_stats`(`solved_count`·`current_streak`·`max_streak` 0, `last_solved_date` None), `::test_unlock_does_not_change_the_leaderboard_entry`(힌트를 열고 1번째에 맞춘 게스트와 그냥 1번째에 맞춘 게스트가 같은 `attempts: 1`, `seconds` 차이 ≤ 1초, `me.attempts == 1`). 스펙 §A' 에서 리더보드 응답의 `solved_in_seconds` 는 `seconds` 로 바뀌었고(티켓 07) 그 값이 tie-breaker 라 거기로 검증했다 |
| 동시성 테스트(기존 `test_concurrency.py` 패턴): 힌트 미리 보기와 제출을 동시에 보내도 FOR UPDATE 로 직렬화되고 상태가 일관됨 | 두 서비스가 같은 `lock_for_guest(guest.id)` 를 쓴다 | `tests/test_concurrency.py::test_hint_unlock_and_guess_are_serialized`(배리어로 두 스레드를 동시에 풀고, 제출은 항상 성공 / 미리 보기는 `ok` 또는 `AlreadyFinishedError`, 그에 맞춰 `HintUnlock` 행 1개 또는 0개, 어느 쪽이든 `Attempt` 1개·`attempt_no == 1`·`solved_count == 1`), `::test_concurrent_hint_unlocks_insert_one_row`(동시 두 번 → `["HintAlreadyUnlockedError", "ok"]` + 행 1개). 6회 반복 실행에서 전부 통과(위 §2) |
| README "설계 판단" 에 "힌트 미리 보기 공정성·AdMob SSV 미사용 근거" 추가 | `README.md` `### 06. 힌트 미리 보기 공정성 · AdMob SSV 미사용`(섹션 끝에 자기 번호 소제목으로 덧붙임) + API 표 끝에 `hint-unlock` 행 1개 | `git diff main..HEAD -- README.md` |

## 설계 판단 메모 (티켓·스펙에 답이 없어 내가 정한 것)

1. **3번째 오답으로 힌트가 이미 보이는 상태에서도 호출을 막지 않는다.** 스펙이
   세는 거절 상태는 `PUZZLE_CHANGED`·`ALREADY_FINISHED`·`HINT_ALREADY_UNLOCKED`
   셋뿐이다. 네 번째를 만들면 클라이언트가 "지금 광고 버튼을 띄워도 되는가"를
   서버 규칙(3번째 오답 경계)으로 한 번 더 계산해야 하고, 그 계산이 서버와
   어긋나는 순간 플레이어는 광고를 본 뒤 409 를 받는다. 그냥 받아서 행 하나를
   넣고 힌트를 돌려주는 쪽이 상태가 단순하다. (README 에 적음)
2. **`rate_limited` 데코레이터를 걸지 않았다.** 제출용 카운터(분당 10회)를 같이
   쓰면 광고를 본 사람이 제출 기회를 깎이는 셈이 되고, 첫 호출 이후는 전부 409
   라서 반복 호출로 늘릴 수 있는 건 조회 한 번뿐이다. 별도 카운터를 새로 파는 건
   티켓 범위 밖이라 하지 않았다. (README 에 적음)
3. **`puzzle_id` 누락도 400 이 아니라 409 `PUZZLE_CHANGED`.** 제출(`GuessRequest`)과
   같은 규칙을 그대로 따랐다 — 클라이언트가 할 일은 두 경우 모두 "새로고침"
   하나다(`app/schemas/puzzle.py` 주석, README `### 04.`).
4. **끝난 퍼즐 판정에 `compute_reveal` 을 재사용한다.** "끝남"의 정의(정답 또는
   5회 소진)가 제출·조회와 한 군데(`app/services/game_rules.py`)에만 있게 하려는
   것이다. `unlock_hint` 는 반환값 중 `finished` 만 쓴다.
5. **열림 조회는 `EXISTS` 성격의 쿼리 하나(`is_unlocked`)로 둔다.** `GET
   /puzzles/today` 와 제출이 요청마다 부르는 경로라 행 전체를 읽을 이유가 없고,
   레포지토리에 쓰기 함수를 따로 두지 않은 건 기존 제출 경로가
   `db.session.add(Attempt(...))` 를 서비스에서 직접 하는 것과 맞췄기 때문이다.

## 남은 것 / 범위 밖

- **계정 삭제 시 `HintUnlock` 행 삭제**(스펙 §A.7)는 티켓 07(계정 삭제) 몫이다.
  이 레포에는 아직 `DELETE /me` 서비스가 없어서 건드릴 자리가 없다.
- **앱의 보상형 광고 흐름**(AdMob 로드·시청 완료 후 이 엔드포인트 호출, S5 "광고
  없이 힌트 미리 보기" 문구)은 Flutter 티켓 몫이다.
- `.env.example`·`docs/RELEASE.md` 는 바꿀 것이 없었다(새 환경변수·배포 절차 변경
  없음).
