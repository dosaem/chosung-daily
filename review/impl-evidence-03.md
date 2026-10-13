# 티켓 03 구현 증거 — 서비스·API 언어 인지화

- 브랜치: `dosaem/t03-language-aware-services-api` (로컬 `main` = `72a2a3c` 위로 rebase)
- 커밋 5개: `d41a31a` 게스트 언어 선호 / `d320dae` 퍼즐 조회·캐시 / `8efda67` 통계·리더보드 /
  `90f05eb` 연속 기록·테스트 / `809a5d6` README. (+ 이 문서 커밋)
- 전용 테스트 자원: `TEST_DATABASE_URL=...chosung_daily_test_t03`,
  `TEST_REDIS_URL=redis://127.0.0.1:6379/5`,
  `TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t03_migrations`
  (공용 테스트 DB·Redis DB 1 은 건드리지 않았다)

## 실행한 검증

### 1. 전체 테스트 스위트 (rebase 후)

```
$ uv run pytest
tests/test_web.py ..                                                     [ 93%]
tests/test_word_model.py ..                                              [ 94%]
tests/test_word_service.py ...........                                   [100%]

======================== 208 passed in 71.41s (0:01:11) ========================
```

작업 시작 시점(티켓 02 머지 상태)의 기준선은 `146 passed` 였고, 그 뒤 로컬 `main` 에
머지된 티켓(19·20·21 등)을 포함한 현재 베이스 + 이 티켓의 신규 22개가 208 이다.
실패·skip·xfail 없음.

### 2. 신규·수정 테스트만

```
$ uv run pytest -q tests/test_guest_language.py tests/test_puzzle_language_api.py \
    tests/test_streak.py tests/test_rate_limit.py tests/test_mask.py
............................................                             [100%]
44 passed in 14.06s
```

### 3. 린트

```
$ uv run ruff check .
All checks passed!
```

### 4. 마이그레이션 head

이 티켓은 마이그레이션을 만들지 않았다(02 의 `4e72a4045fbc` 스키마로 충분).

```
$ ./scripts/check_migration_heads.sh
4e72a4045fbc (head)
OK: Alembic head 1개
```

### 5. 작업 트리

```
$ git status --short     # (이 문서 커밋 전)
 M tests/test_backup_restore.py
$ git log --oneline main..HEAD
809a5d6 docs(03): README API 표 갱신과 설계 판단 03 세 항목
90f05eb feat(03): 연속 기록 언어 무관 + 언어 인지 테스트와 today_puzzle 팩토리
8efda67 feat(03): 통계·리더보드 언어 분리와 ?language= 명시
d320dae feat(03): 오늘 퍼즐 조회 언어 인지화 — puzzle_id·language·mask·캐시 키 분리
d41a31a feat(03): 게스트 퍼즐 언어 선호 — 생성 시 지정·PATCH /me·stats 노출
```

UI 를 건드리지 않는 백엔드 티켓이라 `impeccable detect` / `audit.native` 는 완료
조건에 없고 돌리지 않았다(웹 화면 개편은 17·18, Flutter 는 22~31).

## 체크박스별 근거

