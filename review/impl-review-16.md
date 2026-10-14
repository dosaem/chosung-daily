# 티켓 16 최종 리뷰 — 라운드 1

- 검토일: 2026-10-14. 대상 HEAD: `6044afc`.
- 기준: 로컬 `main`과의 `git diff main...HEAD`, `git log main..HEAD`. 공통 조상은 `4d83feb`; 검토 중 로컬 main이 `a520223`으로 전진했지만 공통 조상과 대상 변경은 동일하다. origin/main은 사용하지 않았다.
- 티켓 원문, 스펙 §A.15·US 29/45/45a·미정 9/21/22/23, 구현 증거, 디자인 SCREENS의 웹 절과 OVERRIDES를 대조했다. 구현 증거의 성공 주장을 판정 근거로 대신 쓰지 않았다.
- 범위: Standards(설정·공유 파일·보안)와 Spec(요구 충족·실제 처리 일치)을 직접 검토했다. 하위 에이전트·NAS·프로덕션·실제 외부 서비스 호출 없이 진행했다.

## 티켓 체크박스별 판정

| 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 조문·정책 → 요구 → 절 id → 테스트 체크리스트 전체 | 충족 | `docs/legal-checklist.md` §1~5에 필수 항목·5개 국외 이전 수신자·전자상거래·스토어 구독·EULA·해외 고지가 모두 있다. 다만 매핑 존재가 내용의 정확성을 보장하지는 않는다(D-16-1~3). |
| ko/en 본문 보완·동일 구조/순서/동치·구현과 보유 기간 일치 | 미충족 | 절 id·순서는 일치하고 14일 백업·7일 철회 재시도는 코드와 맞는다. 국외 이전 거부 방법, 백업 암호화 및 로그 보유 설명은 실제 코드·설정과 불일치한다(D-16-1~3). 백업 암호화 설명은 ko에만 있어 내용 동치도 깨진다. |
| 사업자 정보 설정값만·전화 선택·주소 코드 축약 금지·등록번호 패턴 부재 | 충족 | `app/config.py:124` 이후 사업자 필드는 빈 기본값의 환경변수다. `_business_info`는 strip만 하고 값이 있는 필드만 반환한다. 관련 테스트와 diff 확인상 실제 상호·주소·등록번호 추가 없음; 테스트의 명시적 더미 값은 실사업자 정보로 판정하지 않았다. |
| 공통 사업자 정보 Jinja 조각·양 문서 재사용·빈 신고번호 행 미표시 | 충족 | `_business_info.html`에서만 표시 범위를 결정하고 ko/en privacy·terms가 include한다. privacy 책임자 연락처와 문서 하단 사업자 블록이 같은 설정값을 쓴다. 티켓 18 푸터 연결은 후속 소비자 작업이다. |
| 체크리스트 파싱·ko/en id/순서·핵심 문구·삭제 링크/항목 집합 테스트 | 충족 | `tests/test_legal_checklist.py`는 0행 통과 방지, 실제 응답의 절 id 비교, 로그인 세션의 삭제 항목 비공집합 및 부분집합 검사를 수행한다. 단순 항상 통과 테스트는 아니다. 그러나 주요 설명의 의미와 실제 처리 일치를 검증하지 못해 D-16-1~3을 놓친다. |
| impeccable 0건·시행일 갱신·README 체크리스트/트리거/16절 | 증거 부족 | 직접 렌더한 8개 HTML과 3개 CSS의 오프라인 정적 detect는 0건. 외부 CDN 호출을 금지하기 위해 URL/실브라우저 검사는 재실행하지 않아 그 부분은 독립 확인하지 못했다. README 링크·정책 변경 트리거·16절은 충족. 시행일은 원래부터 작업 당일인 2026-10-14여서 값 유지가 결함은 아니다. |
| RELEASE 16절 사람 확인 체크박스 및 사용자 확인 3건 | 충족 | `docs/RELEASE.md:415`에 통신판매업·책임자·주소/전화·전문가·ASC EULA·Data safety 등 체크박스와 사용자 결정 3행이 있다. coordinator도 해당 사용자 결정을 확인했다. |
| 스펙 미정 9/21/22/23 결과·A.15 변경 금지 | 충족 | 스펙 diff는 티켓 16 결과 한 행 추가뿐이고 §A.15는 바뀌지 않았다. |
| 필요 시 분할·분할 통지·후속 티켓 표시 | 충족 | 분할하지 않고 해외 고지와 스토어 구독 행까지 포함했으므로 조건부 분할 절차는 해당 없음. |

