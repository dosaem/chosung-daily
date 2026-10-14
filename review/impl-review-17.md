# 티켓 17 최종 리뷰 — 라운드 1

## 범위와 기준

- 기준: 로컬 `main` = `abf3e9a`, 구현 HEAD = `6de4cc8`. `git log main..HEAD`의 5개 커밋 및 `git diff main...HEAD` 12개 파일을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 17의 체크박스, 스펙 §A.2·A.16·A'·미정 13, CONTEXT, SCREENS 및 OVERRIDES를 대조했다. 구현 증거 문서는 검증 대상이지 판정 근거로 그대로 인용하지 않았다.
- 애플리케이션·테스트·설정·스펙은 수정하지 않았다. 하위 에이전트·프로덕션·외부 서비스 호출 없이 리뷰 문서만 작성한다.

## 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 언어 칩 → PATCH /me → today 재조회, mask 기반 r/h/s 렌더 | 충족 | `app.js:161`의 변경 요청 뒤 `reloadPuzzle`, `:225`의 mask 렌더. chosung 필드 참조가 없고 `withSeparatorSlots`가 s를 분리한다. 단, 전환과 기존 요청이 겹치는 결함은 D-17-1. |
| 서버 attempts 복원, history만 삭제, 토큰·백업 패널 유지, en 간격 재삽입·미정 13 기록 | 충족 | `app.js:68`, `:243`, `:347`, `index.html:28`, 스펙의 티켓 17 추가 행. Node로 실제 렌더 함수를 실행해 BA 이력의 가운데 s 슬롯 복원 및 history 키만 삭제됨을 확인했다. |
| puzzle_id 동봉, 409 안내·재조회, 언어·계정·백업 전환 시 로컬 상태 폐기 | 미충족 | ID 동봉과 409 재조회 후 안내는 실행 확인. 계정·백업 전환은 저장 후 페이지 재시작 경로가 있다. 그러나 언어 전환 직전 제출 응답이 새 퍼즐 상태를 다시 오염시킨다(D-17-1). |
| 리더보드 entries.display/is_me/me, 통계 language 명시 | 충족 | `app.js:442`, `:458`, `:494`. Node 실행에서 is-me 행·21위 me 표시를 확인. 두 조회 URL 모두 language를 명시한다. |
| UI 사전 ko/en, 기기 언어와 퍼즐 언어 분리, 기존 문구 전부 사전 이동 | 미충족 | 서버 렌더·사전·언어 판정 구현은 존재. API 오류 message를 사전보다 우선해 영어 화면에 한국어를 출력한다(D-17-2). |
| pytest 렌더 테스트 + 요구된 수동 체크리스트 | 충족 | `tests/test_web.py`, `tests/test_ui_strings.py`, README의 웹 수동 체크리스트에 언어 전환·새 탭·자정·계정·백업 항목이 있다. 다만 번들 문자열 검사는 JS 실행 검증이 아니며 아래 두 결함을 검출하지 못한다. |

## 직접 실행한 검증

- 테스트 자원: 기존 로컬 `chosung_daily_test_t17` 및 Redis DB 5를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. 접속 URL의 자격 증명은 이 문서에 기록하지 않는다. 새 DB 생성이나 기본 테스트 DB로의 대체는 하지 않았다. 마이그레이션 테스트는 기본 파생 이름인 기존 `chosung_daily_test_t17_migrations`를 사용한다.
- `uv run pytest -q`: `699 passed in 357.72s (0:05:57)`, exit 0. 첫 실행에서 전부 통과해 재실행은 하지 않았다.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `git diff --check main...HEAD`: 출력 없음, exit 0.
- 이 티켓의 마이그레이션 변경 없음. 추가 확인 `uv run flask db heads`: `a5bab2f58a7b (head)` 한 줄, exit 0.
- Node `vm`에서 작업 트리의 실제 `web/static/app.js`를 읽고 마지막 자동 `init()`만 생략한 뒤 DOM/fetch 경계를 대역으로 제공해 함수를 실행했다. 서버 attempts·s 간격 복원, history만 정리, `is_me`/`me`, 409 재조회 후 안내 유지 모두 assertion 통과. 이는 브라우저 레이아웃·실제 HTTP 왕복 검증을 대신하지 않으며, 구현자의 Chrome 실행 기록을 재실행했다고 주장하지 않는다.

## 결함

### D-17-1 — MAJOR — 전환 이전 요청의 응답이 새 퍼즐 상태를 오염시킨다

- 위치: `web/static/app.js:415` (관련 `:161`, `:324`, `:387`).
- 재현 입력/순서: ko 퍼즐에서 답을 제출하고 그 POST 응답의 클라이언트 도착을 지연시킨다 → 서버가 해당 제출을 처리한 뒤 English 칩으로 전환하여 PATCH 및 en today 조회를 완료한다 → 이전 ko POST 응답을 도착시킨다. 언어 칩은 제출 중에도 활성화되어 있다.
- 기대: 이미 폐기한 ko 요청의 응답은 en 보드·기회·힌트·완료 상태를 바꾸지 않는다.
- 실제: `submitGuess`는 요청 당시 puzzle_id와 현재 puzzle_id가 같은지 확인하지 않고 현재 `state.attempts`에 ko guess를 추가하고 남은 기회를 덮어쓴다. 정답 응답이면 새 en 퍼즐의 입력 폼까지 숨기고 ko 정답으로 완료 표시한다. 서버 DB가 다른 퍼즐에 기록되는 문제는 아니지만 현재 플레이·공유 결과가 잘못되고 새로고침 전까지 유지된다.
- 직접 실행 결과: ko ID 1의 응답을 보류하고 en ID 2(빈 attempts, 5회)로 `discardLocalPlayState`·`applyPuzzle` 후 응답을 풀었을 때 `{"puzzleId":2,"language":"en","attempts":[{"guess":"사과","feedback":[true,false]}],"left":4}`가 됐다. 아래 재현 명령으로 같은 결과를 얻는다.
- 요구 위반: 티켓의 언어 변경 시 로컬 상태 폐기 및 스펙 §A.2의 현재 퍼즐별 보드 일관성. `test_js_discards_local_play_state_on_language_and_account_switch`는 함수명 존재만 검사하므로 이 응답 순서를 검증하지 않는다.

### D-17-2 — MAJOR — 영어 UI의 일반 오류가 한국어로 출력된다

- 위치: `web/static/app.js:406` 및 `:103` (응답 생성 근거 `app/services/guess_service.py:58`, `app/errors.py`).
- 재현 입력: UI 언어 en, 5글자 퍼즐에서 `a` 제출 → 서버 `VALIDATION_ERROR` 응답 → 화면 메시지 확인. 퍼즐이 없는 날의 today 조회와 rate limit/이미 완료 오류도 같은 우선순위 문제를 갖는다.
- 기대: 퍼즐 언어와 무관하게 영어 UI 사전의 안내가 표시된다.
- 실제: `data.message || t("generic_error")` 때문에 서버의 `정답은 5글자입니다.`가 그대로 보인다. `loadToday`도 한국어 `body.message`를 먼저 선택한다. API는 기기 언어별 메시지를 제공하지 않으므로 정상적인 오류 응답에서는 번역된 fallback이 쓰이지 않는다.
- 직접 실행 결과: 영어 사전을 주입한 실제 `submitGuess`에 서버와 동일한 오류 payload를 전달했을 때 `#message.textContent`가 `정답은 5글자입니다.`였다.
- 요구 위반: 티켓의 UI 문구 ko/en 및 기존 문구 전부 사전 이동. 초기 HTML에 한글이 없는지/사전 키가 일치하는지 검사하는 테스트는 API 응답 이후 DOM을 검증하지 않는다.

### 두 결함의 독립 재현 명령

저장소 루트에서 실행한다. 네트워크·DB·실제 토큰을 사용하지 않으며 저장소 파일을 쓰지 않는다. 대역은 DOM과 응답 도착 순서만 제공하고 대상 함수는 현재 구현을 그대로 실행한다.

