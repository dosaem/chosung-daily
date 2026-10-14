# 티켓 18 최종 구현 리뷰 — 라운드 1

- 기준: 로컬 `main` (`055b56c`) → `HEAD` (`a14e6af`), `git diff main...HEAD` 및 `git log main..HEAD`의 구현·문서 커밋 2개. `origin/main`은 사용하지 않았다.
- 읽은 기준: 티켓 18, 스펙 §A.16·US 8·41~45·디자인 부족 항목, SCREENS 웹 절, 디자인 시스템 MASTER와 우선하는 OVERRIDES, `review/impl-evidence-18.md`.
- 결론: **BLOCKER 0 / MAJOR 2 / MINOR 1**. 앱 코드·테스트·설정·`.scratch/`는 수정하지 않았다.

## 체크박스별 충족 여부

| 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 09 토큰 CSS, `primary-button`·`tile-empty`·`tile-correct`, 그림자 없음, 모든 폭 중앙 최대 480px, 자동 다크모드 | 미충족 | 토큰 클래스·색상 전환·480px 상한·그림자 제거는 확인했다. 다만 320px 영어 화면의 머리말이 카드 밖으로 넘친다(D-18-3). |
| 상태 4종, 네트워크 오류 재시도, 오프라인 배너·입력 잠금, 퍼즐 없음 카운트다운, 색 외 피드백 | 미충족 | 퍼즐 조회 실패 경로와 카운트다운·체크/취소선은 구현됐다. 최초 게스트 발급 실패는 스켈레톤에 고착(D-18-1), 제출 실패는 잠긴 입력을 복구할 재시도가 없다(D-18-2). |
| 상단 섹션 토글, 백업/불러오기 패널 유지, pytest 렌더 | 충족 | 템플릿의 세 패널·버튼, `showSection`, 기존 백업/복원 이벤트를 대조했다. `tests/test_web_design.py`와 실제 번들을 실행하는 `tests/js/web_states_and_sections.mjs`가 해당 계약을 검사한다. |
| 결과 앱 CTA 두 배지·설정 기반 Smart App Banner·빈 값 미렌더·공유 URL | 충족 | Flask 클라이언트로 ko/en 각각 설정 없음→배지 0·메타 없음, 설정 있음→배지 2·메타 있음·HTTP 200을 재확인했다. CTA는 결과 영역에 있고, `buildShareText`의 마지막 줄은 지정한 `?utm_source=share` URL이다. 배지는 현재 텍스트형 링크다(참고 참조). |
| 푸터 법적 링크 3개 및 16의 사업자 정보 조각 | 충족 | ko/en 응답에 세 경로와 `business-info`가 있다. 기존 `legal/_business_info.html`을 그대로 include하고 `_business_info` 컨텍스트를 재사용한다. 조각 파일 자체에는 변경이 없다. |
| impeccable detect 0건 및 라이트/다크 헤드리스 스크린샷 | 충족 | 기존 PNG 두 장을 직접 열어 확인했다. 별도로 로컬 렌더 스냅샷 ko/en × light/dark 4개와 320px en 두 개를 실제 detect로 실행해 모두 exit 0·탐지 0건을 확인했다. 재검증 범위·폰트 제약은 아래에 명시했다. |
| pytest 렌더 테스트와 수동 체크리스트(삭제 후 새 게스트 포함) 갱신 | 충족 | 새 렌더/JS 테스트와 README 수동 체크 12~20행을 확인했다. 17행에 삭제 후 새 게스트 발급이 있다. 테스트가 초기 진입·제출 오류를 놓치는 한계는 D-18-1·2에 기록했다. |

## 직접 실행한 검증

- 전체 테스트: `uv run pytest -q` → **1294 passed in 642.21s (0:10:42), exit 0**. 이번 실행은 실패·간헐 오류 없이 완료되어 전체 스위트는 재실행하지 않았다. 이후 코디네이터의 연결 수 조사 요청으로 아래 웹 테스트 93건만 추가 실행했다.
- 테스트 자원: 기존 `chosung_daily_test_t18`, Redis DB 6을 `TEST_DATABASE_URL`·`TEST_REDIS_URL`로 지정했다. 마이그레이션 테스트는 구현 증거에 기재된 기존 `chosung_daily_test_t18_migrations`를 `TEST_MIGRATION_DATABASE_URL`로 지정했다. 새 DB를 생성하지 않았고 기본 DB로 대체하지 않았다. 접속 비밀번호는 이 문서에 기록하지 않는다.
- 명령: 위 테스트 환경변수를 지정한 `uv run pytest -q`; `uv run ruff check .` → **All checks passed!**; `git diff --check main...HEAD` → exit 0.
- 이 티켓은 마이그레이션 파일을 변경하지 않았다(`git diff --name-only main...HEAD -- migrations`가 비어 있음).
- 실제 Flask 렌더: ko/en × 설정 있음/없음 4개 응답 모두 200, 법적 링크·사업자 정보 조각 있음. 설정 있음은 배지 2개와 Smart App Banner 메타, 없음은 각각 0개·미렌더.
- 실제 Chrome CDP에서 라이트 배경/본문/보조 텍스트는 `rgb(250,250,249)` / `rgb(15,23,42)` / `rgb(87,83,78)`, 다크는 `rgb(20,26,38)` / `rgb(241,245,249)` / `rgb(148,163,184)`로 바뀌었다. 보조 텍스트 대비를 별도 계산하면 라이트 7.30:1·다크 6.79:1, 다크 입력 placeholder는 6.07:1이다. 17의 일부만 다크가 되는 중간 상태는 해소됐다.
- detect 실행 파일은 로컬 `/Users/saem/.impeccable/bin/0.1.14/impeccable`이다. `detect http://127.0.0.1:9420/ko-light http://127.0.0.1:9420/ko-dark http://127.0.0.1:9420/en-light http://127.0.0.1:9420/en-dark`와 `detect --viewport 320x844 http://127.0.0.1:9420/en-light http://127.0.0.1:9420/en-dark` 모두 exit 0·출력 없음이었다.
- 위 URL은 테스트 앱으로 렌더한 HTML·현재 CSS를 메모리에만 보관한 로컬 HTTP 서버다. 구현의 `snapshot()`을 재사용해 숨은 상태·샘플 피드백 타일을 펼쳤다. 외부 서비스 호출을 막기 위해 CDN 링크 및 실행 JS를 제거하고 CSS를 인라인했다. 따라서 실제 CDN 폰트 다운로드나 Safari 네이티브 배너 표시는 검증하지 않았으며, 폰트는 선언된 시스템 fallback으로 렌더했다. DOM/색 탐지 0건이 초기화·복구 동작이나 모든 반응형 문제까지 보장하지는 않는다.