## 직접 실행한 검증

- 전용 로컬 MySQL DB `chosung_daily_test_t16`, Redis DB 4를 각각 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. URL의 인증정보는 이 문서에 기록하지 않는다. 접속 성공, 기본 테스트 DB 대체 없음, 새 DB 생성 없음.
- `uv run pytest tests/test_legal_checklist.py tests/test_legal_pages.py tests/test_account_delete_page.py -q`: **250 passed in 186.33s (0:03:06)**, exit 0.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `uv run pytest tests/test_backup_restore.py::test_backup_writes_gzipped_dump tests/test_backup_restore.py::test_backup_keeps_14_days_and_deletes_older -q`: **2 passed in 0.99s**, exit 0. 이 두 테스트는 DB fixture를 사용하지 않으며 외부 명령을 스텁으로 대체한다.
- `FLASK_ENV=testing uv run flask --app wsgi db heads`(Sentry 비활성화): `d7a1f0ca0a29 (head)` 한 줄, exit 0. 변경에 마이그레이션은 없다.
- `git diff main...HEAD --check`: exit 0.
- impeccable 0.1.14: Flask로 privacy/terms 각 2개, 삭제 안내/확인 각 2개를 임시 디렉터리에 렌더하고 로컬 CSS 3개를 함께 정적 검사했다. 임시 사본에서 외부 폰트 CDN link만 제거하고 `/static/` 경로를 로컬 상대 경로로 바꿨다. `impeccable detect --json <임시 디렉터리>` → `[]`, exit 0. 앱·설정·테스트 파일은 수정하지 않았다. 실제 URL 브라우저 검사나 CDN 폰트 포함 레이아웃 검증과 동등하다고 주장하지 않는다.

## 결함 목록 — Spec

### D-16-1 — MAJOR — 계정 미연결을 구독 검증까지 포함한 국외 이전 거부 수단으로 잘못 고지

- 파일: `web/templates/legal/privacy.ko.html:156`, `:167`; `web/templates/legal/privacy.en.html:169`, `:180`.
- Google/Apple 행은 로그인 **및 구독 검증**을 묶은 뒤, 계정을 연결하지 않거나 해제하면 이전이 없다고 단정한다. 그러나 `app/api/subscriptions.py:10`은 게스트 인증만 요구하며 `app/services/subscription_service.py:43` 이후는 연결 계정 여부와 관계없이 스토어 클라이언트를 호출한다. 계정 미연결 상태에서도 구매 식별자가 이전되는 경로다.
- 재현: testing 앱의 요청 컨텍스트에 Account를 연결하지 않은 `Guest(id=1)`을 `g.guest`로 넣고, POST `/api/v1/subscriptions/verify` 본문에 `store=google` 또는 `apple`과 합성 receipt를 준다. `app.clients.play.fetch_subscription` / `app.clients.app_store.fetch_subscription`만 호출 기록 후 예외를 던지는 mock으로 바꾸고 `verify.__wrapped__()`를 실행했다. 인증 후 뷰와 서비스는 실제 코드를 실행하고, 외부 경계만 차단했다.
- 기대: 안내한 거부 방법이 로그인·구독 검증을 각각 구분하고, 미연결 게스트의 구독 검증 및 그 효과를 정확히 설명한다. 실제: 두 경우 모두 `linked_account=None`, `store_client_called=1`인데 본문은 "이전이 없습니다 / there is no transfer"라고 한다.
- 영향: 계정 미연결을 선택한 구독 이용자가 자신의 데이터 이전을 잘못 이해한다. 말미의 광고·분석·오류 전송 일반 주의문으로 이 수신자별 잘못된 안내가 해소되지 않는다. `test_overseas_section_lists_every_recipient`는 이름과 URL만 확인해 이 모순을 검출하지 못한다.

### D-16-2 — MAJOR — 구현하지 않은 백업 덤프 암호화를 한국어 방침에 보장

