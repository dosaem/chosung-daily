# 티켓 01 구현 증거 — 프리팩터(린트 강화·도메인 문서 이관·외부 호출 골격·CSRF·마이그레이션 head)

- 브랜치: `dosaem/t01-prefactor-lint-docs-clients` (로컬 `main` **feb2553** 위로 rebase
  완료 — 작업 중 티켓 19 가 main 에 머지돼 두 번 rebase 했다. README "설계 판단" 충돌은
  19 의 소제목을 보존하고 번호순(`01`×3 → `19`)으로 두는 방식으로 풀었다)
- 커밋 9개, 변경 30파일 (+990 / -10)
- 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t01`, Redis DB 3
  (`TEST_DATABASE_URL`, `TEST_REDIS_URL` 환경변수로 지정. 공용 `chosung_daily_test`·
  Redis 1 은 건드리지 않았다)
- 외부 서비스 호출 0건. Slack 은 가짜 `requests.post` / monkeypatch 한 래퍼로만 검증했다.
  NAS 접속·배포·`git push` 없음. 시크릿 값은 어떤 파일에도 쓰지 않았다(이름만: `SLACK_WEBHOOK_URL`).

## 1. 실행한 명령과 출력

### 전체 테스트 스위트

rebase 후(티켓 19 포함) 최종:

```
$ TEST_DATABASE_URL=...chosung_daily_test_t01 TEST_REDIS_URL=redis://127.0.0.1:6379/3 uv run pytest -q
........................................................................ [ 69%]
...............................                                          [100%]
103 passed in 57.36s
```

머지 기준 main(feb2553)의 baseline 은 85 passed 였다 → **신규 18개**(`test_slack_client.py` 5,
`test_operator_alert_service.py` 2, `test_csrf.py` 7, `test_domain_docs.py` 3,
`test_cli.py` 에 2 추가). 실패·skip·xfail 0건.

### 린트 (강화된 규칙으로)

```
$ uv run ruff check .
All checks passed!
```

티켓 19 가 머지된 코드(`tests/test_compose_config.py` 등)까지 포함해 통과한다 —
rebase 후 재실행한 결과다.

규칙 추가 직후의 red (수정 전):

```
$ uv run ruff check --select "E,F,I,UP,B,PL,RUF,SIM,PT" --statistics .
63	PLR2004	magic-value-comparison
 8	PLC0415	import-outside-top-level
 1	RUF012 	mutable-class-default
 1	PT011  	pytest-raises-too-broad
 1	PT022  	pytest-useless-yield-fixture
 1	RUF059 	unused-unpacked-variable
Found 75 errors.
```

### 마이그레이션 head

```
$ FLASK_APP=wsgi.py uv run flask db heads
9ec267465b4e (head)          ← 1줄

$ ./scripts/check_migration_heads.sh
9ec267465b4e (head)
OK: Alembic head 1개
```

검사기가 실제로 다중 head 를 잡는지 확인(가짜 2번째 리비전을 임시로 넣고 돌린 뒤 삭제):

```
$ ./scripts/check_migration_heads.sh      # down_revision=e759d7e8d071 인 가짜 리비전 추가 상태
9ec267465b4e (head)
ffff00001111 (head)
Alembic head 가 2 개다 (1개여야 한다). 뒤에 머지되는 마이그레이션의 down_revision 을 선행 머지 리비전으로 재설정해라.
exit=1
```

이 티켓은 마이그레이션을 **만들지 않았다**(스키마 변경 없음). head 는 기존 그대로 1개다.

### impeccable

```
$ impeccable context
  "productPath": "PRODUCT.md",
  "designPath": null,
  "platform": "web"
```

`NO_PRODUCT_MD` / `PRODUCT_INIT_REQUIRED` 경고가 사라졌고 config 경고도 0건이다
(작업 전에는 두 경고가 떴다). `designPath: null` 은 정상 — init 절차는 DESIGN.md 를
쓰지 않고, 이 프로젝트의 시각 권위는 DESIGN_DIR 두 경로다.

```
$ impeccable detect web/templates/index.html web/static/style.css web/static/app.js
impeccable detect: could not read linked stylesheet {{ url_for('static', filename='style.css') }}
  ... color and custom-property rules will be incomplete
