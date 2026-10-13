# 티켓 09 최종 리뷰 — 라운드 1

검토 대상 HEAD: `2168a15`, 로컬 main: `21856d8`, merge-base: `72a2a3c`.
`git diff main...HEAD` 및 `git log main..HEAD --oneline`의 구현 커밋 5개를 검토했다.
티켓 09, 스펙 §A.15·§A.16·US45·미정 9, CONTEXT, SCREENS 웹 절, MASTER 및 우선 규칙 OVERRIDES와 구현 증거를 대조했다.

## 체크박스별 판정

| 티켓 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 공용 토큰 CSS, 라이트/다크, 그림자 없음, Pretendard, 메인 스타일 유지 | 충족 | `tokens.css` 색상·간격·폰트 값을 OVERRIDES와 직접 대조했다. 브라우저 라이트/다크 배경·전경도 일치한다. 기존 `style.css`·`index.html` diff 없음. 문서 레이아웃의 별도 편차는 D-09-3. |
| Jinja ko/en 개인정보처리방침 및 필수 공시 | 미충족 | 4개 URL 모두 200이고 수집 항목 6개, 보유 기간, 업체 5개, 국외 이전, 아동, 삭제 링크, 연락처가 존재한다. 그러나 국외 이전 거부 방법이 서비스 사양과 충돌한다(D-09-1). 언어 협상에도 경계 오류가 있다(D-09-2). |
| 구독 자동 갱신·스토어 해지·EULA 선택 자리 | 충족 | 두 언어 약관에 자동 갱신, App Store/Google Play 해지 경로, 삭제와 해지의 구분, Apple 표준 EULA 링크와 커스텀 선택 안내가 있다. 미정 9의 최종 선택은 이 티켓의 완료 조건이 아니다. |
| pytest 렌더 테스트·두 페이지 detect 0건 | 충족 | 전체 실행 307 passed / 8 환경 오류 후 오류 8개 재실행 모두 통과. 추가 테스트 129개는 실제 렌더·정적 파일·순수 함수 검사이며 렌더를 mock하지 않는다. ko/en × 두 페이지의 렌더 HTML과 실제 공용 CSS를 detect로 독립 검사하여 0건. |
| README 경로·갱신 책임·설계 판단 | 충족 | 법적 문서 절에 경로 및 운영자 갱신 책임, 갱신 트리거가 있다. 설계 판단 끝에 자기 번호 `### 09.` 추가, API 표 끝에 자기 경로 2행 추가. |

## 직접 실행한 검증

접속값은 구현 증거의 로컬 테스트 설정을 사용했고 이 문서에는 인증값을 기록하지 않는다.
`TEST_DATABASE_URL`은 기존 `chosung_daily_test_t09`, `TEST_REDIS_URL`은 로컬 Redis DB 11,
`TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t09_migrations`를 지정했다.
새 DB 생성이나 기본 테스트 DB로의 전환은 하지 않았다.

| 명령/검사 | 결과 |
|---|---|
| 위 환경변수 지정 후 `uv run pytest -q` | `307 passed, 8 errors in 203.04s`. 오류 8개 모두 fixture의 `db.create_all()` 연결 단계에서 MySQL 1040 `Too many connections`. 다른 워커 테스트도 병렬 실행 중이었다. |
| 동일 환경에서 `uv run pytest -q --lf --tb=short` | `8 passed in 10.10s`, exit 0. 최초 오류 항목만 1회 재실행했으며 전체를 한 번에 315 passed로 재실행했다고 주장하지 않는다. |
| `uv run ruff check .` | `All checks passed!`, exit 0. |
| `FLASK_ENV=testing uv run flask --app wsgi db heads` | `4e72a4045fbc (head)` 1개. 이 티켓의 마이그레이션 변경은 없다. |
| `git diff main...HEAD --check` | exit 0. |
| Flask test client: `/privacy?lang=ko`, `/privacy?lang=en`, `/terms?lang=ko`, `/terms?lang=en` | 모두 200, Content-Language 및 본문 언어 일치. |
| 로컬 Chrome/Playwright, 768px, 4 URL × light/dark | CSS 로드 완료 후 light 배경/전경 `rgb(250,250,249)` / `rgb(15,23,42)`, dark `rgb(20,26,38)` / `rgb(241,245,249)`. 문서 외곽 폭은 모두 528px. |

