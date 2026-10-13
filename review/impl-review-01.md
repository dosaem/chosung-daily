# 티켓 01 최종 리뷰 — 라운드 1

- 기준: 로컬 `main` = `feb2553`, 구현 HEAD = `56fe3e5`; `git diff main...HEAD`, `git log main..HEAD` 직접 확인(10커밋, 30파일). origin/main 미사용.
- 범위: 티켓 01, 스펙 §A.7·A.11·A.12·A.17·C.31·C.32·Further Notes, 구현 증거와 변경 파일. UI 변경 없음.
- 결함: BLOCKER 0 / MAJOR 2 / MINOR 1. 애플리케이션·테스트·설정·계획 원본은 수정하지 않았다.

## 체크박스별 확인

| # | 요구 | 결과 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | CONTEXT/ADR 루트 이관 및 domain.md 경로 일치 | 충족 | 원본과 사본 diff 확인: 정본 안내 추가, ADR 0003의 §A.8 재조회 갱신 외 내용 보존. `docs/agents/domain.md` 경로와 일치하고 문서 테스트 3개 통과. |
| 2 | impeccable init 산출물 및 DESIGN_DIR 두 경로 | 증거 부족 | `.impeccable/config.json`과 `PRODUCT.md:76` 이후 두 경로·OVERRIDES 우선순위가 커밋되어 있음. 현재 PATH에 impeccable 실행 파일이 없어 init 실행 및 도구가 문서를 소비하는지는 독립 검증하지 못함. 구현 증거의 코디네이터 승인 인용을 확인된 실행 증거로 간주하지 않음; 산출물 자체의 요구 의도는 충족. |
| 3 | ruff PL/RUF/SIM/PT 및 기존 코드 정리 | 충족 | `pyproject.toml` select와 제한된 per-file 예외 근거 주석 확인, 신규 noqa 없음. `uv run ruff check .` exit 0. |
| 4 | CI 단일 migration head 검사 | 충족 | CI가 실행 가능한 `scripts/check_migration_heads.sh` 호출. 실제 실행 결과 head 1개 및 exit 0. 신규 migration 없음. |
| 5 | Slack 래퍼·3초·실패 로그·빈 URL no-op | 미충족 | 호출 인자·빈 URL·실패 반환 동작은 확인했으나 실패 로그가 비밀 Webhook URL 전체를 노출(D-01-1). |
| 6 | notify_operator 및 monkeypatch 호출 인자 검증 | 충족 | 제목/본문을 `[오늘의 초성] kind\nmessage`로 전달. 직접 monkeypatch 호출 검증 및 해당 테스트 코드 확인; 네트워크 없음. |
| 7 | 세션 1회용 CSRF·403 FORBIDDEN·재사용 거부 | 미충족 | 발급·누락·한글 오입력·일반 재전송은 올바름. 원래 쿠키를 그대로 쓰는 재요청은 200으로 통과하여 1회용 보장이 없음(D-01-2). |
| 8 | README 번호 구조·설계 판단 3개 | 충족 | `### 01.` 항목 3개와 번호 규칙 안내 존재, 기존 `### 19.` 내용 보존. 다만 절 끝 추가 규칙은 D-01-3 참조. |
| 9 | SLACK_WEBHOOK_URL 예시 추가·실제 환경값 불변 | 충족 | 빈 값만 추가. `.env`·`.env.prod.example` 변경 없음. 추가 위치 규칙은 D-01-3 참조. |

## 실제 실행한 검증

