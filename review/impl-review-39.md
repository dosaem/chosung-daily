# 티켓 39 최종 리뷰 — 단어 후보 CSV + 검증 스크립트 (라운드 1)

브랜치 `dosaem/t39-word-candidates-csv`, 커밋 `e0c68fc`·`ac30897`·`3effefe`·`622a0ac`(로컬 `main` `8de470b` 위, `git status` clean).
리뷰어가 직접 돌린 것: ruff, 새 테스트, 전체 스위트(전용 DB `chosung_daily_test_t39` / Redis 13), `flask db heads`,
검증 스크립트, `import_word_rows` 드라이런 재현, 후보 CSV 327행 전부 직접 읽기(독립 검사 스크립트 + 눈으로).
정답은 코디네이터 지시대로 이 문서에 5행 이내로만 인용한다.

## 1. 직접 확인한 결과

| 항목 | 명령 | 결과 |
|---|---|---|
| ruff | `uv run ruff check .` | `All checks passed!` |
| 새 테스트 | `uv run pytest tests/test_check_word_csv.py -q` | `17 passed in 0.40s` |
| 전체 스위트 | `uv run pytest -q` (TEST_DATABASE_URL=…`chosung_daily_test_t39`, TEST_REDIS_URL=…`/13`, TEST_MIGRATION_DATABASE_URL=…`_t39_migrations`) | `1526 passed in 1019.41s (0:16:59)`, 종료 코드 0, 실패·에러·건너뜀 0 |
| 마이그레이션 | `uv run flask db heads` | `b1c7d4e0a932 (head)` 1줄 (이 티켓은 마이그레이션 없음) |
| 검증 스크립트 | `uv run python scripts/check_word_csv.py data/word-candidates/ko-general-01.csv data/word-candidates/en-general-01.csv` | 두 파일 `위반 0건`, 종료 코드 0 |
| 드라이런 재현 | 전용 DB 에 `create_all` → seed 20 → ko → en `import_word_rows` → `drop_all` | seed 추가 20 / ko 162행 전부 `added` / en 165행 전부 `added` / 오류 0, ko Word 182·en 165 — 증거 문서 수치와 일치 |
| 후보 파일 커밋 여부 | `git log -p main..HEAD` 에서 `data/word-candidates/` 와 표본 정답 grep | CSV 는 어느 커밋에도 없음. 정답 평문은 `review/impl-evidence-39.md` 표본 40행(티켓이 요구한 20행×2)에만 있음 |
| 독립 규칙 검사(리뷰어 스크립트) | ko: `[가-힣]{2,5}`·힌트 1~60자·따옴표/쉼표·정답 음절 포함·파일 내 중복·seed 중복 / en: `[a-z -]{2,12}`·구분자 ≤1·모음 ≤50%·정답(복수형) 낱말 포함·중복·seed | 양쪽 0건. `*.difficulty.tsv` 줄번호가 CSV 2~끝과 1:1, 분포 ko 64/64/34·en 64/64/37 (증거와 일치) |

## 2. 티켓 체크박스별 충족 여부

| 체크박스 | 판단 | 근거 |
|---|---|---|
| `ko-general-01.csv` ≥150행, ko 규칙 | 충족 | 162행, 전부 `ko,general`. 독립 검사 0건. 162행을 눈으로 읽음: 인명·지명·브랜드 없음, 유행어 없음(외래어 일상어 — 치킨·피자·버스·소파류 — 는 포함, 프롬프트 골자 "일상어" 범위 안). 힌트는 전부 뜻·용도·분류 설명 |
| `en-general-01.csv` ≥150행, en 규칙 | 충족(규칙상) | 165행, 전부 `en,general`. 독립 검사 0건, 두 단어 6개(구분자 1개씩), 모음 비율 최대 50%(`ice cream` 4/8). 고유명사 없음. 단, 티켓 규칙 밖의 품질 문제 D-39-1 참고 |
| 난이도 4:4:2 + 20행 표본·근거 | 충족 | tsv 분포 ko 4.0:4.0:2.1, en 3.9:3.9:2.2. 표본 20행×2 와 기준 설명이 증거 §2·§3 에 있음. 파일이 easy→medium→hard 블록 순인데 배정은 `puzzle_schedule_service._pick_word` 가 `random.choice` 라 순서가 출제 순서에 영향 없음(확인) |
| `scripts/check_word_csv.py` — `parse_word_input` 재사용, DB 없이, `줄번호: 사유`, 종료 코드 1, 0건 증거 | 충족 | 코드 확인: `parse_word_input`·`missing_csv_columns`·`duplicate_csv_columns`·`CSV_EXTRA_FIELD_KEY` 재사용, 헤더 공백 처리까지 `import_word_rows` 와 같음. `app` 픽스처 없이 테스트가 돎. 실제 0건 출력은 §1 |
| `tests/test_check_word_csv.py` — 5케이스 + 종료 코드 0, 실제 후보 파일 미사용 | 충족 | 정상(ko·en) / 힌트 정답 포함(ko 음절·en 단어·복수형) / 길이 초과(정답 ko·en, 힌트) / 중복(파일 내·seed) / 잘못된 category / `main` 종료 코드 0·1 / 없는 파일. 전부 `tmp_path` 와 커밋된 `data/seed_words.csv` 만 읽음. 과한 mock 없음, 실제 함수 호출 |
| `import_word_rows` 드라이런 ≥150·오류 0 | 충족 | 리뷰어가 전용 DB 에서 재현(§1), 증거 수치와 동일 |
| `book_title` 후보 | 충족(건너뜀 조건 성립) | `search_books` 는 `KAKAO_REST_API_KEY`/`ALADIN_TTB_KEY` 없으면 빈 결과(`app/services/book_lookup_service.py` 확인). 증거 §6 과 `docs/RELEASE.md` 39. 에 "사람이 `flask search-books` 로 넣는다" 기록됨. Google Books 는 키 없이 동작하지만 외부 호출 금지 제약으로 안 부른 판단도 타당 |
| `.gitignore`·README 단락·`docs/RELEASE.md` `### 39.` | 충족 | `.gitignore` 에 `data/word-candidates/`(이유 주석), README "운영: 단어 CSV 업로드" 절 끝 "올리기 전 로컬 검증" 한 단락 + 예시, RELEASE.md 맨 끝 `### 39.` 4단계(훑어보기→삭제→업로드→`/admin/schedule` ko·en 30일, en 심사 전) |
| 테스트 전체 통과, ruff 0건 | 충족 | §1 |
| (0) 번호 정리 38→39, spec 리더보드 표기 정정 | 충족 | 첫 커밋 `e0c68fc` 가 `git mv`(similarity 95%) + 본문 38→39 4곳, spec §D0·Further Notes 의 단어 CSV 38→39, user-todo 6행·기록. spec API 표 `display`→`anon_tag`, 설명 "`guest.id % 0x10000` 16진 4자리, 접두사는 웹·앱" 은 main 의 `puzzle_metrics.anon_tag`(`ANON_TAG_MODULUS = 0x10000`, `:04x`)·`schemas/leaderboard.py` 와 일치. 리더보드 38 참조는 그대로. 단 D-39-2 |