### detect 재검증 방법과 한계

사용 바이너리: `/Users/saem/.impeccable/bin/0.1.14/impeccable`.
Flask test client로 4개 문서를 실제 렌더하고, `/tmp/t09-final-review/`의 임시 HTML에
`tokens.css`와 `legal.css` 원문을 순서대로 `<style>`에 넣었다. stylesheet 링크는 제거했다.
이는 Jinja 링크 해석 실패 및 외부 CDN 호출을 피하면서 실제 공용 CSS 기준으로 검사하기 위한 것이다.

```sh
/Users/saem/.impeccable/bin/0.1.14/impeccable detect /tmp/t09-final-review/privacy-ko.html /tmp/t09-final-review/privacy-en.html /tmp/t09-final-review/terms-ko.html /tmp/t09-final-review/terms-en.html
```

출력 없음, exit 0. 대조군 `detect .scratch/store-launch/design/archive/v2_softdark_home.html`은
7건, exit 2로 탐지 동작을 확인했다. 개발 서버는 loopback `127.0.0.1:5099`에만 띄웠고,
브라우저의 외부 요청은 차단했다. CDN 글꼴 다운로드와 외부 약관 링크의 도착지는 검증하지 않았다.
프로덕션·NAS·실제 외부 서비스에 접근하지 않았다.

## 결함 목록

### D-09-1 — MAJOR: 게스트 플레이를 국외 이전 거부 방법으로 잘못 안내

- 위치: `web/templates/legal/privacy.ko.html:108`, `web/templates/legal/privacy.en.html:115`.
- 재현 입력: `/privacy?lang=ko` 또는 `/privacy?lang=en`을 열고 4절의 거부 방법을 읽는다. 이어 스펙 §B.21 광고 게이트, §B.24 분석, §C.30 Sentry 및 티켓 24의 Analytics 이벤트 조건과 대조한다.
- 기대: 계정 연결을 하지 않아도 앱 광고·분석 및 오류 추적의 전송은 발생할 수 있음을 정확하게 구분한다. 계정 연결 여부만으로 전체 국외 이전을 거부할 수 있다고 안내하지 않는다.
- 실제: 두 언어 모두 계정을 연결하지 않고 게스트로 플레이하면 국외 이전을 피할 수 있다고 안내한다. 같은 방침의 광고 ID·제3자 절은 AdMob 직접 전송과 Analytics/Sentry 처리를 설명하며, 사양의 광고 게이트는 UMP 상태이지 계정 연결 여부가 아니다. 퍼즐 완료·공유 분석 이벤트도 연결된 계정에만 한정되지 않는다.
- 영향: 이용자가 실제로 전송을 중단하지 못하는 방법을 거부 절차로 믿게 된다. 법적 문서 티켓의 핵심 공시 내용에 대한 기능적 오류로, 법률 적합성 판단이나 문체 제안이 아니다. 기존 키워드 포함 테스트는 이 모순을 잡지 못한다.

### D-09-2 — MINOR: 지역 언어 태그가 있으면 낮은 q값의 언어를 선택

- 위치: `app/utils/ui_language.py:28`.
- 재현 명령(개발 서버 실행 후):

```sh
curl -s -D - -H 'Accept-Language: en-US,ko;q=0.1' http://127.0.0.1:5099/privacy
curl -s -D - -H 'Accept-Language: ko-KR,en;q=0.1' http://127.0.0.1:5099/terms
```