- 파일: `web/templates/legal/privacy.ko.html:225`; 비교: `web/templates/legal/privacy.en.html:239`.
- 새 문구는 "백업본은 **암호화된 덤프 파일**째로" 폐기한다고 한다. 실제 `scripts/backup.sh:63`은 `mysqldump | gzip -c`만 수행하고 `docker-compose.prod.yml`의 backup 서비스는 그 `.sql.gz` 파일을 bind mount에 보관한다. Apple refresh token의 필드 암호화와 DB 덤프 전체 암호화는 다르다.
- 재현 명령: `uv run pytest tests/test_backup_restore.py::test_backup_writes_gzipped_dump -q`. 실제 스크립트로 생성한 합성 덤프를 테스트 `tests/test_backup_restore.py:134`가 **복호화 키 없이 `gzip.decompress`만으로** 풀어 SQL 내용을 읽으며 통과했다.
- 기대: 공개한 보호 조치가 실제 백업 방식과 일치하고 ko/en이 같은 내용을 설명한다. 실제: 덤프는 압축만 되는데 ko는 암호화를 보장하고 en은 단순 dump files라고 한다.
- 영향: 실제 개인정보 백업 보호 수준을 과장한 고지이며 티켓의 구현 일치·언어 동치 조건을 모두 위반한다. 이 리뷰는 백업 코드 변경을 요구하는 것이 아니라 현재 방식에 맞는 고지가 필요함을 지적한다.

### D-16-3 — MAJOR — 근거 없는 서버 접근 로그 1년 보유·기간 만료 파기를 현재 동작으로 고지

- 파일: `web/templates/legal/privacy.ko.html:90`, `:230`; `web/templates/legal/privacy.en.html:100`, `:244`.
- 새 본문은 서버 접속기록을 1년 이상 보관하고 법정 기간이 지나면 삭제한다고 명시한다. 레포의 운영 실행 경로 `Dockerfile:18`는 접근 로그 옵션 없는 Gunicorn이고, compose·app·scripts 어디에도 해당 로그의 수집/마스킹/1년 보유/만료 파기 구성이 없다. Sentry 수집 제한(`app/observability.py`)은 서버 접근 로그 보관 구현을 대신하지 않는다.
- 재현 명령: `uv run python -c 'from gunicorn.config import Config; print(Config().accesslog)'` → **None**. 이어 `rg -n 'accesslog|logrotate|365|1년' Dockerfile docker-compose* app scripts`로 해당 설정/정리 작업이 없는 것을 확인했다. 운영 command는 이 기본값을 덮어쓰지 않는다.
- 기대: 방침의 보유 기간 숫자는 현행 구현에 근거해야 하며, 외부 운영 설정에 의존하면 확인 가능한 설정 또는 출시 전 미완료 항목으로 구분한다. 실제: 레포 기본 운영 구성에서는 요청 접근 로그조차 활성화되지 않는데 수집·보유·파기를 이미 수행하는 것처럼 적었다.
- 영향: 이용자가 삭제 후 어떤 요청 정보가 얼마나 남는지 잘못 이해한다. NAS의 별도 로그 운영 여부는 접근 금지로 확인하지 않았으며 존재한다고 추정하지 않았다. 특정 법령의 적용 여부가 아니라 **새로 한 기술적 보유 약속의 구현 근거 부재**를 결함으로 판정한다.

## Standards 및 참고

- 인증/CSRF 경로 변경 없음. 삭제 페이지 변경은 링크 문구이며 기존 인증·삭제 대상 바인딩·CSRF 테스트를 함께 실행했다. 사업자 값은 Jinja 기본 escaping으로 출력하며 새 입력 API나 DB 변경이 없어 이번 diff에서 데이터 손상 경로를 발견하지 않았다.
- 공유 파일은 기존 타 티켓의 설계 판단·RELEASE 절을 덮어쓰지 않고 자기 16절/설정 행/결과 행을 추가했다. README 법적 문서 절의 수정은 티켓이 명시한 작업이다. 범위 밖 기능 변경이나 실제 운영 시크릿 추가는 발견하지 않았다. 증거 문서의 로컬 테스트 접속정보는 리뷰에 복사하지 않았다.
- 개인정보 수집·삭제 모델, Apple 철회 7일, 백업 14일, Sentry 수집 제한과 Flutter 초기화 코드를 대조했다. 이 worktree에는 `app_privacy_details.json`이 없고 광고/분석 후속 구현도 아직 완성되지 않아 최종 스토어 제출 데이터와 일치 여부는 검증할 수 없다. 후속 SDK/스토어 라벨 티켓 완료 시 반드시 재대조해야 한다.
- **전문가 확인 권장(결함 수에 포함하지 않음):** 주소 공개 범위 및 통신판매업 해당 여부, 국외 이전의 계약 이행 근거, 국가를 "미국 등"으로 적은 범위의 충분성, EU 광고 처리 근거와 캘리포니아의 "공유하지 않음" 표현. 사용자 결정 자체를 결함으로 올리지 않았고 현행 법 적용을 확정하는 법률 의견도 내지 않는다.
- 전체 스위트 992건 통과 주장은 독립 재실행하지 않았다. 이 리뷰의 테스트 범위와 정적 디자인 검사 한계는 위에 명시했다.

