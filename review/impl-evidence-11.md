# 티켓 11 구현 증거 — 애플 client_secret 자동 갱신·만료 알림

- 브랜치: `dosaem/t11-apple-client-secret-auto-renew`, 로컬 `main` **8115301**(티켓 04·05 머지
  반영) 위로 rebase 완료. 커밋 4개(`git log main..HEAD`), 작업 트리 clean.
- 선행 티켓 08·10 은 머지돼 있다(`20d279a` = 10, `987b58a` = 08). 10 이 만든
  `apple_client_secret(app, client_id)` 와 `app_login_service` 의 토큰 교환 경로, 08 이 만든
  `/health` 의 `apple_secret_expires_at` 자리 위에 올렸다.
- 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t11`, Redis DB **13**
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL`). 마이그레이션 왕복은 `chosung_daily_test_t11_migrations`
  (`TEST_MIGRATION_DATABASE_URL`). 공용 `chosung_daily_test`·Redis DB 1 은 건드리지 않았고
  다른 워커의 컨테이너를 내리지 않았다(기존 `chosung-daily-mysql-1`·`chosung-daily-redis-1` 재사용).
- **외부 서비스 호출 0건.** 애플 토큰/JWKS 엔드포인트, Slack webhook 모두 가짜 또는
  monkeypatch 다. 이 티켓의 동작(서명·만료 판정)은 전부 프로세스 안에서 일어나서 네트워크가
  아예 필요 없다. 애플·구글 콘솔 접속, NAS 접속, 배포, `git push` 없음.
- 시크릿 값은 어떤 파일에도 쓰지 않았다(이름만: `APPLE_CLIENT_ID`, `APPLE_APP_BUNDLE_ID`,
  `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`, `SLACK_WEBHOOK_URL`). `.env`·`.env.prod*`
  의 실제 값은 열지도 수정하지도 않았다. 알림 메시지에 JWT 를 넣지 않는 것도 테스트로 고정했다
  (`test_alert_does_not_leak_the_secret_itself`).
- **UI 변경 없음**(백엔드 전용 티켓, `/health` JSON 한 필드) → `impeccable detect`·`audit.native`
  해당 없음. DESIGN_DIR(`design/SCREENS.md`, `design-system/hidden-vowels/`) 에 이 티켓이 닿는
  화면은 없다.
- **마이그레이션 없음**(모델·스키마 변경 0). `flask db heads` 가 1줄인 것만 확인했다.
- `.env.example` 변경 없음 — 갱신 창(7일)·수명(150일)은 코드 상수고 새 설정값이 없다.

## 1. 실행한 명령과 출력

모든 명령에 아래 환경변수를 붙였다(이하 생략):

```sh
TEST_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t11?charset=utf8mb4"
TEST_REDIS_URL="redis://localhost:6379/13"
TEST_MIGRATION_DATABASE_URL="mysql+pymysql://chosung:chosung@localhost:3306/chosung_daily_test_t11_migrations?charset=utf8mb4"
```

### 전체 테스트 스위트 (rebase 후)

```
$ uv run pytest -q
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 94%]
...................                                                      [100%]
379 passed in 150.84s (0:02:30)
```

실패·skip·xfail **0건**. 신규 **19개**가 전부 `tests/test_apple_secret_renewal.py` 다
(rebase 전 작업 시작 시점의 같은 명령은 365 passed 였고, 늘어난 14개는 rebase 로 들어온
티켓 04 의 테스트다).

### 린트

```
$ uv run ruff check .
All checks passed!
```

> `ruff format --check` 는 돌리지 않았다. CI(`.github/workflows/ci.yml`)가 `ruff check .` 만
> 쓰고, `ruff format --check` 는 **이 티켓이 안 건드린 기존 파일 23개**에서도 실패한다
> (레포가 포매터를 강제하지 않는 상태). 티켓 범위 밖이라 그대로 뒀다.

### 마이그레이션 head

```
$ FLASK_APP=wsgi.py DATABASE_URL=...chosung_daily_test_t11 uv run flask db heads
ff06a1bf5afc (head)
```

1줄. 이 티켓은 마이그레이션을 만들지 않았다.

```
$ uv run pytest tests/test_migrations.py -q
......                                                                   [100%]
6 passed in 25.68s
```

### 이 티켓이 추가·수정한 범위 + 애플 로그인 전체 (verbose)

