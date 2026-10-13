# 티켓 08 구현 증거 — 앱 설정 `/config`·헬스체크 고도화·Sentry 백엔드

- 브랜치: `dosaem/t08-app-config-health-sentry`, 로컬 `main` **72a2a3c**(티켓 21 머지) 위로
  `git rebase main` 완료 — 충돌 없음, 작업 트리 clean
- 커밋 4개, `main..HEAD` 변경 20파일 (+624 / -4)
- 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t08`, Redis DB **10**,
  마이그레이션 왕복용 별도 DB `chosung_daily_test_t08_migrations`
  (`TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL` 로 지정).
  공용 `chosung_daily_test`·Redis 1 과 다른 워커의 DB/Redis DB 는 건드리지 않았다.
  공용 개발 DB `chosung_daily` 에도 마이그레이션을 걸지 않았다 — 수동 확인은 전부
  내 `_t08_migrations` DB 에서 했다.
- 외부 서비스 호출 0건. Sentry 는 `sentry_sdk.init` 을 가로채거나(테스트) 가짜 DSN 으로
  초기화만(수동 확인) 했고 이벤트를 보낸 적 없다. NAS 접속·배포·`git push` 없음.
- UI 변경 없음(API·설정·관측 티켓). `impeccable detect`/`audit.native` 대상 화면이
  없어서 돌리지 않았다 — 티켓 완료 조건에도 없다.
- 시크릿 값은 어떤 파일·로그에도 쓰지 않았다. 추가한 설정은 이름만:
  `STORE_URL_IOS`, `STORE_URL_ANDROID`, `APP_STORE_ID`, `SENTRY_DSN`, `SENTRY_RELEASE`
  (`.env.example` 에 빈 값 예시만). `.env`, `.env.prod*` 실제 값은 열지도 않았다.

## 코디네이터 확정 사항 (`orca orchestration ask`)

1. **경로는 `/api/v1/config`**. 스펙 §A' 표의 prefix `/api/v1` 은 JSON API 에 적용되고,
   `/health` 는 현행 코드·README·배포 스크립트·업타임 모니터가 보는 루트를 유지한다.
   README API 표에 두 경로를 그대로 적고 "설계 판단 08" 에 이 구분을 남겼다.
2. **`APP_STORE_ID` 는 `/config` 응답에 넣지 않는다** — 스펙 응답 필드는 4개뿐이다.
   Flask 설정값으로만 두고 티켓 18 이 서버 렌더링(Smart App Banner)에서 쓴다.

## 1. 실행한 명령과 출력

### 전체 테스트 스위트 (rebase 후)

```
$ TEST_DATABASE_URL=...chosung_daily_test_t08 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/10 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t08_migrations \
  uv run pytest -q
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
203 passed in 79.83s (0:01:19)
```

**실패·skip·xfail 0건.** 수집 기준 203개 중 내 파일 4개가 22개
(`pytest --collect-only -q tests/test_app_config.py tests/test_health.py
tests/test_sentry.py tests/test_migrations.py` → `22 tests collected`)이고, 그중
기존 것이 5개(`test_health.py` 1 + `test_migrations.py` 4)라 **신규 17개**다:

| 파일 | 개수 | 내용 |
|---|---|---|
| `tests/test_app_config.py` | 7 | `/api/v1/config` 기본값·설정 행 반영·캐시·Redis 장애 |
| `tests/test_health.py` | 4 (기존 1 교체) | ok / degraded / 503 / 둘 다 죽음 |
| `tests/test_sentry.py` | 5 | DSN 없을 때 꺼짐, 태그·통합, create_app 배선 |
| `tests/test_migrations.py` | +2 (4 → 6) | `app_setting` 생성·되돌리기 왕복, ORM 없이 행 쓰기 |

작업 시작 시점의 `main`(4f9f179, 티켓 02 머지 상태)은 **146 passed** 였고, 작업 중
티켓 19·21 이 머지돼 rebase 대상 `main`(72a2a3c)의 baseline 이 늘었다. 실측으로
맞춰봤다 — `git checkout --detach main && uv run pytest --collect-only -q` →
`186 tests collected`, 내 브랜치는 `203 tests collected`. 203 = 186 + 17.

### 린트

```
$ uv run ruff check .
All checks passed!
```

### 마이그레이션 head (1줄)

```
$ FLASK_APP=wsgi.py DATABASE_URL=...chosung_daily_test_t08_migrations \
  ./scripts/check_migration_heads.sh