```sh
node <<'JS'
const fs = require('fs'), vm = require('vm');
const els = new Map();
function el() {
  return {textContent:'', value:'', children:[],
    classList:{add(){}, remove(){}},
    appendChild(x){this.children.push(x)},
    set innerHTML(x){this.children=[]}};
}
const document = {
  getElementById(id){if(!els.has(id)) els.set(id,el()); return els.get(id)},
  createElement:el, querySelectorAll(){return []}
};
document.getElementById('ui-strings').textContent = JSON.stringify({
  generic_error:'Something went wrong.', attempts_left:'{left}/{max} tries left',
  hint:'Hint: {hint}', category_general:'General', length_caption:'{length} letters'
});
let release;
const ctx = vm.createContext({document, localStorage:{}, console,
  fetch:()=>new Promise(r=>release=r)});
vm.runInContext(fs.readFileSync('web/static/app.js','utf8')
  .replace(/init\(\);\s*$/,''),ctx);
(async()=>{
  vm.runInContext("state.puzzleId=1; state.puzzleLanguage='ko'",ctx);
  const pending = vm.runInContext("submitGuess({value:'사과'},'사과')",ctx);
  vm.runInContext(`discardLocalPlayState(); applyPuzzle({
    puzzle_id:2, language:'en', date:'2026-10-14', category:'general', length:5,
    mask:[{t:'h',c:''},{t:'r',c:'P'},{t:'r',c:'P'},{t:'r',c:'L'},{t:'h',c:''}],
    attempts:[], attempts_left:5, status:'in_progress', hint:null})`,ctx);
  release({ok:true,json:async()=>({is_correct:false,
    feedback:[true,false],attempts_left:4})});
  await pending;
  console.log(vm.runInContext(`JSON.stringify({puzzleId:state.puzzleId,
    language:state.puzzleLanguage,attempts:state.attempts,left:state.attemptsLeft})`,ctx));
  ctx.fetch=async()=>({ok:false,json:async()=>({
    code:'VALIDATION_ERROR',message:'정답은 5글자입니다.'})});
  await vm.runInContext("submitGuess({value:'a'},'a')",ctx);
  console.log(document.getElementById('message').textContent);
})();
JS
```

## 보안·공유 파일·범위 확인

- `guess`, `display`, 정답, 이메일은 `textContent`로 넣는다. `innerHTML`은 컨테이너를 빈 문자열로 비우는 데만 쓰고 UI JSON은 Jinja `tojson`을 사용한다. 이 변경에서 서버 문자열의 HTML 삽입 경로를 발견하지 않았다.
- 언어 변경·제출은 기존 Bearer 인증을 사용한다. 인증/CSRF 서버 가드를 제거한 변경은 없다. 서버 입력 검증은 유지된다. diff에서 실제 키·토큰·비밀번호 값의 신규 저장을 발견하지 않았다.
- README 설계 판단에는 17 소제목들, 스펙에는 티켓 17의 미정 13 확정 행만 추가됐다. 다른 티켓 본문을 덮어쓰지 않았다. `.env.example`·릴리스 문서는 변경하지 않았다. 웹 수동 체크리스트는 티켓이 요청한 새 절이다.
- `tests/test_token_css.py`의 기존 '메인 스타일 무변경' 검사는 새 요소의 공용 토큰 사용 결정에 맞춰 교체됐다. API·스키마 변경이나 범위 밖 제품 기능은 발견하지 않았다.

## 참고

- 코디네이터의 리뷰 메모에 따라 기존 페이지 토큰 전환·다크모드·다크 OS 대비 중간 상태는 티켓 18의 후속 범위로만 기록하며 결함 수에 넣지 않는다. 이 리뷰에서 시각적 브라우저 검증이나 `impeccable detect`를 재실행하지 않았으므로 증거 문서의 라이트 0건 주장을 독립 확인한 것으로 간주하지 않는다.
- JS 문자열 계약 테스트는 변경 감지 역할만 한다. 위 결함은 실행 순서와 응답 문구 때문에 발생하므로 함수명/문자열의 존재만으로 완료 근거를 삼을 수 없다.
- 결함 합계: BLOCKER 0 / MAJOR 2 / MINOR 0. 수정과 재검토가 필요하다.

판정: FAIL

## 라운드 2

### 범위와 기준

- 리뷰 시작 시 로컬 `main` = `bf287f6`, 구현 HEAD = `be5caf0`. `git log main..HEAD`의 8개 커밋과 `git diff main...HEAD`의 17개 파일을 확인했다. 종료 시 main은 `008a35a`로 이동했지만 merge-base는 `bf287f6`이고 같은 커밋·diff 범위임을 재확인했다. `origin/main`은 사용하지 않았다.
- 티켓 17의 전체 체크박스, 스펙 §A.2·A.16·A'·미정 13, CONTEXT, SCREENS, MASTER 및 우선하는 OVERRIDES를 대조했다. 구현 증거의 수정 라운드 1 주장과 이전 리뷰의 두 결함을 직접 재검증했다.
- 하위 에이전트, 프로덕션 접근, 배포, 외부 서비스 호출 없이 검토했다. 이 리뷰 파일 외에 애플리케이션·테스트·설정·`.scratch/` 파일은 수정하지 않았다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 언어 칩 → PATCH /me → today 재조회, mask 기반 r/h/s 렌더 | 미충족 | 정상 전환의 PATCH→GET 및 mask 렌더는 구현·실행 확인. 그러나 늦은 `/me/stats` 응답이 전환한 언어를 되돌리고 칩 동작까지 막는다(D-17-3). |
| 서버 attempts 복원, history만 삭제, 토큰·백업 패널 유지, en 간격 재삽입·미정 13 기록 | 충족 | `applyPuzzle`의 서버 attempts 적용, `withSeparatorSlots`의 s 복원, history 접두사 키만 삭제됨을 실제 번들 실행으로 확인. 토큰·다른 저장소 키 유지 assertion 통과. 백업 패널과 스펙의 티켓 17 확정 행 존재. 다만 전환 후 늦은 제출로 복원 이력이 오염되는 문제는 D-17-1. |
| puzzle_id 동봉, 409 안내·재조회, 언어·계정·백업 전환 시 로컬 상태 폐기 | 미충족 | 요청 본문의 ID와 409 후 재조회·안내 유지 assertion 통과. 계정·백업 전환의 저장/정리/페이지 재시작 경로 유지. ko→en→ko 왕복 시 폐기한 요청을 다시 유효하다고 판단해 서버 이력에 중복 행을 추가한다(D-17-1 REPEAT). |
| 리더보드 entries.display/is_me/me, 통계 language 명시 | 충족 | 익명 display·is-me 행과 21위 me 렌더 실행 확인. 순위·통계 fetch URL에 `language=en` 포함됨을 assertion으로 확인. |
| UI 사전 ko/en, 기기 언어와 퍼즐 언어 분리, 기존 문구 전부 사전 이동 | 충족 | 공용 언어 판정으로 서버 HTML·JSON 사전을 선택하고 퍼즐 선호는 별도 유지. 오류 6경로 실행에서 영어 문구 확인(D-17-2 FIXED). 서버 제공 퍼즐 내용·익명 display는 API 계약대로 렌더한다. |
| pytest 렌더 테스트 + 요구된 수동 체크리스트 | 충족 | Flask 렌더 테스트·사전 테스트와 README의 언어 전환/새 탭/자정/계정/백업 체크리스트 존재. 새 JS 테스트는 실제 번들을 실행하지만 한 번의 언어 전환만 다루며 아래 왕복·stats 지연 시나리오는 빠져 있다. |

### 직접 실행한 검증

- 테스트는 기존 로컬 `chosung_daily_test_t17`과 Redis DB 5를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. URL 자격 증명은 기록하지 않는다. 새 DB를 만들지 않았고 기본 테스트 DB로 대체하지 않았다. 마이그레이션 테스트는 기존 파생 DB `chosung_daily_test_t17_migrations`를 사용한다.
- 전체 `uv run pytest -q`: `722 passed in 514.37s (0:08:34)`, exit 0. 첫 실행에서 실패 없이 완료되어 재실행하지 않았다.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `uv run flask db heads`: `dae1b5af0cf7 (head)` 한 줄, exit 0. 티켓 17 자체의 마이그레이션 변경은 없다.
- `git diff --check main...HEAD`: 출력 없음, exit 0.
- 작업 트리의 `app.js`를 Node VM으로 실행했다. DOM·fetch 경계만 대역인 기존 `tests/js/harness.mjs`를 재사용하고, 아래 두 재현은 리뷰어가 별도로 구성했다. 정상 경로는 실제 en 사전을 넣어 mask 간격 복원, history만 제거, 토큰 유지, is_me/me, puzzle_id, 409 재조회 후 안내, 언어별 조회 URL을 assertion으로 확인했다.
- `tests/js/error_message_language.mjs`에 실제 en 사전을 넣어 독립 실행: validation / already_finished / rate_limited / unauthorized / unknown / today_no_puzzle 모두 영어 문구. 길이 오류는 `The answer is 5 letters.`, 미등록 code는 `Something went wrong.`, 퍼즐 없음은 `Today's puzzle isn't ready yet.`였다.

### 이전 결함 재판정 및 신규 결함

#### D-17-1 — REPEAT — MAJOR — 같은 퍼즐로 돌아오면 폐기한 제출 응답이 복원 이력을 중복시킨다