```
$ uv run pytest tests/test_apple_secret_renewal.py tests/test_health.py \
    tests/test_celery_wiring.py tests/test_oauth_routes.py tests/test_apple_client.py \
    tests/test_token_exchange.py -v
tests/test_apple_secret_renewal.py::test_accessor_keeps_a_secret_that_is_not_near_expiry PASSED
tests/test_apple_secret_renewal.py::test_accessor_resigns_when_less_than_seven_days_remain PASSED
tests/test_apple_secret_renewal.py::test_accessor_resigns_for_the_bundle_id_by_the_same_rule PASSED
tests/test_apple_secret_renewal.py::test_accessor_signs_a_secret_that_was_never_cached PASSED
tests/test_apple_secret_renewal.py::test_renew_window_is_seven_days PASSED
tests/test_apple_secret_renewal.py::test_apple_login_swaps_the_authlib_client_secret PASSED
tests/test_apple_secret_renewal.py::test_apple_callback_swaps_the_authlib_client_secret PASSED
tests/test_apple_secret_renewal.py::test_apple_login_leaves_a_healthy_secret_alone PASSED
tests/test_apple_secret_renewal.py::test_google_login_does_not_touch_its_client_secret PASSED
tests/test_apple_secret_renewal.py::test_expiry_is_the_earlier_of_the_two_clients PASSED
tests/test_apple_secret_renewal.py::test_expiry_does_not_renew_a_near_expiry_secret PASSED
tests/test_apple_secret_renewal.py::test_expiry_signs_clients_that_were_never_used PASSED
tests/test_apple_secret_renewal.py::test_expiry_is_none_without_apple_signing_keys PASSED
tests/test_apple_secret_renewal.py::test_health_reports_the_earlier_expiry PASSED
tests/test_apple_secret_renewal.py::test_health_reports_null_without_apple_signing_keys PASSED
tests/test_apple_secret_renewal.py::test_notifies_the_operator_when_expiry_is_within_seven_days PASSED
tests/test_apple_secret_renewal.py::test_does_not_notify_while_both_secrets_are_healthy PASSED
tests/test_apple_secret_renewal.py::test_does_not_notify_without_apple_signing_keys PASSED
tests/test_apple_secret_renewal.py::test_alert_does_not_leak_the_secret_itself PASSED
tests/test_health.py::test_health_is_ok_when_db_and_redis_are_up PASSED
tests/test_health.py::test_health_is_degraded_but_still_200_when_redis_is_down PASSED
tests/test_health.py::test_health_is_503_when_db_is_down PASSED
tests/test_health.py::test_health_reports_db_down_even_if_redis_is_also_down PASSED
tests/test_celery_wiring.py::test_tasks_are_registered PASSED
tests/test_celery_wiring.py::test_beat_schedule_matches_spec_times PASSED
tests/test_celery_wiring.py::test_beat_schedule_is_merged_from_task_modules PASSED
tests/test_celery_wiring.py::test_tasks_delegate_to_the_service_functions PASSED
tests/test_celery_wiring.py::test_timezone_is_kst PASSED
tests/test_oauth_routes.py::test_login_rejects_unsupported_provider PASSED
... (중략: test_oauth_routes 9, test_apple_client 4, test_token_exchange 19 전부 PASSED)
============================= 60 passed in 33.69s ==============================
```

### git 상태

```
$ git log --oneline main..HEAD
def162a docs(11): README "설계 판단" 11 — 요청 경로 갱신·Beat 스케줄 표
dea1ef0 feat(11): Beat 주 1회 애플 secret 만료 임박 Slack 알림
6c0357c feat(11): /health 가 애플 secret 만료 시각을 노출한다
d768fb4 feat(11): 애플 client_secret 을 요청 경로에서 갱신한다

$ git status --short
(빈 출력)
```

## 2. 체크박스별 근거