## 결함

### D-18-1 — 최초 게스트 발급 실패가 새 오류 UI 전체를 건너뛴다

- **심각도: MAJOR**
- **위치:** `web/static/app.js:1021` (관련: `:171`, `:1024`), `tests/js/web_states_and_sections.mjs:76`.
- **재현 입력:** 저장된 게스트가 없는 첫 방문에서 HTML/JS는 로드되지만 `POST /api/v1/guests`만 연결 오류로 실패하게 한다. `navigator.onLine=false` 상태 또는 onLine은 true인 일시적인 fetch 실패 모두 해당한다.
- **기대:** 스켈레톤을 종료하고 오류 카드·재시도를 보여준다. 오프라인이면 상단 배너가 표시되고, 복구 후 게스트 발급부터 이어서 진행한다.
- **실제:** `ensureToken()` 예외가 `init()`을 종료시킨다. 새로 추가한 `bindEvents()`·`renderOffline()`보다 앞에서 중단되므로 **스켈레톤 표시=true, 배너 표시=false, 재시도 카드 표시=false, 재시도 이벤트 수=0**이다. 온라인 이벤트도 등록되지 않아 연결이 돌아와도 그대로다. HTTP 5xx로 발급이 실패하는 경우도 인라인 재시도가 없다.
- **직접 실행 근거:** 기존 harness로 `loadApp`, `navigator.onLine=false`, `setFetch(async () => { throw new TypeError('Failed to fetch'); })`, `await app.run('init()')`를 실행했다. `Failed to fetch` rejection과 위 네 값을 확인했다. 실제 번들의 초기화를 실행했으며 애플리케이션 함수는 mock하지 않았다.
- **테스트 누락:** 신규 상태 시나리오의 `started()`는 이미 발급된 게스트 상태를 주입하고 `bindEvents()`를 직접 호출한다. `test_navigator_online_alone_raises_the_banner_before_any_request`도 `init()` 대신 `renderOffline()`을 직접 부르므로 실제 초기 진입 순서를 검증하지 않는다. 티켓의 상태 4종·US 8 요구가 이 경로에서는 충족되지 않는다.

### D-18-2 — 제출 요청 실패 뒤 입력을 잠그지만 재시도 경로를 표시하지 않는다

- **심각도: MAJOR**
- **위치:** `web/static/app.js:663` (관련: `:405`, `:903`).
- **재현 입력:** 정상 퍼즐에서 답을 입력한 뒤, `navigator.onLine=true`를 유지하면서 `POST /api/v1/puzzles/today/guesses`의 fetch 한 번만 네트워크 오류로 reject한다. 이후 서버 연결은 회복하되 브라우저의 offline/online 이벤트는 발생시키지 않는다(일시적 DNS·연결 실패 상황).
- **기대:** 인라인 재시도를 제공해 서버의 최신 퍼즐/시도 이력을 확인하고 입력을 복구할 수 있어야 한다. fetch 실패만으로 서버의 시도 소비 여부를 단정할 수 없으므로 복구 과정은 서버 상태와 다시 맞아야 한다.
- **실제:** `renderOffline(true)`로 입력·제출이 비활성화되고 안내만 `#message`에 표시된다. 유일한 재시도 버튼의 부모 `#puzzle-state`는 계속 hidden이다. onLine이 계속 true였으므로 연결이 복구되어도 `online` 이벤트가 오지 않으며, 사용자는 같은 퍼즐에서 다시 제출하거나 안내의 “다시 시도”를 수행할 수 없다. 페이지 새로고침 또는 다른 언어로의 전환이 우회책이다.
- **직접 실행 근거:** 실제 사전을 읽어 기존 harness에서 `bindEvents()` → 진행 중 퍼즐 `applyPuzzle()` → 답 입력 → fetch reject → `handleSubmit()`을 실행했다. 결과: `online=true`, `disabled=true`, `bannerVisible=true`, `retryVisible=false`, 안내는 “연결이 불안정해요. 다시 시도해주세요.”였다.
- **테스트 누락:** 새 네트워크 복구 시나리오는 `reloadPuzzle()` 실패만 유발한다. 제출 실패 분기는 실행하지 않으므로 위 고착 상태를 잡지 못한다. 조회용 오류 카드가 있다는 사실만으로 제출 오류의 재시도 요구까지 검증된 것은 아니다.