exit=0      ← findings 0건
```

이 티켓은 UI 를 건드리지 않았다(웹 템플릿·JS·CSS 변경 0). 위 출력은 **현행 웹의
baseline** 이고, 0건이다. 경고 한 줄은 Jinja 의 `url_for` 를 정적 파서가 못 푸는
것이라, 웹 UI 티켓(15·18)은 `style.css` 를 함께 인자로 주거나 렌더된 HTML/URL 을
스캔해야 한다는 메모로 남긴다.

## 2. 체크박스별 증거

| # | 티켓 체크박스 | 무엇이 증명하나 | 결과 |
|---|---|---|---|
| 1 | `CONTEXT.md` 루트 이관 + `adr/0001~0003` → `docs/adr/`, `docs/agents/domain.md` 경로와 일치 | `tests/test_domain_docs.py` 3개 (루트 `CONTEXT.md` 존재·`## Language` 포함 / `docs/adr/` 파일명 3개 정확히 / `domain.md` 가 그 두 경로를 가리키는 문구 확인). RED 확인: 두 경로를 잠시 치우면 2 failed | 통과 |
| 2 | `/impeccable init` 산출물 커밋 + DESIGN_DIR 두 경로 지시 | `impeccable context` 가 `productPath: PRODUCT.md`로 부팅(위 출력). `PRODUCT.md` "Evidence on Hand" 가 두 경로와 파일별 역할·우선순위를 적고 있다 | 통과(문구와 다르게 충족 — §3 참고) |
| 3 | ruff 에 `PL,RUF,SIM,PT` 추가 + 기존 코드 수정으로 린트 잡 통과 | `pyproject.toml` `[tool.ruff.lint] select`, `uv run ruff check .` → All checks passed (위 출력). 예외 2건은 pyproject 에 근거 주석 포함 per-file-ignores | 통과 |
| 4 | CI 에 "`flask db heads` 가 정확히 1줄" 스텝 | `.github/workflows/ci.yml` 의 "Migration heads (정확히 1개)" 스텝 + `scripts/check_migration_heads.sh`. 2 heads 일 때 exit 1 임을 실제로 확인(위 출력) | 통과 |
| 5 | `app/clients/` + Slack Webhook 래퍼(함수 하나, 타임아웃 3초, 예외 안 던짐, URL 비면 no-op) | `tests/test_slack_client.py` 5개: 전송 인자(`json={"text": …}`, `timeout == TIMEOUT_SECONDS == 3`) / URL 빈 값이면 `requests.post` 호출 0회 + `False` / `requests.Timeout` 을 삼키고 `False` / 500 응답도 삼키고 `False` | 통과 |
| 6 | `notify_operator(kind, message)` + monkeypatch 한 래퍼로 호출 인자(제목·본문) 검증, 네트워크 없음 | `tests/test_operator_alert_service.py` 2개: 래퍼에 넘어간 텍스트에 제목·본문이 다 있고 `[오늘의 초성]` 로 시작하며 제목 뒤 줄바꿈 / 래퍼 실패 시 예외 없이 `False` | 통과 |
| 7 | CSRF: 세션 1회용 토큰 발급 함수 + 폼 hidden 검증 데코레이터(불일치 403 `FORBIDDEN`), 단위 테스트(발급·검증·재사용 거부) | `tests/test_csrf.py` 7개: 발급→검증 200 / 매번 새 토큰 / 틀린 값 403 `FORBIDDEN` / 값 누락 403 / 발급 없이 제출 403 / **같은 토큰 재사용 403** / 실패 요청이 유효 토큰을 태우지 않음. 실제 쿠키 세션을 타고 검증(테스트 전용 라우트) | 통과 |
| 8 | README "설계 판단" 을 `### NN.` 구조로 시작 + 3개 항목 추가 | `README.md` 절 머리에 번호 규칙 메모, `### 01. 외부 호출 래퍼와 도메인 판정 함수의 분리` / `### 01. Slack Webhook 선택 근거` / `### 01. CSRF 토큰 방식` 3개. 티켓 19 의 `### 19.` 소제목을 그대로 두고 그 앞에 번호순으로 놓았다 | 통과 |
| 9 | `.env.example` 에 `SLACK_WEBHOOK_URL` 추가, `.env`·`.env.prod.example` 실제 값 불변 | `.env.example` 에 빈 값 + 발급·확인 방법 주석. `git diff main..HEAD -- .env .env.prod.example` 비어 있음(둘 다 미변경) | 통과 |

