# 티켓 15 최종 리뷰 — 라운드 1

## 범위와 판정 근거

- 기준: 로컬 `main` = `abf3e9a1706de253aa701ab3d321b42db87e9bc0`, 구현 HEAD = `62991339b09219aadaf05788b01e5af6bcdbd728`.
- `git log main..HEAD`: `e32062a` 구현, `6299133` 구현 증거. `git diff main...HEAD`의 23개 파일을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 체크박스, 스펙 §A.11·US 50–53·운영자 계정·§C, `CONTEXT.md`, 디자인 `SCREENS.md`, `MASTER.md`와 우선 규칙 `OVERRIDES.md`, 구현 증거를 대조했다.
- 결함: **BLOCKER 0 / MAJOR 3 / MINOR 1**. 기존 테스트 통과와 별개로 아래 결함을 실제 HTTP 요청과 DB·Redis 조회로 재현했다.

## 체크박스별 충족 여부

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| `ADMIN_EMAILS` 기본값 없음, 운영자 이메일 주석, 세션→연결 계정 이메일 판정, 비운영자 403·미로그인 안내와 테스트 3종 | 충족 | `app/config.py`의 빈 tuple 기본값, `.env.example`의 15 블록, `app/admin.py:61`의 계정 조회·허용 목록 비교. `test_admin_auth.py` 7개 테스트가 실제 세션 동기화와 응답을 검증하며 전체 실행에서 통과. |
| 모든 `/admin` POST에 기존 CSRF 데코레이터, 토큰 누락 403 | 충족 | 추가·수정·삭제·업로드의 4개 POST 모두 `@csrf_protected` 사용. 각 경로의 토큰 누락 테스트 통과. 정상 요청도 렌더된 폼에서 얻은 토큰으로 직접 재현. |
| 필터·페이지네이션·추가·수정·삭제 Jinja, 토큰 CSS, 저장 시 mask 재계산, 배정 단어 삭제 차단 | 미충족 | 목록·필터·페이지네이션·CRUD·mask 재계산·삭제 차단 테스트는 통과하고 공용 CSS도 연결됨. 그러나 배정 단어 수정 시 캐시가 갱신되지 않고 퍼즐/단어 언어 불일치를 허용함(D-15-1, D-15-2). |
| UTF-8/BOM·헤더 검증·행별 추가/중복/오류 사유, 행 리스트 서비스 | 미충족 | 정상 입력·BOM·누락 헤더·중복·enum 오류 및 `import_word_rows(rows)` 경로 확인. 중복 헤더/초과 열은 데이터 유실을 성공 처리하며(D-15-3), 긴 필드는 행별 오류 대신 예외로 전체 처리가 중단됨(D-15-4). |
| 운영자 페이지 `impeccable detect` 0건 | 충족 | 실제 Flask 응답 HTML과 원본 토큰/admin CSS를 메모리 HTTP 서버로 제공하여 데스크톱 7개·모바일 3개 화면 검사: 각각 `[]`, exit 0. 외부 호출 금지에 따라 CDN 폰트만 제거하고 CSP로 외부 리소스를 차단했으므로 실제 CDN 폰트 상태는 미검증. |
| README 인증 설계 판단 및 운영 CSV 포맷·LLM 생성 가이드 | 충족 | `README.md`의 `### 15. 운영자 인증 = 기존 OAuth + 이메일 허용 목록`과 운영 CSV 절·ko/en 생성 가이드 확인. |

## 직접 실행한 검증

기존 전용 MySQL DB `chosung_daily_test_t15`, Redis DB `3`, 기존 마이그레이션 테스트 DB `chosung_daily_test_t15_migrations`를 각각 `TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL`로 지정했다. 접속 성공으로 기본 DB 폴백·새 DB 생성·간헐 실패 재실행은 필요하지 않았다. 접속 비밀번호·토큰 값은 기록하지 않는다.

```text
uv run pytest -q
717 passed in 487.46s (0:08:07)
exit 0

uv run ruff check .
All checks passed!
exit 0

FLASK_ENV=testing uv run flask --app wsgi db heads
a5bab2f58a7b (head)
exit 0

git diff --check main...HEAD
출력 없음, exit 0
```