- 위치: `web/static/app.js:420` (관련 `:341`, `:441`), 회귀 검증 누락: `tests/js/stale_submit_response.mjs:84`.
- 이전 ko→en 단방향 재현은 ID 비교 가드로 막혔다. 그러나 이 가드는 요청 후 로컬 상태가 폐기/복원되었는지를 구분하지 못한다. 왕복 후 ID가 같아지면 이미 폐기한 요청도 다시 수용하므로 원래의 상태 오염 결함을 완전히 고치지 못했다.
- 재현: ko 퍼즐(ID 1)에서 `사자` 오답 제출 → 서버에는 1회 기록되었지만 POST 응답 도착은 보류 → English 칩으로 en(ID 2) 전환 완료 → 한국어 칩으로 ko(ID 1) 전환 완료(서버 attempts 1행, 남은 기회 4) → 보류했던 POST 응답 도착.
- 기대: 이미 서버 이력으로 복원한 1행을 유지한다. 전환 전에 시작한 제출 응답은 현재 보드에 다시 추가하지 않는다.
- 실제: 같은 `사자` 행이 두 번 보이고 공유 그리드도 중복된다. 남은 기회는 4로 서버 이력과 보드 행 수가 모순된다. DB에 중복 저장되는 문제는 아니지만 새로고침 전까지 플레이 기록·공유가 잘못된다.
- 직접 실행 출력: 응답 전 `{"id":1,"attempts":[{"guess":"사자","feedback":[true,false]}],"left":4}` → 응답 후 `{"id":1,"attempts":[{"guess":"사자","feedback":[true,false]},{"guess":"사자","feedback":[true,false]}],"left":4}`.
- 기존 테스트는 `discardLocalPlayState(); applyPuzzle(en)`만 실행하고 en에서 응답을 풀기 때문에 왕복 후 같은 ID인 경우를 검증하지 않는다. 요청이 속한 상태의 세대까지 무효화되어야 하는 결함이다.

#### D-17-2 — FIXED — 이전 MAJOR — 영어 UI 오류의 한국어 노출

- 위치: `web/static/app.js:24`, `:34`, `:121`, `:432`, `app/utils/ui_strings.py:60`.
- `message` 우선 사용을 없애고 code→사전 키→호출 지점별 fallback으로 변경했다. 실제 영어 사전과 한국어 API 오류 payload를 넣어 `submitGuess`·`loadToday`를 실행해 6경로의 번역 결과를 확인했다.
- 재현 입력: en UI에서 5글자 퍼즐에 `a` 제출, 서버 `VALIDATION_ERROR` + 한국어 message 응답 → 기대 및 실제 모두 `The answer is 5 letters.`. 미등록 code와 today 오류에도 한국어 message가 노출되지 않는다. 활성 결함 수에 포함하지 않는다.

#### D-17-3 — 신규 — MAJOR — 늦은 내 기록 조회가 퍼즐 언어를 되돌려 전환을 막는다

- 위치: `web/static/app.js:144` (관련 `:173`, `:180`, `:693`).
- 재현: ko 퍼즐에서 시작한 `/me/stats` 응답(`puzzle_language: ko`) 도착을 보류 → English 칩의 PATCH 및 today 재조회를 완료해 en(ID 2)을 표시 → 이전 stats 응답 도착 → 한국어 칩 클릭. 초기 `init()`은 stats를 기다리지 않고 today를 읽고, 정답 후에도 stats를 비동기로 읽으므로 실제 UI에서 가능한 순서다.
- 기대: 현재 en 퍼즐과 English 선택 상태를 유지하고, 다음 한국어 클릭에서 PATCH→today로 ko로 전환한다.
- 실제: `renderLanguageChips(stats.puzzle_language)`가 en 퍼즐의 ID·mask는 그대로 두고 `state.puzzleLanguage` 및 선택 칩만 ko로 되돌린다. 그 다음 한국어 클릭은 `language === state.puzzleLanguage` 조건으로 즉시 반환되어 요청이 0건이며 en 퍼즐에서 벗어나지 못한다. 정규화도 en 대문자 처리를 잃는다.
- 직접 실행 출력: `{"id":2,"language":"ko","normalized":"ab"}`, 칩 `ko:true/en:false`, 한국어 클릭 요청 수 `0`. 정상 기대는 ID 2의 language=en, `normalizeGuess("ab")="AB"`, 한국어 클릭 시 PATCH 및 재조회다.
- D-17-1의 제출 응답 가드와 별개인 조회 응답의 언어 덮어쓰기다. 현재 퍼즐/전환보다 오래된 stats 응답이 선택 상태를 바꿔서는 안 된다.

### 두 결함의 독립 재현 명령

레포 루트에서 아래 명령을 실행한다. 네트워크·DB·파일 변경 없이 실제 번들의 `handleLanguageChange`, `reloadPuzzle`, `submitGuess`, `loadStats`를 호출한다. fetch는 응답 도착 순서만 제어한다.

```sh
node --input-type=module <<'JS'
import { loadApp, okResponse } from './tests/js/harness.mjs';
const strings = {
  attempts_left:'{left}/{max}', category_general:'General',
  length_caption:'{length}', hint:'{hint}', streak_summary:'{current}/{max}/{solved}',
  leaderboard_empty:'empty', my_rank_unsolved:'none', stats_empty:'empty'
};
const ko = {puzzle_id:1, language:'ko', date:'2026-10-14', category:'general',
  length:2, mask:[{t:'r',c:'ㅅ'},{t:'r',c:'ㄱ'}], attempts:[],
  attempts_left:5, status:'in_progress', hint:null};
const en = {...ko, puzzle_id:2, language:'en', mask:[{t:'h',c:''},{t:'r',c:'B'}]};
for (const scenario of ['D-17-1', 'D-17-3']) {
  const app = loadApp({strings});
  app.run(`applyPuzzle(${JSON.stringify(ko)})`);
  const release = app.holdFetch();
  const pending = app.run(scenario === 'D-17-1'
    ? 'submitGuess(document.getElementById("guess-input"),"사자")' : 'loadStats()');
  let current = en;
  app.setFetch(async (url, options) => {
    if (options?.method === 'PATCH')
      return okResponse({puzzle_language:JSON.parse(options.body).puzzle_language});
    if (url.endsWith('/puzzles/today')) return okResponse(structuredClone(current));
    return okResponse({entries:[],me:null,total_solved:0,by_attempt:{}});
  });
  await app.run('handleLanguageChange("en")');
  if (scenario === 'D-17-1') {
    current = {...ko, attempts:[{guess:'사자',feedback:[true,false]}], attempts_left:4};
    await app.run('handleLanguageChange("ko")');
    release(okResponse({is_correct:false,feedback:[true,false],attempts_left:4}));
  } else {
    release(okResponse({puzzle_language:'ko',current_streak:0,max_streak:0,
      solved_count:0,linked_account:null}));
  }
  await pending;
  console.log(scenario, app.run(`JSON.stringify({id:state.puzzleId,
    language:state.puzzleLanguage,attempts:state.attempts,left:state.attemptsLeft})`));
  if (scenario === 'D-17-3') {
    let requests = 0;
    app.setFetch(async () => { requests++; return okResponse({}); });
    await app.run('handleLanguageChange("ko")');
    console.log('ko click requests:', requests);
  }
}
JS
```

### 보안·범위·공유 파일 확인 및 한계

- 서버 문자열은 `textContent`, 사전 JSON은 Jinja `tojson`으로 출력한다. `innerHTML`은 비우기에만 사용한다. 변경된 경로에서 HTML 주입·인증/CSRF 가드 제거·서버 입력 검증 제거·실제 비밀값의 신규 커밋은 발견하지 않았다. 위 결함은 화면 상태 오염이며 서버 데이터 손상은 재현되지 않았다.
- README 설계 판단은 자기 번호 `### 17.`만 추가하고 스펙은 자기 미정 13 행만 추가했다. 기존 타 티켓 본문은 유지됐다. 웹 수동 체크리스트 신설은 티켓의 명시 요구다. `.env.example`·`docs/RELEASE.md`는 변경되지 않았다. 범위 밖 API·스키마 변경은 없다.
- 새 JS 테스트는 실제 번들을 실행하므로 항상 통과하는 가짜 구현은 아니다. 다만 전환을 직접 상태 함수 두 개로 대체하는 기존 시나리오가 왕복 전환과 stats 경합을 놓친다. 문자열 존재 검사도 여전히 HTTP/비동기 동작의 증명이 아니다.
- 이전 라운드에 기록된 티켓 18의 다크모드·기존 페이지 토큰 전환 범위는 그대로 구분했다. 이번에도 브라우저 레이아웃이나 `impeccable detect`를 재실행하지 않았으므로 구현 증거의 시각 검증 주장을 독립 확인했다고 하지 않는다. 취향·스타일 제안은 결함으로 세지 않았다.
- 활성 결함: BLOCKER 0 / MAJOR 2 / MINOR 0. D-17-1 REPEAT, D-17-2 FIXED, D-17-3 신규. 두 상태 경합의 수정과 재검토가 남는다.