- `uv run ruff check .` → `All checks passed!`, exit 0.
- `FLASK_APP=wsgi.py FLASK_ENV=testing ... ./scripts/check_migration_heads.sh` → `9ec267465b4e (head)` 한 줄, `OK: Alembic head 1개`, exit 0. 이때 DB는 r01, Redis는 15로 지정했으며 migration 적용은 하지 않았다.
- 전용 `TEST_DATABASE_URL`의 DB 이름을 `chosung_daily_test_r01`로, `TEST_REDIS_URL`을 로컬 DB 15로 지정해 `uv run pytest -q --maxfail=1 --tb=short` 실행: 첫 fixture에서 MySQL 1044 접근 거부, `1 error`. 로컬 MySQL/Redis는 존재하며 Redis DB 15 `PING` 성공. 인증 정보 없는 최초 시도는 MySQL 1045였다.
- 코디네이터 후속 메시지 `msg_b015e9ee37d5`가 기본 테스트 DB 사용을 명시적으로 허용했다. 따라서 `env -u TEST_DATABASE_URL TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q --tb=short`로 재실행했다. 결과는 아래 최종 실행 결과에 기록한다.
- `uv run pytest -q tests/test_domain_docs.py` → `3 passed in 0.01s`.
- 메모리 안의 Flask 앱과 실제 헬퍼로 CSRF 발급/성공/누락/한글 오입력/일반 재전송을 검증했고, Slack requests 경계만 monkeypatch하여 no-op·JSON 본문·timeout=3, 알림 서비스 제목/본문 전달을 assert했다. 모두 통과. 외부 호출 0건.
- 아래 두 재현은 실제 구현 함수를 호출한다. 쿠키/토큰 값은 출력·문서 저장하지 않고, Slack 응답 URL은 비밀값이 아닌 `.invalid` 테스트 주소만 사용했다.

## 결함

### D-01-1 — MAJOR — Slack 실패 로그에 Webhook 비밀 URL 노출

- 위치: `app/clients/slack.py:29`; 테스트 누락: `tests/test_slack_client.py:25`의 가짜 Response에는 실제 응답과 달리 URL이 없다.
- 원인: `exc_info=True`로 requests 예외 전문을 기록한다. 실제 `Response.raise_for_status()`의 HTTPError에는 요청 URL이 포함되며 Slack Incoming Webhook은 URL 경로 자체가 인증 비밀이다. 운영 오류 시 로그 수집/열람 경로에 이 값이 복제된다.
- 재현: 아래 명령. 기대 `False` 반환과 비밀 URL 없는 경고(`url_logged False`), 실제 `result False`, `url_logged True`.

```sh
uv run python - <<'PY'
import io
import logging
from unittest.mock import patch
import requests
from flask import Flask
from app.clients.slack import logger, post_webhook_message
app = Flask(__name__)
r = requests.Response()
r.status_code = 500
r.url = 'https://example.invalid/services/REVIEW_SENTINEL'
app.config['SLACK_WEBHOOK_URL'] = r.url
out = io.StringIO()
h = logging.StreamHandler(out)
logger.addHandler(h)
with app.app_context(), patch('app.clients.slack.requests.post', return_value=r):
    print('result', post_webhook_message('review'))
print('url_logged', r.url in out.getvalue())
logger.removeHandler(h)
PY
```

- 필요한 수정: URL·예외 원문을 남기지 않는 안전한 오류 로그와 URL 비노출 회귀 검증.

### D-01-2 — MAJOR — 원래 세션 쿠키로 소비된 CSRF 토큰 재사용 가능

- 위치: `app/csrf.py:48`; 누락된 경계: `tests/test_csrf.py:74`의 재사용 테스트는 갱신된 쿠키만 사용한다.
- 원인: Flask 기본 서명 쿠키 세션에서 `session.pop`은 응답 쿠키를 바꿀 뿐 서버에 소비 사실을 보관하지 않는다. 동일한 원래 쿠키를 가진 중복/동시 요청은 모두 같은 유효 토큰을 복원해 보호된 함수를 실행한다. 티켓의 1회용 요구와 README의 중복 실행 방지 설명을 만족하지 못한다. 이는 토큰을 모르는 공격자의 일반 CSRF 우회를 입증한 것이 아니라, 명시한 재사용 방지 보장의 결함이다.
- 재현: 아래 명령. 기대 첫 제출 200, 이후 모두 403. 실제 `200`, `403`, **`200`**. 원래 쿠키가 같은 동시 요청 역시 소비 상태를 공유하지 못한다.