- 기대: 첫 요청은 영어, 둘째는 한국어. 구현은 지역 태그를 지원한다고 명시하고 ko/en 본문을 제공한다.
- 실제: 첫 요청은 `Content-Language: ko`, 둘째는 `en`이고 HTML 언어도 동일하게 뒤바뀐다. `resolve_ui_language(None, header)` 및 Flask test client로 직접 재현했다.
- 원인: 설치된 Werkzeug `LanguageAccept.best_match`는 완전 일치를 먼저 반환하고 완전 일치가 없을 때만 주 언어로 fallback한다. 따라서 지원 언어의 낮은 q값 완전 일치가 높은 q값 지역 태그보다 먼저 선택된다. 기존 테스트에는 지역 태그와 반대 언어의 낮은 q값을 조합한 사례가 없다. `?lang=`으로 우회 가능하다.

### D-09-3 — MINOR: 문서 외곽 폭과 모바일 패딩이 명시된 디자인 규칙을 벗어남

- 위치: `web/static/legal.css:20`.
- 재현 입력: 브라우저 viewport를 768px로 설정하고 네 법적 문서 URL 중 하나를 열어 stylesheet 로드를 기다린 뒤 다음 값을 읽는다.

```js
document.querySelector('.doc').getBoundingClientRect().width
getComputedStyle(document.querySelector('.doc')).boxSizing
```

- 기대: OVERRIDES §10 및 SCREENS 웹 절의 중앙 문서 최대 폭 480px.
- 실제: `528`, `content-box`. 내용 최대 폭 480px에 좌우 패딩 24px씩이 더해진다. ko/en × 두 페이지 × light/dark에서 모두 확인했다.
- 추가 재현: viewport 375px에서 computed padding은 24px이며 OVERRIDES §4의 모바일 패딩 16px와 다르다. 실제 전체 폭은 375px로 가로 넘침은 없었다.
- 영향: 읽기 기능은 유지되지만 필수 디자인 수치와 구현 증거의 “최대 480px·다르게 한 것 없음” 주장이 맞지 않는다. 취향에 따른 레이아웃 제안이 아니다.

## 보안·범위·테스트 품질 및 참고

- 새 라우트는 공개 GET 렌더만 수행한다. 계정 변경·삭제·DB 쓰기가 없으므로 새로운 CSRF 변경 경로는 없다. 사용자 `lang` 입력은 ko/en 허용 목록으로 제한되고 템플릿 경로로 그대로 들어가지 않는다. 인증 우회·입력 삽입·데이터 손상 변경은 발견하지 못했다.
- 변경 파일에서 운영 시크릿·실제 사용자 토큰 노출은 발견하지 못했다. 구현 증거의 접속 예시는 `.env.example`과 같은 로컬 개발용 자격 정보이며 운영자 메일은 의도된 공개 연락처다.
- 공용 파일의 다른 티켓 번호 절·행은 수정하지 않았다. `.env.example`, `docs/RELEASE.md`, `.scratch/` 변경 없음. 메인 페이지 스타일 변경 없음.
- `/account/delete`의 미구현은 티켓 14 소유이므로 이 티켓 결함으로 세지 않는다.
- 테스트는 실제 Jinja 응답을 검증하므로 전체가 항상 통과하는 가짜 테스트는 아니다. 다만 `test_privacy_states_backup_retention`의 단순 `"14"` 검사는 “under 14” 아동 문구만으로도 통과하고, 토큰 테스트는 OVERRIDES 파일 자체가 아니라 복사된 기대값을 비교한다. 현재 본문·토큰 값은 직접 대조했으며 이 검증 강도 한계는 별도 출시 차단 결함으로 중복 집계하지 않는다.
- 취향·스타일 제안 없음. 결함 집계: BLOCKER 0, MAJOR 1, MINOR 2. MAJOR 수정 후 재검토가 필요하다.

판정: FAIL

## 라운드 2

