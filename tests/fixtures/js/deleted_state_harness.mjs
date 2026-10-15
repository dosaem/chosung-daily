// `web/static/app.js` 를 Node `vm` 에서 **그대로** 실행해서 "삭제 신호를 받은
// 브라우저" 한 바퀴를 재현한다. 레포에 JS 테스트 러너가 없어서 번들 문자열만
// 확인했더니, `?deleted` 가 붙은 아무 링크로도 토큰이 지워지는 결함(D-14-1)을
// 놓쳤다 — 그래서 문자열이 아니라 동작을 본다.
//
// 대역은 브라우저 바깥(localStorage·DOM·fetch·location)뿐이다. app.js 는 한 줄도
// 고치지 않고, 파일 끝의 자동 `init()` 호출만 떼어낸다(DOM 전체가 필요해진다).
//
// 사용법: node deleted_state_harness.mjs <시나리오> <UI문구사전 JSON> [steps|init]
//         → 결과 JSON 을 stdout 으로.
//
// 모드 두 가지:
//   steps (기본) — `discardDeletedAccountState()` → `ensureToken()` 만 부른다.
//                  토큰을 버리는 판단 자체를 본다.
//   init         — 파일 끝의 그 `init()` 을 통째로 돌린다. **순서**를 본다 —
//                  삭제 안내가 뒤따르는 `restart()` 에 지워지던 결함(D-42-3)은
//                  조각을 따로 부르면 안 보인다.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createContext, runInContext } from "node:vm";

const HERE = dirname(fileURLToPath(import.meta.url));
const APP_JS = resolve(HERE, "../../../web/static/app.js");

const TOKEN_KEY = "chosung_token";
const STORED_TOKEN = "stored-guest-token";
const HISTORY_KEY = "chosung_history_2026-10-14";
const NEW_TOKEN = "brand-new-guest-token";

// 시나리오 = "저장된 토큰을 서버에 물어봤을 때 돌아오는 답".
const SCENARIOS = {
  // 삭제가 정말 끝났다 — 옛 토큰은 더 이상 인증되지 않는다.
  "token-is-dead": { probeStatus: 401 },
  // 토큰이 아직 살아 있다(= 외부 링크로 들어온 가짜 신호).
  "token-is-alive": { probeStatus: 200 },
  // 확인 자체를 못 했다(오프라인).
  "probe-unreachable": { probeStatus: null },
};

const scenario = SCENARIOS[process.argv[2]];
if (!scenario) throw new Error(`알 수 없는 시나리오: ${process.argv[2]}`);

const mode = process.argv[4] ?? "steps";
if (mode !== "steps" && mode !== "init") throw new Error(`알 수 없는 모드: ${mode}`);

// 티켓 17 부터 app.js 는 로드 시점에 `#ui-strings` 의 인라인 JSON 을 읽어 문구
// 사전을 만든다 — 대역이 그걸 안 주면 번들이 뜨다가 죽는다. 사전은 파이썬 쪽
// 진짜 UI_STRINGS 를 그대로 넘겨받는다(tests/test_web.py).
const UI_STRINGS = JSON.parse(process.argv[3]);

// 브라우저 localStorage 는 표준 API(length·key·getItem…)와 **열거 가능한 자기
// 키**를 둘 다 노출한다 — `Object.keys(localStorage)` 가 그래서 동작하고, 티켓 17
// 의 `clearStoredHistory` 가 그 방식을 쓴다. 대역도 둘 다 갖춘다.
function makeStorage(entries) {
  const store = { ...entries };
  const define = (name, value) =>
    Object.defineProperty(store, name, { value, enumerable: false, configurable: true });
  Object.defineProperty(store, "length", {
    get: () => Object.keys(store).length,
    enumerable: false,
  });
  define("key", (index) => Object.keys(store)[index] ?? null);
  define("getItem", (key) => (key in store ? store[key] : null));
  define("setItem", (key, value) => {
    store[key] = String(value);
  });
  define("removeItem", (key) => {
    delete store[key];
  });
  define("snapshot", () => ({ ...store }));
  return store;
}

const localStorage = makeStorage({ [TOKEN_KEY]: STORED_TOKEN, [HISTORY_KEY]: '[{"guess":"사과"}]' });
const requests = [];
const messages = [];
const urls = [];