| 티켓 체크박스 | 구현 | 증명하는 테스트/명령 |
|---|---|---|
| `POST /guests {puzzle_language?}` 기본 ko·미지원 값 `VALIDATION_ERROR`, `PATCH /me` 변경, `GET /me/stats` 에 `puzzle_language` | `app/schemas/guest.py`, `app/api/guests.py`, `app/api/me.py`, `app/services/guest_service.py`(`issue_guest(language)`, `change_puzzle_language`), `app/schemas/stats.py` | `tests/test_guest_language.py` 7개 — `test_guest_defaults_to_korean_when_language_is_omitted`, `test_guest_can_be_created_with_english_preference`, `test_unsupported_language_on_create_is_a_validation_error`(400 + 게스트 행 0), `test_patch_me_changes_puzzle_language`, `test_patch_me_rejects_unsupported_language_and_keeps_current`, `test_patch_me_requires_auth`, `test_me_stats_includes_puzzle_language` |
| `GET /puzzles/today` 가 선호 언어 퍼즐 + `puzzle_id`·`language`·`mask`·`length`, `chosung` 은 ko 현행 / en 은 `mask` 의 `r` 기반 문자열, 스키마에 명시 | `app/services/puzzle_service.py`(`get_today_puzzle_or_404(language)`, `_compat_chosung`), `app/schemas/puzzle.py`(필드별 주석), `app/utils/mask.py`(`mask_to_text`) | `tests/test_puzzle_language_api.py::test_korean_guest_gets_korean_puzzle_with_language_fields`(`chosung == "ㅅㄱ"` 그대로), `::test_english_guest_gets_english_puzzle`(`chosung == "_PPL_"`, `length == 5`), `::test_english_length_excludes_separators`(`harry potter` → `length == 11`, `"H_RRY P_TT_R"`), `::test_missing_puzzle_in_preferred_language_is_404`; 순수 함수는 `tests/test_mask.py` 3개(`mask_to_text` 의 빈 타일 미노출·ko 는 `extract_chosung` 과 동일) |
| Redis 키 `puzzle:{date}:{lang}`·`stats:{date}:{lang}`·`lb:{date}:{lang}` 분리, rate limit 키에는 언어 없음 | `app/services/puzzle_cache.py::_cache_key`, `app/services/puzzle_metrics.py::stats_key/_leaderboard_key`, `app/api/rate_limit.py` 는 **변경 없음**(`ratelimit:guess:{guest_id}`) | `tests/test_puzzle_language_api.py::test_puzzle_cache_keys_are_split_by_language`(ko 조회 후 `:en` 키는 None), `::test_stats_keys_are_split_by_language`(`hgetall stats:{date}:ko == {"1": "1"}`, `:en` 은 빈 dict, `lb` 동일), `tests/test_rate_limit.py::test_rate_limit_counter_survives_a_language_change`(10회 ko 제출 → `PATCH /me` en → 11번째 429) |
| `stats?language=`·`leaderboard?language=` 가 명시 언어(기본 게스트 선호)로 동작, 응답에 `language` | `app/api/puzzles.py::_requested_language`, `app/services/puzzle_metrics.py`, `app/schemas/stats.py`·`leaderboard.py` | `tests/test_puzzle_language_api.py::test_stats_are_counted_per_language`(ko 1 / en 0, 응답 `language`), `::test_leaderboard_is_separated_per_language`(언어별 entries 분리), `::test_unsupported_language_query_param_is_a_validation_error`(두 엔드포인트 모두 400) |
| 연속 기록 서비스 함수: `== today` no-op, `== yesterday` +1, 그 외 1. 같은 날 ko→en 시 streak 유지·`solved_count` +2 | `app/services/guess_service.py::_record_solve` | `tests/test_streak.py::test_solving_both_languages_on_the_same_day_keeps_streak_and_counts_twice`(어제 streak 3 → ko 정답 4 → en 정답도 4, `solved_count == 2`), 기존 `test_streak_increments_when_solved_on_consecutive_day`(+1), `test_streak_resets_when_a_day_was_skipped`(리셋) 그대로 통과 |
| 같은 날 ko/en 공존·언어 변경 후 조회/캐시 분리 테스트, 기존 테스트 통과, 픽스처 `today_puzzle(language)` | `tests/conftest.py::make_today_puzzle` + `today_puzzle` | `tests/test_puzzle_language_api.py::test_both_languages_coexist_on_the_same_day`(같은 날짜 두 퍼즐, 언어 변경 시 `puzzle_id` 가 바뀐다), `test_puzzle_cache_keys_are_split_by_language`; 기존 스위트 전체 통과(위 1번) |
| README "설계 판단" 2항목 + API 표 갱신 | `README.md` | `### 03. 연속 기록은 퍼즐 언어와 무관하다`(L441), `### 03. 캐시 키는 언어로 갈리고, rate limit 키는 안 갈린다`(L459), `### 03. 언어 인지 응답 — chosung 을 어떻게 채우는가`(L471), "API 목록" 표에 `PATCH /me`·`?language=`·today 응답 필드 반영 |