판정: FAIL

## 라운드 3

### 범위와 기준

- 로컬 `main` = `1e764da`, 구현 HEAD = `d80f317` 기준 `git log main..HEAD`의 11개 커밋과 `git diff main...HEAD`의 18개 파일을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 17의 체크박스, 스펙 §A.2·A.16·A'·미정 13, CONTEXT, SCREENS, MASTER 및 우선하는 OVERRIDES를 대조했다. 구현 증거의 수정 라운드 2 주장은 실제 번들과 테스트로 확인했다.
- 하위 에이전트와 프로덕션/외부 서비스 접근 없이 검토했다. 애플리케이션·테스트·설정·`.scratch/`는 수정하지 않았으며 이 리뷰 파일만 변경한다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 언어 칩 → PATCH /me → today 재조회, mask의 r/h/s 렌더 | 미충족 | 정상 PATCH→GET 및 r/h/s 렌더는 확인했다. 그러나 먼저 조회한 응답의 본문 수신이 지연되면 마지막 선택의 퍼즐을 덮어쓴다(D-17-4). |
| 서버 attempts 복원, history만 삭제, 토큰·백업 패널 유지, en 간격 재삽입·미정 13 기록 | 충족 | 실제 번들 실행에서 서버 attempts의 `AB`를 mask에 따라 `A B`로 복원했다. history 키만 삭제하고 토큰·다른 키를 유지하는 assertion 통과. 백업 패널과 티켓 17의 미정 13 확정 행도 유지된다. |
| puzzle_id 동봉, 409 인라인 안내·재조회, 언어·계정·백업 전환 시 상태 폐기 | 미충족 | puzzle_id 포함 요청과 409 이후 보드 복원·안내 유지 assertion 통과. 계정/백업 전환의 저장·정리·페이지 재시작 경로도 유지된다. 이전 제출 응답의 왕복 경합은 해결됐지만 폐기한 조회 본문이 다시 보드를 덮는 경로가 남는다(D-17-4). |
| 리더보드 entries.display/is_me/me, 통계 language 명시 | 미충족 | 내 행 강조·21위 me 렌더와 두 조회 URL의 `language=en`을 실행 확인했다. 본문 수신이 늦으면 전 언어의 순위·통계가 새 언어 화면에 다시 표시된다(D-17-4와 같은 원인). |
| UI 문자열 ko/en 사전, 기기 언어와 퍼즐 언어 분리, 기존 문구 사전 이동 | 충족 | 서버 렌더와 UI 사전 테스트 및 오류 6경로 실행 통과. API 오류의 한국어 message를 표시하지 않고 code로 영어 UI 문구를 고른다(D-17-2 FIXED). 서버 퍼즐 내용과 익명 display는 API 계약대로 표시한다. |
| pytest 렌더 테스트 + 요구된 수동 체크리스트 | 충족 | Flask 렌더·사전·JS 실행 테스트와 README의 언어 전환/새 탭/자정/계정/백업 체크리스트가 있다. 새 JS 테스트는 실제 번들을 실행하지만 fetch와 본문 수신의 두 비동기 경계를 구분하지 않아 D-17-4를 놓친다. |

### 직접 실행한 검증

- 기존 로컬 `chosung_daily_test_t17`과 Redis DB 5를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. URL 자격 증명은 기록하지 않는다. 새 DB를 생성하지 않았고 기본 테스트 DB로 대체하지 않았다. 마이그레이션 테스트의 기본 파생 이름은 기존 `chosung_daily_test_t17_migrations`다.
- 전체 `uv run pytest -q`: `788 passed in 697.94s (0:11:37)`, exit 0. 첫 실행에서 실패 없이 완료되어 재실행하지 않았다.
- `uv run pytest tests/test_web_js.py tests/test_ui_strings.py -q`: `23 passed in 0.27s`, exit 0. Node가 설치되어 있어 JS 테스트는 skip 없이 실제 실행됐다.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `uv run flask db heads`: `dae1b5af0cf7 (head)` 한 줄, exit 0. 티켓 17 자체 마이그레이션은 없다.
- `git diff --check main...HEAD`: 출력 없음, exit 0.
- 별도 Node assertion으로 mask r/h/s, 서버 보드의 구분자 복원, history만 삭제, 토큰/기타 키 보존, is_me/me, 제출 정규화와 puzzle_id, 409 재조회 뒤 안내 유지, 순위·통계의 명시적 언어 URL을 확인했다.

### 이전 결함 재판정

#### D-17-1 — FIXED — 이전 MAJOR — 왕복 후 폐기한 제출 응답의 중복 반영

- 위치: `web/static/app.js:451`, `:457`, `:459`.
- 라운드 2의 ko 제출 보류 → en → ko(서버 1행 복원) → 제출 응답 도착 순서를 다시 실행했다. 기대 및 실제 모두 ID 1, ko, attempts 1행, 남은 기회 4다.
- `submitGuess`는 JSON 본문을 읽은 뒤 세대와 퍼즐 ID를 검사한다. 단방향 오답·정답, 왕복, 전환 없는 대조군 테스트도 통과했다. 활성 결함에 포함하지 않는다.

#### D-17-2 — FIXED — 이전 MAJOR — 영어 UI 오류의 한국어 노출

- 위치: `web/static/app.js:24`, `:34`, `:471`, `app/utils/ui_strings.py:121`.
- en 사전으로 validation / already_finished / rate_limited / unauthorized / unknown / today_no_puzzle을 실행하는 테스트를 다시 돌렸다. 길이 오류는 `The answer is 5 letters.`, 미등록 code는 `Something went wrong.`이며 한국어 API message는 노출되지 않는다. 활성 결함에 포함하지 않는다.

#### D-17-3 — FIXED — 이전 MAJOR — 늦은 내 기록 조회의 언어 되돌림

- 위치: `web/static/app.js:149`, `:159`, `:174`.
- 라운드 2의 ko stats 응답 보류 → en 전환 → ko stats 도착 순서를 다시 실행했다. 기대 및 실제 모두 ID 2 / language=en이며 다음 한국어 클릭에서 요청 4건(PATCH·today·순위·통계)이 발생했다. `normalizeGuess("ab")`가 `AB`인 회귀 테스트도 통과했다.
- `loadStats`의 칩 갱신 검사는 JSON 본문을 읽은 뒤에 있어 이번 D-17-4와 달리 본문 대기 중 전환도 걸러낸다. 활성 결함에 포함하지 않는다.
- 이전 리뷰의 독립 명령은 마지막 클릭의 fetch 대역이 모든 경로에 `{}`를 돌려주므로, 수정 후 실제 재조회에 도달하면 mask 누락 오류가 났다. 재검증에서는 그 대역만 정상 PATCH/퍼즐/순위/통계 payload로 바꿨다. 애플리케이션 코드는 변경하지 않았다.

### 신규 결함

#### D-17-4 — 신규 — MAJOR — 응답 본문 대기 중 전환하면 이전 조회가 새 퍼즐·순위·통계를 덮어쓴다

- 위치: `web/static/app.js:140`, `:146` → `:396` (같은 검사 위치 문제: `:218`→`:224`, `:515`→`:521`, `:563`→`:566`).
- 원인: today·PATCH·순위·통계는 `await fetch()` 직후 세대를 검사한 뒤 `res.json()`을 기다린다. 헤더를 받은 뒤에도 본문 읽기는 비동기로 계속될 수 있다. 그 사이 상태가 폐기되면 이미 통과한 검사는 무효지만, 본문 완료 뒤에는 검사 없이 적용한다. 제출과 `/me/stats`는 본문을 읽은 뒤 검사하므로 이번 결함의 대상이 아니다.
- 재현 입력: ko 상태에서 재조회 시작 → ko 응답 헤더는 도착시키되 본문은 보류 → English 칩의 PATCH와 en today 조회를 완료 → 앞선 ko 본문을 도착시킨다. 또는 English 전환의 today 본문 보류 → 한국어 전환 완료 → 앞선 en 본문 도착으로도 재현된다.
- 기대: 마지막 선택 en(ID 2)을 유지하고 폐기한 ko 본문은 버린다. 순위·통계에도 선택한 en 자료만 남아야 한다.
- 실제: 본문 도착 후 ID 1 / ko로 되돌아간다. 별도로 순위·통계 본문을 보류하면 en(ID 2)은 유지하면서 `old-ko-player` 순위 및 ko의 `1:100` 분포가 나타난다. 반대 방향 실행에서도 마지막 ko(ID 1, generation 2)가 늦은 en 본문 때문에 en(ID 2, generation 2)으로 바뀌었다. 보드·언어 선택·서버 선호가 불일치하며 다음 제출은 409 재조회가 필요해질 수 있다. 서버 DB 손상은 재현되지 않았다.
- 직접 검증은 Node의 실제 `Response`와 `ReadableStream`으로 본문 도착만 지연했다. DOM/fetch 경계 외의 대상 함수는 작업 트리 번들 그대로이며 네트워크·DB·파일 수정이 없다.
- 기존 `tests/js/stale_state_generation.mjs`의 E 시나리오는 fetch Promise 자체를 보류한다. `okResponse`의 json은 즉시 완료되므로 검사 이후 본문 대기 창을 검증하지 않는다. "모든 비동기 요청을 세대 하나로 거른다"는 구현 증거의 주장은 이 경계까지 성립하지 않는다.
- 요구 위반: 티켓의 언어 변경 후 재조회 및 상태 폐기, 스펙 §A.2의 현재 퍼즐 보드 일관성과 언어별 순위·통계. 상태 적용 직전에 요청의 세대가 유효해야 한다.

