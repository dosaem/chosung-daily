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

새 리비전 `dae1b5af0cf7` 의 `down_revision` 은 `a5bab2f58a7b`(구독 테이블,
티켓 12)이다. 리뷰 시점엔 `ff06a1bf5afc`(설정 테이블)였는데, 그 뒤 티켓 12 가
먼저 머지돼 머지 준비 rebase 에서 한 줄을 그 리비전으로 다시 가리켰다
(아래 "머지 준비 rebase"). 티켓 09·11 은 마이그레이션이 없어서 그 두 번의
rebase 에선 손댈 것이 없었다.

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
| `HintUnlock(guest_id, puzzle_id, unlocked_at)` PK(guest_id, puzzle_id) 마이그레이션. 머지 직전 `flask db heads` 1개 | `app/models/hint_unlock.py`(PK 두 컬럼 + `unlocked_at`, 플래그 컬럼 없음), `migrations/versions/dae1b5af0cf7_add_hint_unlock_table_for_early_hint.py`(`down_revision = 'a5bab2f58a7b'`) | `tests/test_migrations.py::test_hint_unlock_table_round_trips`(별도 DB 에서 `flask db upgrade` → 테이블 존재 → `downgrade a5bab2f58a7b` → 사라짐 → 다시 `upgrade` → 존재), `::test_hint_unlock_rows_are_one_per_guest_and_puzzle`(ORM 없이 같은 (guest, puzzle) 를 두 번 INSERT → `IntegrityError`, 행 1개), `./scripts/check_migration_heads.sh`(위 §4) |
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

## 머지 준비 rebase

리뷰(`review/impl-review-06.md` round 1 PASS)를 받은 뒤 로컬 `main` 이
`abf3e9a`("Merge 티켓 12: 구독 DB·영수증 검증 엔드포인트·상태 정규화")로
앞서가서, 리뷰받은 동작을 그대로 둔 채 그 위로 다시 올렸다
(`git rebase main`, 커밋 6개 재적용).

```
$ git merge-base main HEAD
abf3e9a1706de253aa701ab3d321b42db87e9bc0
$ git rev-parse main
abf3e9a1706de253aa701ab3d321b42db87e9bc0
$ git status --short     # (이 절 커밋 전)
 M review/impl-evidence-06.md
```

### 충돌 1건 — `app/models/__init__.py`

유일한 충돌이다. 양쪽이 `from app.models.guest_stats import GuestStats` 바로
아래에 import 한 줄씩을 넣어서 같은 자리가 겹쳤다. 둘 다 살려 알파벳 순으로
놓는 것으로 풀었다.

```python
from app.models.hint_unlock import HintUnlock      # 이 티켓
from app.models.subscription import Subscription   # 티켓 12
```

`__all__` 은 리스트가 알파벳 순이고 두 항목(`"HintUnlock"` / `"Subscription"`
계열 4개)이 서로 떨어진 자리에 들어가서 git 이 자동 병합했다 — 양쪽 항목이
모두 남아 있다.

### 자동 병합된 공유 파일 (충돌 없음, 양쪽 줄 보존 확인)

| 파일 | 이 티켓이 넣은 것 | 티켓 12 가 넣은 것 |
|---|---|---|
| `README.md` API 표 | `POST /api/v1/puzzles/today/hint-unlock` 행 | `POST /api/v1/subscriptions/verify` 행 (두 행 모두 표에 있다) |
| `README.md` "설계 판단" | `### 06. 힌트 미리 보기 공정성 · AdMob SSV 미사용` | `### 12. 구독 검증 …` (두 절 모두 있다) |
| `app/errors.py` | `HintAlreadyUnlockedError`(409) | `ReceiptInvalidError`(400)·`StoreUnavailableError`(503) (세 클래스 모두 있다) |

`.env.example`·`docs/RELEASE.md`·`.scratch/store-launch/spec.md`("미정 항목")·
`pyproject.toml`·`uv.lock` 은 이 티켓이 건드린 적이 없어서 `main` 과 바이트
단위로 같다 — 티켓 12 가 넣은 줄이 그대로다.

```
$ for f in .env.example docs/RELEASE.md .scratch/store-launch/spec.md pyproject.toml uv.lock; do
>   git diff --quiet main HEAD -- "$f" && echo "same as main: $f"; done
same as main: .env.example
same as main: docs/RELEASE.md
same as main: .scratch/store-launch/spec.md
same as main: pyproject.toml
same as main: uv.lock
```

### 마이그레이션 — `down_revision` 재설정

