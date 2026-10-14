// `web/static/app.js` 를 Node `vm` 에서 **그대로** 실행해서 "삭제 신호를 받은
// 브라우저" 한 바퀴를 재현한다. 레포에 JS 테스트 러너가 없어서 번들 문자열만
// 확인했더니, `?deleted` 가 붙은 아무 링크로도 토큰이 지워지는 결함(D-14-1)을
// 놓쳤다 — 그래서 문자열이 아니라 동작을 본다.
//
// 대역은 브라우저 바깥(localStorage·DOM·fetch·location)뿐이다. app.js 는 한 줄도
// 고치지 않고, 파일 끝의 자동 `init()` 호출만 떼어낸다(DOM 전체가 필요해진다).
//
// 사용법: node deleted_state_harness.mjs <시나리오> <UI문구사전 JSON>
//         → 결과 JSON 을 stdout 으로.
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
// 수정 라운드 1 부터 `ensureToken()` 은 토큰을 돌려주지 않고 성공 여부만 돌려준다
// — 발급 실패를 예외가 아니라 화면 상태로 눕히려고 바꿨다(D-18-1). 발급된 토큰은
// `state.token` 에 있다.
const issued = await context.ensureToken();
const issuedToken = issued ? runInContext("state.token", context) : null;

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