### D-18-3 — 320px 영어 화면의 머리말이 카드와 뷰포트를 벗어난다

- **심각도: MINOR**
- **위치:** `web/static/style.css:82` (관련: `:93`, `:103`).
- **재현 입력:** 320×844 뷰포트에서 `/?lang=en`을 렌더하고 정상 초기 통계 `0-day streak · best 0 · 0 solved`를 표시한다. CDN을 사용할 수 없는 상황의 선언된 시스템 fallback 폰트로 재현했다. 보드는 비워 머리말 단독의 넘침을 확인했다.
- **기대:** OVERRIDES §10 및 티켓의 모든 폭 중앙 정렬 조건대로 320px 카드 안에 제목·스트릭이 배치되어 가로 스크롤이 생기지 않아야 한다.
- **실제:** Chrome CDP 측정 결과 `innerWidth=320`, 카드 오른쪽 끝 `320`, 스트릭 오른쪽 끝 `369.09375`, 문서 `scrollWidth=369`였다. 제목의 최소 단어 폭과 줄바꿈 불가 스트릭을 한 flex 행에 고정해 내용이 약 49px 넘친다. 1000px 스크린샷만으로는 이 상태가 드러나지 않는다.
- **직접 실행 근거:** 현재 템플릿을 실제 Flask로 렌더하고 현재 두 CSS 파일을 Chrome에 적용했다. CDP `Emulation.setDeviceMetricsOverride`로 320px을 지정한 뒤 `document.documentElement.scrollWidth`와 각 요소의 `getBoundingClientRect()`를 측정했다. 외부 폰트 다운로드는 하지 않았다.

## 추가 확인 — MySQL 유휴 연결 증가

코디네이터가 전체 테스트 실행 중 t18 DB의 Sleep 연결 89개를 관측해 신규 테스트의 누수 여부를 요청했다. 전체 pytest 프로세스가 끝난 직후 직접 `information_schema.PROCESSLIST`를 조회한 결과 t18 DB에는 관측용 Query 연결 1개만 있었고 Sleep은 0개였다.

같은 전용 DB·Redis를 사용해 기존 웹 테스트(주로 티켓 17), 신규 디자인 테스트, JS 테스트를 한 Python 프로세스에서 차례로 실행했다. 파일은 만들지 않고 인메모리 pytest 플러그인의 teardown 후 hook에서 매 테스트의 t18 Sleep 수를 읽었다. 관측 엔진은 `NullPool`로 만들어 측정 자체가 유휴 연결을 남기지 않게 했으며, 각 모듈 시작 전에 `gc.collect()`로 조건을 맞췄다.

| 대상 | 테스트 결과 | 시작 Sleep | 실행 중 최대 Sleep | pytest 반환 직후 | 추가 GC 후 |
|---|---|---:|---:|---:|---:|
| 기존 `tests/test_web.py` | 28 passed in 17.02s | 0 | 17 | 0 | 0 |
| 신규 `tests/test_web_design.py` | 26 passed in 12.27s | 0 | 17 | 0 | 0 |
| `tests/test_web_js.py` | 39 passed in 0.68s | 0 | 0 | 0 | 0 |

`tests/conftest.py:23`의 function-scope app fixture는 앱마다 엔진을 생성하고 teardown에서 `db.session.remove()`·`db.drop_all()`만 호출하며 명시적인 `engine.dispose()`는 없다. 이 fixture와 앱 팩토리·extensions는 `main...HEAD` diff가 비어 있어 이 티켓이 바꾸지 않았다. 신규 디자인 테스트도 별도 앱/엔진을 생성하거나 보관하는 fixture 없이 같은 기존 `app`/`client`를 사용한다. 새 fixture는 CSS 문자열과 HTML 문자열만 반환하고 JS 테스트는 DB fixture를 사용하지 않는다.

**판단:** 기존 테스트에서도 같은 유휴 연결 누적·실행 종료 시 해제가 관측되어, 티켓 18에서 새로 생긴 누수라는 근거는 없다. 89개라는 전체 스위트 최대치를 이번 좁은 재실행에서 재현했다고 주장하지 않는다. 병렬 테스트가 한도에 접근할 위험은 공통 fixture의 연결 풀 수명 관리 문제로 별도 정리할 가치가 있지만, 요청된 “이 티켓에서 생긴 경우” 조건에 해당하지 않아 새 MAJOR로 등록하지 않는다.

## 범위·보안·공유 파일 검토