### D-17-4 독립 재현 명령

레포 루트에서 실행한다. 실제 `Response`가 본문 스트림을 다 읽기 전에 언어 전환을 완료시키는 재현이며, 세 줄 모두 이전 데이터가 들어오는 것이 현재 실제 결과다.

```sh
node --input-type=module <<'JS'
import {loadApp,okResponse} from './tests/js/harness.mjs';
const strings={attempts_left:'{left}/{max}',category_general:'General',
  length_caption:'{length}',hint:'{hint}',leaderboard_empty:'empty',
  my_rank_unsolved:'none',stats_empty:'empty',my_rank:'#{rank}',
  leaderboard_entry:'{display}',stats_row:'{attempt}:{percent}'};
const ko={puzzle_id:1,language:'ko',date:'2026-10-14',category:'general',
  length:2,mask:[{t:'r',c:'ㅅ'},{t:'r',c:'ㄱ'}],attempts:[],
  attempts_left:5,status:'in_progress',hint:null};
const en={...ko,puzzle_id:2,language:'en',mask:[{t:'h',c:''},{t:'r',c:'B'}]};
for(const kind of ['today','leaderboard','stats']){
  const app=loadApp({strings});app.run(`applyPuzzle(${JSON.stringify(ko)})`);
  let controller;
  const response=new Response(new ReadableStream({start(c){controller=c}}),
    {status:200,headers:{'Content-Type':'application/json'}});
  app.setFetch(async()=>response);
  const pending=app.run(kind==='today'?'reloadPuzzle()':
    kind==='leaderboard'?'loadLeaderboard()':'loadTodayStats()');
  await new Promise(r=>setTimeout(r,0));
  app.setFetch(async(url,options)=>{
    if(options?.method==='PATCH')return okResponse({puzzle_language:'en'});
    if(url.endsWith('/puzzles/today'))return okResponse(structuredClone(en));
    if(url.includes('leaderboard'))return okResponse({entries:[],me:null});
    return okResponse({total_solved:0,by_attempt:{}});
  });
  await app.run('handleLanguageChange("en")');
  const old=kind==='today'?ko:kind==='leaderboard'?{
    entries:[{rank:1,display:'old-ko-player',attempts:1,seconds:1,is_me:false}],
    me:{rank:9,attempts:1,seconds:1}}:{total_solved:10,by_attempt:{1:1}};
  controller.enqueue(new TextEncoder().encode(JSON.stringify(old)));
  controller.close();await pending;
  console.log(kind,app.run('JSON.stringify({id:state.puzzleId,language:state.puzzleLanguage})'),
    app.el('leaderboard-entries').text,app.el('today-stats').text);
}
JS
```

실제 출력:

```text
today {"id":1,"language":"ko"}  empty
leaderboard {"id":2,"language":"en"} #1old-ko-player empty
stats {"id":2,"language":"en"}  1:1002:03:04:05:0
```

### 보안·공유 파일·범위 및 참고

- 문자열은 `textContent`, 사전은 Jinja `tojson`으로 출력하며 `innerHTML`은 컨테이너 비우기에만 사용한다. 변경에서 인증/CSRF 가드나 서버 입력 검증 제거, 실제 시크릿의 신규 기록, 서버 데이터 손상을 발견하지 않았다. 테스트 fixture 문자열은 실제 인증 정보로 사용하지 않았다.
- README 설계 판단은 자기 번호 `### 17.`만 추가했고, 스펙은 티켓 17의 미정 13 확정 행만 추가했다. 타 티켓 기존 본문 수정은 없고 `.env.example`·릴리스 문서·스키마도 변경하지 않았다. README 수동 체크리스트와 JS 회귀 테스트는 티켓/결함의 범위다.
- 테스트 대역은 DOM·응답 도착 순서를 제공하며 구현을 복제하지 않는다. 기존 회귀 테스트는 유효하지만 fetch와 본문 수신을 합쳐 보는 범위 한계가 있다. 문자열 존재 검사만으로 HTTP·비동기 동작이 증명되는 것은 아니다.
- 브라우저 레이아웃·`impeccable detect`는 이번에 재실행하지 않았다. 구현 증거의 시각 검증 주장을 독립 확인했다고 하지 않는다. 기존 페이지 토큰·다크모드·아이콘 등 이전 라운드에서 구분한 티켓 18 범위는 유지하며 취향·스타일 제안은 결함으로 세지 않았다.
- 활성 결함: BLOCKER 0 / MAJOR 1 / MINOR 0. D-17-1·2·3은 FIXED이며 D-17-4의 수정과 재검토가 남는다.

판정: FAIL

## 라운드 4

### 범위와 기준

- 로컬 `main` = `b8f63cc`, 구현 HEAD = `27b1aa7`. `git log main..HEAD`의 14개 커밋과 `git diff main...HEAD`의 19개 파일을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 17의 6개 체크박스, 스펙 §A.2·A.16·A'·미정 13, CONTEXT, SCREENS, MASTER 및 우선하는 OVERRIDES를 대조했다. 구현 증거의 수정 라운드 3 주장과 이전 리뷰의 재현 명령을 직접 확인했다.
- 애플리케이션·테스트·설정·`.scratch/`를 수정하지 않았다. 하위 에이전트·프로덕션·실제 외부 서비스 접근 없이 이 리뷰 파일만 변경한다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 언어 칩 → PATCH /me → today 재조회, mask r/h/s 렌더 | 미충족 | 정상 전환과 타일 렌더는 실행 확인했다. 그러나 중복 PATCH의 서버 처리 순서가 뒤집히면 마지막 선택 ko와 서버 선호 en이 불일치한다(D-17-5). |
| 서버 attempts 복원, history만 삭제, 토큰·백업 패널 유지, en 간격 재삽입·미정 13 기록 | 충족 | 실제 번들 assertion으로 `AB` 이력의 `A B` 복원, r/h/s 클래스, history만 삭제하고 토큰·다른 키 보존을 확인했다. 템플릿의 백업 패널과 스펙의 티켓 17 확정 행도 유지된다. |
| puzzle_id 동봉, 409 인라인 안내·재조회, 언어·계정·백업 전환 시 상태 폐기 | 충족 | 정규화된 `AB`와 화면 ID를 제출하고, 409 뒤 서버 이력 복원·안내 유지하는 실행 assertion이 통과했다. 계정 콜백은 새 페이지 초기화 전에 토큰/이력을 처리하고 백업 전환은 폐기 후 페이지를 다시 연다. 폐기한 응답의 재반영은 D-17-1·3·4 수정으로 차단되지만, 이미 보낸 PATCH의 서버 부작용은 D-17-5로 별도 기록한다. |
| 리더보드 entries.display/is_me/me, 통계 language 명시 | 충족 | 내 행의 `is-me`, 목록 밖 21위 `me`, 순위/통계의 `language=en` URL을 직접 실행해 확인했다. 본문 수신 중 전환 회귀 테스트도 통과했다. |
| UI 문자열 ko/en 사전, 기기 언어와 퍼즐 언어 분리, 기존 문구 사전 이동 | 충족 | Flask 렌더·언어 판정·사전 테스트와 영어 오류 6경로의 번들 실행이 통과했다. API message 대신 code로 UI 사전 문구를 고른다. API 계약의 익명 display 및 퍼즐 내용은 그대로 표시한다. |
| pytest 렌더 테스트 + 요구된 수동 체크리스트 | 충족 | 렌더·사전·실행 테스트와 README의 언어 전환/새 탭/자정/계정/백업 항목이 있다. 새 본문 지연 테스트는 실제 Response/ReadableStream을 사용한다. 다만 선호 저장까지 모델링한 중복 PATCH 경합은 검증하지 않는다(D-17-5). |

### 직접 실행한 검증