| 티켓 체크박스 | 구현 | 이걸 증명하는 테스트/명령 |
|---|---|---|
| client_secret 접근자(공개 함수, client_id 인자)가 "<7일 남음이면 재서명 후 교체" 를 수행 | `app/extensions.py` `apple_client_secret(app, client_id)` | `test_accessor_resigns_when_less_than_seven_days_remain` (교체된 JWT 의 `sub`·150일 `exp`·캐시 반영까지), `test_accessor_keeps_a_secret_that_is_not_near_expiry`, `test_renew_window_is_seven_days` |
| …`/auth/apple/login` 진입에서 사용 | `app/api/oauth.py` `_get_client` | `test_apple_login_swaps_the_authlib_client_secret` |
| …`/auth/apple/callback` 진입에서 사용 | 같은 `_get_client`(두 라우트가 공유) | `test_apple_callback_swaps_the_authlib_client_secret` |
| …10 의 토큰 교환 경로에서 사용 | `app/services/app_login_service.py::_exchange_apple_code` 가 같은 접근자를 호출(티켓 10 이 이미 그렇게 둠 — 이 티켓이 그 함수를 갱신 접근자로 바꿔서 교환 경로가 자동으로 혜택을 받는다) | `test_accessor_resigns_for_the_bundle_id_by_the_same_rule` + 기존 `test_token_exchange.py::test_apple_exchange_uses_bundle_id_credentials`(교환에 쓰는 `client_secret` 이 번들 ID 로 서명된 JWT 임을 확인) |
| 프로세스별 자체 갱신, 외부 저장 없음 | 캐시가 `app.extensions["chosung_apple_client_secrets"]` 뿐 — Redis·DB 쓰기 없음 | `test_accessor_signs_a_secret_that_was_never_cached`(캐시 위치를 직접 본다) + Redis/DB 접근 코드 자체가 없음. 앱별 격리는 기존 `tests/test_extensions_isolation.py` 패턴과 같은 저장 방식 |
| 만료 6일 남은 secret 으로 login 호출 시 새 JWT 로 교체되고 Authlib `client_secret` 이 바뀐다 | 위와 같음 | `test_apple_login_swaps_the_authlib_client_secret` (6일 남은 secret 을 심고 → 302 확인 → `client.client_secret != STALE_JWT` + 새 `exp` > 149일) |
| 만료 6일 남은 secret 으로 callback 호출 시 같음 | 위와 같음 | `test_apple_callback_swaps_the_authlib_client_secret` |
| 번들 ID 접근자도 같은 규칙 | 접근자가 `client_id` 인자를 받으므로 한 함수 | `test_accessor_resigns_for_the_bundle_id_by_the_same_rule` |
| `/health` 의 `apple_secret_expires_at` 이 채워진다 (둘 중 더 이른 시각) | `app/api/health.py` + `app/extensions.py::apple_secret_expires_at` | `test_health_reports_the_earlier_expiry`(9일/100일 심고 9일 쪽이 나오는지), `test_expiry_is_the_earlier_of_the_two_clients`, `test_expiry_signs_clients_that_were_never_used`(첫 앱 로그인 전에도 번들 ID 쪽이 포함), `test_health.py::test_health_is_ok_when_db_and_redis_are_up`(더 이상 `null` 아님), `test_health_reports_null_without_apple_signing_keys` |
| Beat 주 1회: 7일 전이면 `notify_operator` 호출 (테스트: 서비스 함수 직접 호출) | `app/services/apple_secret_service.py::notify_apple_secret_expiry`, `app/tasks/scheduled.py` 의 `notify-apple-secret-expiry`(월 09:10 KST) | `test_notifies_the_operator_when_expiry_is_within_seven_days`(서비스 함수 직접 호출, 제목·본문·반환값), `test_does_not_notify_while_both_secrets_are_healthy`, `test_does_not_notify_without_apple_signing_keys`, `test_alert_does_not_leak_the_secret_itself`, `test_celery_wiring.py::test_tasks_are_registered`·`test_beat_schedule_matches_spec_times`(day_of_week={1})·`test_tasks_delegate_to_the_service_functions` |
| README "설계 판단" 에 "애플 secret 요청 경로 갱신(Beat 재서명 대신)" 추가 | `README.md` `### 11. 애플 secret 요청 경로 갱신 (Beat 재서명 대신)` | 커밋 `def162a`. Beat 스케줄 표에 자기 행(월 09:10)도 추가 |

## 3. 테스트가 진짜 잡는지 — 변이(mutation) 확인

구현을 먼저 쓴 구간이 있어서, 새 테스트가 "통과만 하는 테스트"가 아닌지 코드를 일부러
깨뜨려서 확인했다(확인 후 전부 원복, `git diff --stat` 로 복원 검증).