- 변경된 템플릿은 Jinja 자동 이스케이프를 유지하고, 사용자 입력을 새 `innerHTML`로 삽입하는 경로는 추가하지 않았다. 인증·CSRF 처리와 법적 정보 공개 범위를 바꾸는 변경은 발견하지 못했다. 프로덕션·외부 서비스에는 접근하지 않았다.
- `fetchJson`의 본문 수신 후 세대 검사, `languageWanted` 쓰기 직렬화는 유지됐다. 스펙이 수용한 기존 D-17-6은 새 결함으로 재등록하지 않는다.
- README 설계 판단과 RELEASE의 추가 내용은 `### 18.` 아래에 있다. 수동 체크리스트 갱신은 티켓 자체의 요구이며, `.env.example`·API 표·스펙 미정 항목·타 티켓 사업자 정보 조각은 변경하지 않았다. 병렬 공유 파일 소유권 위반을 발견하지 못했다.
- 데이터 스키마/저장 경로 변경은 없다. 변경 파일에서 실제 운영 시크릿이 새로 노출된 증거는 발견하지 못했다. 구현 증거의 DB 접속 예시는 `.env.example`의 로컬 테스트 계정 형식이며 이 리뷰에 재기록하지 않았다.

## 참고

- CTA의 두 링크는 스토어 이름을 표시하는 텍스트형 배지이고, 공식 아트워크는 RELEASE 18에 후속 작업으로 적혀 있다. 티켓이 공식 이미지 형식을 명시하지 않았으므로 모양 선호를 결함으로 올리지 않았다.
- 타일의 글자 수별 크기·9글자 이상 줄바꿈 규칙은 구현 증거에서도 미적용을 밝힌 기존 레이아웃이다. 이 리뷰에서는 위 세 결함과 별개로, 긴 퍼즐의 디자인 적합성이 증명됐다고 보지 않는다.
- 수동 체크리스트의 갱신 여부는 확인했지만 실제 iOS Safari·스토어 등록·삭제 후 브라우저 왕복을 사람이 수행했다고 주장하지 않는다.

판정: FAIL

## 라운드 2

- 기준: 로컬 `main` (`055b56c`) → 구현 `HEAD` (`22a76f0`). `git log main..HEAD`의 4개 커밋과 `git diff main...HEAD`, 특히 라운드 1 이후 수정 커밋을 대조했다. `origin/main`은 사용하지 않았다.
- 티켓 18, 스펙 §A.16·US 8·41~45·디자인 부족 항목, SCREENS 웹 절, MASTER와 우선하는 OVERRIDES, 구현 증거와 라운드 1 리뷰를 읽었다. 구현 증거의 통과 주장을 그대로 채택하지 않고 아래 검증을 다시 실행했다.
- 기존 **D-18-1·2·3 모두 FIXED**, REPEAT 없음. 신규 **D-18-4 MAJOR 1건**. 현재 미해결 합계는 **BLOCKER 0 / MAJOR 1 / MINOR 0**이다.

### 체크박스별 충족 여부

| 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 09 토큰 CSS, 이름 유지, 그림자 없음, 중앙 최대 480px, 자동 다크모드 | 충족 | CSS가 공용 토큰을 사용하고 `.card` 최대 폭을 유지한다. Chrome에서 320px 영어 머리말의 `scrollWidth=320`, 카드 우측 320, 스트릭 우측 249.28125를 라이트·다크 모두 확인했다(D-18-3 FIXED). 배경은 각각 `rgb(250,250,249)`·`rgb(20,26,38)`로 전환된다. |
| 상태 4종·인라인 재시도·오프라인 배너/입력 잠금·퍼즐 없음 카운트다운·색 외 피드백 | 충족 | 실제 번들을 실행하는 JS 시나리오에서 첫 방문 발급 실패·5xx·온라인 복구·제출 실패 후 서버 이력 재동기화가 통과했다. 카운트다운과 체크/취소선도 유지된다(D-18-1·2 FIXED). |
| 상단 섹션 토글·백업/불러오기 패널 유지·pytest 렌더 | 미충족 | 세 패널의 토글과 배치·렌더 계약은 유지된다. 그러나 백업 복원 후 기존 토큰으로 초기화할 때 세션 동기화가 빠져 계정 기능의 동작이 바뀌었다(D-18-4). |
| 결과 앱 CTA 두 배지·설정 기반 Smart App Banner·빈 값 미렌더·공유 URL | 충족 | Flask 클라이언트 ko/en × 설정 있음/없음 4개 응답 모두 200. 설정 있음은 배지 2·메타 있음, 없음은 배지 0·메타 없음. 실제 JS 공유 결과의 마지막 줄 URL도 테스트로 확인했다. |
| 법적 링크 3개·16의 사업자 정보 조각 | 충족 | 위 네 응답 모두 법적 링크와 `business-info`가 있고 공통 조각·컨텍스트를 그대로 재사용한다. 링크의 존재와 별개로 삭제 대상의 세션 불일치는 D-18-4에 기록한다. |
| impeccable detect 0건·라이트/다크 스크린샷 기록 | 충족 | 기존 `home-light.png`·`home-dark.png`를 직접 열었다. 현재 템플릿/CSS로 만든 로컬 ko/en × light/dark 4개 스냅샷과 320px 영어 2개에 detect를 실제 실행해 모두 exit 0·탐지 0건이었다. |
| pytest 렌더 테스트·삭제 후 새 게스트 포함 수동 체크리스트 갱신 | 충족 | 렌더 테스트와 README 수동 체크 12~20행(17행 삭제 후 새 게스트)을 확인했다. 체크리스트가 갱신됐다는 판정이며, 기존 토큰의 세션 동기화까지 테스트됐다는 뜻은 아니다. |

### 이전 결함 재판정

