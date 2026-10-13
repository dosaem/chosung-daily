# 티켓 02 구현 증거 — 퍼즐 언어 마이그레이션·모델·가림 포맷

- 브랜치: `dosaem/t02-puzzle-language-migration-mask` (로컬 `main` **491418f** 위.
  `git rebase main` 은 no-op 이었다 — main 이 이미 조상)
- 커밋 3개, 변경 19파일 (+1003 / -37)
- 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t02`, Redis DB **4**,
  마이그레이션 왕복용 별도 DB `chosung_daily_test_t02_migrations`
  (`TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL` 로 지정).
  공용 `chosung_daily_test`·Redis 1 과 다른 워커의 DB 는 건드리지 않았다.
- 외부 서비스 호출 0건. NAS 접속·배포·`git push` 없음. UI 변경 없음(스키마·모델·순수
  함수 티켓이라 `impeccable detect` 대상 화면이 없다). 시크릿 값은 어떤 파일에도 쓰지
  않았다 — 추가한 설정은 이름만: `TEST_MIGRATION_DATABASE_URL`.

## 1. 실행한 명령과 출력

### 전체 테스트 스위트

```
$ TEST_DATABASE_URL=...chosung_daily_test_t02 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/4 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t02_migrations \
  uv run pytest -q
........................................................................ [ 49%]
........................................................................ [ 98%]
..                                                                       [100%]
146 passed in 69.06s (0:01:09)
```

작업 시작 시점(`main` = 491418f) baseline 은 **108 passed** → **신규 38개**:
`test_mask.py` 17, `test_puzzle_language_model.py` 11, `test_migrations.py` 4,
`test_word_service.py` 에 6개 추가(5 → 11). **실패·skip·xfail 0건.**

### 린트

```
$ uv run ruff check .
All checks passed!
```

### 마이그레이션 head (1줄)

```
$ FLASK_APP=wsgi.py uv run flask db heads
4e72a4045fbc (head)

$ ./scripts/check_migration_heads.sh
4e72a4045fbc (head)
OK: Alembic head 1개
```

### 마이그레이션 왕복 (별도 DB, `flask db` 서브프로세스)

```
$ uv run pytest tests/test_migrations.py -q
....                                                                     [100%]
4 passed in 14.36s
```

실제 DDL 결과(수동 확인, `SHOW CREATE TABLE`):

```
daily_puzzle:  UNIQUE KEY `uq_daily_puzzle_date_language` (`puzzle_date`,`language`)
               `language` enum('ko','en') NOT NULL DEFAULT 'ko'
