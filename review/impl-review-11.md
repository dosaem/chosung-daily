# 티켓 11 최종 리뷰 — 라운드 1

## 검토 기준

- 로컬 `main` = `d44017269f7c6781048ddb2fefc246b6d32a22b1`, 구현 HEAD = `5197a29ab072adf2a23b95e998e3bba3dd5feb5d`.
- `git diff main...HEAD` 전체 12개 파일과 `git log main..HEAD`의 6개 커밋을 직접 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 `.scratch/store-launch/issues/11-apple-client-secret-auto-renew.md`, 스펙 §A.12·§A.13·US 68 및 번들 ID 관련 미정 17 확정 사항, `review/impl-evidence-11.md`를 대조했다.
- 사용자 지시에 따라 하위 에이전트 없이 검토했다. 애플리케이션·테스트·설정·`.scratch/` 수정, 프로덕션 접근, 실제 Apple/Slack 호출, push는 하지 않았다.

## 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 공개 client_id 접근자, 7일 미만 재서명·교체, login/callback 및 티켓 10 토큰 교환에서 사용, 프로세스별 보관 | 충족 | `app/extensions.py:108` 접근자가 캐시 잔여 시간을 비교해 재서명한다. `app/api/oauth.py:33`에서 Authlib 속성을 교체하며 login(63행)·callback(83행)이 모두 진입 시 호출한다. `app/services/app_login_service.py`의 `_exchange_apple_code`도 같은 공개 접근자를 호출한다. 저장 위치는 앱별 `app.extensions`이고 DB·Redis 저장이 없다. |
| 만료 6일 남은 login/callback의 새 JWT·Authlib 교체 테스트 및 번들 ID 규칙 | 충족 | `tests/test_apple_secret_renewal.py:112`, `:124`에서 두 라우트를 실제 Flask 클라이언트로 호출해 속성 변경·새 만료 시각을 검사한다. 번들 ID 갱신·캐시 유지 테스트도 실행해 통과했다. 별도 메모리 검증으로 두 ID의 실제 ES256 서명, 150일 수명, 정확히 7일/7일 미만 경계와 이미 만료된 secret을 확인했다. |
| `/health.apple_secret_expires_at`에 두 ID 중 이른 시각 | 충족 | `app/extensions.py:151`, `:168`에서 설정된 두 client의 만료 시각을 읽어 최솟값을 반환하고 `app/api/health.py`가 ISO 형식으로 응답한다. 미사용 번들 ID 최초 서명, 관측 시 갱신하지 않음, 설정 없음의 null, DB·Redis 장애 시 응답 관련 테스트가 통과했다. |
| Beat 주 1회, 7일 전 notify_operator, 서비스 직접 호출 테스트 | 충족 | `app/tasks/scheduled.py:57`에 월요일 09:10 스케줄이 있고 태스크가 서비스를 호출한다. `app/services/apple_secret_service.py:31`의 만료 필터·알림 호출과 서비스 직접 호출 테스트를 확인했다. 번들 ID만 임박한 경우도 별도 검증에서 알림 1회·JWT 미포함을 확인했다. |
| README 설계 판단에 요청 경로 갱신 선택 근거 | 충족 | `README.md:978`의 `### 11.`에 Beat 재서명과의 비교, 프로세스별 캐시, Authlib 갱신 지점, 관측 함수 분리 이유가 있다. |

## 독립 실행 결과

구현 증거의 성공 주장을 그대로 인용하지 않고 다음을 새로 실행했다.