새 마이그레이션은 없다. 전체 테스트 종료 후 동일한 전용 DB/Redis에서 별도 Python 표준입력 프로그램으로 테스트 계정·단어·오늘 퍼즐을 만들고, 실제 세션 동기화 및 폼 CSRF 토큰을 거친 HTTP 요청으로 아래 결과를 확인했다. 종료 시 테스트 테이블과 Redis DB 3을 정리했다. 애플리케이션·테스트·설정·`.scratch/` 파일은 수정하지 않았다.

```text
CACHE_REPRO 302 database= 수정된 힌트 game= 원래 힌트
LANGUAGE_REPRO 302 puzzle= ko word= en answer= apple
  mask= [h, r(P), r(P), r(L), h]
EXTRA_COLUMN_REPRO 200 saved_hint= 배우는 added= True
DUP_HEADER_REPRO 200 saved_answer= 버스 added= True
LONG_FIELD_REPRO Error field larger than field limit (131072)
```

디자인 검사 실행기는 로컬 설치된 `/Users/saem/.claude/plugins/marketplaces/impeccable/cli/bin/cli.js`를 사용했다. 최초 템플릿 정적 검사 `[]`에는 Jinja CSS 링크 해석 실패 경고가 있어 증거로 채택하지 않고 아래 URL 검사로 보완했다. 스냅샷 파일은 만들지 않았다.

```text
node <위 CLI 경로> detect --json --viewport 1280x800 <로컬 URL 7개>
[] / stderr 없음 / exit 0
대상: 목록, 필터 목록, 빈 목록, 추가, 수정, 업로드, 업로드 결과

node <위 CLI 경로> detect --json --viewport 390x844 <로컬 URL 3개>
[] / stderr 없음 / exit 0
대상: 목록, 추가, 업로드 결과
```

## 결함 목록

### D-15-1 — MAJOR — 단어 수정 성공 후에도 오늘 퍼즐은 수정 전 캐시를 사용

- 위치: `app/services/word_service.py:228`–`233` (`update_word`). 관련 읽기 경로: `app/services/puzzle_service.py:38`, `app/services/puzzle_cache.py:12`.
- 재현: 오늘 ko 퍼즐에 `사과 / 원래 힌트`를 배정 → `get_today_puzzle_or_404(PuzzleLanguage.KO)`로 캐시 생성 → 운영자 수정 폼에서 정상 CSRF 토큰을 받아 `POST /admin/words/<id>`로 힌트만 `수정된 힌트`로 저장 → 같은 서비스로 오늘 퍼즐 재조회.
- 기대: 성공으로 저장된 힌트가 해당 퍼즐 읽기에도 반영되어야 한다.
- 실제: POST는 302, DB는 `수정된 힌트`지만 게임 읽기는 `원래 힌트`. 수정 함수는 DB 커밋만 하고 관련 캐시를 무효화하지 않는다. 캐시 TTL은 26시간이어서 당일 내내 오타·부적절한 내용 수정이 플레이어에게 반영되지 않을 수 있다. 정답·mask·카테고리도 동일한 캐시 구조를 사용한다.
- 테스트 공백: `test_update_word_can_keep_its_own_answer` 등은 DB 값만 확인하고 캐시를 먼저 채운 뒤 게임 읽기를 검증하지 않는다.

### D-15-2 — MAJOR — 배정된 단어의 언어를 바꾸면 퍼즐 언어와 불일치

