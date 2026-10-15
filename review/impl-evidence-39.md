# 티켓 39 구현 증거 — 단어 후보 CSV + 검증 스크립트

브랜치 `dosaem/t39-word-candidates-csv`. 전용 테스트 자원:
DB `chosung_daily_test_t39` / `chosung_daily_test_t39_migrations`, Redis DB 13.

```sh
export TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t39?charset=utf8mb4"
export TEST_REDIS_URL="redis://localhost:6379/13"
export TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t39_migrations?charset=utf8mb4"
```

## 0. 번호 정리 (사용자 결정 2026-10-15)

38 번은 이미 머지된 "리더보드 익명 이름 언어 중립화"(머지 `1172b9b`, `review/impl-review-38.md`)가
쓰고 있어서 이 티켓을 39 로 옮겼다. 첫 커밋 `e0c68fc`:

- `git mv .scratch/store-launch/issues/38-word-candidates-csv.md → 39-word-candidates-csv.md`,
  본문의 자기 번호(제목·`review/impl-evidence-NN.md`·`### NN.`) 38 → 39
- `spec.md` §D0 "후보 생성은 티켓 38" → 39, Further Notes 의 "2026-10-15: 38 단어 후보 CSV 생성" → 39
  (리더보드 38 참조와 US 38 은 건드리지 않았다)
- `user-todo.md` 6 행의 티켓 번호·파일명 → 39, 변경 기록에 "38 은 리더보드 익명 이름이 이미 사용" 추가
- `spec.md` §A' 리더보드 표기를 머지된 결과로 정정: 응답 필드 `display` → `anon_tag`,
  표 아래 설명을 "서버는 언어 중립 태그만 주고 `게스트 #` / `Guest #` 접두사는 웹·앱이 자기 UI
  언어로 붙인다(README 38.)" 로 바꾸고 "응답에 `display` 는 없다" 를 명시

## 1. 산출물 (커밋되지 않는 파일)

`.gitignore` 에 `data/word-candidates/` 를 넣었으므로 아래 파일들은 레포에 없다 —
코디네이터가 사용자에게 따로 전달한다.

| 경로 | 행 수(헤더 제외) | 검증 |
|---|---|---|
| `data/word-candidates/ko-general-01.csv` | **162** (`ko,general`) | 위반 0건 |
| `data/word-candidates/en-general-01.csv` | **165** (`en,general`) | 위반 0건 |
| `data/word-candidates/ko-general-01.difficulty.tsv` | 162 | 줄번호→난이도 기록 |
| `data/word-candidates/en-general-01.difficulty.tsv` | 165 | 줄번호→난이도 기록 |

`*.difficulty.tsv` 는 CSV 포맷에 난이도 열이 없어서(`language,category,answer,hint` 고정)
따로 뺀 기록이다. 사람이 행을 지울 때 "어려운 것부터 보기" 에 쓰고, 업로드에는 쓰지 않는다.
`docs/RELEASE.md` "### 39." 에 사용법을 적었다.

### 검증 스크립트 실행 결과 (0건)

```
$ uv run python scripts/check_word_csv.py \
    data/word-candidates/ko-general-01.csv data/word-candidates/en-general-01.csv
data/word-candidates/ko-general-01.csv: 위반 0건
data/word-candidates/en-general-01.csv: 위반 0건
$ echo $?
0
```

첫 생성에서는 ko 12건이 잡혔고(전부 "힌트에 정답 음절이 들어 있습니다" — 예: `고구마` 힌트의
"달**고**", `소나무` 힌트의 "바늘잎 **나무**"), 그 12행의 힌트를 고쳐 0건으로 만들었다.
en 은 첫 생성부터 0건이었다. 생성 과정에서 규칙에 걸려 버린 후보: `referee`(모음 4/7 = 57%),
`traffic light`(13자 > 12자).

스크립트가 못 잡는 것도 두 가지 더 걸렀다:

- **철자가 영/미로 갈리는 en 정답** — 플레이어가 다른 쪽 철자를 치면 틀린 답이 된다.
  `theatre` → `cinema`, `neighbour` → `stranger` 로 바꿨고 힌트의 `colour`·`vapour`·`woollen`
  도 흔한 쪽으로 통일했다.
