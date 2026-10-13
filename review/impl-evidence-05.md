# 티켓 05 구현 증거 — 자정 배정 언어별 실행·캐시·잔량 Slack 알림

브랜치 `dosaem/t05-midnight-assignment-per-language-alerts`, 로컬 `main`(20d279a,
티켓 10 머지) 위로 rebase 한 상태에서 측정했다. UI 를 건드리지 않는 티켓이라
`impeccable detect`/`audit.native` 는 해당 없음.

## 실행 환경

다른 워커와 테스트 자원을 나눠 쓰기 때문에 전용 DB/Redis 를 썼다(공용 테스트
DB·Redis 는 건드리지 않았다).

```sh
export TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t05?charset=utf8mb4"
export TEST_REDIS_URL="redis://localhost:6379/7"
export TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t05_migrations?charset=utf8mb4"
```

실행 중 공용 MySQL 이 `(1040, 'Too many connections')` 로 7개 테스트를 떨어뜨렸다
(병렬 워커 합산 접속 수 > 기본 `max_connections=151`, `Max_used_connections=152`).
테스트 코드 문제가 아니어서 컨테이너의 `SET GLOBAL max_connections = 500` 으로
한도만 올렸다 — 데이터는 건드리지 않았고, 재실행에서 같은 7개가 전부 통과했다.

## 명령과 출력

### 전체 테스트 (rebase 후)

```
$ uv run pytest -q
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
..........................                                               [100%]
314 passed in 173.29s (0:02:53)
```

### 린트 (rebase 후)

```
$ uv run ruff check .
All checks passed!
```

`ruff format --check` 는 레포 전체(기존 18개 파일 포함)가 아직 포맷터를 안 거친
상태라 돌리지 않았다 — CI 게이트는 `.github/workflows/ci.yml` 의 `ruff check .` 다.

### 마이그레이션

이 티켓은 스키마를 바꾸지 않아 새 리비전이 없다. head 는 여전히 1줄이다.

```
$ uv run flask db heads
f394da7f4d88 (head)
```

### 이 티켓이 추가·수정한 테스트 (37개)

```
$ uv run pytest tests/test_puzzle_schedule_service.py tests/test_puzzle_maintenance.py \
    tests/test_word_pool_service.py tests/test_celery_wiring.py tests/test_cli.py -q
37 passed in 19.91s
```

## 체크박스별 근거

| 티켓 체크박스 | 증명하는 테스트/명령 |
|---|---|
| `schedule_puzzles(language, days)` 가 그 언어의 미사용 단어만 고름 | `test_puzzle_schedule_service.py::test_schedule_only_picks_words_of_the_requested_language`(en 배정에 ko 단어가 안 섞임), `::test_schedule_fills_the_other_language_on_the_same_dates`(같은 날짜라도 언어가 다르면 배정됨), `::test_schedule_raises_when_the_language_has_no_words` + 기존 6개 회귀 테스트 |
| CLI `schedule-puzzles --language` | `test_cli.py::test_schedule_puzzles_command_takes_a_language`(`--language en --days 2` → en 퍼즐 2개), `::test_schedule_puzzles_command_rejects_unknown_language`(`jp` → 종료코드≠0, 행 0개), `::test_schedule_puzzles_command`(기본 ko 회귀) |
| `flush_daily_stats_for_yesterday` 가 언어별 키 순회 | `test_puzzle_maintenance.py::test_flush_daily_stats_reads_one_key_per_language`(ko 3·en 5 를 각 행에), `::test_flush_daily_stats_with_no_activity_records_all_zero`(언어마다 0행), 기존 3개 회귀 |
| 배정 서비스 함수가 언어 하나로 배정·캐시 워밍·커밋 | `test_puzzle_maintenance.py::test_ensure_today_puzzle_creates_when_missing`, `::test_ensure_today_puzzle_warms_the_cache_of_its_own_language`(en 키만 생기고 ko 키는 없음), `::test_ensure_today_puzzle_is_idempotent_when_already_exists` |
| Celery 태스크가 지원 언어 순회, 한 언어 실패 → `notify_operator` 후 계속 | `test_puzzle_maintenance.py::test_one_language_failing_does_not_block_the_others`(en 단어 0개 → ko 퍼즐 생성·en 없음·Slack 래퍼 1회 호출, 메시지에 "퍼즐 배정 실패"·"en"), `::test_all_languages_get_their_own_puzzle_and_cache`(정상 경로는 알림 0회), `test_celery_wiring.py::test_tasks_delegate_to_the_service_functions`(태스크 본문이 순회 함수를 부른다) |
| 잔량 계산 서비스 함수(언어별 미사용 단어 수 → 며칠치) | `test_word_pool_service.py::test_remaining_days_counts_unused_words_per_language`, `::test_remaining_days_drops_as_words_get_scheduled`(5개 중 2일 배정 → 3일치), `::test_remaining_days_is_zero_for_a_language_with_no_words` |
| Beat 가 매일 1회 14일 미만 언어를 Slack 알림 | `test_word_pool_service.py::test_notifies_only_the_languages_below_the_threshold`(임계 정확히 14 = 알림 없음, 12 = 알림 1회), `::test_stays_quiet_when_every_language_has_enough_words`, `test_celery_wiring.py::test_beat_schedule_matches_spec_times`(09:00 KST), `::test_tasks_delegate_to_the_service_functions` |
| 배정 시 `puzzle:{date}:{lang}` 캐시 + Redis 장애 시 `safe_redis_call` DB 폴백 | `test_puzzle_maintenance.py::test_ensure_today_puzzle_creates_when_missing`(`puzzle:{today}:ko` 값 확인), `::test_ensure_today_puzzle_warms_the_cache_of_its_own_language`, `::test_ensure_today_puzzle_still_commits_when_redis_is_down`(`broken_redis` 픽스처 — 모든 Redis 호출이 예외를 내는 상태에서도 배정 커밋) |
| Beat 스케줄(KST)에 언어별 배정·잔량 알림 등록 + README 운영 절 | `test_celery_wiring.py::test_tasks_are_registered`(세 태스크 이름), `::test_beat_schedule_matches_spec_times`(00:00 / 00:05 / 09:00), `::test_timezone_is_kst`, README "운영: Celery Beat 스케줄" 절(표 + 수동 트리거 명령) |
| (선택) `beat_schedule` 모듈별 합치기 구조 | `test_celery_wiring.py::test_beat_schedule_is_merged_from_task_modules`, `app/tasks/scheduled.py` 끝의 `celery.conf.beat_schedule = {**celery.conf.beat_schedule, **BEAT_SCHEDULE}` |
| README "설계 판단" 에 "언어별 각각 커밋·부분 실패 허용" | README `### 05. 자정 배정은 언어별로 각각 커밋하고, 부분 실패를 허용한다` |