검토 대상 HEAD: `eb2c8f4`, 로컬 main 및 merge-base: `8115301`.
`git diff main...HEAD` 전체와 `git log main..HEAD --oneline`의 10개 커밋을 검토했다.
티켓 09, 스펙 §A.15·§A.16·US45·미정 9, 국외 이전 안내와 관계된 §B.21·§B.24·§C.30,
CONTEXT, SCREENS 웹 절, MASTER와 우선 규칙 OVERRIDES를 대조했다.
코디네이터의 추가 범위인 연락처 설정값 및 사업자 정보 5개도 포함했다.

### 체크박스별 판정

| 티켓 체크박스 | 충족 여부 | 직접 확인한 근거 |
|---|---|---|
| 공용 토큰 CSS, 라이트/다크, 그림자 없음, Pretendard, 메인 스타일 유지 | 충족 | `tokens.css`의 색·간격·폰트 값을 OVERRIDES와 대조했다. `tile-empty`는 muted 참조이며 다크 재정의도 있다. 기존 메인 `style.css`·`index.html` 변경 없음. 실제 브라우저의 문서 폭·패딩은 D-09-3 재검증 참조. |
| Jinja ko/en 개인정보처리방침 및 필수 공시 | 충족 | 두 페이지 × 두 언어가 200 및 정확한 Content-Language로 렌더된다. 수집 항목 6개, 보유 기간, 업체 5개, 국외 이전, 아동, 삭제 링크와 연락처를 본문에서 대조했다. 게스트 상태와 광고·분석·오류 전송을 구분하며 D-09-1은 수정됐다. |
| 구독 자동 갱신·스토어 해지·EULA 선택 자리 | 충족 | ko/en 모두 자동 갱신, 스토어 해지, 계정 삭제로 구독이 해지되지 않는다는 설명, Apple 표준 EULA 링크 및 커스텀 선택 자리가 있다. 미정 9의 최종 결정은 별도 사람 작업이다. |
| pytest 렌더 테스트·두 페이지 detect 0건 | 충족 | 실제 Jinja 응답을 검사하는 렌더 테스트와 독립 test client 검증을 실행했다. 공용 CSS를 적용한 ko/en × 두 페이지 detect는 모두 0건이다. 실행 결과·한계는 아래 검증 절 참조. |
| README 경로·갱신 책임·설계 판단 | 충족 | 문서 경로·시행일·갱신 책임과 트리거, 법적 페이지에서 토큰을 먼저 도입하는 `### 09.`가 있다. 내용 요건은 충족하지만 공통 추가 위치 규칙은 D-09-4 참조. |

추가 사용자 결정도 충족한다. `app/config.py:92`의 연락처는 환경 설정값으로 읽고 빈 문자열이면
기본 연락처를 사용한다. 사업자 정보 5개는 기본값이 빈 문자열이며 `app/web.py:70`에서
공백을 제거한 뒤 값이 있는 항목만 공통 레이아웃(`web/templates/legal/_layout.html:68`)에 전달한다.
실제 test client로 연락처 변경, 일부 사업자 값만 설정, 공백 항목 생략, HTML 특수문자
이스케이프를 ko/en × 두 페이지에서 확인했다. 운영 Compose의 `env_file`로 이 설정들이
앱에 전달되는 구조도 읽어서 확인했으며 운영 접속은 하지 않았다.

### 이전 결함 재판정

