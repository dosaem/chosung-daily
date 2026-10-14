// `web/static/app.js` 를 Node `vm` 에서 **그대로** 실행해서 "삭제 신호를 받은
// 브라우저" 한 바퀴를 재현한다. 레포에 JS 테스트 러너가 없어서 번들 문자열만
// 확인했더니, `?deleted` 가 붙은 아무 링크로도 토큰이 지워지는 결함(D-14-1)을
// 놓쳤다 — 그래서 문자열이 아니라 동작을 본다.
//
// 대역은 브라우저 바깥(localStorage·DOM·fetch·location)뿐이다. app.js 는 한 줄도
// 고치지 않고, 파일 끝의 자동 `init()` 호출만 떼어낸다(DOM 전체가 필요해진다).
//
// 사용법: node deleted_state_harness.mjs <시나리오> → 결과 JSON 을 stdout 으로.
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

function makeStorage(entries) {
  const map = new Map(Object.entries(entries));
  return {
    get length() {
      return map.size;
    },
    key(index) {
      return [...map.keys()][index] ?? null;
    },
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
    snapshot() {
      return Object.fromEntries(map);
    },
  };
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
  getElementById(id) {
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
  createElement: () => ({ ...element }),
};

async function fetchStub(url, options = {}) {
  const method = (options.method ?? "GET").toUpperCase();
  requests.push({ method, url, headers: options.headers ?? null });

  if (method === "POST" && url.endsWith("/guests")) {
    return jsonResponse(200, { token: NEW_TOKEN });
  }
  // 그 밖의 Bearer 조회 = "이 토큰이 아직 유효한가" 확인.
  if (scenario.probeStatus === null) throw new TypeError("network error");
  return jsonResponse(scenario.probeStatus, scenario.probeStatus === 200 ? [] : { code: "UNAUTHORIZED" });
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
  navigator: { clipboard: { writeText: async () => {} } },
  JSON,
  Promise,
  Error,
  TypeError,
});
runInContext(source, context, { filename: "app.js" });

// init() 의 앞머리와 같은 순서: 삭제 신호 처리 → 토큰 확보.
await context.discardDeletedAccountState();
const tokenAfterDiscard = localStorage.getItem(TOKEN_KEY);
const issuedToken = await context.ensureToken();

process.stdout.write(
  JSON.stringify({
    tokenAfterDiscard,
    originalTokenRetained: tokenAfterDiscard === STORED_TOKEN,
    historyRetained: localStorage.getItem(HISTORY_KEY) !== null,
    issuedNewGuest: issuedToken === NEW_TOKEN,
    requests,
    messages,
    urlsReplaced: urls,
    finalSearch: location.search,
  }),
);