## 최종 검증 기록

법적 문서·계정 삭제 관련 테스트 250건 및 백업 관련 추가 검증 2건 모두 통과했다. 간헐 실패가 없어 재실행하지 않았다. ruff 통과와 마이그레이션 단일 head를 직접 확인했으나, 위 세 문서/구현 불일치는 그대로 존재한다.

결함 합계: BLOCKER 0 / MAJOR 3 / MINOR 0.

판정: FAIL

## 라운드 2

- 검토일: 2026-10-14. 대상 HEAD: `a334ea6`, 로컬 main과의 공통 조상: `0756137`.
- `git diff main...HEAD` 및 `git log main..HEAD`의 8개 커밋을 확인했다. origin/main은 사용하지 않았다. 수정분은 `git diff 1c0bda6..HEAD`로도 대조했다.
- 티켓 16, 스펙 §A.15·US 29/45/45a·미정 9/21/22/23, 구현 증거, SCREENS 웹 절 및 OVERRIDES §10을 직접 읽었다. Standards와 Spec을 직접 검토했고 하위 에이전트는 사용하지 않았다.
- 코디네이터의 재리뷰 지시를 반영했다: 백업 암호화·접속기록 보관의 미구현 상태를 사실대로 고지하고 RELEASE 사람 항목으로 넘긴 것은 그 자체로 결함이 아니다. 법률 적합성의 최종 인증이 아니라 티켓 요구 및 고지와 코드의 일치 여부를 판정한다.

### 티켓 체크박스별 판정

| 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 조문·정책 → 요구 → 절 id → 테스트 체크리스트 전체 | 충족 | `docs/legal-checklist.md` §1~5에 필수 기재 항목, 국외 이전 5개 수신자, 전자상거래·구독·EULA·해외 사용자 항목이 있다. 파싱 및 양방향 절 매핑 테스트 통과. 의미상의 정확성은 별도 D-16-4 참조. |
| ko/en 본문 보완·동일 구조/순서/동치·현행 구현과 일치 | 미충족 | 구조·순서 테스트 통과. 백업 14일·Apple 철회 재시도 7일, 백업 비암호화 및 로그 보관 미구현 고지는 코드와 대조했다. 다만 새 Apple 철회 거부 문장이 삭제 후 전송과 충돌한다(D-16-4). |
| 사업자 정보 설정값만·전화 선택·주소 코드 축약 금지·등록번호 패턴 부재 | 충족 | `app/config.py:130` 부근 사업자 필드는 빈 환경변수 기본값이며 `_business_info`는 strip만 한다. 등록번호 패턴 부재·빈 값/부분 설정 표시 테스트 통과. 실제 사업자 정보 추가는 발견하지 않았다. |
| 사업자 정보 공통 Jinja 조각·양 문서 재사용·빈 신고번호 미표시 | 충족 | `_business_info.html`에 표시 조건을 모으고 ko/en privacy·terms가 include한다. 테스트가 실제 렌더 응답을 확인한다. 티켓 18의 푸터 소비는 별도 후속 범위다. |
| 체크리스트 파싱·절 id/순서·핵심 문구·삭제 링크/항목 집합 테스트 | 충족 | 테스트가 빈 표/빈 삭제 항목 집합을 거부하고 실제 페이지의 절·항목을 비교한다. 추가 구독 테스트는 외부 스토어 경계만 대체하며 게스트 인증·서비스·DB를 실제로 통과한다. 철회 문구 회귀의 빈틈은 D-16-4에 적었다. |
| impeccable 0건·시행일 갱신·README 링크/트리거/16절 | 증거 부족 | 오프라인 정적 detect는 0건이며 README 요구는 충족. 시행일은 작업일과 같은 2026-10-14라 유지가 결함은 아니다. 외부 서비스 호출 금지에 따라 CDN을 포함한 URL 브라우저 검사는 재실행하지 않았다. |
| RELEASE 16절 사람 확인 및 사용자 확인 결과 3건 | 충족 | `docs/RELEASE.md:564` 이하 사용자 결정 3행·필수 사람 체크박스가 있고 `:605`, `:612`에 로그 보관·백업 암호화 결정이 추가됐다. 이전 라운드의 사용자 결정 확인을 유지한다. |
| 스펙 미정 9/21/22/23 결과·A.15 변경 금지 | 충족 | diff는 자기 16 결과/수정 행 추가뿐이며 §A.15는 변경하지 않았다. |
| 필요 시 분할·통지·후속 표시 | 충족 | 해외 사용자와 스토어 구독 고지를 모두 포함하여 조건부 분할 절차는 해당 없음. |