ff06a1bf5afc (head)
OK: Alembic head 1개
```

### 마이그레이션 왕복 (별도 DB, `flask db` 서브프로세스)

```
$ uv run pytest tests/test_migrations.py -q
......                                                                   [100%]
6 passed in 18.86s
```

TDD 의 red 도 확인했다 — 마이그레이션 파일을 잠시 치우고 돌리면 두 테스트가 깨진다:

```
$ mv migrations/versions/ff06a1bf5afc_*.py /tmp/scratch/ && uv run pytest tests/test_migrations.py -q -k app_setting
FAILED tests/test_migrations.py::test_app_setting_table_round_trips - Asserti...
FAILED tests/test_migrations.py::test_app_setting_rows_written_without_the_orm_are_readable
2 failed, 4 deselected in 5.44s
```

### 실제 서버로 수동 확인 (`flask run`, 내 `_t08_migrations` DB + Redis DB 10)

설정 행 3개를 DB 에 직접 넣은 상태(= 운영자가 DB 행으로 바꾸는 그 경로):
`maintenance_enabled=true`, `maintenance_message=00:00~01:00 서버 점검 중입니다`,
`min_app_version_ios=1.2.0`.

```
### 1) 정상 (DB+Redis 살아있음), 스토어 링크 환경변수 설정
$ curl -s localhost:5108/api/v1/config
{
  "languages": ["ko", "en"],
  "maintenance": { "enabled": true, "message": "00:00~01:00 서버 점검 중입니다" },
  "min_app_version": { "android": "1.0.0", "ios": "1.2.0" },
  "store_urls": {
    "android": "https://play.google.com/store/apps/details?id=com.dosaem.chosung",
    "ios": "https://apps.apple.com/app/id1234567890"
  }
}
$ curl -s -w "<HTTP %{http_code}>" localhost:5108/health
{"apple_secret_expires_at":null,"db":"ok","redis":"ok","status":"ok"}  <HTTP 200>