- 기존 로컬 `chosung_daily_test_t17`과 Redis DB 5를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. 접속 자격 증명은 기록하지 않는다. 새 DB를 만들거나 기본 테스트 DB로 대체하지 않았다. 마이그레이션 테스트에는 기존 파생 DB `chosung_daily_test_t17_migrations`가 사용된다.
- 전체 `uv run pytest -q` 첫 실행은 진행 중 exit 143(SIGTERM)으로 종료됐다. 완료 요약이나 assertion 실패는 나오지 않았으며 종료 원인은 확인하지 못했다. 같은 머신의 다른 워크트리 pytest 실행은 관찰했지만 그것이 종료 원인이라고 단정하지 않는다. 전체 실행을 한 번 재시도했으나 두 번째도 exit 143으로 종료되어 전체 통과 여부는 증거 부족이다. 아래 130개 관련 테스트는 별도 실행으로 끝까지 통과했다.
- `uv run pytest tests/test_web.py tests/test_web_js.py tests/test_ui_strings.py tests/test_ui_language.py tests/test_token_css.py -q`: `130 passed in 18.26s`, exit 0.
- 별도 `uv run pytest tests/test_web_js.py tests/test_ui_strings.py -q`: `32 passed in 0.53s`, exit 0. Node 실행 테스트는 skip되지 않았다.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `uv run flask db heads`: `dae1b5af0cf7 (head)` 한 줄, exit 0. 티켓 17 자체 마이그레이션 변경은 없다.
- `git diff --check main...HEAD`: 출력 없음, exit 0.
- 실제 번들에 대한 별도 Node assertion: mask r/h/s, 서버 이력의 구분자 재삽입, history만 삭제, 토큰/기타 키 보존, is_me/me, 정규화·puzzle_id, 409 뒤 안내, 순위·통계 언어 URL 모두 통과.

### 이전 결함 재판정

| ID | 판정 | 위치 및 재현 → 기대/실제 |
|---|---|---|
| D-17-1 (이전 MAJOR) | FIXED | `web/static/app.js:469`, `:475`: ko 제출 보류 → en → ko 서버 이력 복원 → 옛 제출 응답. 회귀 테스트의 기대/실제 모두 attempts 1행·남은 기회 4이며 단방향 정답/오답과 전환 없는 대조군도 통과. |
| D-17-2 (이전 MAJOR) | FIXED | `web/static/app.js:24`, `:34`, `:487`: en UI의 validation/완료/rate limit/인증/미등록 오류 및 today 없음 실행. 기대/실제 모두 영어 사전 문구이며 서버 한국어 message가 노출되지 않는다. |
| D-17-3 (이전 MAJOR) | FIXED | `web/static/app.js:169`, `:190`: ko stats 응답 보류 → en 전환 → 옛 stats 응답. 기대/실제 모두 en 칩·ID 2 유지, `ab` 정규화는 `AB`, 다음 ko 클릭은 실제 요청을 보낸다. 게스트 요약은 계속 갱신한다. |
| D-17-4 (이전 MAJOR) | FIXED | `web/static/app.js:87`, `:94`, `:155`, `:230`, `:522`, `:573`: 이전 리뷰의 독립 명령을 그대로 추출해 Node에서 다시 실행했다. today·순위·통계 본문 보류 → en 전환 → ko 본문 도착 후 모두 ID 2/en 및 빈 순위/통계 유지. 여섯 요청의 본문 지연, 반대 방향, 정상 대조군, 비 JSON 본문 테스트도 통과했다. |

D-17-4 독립 명령의 이번 출력(exit 0):

```text
today {"id":2,"language":"en"}  empty
leaderboard {"id":2,"language":"en"}  empty
stats {"id":2,"language":"en"}  empty
```

### 신규 결함

#### D-17-5 — MAJOR — 중복 언어 PATCH가 뒤늦게 저장되면 마지막 선택과 서버 선호가 갈린다

- 위치: `web/static/app.js:227`–`:244`, 특히 요청을 동시에 허용하는 `:230`과 오래된 쓰기 응답을 버리는 `:237`. 서버 계약 근거는 `app/services/guest_service.py:21`–`:28`(요청 값을 저장하고 커밋), 다음 제출의 근거는 `app/services/guess_service.py:45`–`:50`(현재 선호의 퍼즐과 ID 비교)다.
- 재현 입력/순서: ko 화면 → English를 두 번 클릭하여 PATCH A/B를 보낸다(아직 칩이 ko라 두 요청 모두 허용됨) → A는 서버 처리 전 지연시키고 B만 처리해 en 전환을 완료한다 → 한국어 클릭의 PATCH C와 ko 조회를 완료한다 → 남아 있던 A를 처리한다. 이는 **본문 도착만** 늦추는 D-17-4와 달리 서버에 적용되는 쓰기의 순서가 B→C→A인 경우다.
- 기대: 마지막으로 완료한 한국어 선택이 화면과 서버 선호에 유지되며, 다음 한국어 답 제출은 그 퍼즐에 적용된다.
- 실제: A가 서버 선호를 en으로 저장하지만 `stale` 때문에 응답을 통째로 무시한다. 화면은 ko/ID 1, 서버는 en으로 갈린다. 다음 제출은 409이고 재조회로 en/ID 2가 나타나 마지막 선택이 취소된다. 새 탭/새로고침도 en 선호를 읽는다. 시도/정답 기록의 손상은 확인되지 않았지만 퍼즐 선택이라는 핵심 기능과 저장된 선호가 잘못된다.
- 원인: 조회 응답의 폐기와 쓰기 요청의 취소는 다르다. 현재 세대 검사는 DOM 반영만 막고, 이미 보낸 PATCH의 뒤늦은 커밋을 막거나 마지막 선택으로 수렴시키지 않는다.
- 검증 범위: 실제 번들을 Node로 실행하고 fetch 경계에 서버 선호 변수 및 PATCH 적용 순서를 제공했다. 서버가 단순 대입·커밋하고 today/제출은 현재 선호를 사용한다는 점은 서버 코드를 직접 확인했다. 실제 네트워크/DB 경합을 실행한 결과라고 주장하지 않는다.
- 기존 회귀 테스트의 한계: `serveSwitch(puzzle)`은 today를 고정된 puzzle로 반환하고 PATCH는 요청 언어를 반환할 뿐 지속적인 서버 선호를 모델링하지 않는다. `late_patch_body` 역시 지연된 쓰기가 서버에 무엇을 저장했는지 검증하지 않는다. 따라서 D-17-4 FIXED와 이 결함은 양립한다.

재현 명령(파일 변경·외부 호출 없음):

```sh
node --input-type=module <<'JS'
import {loadApp,okResponse,errorResponse} from './tests/js/harness.mjs';
const strings={attempts_left:'{left}/{max}',category_general:'General',
  length_caption:'{length}',hint:'{hint}',leaderboard_empty:'empty',
  my_rank_unsolved:'none',stats_empty:'empty',puzzle_changed:'new puzzle'};
const ko={puzzle_id:1,language:'ko',date:'2026-10-14',category:'general',
  length:2,mask:[{t:'r',c:'ㅅ'},{t:'r',c:'ㄱ'}],attempts:[],
  attempts_left:5,status:'in_progress',hint:null};
const en={...ko,puzzle_id:2,language:'en',mask:[{t:'h',c:''},{t:'r',c:'B'}]};
const app=loadApp({strings});app.run(`applyPuzzle(${JSON.stringify(ko)})`);
let preference='ko', patches=0, releaseFirst;
const commits=[];
app.setFetch(async(url,options)=>{
  if(options?.method==='PATCH'){
    const language=JSON.parse(options.body).puzzle_language;
    if(++patches===1) await new Promise(resolve=>{releaseFirst=resolve});
    preference=language;commits.push(language);
    return okResponse({puzzle_language:language});
  }
  if(url.endsWith('/guesses')){
    const expectedId=preference==='ko'?1:2;
    if(JSON.parse(options.body).puzzle_id!==expectedId)
      return errorResponse(409,{code:'PUZZLE_CHANGED'});
    return okResponse({is_correct:false,feedback:[true,false],attempts_left:4});
  }
  if(url.endsWith('/puzzles/today'))
    return okResponse(structuredClone(preference==='ko'?ko:en));
  if(url.includes('leaderboard'))return okResponse({entries:[],me:null});
  return okResponse({total_solved:0,by_attempt:{}});
});
const first=app.run('handleLanguageChange("en")');
await app.run('handleLanguageChange("en")');
await app.run('handleLanguageChange("ko")');
releaseFirst();await first;
console.log('after last ko click',JSON.stringify({server:preference,commits}),
  app.run('JSON.stringify({language:state.puzzleLanguage,id:state.puzzleId})'));
await app.run('submitGuess(document.getElementById("guess-input"), "사과")');
console.log('after next submit',
  app.run('JSON.stringify({language:state.puzzleLanguage,id:state.puzzleId})'),
  app.el('message').textContent);
JS
```