- 위치: `app/services/word_service.py:228` (`word.language = parsed.language`).
- 재현: 오늘 ko 퍼즐이 참조하는 `사과` 단어를 운영자 수정 폼에서 `language=en, category=general, answer=apple, hint=red fruit`로 저장 → 해당 ko 캐시를 지워 캐시 미스 상태로 만들고 오늘 ko 퍼즐 조회.
- 기대: 이미 ko 퍼즐이 참조하는 단어가 en으로 바뀌어 퍼즐 언어 불변식을 깨는 저장은 거부되거나 배정 관계의 일관성이 유지되어야 한다.
- 실제: POST 302로 허용되고 `DailyPuzzle.language=ko`, `Word.language=en`, 정답 `apple`, 영어 모음 가림이 함께 반환된다. 기존 퍼즐은 ko로 남아 ko 조회·채점 경로에서 영어 단어를 사용한다. 캐시 문제와 독립적이며 캐시를 무효화해도 발생한다.
- 테스트 공백: `test_update_word_recalculates_the_mask`는 배정되지 않은 단어의 ko→en 변경만 검증한다. 배정 검사도 삭제 경로에만 있다.

### D-15-3 — MAJOR — 잘못된 CSV 구조를 성공 처리하면서 값을 버림

- 위치: `app/services/word_service.py:111`–`112`, `133`–`139`; `app/admin.py:184`–`191`.
- 재현 A: 정상 인증/CSRF로 아래 UTF-8 파일을 업로드한다.

```csv
language,category,answer,hint
ko,general,학교,배우는,장소
```

- 기대: 4열 헤더에 5개 값이 온 행은 열 개수 오류와 사유를 표시하고 잘못된 내용을 저장하지 않는다.
- 실제 A: HTTP 200, `추가 1개`; 저장된 힌트는 `배우는`이며 `장소`는 버려진다. `DictReader`의 `None` 키에 담긴 초과 값을 서비스가 무시한다.
- 재현 B: 다음 중복 헤더 파일을 업로드한다.

```csv
language,category,answer,answer,hint
ko,general,기차,버스,교통
```

- 기대: 중복된 필수 헤더를 오류로 거부한다.
- 실제 B: HTTP 200, `추가 1개`; `기차`가 사라지고 `버스`가 정답으로 저장된다. 헤더 검증이 집합 기반 존재 여부만 확인해 중복을 놓치며 `DictReader`가 앞의 값을 덮어쓴다. 잘못된 LLM CSV 행을 찾아 고친다는 US 51–52 및 행별 결과 요구를 충족하지 못한다.
- 테스트 공백: 누락 헤더와 잘못된 enum 테스트는 있지만 열 개수·중복 헤더 테스트는 없다.

### D-15-4 — MINOR — CSV 필드 파싱 한도를 넘으면 행별 오류 대신 예외

- 위치: `app/admin.py:191` (`list(reader)`).
- 재현: 정상 4열 헤더 아래 `ko,general,기차,` 뒤에 ASCII `x` 131073개를 붙인 행을 정상 CSRF로 업로드한다. 입력 생성식: `'language,category,answer,hint\nko,general,기차,' + 'x' * 131073 + '\n'`.
- 기대: 너무 긴 힌트의 행별 오류 또는 명시적인 CSV 입력 오류를 보여준다.
- 실제: 테스트 클라이언트에서 `csv.Error: field larger than field limit (131072)`가 처리되지 않고 전파된다. 운영 설정에서는 기존 500 핸들러로 귀결되는 경로다. 서비스의 200자 길이 검증에 도달하지 못하고 전체 업로드 결과 표도 생성되지 않는다. 정상 행이 함께 있어도 리스트 변환 단계에서 중단된다.

## 보안·범위·공유 파일 확인 및 참고