### 티켓 "What to build" 의 추가 서술

"운영자가 Slack 으로 첫 테스트 알림을 받을 수 있다" — 체크박스에는 없지만 본문이
요구하는 결과라, 호출 경로로 `flask notify-operator-test` 를 넣었다
(`tests/test_cli.py` 2개: URL 없을 때 건너뜀 안내 / 래퍼를 통해 1건 전송).
운영자가 실제 채널에서 받는 건 사람이 `.env` 에 URL 을 넣은 뒤 이 명령을 치는
단계이고, 이 세션에서는 외부 호출 금지라 실제 발송은 하지 않았다.

## 3. 체크박스 문구와 다르게 충족한 항목

**체크박스 2 — "생성된 설정이 DESIGN_DIR 두 경로를 가리킨다"**

impeccable 4.5.2 의 `.impeccable/config.json` 은 스키마가 고정이고 디자인 경로를
담을 키가 없다. 실제로 `designSystem` 키를 넣고 부팅해보니:

```
"id": "config-unknown-keys",
"summary": ".impeccable/config.json has top-level key(s) nothing reads: `designSystem`.
            Recognized keys are `hook`, `detector`, `updateCheck`, `stalenessCheck`,
            `projectRoots`, `buildPath`, `browser`, `$schema`, `version`."
```

`init` 절차(`reference/init.md`)도 "never ... offer DESIGN.md during init" 로 DESIGN.md
작성을 금지한다. 그래서 **init 이 쓰는 파일인 `PRODUCT.md`** 에 DESIGN_DIR 두 경로와
각 파일의 역할·우선순위(`OVERRIDES.md` > `MASTER.md`·`SCREENS.md`)를 적고,
`Brand Commitments` 에 구속력 있는 토큰 규칙(brand 면 채움 금지, 주 버튼 검정,
피드백 색 분리)을 옮겨 적었다. `.impeccable/config.json` 은 읽히는 키만 남겼다
(`detector.extensions`: `.html`/`.css`/`.js` — `web/static` 의 vanilla JS·CSS 도
detect 대상에 넣기 위해).

코디네이터 확인(`orca orchestration ask`, 이 세션): **"그대로 통과. 체크박스의 의도는
'impeccable 이 DESIGN_DIR 두 경로를 근거로 삼는다' 이고, 도구 스키마상 config 에 경로
키를 둘 수 없으니 PRODUCT.md 에 경로·우선순위를 적는 방식이 의도에 맞다. 읽히지 않는
키는 넣지 않는다."**

**`/impeccable init` 의 인터뷰 라운드** — init 절차는 제품 질문 라운드를 요구한다.
스펙 r5 + `CONTEXT.md` + ADR 0001~0003 이 init 의 세 질문(주 사용자·제품 목적·보존할
제약)에 이미 답하고 있어 PRODUCT.md 를 그 문서들로만 채웠고, 같은 `ask` 로 코디네이터에게
확인했다 → **"없음 — 스펙 r5·CONTEXT.md·ADR 이 유일한 근거다. 거기에 없는 사실을
PRODUCT.md 에 추가하지 말 것."** `buildPath` 는 기록하지 않았다: `impeccable context` 가
`IMAGE_GEN_AVAILABLE` 을 보고하지 않아(이미지 생성 없음) 고를 선택지가 없고, init 은
그 경우 "code-first 가 유일한 경로" 라고 정한다.

**`PRODUCT.md` 의 `## Platform` = `web`** — 이 레포 UI 는 현재 `web/templates` +
`web/static` 뿐이다. Flutter(`mobile/`, 티켓 22~31)가 들어오면 네이티브 설계 작업이
`reference/ios.md`·`android.md` 를 읽어야 하므로 그때 다시 판단하라는 근거를
PRODUCT.md 에 남겼다. 코디네이터가 22~31 워커 스펙에 전달하기로 했다.

## 4. ruff 예외 2건(완화한 규칙)과 근거

`pyproject.toml` 의 `[tool.ruff.lint.per-file-ignores]` 에 주석과 함께 둔다. `noqa` 는
한 건도 새로 넣지 않았고, 기존 `noqa` 2건은 **없애는 쪽으로** 고쳤다
(`B017` → `pytest.raises(RedisError)`, `F401`/`E402` 는 규칙 선택이 바뀌며 자연 해소).