daily_stats:   PRIMARY KEY (`puzzle_date`,`language`)
```

downgrade 후:

```
daily_puzzle:  UNIQUE KEY `puzzle_date` (`puzzle_date`)      ← 옛 스키마 복귀
daily_stats:   PRIMARY KEY (`puzzle_date`)
word:          language·mask 컬럼 없음
```

### 테스트가 실제로 결함을 잡는지 (돌연변이 확인 1회)

마이그레이션의 데이터 단계(`_fill_word_masks()`)를 `pass` 로 바꿔 돌렸다:

```
FAILED tests/test_migrations.py::test_korean_data_survives_downgrade_and_upgrade
FAILED tests/test_migrations.py::test_upgrade_fills_mask_for_rows_created_before_the_column_existed
2 failed, 2 passed in 14.44s
```

→ 원복 후 다시 4 passed. 왕복 테스트가 "데이터 단계 없음"을 잡는다.

## 2. 체크박스별 근거

| 티켓 체크박스 | 증명하는 테스트/명령 |
|---|---|
| Alembic 마이그레이션 1개: `Word.language`(기본 ko), `DailyPuzzle (puzzle_date, language)` 유니크, `Guest.puzzle_language`(기본 ko), `Word.mask`(JSON), `chosung` 유지, `DailyStats` 키에 언어 | `migrations/versions/4e72a4045fbc_*.py` / `tests/test_migrations.py::test_downgrade_removes_the_language_columns`, `::test_both_languages_fit_on_the_same_date_after_upgrade` + 위 `SHOW CREATE TABLE` 출력. `chosung` 은 그대로 NOT NULL 로 남아 있다(`tests/test_puzzle_language_model.py::test_english_word_keeps_chosung_column_filled`) |
| 왕복 테스트 `tests/test_migrations.py`: 별도 DB + `flask db` 서브프로세스, ko 단어·퍼즐·시도 동일 조회, conftest `create_all` 경로와 분리 | `tests/test_migrations.py::test_korean_data_survives_downgrade_and_upgrade` (word·daily_puzzle·attempt·guest·daily_stats 전체 스냅샷 비교). `app` 픽스처를 쓰지 않고 `TEST_MIGRATION_DATABASE_URL` DB 에서 `python -m flask db upgrade/downgrade` 를 `subprocess` 로 돌린다 |
| 가림 순수 함수: `[{t: r\|h\|s, c}]`, ko 초성(현행 로직 이동), en 모음 `h`·공백/하이픈 `s`·나머지 `r`, `length` 는 `s` 제외 | `app/utils/mask.py` / `tests/test_mask.py` 13개 — `apple`→`_PPL_`, `harry potter`(공백 `s`, length 11), `spider-man`(하이픈 `s`, length 9), `APPLE`==`apple`, 숫자 `r`, ko 초성·독립 자모·비한글 `h`, 빈 입력 |
| ko 초성 "현행 로직 이동" | `app/utils/chosung.py` 의 한글 계산을 글자 단위 `syllable_chosung()` 으로 꺼내 `build_mask` 가 그걸 쓴다(초성 계산 한 벌). `tests/test_mask.py::test_korean_mask_matches_the_existing_chosung_column_logic` 가 5개 입력에서 ko 가림 == 기존 `extract_chosung` 결과임을 고정 |
| 단어 저장 서비스 함수가 저장 시 `mask` 계산 | `tests/test_word_service.py::test_seed_words_defaults_to_korean_and_fills_mask`, `::test_seed_words_reads_language_column`, `::test_add_word_from_book_defaults_to_korean_and_fills_mask`, `::test_add_word_from_book_can_register_an_english_title` + `tests/test_puzzle_language_model.py` 의 insert/update 재계산 3개 |
| 기존 ko 단어는 마이그레이션 데이터 단계에서 `mask` 채워짐 | `tests/test_migrations.py::test_upgrade_fills_mask_for_rows_created_before_the_column_existed` (언어·가림 컬럼이 없던 시절 행을 넣고 upgrade → `language='ko'`, `mask == build_mask(KO, answer)`) + 위 돌연변이 확인 |
| 기존 테스트 전부 ko 기본값으로 통과 | `uv run pytest -q` → 146 passed (baseline 108 전부 포함, 실패 0). 아래 §3 에 기존 테스트 수정 내역 |
| 머지 직전 `flask db heads` 1개 | `./scripts/check_migration_heads.sh` → `OK: Alembic head 1개` |
| README "설계 판단" 에 2개 항목 추가 | `README.md` `### 02. 퍼즐 언어 모델 — expand–contract 대신 마이그레이션 1개`, `### 02. 가림(mask) 포맷 — 언어마다 다른 렌더링 코드를 만들지 않기` (절 끝에 번호순으로 덧붙임) |

## 3. 숨기지 않을 것들

### 기존 테스트 1개 파일을 고쳤다 (4+1줄, assert 내용은 그대로)

`DailyStats` 키에 언어를 넣으라는 체크박스 때문에 PK 가 `(puzzle_date, language)` 가 됐고,
그러면 `db.session.get(DailyStats, yesterday)` 는 SQLAlchemy 가 거부한다
(`Incorrect number of values in identifier to formulate primary key`). 그래서
`tests/test_puzzle_maintenance.py` 의 조회 4줄을 `(yesterday, PuzzleLanguage.KO)` 로,
삽입 1줄에 `language=` 를 더했다. **단언(assert) 내용·개수는 바뀌지 않았다** — 복합키
조회 형식만 맞춘 기계적 변경이고, 체크박스의 직접적 귀결이다.

같은 이유로 `flush_daily_stats_for_yesterday()` 는 이제 ko 행에 기록한다. Redis 통계
키(`stats:{date}`)가 아직 언어별로 갈리지 않았기 때문이고, 그 분리는 "자정 배정·캐시"
티켓 몫이다(스펙 §A.1 티켓 분할 지침).

