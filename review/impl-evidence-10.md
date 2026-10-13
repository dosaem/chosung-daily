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
