# 티켓 10 구현 증거 — 앱 로그인(id_token 교환·aud 매트릭스·애플 refresh token 보관)

- 브랜치: `dosaem/t10-app-login-id-token-exchange` (로컬 `main` **491418f** 위로 rebase 완료)
- 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t10`, Redis DB **12**
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL` 로 지정. 공용 `chosung_daily_test`·Redis 1 은 건드리지
  않았다). 마이그레이션 검증은 별도 DB `chosung_daily_mig_t10` 에서 돌렸다.
- 외부 서비스 호출 0건. 구글 JWKS·애플 토큰 엔드포인트는 전부 가짜 `requests` / monkeypatch
  한 래퍼로만 검증했다. 애플·구글 콘솔에 접속하지 않았고 NAS 접속·배포·`git push` 없음.
- 시크릿 값은 어떤 파일에도 쓰지 않았다(이름만: `GOOGLE_IOS_CLIENT_ID`,
  `GOOGLE_WEB_CLIENT_ID`, `APPLE_APP_BUNDLE_ID`, `APPLE_PRIVATE_KEY`). `.env`·`.env.prod*` 의
  실제 값은 열지도 수정하지도 않았다.
- UI 변경 없음(백엔드 전용 티켓) → `impeccable detect`·`audit.native` 해당 없음.

## 1. 실행한 명령과 출력

### 전체 테스트 스위트

```
$ TEST_DATABASE_URL=...chosung_daily_test_t10 TEST_REDIS_URL=redis://127.0.0.1:6379/12 uv run pytest -q
........................................................................ [ 50%]
........................................................................ [100%]
144 passed in 61.77s (0:01:01)
```

작업 시작 시점 `main`(491418f) baseline 은 **108 passed** 였다 → **신규 36개**
(`test_token_exchange.py` 15, `test_id_token_verify.py` 12, `test_apple_client.py` 4,
`test_secret_crypto.py` 3, `test_oauth_routes.py` 에 2 추가). 실패·skip·xfail 0건.

이 티켓이 추가·수정한 파일만 verbose 로 다시:

```
$ uv run pytest tests/test_token_exchange.py tests/test_id_token_verify.py \
    tests/test_secret_crypto.py tests/test_apple_client.py tests/test_oauth_routes.py \
    tests/test_account_service.py -v
...
tests/test_account_service.py::test_linking_second_provider_to_already_linked_guest_is_rejected PASSED [100%]

============================= 47 passed in 17.43s ==============================
```

### 린트

```
$ uv run ruff check .
All checks passed!
```

(`PLR0913`(인자 6개)과 `RUF002`(전각 `×`)가 처음에 걸려서, refresh token + 발급 client 를
`ProviderTokens` NamedTuple 한 개로 묶고 독스트링 문자를 고쳤다. 둘은 항상 같이 움직이는
값이라 묶는 게 의미상으로도 맞다 — 하나만 저장되면 revoke 를 못 한다.)

### 마이그레이션 head

```
$ FLASK_APP=wsgi.py uv run flask db heads
f394da7f4d88 (head)          ← 1줄

$ ./scripts/check_migration_heads.sh
f394da7f4d88 (head)
OK: Alembic head 1개
```

### 마이그레이션 실제 적용 + 롤백 왕복

```
$ FLASK_APP=wsgi.py DATABASE_URL=...chosung_daily_mig_t10 uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 9ec267465b4e -> f394da7f4d88, add account provider refresh token and client id

$ mysql -e "SHOW COLUMNS FROM chosung_daily_mig_t10.account"   (upgrade 후)
id int / guest_id int / provider enum('google','apple') / provider_user_id varchar(191)
email varchar(255) / created_at datetime / provider_refresh_token text / provider_client_id varchar(191)

$ uv run flask db downgrade     → 두 컬럼 사라짐(id … created_at 만 남음)
$ uv run flask db upgrade       → 다시 생김(위와 같음)
```

`provider_refresh_token` 이 `Text` 인 이유: Fernet 암호문은 평문보다 길어진다(애플 refresh
token ~100자 → 암호문 ~200자). `String(191)` 에 넣으면 운영에서 잘릴 수 있다.