### 다음 티켓으로 넘기는 것 (이 티켓 범위 밖, 의도적)

- **퍼즐 배정은 아직 언어를 모른다.** `puzzle_schedule_service._pick_word()` 가 언어
  필터 없이 단어를 고르므로, 운영자가 en 단어를 넣고 나면 ko 퍼즐에 en 단어가 뽑힐 수
  있다. 자정 배정 언어 인지화는 스펙 §A.1 의 분할대로 다음 티켓 담당이라 손대지 않았다.
  지금은 en 단어가 0개라 실제 영향이 없다.
- **응답·캐시·리더보드 필드**(`mask` 노출, `puzzle:{date}:{lang}` 등)는 전부 API 티켓.
  `app/schemas/puzzle.py` 의 `chosung` 필드와 `puzzle_cache` 키는 그대로 뒀다.
- `data/seed_words.csv` 는 `language` 열 없이 그대로 뒀다 — 없으면 ko 로 읽는다.

### 범위에 대해 판단한 것

- CSV `language` 열(없으면 ko)과 `add_word_from_book(language=...)` 을 추가했다.
  체크박스가 "단어 저장 서비스 함수"를 지목하는데, 언어를 못 넣으면 en 단어를 만들 수
  있는 경로가 하나도 없어 가림의 en 분기가 저장 경로에서 검증되지 않는다. 관리자 CSV
  업로드 화면은 건드리지 않았다(별도 티켓). 중복 판정 키에도 언어를 넣었다 — 철자가
  같고 뜻이 다른 ko/en 단어(예: "plan")를 한 단어로 묶으면 안 된다.
- 가림 계산을 호출하는 자리는 `Word` 의 `before_insert`/`before_update` 이벤트다
  (기존 `chosung` 계산이 쓰던 그 자리). 저장 경로가 여러 개(CLI 시드·책 등록·관리자
  CRUD)라 서비스 함수마다 계산을 복사하는 대신 모델 한 곳에 뒀다. 이벤트 안에서
  `language` 기본값을 직접 넣는데, 컬럼 `default` 는 INSERT 문을 만들 때 적용돼서
  `before_insert` 보다 늦고 그러면 `build_mask` 가 `None` 을 받는다.
- 마이그레이션이 `app.utils.mask.build_mask` 를 import 한다. 가림 규칙을 마이그레이션
  안에 복사하면 두 벌이 생기고, 어긋나면 "저장할 때와 마이그레이션할 때 문제가 다르게
  보이는" 버그가 된다.
- downgrade 는 en 데이터(시도→퍼즐→단어→통계 순)를 지운다. 옛 스키마가 영어를 표현할
  수 없어서(퍼즐 유니크가 날짜뿐, 통계 PK 도 날짜뿐) 되돌리기는 "ko 전용 상태로의
  복귀"다. 마이그레이션 파일 주석에 적었다.

### CI·문서에 손댄 곳

- `.github/workflows/ci.yml`: 왕복 테스트용 DB 를 root 로 만들어 주는 스텝 1개
  (테스트 유저에겐 `CREATE DATABASE` 권한이 없다). 기존 스텝은 안 건드렸다.
- `.env.example`: 파일 끝에 `[02]` 주석 + `TEST_MIGRATION_DATABASE_URL=` (빈 값).
- `README.md`: "실행 방법" 에 그 DB 만드는 방법, "설계 판단" 끝에 `### 02.` 2개.
  API 표는 건드리지 않았다(이 티켓은 응답을 바꾸지 않는다).

## 4. 되돌아보며

왕복 테스트가 값을 한 번 했다. 처음에 `docker exec mysql -e` 로 손으로 한글 데이터를
넣고 upgrade 를 돌렸더니 가림이 전부 빈 타일로 나왔다 — 컨테이너 안 mysql 클라이언트의
기본 문자셋(latin1)이 한글을 이중 인코딩해서 넣은 거였고, 마이그레이션 코드는 멀쩡했다.
테스트가 SQLAlchemy(utf8mb4)로 데이터를 넣기 때문에 같은 함정에 빠지지 않는다. 손으로
확인할 때는 `--default-character-set=utf8mb4` 를 붙여야 한다.