실제 출력:

```text
after last ko click {"server":"en","commits":["en","ko","en"]} {"language":"ko","id":1}
after next submit {"language":"en","id":2} new puzzle
```

### 보안·공유 파일·범위 및 참고

- 변경 경로의 사용자/서버 문자열은 `textContent`, 사전 JSON은 Jinja `tojson`으로 출력한다. `innerHTML`은 컨테이너 비우기뿐이다. 인증·CSRF 가드 제거, 서버 입력 검증 제거, 실제 시크릿 신규 기록은 발견하지 않았다. 리뷰 문서에 키·토큰·비밀번호를 기록하지 않았다.
- README 설계 판단은 `### 17.` 소제목들만 추가했고 수동 체크리스트는 티켓의 명시 요구다. 스펙 변경도 티켓 17의 미정 13 확정 행뿐이다. 타 티켓 본문·`.env.example`·릴리스 문서·스키마는 변경하지 않았다.
- JS 테스트는 실제 번들을 읽어 실행하며, 본문 지연 테스트도 구현 복제나 항상 통과하는 mock은 아니다. 문자열 존재 테스트와 Node DOM 대역만으로 브라우저의 레이아웃·실제 HTTP 왕복까지 증명되지는 않는다.
- 브라우저 레이아웃·`impeccable detect`는 이번에 재실행하지 않았다. 기존 페이지 토큰 전환·다크모드·아이콘·로딩/오프라인 상태 등 티켓 18 범위는 이번 결함 수에 포함하지 않았다. 취향·스타일 제안은 없다.
- 활성 결함: BLOCKER 0 / MAJOR 1 / MINOR 0. D-17-1·2·3·4는 FIXED, D-17-5는 신규이며 중복 PATCH의 처리 순서에 대한 수정·검증이 남는다.

판정: FAIL

## 라운드 5

### 범위와 기준

- 로컬 `main` = `7df7809`, 구현 HEAD = `65b9538`. `git log main..HEAD`의 17개 커밋과 `git diff main...HEAD`의 21개 파일을 검토했다. `origin/main`은 사용하지 않았다.
- 티켓 17의 6개 체크박스, 스펙 §A.16·A'·미정 13, CONTEXT, SCREENS, MASTER 및 우선하는 OVERRIDES를 대조했다. 이전 라운드와 구현 증거의 수정 라운드 4 주장을 직접 검증했다.
- 코디네이터의 마지막 라운드 메모에 따라 D-17-5와 티켓 14 rebase 충돌 해결을 우선 확인했다. 두 기기·두 탭의 동시 전환은 범위 밖이다. 새로 발견한 단일 탭 경합은 아래에 **알려진 한계 후보**로 분리했다. 후보 표시는 수용 확정이나 심각도 면제를 뜻하지 않는다.
- 앱·테스트·설정·`.scratch/` 수정, 하위 에이전트, 프로덕션 접근, 배포, 실제 외부 서비스 호출 없이 이 리뷰 파일만 변경했다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 언어 칩 → PATCH /me → today 재조회, mask r/h/s 렌더 | 미충족 | 정상 전환과 중복 쓰기 직렬화는 통과(D-17-5 FIXED). 별도 번들 assertion으로 r/h/s 렌더도 확인했다. 다만 쓰기 도중 409 재조회가 겹치면 대기 중인 마지막 선택을 잃는다(D-17-6). |
| 서버 attempts 복원, history만 삭제, 토큰·백업 패널 유지, en 간격 재삽입·미정 13 기록 | 충족 | 실제 번들 실행에서 서버 `AB` 이력을 `A B`로 복원하고 history 키만 삭제하며 토큰·기타 키를 유지했다. 백업/복원 템플릿과 스펙의 티켓 17 확정 행도 유지된다. |
| puzzle_id 동봉, 409 안내·재조회, 언어·계정·백업 전환 시 로컬 상태 폐기 | 충족 | 실제 제출 본문의 ID·정규화된 guess, 409 뒤 서버 이력 복원·인라인 안내를 assertion으로 확인했다. 계정 콜백의 history 정리, 백업 복원의 폐기·페이지 재시작도 유지된다. 409와 대기 선택의 결합 문제는 D-17-6으로 별도 기록한다. |
| 리더보드 entries.display/is_me/me, 통계 language 명시 | 충족 | 실제 번들에서 `is-me` 행과 목록 밖 21위 `me` 표시, 순위·통계의 `language=en` URL을 확인했다. |
| UI ko/en 사전, 기기 언어와 퍼즐 언어 분리, 기존 문구 사전 이동 | 충족 | 공용 `_requested_ui_language()`와 별도 퍼즐 선호를 유지한다. 사전·오류 실행 테스트가 통과하고 새 `account_deleted` 안내도 ko/en 사전을 실제로 사용한다. |
| pytest 렌더 테스트 + 요구된 수동 체크리스트 | 충족 | 렌더·사전·JS 실행 테스트와 README의 언어/새 탭/자정/계정/백업 체크리스트가 존재한다. 중복 쓰기 테스트는 서버 선호를 모델링하므로 항상 통과하는 대역은 아니다. 409와 대기 쓰기 조합은 누락되어 있다(D-17-6). |

### 직접 실행한 검증

- 기존 로컬 `chosung_daily_test_t17` 및 Redis DB 5를 `TEST_DATABASE_URL` / `TEST_REDIS_URL`로 지정했다. 접속 성공하여 기본 테스트 DB로 대체하지 않았다. 새 DB 생성 없이 마이그레이션 테스트도 기존 파생 DB `chosung_daily_test_t17_migrations`를 사용한다. URL의 자격 증명은 기록하지 않는다.
- 전체 `uv run pytest -q`: `859 passed in 592.32s (0:09:52)`, exit 0. 첫 실행에서 모두 통과하여 재실행하지 않았다.
- `uv run pytest tests/test_web_js.py tests/test_ui_strings.py -q`: `37 passed in 0.28s`, exit 0. DB를 사용하지 않는 두 모듈만 전체 테스트와 별도로 실행했으며 Node skip은 없었다.
- `uv run ruff check .`: `All checks passed!`, exit 0.
- `uv run flask db heads`: `94a83f12fddb (head)` 한 줄, exit 0. 티켓 17 자체의 마이그레이션 변경은 없다.
- `git diff --check main...HEAD`: 출력 없음, exit 0.
- 별도 실제 번들 assertion: mask r/h/s, 서버 attempts의 s 간격 복원, history만 제거, 토큰/기타 키 보존, is_me/me, 정규화·puzzle_id, 409 뒤 안내, 순위·통계 언어 URL 모두 통과.

### 이전 결함 재판정

| ID | 판정 | 위치 및 재현 → 기대/실제 |
|---|---|---|
| D-17-1 (이전 MAJOR) | FIXED | `web/static/app.js:519`, `:526`: ko 제출 응답 보류 → en → ko 복원 → 옛 응답. 회귀 테스트에서 기대/실제 모두 1행·남은 기회 4 유지. 단방향 정답/오답·정상 대조군도 통과. |
| D-17-2 (이전 MAJOR) | FIXED | `web/static/app.js:24`, `:34`, `:538`: en UI에서 validation/완료/rate limit/인증/미등록 code/today 없음. 기대/실제 모두 영어 사전 문구이며 한국어 API message를 출력하지 않는다. |
| D-17-3 (이전 MAJOR) | FIXED | `web/static/app.js:185`, `:206`: ko stats 보류 → en 전환 → 옛 stats 응답. 기대/실제 모두 en 칩·ID 2·대문자 정규화 유지, 다음 ko 클릭도 요청 발생. 게스트 요약은 갱신된다. |
| D-17-4 (이전 MAJOR) | FIXED | `web/static/app.js:99`, `:105`, `:175`, `:262`, `:581`, `:629`: 본문 수신 중 전환하는 여섯 요청 회귀 및 반대 방향·정상 대조군·비 JSON 본문 테스트 통과. 폐기한 본문으로 현재 화면을 덮지 않는다. 아래 D-17-6은 본문 반영 문제가 아니라 대기한 쓰기의 취소다. |
| D-17-5 (이전 MAJOR) | FIXED | `web/static/app.js:252`, `:274`: 라운드 4의 원문 Node 명령을 그대로 추출해 실행했다. 기대/실제 모두 마지막 ko 선택이 서버·화면에 남고 commits는 `[en,ko]`, 다음 제출도 409 없이 ko 유지. 동일 칩 중복·쓰기 중 반대 선택·정상 대조군 회귀 테스트도 통과. |

D-17-5 독립 재현 출력(exit 0):