| 대상 | 규칙 | 건수 | 근거 |
|---|---|---|---|
| `app/__init__.py`, `app/api/__init__.py` | `PLC0415` | 6 | 블루프린트·모델을 함수 안에서 import 하는 건 **순환 import 회피**다. `app/__init__.py` → `app.api` → `app.extensions`(= `app` 패키지 실행) 로 돌아서, 최상단으로 올리면 import 가 순환한다. 설계상 필요한 지연 import |
| `tests/*` | `PLR2004` | 63 | `assert res.status_code == 200`, `assert len(rows) == 3` 류. 상수로 빼면 무엇을 검증하는지 오히려 안 보인다. 프로덕션 코드에는 적용하지 않는다(앱 코드 PLR2004 0건) |

함수 안에 있던 `import os`(`app/__init__.py`)와 `from app.models import …`
(`tests/test_puzzle_cache.py`)는 순환과 무관해서 **그냥 최상단으로 옮겼다** — 예외
범위를 필요한 만큼만 남기려고.

## 5. 수정한 기존 코드 (린트 통과를 위해)

| 파일 | 규칙 | 수정 |
|---|---|---|
| `app/config.py` | `RUF012` | Flask 설정 클래스의 dict 기본값에 `ClassVar[dict[str, object]]` 표기 |
| `app/__init__.py` | `PLC0415` | 함수 안의 `import os` → 최상단 |
| `tests/conftest.py` | `PT022` | teardown 없는 `broken_redis` fixture 의 빈 `yield` 제거(`monkeypatch.setitem` 이 스스로 원복) |
| `tests/test_puzzle_cache.py` | `PLC0415` | 함수 안 import → 최상단 |
| `tests/test_puzzle_maintenance.py` | `PT011`, `B017` | `pytest.raises(Exception)` + `noqa` → `pytest.raises(RedisError)` |
| `tests/test_word_service.py` | `RUF059` | 안 쓰는 언패킹 변수 `word` → `_word` |

동작 변경은 없고, 수정 후 기존 77개 테스트가 그대로 통과한다.

## 6. 구현 중 실제로 잡은 버그 하나

`@csrf_protected` 의 첫 구현은 `secrets.compare_digest(expected, submitted)` 였는데,
비 ASCII 문자가 든 `str` 을 받으면 `TypeError` 를 낸다. 폼에 한글이 섞인 값을 넣으면
403 이어야 할 요청이 500 이 된다 — 테스트(`test_wrong_token_is_forbidden`)가 한글
값으로 먼저 실패해서 잡혔다. 양쪽을 `encode()` 해 bytes 로 비교하도록 고쳤고,
그 판단을 README "01. CSRF 토큰 방식" 에 남겼다.

## 7. 하지 않은 것 / 남은 것

- 마이그레이션 없음(이 티켓은 스키마를 건드리지 않는다). `flask db heads` 1줄 유지.
- CSRF 헬퍼를 쓰는 라우트 없음 — 티켓 지시대로 헬퍼 + 단위 테스트까지만. 14·15·16 이
  `issue_csrf_token()` / `@csrf_protected` 를 가져다 쓴다.
- `app/clients/` 에는 Slack 하나만 있다. Apple/App Store/Play/Google Books/JWKS 래퍼는
  각 티켓이 같은 패턴(모듈 하나 = provider, 함수 하나 = 외부 호출)으로 추가한다.
- Slack 실제 발송 미확인(외부 호출 금지). 운영자가 `.env` 에 `SLACK_WEBHOOK_URL` 을 넣고
  `uv run flask notify-operator-test` 를 돌리는 단계가 남아 있다 — 스펙 D1 의 "Slack
  Webhook" 항목.
- 스펙 "미정 항목" 은 수정하지 않았다. 다만 **미정 15**(ADR 0003 의 1h TTL 문구)가 "구현 첫
  티켓의 ADR 이관 때" 를 지정하고 있어, `docs/adr/0003` 사본의 재조회 문구를 §A.8 기준
  (`last_verified_at` 1시간 TTL, 만료 ±24h 는 무상한, `next_check_at = last_verified_at + 1h`)
  으로 갱신했다. `.scratch` 원본은 그대로 뒀다.
- `impeccable detect` 가 Jinja `url_for` 링크를 못 푼다 — 웹 UI 티켓(15·18)은 CSS 를 인자로
  같이 주거나 렌더된 URL 을 스캔해야 한다.

## 수정 라운드 1