- **힌트의 어간 누출** — `painting` 힌트에 `paint`, `weekend` 힌트에 `week`, `afternoon`
  힌트에 `after` 가 있었다. 낱말이 정확히 같지 않아 스크립트는 통과시키지만 사실상 답이다.
  정답과 4자 이상 접두를 공유하는 힌트 낱말을 따로 훑어 3건을 고쳤고, 다시 훑어 0건이다.
  (이 규칙은 스크립트에 넣지 않았다 — 뜻·분류를 설명하려면 어간이 같은 말이 힌트에 정당하게
  들어갈 수도 있어서, 기계로 거부하면 멀쩡한 행을 버린다. 티켓이 정한 규칙도 "정답 단어와
  그 복수형" 까지다. 생성할 때 사람이 한 번 훑는 쪽을 택했다.)

### `import_word_rows` 드라이런 (테스트 DB, 테스트 코드로 고정하지 않음)

후보 CSV 가 레포에 없으므로 CI 가 읽을 수 없다 → 테스트가 아니라 로컬 1회 확인이다.
운영 순서와 같게 `data/seed_words.csv`(20행) 를 먼저 넣고 그 위에 후보를 올렸다.

```
DB: chosung_daily_test_t39
seed_words.csv: 추가 20, 건너뜀 0
data/word-candidates/ko-general-01.csv: 총 162행 / 추가 162 / 중복 0 / 오류 0
data/word-candidates/en-general-01.csv: 총 165행 / 추가 165 / 중복 0 / 오류 0
ko Word 행 수: 182 (= 하루 한 문제 기준 182일치)
en Word 행 수: 165 (= 하루 한 문제 기준 165일치)

가림 표본 (플레이어가 보는 문제):
  ko ㅅㄱ  ← 빨갛고 아삭한 과일        (seed 의 사과)
  ko ㅎㄱ  ← 공부하러 가는 곳
  ko ㅋㅍㅌ  ← 코딩할 때 쓰는 기계
  en W_ND_W  ← an opening in a wall fitted with glass
  en T_BL_  ← a flat top on four legs for meals
  en CH__R  ← a single seat with a back
```

추가 ≥150·오류 0 충족. 스펙 §D0 의 "ko/en 각 ≥120", "심사 전 en 30일 배정" 둘 다
여유가 있다(en 165일치). 확인 뒤 `db.drop_all()` 로 테이블을 지웠다 — 공용 테스트 DB 는
건드리지 않았다.

## 2. 난이도 분포

| 파일 | easy | medium | hard | 합 | 비율 | 목표 4:4:2 |
|---|---|---|---|---|---|---|
| `ko-general-01.csv` | 64 | 64 | 34 | 162 | 4.0 : 4.0 : 2.1 | 충족 |
| `en-general-01.csv` | 64 | 64 | 37 | 165 | 3.9 : 3.9 : 2.2 | 충족 |

난이도를 가른 기준 — **가림을 보고 정답 후보가 몇 개나 떠오르는가**다.

- **ko** (초성 가림): `easy` = 2~3글자 고빈도 구체 명사(사물·음식·자연). 초성 2~3칸이면
  후보가 사실상 하나다(`ㅊㅅ` → 책상). `medium` = 3~4글자 복합명사·집안일·생물.
  초성이 늘어 후보가 줄긴 하지만 힌트를 읽어야 고른다(`ㅅㅅㄱ` → 손수건/손수레).
  `hard` = 추상어(돈·절차·계약)와 덜 쓰는 도구 이름. 초성만으로는 범주조차 안 좁혀져
  힌트가 사실상 유일한 단서다(`ㅇㅈ` → 이자/임자/옹자…).
- **en** (모음 가림): `easy` = 5~7자 고빈도 명사. 자음 뼈대가 거의 유일해(`W_ND_W` → window)
  바로 읽힌다. `medium` = 6~9자 일상어. 자음 뼈대 후보가 둘 셋 생긴다
  (`B_TT_N` → button/batten/bitten). `hard` = 8~12자·두 단어·몸/과학 어휘.
  긴 자음열은 오히려 읽기 어렵고(`TMPRTR` → temperature) 두 단어는 구분자 위치까지 봐야 한다.

줄 번호 → 난이도는 `*.difficulty.tsv` 에 1:1로 들어 있다. CSV 는 easy → medium → hard
순으로 쓰여 있어서, 사람이 "뒤쪽부터 지우면 쉬워진다" 로 난이도를 조절할 수 있다.

## 3. 표본 20행

> 이 20행은 레포에 평문으로 남는 유일한 정답들이다(티켓의 "20행 표본" 요구). 공개 레포에
> 아무 정답도 남기지 않으려면 **업로드 전에 이 줄 번호의 행만 지우면 된다** — 그래도 양쪽
> 다 140행 이상 남는다.

### `ko-general-01.csv`

| 줄 | 난이도 | 정답 | 힌트 |
|---|---|---|---|
| 2 | easy | 책상 | 공부할 때 앞에 두는 가구 |
| 10 | easy | 가방 | 물건을 담아 어깨에 메는 것 |
| 19 | easy | 수박 | 여름에 먹는 크고 둥근 과일 |
| 27 | easy | 마늘 | 알싸한 맛을 내는 향신 재료 |
| 36 | easy | 공원 | 나무와 길이 있어 산책하는 넓은 곳 |
| 44 | easy | 농구 | 높은 그물에 공을 넣는 경기 |
| 53 | easy | 가족 | 함께 사는 식구 |
| 61 | easy | 코끼리 | 상아와 큰 귀를 가진 아주 무거운 짐승 |
| 70 | medium | 전자레인지 | 음식을 짧게 데우는 작은 조리 기계 |
| 78 | medium | 숟가락 | 밥이나 국을 떠먹는 도구 |
| 87 | medium | 주차장 | 탈것을 세워 두고 자리를 빌리는 공간 |
| 95 | medium | 뿌리 | 흙 속으로 뻗어 물을 빨아들이는 부분 |
| 104 | medium | 다람쥐 | 볼에 먹이를 넣고 나무를 타는 작은 짐승 |
| 112 | medium | 소금 | 짠맛을 내는 흰 가루 |
| 121 | medium | 국수 | 가늘고 길게 뽑은 반죽을 삶아 먹는 음식 |
| 129 | medium | 담요 | 몸에 덮는 두툼한 천 |
| 138 | hard | 월급 | 일한 값으로 달마다 받는 돈 |
| 146 | hard | 출입구 | 드나드는 문이 있는 자리 |
| 155 | hard | 현미경 | 아주 작은 것을 크게 보는 기구 |
| 163 | hard | 목도리 | 추울 때 고개 아래에 감는 긴 천 |

### `en-general-01.csv`

| 줄 | 난이도 | 정답 | 힌트 |
|---|---|---|---|
| 2 | easy | window | an opening in a wall fitted with glass |
| 11 | easy | doctor | a person who treats the sick |
| 19 | easy | evening | the hours after sunset |
| 28 | easy | blanket | a warm cover spread over a bed |
| 37 | easy | tunnel | a passage dug through rock or under water |
| 45 | easy | thunder | the loud crash that follows lightning |
| 54 | easy | potato | a starchy tuber dug from the soil |
| 62 | easy | dinner | the main meal of the evening |
| 71 | medium | monitor | the screen that shows a picture |
| 80 | medium | passport | the booklet you show at a border |
| 88 | medium | necklace | a chain worn around the throat |
| 97 | medium | thread | a fine strand drawn through cloth |
| 106 | medium | magazine | a glossy weekly with articles |
| 114 | medium | painting | art made with a brush on canvas |
| 123 | medium | fishing | catching with a hook and line |
| 131 | hard | apartment | a flat inside a larger building |
| 140 | hard | stranger | a person you have never met |
| 149 | hard | temperature | how hot or cold a thing is |
| 157 | hard | muscle | the tissue that pulls on a bone |
| 166 | hard | t-shirt | a short sleeved cotton top |

## 4. 체크박스별 근거

| 티켓 체크박스 | 무엇이 증명하는가 |
|---|---|
| `ko-general-01.csv` 150행 이상 + ko 규칙(2~5글자 완성형 한글·중복 없음·seed 와 안 겹침·힌트 1~60자·정답 음절 미포함·따옴표/쉼표 없음) | 162행, `check_word_csv.py` 위반 0건(§1). 규칙별 검사는 `_ko_answer_reasons`·`_ko_hint_leak_reasons`·`_hint_reasons`, 각각 `tests/test_check_word_csv.py` 의 `test_ko_answer_with_non_hangul_characters_is_caught`·`test_ko_hint_sharing_a_syllable_with_the_answer_is_caught`·`test_hint_longer_than_the_candidate_limit_is_caught`·`test_duplicate_answer_in_the_same_file_is_caught`·`test_answer_already_in_seed_words_is_caught` 가 "안 잡히면 실패" 로 고정. 인명·지명·브랜드·유행어 없음은 기계로 못 재는 항목이라 생성 단계에서 범주(사물·음식·자연·생물·절차)로 제한했고, 사람 검수 단계가 `docs/RELEASE.md` "### 39." 에 있다 |
| `en-general-01.csv` 150행 이상 + en 규칙(소문자 a-z·공백/하이픈 최대 1개·2~12자·모음 ≤50%·힌트에 정답/복수형 미포함) | 165행, 위반 0건(§1). `_en_answer_reasons`·`_en_hint_leak_reasons`, 테스트 `test_en_answer_rules_catch_uppercase_extra_separators_and_vowel_heavy_words`(`Mountain`/`a b c`/`aeon` 각 1건)·`test_en_hint_containing_the_answer_or_its_plural_is_caught`(`mountain`/`keyboards`)·`test_answer_longer_than_the_language_limit_is_caught` |
| 난이도 4:4:2 + 20행 표본·분포 근거 | §2 표(4.0:4.0:2.1 / 3.9:3.9:2.2)와 기준 설명, §3 표본 20행 × 2 |
| 검증 스크립트 `scripts/check_word_csv.py <csv>...` — `parse_word_input` 재사용, DB 없이, `줄번호: 사유`, 위반 시 종료 코드 1 | 스크립트 §1 실행 출력. DB 를 안 쓰는 건 `tests/test_check_word_csv.py` 가 `app`/`client` 픽스처 없이 도는 것으로 증명(아래 pytest 출력). 종료 코드는 `test_main_exits_zero_on_a_clean_file_and_one_on_violations` |
| 스크립트 테스트 `tests/test_check_word_csv.py` — 정상/힌트에 정답 포함/길이 초과/중복/잘못된 category 각 1건 + 정상 파일 종료 코드 0 | 17개 테스트 전부 통과(§5). 실제 후보 파일은 읽지 않는다 — 전부 `tmp_path` 임시 CSV 와 커밋된 `data/seed_words.csv` 만 쓴다 |
| `import_word_rows` 드라이런 추가 ≥150·오류 0 | §1 드라이런 출력(ko 162/0, en 165/0) |
| `book_title` 후보 | **건너뜀.** 근거는 §6 |
| `.gitignore`·README 한 단락·`docs/RELEASE.md` `### 39.` | `.gitignore` 에 `data/word-candidates/`(+ 이유 주석), README "운영: 단어 CSV 업로드" 절 끝 "**올리기 전 로컬 검증**" 단락, `docs/RELEASE.md` 맨 끝 "### 39. 단어 후보 CSV — 사람이 할 일" 4단계 체크리스트 |
| 테스트 전체 통과, ruff 0건 | §5 — `1526 passed`, `ruff check .` All checks passed |

## 5. 검증 명령과 출력

### ruff

```
$ uv run ruff check .
All checks passed!
```

### 마이그레이션 heads (1줄)

```
$ uv run flask db heads
b1c7d4e0a932 (head)
```

이 티켓은 마이그레이션을 만들지 않았다(스키마 변경 없음) — 기존 head 그대로다.

### 전체 테스트 스위트

로컬 `main`(`8de470b` Merge 티켓 32) 위로 rebase 한 뒤 전부 다시 돌렸다(충돌 없음).

```
$ uv run pytest -q
........................................................................ [  4%]
...(생략)...
........................................................................ [ 94%]
........................................................................ [ 99%]
..............                                                           [100%]
1526 passed in 1183.60s (0:19:43)
$ echo $?
0
```

실패 0, 건너뜀 0, 에러 0. 19분 43초는 공용 MySQL 을 병렬 워커와 같이 쓰기 때문이다
(전용 DB `chosung_daily_test_t39` / Redis 13 을 쓰므로 다른 워커의 데이터는 건드리지 않는다).

### 새 테스트만

```
$ uv run pytest tests/test_check_word_csv.py -q
.................                                                        [100%]
17 passed in 0.30s
```

17개는 티켓이 요구한 5개 케이스(정상 / 힌트에 정답 포함 / 길이 초과 / 중복 /
잘못된 category)에 ko·en 규칙별 케이스, 헤더 누락, 헤더 공백, 빈 정답·빈 힌트,
`main` 종료 코드, 없는 파일 처리를 더한 것이다.

## 6. 건너뛴 것·남은 것

- **`book_title` 후보 CSV 는 만들지 않았다.** 티켓의 조건("`flask search-books` 가 API 키
  없이 동작하면")이 성립하지 않는다:

  ```
  $ uv run flask search-books "소설" --size 5
  검색 결과 없음 (API 키가 안 설정됐을 수 있음 — .env의 KAKAO_REST_API_KEY / ALADIN_TTB_KEY 확인)
  ```

  `search_books` 는 `KAKAO_REST_API_KEY`·`ALADIN_TTB_KEY` 가 없으면 각 소스를 조용히
  건너뛰어 빈 리스트를 돌려준다(`app/services/book_lookup_service.py`). 두 키 모두 이
  환경에 없다. en 쪽 `search_google_books` 는 키 없이도 동작하도록 만들어져 있지만
  (`app/clients/google_books.py`), 워커 제약이 실제 외부 서비스 호출을 금지하므로 부르지
  않았다. → 티켓 지시대로 **"사람이 `flask search-books` 로 넣는다"**. `docs/RELEASE.md`
  "### 39." 마지막 단락에 같은 내용을 적어 뒀다.
- 실패한 테스트·건너뛴 테스트 없음(§5).
- 운영 서버 업로드·단어 DB 적재·잔량 알림 로직은 티켓의 "하지 않는 것" 대로 손대지 않았다.
- 스펙 "미정 항목" 에 추가할 결정 사항 없음.