| ID | 원 심각도 | 판정 | 현재 위치·재현 및 기대/실제 |
|---|---|---|---|
| D-18-1 | MAJOR | FIXED | `web/static/app.js:175`, `:1060`, `:1076`. 저장 토큰 없는 `init()`에서 게스트 발급 fetch reject/500 → 기대한 오류 카드·재시도와 오프라인 배너가 표시되고 스켈레톤이 종료된다. 버튼 재시도와 online 이벤트 모두 발급부터 재개해 정상 퍼즐로 돌아온다. |
| D-18-2 | MAJOR | FIXED | `web/static/app.js:687`, `:936`. `navigator.onLine=true`에서 제출 fetch만 reject → 기대한 인라인 재시도가 표시된다. 서버가 해당 시도를 소비한 응답으로 바꾼 뒤 재시도 → 시도 행 1개·남은 기회 4로 복원되고 입력이 활성화된다. |
| D-18-3 | MINOR | FIXED | `web/static/style.css:88`. 320×844, 영어 제목과 `0-day streak · best 0 · 0 solved`, 시스템 fallback 폰트 → 기대한 카드 안 줄바꿈이 발생한다. Chrome 실측 라이트·다크 모두 문서 폭 320으로 이전 369px 넘침이 재현되지 않는다. |

### 신규 결함

#### D-18-4 — 저장된 토큰으로 시작하면 세션 동기화가 생략되어 다른 계정을 삭제할 수 있다

- **심각도: MAJOR**
- **위치:** `web/static/app.js:178`~`:181`, `:203`~`:206`, `:1065` (관련: `:899`의 백업 복원, `app/web.py:136`·`:161`, `app/api/oauth.py:57`·`:65`).
- **원인:** 이전 `init()`은 `ensureToken()` 뒤에 항상 `syncSession()`을 호출했다. 수정본은 이 호출을 새 게스트 발급 성공 분기 안으로 옮겼다. localStorage 토큰이 있으면 그 위에서 바로 반환하므로 첫 방문을 제외한 초기화에서는 `/session/sync`가 호출되지 않는다. `handleOAuthLogin()`도 동기화 없이 이동한다.
- **재현 입력:** 게스트 A로 방문해 세션 쿠키를 만든 뒤, 기존 백업/불러오기 패널로 다른 게스트 B의 백업 코드를 복원한다. 복원은 localStorage를 B로 바꾸고 페이지를 새로고침한다. 그 뒤 푸터의 계정 삭제 페이지를 열고 확인한다. 또는 localStorage만 남고 세션 쿠키가 없는 브라우저에서 재방문한다.
- **기대:** 새로고침 후 B의 토큰으로 세션을 동기화해 플레이·계정 연결·삭제가 모두 B를 가리켜야 한다. 세션 쿠키만 없는 재방문도 현재 게스트로 삭제 페이지를 사용할 수 있어야 한다.
- **실제:** 저장된 토큰을 읽는 분기에서 세션 동기화가 0회다. 따라서 백업 복원 후 API는 B로 호출되지만 세션은 A로 남는다. 삭제 페이지는 세션의 A로 폼을 발급하고 같은 A를 삭제 대상으로 사용한다. 폼 대상 검사와 CSRF는 둘 다 A에 맞으므로 이 불일치를 막지 못한다. 쿠키가 없는 경우에는 기록이 있어도 삭제 안내 화면만 표시된다. OAuth 계정 전환 콜백 후에도 새 토큰과 기존 세션을 맞추지 못한다.
- **직접 실행 근거:** `tests/js/harness.mjs`의 `loadApp`으로 실제 번들을 읽고 실제 `UI_STRINGS['ko']`를 주입했다. fetch 경계만 기록용 대역으로 바꿔 `await app.run('init()')`을 실행했다. 대조군인 저장 토큰 없는 방문은 요청 순서가 `guests → session/sync → me/stats → puzzles/today`이고 **sync 1회**였다. 저장 토큰 있는 방문은 `me/stats → puzzles/today`뿐으로 **sync 0회**였다. `init`, `ensureToken`, `syncSession`은 mock하지 않았다. 삭제 영향은 실제 서버 코드의 세션 게스트 선택·폼 대상 검사와 대조했다.
- **실제 삭제까지 추가 확인:** 전체 pytest 종료 후 같은 전용 DB/Redis에서 임시 게스트 A/B를 발급했다. Flask 클라이언트로 A의 세션을 만든 뒤 loopback HTTP 브리지를 통해 실제 번들의 `init()` → `handleRestoreSubmit()` → 새 페이지의 `init()` 요청을 실제 Flask API로 보냈다. 출력은 `restoreReloads=1`, `uiUsesB=true`, `/session/sync` 요청 **0회**였다. 이어 실제 `/account/delete`에서 받은 CSRF 값을 그대로 제출한 결과 HTTP **302**, **A 존재=false / 복원한 B 존재=true**였다. 즉 화면이 B로 바뀐 뒤에도 실제로 A를 삭제했다. 이 재현에는 외부 인증이나 서비스 호출이 없고, 임시 테스트 데이터·테이블·Redis 상태는 종료 시 정리했다. 생성 토큰·CSRF 값은 출력하거나 문서에 기록하지 않았다.
- **재현 명령의 핵심:** `uv run python`에서 UI 사전을 JSON으로 전달해 `node --input-type=module -e`로 harness를 불러온다. `app.context.localStorage.setItem('chosung_token', 'dummy-restored-guest')`, 요청 URL을 수집하는 `app.setFetch(...)`, `await app.run('init()')` 후 `calls.filter(url => url.endsWith('/session/sync')).length`를 출력하면 기대 1 / 실제 0이다. dummy 값은 로컬 JS 대역에서만 사용한 비인증 문자열이다.
- **테스트 사각지대:** 새 첫 방문 회귀 테스트는 신규 발급 성공만 검증한다. 저장 토큰으로 시작하는 제출 시나리오는 `/session/sync` 호출을 확인하지 않는다. 서버의 삭제·OAuth 테스트는 fixture/테스트에서 동기화 요청을 직접 보내므로 프론트가 그 요청을 빠뜨린 회귀를 잡지 못한다.