## 문구와 다르게 충족한 항목 (리뷰어 확인용)

1. **픽스처 이름**: 스펙·티켓 문구는 `today_puzzle(language)` 지만, 실제로는
   팩토리 픽스처를 **`make_today_puzzle(language, answer, hint, category)`** 로 추가하고
   기존 `today_puzzle`(ko 한 행)이 그걸 쓰게 했다. `today_puzzle` 자체를 호출형으로
   바꾸면 기존 테스트 11개 파일 35곳을 기계적으로 고쳐야 하고, 같은 파일을 건드리는
   04·05·06·07 과 머지 충돌만 늘어난다. 코디네이터에게 `ask` 로 확인받고 (A) 안으로 갔다.
2. **`chosung` 을 en 에서 `null` 로 두지 않았다**: 티켓이 "mask 의 `r` 글자 기반
   문자열(또는 null)" 중 하나를 허용하는데, 문자열을 골랐다. 필드 타입이 언어에 따라
   바뀌면 `chosung` 을 그대로 그리는 옛 클라이언트가 en 에서 `null` 을 출력한다.
   근거는 README "03. 언어 인지 응답" 에 적었다.
3. **`length` 의미를 `mask` 기준(구분자 제외)으로 바꿨다**: 같은 응답 안의 `mask` 와
   숫자가 안 맞으면 클라이언트가 타일을 몇 개 그릴지 알 수 없어서 스펙 §A.2 정의를
   따랐다. 다만 **제출 쪽 길이 검증은 이 티켓에서 안 건드렸다**(티켓 04 범위) —
   그래서 "공백·하이픈이 들어간 정답" 에 대해서는 04 머지 전까지 `length`(구분자 제외)와
   제출 검증(`len(word.answer)`, 구분자 포함)이 어긋난다. 현행 시드 단어
   (`data/seed_words.csv` 21행)에는 공백·하이픈이 들어간 정답이 없어서 지금 운영 중인
   ko 퍼즐에는 영향이 없다. 04 가 같은 기준으로 합류시킨다.

## 범위 밖이라 손대지 않은 것

- `puzzle_maintenance_service`(자정 배정·통계 flush)는 현행대로 **ko 키 하나만** 본다.
  언어별 순회·언어별 커밋은 티켓 05 가 한다 — 코드 주석에도 그렇게 적었다.
- 제출 요청의 `puzzle_id` 동봉·`PUZZLE_CHANGED`·`attempts` 이력·en 대소문자/구분자
  정답 비교는 티켓 04. `hint_unlocked` 는 06. 리더보드 `display`/`me`/`guest_id` 제거는 07.
- 웹 프론트(`web/static/app.js`)는 안 건드렸다. 응답 변화가 **필드 추가뿐**이고
  `chosung`·`length` 는 ko 에서 현행 값 그대로라 현재 웹이 그대로 돈다.

## 로컬 `main` 위 rebase 때 고친 충돌 1건

티켓 21(`72a2a3c`)이 머지되며 들어온 `tests/test_backup_restore.py::
test_restarting_the_app_does_not_clear_the_puzzle_cache` 가 `_cache_key(date)` /
`get_cached_puzzle(date)` 를 옛 시그니처로 부른다. 언어 인자를 넘기고 캐시 JSON 에
`mask` 를 넣어 통과시켰다(검증 내용은 그대로 — `restore.sh` 의 `puzzle:*` 스캔은 새
키 포맷도 그대로 잡는다).

```
$ uv run pytest -q tests/test_backup_restore.py
........................................                                 [100%]
40 passed in 5.16s
```
