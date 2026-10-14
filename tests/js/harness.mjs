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
const INITIALLY_HIDDEN = [
  "result",
  "linked-account",
  "backup-panel",
  "restore-panel",
  "share-copied",
  "copy-token-done",
];

function makeElement(tagName = "div") {
  const classes = new Set();
  return {
    tagName,
    className: "",
    textContent: "",
    value: "",
    maxLength: null,
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

  const document = {
    documentElement: { lang },
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, makeElement());
      return elements.get(id);
    },
    createElement: (tagName) => makeElement(tagName),
    querySelectorAll(selector) {
      return selector === "[data-puzzle-language]" ? chips : [];
    },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] ?? null;
    },
  };

  for (const id of INITIALLY_HIDDEN) document.getElementById(id).classList.add("hidden");
  document.getElementById("ui-strings").textContent = JSON.stringify(strings);

  const context = vm.createContext({
    document,
    console,
    localStorage: makeStorage(),
    navigator: { clipboard: { writeText: async () => {} } },
    location: { search: "", pathname: "/", href: "/", reload: () => {} },
    history: { replaceState: () => {} },
    setTimeout,
    clearTimeout,
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

/** 오류 응답 대역. 서버는 code + 한국어 message 를 준다(app/errors.py). */
export function errorResponse(status, body) {
  return { ok: false, status, json: async () => body };
}