```sh
uv run python - <<'PY'
import secrets
from flask import Flask
from app.csrf import csrf_protected, issue_csrf_token
from app.errors import register_error_handlers
app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
register_error_handlers(app)
app.add_url_rule('/issue', 'issue', lambda: {'token': issue_csrf_token()})
app.add_url_rule('/submit', 'submit', csrf_protected(lambda: {'ok': True}), methods=['POST'])
c = app.test_client()
t = c.get('/issue').json['token']
original = c.get_cookie('session').value
print(c.post('/submit', data={'csrf_token': t}).status_code)
print(c.post('/submit', data={'csrf_token': t}).status_code)
c.set_cookie('session', original)
print(c.post('/submit', data={'csrf_token': t}).status_code)
PY
```

- 필요한 수정: 서버가 토큰 소비를 원자적으로 기억하도록 하여 동일 쿠키 재전송/동시 제출도 거부하고 해당 경계를 테스트할 것.

### D-01-3 — MINOR — 공유 파일의 끝에 추가해야 하는 규칙 위반

- 위치: `.env.example:8`, `README.md:285`.
- 요구: 티켓 공통 규칙은 공유 파일/절에 자기 번호 소제목 또는 자기 행을 **끝에 덧붙이고**, 번호순 통합은 코디네이터가 하도록 정했다.
- 재현: `git diff main...HEAD -- .env.example README.md`. 기대 Slack 환경변수는 파일 끝, 설계 판단은 기존 19절 뒤에 추가. 실제 환경변수는 Redis와 기존 도서 API 설정 사이에 삽입하고 01절은 기존 19절 앞에 삽입했다. 또한 설계 판단 절 앞의 공통 안내를 수정했다. 타 티켓 내용 삭제는 없으나 정해진 병렬 편집 경계를 벗어나 통합 충돌 가능성을 높인다.
- 필요한 수정: 새 자기 행/절을 지정된 append 위치로 이동하고 공통 위치의 변경은 코디네이터에게 맡길 것. 스타일 취향이 아니라 티켓의 명시적인 병렬 작업 규칙 위반이다.

## 참고 및 한계

- 실서비스 호출, NAS 접근, 배포, push 없음. 변경 파일에서 실제 키/토큰/비밀번호 추가는 발견하지 못했다. D-01-1은 저장소에 현재 비밀이 있다는 주장이 아니라 운영 실패 시 로그로 새어 나오는 실행 경로다.
- 테스트들은 실제 함수를 호출하며 항상 통과하는 assertion은 발견하지 못했다. 다만 CSRF 쿠키 갱신과 URL 없는 Slack 응답 대역이 각각 위 결함을 놓쳤다.
- 증거 문서의 테스트 파일별 숫자는 그대로 믿을 수 없다(`test_slack_client.py`는 5개가 아니라 4개). 그 숫자 차이는 별도 제품 결함으로 세지 않았다.
- 문서 테스트가 ADR 목록을 정확히 3개로 고정하는 점, ADR 0003 도입부의 예전 설명과 후반 상태 판정 설명이 혼재하는 점은 향후 문서 확장 때 참고할 사항이다. 이번 복사 티켓의 별도 결함으로 추가하지 않았다.

## 최종 실행 결과