## 설계 판단 메모 (README 에 적은 것 요약)

- **언어별 각각 커밋.** ko·en 을 한 트랜잭션으로 묶으면 en 단어 고갈 같은 무관한
  사고가 ko 플레이어까지 "오늘의 퍼즐 없음"으로 만든다. 커밋 단위는 여전히
  `schedule_puzzles` 한 번이고, 순회 함수는 그 단위를 언어 수만큼 반복하는 바깥
  루프다.
- **순회를 태스크가 아니라 서비스 함수에.** 티켓 문구는 "Celery 태스크가 순회"
  지만, 태스크는 자기만의 Flask 앱(`celery_app.py`)을 캡처해 pytest 가 직접 부를
  수 없다(README "Celery Beat" 절에 이미 적힌 제약). "en 이 터져도 ko 는 배정된다"
  는 반드시 테스트로 지켜야 하는 동작이라 서비스 함수
  `ensure_today_puzzles_for_all_languages()` 에 뒀고, 태스크는 그걸 호출만 한다.
  태스크 배선은 `.run()`(ContextTask 를 안 거치는 원래 함수)에 서비스 함수를
  monkeypatch 해서 DB/Redis 없이 확인한다.
- **Beat 합치기를 태스크 모듈 쪽에.** 처음엔 `celery_app.py` 가
  `scheduled.BEAT_SCHEDULE` 을 읽어 합치게 했는데, 태스크 모듈이 먼저 import 되면
  (pytest 의 import 순서) `celery_app.py` 가 부분 초기화된 모듈을 보고
  `AttributeError: partially initialized module ... has no attribute
  'BEAT_SCHEDULE'` 가 난다. 그래서 태스크 모듈이 자기 스케줄을 직접 합치고
  `celery_app.py` 는 import 만 한다 — 두 import 순서 모두에서 세 항목이 등록되는
  걸 `python -c` 로 확인했다.
- **잔량 = "아직 한 번도 배정된 적 없는 단어" 수.** 쓴 단어도 `avoid_days` 가
  지나면 폴백으로 다시 나올 수 있지만, 운영자가 알고 싶은 건 "안 겹치는 새
  단어로 며칠을 버티나"다. 퍼즐이 (날짜, 언어)당 하나라 미사용 단어 하나 = 하루치.
- **잔량 알림 09:00 KST.** 스펙은 "매일 1회"만 정했다. 자정에 보내면 운영자가
  자는 사이에 오고, 09:00 이면 그날 안에 `flask seed-words` 로 채울 수 있다.

## 하지 않은 것 / 남은 것

- 마이그레이션 없음(스키마 변경 없음).
- `.env.example`·`docs/RELEASE.md` 변경 없음 — 새 설정값이 없다(임계 14일과
  09:00 은 코드 상수, 근거는 README·스펙 §A.12).
- 실제 Slack 전송은 하지 않았다. 모든 알림 테스트는 `post_webhook_message` 를
  monkeypatch 해서 문구와 호출 횟수만 본다(네트워크 없음).
- 실제 Beat 컨테이너가 자정을 넘기며 태스크를 큐에 넣는 건 확인하지 않았다 —
  README 가 이미 구분해 둔 한계 그대로다(설정값·스케줄 계산까지만).