### 직접 실행한 검증

- 위 전용 테스트 환경변수를 지정한 `uv run pytest -q` → **1301 passed in 926.05s (0:15:26)**, exit 0. 실패·간헐 오류가 없어 전체 스위트를 다시 실행하지 않았다. 구현 증거의 1301건과 수·통과 여부가 일치하며, `db.engine.dispose()` 추가 때문에 기존 테스트가 빠지거나 실패한 증거는 없다.
- 자원은 요청된 기존 `chosung_daily_test_t18`, Redis DB 6, 기존 `chosung_daily_test_t18_migrations`를 각각 `TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`로 지정했다. 새 DB를 만들지 않았고 기본 DB로 대체하지 않았다. 접속 정보 값은 이 문서에 쓰지 않는다.
- `uv run pytest --collect-only -q` → **1301 tests collected in 0.55s**. 기존 1294 대비 수정 커밋의 추가 7건(JS 6 + CSS 1)과 일치한다.
- `uv run pytest -q tests/test_web_js.py` → **45 passed in 0.56s**, exit 0. 기존 응답 본문 지연·세대 검사·언어 쓰기 직렬화 시나리오와 D-18-1·2 신규 시나리오가 포함된다.
- `uv run ruff check .` → **All checks passed!**, exit 0. `git diff --check main...HEAD` → exit 0. 마이그레이션 diff는 비어 있어 이 티켓에서 heads 확인이 요구되는 스키마 변경은 없다.
- 코디네이터가 확인 요청한 `tests/conftest.py:37`의 `db.engine.dispose()`는 기존 session 제거·테이블 정리 뒤 엔진 풀을 닫는다. 전체 테스트 실행 중 `NullPool` 관측 연결로 55초간 12회 조사한 t18 Sleep 수는 **최대 1 / 마지막 0**이었다. 이는 해당 표본 구간의 관측이며 전체 스위트 최고치라고 주장하지 않는다.
- 디자인 재검증 명령: `/Users/saem/.impeccable/bin/0.1.14/impeccable detect http://127.0.0.1:9422/ko-light http://127.0.0.1:9422/ko-dark http://127.0.0.1:9422/en-light http://127.0.0.1:9422/en-dark`; 같은 실행 파일의 `detect --viewport 320x844 http://127.0.0.1:9422/en-light http://127.0.0.1:9422/en-dark`. 모두 exit 0·출력 없음.
- 디자인 서버는 Flask로 렌더한 HTML과 현재 CSS를 메모리에서만 제공했다. 외부 링크·실행 스크립트를 제거하고 CSS를 인라인했으며, 숨은 상태는 기존 `snapshot()`으로 펼쳤다. 별도 헤더 페이지는 현재 템플릿 그대로 두고 Chrome CDP에서 스트릭 텍스트와 320px 뷰포트·시스템 색상 모드를 지정했다. CDN 폰트·Safari 네이티브 배너·실제 외부 스토어는 검증하지 않았다.

### 범위·보안·공유 파일·참고

- `fetchJson`의 본문 수신 후 세대 검사와 `languageWanted` 쓰기 직렬화 구조는 유지되고 해당 JS 회귀 테스트도 통과했다. 스펙이 이미 수용한 D-17-6은 새 결함으로 올리지 않는다. 계정 세션 동기화는 이들과 별개로 이번 수정에서 깨진 경로다.
- 인증·CSRF의 서버 검증 자체는 변경하지 않았지만, D-18-4 때문에 클라이언트와 서버의 계정 식별이 어긋나 데이터 손실 가능성이 생긴다. 새 사용자 입력을 HTML로 삽입하는 경로나 실제 운영 시크릿 추가 기록은 발견하지 못했다.
- README 설계 판단과 RELEASE는 자기 번호 `### 18.`에 추가됐다. 수동 체크리스트 수정은 티켓의 명시적 요구다. `.env.example`·API 표·스펙 미정 항목·법적 정보 조각은 변경하지 않았다. 공통 fixture 변경은 코디네이터가 별도로 승인하고 검증을 요청한 범위임을 수신 메시지로 확인했다.
- 공식 스토어 배지 아트워크·긴 퍼즐 타일의 기존 레이아웃·실기기 수동 검증의 제한은 라운드 1 참고와 같다. 취향이나 스타일 제안을 새 결함으로 올리지 않았다.
- 이 리뷰 작업은 애플리케이션·테스트·설정·`.scratch/`를 수정하지 않았으며 프로덕션·NAS·배포·외부 서비스 API에 접근하지 않았다.