- 허용 목록은 기본 거부이며 POST에 기존 CSRF 보호를 적용했다. 입력은 ORM 필터와 Jinja 자동 이스케이프를 거치고 검색 LIKE 특수문자 이스케이프 테스트도 통과했다. 변경 파일에서 실제 시크릿 값의 추가는 발견하지 않았다.
- README 설계 판단은 15번 소제목을 절 끝에 추가했고, API 표는 자기 경로 행만 추가했다. `.env.example`과 `docs/RELEASE.md`도 티켓 15 블록을 덧붙였다. 공유 규칙 위반이나 무관한 기능 변경은 발견하지 않았다. 기존 CSV CLI를 새 행 리스트 서비스에 연결한 변경은 관련 범위이며 기존 테스트도 통과했다.
- 관리자 화면 폭 1040px는 OVERRIDES §10의 480px와 다르다. 구현자가 운영 표를 위한 의도적 차이로 README와 증거에 기록했다. 운영자 전용 목업이 없다는 점과 실제 기능 결함을 구분해 이 레이아웃 선택은 참고로 남긴다.
- 실제 Google 로그인 왕복·운영 두 계정·프로덕션·외부 서비스·CDN 폰트는 접근하지 않았다. 인증 테스트가 검증하는 범위는 연결 계정과 동기화된 웹 세션 이후다.
- 테스트는 실제 DB/Redis와 HTTP 폼을 사용하며 과도한 mock이나 무조건 통과하는 신규 테스트는 발견하지 않았다. 다만 통과 결과가 위 네 입력·상태 경계의 안전성을 보증하지는 않는다.

판정: FAIL

## 라운드 2

### 범위와 판정 근거

- 기준은 로컬 `main` = `148715ba7f8008cd0e7495ee68266374ec5dff45`, 구현 HEAD = `243e1a1eab129d1454ac9d9409b00decd551e0ac`이다. `origin/main`은 사용하지 않았다.
- `git diff main...HEAD`의 25개 파일과 `git log main..HEAD`의 `8407a65`, `11d5953`, `1a46336`, `98c197b`, `243e1a1`을 확인했다. 티켓 15, 스펙 §A.11·US 50–53·운영자 계정·§C, `CONTEXT.md`, 디자인 `SCREENS.md`·`MASTER.md`·우선 규칙 `OVERRIDES.md`, 구현 증거의 수정 라운드 1을 대조했다.
- 이전 결함 **4건 모두 FIXED**, REPEAT 0건, 신규 결함 0건. 현재 열린 결함은 **BLOCKER 0 / MAJOR 0 / MINOR 0**이다.
- 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다. 하위 에이전트, 프로덕션, NAS, 배포, push, 실제 외부 서비스 호출은 사용하지 않았다.

### 티켓 체크박스별 충족 여부

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| `ADMIN_EMAILS` 기본값 없음·운영자 이메일 주석·세션→연결 계정 이메일 판정·비운영자 403·미로그인 안내·테스트 3종 | 충족 | `app/config.py:129`는 미설정 시 빈 tuple, `.env.example`은 15번 블록에 운영자 주소를 주석으로 명시한다. `app/admin.py:61`은 세션 guest ID로 Account를 읽어 허용 목록을 확인한다. `tests/test_admin_auth.py`의 운영자/비운영자/미로그인 및 경계 테스트가 실제 세션 동기화와 HTTP 응답을 검증하며 통과했다. |
| 모든 `/admin` POST에 기존 CSRF 데코레이터·토큰 누락 403 | 충족 | 추가·수정·삭제·업로드 4개 POST 모두 `@csrf_protected`를 적용한다. 실제 폼에서 발급한 토큰을 사용하는 정상 요청과 각 경로의 토큰 누락 403 테스트가 통과했다. |
| 필터·페이지네이션·CRUD Jinja·공용 토큰 CSS·mask 재계산·배정 단어 삭제 차단 | 충족 | `tests/test_admin_words.py`에서 목록/필터/쪽 넘김/CRUD/mask/배정 삭제 차단을 검증했다. 배정 단어 수정 후 게임 읽기 갱신과 언어 변경 거부까지 회귀 테스트로 확인했다(D-15-1·2 FIXED). 템플릿은 공용 `tokens.css`를 연결한다. |
| CSV UTF-8/BOM·헤더 검증·행별 추가/중복/오류+사유·행 리스트 서비스 | 충족 | `tests/test_admin_csv_upload.py` 및 `tests/test_word_service.py`가 실제 업로드·DB 결과·행 리스트 적재를 검증한다. 중복 필수 헤더와 초과 열은 저장되지 않고 사유가 표시되며, 파서 한도 초과는 명시적인 입력 오류로 처리된다(D-15-3·4 FIXED). |
| 운영자 페이지 `impeccable detect` 0건 | 충족 | 실제 인증/CSRF 경로로 얻은 응답 10개와 원본 CSS를 메모리 로컬 서버로 제공해 직접 실행했다. 1280×800과 390×844 모두 `[]`, exit 0, stderr 없음. 외부 CDN 폰트는 제외했다. |
| README 인증 설계 판단 및 운영 CSV 포맷·LLM 생성 가이드 | 충족 | README의 `### 15. 운영자 인증 = 기존 OAuth + 이메일 허용 목록`과 `운영: 단어 CSV 업로드` 절에서 포맷·예시·ko/en 생성 가이드를 확인했다. |