### 이전 결함 판정

| ID | 이전 심각도 | 판정 | 직접 확인한 수정 및 재현 결과 |
|---|---|---|---|
| D-16-1 | MAJOR | FIXED | `privacy.ko.html:160`, `:171` 및 en `:174`, `:185`가 구독 검증을 로그인과 분리하고 계정 미연결 상태에서도 구매 식별자가 전송됨을 명시한다. `test_verify_reaches_the_store_without_a_linked_account` 두 스토어 사례가 실제 API 호출 후 Account 0행 및 스토어 경계 호출을 검증하며 통과했다. 원래 지적한 **구독 검증** 누락은 해소됐다. 새로 명시한 철회 범위의 오류는 D-16-4로 구분한다. |
| D-16-2 | MAJOR | FIXED | ko `:230`·en `:245`가 압축 덤프 및 덤프 자체 비암호화를 동일하게 고지한다. `scripts/backup.sh:63`과 실제 스크립트의 gzip 복원 테스트를 대조했다. 백업 암호화 구현은 요구하지 않는다. |
| D-16-3 | MAJOR | FIXED | ko `:90`~`:97`, `:235`~`:236`, `:271`과 en 대응 절에서 1년 보유/법정 기간 만료 파기 약속을 제거하고 현행 별도 보관 없음·출시 전 적용 예정으로 구분했다. Gunicorn 기본 accesslog=None과 Dockerfile·compose 설정 및 관련 테스트를 확인했다. RELEASE의 미완료 항목도 존재한다. 실제 NAS 로그 설정은 확인하지 않았다. |

### 새 결함 — Spec

#### D-16-4 — MAJOR — Apple 연결 철회를 이전이 없는 범위에 넣어 실제 철회·재시도 전송과 충돌

- 파일: `web/templates/legal/privacy.ko.html:171`, `web/templates/legal/privacy.en.html:185`.
- 수정된 거부 방법은 **“로그인·연결 철회” / “Sign-in and revocation”**를 묶어, 계정을 연결하지 않거나 해제하면 이전이 없다고 단정한다. 특히 en의 “the Apple refresh token exists only for a linked account”는 계정 삭제 뒤에도 토큰이 재시도 테이블에 남는 사실과 맞지 않는다.
- 실제 경로: `app/services/account_deletion_service.py:57`~`:69`는 철회 의무를 저장하고 Account/Guest 삭제를 커밋한 **뒤** Apple 철회 호출을 한다. 실패하면 `AppleRevocationRetry`에 토큰을 남기고 `app/services/apple_revocation_service.py:83`~`:85`, `:125`~`:129`에서 다시 전송한다. 즉 구독을 구매하지 않은 이용자도 이미 연결했던 Apple 계정을 삭제하는 과정과 실패 재시도 중에 refresh token이 전송될 수 있다.
- 재현 명령(아래와 동일한 전용 테스트 환경): `uv run pytest tests/test_apple_revocation.py::test_ios_linked_account_is_revoked_with_the_app_bundle_id tests/test_apple_revocation.py::test_failed_revoke_still_deletes_the_account_and_records_a_retry tests/test_apple_revocation.py::test_retry_removes_the_row_when_apple_accepts -q`. 이 세 사례를 포함한 파일 전체 18건을 직접 실행해 모두 통과했다. 첫 사례는 삭제 시 HTTP 경계에 전달된 토큰을 검사하고, 두 번째는 계정 삭제 뒤 토큰 보존을, 세 번째는 연결 계정 없이 재시도 행만 있는 상태에서 토큰 재전송을 검사한다. 실제 Apple 호출은 requests.post 대역으로 차단한다.
- 기대: 처음부터 연결하지 않은 경우, 연결 후 삭제/철회 요청 시 전송, 실패 시 재시도 전송을 구분해 현행 처리와 같은 범위로 거부 효과를 설명해야 한다. 실제: 철회까지 “이전 없음” 범위로 읽히며, 같은 방침의 7일 재시도 고지와도 충돌한다.
- 테스트 한계: `tests/test_legal_pages.py:464`~`:473`는 “로그인/Sign-in”이 “이전 없음”보다 먼저 나오는지만 검사하므로, 그 범위에 “연결 철회/and revocation”를 추가한 현재 문장도 통과한다. 문구 검사 통과만으로 이 철회 경로의 설명이 정확하다고 볼 수 없다.
- 영향: 이용자가 삭제/연결 철회를 통해 중단되는 이전의 범위를 잘못 이해한다. 법 해석의 불확실성이 아닌 재현 가능한 문서/처리 불일치이며, 애플리케이션 변경 없이 고지 범위를 바로잡을 수 있다.