티켓 12 가 `a5bab2f58a7b`(구독 테이블)을 `ff06a1bf5afc` 위에 올려 머지됐고, 이
티켓의 `dae1b5af0cf7` 도 같은 `ff06a1bf5afc` 를 가리키고 있었다. 그대로 두면
head 가 둘로 갈라지므로 이 티켓 쪽을 `a5bab2f58a7b` 위로 다시 가리켰다
(`scripts/check_migration_heads.sh` 주석이 지시하는 그 조치다). `upgrade`/
`downgrade` 본문은 손대지 않았다.

```
$ ./scripts/check_migration_heads.sh
dae1b5af0cf7 (head)
OK: Alembic head 1개
```

왕복도 수동으로 한 번 더 확인했다(`DATABASE_URL` = `chosung_daily_test_t06_migrations`).

```
$ uv run flask db upgrade
... Running upgrade ff06a1bf5afc -> a5bab2f58a7b, add subscription table
... Running upgrade a5bab2f58a7b -> dae1b5af0cf7, add hint_unlock table for early hint
$ uv run flask db current
dae1b5af0cf7 (head)
$ uv run flask db downgrade a5bab2f58a7b
... Running downgrade dae1b5af0cf7 -> a5bab2f58a7b, add hint_unlock table for early hint
$ uv run flask db current
a5bab2f58a7b
$ uv run flask db upgrade
... Running upgrade a5bab2f58a7b -> dae1b5af0cf7, add hint_unlock table for early hint
$ uv run flask db current
dae1b5af0cf7 (head)
```

이에 맞춰 `tests/test_migrations.py` 의
`HINT_UNLOCK_PARENT_REVISION` 을 `"ff06a1bf5afc"` → `"a5bab2f58a7b"` 로 바꿨다.
이 상수는 `test_hint_unlock_table_round_trips` 가 downgrade 목표로 쓰는 값이라,
안 바꾸면 그 테스트가 구독 테이블까지 같이 내렸다 올리면서 "힌트 테이블 직전
리비전" 이라는 이름과 어긋난다.

### 리뷰 이후 코드 변경 — 없음 (리비전 문자열 3줄만)

rebase 전후의 티켓 변경분을 줄 단위로 비교했다. 다른 줄은 하나도 없고, 바뀐 건
위에 적은 리비전 체인 문자열 3줄뿐이다 — 동작·분기·스키마·테스트 단정은 리뷰가
PASS 한 상태 그대로다.

```
$ git diff b43567e bb1cb55 > before.diff      # rebase 전 (리뷰받은 상태)
$ git diff main     HEAD    > after.diff      # rebase 후
$ diff <(grep -E '^[+-]' before.diff) <(grep -E '^[+-]' after.diff)
194c194
< +Revises: ff06a1bf5afc
---
> +Revises: a5bab2f58a7b
204c204
< +down_revision = 'ff06a1bf5afc'
---
> +down_revision = 'a5bab2f58a7b'
729c729
< +HINT_UNLOCK_PARENT_REVISION = "ff06a1bf5afc"  # 힌트 미리 보기 테이블 직전 리비전
---
> +HINT_UNLOCK_PARENT_REVISION = "a5bab2f58a7b"  # 힌트 미리 보기 테이블 직전 리비전
```

이 문서의 §4 와 체크박스 표에 있던 `ff06a1bf5afc` 도 현재 값으로 고쳤다
(문서만, 코드 아님).

### 재실행 — 전체 테스트 · 린트

```
$ uv run pytest -q
........................................................................ [ 10%]
...(생략)...
........................................................................ [ 84%]
........................................................................ [ 94%]
....................................                                     [100%]
684 passed in 396.94s (0:06:36)
```

684 = 티켓 12 까지 머지된 새 베이스(`main` = `abf3e9a`) + 이 티켓의 신규 16개.
rebase 전 571 에서 늘어난 113 개는 전부 티켓 12 가 들고 온 테스트다
(`tests/test_store_clients.py`·`test_subscription_verify.py`·
`test_subscription_status.py`). 삭제·비활성화·skip 으로 돌린 테스트는 없다.

```
$ uv run pytest -q tests/test_hint_unlock.py tests/test_concurrency.py \
    tests/test_migrations.py
.......................                                                  [100%]
23 passed in 54.52s

$ uv run ruff check .
All checks passed!
```

전용 테스트 자원은 그대로 썼다 — DB `chosung_daily_test_t06`, Redis DB 8,
`TEST_MIGRATION_DATABASE_URL` = `chosung_daily_test_t06_migrations`.
