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