`review/impl-review-01.md` 라운드 1(판정 FAIL)의 MAJOR 2건·MINOR 1건을 받아 고쳤다. 각 결함은
리뷰에 적힌 재현 명령으로 **먼저 재현**하고, 그 재현을 실패하는 테스트로 고정한 뒤 고쳤다.
BLOCKER·REPEAT 는 없었다.

### D-01-1 (MAJOR) — Slack 실패 로그의 Webhook 비밀 URL 노출 → 수정

**원인.** `app/clients/slack.py` 가 `logger.warning(..., exc_info=True)` 로 requests 예외
전문을 남겼다. `Response.raise_for_status()` 가 만드는 `HTTPError` 는 메시지에
`... for url: <요청 URL>` 을 담고 traceback 에도 URL 이 들어가는데, Slack Incoming Webhook 은
**URL 경로 자체가 인증 비밀**이다. 즉 운영 중 Slack 이 5xx 를 한 번만 돌려줘도 비밀이 로그
수집·열람 경로로 복제되고, 로그는 회수할 수 없다. 증상(로그 한 줄)이 아니라 "예외 객체를
그대로 로그에 넘긴다" 는 원인을 고쳤다.

재현(리뷰의 명령 그대로, 수정 전):

```
result False
url_logged True
```

**수정.** 예외를 로그에 넘기지 않고 **예외 타입 이름과 HTTP 상태 코드만** 남긴다
(`app/clients/slack.py`). `exc_info` 와 `str(exc)` 둘 다 쓰지 않으므로 메시지 경로·traceback
경로가 같이 막힌다. 반환값(실패 시 `False`, 호출자에게 예외 안 올림)·타임아웃 3초·빈 URL
no-op 동작은 그대로다.

**증명.** 같은 재현 명령, 수정 후:

```
result False
url_logged False
logged_line Slack webhook 전송 실패 (HTTPError, status=500)
```

회귀 테스트 2개를 `tests/test_slack_client.py` 에 추가했다. 리뷰가 지적한 "가짜 응답에 URL 이
없어서 못 잡았다" 는 구멍을 먼저 메웠다 — `_RecordingPost` 가 응답에 요청 URL 을 실어주도록
고쳐서, 가짜 응답으로도 실제 `raise_for_status()` 의 에러 메시지가 재현된다.

- `test_failure_log_does_not_leak_webhook_url` — 5xx 경로. 남은 로그 레코드의
  `getMessage()` + `exc_info` traceback 을 합쳐서 URL 과 워크스페이스 토큰(`T000`)이 없는지
  본다. "경고 로그는 남는다" 도 같이 assert 해서, 로그를 아예 지워서 통과하는 수정은 못 한다.
- `test_failure_log_does_not_leak_url_from_exception_message` — 예외 메시지에 URL 이 든
  타임아웃 경로(실제 `requests` 가 이렇게 던진다).

수정 전 두 테스트는 실패하고(`assert 'https://hooks.slac...' not in 'Slack webho...'`,
HTTPError traceback 에 URL 이 그대로 보였다), 수정 후 통과한다.

### D-01-2 (MAJOR) — 원래 세션 쿠키로 소비된 CSRF 토큰 재사용 가능 → 수정

**원인.** Flask 기본 세션은 **서명된 쿠키**라서 상태가 전부 클라이언트에 있다.
`session.pop(SESSION_KEY)` 은 응답 `Set-Cookie` 를 바꾸는 것뿐이고 서버에는 "이 토큰을 썼다"
는 기록이 남지 않는다. 그래서 토큰을 담고 있던 **옛 쿠키를 그대로 다시 보내면** 세션 안의
토큰이 되살아나 다시 통과한다. 새로고침 연타·더블 클릭이 만드는 동시 제출은 애초에 전부
같은 옛 쿠키를 들고 오므로 응답 쿠키로는 구분할 수 없다. 쿠키 세션 안에 머무는 어떤 방법으로도
고칠 수 없고 **서버측 상태**가 필요하다는 것이 원인 진단의 결론이다.

재현(리뷰의 명령 그대로, 수정 전): `200` / `403` / **`200`** — 세 번째가 원래 쿠키 재전송.

**수정.** 검증을 통과한 토큰의 소비 사실을 Redis 에 원자적으로 기록한다(`app/csrf.py`).

