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