| 변이 | 결과 |
|---|---|
| `app/api/oauth.py` 의 `client_secret` 교체 블록 삭제 (요청 경로 갱신 없음) | **2 failed** — `test_apple_login_swaps_the_authlib_client_secret`, `test_apple_callback_swaps_the_authlib_client_secret` |
| 관측(`_signed_apple_client_secret`)이 갱신 접근자를 경유하게 바꿈 | **3 failed** — `test_expiry_does_not_renew_a_near_expiry_secret`, `test_notifies_the_operator_when_expiry_is_within_seven_days`, `test_alert_does_not_leak_the_secret_itself` |
| 접근자가 7일 창을 무시하고 매번 재서명 | **2 failed** — `test_accessor_keeps_a_secret_that_is_not_near_expiry`, `test_apple_login_leaves_a_healthy_secret_alone` |

## 4. 설계 판단 요약 (README 11 에 전문)

- **Beat 재서명을 안 골랐다.** Beat 가 재서명하면 그 JWT 를 gunicorn 워커에게 전달하려고
  Redis/DB 에 넣어야 하고, 그 순간 "서명된 자격증명을 저장소에 둔다"는 새 문제가 생긴다.
  secret 은 키만 있으면 아무 프로세스나 똑같이 만드는 값이라 공유할 이유가 없다 — 각
  프로세스가 자기 것만 들고 7일 전부터 재서명한다.
- **갱신 지점은 토큰 교환 직전이 아니라 `_get_client` 진입이다.** 콜백은
  `authorize_access_token()` 안에서 애플에 요청을 보내버려서, 그 뒤에 교체하면 이미 만료된
  secret 으로 한 번 실패한다.
- **관측(`apple_client_secret_expiries`)은 갱신하지 않는다.** 관측이 갱신까지 하면 "만료
  임박" 이 보이는 순간 사라져서 **Beat 알림이 영원히 안 울리는 죽은 분기**가 된다. 처음엔
  접근자 하나로 둘 다 쓰려다 이걸 발견해 읽기용을 갈랐고, 위 변이 2가 그 경계를 지킨다.
- 그래서 이 알림의 의미는 "갱신해라"가 아니라 **"갱신이 안 돌고 있다"는 신호**다(요청을
  안 받는 Beat 자신이 전형적인 경우). 주 1회로 둔 것도 안전망이라서다.
- Authlib 쪽 전제: `OAuth` 레지스트리가 클라이언트를 `_clients` 에 프로세스 수명 내내
  캐싱하고(`authlib/integrations/base_client/registry.py`), `client_secret` 은 매 토큰 요청마다
  `_get_oauth_client()` 가 다시 읽는다(`sync_app.py`) — 그래서 등록된 객체의 속성을 바꾸면
  다음 요청부터 바로 먹는다. 레지스트리가 앱별(`app.extensions`)이라 앱 간 오염도 없다.

## 5. 범위 밖으로 손댄 것 / 남은 것

- `tests/conftest.py`: `offline_provider_metadata` 픽스처와 `PROVIDER_METADATA` 를
  `tests/test_oauth_routes.py` 에서 옮겨왔다. 새 테스트 모듈도 같은 대역이 필요한데, 다른
  테스트 모듈에서 픽스처를 import 하면 ruff `F811`(인자 이름이 import 를 가린다)이 뜬다.
  두 모듈이 쓰는 픽스처라 conftest 가 제자리다. 동작 변경 없음.
- `app/extensions.py::init_oauth`: 애플 설정 판정을 `apple_client_ids(app)` 로 모았다. 서명 키
  4개 목록이 두 곳에 복제되는 걸 피한 것이고, 판정 결과는 이전과 같다.
- **README 공유 절은 안 고쳤다.** "08. 헬스체크 등급" 의 "`apple_secret_expires_at` 은 …
  지금은 `null`" 과 "알려진 제한사항" 의 "애플 client_secret 은 앱 시작 시점에 한 번만
  만든다" 는 이 티켓으로 해소됐지만, 공유 절은 덧붙이기만 하는 공통 규칙(티켓 10 이 같은
  이유로 같은 판단을 했다)에 따라 그 줄들은 그대로 두고 `### 11.` 안에서 해소됐다고 적었다.
  → **코디네이터 판단 필요**: 머지 후 그 두 줄을 정리하고 싶으면 별도로 해야 한다.
- 남은 것: 없음. 다만 **실제 애플 서버가 이 JWT 를 받아주는지는 콘솔 등록 후에만 확인
  가능**하다(기존 애플 로그인 코드와 같은 한계 — `tests/test_oauth_routes.py` 상단 설명).
  이 티켓이 검증한 것은 "만료 임박이면 새 JWT 로 교체되고 Authlib 이 그걸 쓴다" 까지다.