`env -u TEST_DATABASE_URL TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q --tb=short` → **103 passed in 41.17s**, exit 0. 코디네이터가 허용한 기본 로컬 테스트 DB로 1회 실행하여 통과했으며, 공유 자원 충돌로 인한 재실행은 없었다. 테스트 통과와 별개로 D-01-1·D-01-2를 독립 재현했으므로 FAIL이다.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` = `feb2553`, 구현 HEAD = `c17379f`. `git log main..HEAD` 12커밋 및 `git diff main...HEAD` 31파일을 직접 확인했다. origin/main은 사용하지 않았다.
- 범위: 티켓 01의 9개 체크박스, 스펙 §A.7·A.11·A.12·A.17·C.31·C.32·Further Notes, 구현 증거와 이전 리뷰. UI 변경은 없다.
- 현재 결함: BLOCKER 0 / MAJOR 0 / MINOR 0. 이전 결함 3개는 모두 FIXED로 판정하며 새 결함은 없다.

### 체크박스별 확인

| # | 요구 | 결과 | 직접 확인한 근거 |
|---|---|---|---|
| 1 | CONTEXT/ADR 루트 이관 및 domain.md 경로 일치 | 충족 | 원본/사본과 `docs/agents/domain.md`를 대조했다. 정본 안내와 ADR 0003의 스펙 재조회 설명 외 원본 내용이 보존되고 `.scratch/` 변경은 없다. |
| 2 | impeccable init 산출물 및 DESIGN_DIR 두 경로 | 증거 부족 | 설정과 `PRODUCT.md:76` 이후 두 경로·OVERRIDES 우선순위가 커밋되어 있다. 현재 PATH에 impeccable이 없어 init 실행 자체와 도구의 소비는 독립 검증할 수 없었다. 이전 라운드와 동일한 검증 한계이며 새 결함으로 세지 않는다. |
| 3 | ruff PL/RUF/SIM/PT 및 기존 코드 정리 | 충족 | 규칙 추가, 두 순환 import 파일 및 테스트 매직값의 제한된 예외와 근거 주석 확인. ruff 직접 실행 통과. |
| 4 | CI 단일 migration head 검사 | 충족 | CI가 실행 가능한 검사 스크립트를 호출한다. 실제 head 출력은 1줄이며 스크립트 exit 0. 신규 migration 없음. |
| 5 | Slack 래퍼·3초·실패 로그·빈 URL no-op | 충족 | requests 경계만 대체하는 테스트와 구현 확인. 이전 URL 유출 재현을 다시 실행하여 실패 반환·경고 존재·URL 비노출 확인(D-01-1). |
| 6 | notify_operator 및 monkeypatch 호출 인자 검증 | 충족 | 실제 서비스가 제목과 본문을 조립하며 래퍼 monkeypatch로 태그·제목·줄바꿈·본문과 실패 반환을 검증한다. |
| 7 | 세션 1회용 CSRF·403 FORBIDDEN·재사용 거부 | 충족 | 비교 후 Redis `SET NX EX` 성공 시에만 실행. 원래 쿠키 재전송 회귀 검증과 별도 6개 동시 요청 확인(D-01-2). 미적용 헬퍼이며 실제 앱 라우트는 바꾸지 않았다. |
| 8 | README 번호 구조·설계 판단 3개 | 충족 | `### 01.` 3개가 기존 19절 뒤에 추가됐다. 공통 안내는 티켓 P1-13의 명시적 구조 도입 지시로 인정(D-01-3). |
| 9 | SLACK_WEBHOOK_URL 예시 추가·실제 환경값 불변 | 충족 | `.env.example` 끝에 빈 값 추가. `.env`·`.env.prod.example` 변경 없음. |

### 이전 결함 판정