## 2. 체크박스 ↔ 증거 표

| 티켓 체크박스 | 구현 | 이걸 증명하는 테스트/명령 |
|---|---|---|
| `Account.provider_refresh_token`(Fernet, SECRET_KEY 파생), `provider_client_id` 마이그레이션, `flask db heads` 1개 | `app/models/account.py`, `migrations/versions/f394da7f4d88_*.py`, `app/utils/crypto.py` | `flask db heads`(1줄)·`scripts/check_migration_heads.sh`·upgrade/downgrade 왕복(위 §1), `test_secret_crypto.py::test_roundtrip`, `::test_other_secret_key_cannot_decrypt`, `::test_same_plaintext_encrypts_to_different_ciphertext` |
| `clients/google_jwks.py`·`clients/apple.py` 와 id_token 검증 순수 함수 분리. 테스트 키 쌍으로 서명한 토큰을 진짜 검증(JWKS monkeypatch) | `app/clients/google_jwks.py`(JWKS), `app/clients/apple.py`(JWKS·토큰 교환), `app/services/id_token_service.py`(`verify_id_token`, 네트워크 없음) | `test_id_token_verify.py` 12개 전부 — 실제 RSA 키 쌍으로 서명(`tests/id_token_helpers.py`)해서 서명·iss·aud·exp·kid 를 진짜 검증. `test_apple_client.py::test_exchange_posts_code_to_apple_token_endpoint`, `::test_jwks_fetch_returns_keys_array` 는 가짜 `requests` 로 래퍼만 본다 |
| `POST /auth/token-exchange` (Bearer) → aud 매트릭스 → `link_or_switch_account` → `{token}`; 401 `INVALID_ID_TOKEN`, 전환(`existing`), `ACCOUNT_ALREADY_LINKED` | `app/api/oauth.py::token_exchange`, `app/schemas/auth.py`, `app/services/app_login_service.py`(`allowed_audiences`, `exchange_id_token`) | `test_token_exchange.py::test_google_ios_token_links_current_guest`(200+`{token}`), `::test_google_android_token_uses_web_client_id`(웹 클라이언트 ID aud), `::test_audience_outside_matrix_is_unauthorized`(401 `INVALID_ID_TOKEN`, 계정 0), `::test_already_linked_provider_account_switches_guest`(전환 — 원래 게스트 토큰 반환), `::test_guest_with_another_account_is_rejected`(409 `ACCOUNT_ALREADY_LINKED`), `::test_requires_bearer_token`(401), `::test_unknown_provider_is_validation_error`(400), `::test_jwks_is_fetched_once_for_two_logins`(1시간 캐시) |
| apple: `authorization_code` 교환(client_id=번들 ID, client_secret=번들 ID JWT) → 두 컬럼 저장, 교환 id_token `sub` 일치 확인(불일치 401), 재로그인·전환 시 덮어쓰기, client_secret 생성 인자화 | `app/services/app_login_service.py::_exchange_apple_code`, `app/extensions.py::apple_client_secret(app, client_id)`, `app/services/account_service.py::_store_provider_tokens` | `test_token_exchange.py::test_apple_stores_encrypted_refresh_token_and_bundle_id`(암호문 저장 + 복호화 일치 + `provider_client_id` = 번들 ID), `::test_apple_exchange_uses_bundle_id_credentials`(교환 호출 인자 + client_secret JWT 의 `sub` == 번들 ID), `::test_apple_subject_mismatch_is_unauthorized`(401, 계정 0), `::test_apple_rejected_code_is_unauthorized`(401), `::test_apple_requires_authorization_code`(400), `::test_apple_relogin_overwrites_stored_tokens`(전환 경로에서 덮어쓰기), `test_apple_client.py::test_client_secret_can_be_signed_for_bundle_id` |
| 웹 `/auth/apple/callback` 도 `refresh_token`·Services ID 를 같은 컬럼에 저장(기존 `test_oauth_routes.py` 통과) | `app/api/oauth.py::callback` | `test_oauth_routes.py::test_apple_callback_stores_refresh_token_and_services_id`(새로 추가), `::test_google_callback_stores_no_provider_token`(구글은 두 컬럼 비어 있음), 기존 8개 테스트 그대로 통과(위 verbose 47 passed) |
| 설정값 `GOOGLE_IOS_CLIENT_ID`, `GOOGLE_WEB_CLIENT_ID`, `APPLE_APP_BUNDLE_ID`, 번들 ID 용 Apple key 설정을 `.env.example` 에 추가(미정 17 반영) | `.env.example`(주석 포함), `app/config.py`(`Config` + `TestingConfig` 더미), 스펙 "미정 항목" 에 17 확정 줄 추가 | `test_token_exchange.py` 전체가 이 설정값을 실제로 읽어서 aud 를 판정한다(`app.config[...]` 로만 참조, 하드코딩 없음), `test_id_token_verify.py::test_empty_audience_matrix_is_rejected`(설정 누락 = 거부) |
| README "설계 판단" 에 ADR 0002 요약(aud 매트릭스 표, 애플 토큰 보관 이유) | `README.md` `### 10. 앱 로그인은 id_token 교환 (ADR 0002 요약)` + API 목록 표에 `POST /api/v1/auth/token-exchange` 행 | 문서 — 공통 규칙대로 "설계 판단" 섹션 끝에 자기 번호 소제목만, API 표에는 자기 행만 덧붙였다 |