### 직접 실행한 검증

- 기존 로컬 DB `chosung_daily_test_t16` 및 Redis DB 4를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. 접속 성공, 기본 DB 대체 없음, 새 DB 생성 없음. 접속 URL·키·토큰·비밀번호 값은 이 문서에 기록하지 않는다. Sentry DSN을 비워 테스트 중 외부 전송을 비활성화했다.
- `uv run pytest tests/test_legal_checklist.py tests/test_legal_pages.py tests/test_account_delete_page.py tests/test_subscription_verify.py tests/test_backup_restore.py -q` → **344 passed in 266.06s (0:04:26)**, exit 0.
- `uv run pytest tests/test_apple_revocation.py -q` → **18 passed in 12.97s**, exit 0. 앞 테스트와 순차 실행하여 DB 정리 경합을 피했다. 간헐 실패가 없어 재실행하지 않았다.
- `uv run ruff check .` → **All checks passed!**, exit 0.
- `FLASK_ENV=testing SENTRY_DSN='' uv run flask --app wsgi db heads` → **d7a1f0ca0a29 (head)** 한 줄, exit 0. 이 티켓의 마이그레이션 변경은 없다.
- `git diff main...HEAD --check` → exit 0.
- impeccable 0.1.14: privacy/terms ko/en 4개, 삭제 안내 ko/en 2개, 삭제 확인 템플릿 ko/en 2개를 임시 디렉터리에 렌더하고 tokens/legal/account CSS를 복사했다. 임시 HTML에서 외부 CDN link만 제거하고 static 경로를 상대 경로로 바꾼 뒤 `impeccable detect --json <임시 디렉터리>` → **[]**, exit 0. 확인 폼은 합성 값으로 템플릿을 렌더했으며 앱 파일은 수정하지 않았다. URL 브라우저 검사·외부 폰트 레이아웃 검증과 동등하지 않다.
- 증거 문서의 전체 스위트 1253건 성공 주장을 독립 재실행했다고 주장하지 않는다. 이번 직접 검증 범위는 위 362건이다.

### Standards 및 참고

- 인증·CSRF·DB 모델 변경 없음. 삭제 페이지는 링크 표시 문구만 바뀌었고 관련 인증/CSRF 테스트도 위 스위트에 포함된다. 사업자 값은 기본 Jinja escaping을 통과한다. 이번 diff에서 새 데이터 손상 경로나 운영 시크릿 추가는 발견하지 않았다. 증거의 로컬 테스트 접속값과 테스트 합성 자격증명을 실제 운영 시크릿으로 판정하지 않았으며 이 리뷰에는 복사하지 않았다.
- README 설계 판단·RELEASE는 자기 16절, `.env.example`과 스펙은 자기 설정/결과 행을 추가한다. 타 티켓 절 덮어쓰기 없음. README 법적 문서 절 수정은 티켓이 명시한 범위다. 앱·테스트·설정·`.scratch/` 파일은 리뷰 중 수정하지 않았다.
- 전문가 확인 권장: 주소 공개 범위와 통신판매업 해당 여부, 국외 이전 근거·국가 표현, 해외 광고 처리 근거 및 캘리포니아 공유 표현. 이는 이번 결함 수에 포함하지 않으며 출시 전 사람 체크리스트와 후속 SDK/스토어 라벨 대조로 남긴다.

기존 결함 FIXED 3 / REPEAT 0. 현재 결함 합계: BLOCKER 0 / MAJOR 1 / MINOR 0 (신규 D-16-4).

판정: FAIL
