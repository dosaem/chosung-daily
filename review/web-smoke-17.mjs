// 최소 CDP 드라이버: 헤드리스 크롬에 붙어 JS 를 평가한다.
const base = process.argv[2];           // http://127.0.0.1:9222
const url = process.argv[3];

const targets = await (await fetch(`${base}/json/list`)).json();
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();

ws.addEventListener("message", (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
await new Promise((r) => ws.addEventListener("open", r));

function send(method, params = {}) {
  const myId = ++id;
  return new Promise((resolve) => {
    pending.set(myId, resolve);
    ws.send(JSON.stringify({ id: myId, method, params }));
  });
}

async function evaluate(expression) {
  const res = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (res.result?.exceptionDetails) throw new Error(JSON.stringify(res.result.exceptionDetails));
  return res.result?.result?.value;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await send("Page.enable");
// 새 방문자로 시작한다 — 저장된 토큰이 있으면 그 게스트로 이어진다.
await send("Page.navigate", { url });
await sleep(1500);
await evaluate("localStorage.clear()");
await send("Page.navigate", { url });
await sleep(2500);

console.log("[1] 처음 상태");
console.log("  lang=", await evaluate("document.documentElement.lang"));
console.log("  chips=", JSON.stringify(await evaluate(
  "[...document.querySelectorAll('[data-puzzle-language]')].map(c=>c.dataset.puzzleLanguage+':'+c.getAttribute('aria-pressed'))"
)));
console.log("  mask=", await evaluate("document.getElementById('mask-row').innerText.replace(/\\n/g,'')"));
console.log("  caption=", await evaluate("document.getElementById('length-caption').textContent"));

console.log("[2] 퍼즐 언어 칩 'en' 클릭 → PATCH /me → 재조회");
await evaluate("document.querySelector('[data-puzzle-language=\"en\"]').click()");
await sleep(2000);
console.log("  chips=", JSON.stringify(await evaluate(
  "[...document.querySelectorAll('[data-puzzle-language]')].map(c=>c.dataset.puzzleLanguage+':'+c.getAttribute('aria-pressed'))"
)));
console.log("  mask=", await evaluate("document.getElementById('mask-row').innerText.replace(/\\n/g,'')"));
console.log("  caption=", await evaluate("document.getElementById('length-caption').textContent"));
console.log("  board rows=", await evaluate("document.getElementById('board').children.length"));
console.log("  puzzle_language on server=", await evaluate(
  "(async()=>(await (await fetch('/api/v1/me/stats',{headers:{Authorization:'Bearer '+localStorage.getItem('chosung_token')}})).json()).puzzle_language)()"
));

console.log("[3] 오답 1회 제출");
await evaluate("document.getElementById('guess-input').value='harry pitter'");
await evaluate("document.getElementById('guess-form').dispatchEvent(new Event('submit',{cancelable:true}))");
await sleep(2000);
console.log("  board=", await evaluate("document.getElementById('board').innerText.replace(/\\n/g,'')"));
console.log("  attempts-left=", await evaluate("document.getElementById('attempts-left').textContent"));

console.log("[4] puzzle_id 를 낡은 값으로 바꿔 409 PUZZLE_CHANGED 유도");
await evaluate("state.puzzleId = 999999");
await evaluate("document.getElementById('guess-input').value='harry potter'");
await evaluate("document.getElementById('guess-form').dispatchEvent(new Event('submit',{cancelable:true}))");
await sleep(2500);
console.log("  message=", await evaluate("document.getElementById('message').textContent"));
console.log("  puzzleId 복구=", await evaluate("state.puzzleId"));
console.log("  attempts-left(안 깎임)=", await evaluate("document.getElementById('attempts-left').textContent"));
console.log("  board rows(서버 이력으로 복원)=", await evaluate("document.getElementById('board').children.length"));

console.log("[5] 옛 localStorage history 키 제거 확인");
await evaluate("localStorage.setItem('chosung_history_2026-10-14','[]')");
await evaluate("clearStoredHistory()");
console.log("  남은 history 키=", await evaluate(
  "Object.keys(localStorage).filter(k=>k.startsWith('chosung_history_')).length"
));
console.log("  토큰은 유지=", await evaluate("!!localStorage.getItem('chosung_token')"));

console.log("[6] 콘솔 에러 없음 확인용 정답 제출 + 리더보드");
await evaluate("document.getElementById('guess-input').value='harry potter'");
await evaluate("document.getElementById('guess-form').dispatchEvent(new Event('submit',{cancelable:true}))");
await sleep(2500);
console.log("  result=", await evaluate("document.getElementById('result-text').textContent"));
console.log("  my-rank=", await evaluate("document.getElementById('my-rank').textContent"));
console.log("  leaderboard=", await evaluate("document.getElementById('leaderboard-entries').innerText.replace(/\\n/g,' | ')"));
console.log("  stats=", await evaluate("document.getElementById('today-stats').innerText.replace(/\\n/g,' | ')"));
console.log("  share=", JSON.stringify(await evaluate("buildShareText()")));

ws.close();

// 사용법 (티켓 17 증거 재현):
//   1) 전용 DB/Redis 로 개발 서버: DATABASE_URL=...chosung_daily_web_t17 REDIS_URL=redis://127.0.0.1:6379/6 \
//        FLASK_APP=wsgi.py FLASK_ENV=development uv run flask run --port 8017
//      (flask db upgrade → seed-words → schedule-puzzles --language ko|en 로 ko/en 퍼즐 1개씩)
//   2) 헤드리스 크롬: "Google Chrome" --headless=new --remote-debugging-port=9222 \
//        --lang=ko-KR --accept-lang=ko-KR,ko --user-data-dir=<임시> about:blank
//   3) node review/web-smoke-17.mjs http://127.0.0.1:9222 http://127.0.0.1:8017/
//
// CI 에는 안 들어간다(스펙 "미정 항목" 5: Playwright 보류). README "웹 수동
// 체크리스트" 를 손으로 밟는 대신 쓰는 보조 도구다.