```text
after last ko click {"server":"ko","commits":["en","ko"]} {"language":"ko","id":1}
after next submit {"language":"ko","id":1}
```

### 티켓 14 rebase 충돌 검토

- `app/web.py:175`의 기존 `_requested_ui_language()`를 재사용하며, main 대비 삭제 GET/POST·CSRF·삭제 서비스의 변경은 없다. index에만 사전·언어 응답 헤더가 추가됐다.
- `web/static/app.js:789`의 삭제 신호 처리는 main과 같이 401 확인 후에만 토큰을 제거한다. `init()` 첫 단계 호출도 유지된다. history 삭제 루프를 공용 함수로 합쳤지만 접두사·예외 처리·토큰 확인 순서는 유지됐다.
- `tests/fixtures/js/deleted_state_harness.mjs`를 진짜 ko/en 사전으로 각각 실행했다. 삭제된 토큰: 토큰·history 제거/새 게스트 발급/신호 제거. 살아 있는 토큰: 토큰 유지/새 게스트 미발급/신호 제거. 확인 불가: 토큰 유지/새 게스트 미발급/신호 유지. 두 언어 모두 같은 결과였다.
- 영어 삭제 안내는 `Your account and records were deleted. Starting fresh.`였다. `app/utils/ui_strings.py:58`, `:122`와 실제 호출 `app.js:808`을 대조했다. 기존 테스트의 시나리오·assertion은 유지되고, 대역의 변경은 JSON 사전·문서 언어 및 Storage 열거 동작 제공이다.

### 신규 결함 — 알려진 한계 후보

#### D-17-6 — MAJOR — 409 재조회가 진행 중인 언어 쓰기를 폐기하며 마지막 선택도 잃는다

- 위치: `web/static/app.js:262` (`stale`이면 쓰기 루프 종료), `:290` (대기 선택을 무조건 null로 초기화), 관련 `:532`의 409 재조회 및 `:440`의 generation 증가.
- 재현: **한 탭**의 ko 퍼즐에서 English 클릭 → 서버에는 en 저장 완료, PATCH 응답 본문만 지연 → 한국어 클릭(대기 선택 ko) → 여전히 보이는 ko 입력창에서 제출 → 서버 선호 en과 ID가 달라 409 → en today 재조회 완료 → 지연한 PATCH 본문 도착.
- 기대: 같은 게스트의 409 재조회가 새로 대기시킨 한국어 선택을 취소하지 않고, 쓰기 완료 뒤 마지막 선택 ko가 서버·화면에 남는다.
- 실제: 409가 generation을 올려 첫 PATCH를 stale로 만든다. `drainLanguageWrites()`가 대기한 ko 쓰기를 보내기 전에 반환하고 `finally`가 선택을 지운다. 서버·화면은 en/ID 2로 남으며 새 탭도 en을 받는다. 한국어 칩을 다시 클릭하면 복구된다.
- 원인: 계정 변경으로 더 이상 적용하면 안 되는 작업과, 같은 게스트의 409로 보드만 다시 읽는 작업을 같은 generation 취소 규칙으로 처리한다. 직렬화 자체는 정상이나, 이미 수용한 대기 선택이 그 취소에 함께 포함된다.
- D-17-5와 구분: 기존 중복 PATCH의 서버 커밋 역전은 해결됐다. 이번에는 중복 요청도 역전도 없고, 새 큐가 409 때문에 마지막 쓰기를 실행하지 않는 별도 조합이다. `concurrent_language_writes.mjs`는 전환 **완료 후** 제출만 검증하고, `late_patch_body`는 대기 선택·지속하는 서버 선호를 검증하지 않는다.
- 영향/심각도: 퍼즐 선택·저장된 선호가 마지막 입력과 달라지는 핵심 동작 누락이므로 MAJOR로 분류한다. 시도 소비·정답 기록 손상·인증 우회는 확인되지 않았다. 느린 PATCH 본문과 전환 중 제출이 함께 필요하며 재클릭으로 복구 가능한 **알려진 한계 후보**다. 두 탭/두 기기 동시 전환은 재현에 필요 없다.
- 검증 한계: 실제 번들을 실행하고 DOM·fetch 경계만 대역으로 제공했다. PATCH의 선호 저장 및 제출 ID 불일치 409 계약은 `app/services/guest_service.py:21`, `app/services/guess_service.py:45`에서 직접 확인했다. 본문 지연에는 실제 `Response`/`ReadableStream`을 사용했다. 실브라우저·실DB의 네트워크 경합 재현이라고 주장하지 않는다.

독립 재현 명령(저장소 파일 변경·외부 호출 없음, 마지막 선택은 두 경우 모두 ko):

```sh
node --input-type=module <<'JS'
import {loadApp,okResponse,errorResponse,heldBodyResponse} from './tests/js/harness.mjs';
const strings={attempts_left:'{left}/{max}',category_general:'General',
  length_caption:'{length}',hint:'{hint}',leaderboard_empty:'empty',
  my_rank_unsolved:'none',stats_empty:'empty',puzzle_changed:'new puzzle'};
const ko={puzzle_id:1,language:'ko',date:'2026-10-14',category:'general',
  length:2,mask:[{t:'r',c:'ㅅ'},{t:'r',c:'ㄱ'}],attempts:[],
  attempts_left:5,status:'in_progress',hint:null};
const en={...ko,puzzle_id:2,language:'en',mask:[{t:'h',c:''},{t:'r',c:'B'}]};
for(const submitDuringWrite of [false,true]){
  const app=loadApp({strings});app.run(`applyPuzzle(${JSON.stringify(ko)})`);
  let preference='ko';const commits=[];
  const held=heldBodyResponse({puzzle_language:'en'});
  app.setFetch(async(url,options)=>{
    if(options?.method==='PATCH'){
      preference=JSON.parse(options.body).puzzle_language;commits.push(preference);
      return commits.length===1?held.response:okResponse({puzzle_language:preference});
    }
    if(url.endsWith('/guesses')){
      const expectedId=preference==='ko'?1:2;
      return JSON.parse(options.body).puzzle_id!==expectedId
        ?errorResponse(409,{code:'PUZZLE_CHANGED'})
        :okResponse({is_correct:false,feedback:[true,false],attempts_left:4});
    }
    if(url.endsWith('/puzzles/today'))
      return okResponse(structuredClone(preference==='ko'?ko:en));
    if(url.includes('leaderboard'))return okResponse({entries:[],me:null});
    return okResponse({total_solved:0,by_attempt:{}});
  });
  const first=app.run('handleLanguageChange("en")');
  await app.run('handleLanguageChange("ko")');
  if(submitDuringWrite)
    await app.run('submitGuess(document.getElementById("guess-input"),"사과")');
  held.send();await first;
  console.log(JSON.stringify({submitDuringWrite,lastClick:'ko',server:preference,
    commits,...JSON.parse(app.run('JSON.stringify({language:state.puzzleLanguage,id:state.puzzleId,wanted:state.languageWanted})'))}));
}
JS
```

직접 실행 출력(exit 0, 제출 유무 하나만 다른 대조군):

```text
{"submitDuringWrite":false,"lastClick":"ko","server":"ko","commits":["en","ko"],"language":"ko","id":1,"wanted":null}
{"submitDuringWrite":true,"lastClick":"ko","server":"en","commits":["en"],"language":"en","id":2,"wanted":null}
```

### 보안·공유 파일·범위 및 참고

- 변경된 렌더 경로는 `textContent`, 사전은 Jinja `tojson`을 사용한다. `innerHTML`은 비우기뿐이다. 인증·CSRF·입력 검증의 제거, 시도/정답 기록 손상, 실제 키·토큰·비밀번호의 신규 파일 기록은 발견하지 않았다.
- README 설계 판단은 자기 `### 17.` 소제목만 추가했고 수동 체크리스트는 티켓 요구다. 스펙도 자기 미정 13 확정 행만 추가했다. `.env.example`·릴리스 문서·다른 티켓 본문·스키마 변경은 없다.
- JS 실행 테스트와 대조군은 실제 번들을 사용한다. 다만 문자열 검사와 Node DOM 대역은 브라우저 레이아웃·네트워크 전체를 증명하지 않는다. 이번 리뷰에서는 브라우저 및 `impeccable detect`를 재실행하지 않았다.
- 기존 스타일·다크모드·아이콘·로딩/오프라인 및 섹션 전환 디자인은 합의된 티켓 18 범위로 유지한다. 취향·스타일 제안은 결함에 포함하지 않았다.
- 활성 결함: BLOCKER 0 / MAJOR 1 / MINOR 0. D-17-1~5는 FIXED, D-17-6은 신규 알려진 한계 후보이며 수용 확정 전에는 아래 판정 규칙상 FAIL이다.

판정: FAIL