### 2) Redis 장애 (REDIS_URL 을 죽은 포트 6399 로)
$ curl -s -w "<HTTP %{http_code}>" localhost:5108/health
{"apple_secret_expires_at":null,"db":"ok","redis":"down","status":"degraded"}  <HTTP 200>
$ curl -s localhost:5108/api/v1/config | head -c 120
{"languages":["ko","en"],"maintenance":{"enabled":true,...   (200, 캐시 없이 DB 에서)

### 3) DB 장애 (DATABASE_URL 을 죽은 포트 3399 로)
$ curl -s -w "<HTTP %{http_code}>" localhost:5108/health
{"apple_secret_expires_at":null,"db":"down","redis":"ok","status":"down"}  <HTTP 503>
```

스토어 링크 환경변수가 비어 있을 때(기본값)는 같은 요청이 `"store_urls":
{"android":null,"ios":null}` 를 돌려준다 — 위 2)·3) 서버는 환경변수를 안 줬고,
1) 전에 돌린 서버 응답으로 확인했다.

### 실제 Sentry 초기화 (가짜 DSN, 이벤트 전송 없음)

```
$ SENTRY_DSN='https://examplepublickey@o0.ingest.sentry.io/0' \
  SENTRY_RELEASE='t08-local-check' uv run python -c "...create_app('production')..."
active: True
environment: production
release: t08-local-check
send_default_pii: False
integrations: ['argv', 'atexit', 'celery', 'dedupe', 'excepthook', 'flask',
               'logging', 'modules', 'redis', 'sqlalchemy', 'stdlib', 'threading']

$ uv run python -c "...create_app('production') without SENTRY_DSN..."
active: False
```

`flask`·`celery` 통합이 둘 다 붙고, DSN 이 없으면 클라이언트가 아예 비활성이다.

## 2. 티켓 체크박스별 근거

| 체크박스 | 구현 | 증명하는 테스트/명령 |
|---|---|---|
| `AppSetting`(키·값) 테이블 + 마이그레이션, head 1개 | `app/models/app_setting.py`, `migrations/versions/ff06a1bf5afc_*.py` | `tests/test_migrations.py::test_app_setting_table_round_trips`, `::test_app_setting_rows_written_without_the_orm_are_readable`, `./scripts/check_migration_heads.sh` → `OK: Alembic head 1개` |
| `GET /config` 가 `min_app_version{ios,android}`·`maintenance{enabled,message}`·`languages`·`store_urls{ios,android}` 를 돌려준다 | `app/api/config.py`, `app/services/app_config_service.py`, `app/schemas/config.py` | `test_app_config.py::test_config_needs_no_auth_and_returns_defaults`(응답 전체를 dict 비교), `::test_config_reflects_setting_rows`, 수동 확인 1) |
| 인증 없음 | 블루프린트에 `with_guest`/세션 가드 없음 | `test_config_needs_no_auth_and_returns_defaults`(헤더 없이 200) |
| 캐시 60초 | `CACHE_TTL_SECONDS = 60`, `safe_redis_call("set", ..., ex=...)` | `::test_config_is_cached_so_a_changed_row_is_not_seen_right_away`, `::test_config_cache_expires_within_a_minute`(실제 Redis TTL 확인) |
| `store_urls`·`APP_STORE_ID` 출처는 환경변수, 등록 전 빈 값 허용 → 응답 null | `app/config.py` 의 `STORE_URL_IOS`/`STORE_URL_ANDROID`/`APP_STORE_ID` | `::test_store_urls_come_from_the_environment`, `::test_config_needs_no_auth_and_returns_defaults`(빈 값 → null) |
| `.env.example` 에 추가 | `.env.example` `# [08]` 블록 2개 | 파일 diff (값은 비워둔 예시만) |
| 18 의 웹 배지·메타 태그도 같은 설정값 | `APP_STORE_ID` 를 Flask 설정값으로 두고 `/config` 응답에는 넣지 않음(코디네이터 확정 2) | `app/config.py` 주석 + README "설계 판단 08" + `.env.example` 주석이 티켓 18 을 가리킨다 |
| `GET /health` 가 `{status, db, redis, apple_secret_expires_at}` | `app/api/health.py` | `test_health.py::test_health_is_ok_when_db_and_redis_are_up`(응답 전체 dict 비교) |
| DB 실패 503 | `return jsonify(body), 200 if db_ok else 503` | `::test_health_is_503_when_db_is_down`, `::test_health_reports_db_down_even_if_redis_is_also_down`, 수동 확인 3) |
| Redis 실패 200 + `degraded` (`test_redis_failure_fallback.py` 패턴) | `safe_redis_call("ping", default=False)` | `::test_health_is_degraded_but_still_200_when_redis_is_down`(기존 `broken_redis` fixture 그대로 사용), 수동 확인 2) |
| `apple_secret_expires_at` null 허용 (11 에서 채움) | 지금은 `None` 고정 + 티켓 11 을 가리키는 주석 | 위 두 `test_health` 테스트가 `None` 을 단정 |
| `sentry_sdk` Flask·Celery 통합이 `SENTRY_DSN` 있을 때만 활성 | `app/observability.py`, `create_app()` 에서 한 번 호출 | `test_sentry.py::test_sentry_stays_off_without_a_dsn`, `::test_sentry_init_registers_both_flask_and_celery_integrations`, `::test_create_app_initializes_sentry`, 실제 초기화 확인(위) |
| 릴리스·환경 태그 포함 | `environment=ENV_NAME`, `release=SENTRY_RELEASE or None` | `::test_sentry_init_carries_release_and_environment_tags`, `::test_release_is_omitted_when_not_set`, 실제 초기화 확인(`environment: production`, `release: t08-local-check`) |
| README "설계 판단" 에 "점검·최소 버전을 서버 설정으로", "헬스체크 등급" 추가 | `### 08.` 두 소제목 | README 172~ 절, diff |
| 운영 절에 UptimeRobot 등록(사람) 메모 | `## 운영: 업타임 모니터` | README 159~ 절 |

## 3. 설계 판단 요약 (자세한 근거는 README "설계 판단 08")

- **점검·최소 버전은 DB 행**: 환경변수면 값을 바꿀 때 재배포(=재시작)가 필요하다.
  스토어 심사를 다시 받지 않고 끄고 켜야 하는 값이라 `app_setting` 키·값 테이블에 뒀다.