| ID | 기존 심각도 | 판정 | 위치 및 동일 입력 재검증 |
|---|---|---|---|
| D-09-1 | MAJOR | FIXED | `web/templates/legal/privacy.ko.html:111`, `privacy.en.html:118`. 두 언어 개인정보처리방침 4절을 읽으면 계정 미연결로 막을 수 있는 로그인 정보와 게스트에게도 발생하는 광고·분석·오류 전송을 구분한다. 게스트 플레이를 전체 국외 이전 거부 방법으로 안내하던 문구가 제거됐고 기능별 거부·제한을 명시한다. |
| D-09-2 | MINOR | FIXED | `app/utils/ui_language.py:46`. 실제 test client로 두 경로에 `Accept-Language: en-US,ko;q=0.1` → `en`, `ko-KR,en;q=0.1` → `ko`를 확인했다. 지역 태그의 주 언어를 q 순서로 선택하므로 이전의 역전이 없다. |
| D-09-3 | MINOR | FIXED | `web/static/legal.css:22`, `:31`. 실제 Chrome에서 네 문서 × 375/480/481/768px를 측정했다. 외곽 폭은 각각 375/480/480/480px, 좌우 패딩은 16/16/24/24px, 가로 넘침은 전부 false다. 라이트·다크 각 16건 모두 통과하여 이전 528px·모바일 24px 문제가 해소됐다. |

REPEAT 0건. 위 FIXED 결함은 현재 결함 수에 포함하지 않는다.

### 새 결함 목록

#### D-09-4 — MINOR: README 설계 판단을 섹션 끝에 덧붙이지 않음

- 위치: `README.md:895`.
- 근거: 티켓 공통 규칙은 README 설계 판단에 자기 번호 소제목을 **섹션 끝에 덧붙이도록** 명시한다.
- 재현 명령: `git diff main...HEAD -- README.md` 및 `rg -n '^### (09|04)\.|^## 부하' README.md`.
- 기대: 기존 설계 판단 마지막 `### 04. 제출 일관성` 뒤, 다음 최상위 `## 부하 테스트 요약` 전에 `### 09.`가 추가된다.
- 실제: 895행의 `### 09.`가 기존 `### 04.` 소제목 3개(924·943·962행) 앞에 삽입된다. 로컬 main에도 이 04 절들이 이미 있으므로 현재 main 대비 섹션 끝 추가가 아니다.
- 영향: 병렬 티켓의 공용 파일 추가 위치 약속을 벗어난다. 타 티켓 본문을 덮어쓰거나 런타임 동작을 손상시키지는 않았으므로 MINOR이며, 문체·취향 제안이 아니다. 자기 09 절만 설계 판단 끝으로 옮기면 된다.

### 직접 실행한 검증

접속값은 구현 증거의 로컬 테스트 설정을 사용했으며 인증값은 이 리뷰에 기록하지 않는다.
`TEST_DATABASE_URL`은 기존 `chosung_daily_test_t09`, `TEST_REDIS_URL`은 로컬 Redis DB 11,
`TEST_MIGRATION_DATABASE_URL`은 기존 `chosung_daily_test_t09_migrations`로 지정했다.
새 DB를 만들지 않았고 기본 테스트 DB로 전환하지 않았다.

| 명령/검사 | 결과 |
|---|---|
| 위 테스트 환경변수를 지정한 `uv run pytest -q` | `536 passed in 202.24s (0:03:22)`, exit 0. 접속 오류·간헐 실패가 없어 재실행하지 않았다. |
| `uv run ruff check .` | `All checks passed!`, exit 0. |
| `FLASK_ENV=testing uv run flask --app wsgi db heads` | `ff06a1bf5afc (head)` 한 줄. 이 티켓 자체의 마이그레이션 변경은 없다. |
| `git diff main...HEAD --check` | exit 0. |
| Flask test client, 두 문서 × ko/en | 4건 모두 200, Content-Language 일치. D-09-2의 헤더 입력 4건도 통과. |
| 추가 설정값 직접 렌더 | 두 문서 × ko/en에서 연락처 교체, 일부 항목·공백 항목 생략, 사업자 값의 `<script>` 문자열 이스케이프 통과. |
| Chrome headless, 네 문서 × 네 폭 × light/dark | 32건 폭·패딩·넘침 검사 통과. 배경/전경은 light `rgb(250,250,249)` / `rgb(15,23,42)`, dark `rgb(20,26,38)` / `rgb(241,245,249)`. |
| `impeccable detect` 기본 문서 4개 및 사업자 정보가 채워진 문서 4개 | 각각 출력 없음, exit 0. 대조군 `design/archive/v2_softdark_home.html`은 7건, exit 2로 탐지기 동작 확인. |