- 키는 토큰 원문이 아니라 `csrf:used:<sha256(token)>` — 원문을 키로 쓰면 `KEYS`·`MONITOR`·
  슬로우로그 같은 운영 경로에 아직 유효한 토큰이 남는다.
- 연산은 `SET ... NX EX <ttl>` 하나. "없을 때만 쓰기" 를 왕복 한 번의 원자적 연산으로 하므로
  동시 제출 중 정확히 하나만 `True` 를 받는다. `exists` → `set` 2단계로 쪼개면 둘 다 통과한다.
- TTL 은 `PERMANENT_SESSION_LIFETIME`. Flask 는 세션 쿠키를 풀 때 이 값을 `max_age` 로
  검사하므로(`SecureCookieSessionInterface.open_session`) 그보다 오래된 쿠키는 서명이 맞아도
  세션이 안 열린다 — 그 시점부터는 소비 기록을 들고 있을 이유가 없다. 임의의 상수가 아니다.
- **발급(`issue_csrf_token`)은 Redis 를 건드리지 않는다.** 소비 기록만 서버에 남기면 되고,
  폼을 그리는 GET 이 Redis 장애로 500 이 되면 안 된다.
- 세션 `pop` 은 남겼다 — 보장의 근거는 아니지만, 이미 쓴 토큰을 계속 쿠키에 실어 보내지 않기
  위한 정리다.
- 저장소 선택: 이 레포에서 쓸 수 있는 서버측 상태는 Redis(이미 캐시·레이트리밋·리더보드가
  쓴다)와 MySQL 새 테이블뿐이다. 후자는 마이그레이션 추가라서(이 티켓은 마이그레이션 0개,
  CI head 검사 대상) 피했다.
- **Redis 장애 시 fail-closed(403).** `safe_redis_call` 이 `None` 을 돌려주면 "소비 기록을
  남기지 못했다" 로 보고 통과시키지 않는다. 랭킹·통계는 폴백해서 넘기는 게 맞지만 이
  데코레이터를 쓰는 건 계정 삭제·운영자 폼이라 **"실행 못 함" 보다 "두 번 실행됨" 이 비싸다**.
  1회용 보장이 Redis 상태에 따라 조용히 사라지는 쪽(fail-open)은 같은 결함의 재발이라 택하지
  않았다. 이 판단은 코디네이터에게 `orca orchestration ask` 로 확인 요청을 보냈고(A/B/C 옵션),
  답을 기다리는 동안 추천안 A(fail-closed)로 구현했다. 반대 결정이 오면 `_claim_token` 의
  반환 한 줄로 뒤집을 수 있다.

**증명.** 같은 재현 명령, 수정 후(Redis DB 3): `200` / `403` / `403` — 기대 출력과 일치.

회귀 테스트 3개를 `tests/test_csrf.py` 에 추가했다.

- `test_replayed_original_cookie_cannot_reuse_a_consumed_token` — 리뷰의 재현을 그대로 고정.
  수정 전 실패(`200` 이 와서 403 assert 가 깨짐), 수정 후 통과.
- `test_only_one_of_several_same_cookie_submits_passes` — 같은 원래 쿠키를 든 클라이언트 3개의
  제출 중 하나만 통과(`sorted(statuses) == [200, 403, 403]`). 리뷰가 "동시 요청 역시 소비
  상태를 공유하지 못한다" 고 지적한 경계다. 수정 전 `[200, 200, 200]` 으로 실패, 수정 후 통과.
- `test_submit_is_forbidden_while_redis_is_down` — `broken_redis` fixture 로 Redis 장애를 만들고
  403 을 확인한다. fail-closed 를 테스트로 못 박아서, 나중에 조용히 fail-open 으로 바뀌면 깨진다.

기존 CSRF 테스트 7개(발급·성공·누락·한글 오입력·일반 재전송·실패가 유효 토큰을 태우지 않음)는
그대로 통과한다 — 틀린 값을 던진 요청은 비교 단계에서 막혀 소비 기록을 남기지 않는다.

README `### 01. CSRF 토큰 방식` 의 설계 판단을 실제 구현에 맞게 갱신했다(서명 쿠키 세션의
한계, `SET NX` 와 TTL 근거, fail-closed 선택). `### 01. Slack Webhook 선택 근거` 에는 실패
로그에 URL 을 넣지 않는 이유를 한 단락 추가했다.