## 3. 설계 판단(코드에 남긴 근거)

- **aud 매트릭스는 설정 집합으로**: 서버는 요청만 보고 iOS/Android 를 구분할 수 없어서
  구글은 iOS 클라이언트 ID 와 웹 클라이언트 ID 둘 다 받는다(둘 다 우리 프로젝트의
  클라이언트). 애플은 번들 ID 하나. 설정이 비어 있으면 **빈 집합 = 거부** —
  "검증 건너뜀" 으로 조용히 바뀌지 않게 `verify_id_token` 이 빈 `audiences` 를 즉시 거부한다.
- **허용 알고리즘 `RS256` 고정**: JWKS 는 공개 정보라, 알고리즘을 토큰 헤더에 맡기면 공개키를
  HMAC 비밀로 쓴 위조 토큰이 통과한다. PyJWT 가 encode 쪽에서 그런 키를 막기 때문에, 테스트는
  공격자처럼 토큰을 직접 조립해서(`_hmac_signed_token`) `HS256`·`alg=none` 둘 다 거부되는지 본다.
- **애플인데 `authorization_code` 가 없으면 400 거절**(코디네이터 확인). 스키마에서 선택인 건
  구글이 안 보내기 때문이고, 애플에서 빠지면 "연결은 됐는데 애플 쪽 철회 수단이 없는 계정" 이
  생겨 심사 요구(계정 삭제 시 연결 철회)를 못 지킨다. `test_apple_requires_authorization_code`
  가 고정한다.
- **교환 응답의 `id_token` 도 똑같이 검증하고 `sub` 를 비교**: 안 하면 남의
  `authorization_code` 를 끼워 넣어 그 사람의 refresh token 을 내 계정에 붙일 수 있다.
- **refresh token + 발급 client 는 `ProviderTokens` 로 함께 다룬다**: 애플 revoke 는 "그 토큰을
  발급한 client" 의 자격증명으로만 받아주므로 둘 중 하나만 저장되면 쓸 수 없는 값이다.
  구글 로그인은 `None` 으로 들어오고, 그때는 기존 컬럼을 건드리지 않는다.
- **JWKS 1시간 프로세스 캐시**: provider 키 교체 때만 바뀌는 공개 정보고, 앱 설정과 무관해서
  (어느 Flask 앱이 물어도 같은 공개키) redis·Authlib 때와 달리 모듈 전역에 둬도 멀티 앱
  오염이 없다 — 그 근거를 코드 주석과 README 에 남겼다.
- **외부 호출 래퍼 / 순수 함수 분리(§A.17)**: `clients/*.py` 는 요청만, 판정은
  `services/id_token_service.py`(순수)·`app_login_service.py`. 그래서 검증 테스트 12개가
  네트워크 없이 진짜 서명을 검증한다.

## 4. 범위 밖으로 남긴 것(숨기지 않고 적음)