검증용 임시 파일은 `/tmp/t09-review-r2/`에만 작성했다. Flask test client의 실제 렌더 HTML에서
외부 링크 태그를 제거하고 실제 `tokens.css`·`legal.css`를 원문 그대로 inline했다.
`/Users/saem/.impeccable/bin/0.1.14/impeccable detect`에 `privacy-ko.html`, `privacy-en.html`,
`terms-ko.html`, `terms-en.html`을 전달했다(사업자 값 설정본은 같은 이름 앞에 `filled-`).
브라우저는 폭 고정 iframe에서 `getBoundingClientRect().width`, computed padding,
문서 scrollWidth 및 색상을 읽었다. 외부 리소스 요청은 CSP와 호스트 해석 차단으로 제한했다.
따라서 CDN 글꼴 실제 다운로드나 외부 약관 링크 도착지는 이번 검증 범위에 포함하지 않는다.
프로덕션·NAS·실제 외부 서비스에 접근하지 않았다.

### 보안·범위·테스트 품질 및 참고

- 공개 GET 렌더 경로만 추가되어 인증 변경·CSRF 상태 변경·DB 쓰기는 없다. `lang`은 허용된 ko/en 값으로만 템플릿 이름에 들어가고 사업자 정보와 연락처는 Jinja 자동 이스케이프를 거친다. 새 인증 우회·입력 삽입·데이터 손상 결함을 발견하지 못했다.
- 추가 환경 설정·운영자 블록은 코디네이터가 확인한 사용자 결정 범위다. 사업자 실제 값이 비어 있는 것은 의도이며 결함이 아니다. `.env.example`은 자기 `[09]` 블록, `docs/RELEASE.md`는 자기 `### 09.`를 끝에 추가했고 다른 티켓 내용은 수정하지 않았다. README의 추가 위치만 D-09-4에 기록했다.
- `.scratch/`·기존 메인 스타일 변경 없음. 운영 시크릿 노출은 발견하지 못했다. 구현 증거의 DB 접속 예시는 로컬 개발용 값이며 이 리뷰에 복사하지 않았다. 공개 연락처와 테스트용 사업자 샘플은 운영 인증정보가 아니다.
- 테스트는 Jinja 응답을 mock하지 않고 실제 렌더를 검사한다. 추가 언어 회귀 테스트는 문제였던 헤더 조합을 직접 사용하고, 국외 이전 검사는 4절로 범위를 좁혔다. CSS 테스트는 선언 문자열 수준이므로 위 브라우저 측정으로 보완했다.
- 이전 라운드에 적힌 테스트 한계는 남아 있다: 백업 보유 기간의 단순 `"14"` 검사는 아동 문구로도 통과할 수 있고, 토큰 테스트는 OVERRIDES 파일을 읽지 않고 복사한 기대값과 비교한다. 현재 본문과 토큰은 직접 대조했으며 기존 참고사항을 신규 결함으로 중복 집계하지 않는다. README의 “OVERRIDES를 고치면 테스트가 먼저 깨진다”는 설명도 이 테스트 한계 아래 해석해야 한다.
- `/account/delete` 구현과 EULA 최종 선택, 출시 전 실제 사업자 값 입력은 각각 후속 티켓·사람 작업이다. 이 리뷰는 제품 사양과 구현의 일치를 확인했으며 법률 적합성을 별도로 인증하지 않는다.
- 취향·스타일 제안 없음. 현재 결함: BLOCKER 0, MAJOR 0, MINOR 1(D-09-4). 기존 3건은 모두 FIXED, REPEAT 0건이다.

판정: PASS