### D-01-3 (MINOR) — 공유 파일 append 규칙 위반 → 일부 수정, 일부 반론

**수정한 것(2곳).** 티켓 공통 규칙("자기 행/자기 번호 소제목만 섹션 끝에 덧붙인다")대로 옮겼다.

- `.env.example`: `SLACK_WEBHOOK_URL` 블록을 Redis 설정과 도서 API 키 사이 삽입에서
  **파일 끝**으로 이동. 다른 티켓이 건드리는 중간 영역을 더 이상 차지하지 않는다.
- `README.md`: `### 01.` 소제목 3개를 기존 `### 19.` **뒤**(설계 판단 절 끝)로 이동. 내용은
  그대로이고 위치만 바뀌었다. `git diff main...HEAD -- README.md` 에서 19절 내용은 변경 0줄.

**고치지 않은 것(1곳) — 근거.** 설계 판단 절 머리의 공통 안내(`> 아래 ... 이 절 끝에
덧붙인다`) 는 그대로 뒀다. 이 티켓이 그 안내를 넣으라고 **명시적으로 지시받은 작업**이기
때문이다:

- 티켓 체크박스: "README '설계 판단' 절을 `### NN.` 소제목 구조로 **시작하고** …"
  (`.scratch/store-launch/issues/01-prefactor-lint-docs-clients.md`)
- 같은 파일 리뷰 노트 P1-13: "병렬 티켓의 공유 파일 … 충돌 규칙은 **이 티켓이 README
  구조(`### NN.`)로 시작하고 전 티켓 공통 규칙 줄로 반영함**"

즉 "공통 위치 변경은 코디네이터에게" 라는 일반 규칙과 "01 이 이 구조를 시작한다" 는 티켓
지시가 충돌하는 자리이고, 후자가 이 티켓에 대한 더 구체적인 지시다. 이 안내가 없으면 02 이후
티켓들은 `### NN.` 규칙을 README 안에서 읽을 곳이 없다. 코디네이터가 다르게 판단하면 그 세
줄만 지우면 되고 다른 변경에는 영향이 없다.

### 미수정 MINOR / 리뷰어 지적에 대한 기타 메모

- 리뷰 "참고 및 한계" 의 테스트 개수 불일치(`test_slack_client.py` 4개를 5개로 적음)는 이
  문서의 수치 오류였다. 이번 라운드에서 2개를 추가해 **6개**가 됐다. 결함으로 세지 않은
  항목이지만, 숫자를 쓰는 대신 아래 실행 출력으로 대체한다.
- 체크박스 2(`impeccable init` 산출물)의 "증거 부족" 은 PATH 에 실행 파일이 없어 리뷰어가
  독립 실행을 못 한 것이고, 결함으로 제기되지 않았다. 산출물(`.impeccable/config.json`,
  `PRODUCT.md` 의 DESIGN_DIR 두 경로)은 커밋돼 있다. 이번 라운드에서 건드리지 않았다.
- ADR 0003 도입부/후반 설명 혼재, 문서 테스트가 ADR 을 3개로 고정하는 점은 리뷰어가 이 티켓
  결함으로 세지 않은 향후 참고 사항이라 손대지 않았다(수정 범위 초과 금지).

### 수정 라운드 1 최종 검증

전용 자원으로만 돌렸다: DB `chosung_daily_test_t01`, Redis DB 3. 공용 테스트 DB·Redis DB 1 은
건드리지 않았다.

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t01... TEST_REDIS_URL=redis://127.0.0.1:6379/3 \
    uv run pytest -q --tb=short
108 passed in 36.08s

$ ... uv run pytest -q tests/test_csrf.py tests/test_slack_client.py
16 passed in 11.77s

$ FLASK_APP=wsgi.py FLASK_ENV=testing ... ./scripts/check_migration_heads.sh
9ec267465b4e (head)
OK: Alembic head 1개
```

라운드 1 시작 시 103개였던 테스트가 108개다(추가 5개: Slack 2, CSRF 3). 새 마이그레이션 없음,
`flask db heads` 1줄 유지. 로컬 `main`(`feb2553`) 위로 rebase 된 상태이고 작업 트리는 clean 이다.
변경 파일은 `app/clients/slack.py`, `app/csrf.py`, `tests/test_slack_client.py`,
`tests/test_csrf.py`, `README.md`, `.env.example`, 이 문서. `review/impl-review-01.md` 는
수정하지 않았다.