판정: FAIL

## 라운드 3

- 기준: 로컬 `main` (`1afeffa`) → 구현 `HEAD` (`73604eb`). `git log main..HEAD`의 7개 커밋과 `git diff main...HEAD`를 확인했으며, 라운드 2 이후 수정 `c5082dc`를 별도로 대조했다. `origin/main`은 사용하지 않았다.
- 티켓 18, 스펙 §A.16·US 8·41~45·디자인 부족 항목, SCREENS 웹 절, MASTER와 우선하는 OVERRIDES, 구현 증거 및 이전 두 라운드를 읽었다. 사용자 지시에 따라 하위 에이전트 없이 직접 검토했다.
- 이전 **D-18-1·2·3·4 모두 FIXED**, REPEAT 없음. 신규 결함 없음. 미해결 **BLOCKER 0 / MAJOR 0 / MINOR 0**.

### 체크박스별 충족 여부

| 티켓 요구 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 09 토큰 CSS, 토큰 클래스 이름 유지, 그림자 없음, 중앙 최대 480px, 자동 다크모드 | 충족 | `style.css`의 공용 변수·폭·정렬·그림자 제거와 `tokens.css` 시스템 색상 분기를 대조했다. 디자인 계약 테스트 통과, 기존 라이트/다크 PNG 및 320px 영어 머리말 PNG를 직접 열었다. 라운드 2 이후 CSS·템플릿 diff 없음. |
| 상태 4종·인라인 재시도·오프라인 배너·퍼즐 없음 카운트다운·색 외 피드백 | 충족 | 실제 번들의 상태 시나리오가 통과했다. 첫 발급 실패/500/online 복구, 제출 실패 후 서버 이력 복원, 카운트다운과 섹션 전환을 포함한다. 체크 아이콘·굵기와 오답 취소선도 유지된다. |
| 상단 섹션 토글·백업/불러오기 패널 유지·pytest 렌더 | 충족 | 세 패널의 렌더·토글 및 실제 복원 클릭 핸들러 테스트 통과. 복원 후 새 로드에서 B 토큰으로 세션 동기화 요청 1회와 화면 API의 토큰 일치를 검증한다(D-18-4 FIXED). |
| 결과 앱 CTA 두 배지·설정 기반 Smart App Banner·빈 값 미렌더·공유 URL | 충족 | Flask 렌더 테스트에서 설정 있음/없음·플랫폼별 독립 배지·결과 영역 위치를 확인했다. 템플릿은 08 설정값을 사용하며 JS 공유 테스트가 지정된 `https://chosung.dosaem.com/?utm_source=share`를 검증한다. |
| 법적 링크 3개·16의 사업자 정보 조각 | 충족 | 렌더 테스트 통과. `/privacy`·`/terms`·`/account/delete`와 `legal/_business_info.html` include 및 `_business_info` 재사용을 대조했다. 해당 조각이나 공개 항목에 변경 없음. |
| impeccable detect 0건·라이트/다크 스크린샷 기록 | 충족 | 현재 템플릿/CSS를 렌더한 로컬 메모리 스냅샷 ko/en × light/dark 4개 및 320px en 2개를 직접 detect 실행하여 모두 exit 0·탐지 0건. 기존 `home-light.png`·`home-dark.png`를 직접 확인했다. |
| pytest 렌더 테스트·삭제 후 새 게스트 포함 수동 체크리스트 갱신 | 충족 | 웹 렌더/JS 및 계정 삭제 테스트 총 130건 통과. README 수동 체크 12~20행과 17행의 삭제 후 새 게스트 발급 항목 확인. 체크리스트 갱신을 검증했으며 실기기 수동 수행을 주장하지 않는다. |

### 이전 결함 재판정

| ID | 원 심각도 | 판정 | 현재 파일:라인·재현 입력 → 기대와 실제 |
|---|---|---|---|
| D-18-1 | MAJOR | FIXED | `web/static/app.js:185`, `:1108`. 저장 토큰 없는 `init()`에서 게스트 발급 fetch reject/500 → 기대한 오류 카드·재시도 표시 및 스켈레톤 종료. 실제 초기화/버튼/online 핸들러를 실행하는 회귀 테스트가 통과했고, 발급 성공 후 퍼즐로 복구한다. |
| D-18-2 | MAJOR | FIXED | `web/static/app.js:717`, `:968`. onLine=true에서 제출 fetch reject → 기대한 인라인 재시도가 표시된다. 서버가 시도 1회를 소비한 상태로 응답한 뒤 재시도 → 실제 시도 행 1개·남은 기회 4·입력 활성으로 복구하는 테스트 통과. |
| D-18-3 | MINOR | FIXED | `web/static/style.css:88`. 320px 영어 제목/스트릭 → 제목과 스트릭이 카드 안에서 줄바꿈해야 한다. `flex-wrap: wrap` 유지 및 회귀 테스트 통과, 기존 320px PNG에서 줄바꿈 확인. 라운드 2 실측 이후 CSS·템플릿이 동일하며 이번 320px detect도 0건이다. 이번에는 scrollWidth 수치를 새로 측정하지 않았다. |
| D-18-4 | MAJOR | FIXED | `web/static/app.js:185`, `:226`, `:943`. 저장 토큰 시작·백업 복원 후 새 로드·OAuth 콜백 → 기대한 현재 토큰의 `/session/sync` 1회 호출. 실제 번들 `init()`과 복원 클릭 핸들러 테스트에서 모두 1회이며 `/me/stats` Authorization과 일치한다. 첫 발급·삭제 후 새 발급 대조군도 통과. 오프라인 저장 토큰 진입에서는 rejection 없이 미동기화 상태를 유지하고 online에서 같은 토큰으로 재시도한다. |