### 이전 결함 재검증

각 항목의 심각도는 라운드 1의 심각도이며, FIXED 항목은 현재 열린 결함 수에 포함하지 않는다. 아래 테스트는 전체 pytest 실행에 포함되어 모두 통과했다.

#### D-15-1 — FIXED — 기존 MAJOR — 단어 수정 후 오늘 퍼즐 캐시

- 수정 위치: `app/services/word_service.py:277`, `app/services/word_service.py:294`, `app/services/puzzle_cache.py:61`, `app/repositories/word_repository.py:66`.
- 재현: `tests/test_admin_words.py::test_update_word_makes_the_change_visible_in_todays_puzzle`. 오늘 ko 퍼즐을 게임 서비스로 읽어 캐시 생성 → 실제 수정 폼의 CSRF 토큰으로 힌트를 변경 → 같은 게임 서비스로 재조회한다.
- 기대: DB와 게임 읽기가 모두 수정된 힌트를 반환한다. 실제: POST 302, DB와 게임 읽기 모두 `고친 힌트`로 검증되어 통과했다.
- 수정은 DB 커밋 이후 배정된 날짜·언어별 캐시를 삭제한다. 단순 DB 값만 확인하거나 Redis를 mock하는 테스트가 아니다.

#### D-15-2 — FIXED — 기존 MAJOR — 배정된 단어의 언어 불일치

- 수정 위치: `app/services/word_service.py:277`.
- 재현: `tests/test_admin_words.py::test_update_word_rejects_a_language_change_for_an_assigned_word`. ko 퍼즐에 배정된 `사과`를 운영자 폼에서 `en / apple`로 변경한다.
- 기대: 사유를 표시하며 거부하고 기존 단어·퍼즐 언어를 보존한다. 실제: HTTP 200 오류 폼에 `배정` 사유, DB는 ko/사과, 게임 읽기도 사과로 유지되어 통과했다.
- 반대 경계인 미배정 단어의 언어 변경 테스트도 통과했다. 배정 단어의 힌트 수정까지 차단하는 과잉 제한은 없다.

#### D-15-3 — FIXED — 기존 MAJOR — CSV 초과 열·중복 필수 헤더의 데이터 유실

- 수정 위치: `app/admin.py:186`, `app/admin.py:201`, `app/services/word_service.py:121`, `app/services/word_service.py:150`.
- 재현 A: 정상 헤더 `language,category,answer,hint` 아래 `ko,general,학교,배우는,장소`를 업로드한다. 기대는 행 오류와 저장 0건이며, 실제도 HTTP 200·`열이 헤더보다 많습니다`·저장 0건으로 통과했다(`test_upload_rejects_a_row_with_more_values_than_the_header`).
- 재현 B: `language,category,answer,answer,hint` 아래 `ko,general,기차,버스,교통`을 업로드한다. 기대는 중복 헤더 거부이며, 실제도 HTTP 200·`같은 열이 두 번 있어요: answer`·저장 0건으로 통과했다(`test_upload_rejects_a_duplicated_required_header`).
- 깨진 행 옆 정상 행은 계속 적재되는 테스트와 CLI의 초과 열 행 오류 테스트도 통과했다. 이 FIXED 판정은 원래 결함의 웹 업로드 A/B에 대한 것이며 CLI의 모든 헤더 정책까지 동일하다고 확대 해석하지 않는다.

#### D-15-4 — FIXED — 기존 MINOR — CSV 파서 필드 한도 초과 예외