- **기본값은 코드에만**: 마이그레이션이 기본값 행을 심지 않는다(두 벌이 어긋나는 걸
  피함). 빈 테이블에서도 `/config` 가 정상 응답한다 — 테스트 첫 줄이 그걸 본다.
- **점검 플래그는 꺼진 쪽으로 기운다**: `"true"`/`"1"` 만 참. 오타로 전체 유저가 점검
  화면을 보는 쪽이 훨씬 비싸다.
- **헬스체크 등급**: DB 는 503(게임 불가), Redis 는 200+degraded(캐시·랭킹만 빠짐).
  업타임 모니터가 "깨울 상태" 만 실패로 보게 하려는 것. README 에 "UptimeRobot 에서
  keyword 로 `status: ok` 를 보면 degraded 에도 알람이 울린다" 는 함정을 적어뒀다.
- **Sentry 초기화 지점은 `create_app()` 하나**: 워커·Beat 도 `celery_app.py` 에서 같은
  `create_app()` 을 거치니 Flask·Celery 통합을 여기서 같이 등록하면 설정이 한 벌이다.

## 4. 남은 것 / 하지 않은 것

- **`AppSetting` 쓰기 경로(토글 UI)는 티켓 16** 담당이라 읽기만 구현했다. 그래서
  리포지토리에 `find_all_settings()` 하나뿐이고 쓰기 함수는 없다(쓰지 않을 코드를 미리
  두지 않았다). 운영자가 DB 행을 직접 넣는 경로는 마이그레이션 테스트가 검증한다.
- **`apple_secret_expires_at` 은 `null` 고정** — 티켓 11(애플 secret 요청 경로 갱신)이
  채운다. 주석으로 그 자리를 표시해뒀다.
- **`SENTRY_RELEASE` 를 넣는 주체는 배포 스크립트(티켓 27)** 다. 비어 있으면 릴리스
  태그 없이 환경 태그만 붙는다(`test_release_is_omitted_when_not_set`).
- **`.env.prod.example`·`.env.develop.example` 은 건드리지 않았다.** 티켓이 지정한 건
  `.env.example` 이고, 선행 티켓(01 의 `SLACK_WEBHOOK_URL`)도 같은 범위만 고쳤다.
  prod 에 실제로 넣을 키 목록은 스펙 §D3 "prod `.env` 새 키" 에서 사람이 챙긴다.
- **UptimeRobot 실제 등록은 사람(스펙 §D1)** — 배포 도메인이 생긴 뒤에야 가능해서
  README 운영 절의 메모가 끝이다.
- `GET /config` 에 `app_store_id` 를 넣지 않은 것은 코디네이터 확정 사항 2 번이다.

## 수정 라운드 1

최종 리뷰(`review/impl-review-08.md` 라운드 1, FAIL) 의 BLOCKER 0 / MAJOR 1 /
MINOR 0 을 처리했다. 머리글의 "커밋 4개 / 20파일 / 로컬 main 72a2a3c" 는 이 라운드
기준으로 **커밋 8개, `main..HEAD` 22파일, 로컬 main `528879b`(티켓 20 머지) 위로
rebase** 로 바뀌었다.

### D-08-1 (MAJOR) — Sentry 가 OAuth 인증 코드·사용자 JSON 을 요청 본문에 보존한다

**재현(수정 전).** 리뷰가 적은 절차대로, 실제 SDK 를 켜고 Transport 만 메모리로
바꿔서 애플 콜백을 터뜨렸다(`_get_client` 를 RuntimeError 를 내는 객체로 교체 —
외부 요청 없음, 실제 인증정보 없음):

```
status: 500
events: 1
request.data: {"code": "FORM-CODE-MARKER", "user": "{\"email\": \"repro@example.test\", \"name\": {\"firstName\": \"a\"}}", "id_token": "FORM-IDTOKEN-MARKER"}
request.query_string: code=QUERY-CODE-MARKER&state=st
  marker 'FORM-CODE-MARKER' in event: True
  marker 'QUERY-CODE-MARKER' in event: True
  marker 'FORM-IDTOKEN-MARKER' in event: True
  marker 'repro@example.test' in event: True
```

리뷰 판정이 맞다. 본문뿐 아니라 **쿼리스트링도** 그대로 실린다(구글 콜백은 같은
인증 코드를 `?code=` 로 보낸다).