- 테스트 환경: `TEST_DATABASE_URL`은 localhost의 기존 `chosung_daily_test_t11`, `TEST_REDIS_URL`은 localhost의 Redis DB 13, `TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t11_migrations`를 지정했다. 접속 성공으로 기본 DB 대체나 새 DB 생성은 없었다. 접속 자격정보는 문서에 기록하지 않는다.
- `FLASK_SKIP_DOTENV=1`, 빈 `SLACK_WEBHOOK_URL`·`SENTRY_DSN`을 지정했다. 외부 API 경계는 기존 테스트의 대역을 사용하며 배포·백업 테스트도 로컬 스텁/루프백 대상이다.
- `uv run pytest -q`: **555 passed in 331.11s (0:05:31)**, 종료 코드 0. 최초 실행은 테스트 실패 출력 없이 11개 진행 표시 후 종료 코드 143으로 중단돼 원인 미확정으로 남겼고, 동일 명령 재실행은 모두 통과했다. 실패·skip·xfail 없음.
- `uv run ruff check .`: **All checks passed!**, 종료 코드 0.
- `FLASK_APP=wsgi.py uv run flask db heads`(위 환경 적용): **`ff06a1bf5afc (head)`**, 한 줄. 이 티켓의 마이그레이션 변경은 없다.
- `git diff --check main...HEAD`: 출력 없음.
- 파일을 만들지 않는 `uv run python -` 추가 검증: 테스트 설정의 일회성 EC 키로 만든 JWT를 공개키로 검증했다. Services ID·번들 ID 각각 `iss`·`aud`·`sub`·150일 수명을 확인했고, 시계를 고정해 정확히 7일이면 유지, 7일에서 1마이크로초 부족하면 갱신, 이미 만료됐으면 갱신됨을 확인했다. `_get_client('apple')` 이후 실제 Authlib `_get_oauth_client()`가 새 secret을 전달받는지도 확인했다. 모두 통과했고 네트워크 호출은 없었다.

## 결함 목록

없음. BLOCKER 0건 / MAJOR 0건 / MINOR 0건. 등록할 결함이 없어 D-11-1은 부여하지 않았다.

## 보안·범위·테스트 검토

- 갱신은 기존 인증·세션·nonce·state 검증을 제거하거나 우회하지 않는다. client_id는 요청 입력이 아닌 서버 설정에서 선택한다.
- 새 `/health` 필드는 만료 시각만, 알림은 client_id·만료 시각만 내보낸다. 변경 파일에 실제 개인키·OAuth JWT·Slack 토큰이 기록된 증거는 없다. 증거 문서의 로컬 테스트 DB 예시와 테스트의 가짜 문자열은 운영 시크릿과 구분했다.
- 모델·데이터 쓰기 경로 변경이 없고 새 데이터 손상 경로는 발견하지 못했다.
- 공유 문서의 기존 설계 판단·타 티켓 내용을 바꾸지 않고 `### 11.`과 자신의 스케줄 행·명령을 추가했다. `.env.example`, RELEASE, 스펙은 변경하지 않았다.
- 공통 OAuth discovery fixture를 `conftest.py`로 옮긴 변경은 두 테스트 모듈에서 오프라인 대역을 재사용하려는 범위다. 서명·갱신 함수 자체는 mock하지 않아 변경된 동작을 실질적으로 검사한다.
- UI 변경이 없어 디자인 대조는 해당 없음.

## 참고

- 콜백 갱신 테스트는 보류 세션 없는 401 응답까지 진행하므로 실제 Apple 로그인 왕복 성공까지 증명하지 않는다. 요구된 진입 시 교체는 검증하며, 추가 검증과 설치된 Authlib 코드 확인으로 다음 OAuth 세션에 새 secret이 전달됨을 확인했다. 실제 외부 서버 검증은 이번 작업 범위 밖이다.
- 알림은 태스크를 실행하는 Celery 워커의 로컬 캐시를 관측한다. gunicorn 워커 전체의 갱신 상태를 집계하지 않으므로, 알림을 웹 로그인 갱신 장애의 확정 신호로 해석하면 안 된다. README의 “Beat 자신” 표현도 정확히는 태스크 실행 워커를 뜻한다. 프로세스별 캐시·외부 저장 없음이라는 이번 명시 범위에서는 이를 기능 결함으로 올리지 않았다.

판정: PASS