- 수정 위치: `app/admin.py:187`.
- 재현: `tests/test_admin_csv_upload.py::test_upload_reports_a_field_over_the_csv_parser_limit`. 정상 헤더 아래 `ko,general,기차,` 뒤에 `x` 131073개를 붙여 업로드한다.
- 기대: 500 대신 명시적인 CSV 입력 오류를 보여준다. 실제: HTTP 200·`CSV 를 읽지 못했어요`·저장 0건으로 통과했다. 헤더 접근과 행 목록 변환 모두 `csv.Error` 처리 범위에 있다.

### 직접 실행한 검증

기존 전용 DB `chosung_daily_test_t15`, Redis DB `3`, 기존 마이그레이션 DB `chosung_daily_test_t15_migrations`를 각각 `TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL`로 지정했다. 모두 접속되어 새 DB 생성이나 기본 DB 폴백은 하지 않았다. 전체 실행 중 간헐 실패가 없어 재실행도 하지 않았다. 접속 비밀번호·토큰 값은 기록하지 않는다.

```text
uv run pytest -q
743 passed in 1796.05s (0:29:56)
exit 0

uv run ruff check .
All checks passed!
exit 0

FLASK_ENV=testing uv run flask --app wsgi db heads
dae1b5af0cf7 (head)
exit 0

git diff --check main...HEAD
출력 없음, exit 0
```

티켓이 추가한 마이그레이션은 없다. 구현 증거의 과거 실행 시간보다 이번 전체 테스트는 느렸으나 모든 테스트가 종료되어 성공했다.

디자인 검사는 별도 파일을 만들지 않는 Python 표준입력 프로그램으로 수행했다. 전용 DB에 테스트 계정·단어·오늘 퍼즐을 만들고 실제 `session/sync`와 폼 CSRF를 거쳐 응답을 얻었다. 외부 폰트 링크와 hidden 토큰을 제거한 HTML, 원본 `tokens.css`·`admin.css`를 메모리 HTTP 서버로 제공했다. CSP로 외부 리소스를 차단했고 종료 시 테스트 테이블과 Redis DB 3을 정리했다.

```text
node /Users/saem/.claude/plugins/marketplaces/impeccable/cli/bin/cli.js detect --json --viewport 1280x800 <로컬 URL 10개>
[]
stderr 없음 / exit 0

node /Users/saem/.claude/plugins/marketplaces/impeccable/cli/bin/cli.js detect --json --viewport 390x844 <로컬 URL 10개>
[]
stderr 없음 / exit 0
```

대상: 목록, 필터 목록, 빈 목록, 추가 폼, 수정 폼, 업로드 폼, 업로드 결과, 초과 열 행 오류, 파서 필드 한도 오류, 배정 단어 언어 변경 거부 폼.

### 보안·범위·공유 파일 확인 및 참고

- 기본 거부 허용 목록, 모든 운영자 POST의 기존 CSRF 보호, ORM 조회, Jinja 자동 이스케이프를 확인했다. 변경 파일에 실제 시크릿 값 추가는 발견하지 않았다. 새 테스트는 실제 DB·Redis·HTTP 폼을 사용하며, 이번 네 수정의 핵심 결과를 무조건 통과시키는 mock은 없다.
- README 설계 판단은 자기 번호 15 소제목, API 표는 자기 경로 행, `.env.example`·`docs/RELEASE.md`는 자기 번호 블록을 추가했다. 다른 티켓 항목을 고친 공유 규칙 위반이나 무관한 기능 변경은 발견하지 않았다.
- 관리자 최대 폭 1040px 선택은 이전 라운드와 동일하게 참고로 유지한다. 운영자 전용 목업은 없고, 구현자가 운영 표를 위한 차이를 README에 기록했다. 취향·스타일 제안은 결함으로 계산하지 않는다.
- 실제 Google 로그인 왕복, 운영자 실제 두 계정, CDN 폰트와 실제 배포 환경은 검증하지 않았다. 인증 검증의 범위는 연결된 Account와 동기화된 웹 세션 이후다.

판정: PASS