### 신규 결함

없음. 위 FIXED는 이전에 명시한 재현 경로가 해소됐다는 판정이다.

### 직접 실행한 검증

- 요청된 기존 `chosung_daily_test_t18`와 Redis DB 6을 각각 `TEST_DATABASE_URL`·`TEST_REDIS_URL`로 지정했다. 연결 성공으로 기본 테스트 DB 폴백이나 새 DB 생성은 없었다. 접속 비밀번호·토큰은 기록하지 않는다.
- `uv run pytest -q tests/test_web.py tests/test_web_design.py tests/test_web_js.py tests/test_account_delete_page.py` → **130 passed in 48.63s**, exit 0. 간헐 실패나 경합이 없어 재실행하지 않았다. 프론트 전체 웹 회귀와 세션 전환 후 삭제 대상을 검사하는 서버 테스트를 포함한다.
- `uv run ruff check .` → **All checks passed!**, exit 0.
- `git diff --check main...HEAD` → exit 0. `git diff --name-only main...HEAD -- migrations` → 출력 없음. 마이그레이션 변경이 없어 이번 라운드는 `flask db heads`를 실행하지 않았다.
- 디자인 명령: `/Users/saem/.impeccable/bin/0.1.14/impeccable detect http://127.0.0.1:9424/ko-light http://127.0.0.1:9424/ko-dark http://127.0.0.1:9424/en-light http://127.0.0.1:9424/en-dark` → exit 0·출력 없음. 같은 실행 파일의 `detect --viewport 320x844 http://127.0.0.1:9424/en-light http://127.0.0.1:9424/en-dark` → exit 0·출력 없음.
- 디자인 입력은 실제 Flask 렌더 HTML에 현재 tokens/style CSS를 인라인한 메모리 전용 로컬 서버였다. 기존 `snapshot()`으로 숨은 상태와 샘플 타일을 펼쳤다. 외부 링크 및 실행 스크립트를 제거하여 CDN·실제 스토어·외부 서비스를 호출하지 않았으며 서버는 종료했다. 시스템 fallback 폰트 기준이다.
- 구현 증거의 **전체 1403건 통과는 이번 리뷰에서 재실행한 결과가 아니다**. 이번 라운드의 직접 검증 범위는 위 130건이다. 신규 수정은 세션 동기화 JS와 해당 테스트이며 CSS·템플릿·서버 인증 로직에는 라운드 2 이후 변경이 없다.

### 범위·보안·테스트 경계·참고

- D-18-4 테스트는 구현 함수를 대체하지 않고 실제 `init()`·`ensureToken()`·`syncSession()`과 복원 버튼 핸들러를 실행한다. DOM/fetch/storage는 대역이며 요청 횟수와 사용 토큰을 검사하므로 이전의 호출 누락을 잡는 유효한 회귀 테스트다. 서버의 세션 전환 후 삭제 테스트도 실제 Flask API와 전용 DB를 사용하여 통과했다.
- 다만 요청을 보냈다는 사실이 응답 완료를 보장하지는 않는다. 구현 증거의 “둘이 같으면 ... 어긋날 수 없다”는 표현은 테스트가 증명한 범위보다 강하다. `syncSession()`을 기다리지 않는 구조는 로컬 main에도 존재하므로 이번 변경의 새 결함으로 등록하지 않는다. 이번에는 라운드 2처럼 JS→Flask 브리지로 실제 삭제까지 연결한 종단 재현을 반복하지 않았다.
- 기존 세대 검사·언어 변경 직렬화 회귀 테스트가 통과했고, 사용자 수용 D-17-6을 재등록하지 않았다. 인증·CSRF 서버 검증이나 스키마 변경은 없다. 사용자 입력을 새 HTML로 삽입하는 경로 또는 실제 운영 시크릿의 신규 기록을 발견하지 못했다. 증거의 DB 예시는 `.env.example`의 로컬 테스트 계정 형식이며 리뷰에는 복사하지 않았다.
- README 설계 판단과 RELEASE는 `### 18.`에 추가됐고, 수동 체크리스트 변경은 티켓 요구다. `.env.example`·API 표·스펙 미정 항목·사업자 정보 조각은 변경하지 않았다. 공통 fixture의 엔진 풀 정리는 이전 라운드에 승인 범위로 기록된 변경이며 이번 수정에는 추가 변경이 없다.
- 공식 배지 아트워크, 긴 퍼즐 타일의 기존 레이아웃, Safari 네이티브 배너·실기기 수동 검증의 제한은 이전 참고와 같다. 취향·스타일 제안을 결함으로 올리지 않았다.
- 이 리뷰는 `review/impl-review-18.md`만 수정한다. 앱·테스트·설정·`.scratch/` 수정, 프로덕션/NAS 접근, 배포, push, 실제 외부 서비스 호출은 하지 않았다.

판정: PASS