- **애플 revoke 호출 자체는 이 티켓이 아니다**(티켓 14). 여기서는 revoke 에 필요한 값
  (`provider_refresh_token`·`provider_client_id`)을 모으고 보관하는 데까지만 했다.
- **client_secret 자동 갱신 접근자는 티켓 11**. 이 티켓은 함수를 `apple_client_secret(app,
  client_id)` 로 인자화해 웹 Services ID / 앱 번들 ID 둘 다 서명할 수 있게만 했다. 티켓 11 은
  **두 client 의 secret 을 모두** 갱신 대상에 넣어야 한다(스펙 미정 17 확정 줄에 기록).
- **`.env.prod.example`·`.env.develop.example` 에는 새 키를 넣지 않았다** — 티켓 체크박스가
  `.env.example` 만 지정했고 두 파일은 배포 티켓 쪽에서 같이 관리된다. 실제 배포 전에
  `GOOGLE_IOS_CLIENT_ID`·`GOOGLE_WEB_CLIENT_ID`·`APPLE_APP_BUNDLE_ID` 세 줄을 거기에도 넣어야
  앱 로그인이 켜진다(배포 담당 티켓에 넘기는 메모).
- **실제 provider 왕복은 여전히 미검증**: 구글·애플 콘솔에 iOS 클라이언트 ID·App ID 를
  등록해야 끝까지 돌려볼 수 있다(README "알려진 제한사항" 의 기존 항목과 같은 이유).
  서버 쪽은 서명 검증까지 진짜 키로 테스트했지만, "애플이 우리 번들 ID JWT 를 받아주는가" 는
  콘솔 등록 후 수동 확인 대상이다.

## 수정 라운드 1

최종 리뷰(`review/impl-review-10.md` 라운드 1, FAIL)의 결함 2건을 모두 고쳤다. 리뷰 파일은
수정하지 않았다. 테스트 자원은 그대로 DB `chosung_daily_test_t10`, Redis DB 12 이고,
마이그레이션 왕복 테스트(티켓 02 가 main 에 들여온 `tests/test_migrations.py`)용으로
`chosung_daily_test_t10_migrations` 를 새로 만들었다(기본 이름 규칙 = 테스트 DB + `_migrations`.
공용 `chosung_daily_test*` 와 다른 티켓의 DB 는 건드리지 않았다).

### D-10-1 (MAJOR) — 새 kid 가 나타나도 JWKS 를 갱신하지 않아 정상 로그인을 거부

**재현 먼저**: 리뷰에 적힌 스크립트를 그대로 돌려 결함을 확인했다.

```
$ uv run python repro_d1.py    # 리뷰 본문의 스크립트를 그대로(레포 밖 임시 파일)
rotation: INVALID_ID_TOKEN; fetch calls: 1
after cache clear: True fetch calls: 2
```