## 3. 결함

### D-39-1 (MINOR) — en 힌트 9행이 정답의 구성 낱말을 그대로 써서 가려진 모음을 알려 준다

- 파일: `data/word-candidates/en-general-01.csv` 30, 31, 41, 68, 79, 118, 144, 146, 160행 (리뷰어 스캔: 힌트 낱말 중 길이 3 이상이 정답의 부분 문자열인 것 + `keys`/`grams` 같은 복수형)
- 재현: 예) 31행 — 플레이어가 보는 문제는 `B_THR__M`, 힌트에 `room` 이 그대로 있어 `R__M` 네 칸 중 가려진 모음 두 개가 공짜다. 144행은 힌트의 `night` 가 정답 뒤 다섯 글자다
- 기대: 티켓은 en 힌트 규칙을 "정답 단어(와 복수형) 미포함" 까지만 뒀고 스크립트는 그 규칙을 정확히 구현했으므로 **티켓 위반은 아니다**. 그러나 ko 쪽 규칙("정답 음절 하나도 미포함")의 취지는 가림 단서 누출 방지이고, en 복합어의 구성 낱말은 같은 종류의 누출이다. 증거 §1 은 "정답과 4자 이상 접두를 공유하는 힌트 낱말을 훑어 0건" 이라 적었는데 접두만 봐서 접미(`-room`·`-night`·`-card`·`-ball`·`-brow`·`-land`)는 걸러지지 않았다
- 심각도 MINOR 인 이유: 사람 검수 단계(RELEASE.md 39. "마음에 안 드는 행 삭제")가 있고 9행을 지워도 156행이 남아 150 조건을 만족한다. 코디네이터가 사용자에게 파일을 전달할 때 이 9행 번호를 같이 알려 주면 된다

### D-39-2 (MINOR) — spec Further Notes 의 티켓 범위 `01~38` 이 39 추가 뒤에도 그대로

- 파일: `.scratch/store-launch/spec.md:352` — `- 티켓: \`.scratch/store-launch/issues/01~38\`(의존성 순 …` 같은 줄 뒤에 "2026-10-15: 39 단어 후보 CSV 생성 … 추가" 를 적었으므로 범위는 `01~39` 여야 한다
- 재현: `ls .scratch/store-launch/issues/ | tail -1` → `39-word-candidates-csv.md`, 같은 줄의 범위 표기는 38
- 티켓 0번 지시("단어 후보 CSV 를 가리키는 38 도 39 로")의 직접 대상은 아니지만 같은 줄을 고치면서 남긴 불일치라 적는다. 다음 `.scratch` 수정 티켓이나 코디네이터가 한 글자 고치면 된다

## 4. 참고 (결함 아님)

- 증거 문서 §3 의 표본 40행은 티켓이 요구한 것이고 "업로드 전 그 줄 번호만 지우면 공개 레포에 정답이 하나도 안 남는다" 는 완화책도 적혀 있다. 코디네이터가 사용자에게 파일을 전달할 때 이 선택지를 알려 줄 것.
- `_en_hint_leak_reasons` 는 힌트만 소문자화하고 정답은 그대로 비교한다. 대문자 정답은 `_en_answer_reasons` 가 이미 거부하므로 결과엔 영향 없다.
- `load_seed_keys` 의 중복 키가 (언어, 정답, 카테고리) 라 seed 의 `book_title` 정답과 같은 `general` 정답은 통과한다. 업로드(`import_word_rows`)도 같은 키를 쓰므로 "로컬 통과·업로드 중복" 불일치는 없다. 현재 후보 파일엔 해당 없음.
- en 정답에 형용사(`electric`·`magnetic`)·수사(`thousand`)가 몇 개 있다. README en 프롬프트는 "2~12자 단어" 만 요구하고 명사 제한이 없어 규칙 위반은 아니다. 취향이면 검수에서 지운다.
- ko 2글자 정답이 108/162 다. 규칙(2~5글자) 안이고 난이도 기준 설명(§2)과도 맞다.
- 전체 스위트 실행 시간은 공용 MySQL 을 다른 워커와 같이 써서 길다. 실패·건너뜀은 없다(§1).

판정: PASS