const location = { pathname: "/", search: "?deleted=1", reload() {} };
const history = {
  replaceState(_state, _title, url) {
    urls.push(url);
    const [pathname, search] = url.split("?");
    location.pathname = pathname;
    location.search = search ? `?${search}` : "";
  },
};
const element = {
  textContent: "",
  value: "",
  classList: { add() {}, remove() {} },
  addEventListener() {},
  appendChild() {},
};
const document = {
  // 티켓 17 의 ensureToken 은 새 게스트의 퍼즐 언어 기본값으로 기기 언어를 보낸다.
  documentElement: { lang: "ko" },
  getElementById(id) {
    if (id === "ui-strings") return { ...element, textContent: JSON.stringify(UI_STRINGS) };
    return {
      ...element,
      set textContent(text) {
        if (id === "message") messages.push(text);
      },
      get textContent() {
        return "";
      },
    };
  },
  // init 모드가 `bindEvents()`·섹션 토글·언어 칩까지 돈다 — 이 대역에는 그 마크업이
  // 없으니 빈 목록이다. 우리가 보는 건 DOM 이 아니라 호출 **순서**다.
  querySelectorAll: () => [],
  createElement: () => ({ ...element }),
};
const window = { addEventListener() {} };

// init 모드가 `restart()` 까지 도는 바람에 첫 화면 한 벌(`/me/stats`·`/puzzles/today`·
// 순위·오늘 통계)이 실제로 조회된다. 비어 있는 응답을 주면 렌더가 터져서 이 하네스가
// 보려는 **순서**에 닿지 못하므로, 모양만 맞는 최소 응답을 돌려준다. 값은 아무 뜻이 없다.
const PUZZLE = {
  date: "2026-10-16",
  puzzle_id: 1,
  language: "ko",
  category: "general",
  mask: [{ t: "h" }, { t: "h" }],
  length: 2,
  attempts: [],
  status: "in_progress",
  hint: null,
};
const STATS = { current_streak: 0, max_streak: 0, solved_count: 0, linked_account: null, puzzle_language: "ko" };

async function fetchStub(url, options = {}) {
  const method = (options.method ?? "GET").toUpperCase();
  requests.push({ method, url, headers: options.headers ?? null });

  if (method === "POST" && url.endsWith("/guests")) {
    return jsonResponse(200, { token: NEW_TOKEN });
  }
  // `guestTokenIsGone` 의 확인 조회(`/me/history?days=1`)와 첫 화면 조회가 같은
  // 시나리오 상태를 따른다 — 토큰이 죽었으면 전부 401 이다.
  if (scenario.probeStatus === null) throw new TypeError("network error");
  if (scenario.probeStatus !== 200) {
    return jsonResponse(scenario.probeStatus, { code: "UNAUTHORIZED" });
  }
  if (url.includes("/puzzles/today/leaderboard")) return jsonResponse(200, { entries: [], me: null });
  if (url.includes("/puzzles/today/stats")) return jsonResponse(200, { total_solved: 0, by_attempt: {} });
  if (url.includes("/puzzles/today")) return jsonResponse(200, PUZZLE);
  if (url.includes("/me/stats")) return jsonResponse(200, STATS);
  return jsonResponse(200, []);
}

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
  };
}

const source = readFileSync(APP_JS, "utf8").replace(/\binit\(\);\s*$/, "");
const context = createContext({
  localStorage,
  document,
  location,
  history,
  fetch: fetchStub,
  console,
  URLSearchParams,
  URL,
  setTimeout,
  clearTimeout,
  navigator: { onLine: true, clipboard: { writeText: async () => {} } },
  window,
  setInterval,
  clearInterval,
  JSON,
  Promise,
  Error,
  TypeError,
});
runInContext(source, context, { filename: "app.js" });

let tokenAfterDiscard;
let issuedToken;
if (mode === "init") {
  // 통째로. `restart()` 안의 조회는 전부 위 fetchStub 으로 떨어진다.
  await context.init();
  tokenAfterDiscard = localStorage.getItem(TOKEN_KEY);
  issuedToken = runInContext("state.token", context);
} else {
  // init() 의 앞머리와 같은 순서: 삭제 신호 처리 → 토큰 확보.
  await context.discardDeletedAccountState();
  tokenAfterDiscard = localStorage.getItem(TOKEN_KEY);
  // 수정 라운드 1 부터 `ensureToken()` 은 토큰을 돌려주지 않고 성공 여부만 돌려준다
  // — 발급 실패를 예외가 아니라 화면 상태로 눕히려고 바꿨다(D-18-1). 발급된 토큰은
  // `state.token` 에 있다.
  const issued = await context.ensureToken();
  issuedToken = issued ? runInContext("state.token", context) : null;
}

process.stdout.write(
  JSON.stringify({
    tokenAfterDiscard,
    originalTokenRetained: tokenAfterDiscard === STORED_TOKEN,
    historyRetained: localStorage.getItem(HISTORY_KEY) !== null,
    issuedNewGuest: issuedToken === NEW_TOKEN,
    requests,
    messages,
    // 사용자가 **끝까지 보는** 문구. D-42-3 은 안내를 적은 직후 빈 문자열이 덮어쓰던
    // 결함이라, 거쳐 간 문구 목록이 아니라 마지막 값을 봐야 잡힌다.
    finalMessage: messages.length ? messages[messages.length - 1] : "",
    urlsReplaced: urls,
    finalSearch: location.search,
  }),
);