**원인**: `_load_jwks` 가 TTL(1시간)만 보고 캐시를 돌려줘서, 공개키 선택이 "캐시에 이 토큰의
`kid` 가 있는가" 를 전혀 보지 않았다. provider 가 키를 교체하면 새 `kid` 로 서명된 **정상**
토큰이 들어오는데, 캐시가 따뜻한 프로세스는 TTL 이 끝날 때까지 그걸 전부
`INVALID_ID_TOKEN` 으로 거부한다. `id_token_service` 의 주석("TTL 이 지나면 다음 로그인에서
새 키를 받는다")이 바로 그 잘못된 전제였다. 애플은 이 검증이 code 교환보다 앞이라 교환도 못
간다. 같은 구멍이 교환 응답 id_token 검증(`_exchange_apple_code`)에도 있었다.

**수정**(`app/services/app_login_service.py`, `app/services/id_token_service.py`):

- `id_token_service` 에 `unverified_kid`(헤더의 `kid` 만 읽는다)·`jwks_contains_kid` 를 추가하고,
  `verify_id_token` 도 그걸 쓰게 했다. `alg` 등 헤더의 다른 값은 그대로 믿지 않는다.
- `_load_jwks` → `_jwks_for(provider, id_token)`: 캐시에 토큰의 `kid` 가 없으면 **그 자리에서**
  공개키를 다시 받는다. 갱신 후에도 없는 `kid`·틀린 서명·틀린 `aud`/`iss` 는 그대로 거부다 —
  검증을 느슨하게 한 게 아니라 "어떤 공개키를 쓸지" 만 고쳤다.
- 모르는 `kid` 를 박은 토큰을 연달아 보내는 요청이 provider JWKS 엔드포인트 호출로 증폭되지
  않게, 이 갱신은 provider 당 `JWKS_REFRESH_MIN_INTERVAL_SECONDS`(60초)에 한 번으로 제한한다.
  정상 TTL 만료 조회로 받은 키는 "방금 받은 키" 라 다시 받지 않는다(캐시에 `refreshed_at` 을
  같이 들고 `_CachedJwks` 로 묶었다).
- 애플 code 교환 응답의 id_token 검증도 같은 `_jwks_for` 를 쓴다.

**증명하는 테스트**(모두 먼저 빨갛게 만든 뒤 고쳤다 — 수정 전 세 개가 각각
`assert 401 == 200`, `assert 1 == 2`, `assert 401 == 200` 으로 실패):

```
$ uv run pytest tests/test_token_exchange.py -k "rotat or unknown_kid" -q
...
3 passed, 15 deselected in 1.80s
```

- `test_rotated_signing_key_is_refetched_and_accepted` — 예전 키로 로그인해 캐시를 채운 뒤
  키를 교체하고, 새 `kid` 로 서명된 정상 토큰이 200 이고 JWKS 조회가 2회인지 본다.
- `test_unknown_kid_refetches_once_and_stays_rejected` — 없는 `kid` 토큰을 3번 보내 전부 401
  `INVALID_ID_TOKEN` 이고 조회가 2회(첫 조회 + 갱신 1회)에 멈추는지 본다(증폭 방지).
- `test_apple_exchanged_token_with_rotated_key_is_accepted` — 앱이 보낸 토큰은 캐시의 예전
  키로 통과하고 **교환 응답만** 새 `kid` 인 상황에서 200 과 refresh token 덮어쓰기를 본다.

리뷰의 재현 스크립트도 수정 후 다시 돌렸다(기대대로 수용 + 조회 2회):

```
rotation: ACCEPTED sub=provider-uid-1; fetch calls: 2
after cache clear: True fetch calls: 3
```

### D-10-2 (MINOR) — 공유 파일의 append-only 규칙 위반

**원인**: 이 티켓이 `_apple_client_secret` 을 `apple_client_secret(app, client_id)` 로 개명하면서,
그 함수명을 언급하는 **기존** 문서 줄(`.env.example` 애플 설명, README "설계 판단" OAuth 항목,
"알려진 제한사항")까지 같이 고쳤다. 정확한 서술이긴 해도 공통 규칙("자기 번호 소제목/자기 행만
섹션 끝에 덧붙인다")을 벗어나 병렬 티켓과 충돌할 수 있는 편집이었다. `.env.example` 의 새 블록도
파일 끝이 아니라 기존 Slack 설정 **앞**에 끼워 넣었다.

**수정**: 세 줄을 모두 원문(`_apple_client_secret`)으로 되돌리고, `.env.example` 의 티켓 10
블록을 파일 맨 끝으로 옮겼다. 개명 사실은 **자기 번호 절 안에만** 적었다 — README `### 10.`
끝에 "`apple_client_secret(app, client_id)` 로 인자화·공개했고, 위 기존 절의
`_apple_client_secret` 은 같은 함수의 예전 이름" 한 단락, `.env.example` 은 내 블록 주석에 한 줄.
머지 담당이 기존 절의 예전 이름을 일괄로 갱신하면 그 두 줄은 지워도 된다.

**증명**: 두 공유 파일의 변경이 **추가만** 남았다(삭제·수정 줄 0).

```
$ git diff main -- .env.example README.md | grep "^-" | grep -v "^---"
(출력 없음)
```

같은 README `### 10.` 절에 D-10-1 의 갱신 규칙도 한 단락 적었다(캐시에 없는 `kid` → 즉시 재조회,
provider 당 60초 최소 간격).

### 리뷰 본문의 검증 메모 — 기존 OAuth 테스트의 provider discovery 호출 (코디네이터 지시로 수정)

리뷰가 지적한 대로, 구현 증거 1절의 "외부 서비스 호출 0건" 은 **테스트 스위트 전체에 대해서는
사실이 아니었다**. 소켓을 로컬로 제한하고 전체 스위트를 돌려 먼저 재현했다.

```
$ uv run python guarded_run.py   # socket.connect 를 127.0.0.1/localhost 로 제한한 뒤 pytest.main
2 failed, 223 passed in 93.46s
FAILED tests/test_oauth_routes.py::test_sync_then_login_redirects_to_provider
FAILED tests/test_oauth_routes.py::test_sync_then_apple_login_redirects_to_provider
E   RuntimeError: blocked external network: ('192.178.226.84', 443)   # 구글 discovery
E   RuntimeError: blocked external network: ('17.32.194.6', 443)      # 애플 discovery
```

**원인**: `authorize_redirect` → Authlib `OAuth2Mixin.create_authorization_url` 이
`authorization_endpoint` 를 **discovery 문서**(`server_metadata_url`)에서 읽는다. 그 조회는
`load_server_metadata` 가 `server_metadata` 에 `_loaded_at` 이 없으면 실제 HTTPS 요청으로
가져오기 때문에, 두 테스트는 돌 때마다 `accounts.google.com`·`appleid.apple.com` 에 붙었다.
이 티켓이 만든 회귀는 아니다(두 테스트 본문은 main 과 같다) — 코디네이터 지시로 함께 고쳤다.

**수정**(`tests/test_oauth_routes.py`): `offline_provider_metadata` 픽스처가 등록된 Authlib
클라이언트의 `load_server_metadata` 를 대역으로 바꿔, 로그인 시작이 쓰는 두 값
(`authorization_endpoint`·`token_endpoint`)만 돌려준다. 값은 실제 엔드포인트와 같고, 단정문
(`"accounts.google.com" in Location`, `"appleid.apple.com" in Location`)은 그대로 뒀다. 대신
이 테스트가 보증하는 범위가 좁아진 걸 픽스처 독스트링에 적었다 — **discovery 문서 자체와
실제 로그인 왕복은 여전히 콘솔 등록 후 수동 확인 대상**이다. 애플 쪽은 ES256 client_secret
서명이 등록 단계에서 깨지면 여전히 이 테스트에서 드러난다(서명은 대역이 아니다).

**증명**: 외부 네트워크를 막은 상태로 전체 스위트가 통과한다.

```
$ uv run python guarded_run.py
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
.........                                                                [100%]
225 passed in 72.94s (0:01:12)
```

정정해서 다시 쓰면: **수정 라운드 1 이후 전체 테스트 스위트의 외부 호출은 0건이다**(JWKS 조회·
애플 토큰 교환·provider discovery 가 전부 대역). 계정 자격증명 입력·NAS 접속·배포·`git push` 는
없었다.

미수정 MINOR 는 없다(D-10-2 를 고쳤다).

### rebase 후 전체 재검증

로컬 `main` **72a2a3c**(티켓 02 머지 4f9f179 + 티켓 21 머지) 위로 rebase 했다. 작업 트리는 clean.

```
$ uv run ruff check .
All checks passed!

$ uv run pytest -q
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
.........                                                                [100%]
225 passed in 76.63s (0:01:16)

$ FLASK_SKIP_DOTENV=1 FLASK_APP=wsgi.py uv run flask db heads
f394da7f4d88 (head)
```

rebase 로 `main` 에 티켓 02 의 `4e72a4045fbc` 가 들어와 heads 가 2개가 됐으므로, 공통 규칙대로
f394da7f4d88 의 `down_revision` 을 `9ec267465b4e` → `4e72a4045fbc` 로 재설정했다(위 출력이 1줄인
근거). 티켓 02 가 들여온 마이그레이션 왕복 테스트도 내 리비전이 얹힌 상태로 통과한다.

```
$ uv run pytest tests/test_token_exchange.py tests/test_migrations.py -q
22 passed in 26.59s
```

내 리비전만 따로 왕복도 다시 확인했다(마이그레이션 전용 DB `chosung_daily_test_t10_migrations`).

```
$ DATABASE_URL=...chosung_daily_test_t10_migrations uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 9ec267465b4e -> 4e72a4045fbc, add puzzle language and mask
INFO  [alembic.runtime.migration] Running upgrade 4e72a4045fbc -> f394da7f4d88, add account provider refresh token and client id
$ ... flask db current                     → f394da7f4d88 (head)
$ ... SHOW COLUMNS FROM account            → ['provider_user_id', 'provider_refresh_token', 'provider_client_id']
$ ... flask db downgrade 4e72a4045fbc
INFO  [alembic.runtime.migration] Running downgrade f394da7f4d88 -> 4e72a4045fbc, add account provider refresh token and client id
$ ... SHOW COLUMNS FROM account            → ['provider_user_id']
$ ... flask db upgrade                     → 4e72a4045fbc -> f394da7f4d88
$ ... SHOW COLUMNS FROM account            → ['provider_user_id', 'provider_refresh_token', 'provider_client_id']
```

마지막 전체 재확인(수정 전부 반영된 HEAD):

```
$ uv run ruff check .
All checks passed!
$ uv run pytest -q
225 passed in 97.61s (0:01:37)
$ FLASK_SKIP_DOTENV=1 FLASK_APP=wsgi.py uv run flask db heads
f394da7f4d88 (head)
```

## 머지 준비 rebase

리뷰(Codex 최종 PASS) 이후 로컬 `main` 이 두 번 앞서갔다. 처음 `21856d8`(티켓 03 머지)
위로 rebase 하는 도중 `main` 이 다시 `528879b`(티켓 20 머지)로 움직여서, 같은 방식으로 한 번
더 올렸다. 최종 베이스는 `528879b` 다.

```
$ git merge-base main HEAD
528879bec2ad62cecd6834e5342104f9d02a9e8a
$ git rev-parse main
528879bec2ad62cecd6834e5342104f9d02a9e8a
$ git status --short
(출력 없음 — clean)
```

### 충돌 파일과 해결 방식

충돌은 **`README.md` 1개**뿐이었다. 티켓 03 이 "설계 판단" 에 `### 03.` 세 절을, 이 티켓이
같은 자리에 `### 10.` 절을 붙여서 같은 블록을 양쪽이 건드렸다. **양쪽 내용을 모두 보존**해
03 세 절 뒤에 10 절이 오게 두는 것으로 풀었다 — 어느 쪽 문장도 지우거나 고치지 않았다.
두 번째 rebase(티켓 20)에서는 20 이 README 의 다른 영역(`### 20.`)만 건드려 자동 병합됐고,
결과적으로 `### 01./02./03./19./20./21.` 과 `### 10.` 이 모두 남아 있다.

다른 공유 파일은 충돌 없이 양쪽이 다 남았다.

- `README.md` API 표 — 03 의 `?language=` 행들과 이 티켓의 `POST /api/v1/auth/token-exchange`
  행이 함께 있다.
- `.env.example` — 앱 로그인 설정값 블록(`GOOGLE_IOS_CLIENT_ID`·`GOOGLE_WEB_CLIENT_ID`·
  `APPLE_APP_BUNDLE_ID`)이 그대로.
- `docs/RELEASE.md` — 티켓 20 이 추가한 내용만 있고 이 티켓은 손대지 않았다.
- `.scratch/store-launch/spec.md` — 이 티켓의 "미정 항목" 행만 유지.

### 리뷰 이후 코드 변경

**없다.** `git range-diff` 로 rebase 전 11개 커밋과 rebase 후 11개 커밋을 비교하면
`docs(10): 앱 로그인 설정값·ADR 0002 요약·구현 증거` 한 개만 다르고, 그 차이도 위 README
절이 붙는 위치(앞뒤 문맥 줄)뿐이다. 나머지 10개는 전부 동일(`=`)하다.

```
$ git range-diff 72a2a3c..808f23f 528879b..HEAD
 1:  0d0bcc8 =  1:  b65dd68 feat(10): Account 에 애플 refresh token·발급 client 컬럼 추가
 2:  51602d8 =  2:  b99acd6 feat(10): 구글·애플 JWKS 래퍼와 id_token 검증 순수 함수
 3:  f8057e9 =  3:  e653d97 feat(10): POST /auth/token-exchange — 앱 로그인과 애플 토큰 보관
 4:  b84111d !  4:  302889e docs(10): 앱 로그인 설정값·ADR 0002 요약·구현 증거
 5:  1d96d5e =  5:  df1caf4 review(10): final review round 1
 6:  abc3cd0 =  6:  0b537f4 fix(10): 모르는 kid 면 JWKS 를 다시 받아 키 교체 로그인을 받아들인다 (D-10-1)
 7:  754a75b =  7:  0b3b2b7 chore(10): 마이그레이션 down_revision 을 머지된 02 리비전 위로 재설정
 8:  9d8042a =  8:  af9e3b8 docs(10): 수정 라운드 1 증거 — D-10-1·D-10-2 원인·수정·검증 출력
 9:  5f9ffdd =  9:  85cd41f fix(10): 기존 OAuth 리다이렉트 테스트의 provider discovery 호출 제거
10:  853bfb6 = 10:  9b0d580 docs(10): 증거의 rebase 기준 커밋을 main 실제 tip(72a2a3c)으로 정정
11:  808f23f = 11:  10f6839 review(10): final review round 2
```

main 에 새로 들어온 코드(티켓 03 의 언어 인지 서비스·API, 티켓 20 의 배포 스크립트)와
맞물려 깨지는 테스트는 **없어서 테스트도 고치지 않았다.**

### 마이그레이션

티켓 03·20 은 마이그레이션을 들여오지 않아서 `main` 의 head 는 여전히 `4e72a4045fbc`(티켓 02)
이고, 이 티켓의 `f394da7f4d88` 은 이미 그 위에 얹혀 있다 — `down_revision` 을 다시 손댈 필요가
없었다. heads 가 1줄인 것과 왕복을 다시 확인했다.

```
$ FLASK_SKIP_DOTENV=1 FLASK_APP=wsgi.py uv run flask db heads
f394da7f4d88 (head)
```

```
$ DATABASE_URL=...chosung_daily_test_t10_migrations uv run flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade  -> 19c8c4591377, add word, daily_puzzle, guest, attempt, guest_stats, daily_stats
INFO  [alembic.runtime.migration] Running upgrade 19c8c4591377 -> e759d7e8d071, add account table for oauth linking
INFO  [alembic.runtime.migration] Running upgrade e759d7e8d071 -> 9ec267465b4e, replace kakao with apple as oauth provider
INFO  [alembic.runtime.migration] Running upgrade 9ec267465b4e -> 4e72a4045fbc, add puzzle language and mask
INFO  [alembic.runtime.migration] Running upgrade 4e72a4045fbc -> f394da7f4d88, add account provider refresh token and client id
$ ... flask db current            → f394da7f4d88 (head)
$ ... SHOW COLUMNS FROM account   → ['provider', 'provider_user_id', 'provider_refresh_token', 'provider_client_id']
$ ... flask db downgrade 4e72a4045fbc
INFO  [alembic.runtime.migration] Running downgrade f394da7f4d88 -> 4e72a4045fbc, add account provider refresh token and client id
$ ... SHOW COLUMNS FROM account   → ['provider', 'provider_user_id']
$ ... flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade 4e72a4045fbc -> f394da7f4d88, add account provider refresh token and client id
$ ... SHOW COLUMNS FROM account   → ['provider', 'provider_user_id', 'provider_refresh_token', 'provider_client_id']
$ ... flask db current            → f394da7f4d88 (head)
```

### rebase 후 전체 재실행

테스트 전용 자원(DB `chosung_daily_test_t10`, Redis DB 12, 마이그레이션 DB
`chosung_daily_test_t10_migrations`)으로 돌렸다. 리뷰 시점 225개에서 297개로 는 건 티켓 03·20
이 들여온 테스트가 합류했기 때문이고, 전부 통과한다.

```
$ uv run ruff check .
All checks passed!
$ uv run pytest -q
297 passed in 122.84s (0:02:02)
```