- **D-01-1 — FIXED (이전 MAJOR)** — `app/clients/slack.py:28-36`. 이전 라운드의 `.invalid` URL을 가진 실제 `requests.Response(status=500)` 재현을 그대로 실행했다. 기대와 실제 모두 `result False`, `url_logged False`, `warning_present True`. 예외 원문과 traceback 대신 예외 타입/상태 코드만 기록한다. HTTP 오류 및 URL을 포함한 Timeout 회귀 테스트가 메시지와 traceback을 모두 검사한다.
- **D-01-2 — FIXED (이전 MAJOR)** — `app/csrf.py:43-45,92-95`. 원래 쿠키를 복원하는 테스트가 403을 검증한다. 추가로 메모리 Flask 앱에 실제 헬퍼와 로컬 Redis DB 15를 연결하고, 토큰 발급 당시 쿠키를 6개 클라이언트에 복사해 `ThreadPoolExecutor(max_workers=6)`로 POST했다. 기대와 실제 정렬 상태가 모두 `[200, 403, 403, 403, 403, 403]`이고 소비 키 TTL도 양수였다. 검증 후 해당 임시 키만 삭제했다. Redis 장애 시 403으로 닫히며 오입력은 정상 토큰을 소비하지 않는다.
- **D-01-3 — FIXED (이전 MINOR)** — `.env.example:33-36`, `README.md:306,321,342`. `git diff main...HEAD -- .env.example README.md` 재확인 결과 환경변수는 파일 끝, 01 소제목들은 기존 19절 뒤인 설계 판단 절 끝에 추가되었다. 기대 append 위치와 실제가 일치하고 19절 내용은 보존됐다. 공통 안내에 대한 이전 지적은 철회한다: 티켓 리뷰 노트 P1-13이 01에 공통 규칙 줄과 번호 구조 도입을 명시적으로 맡겼으므로 이 안내는 허용된 작업이다.

### 직접 실행한 검증

- `uv run ruff check .` → `All checks passed!`, exit 0.
- `env -u TEST_DATABASE_URL FLASK_APP=wsgi.py FLASK_ENV=testing TEST_REDIS_URL=redis://127.0.0.1:6379/15 ./scripts/check_migration_heads.sh` → `9ec267465b4e (head)` 1줄 및 `OK: Alembic head 1개`, exit 0. 마이그레이션 적용 없음.
- `env -u TEST_DATABASE_URL TEST_REDIS_URL=redis://127.0.0.1:6379/15 uv run pytest -q --tb=short` 첫 실행 → `106 passed, 3 errors in 40.72s`. Slack 테스트 teardown의 MySQL 3730 FK drop 충돌 및 stats 테스트 setup의 MySQL 1684 `definition is being modified by concurrent DDL statement` 등 공유 DB 충돌이 발생했다. 기본 DB `chosung_daily_test`를 사용했고 새 DB를 만들지 않았다. 지시에 따라 같은 명령으로 1회 재실행했다.

### 참고 및 한계

- `test_only_one_of_several_same_cookie_submits_passes` 자체는 순차 제출이다. 이번 리뷰에서 실제 스레드 동시 제출을 추가 확인했으므로 현재 구현 결함으로 올리지 않는다.
- Redis에 소비 기록이 유지되는 조건에서 1회용을 보장한다. Redis 장애 시 fail-closed 선택은 구현·README·회귀 테스트가 일치한다.
- 외부 서비스 호출, 프로덕션/NAS 접근, 배포, push 없음. 변경 파일에서 실제 시크릿 추가나 새로운 인증 우회·데이터 손상 경로를 발견하지 못했다. Slack의 테스트 주소는 가짜 값이다.
- 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았다. 소유 파일인 이 리뷰 문서만 갱신한다.

### 재실행 결과와 최종 판단

동일 명령의 두 번째 실행도 공유 DB 동시 DDL 충돌이 계속되어 **`2 failed, 66 passed, 44 errors in 25.88s`**, exit 1이었다. MySQL 1684가 여러 fixture의 create/drop에서 반복되었다. 따라서 **이번 라운드에서 전체 스위트 통과는 확인하지 못했다**. 첫 실행에서 CSRF·Slack 신규 테스트 본문이 실행됐고 독립 Slack 재현 및 실제 동시 CSRF 제출은 통과했지만, 이를 전체 회귀 통과로 대체하지 않는다. 공유 DB를 독점할 수 있는 시점의 전체 재검증은 코디네이터에게 남긴다. 티켓 변경에 귀속되는 새 제품 결함은 확인되지 않았으며, PASS는 이전 결함 수정에 대한 코드 리뷰 판정이다.

판정: PASS
