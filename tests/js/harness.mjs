/** `web/static/app.js` 를 node 안에서 실제로 실행하는 최소 대역(DOM · fetch · 저장소).
 *
 * 번들 문자열 어서션(tests/test_web.py)은 "함수가 있다"까지만 본다. 제출 응답이
 * 늦게 도착하는 순서 문제나, 오류 payload 를 받은 뒤의 화면 문구는 **함수를
 * 돌려봐야** 드러난다(review/impl-review-17.md D-17-1 · D-17-2). Playwright 는
 * 아직 안 들이기로 했으니(스펙 "미정 항목" 5) 브라우저 없이 번들만 실행한다.
 *
 * 대역이 제공하는 건 DOM 모양과 응답 도착 순서뿐이고, 검사 대상 함수는 작업
 * 트리의 번들을 그대로 쓴다 — 대역 쪽에 로직을 복사해두면 테스트가 구현을 따라
 * 가지 못한다.
 */
import fs from "node:fs";
import vm from "node:vm";

const BUNDLE = new URL("../../web/static/app.js", import.meta.url);

// HTML 에서 class="hidden" 으로 시작하는 것들(web/templates/index.html).
// 티켓 18 이 퍼즐 영역·제출 폼·상태 카드·오프라인 배너를 여기 추가했다 — 처음
// 보이는 건 스켈레톤 하나뿐이다.
const INITIALLY_HIDDEN = [
  "result",
  "linked-account",
  "backup-panel",
  "restore-panel",
  "share-copied",
  "copy-token-done",
  "puzzle",
  "guess-form",
  "puzzle-state",
  "puzzle-state-countdown",
  "offline-banner",
];

// 상단 섹션 토글(오늘 · 순위 · 내 기록). 링크와 패널이 `data-section*` 로 짝을 맞춘다.
const SECTIONS = ["today", "leaderboard", "records"];