**원인.** `send_default_pii=False` 로는 요청 본문이 막히지 않는다. 설치된 SDK
2.72.0 의 `sentry_sdk/integrations/_wsgi_common.py:88` 에
`attach_request_body = True` 가 기본값으로 박혀 있고(주석도 "Prior to data
collection being implemented we unconditionally attached the request body"),
`send_default_pii` 가 끄는 건 쿠키·유저 식별자뿐이다. 같은 파일 wsgi 이벤트
프로세서(`integrations/wsgi.py:422`)도 `data_collection` 을 안 쓰면 쿼리스트링을
`request.query_string` 에 그대로 넣는다. 기본 `EventScrubber` 도 못 막는다 —
`scrubber.py:15` 의 `DEFAULT_DENYLIST` 에 `code`/`user`/`receipt` 가 없고
`recursive=False` 라 문자열로 인코딩된 `user` JSON 안쪽은 보지도 않는다.
즉 "옵션을 하나 빼먹은" 게 아니라 **PII 보호를 `send_default_pii` 하나에 맡긴
설계 판단이 SDK 실제 동작과 달랐던 것**이고, README·독스트링의 보장도 거기서 틀렸다.

**수정.** `app/observability.py` 에서 `send_default_pii` 를 버리고
`SENTRY_DATA_COLLECTION`(SDK 2.72 의 `data_collection` 옵션) 으로 범주별로 끈다.
`data_collection` 은 2.72 에서 `send_default_pii` 를 대체한 옵션이고, 옛 옵션은
이제 `DeprecationWarning` 이 뜬다(red 단계 테스트 출력에서 실제로 떴다). 끈 것:

| 범주 | 설정 | 왜 |
|---|---|---|
| 요청 본문 | `http_bodies: []` | OAuth `code`·`user`, 영수증 `receipt` 가 들어오는 자리. 민감 필드 목록을 관리하는 대신 본문 자체를 안 받는다 — 엔드포인트가 늘 때마다 목록을 따라 늘려야 하는 쪽이 더 잘 샌다 |
| 쿼리스트링 | `url_query_params: {"mode": "off"}` | 구글 콜백 `?code=` |
| 쿠키 | `cookies: {"mode": "off"}` | 서명된 세션 쿠키(어느 게스트인지) |
| 유저 식별자·IP | `user_info: False` | |
| SQL 바인드 파라미터 | `database_query_data: False` | 닉네임·정답 |
| Celery task 인자 | `queues: False` | |
| 스택 프레임 지역 변수 | `stack_frame_variables: False` | 아래 참고 |

**지역 변수를 이름 필터로 못 막는 이유(리뷰가 "쿼리·로컬 변수도 같은 기준으로
검토" 라고 한 부분).** 처음엔 `stack_frame_variables` 를 denylist 모드로 두고
민감어만 가리려 했는데, 쿼리스트링 테스트가 red 로 남았다. 터진 뷰의 프레임만
올라오는 게 아니라 `flask/app.py:wsgi_app` 프레임도 같이 올라오고, 그 프레임의
`environ` 지역 변수에 `QUERY_STRING`·`REQUEST_URI`·`RAW_URI`(= `?code=...`)와
`HTTP_COOKIE` 가 통째로 들어 있다:

```
E  'sentinel-query-code' is contained here:
E    ": "'code=sentinel-query-code&state=xyz'", "REQUEST_URI": "'/api/v1/auth/google/callback?code=sentinel-query-code&state=xyz'", ...
```

SDK 필터는 변수 **이름** 만 보니 이런 중첩 dict 안쪽도, werkzeug `Request` 객체
repr(전체 URL 이 그대로 보인다)도 들여다보지 못한다. 그래서 끄는 쪽을 택했다.
남는 건 예외·스택·소스 컨텍스트(프레임 주변 소스 5줄)·메서드·경로·환경·릴리스다.

**증명하는 테스트.** `tests/test_sentry.py` 뒤쪽에 실제 SDK + 메모리 Transport 로
완성된 이벤트 payload 를 검사하는 층을 더했다(리뷰가 요구한 "초기화 인자 mock 외의
이벤트 내용 회귀 검증"). 앞쪽 init 인자 테스트 5개는 그대로 남겼다.

| 테스트 | 무엇을 고정하나 |
|---|---|
| `test_oauth_callback_error_is_reported_without_the_request_body` | 애플 form POST 의 `code`·`user`(이메일)·`id_token` 이 이벤트 어디에도 없다 |
| `test_oauth_callback_error_is_reported_without_the_query_string` | 구글 GET `?code=` 가 `request.query_string` 과 이벤트 전체에 없다 |
| `test_error_report_still_carries_the_exception_environment_and_release` | 막는 설정이 오류 보고 자체를 끈 게 아니다 — 예외 타입·환경·릴리스·메서드·경로는 남고, 쿠키는 `[Filtered]`, `user`(IP) 는 없다 |
| `test_celery_task_error_is_reported_without_the_task_arguments` | 워커 쪽도 같은 설정을 탄다: 오류는 올라가고 `extra["celery-job"]` 에 task 이름만 남는다 |

red → green (DB `chosung_daily_test_t08`, Redis DB 10):

```
$ uv run pytest tests/test_sentry.py -q          # 수정 전
FAILED tests/test_sentry.py::test_oauth_callback_error_is_reported_without_the_request_body
FAILED tests/test_sentry.py::test_oauth_callback_error_is_reported_without_the_query_string
2 failed, 6 passed, 3 warnings in 0.30s
  (warning: DeprecationWarning: The send_default_pii option is deprecated. Use data_collection instead.)

$ uv run pytest tests/test_sentry.py -q          # data_collection 적용 후 (locals 는 아직 denylist)
FAILED tests/test_sentry.py::test_oauth_callback_error_is_reported_without_the_query_string
1 failed, 7 passed in 0.29s

$ uv run pytest tests/test_sentry.py -q          # stack_frame_variables=False 까지
9 passed in 0.30s
```

**수정 후 수동 확인(세 경로).** form POST / GET 쿼리 / JSON 본문을 각각 터뜨려
이벤트 전체를 덤프했다. 세 경로 모두 표식이 하나도 남지 않는다:

```
### apple form POST: status=500 events=1
  request keys: ['env', 'headers', 'method', 'url']
  request.data: None          request.query_string: None
  request.headers: {... "Cookie": "[Filtered]"}
  request.env: {"SERVER_NAME": "localhost", "SERVER_PORT": "80"}
  frames with vars: []        breadcrumbs: {"values": []}        user: None
  LEAKED sentinels: []
### google GET with query: status=500 events=1   → LEAKED sentinels: []
### json POST body (authorization_code·receipt): status=500 events=1 → LEAKED sentinels: []

== TOTAL LEAKED: []
```

**문서.** README 의 틀린 보장("`send_default_pii=False` 로 쿠키·바디가 안 따라간다")을
지우고, 무엇을 왜 끄는지와 "init 인자 mock 으로는 검증이 안 된다" 는 함정을 적었다.
`app/observability.py` 독스트링·주석도 같이 고쳤다.

### 리뷰의 나머지 지적

- **"구현 증거의 4커밋·20파일이 실제와 다르다"** — 리뷰도 기능 결함이 아니라고 적었고,
  이 라운드 머리글(위)에서 7커밋·22파일·main `528879b` 로 갱신했다.
- **미수정 MINOR: 없음**(리뷰 MINOR 0건). 리뷰가 틀렸다고 판단한 지적도 없다 —
  D-08-1 은 재현으로 확인했다.

### 이 라운드 전체 재검증

```
$ git rebase main                        # 로컬 main 528879b, 충돌 없음
Successfully rebased and updated refs/heads/dosaem/t08-app-config-health-sentry.

$ uv run pytest -q
279 passed in 189.48s (0:03:09)

$ uv run ruff check .
All checks passed!

$ FLASK_SKIP_DOTENV=1 SENTRY_DSN='' FLASK_APP=wsgi.py uv run flask db heads
ff06a1bf5afc (head)

$ git diff main...HEAD --check            # 출력 없음
```

마이그레이션은 이 라운드에서 건드리지 않았다(head 1개 그대로). 테스트 수가 203 →
279 로 늘어난 건 rebase 로 들어온 다른 티켓 테스트와 이번 회귀 테스트 4개 때문이다.
외부 서비스 호출·배포·`git push` 없음. 시크릿 값은 기록하지 않았다 — 위 표식은
전부 더미(`sentinel-*`, `*-MARKER`, `@example.test`)다.