function makeElement(tagName = "div") {
  const classes = new Set();
  return {
    tagName,
    className: "",
    textContent: "",
    value: "",
    maxLength: null,
    disabled: false,
    children: [],
    dataset: {},
    attributes: {},
    listeners: {},
    classes,
    classList: {
      add: (...names) => names.forEach((name) => classes.add(name)),
      remove: (...names) => names.forEach((name) => classes.delete(name)),
      toggle: (name) => (classes.has(name) ? classes.delete(name) : classes.add(name)),
      contains: (name) => classes.has(name),
    },
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    addEventListener(type, handler) {
      (this.listeners[type] ??= []).push(handler);
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    getAttribute(name) {
      return this.attributes[name] ?? null;
    },
    // 번들은 innerHTML 을 "" 로 비우는 데만 쓴다(렌더 함수들).
    set innerHTML(value) {
      if (value === "") this.children = [];
    },
    get innerHTML() {
      return "";
    },
    /** 자식까지 이어붙인 보이는 텍스트. 보드·순위 행 검사에 쓴다. */
    get text() {
      return this.children.length > 0
        ? this.children.map((child) => child.text).join("")
        : this.textContent;
    },
  };
}

function makeStorage() {
  const storage = {};
  const define = (name, value) =>
    Object.defineProperty(storage, name, { value, enumerable: false });
  define("getItem", (key) => (key in storage ? storage[key] : null));
  define("setItem", (key, value) => {
    storage[key] = String(value);
  });
  define("removeItem", (key) => {
    delete storage[key];
  });
  return storage;
}

/** 번들을 한 번 실행한 샌드박스를 돌려준다.
 *
 * @param {object} options
 * @param {object} options.strings 서버가 심어주는 UI 문구 사전 한 벌
 * @param {string} options.lang `<html lang>` (기기 언어)
 */
export function loadApp({ strings, lang = "ko" }) {
  const elements = new Map();
  const chips = ["ko", "en"].map((language) => {
    const chip = makeElement("button");
    chip.dataset.puzzleLanguage = language;
    return chip;
  });
  const sectionLinks = SECTIONS.map((name) => {
    const link = makeElement("button");
    link.dataset.section = name;
    link.setAttribute("aria-pressed", String(name === "today"));
    return link;
  });
  const sectionPanels = SECTIONS.map((name) => {
    const panel = makeElement("section");
    panel.dataset.sectionPanel = name;
    if (name !== "today") panel.classList.add("hidden");
    return panel;
  });

  const document = {
    documentElement: { lang },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, makeElement());
      return elements.get(id);
    },
    createElement: (tagName) => makeElement(tagName),
    querySelectorAll(selector) {
      return (
        {
          "[data-puzzle-language]": chips,
          "[data-section]": sectionLinks,
          "[data-section-panel]": sectionPanels,
        }[selector] ?? []
      );
    },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] ?? null;
    },
  };

  for (const id of INITIALLY_HIDDEN) document.getElementById(id).classList.add("hidden");
  document.getElementById("ui-strings").textContent = JSON.stringify(strings);

  // `online`/`offline` 은 window 이벤트다 — 대역은 핸들러를 받아 두고 시나리오가
  // 직접 부른다(브라우저 없이 연결 상태를 흉내낼 방법이 없다).
  const windowListeners = {};
  const windowStub = {
    addEventListener(type, handler) {
      (windowListeners[type] ??= []).push(handler);
    },
  };

  const context = vm.createContext({
    document,
    console,
    localStorage: makeStorage(),
    navigator: { onLine: true, clipboard: { writeText: async () => {} } },
    location: { search: "", pathname: "/", href: "/", reload: () => {} },
    history: { replaceState: () => {} },
    window: windowStub,
    setTimeout,
    clearTimeout,
    // 카운트다운 타이머는 `unref()` 로 둔다 — 안 그러면 "퍼즐 없음" 상태로 끝난
    // 시나리오에서 node 가 1초 타이머를 붙들고 종료하지 않는다(테스트가 타임아웃).
    // 똑딱이는 동작 자체는 `renderCountdown()` 을 직접 불러서 본다.
    setInterval: (handler, ms) => setInterval(handler, ms).unref(),
    clearInterval,
    URLSearchParams,
    fetch: async () => {
      throw new Error("대역이 예상하지 못한 fetch 호출");
    },
  });

  // 마지막 자동 실행만 뗀다 — 나머지는 작업 트리의 번들 그대로다.
  const source = fs.readFileSync(BUNDLE, "utf8");
  const stripped = source.replace(/\ninit\(\);\s*$/, "\n");
  if (stripped === source) throw new Error("app.js 끝의 init() 호출을 찾지 못했다");
  vm.runInContext(stripped, context, { filename: "app.js" });

  return {
    context,
    document,
    chips,
    sectionLinks,
    sectionPanels,
    /** 브라우저가 보냈을 `online`/`offline` 이벤트를 흘려 넣는다. */
    async emitWindow(type) {
      context.navigator.onLine = type === "online";
      for (const handler of windowListeners[type] ?? []) await handler();
    },
    /** 샌드박스 안에서 표현식을 평가한다. */
    run: (expression) => vm.runInContext(expression, context),
    /** 다음 fetch 응답을 정한다. */
    setFetch(implementation) {
      context.fetch = implementation;
    },
    /** 응답을 내 손으로 풀어줄 수 있는 fetch 를 심고, 그 해제 함수를 돌려준다. */
    holdFetch() {
      let release;
      context.fetch = () => new Promise((resolve) => (release = resolve));
      return (response) => release(response);
    },
    el: (id) => document.getElementById(id),
  };
}

/** `ok` 응답 대역. */
export function okResponse(body) {
  return { ok: true, status: 200, json: async () => body };
}

/** 헤더는 바로 주고 **본문은 내가 보낼 때** 도착하는 실제 `Response`.
 *
 * `okResponse` 의 json 은 즉시 끝나서 "헤더는 받았지만 본문은 아직" 인 창을 만들
 * 수 없다 — `await fetch()` 와 `res.json()` 사이의 그 창에서 상태가 폐기되는 것이
 * D-17-4 다(review/impl-review-17.md). 브라우저와 같은 경계를 쓰려고 대역을 직접
 * 짜지 않고 node 의 실제 `Response` + `ReadableStream` 을 쓴다.
 *
 * @param {object} body 나중에 도착할 JSON 본문
 * @param {object} [options]
 * @param {number} [options.status] HTTP 상태 코드
 * @returns {{response: Response, send: function(): void}}
 */
export function heldBodyResponse(body, { status = 200 } = {}) {
  let controller;
  const stream = new ReadableStream({
    start(streamController) {
      controller = streamController;
    },
  });
  const response = new Response(stream, {
    status,
    headers: { "Content-Type": "application/json" },
  });
  return {
    response,
    send() {
      controller.enqueue(new TextEncoder().encode(JSON.stringify(body)));
      controller.close();
    },
  };
}

/** 오류 응답 대역. 서버는 code + 한국어 message 를 준다(app/errors.py). */
export function errorResponse(status, body) {
  return { ok: false, status, json: async () => body };
}
