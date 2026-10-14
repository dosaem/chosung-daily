/** D-17-5 재현: 언어 **쓰기**(PATCH /me)가 여러 개 겹칠 때의 적용 순서.
 *
 * 조회 응답은 세대로 버리면 되지만(D-17-1·3·4), 쓰기는 버려도 서버에 이미
 * 커밋된다 — 겹쳐 보낸 PATCH 가 B→C→A 순으로 적용되면 화면은 마지막 선택을,
 * 서버 선호는 중간 선택을 들고 갈라진다. 다음 제출이 409 로 되돌아가고 새 탭도
 * 틀린 언어를 연다(review/impl-review-17.md 라운드 4 D-17-5).
 *
 * 그래서 이 대역의 fetch 는 앞선 시나리오들과 달리 **지속하는 서버 선호**를
 * 들고, today·제출이 그 선호를 보고 답한다. PATCH 응답을 따라가는 것만으로는
 * 드러나지 않던 갈림을 이 변수 하나가 드러낸다.
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { loadApp, errorResponse, okResponse } from "./harness.mjs";

const strings = JSON.parse(process.argv[2]);
const lang = process.argv[3] ?? "ko";

const KO_PUZZLE = {
  puzzle_id: 1,
  language: "ko",
  date: "2026-10-14",
  category: "general",
  length: 2,
  mask: [
    { t: "r", c: "ㅅ" },
    { t: "r", c: "ㄱ" },
  ],
  attempts: [],
  attempts_left: 5,
  status: "in_progress",
  hint: null,
};

const EN_PUZZLE = {
  ...KO_PUZZLE,
  puzzle_id: 2,
  language: "en",
  mask: [
    { t: "h", c: "" },
    { t: "r", c: "B" },
  ],
};

const PUZZLES = { ko: KO_PUZZLE, en: EN_PUZZLE };

/** 붙잡아 둔 응답 말고 나머지 await 가 풀릴 틈. */
function tick() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/** ko 퍼즐을 그려둔 앱 + "선호를 기억하는" 서버 대역.
 *
 * @param {object} [options]
 * @param {number} [options.holdPatch] 몇 번째 PATCH 를 손으로 풀어줄지(1-based)
 * @returns {{app: object, server: object, release: function(): void}}
 */
function appWithServer({ holdPatch = 0 } = {}) {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.run(`applyPuzzle(${JSON.stringify(KO_PUZZLE)})`);

  // 서버가 들고 있는 상태. `preference` 는 커밋된 퍼즐 언어, `commits` 는 적용된
  // 쓰기의 순서다.
  const server = { preference: "ko", commits: [] };
  let patches = 0;
  let release;

  app.setFetch(async (url, options) => {
    if (options?.method === "PATCH") {
      const language = JSON.parse(options.body).puzzle_language;
      patches += 1;
      // 붙잡은 요청은 **커밋 전에** 멈춘다 — 늦게 적용되는 쓰기를 만든다.
      if (patches === holdPatch) await new Promise((resolve) => (release = resolve));
      server.preference = language;
      server.commits.push(language);
      return okResponse({ puzzle_language: language });
    }
    if (url.endsWith("/guesses")) {
      // 서버는 "지금 내 선호의 오늘 퍼즐" 과 ID 를 맞춰본다(guess_service).
      if (JSON.parse(options.body).puzzle_id !== PUZZLES[server.preference].puzzle_id) {
        return errorResponse(409, { code: "PUZZLE_CHANGED" });
      }
      return okResponse({ is_correct: false, feedback: [true, false], attempts_left: 4 });
    }
    if (url.endsWith("/puzzles/today")) {
      return okResponse(structuredClone(PUZZLES[server.preference]));
    }
    if (url.includes("leaderboard")) return okResponse({ entries: [], me: null });
    return okResponse({ total_solved: 0, by_attempt: {} });
  });

  return { app, server, release: () => release() };
}

function chipState(app) {
  return Object.fromEntries(
    app.chips.map((chip) => [chip.dataset.puzzleLanguage, chip.getAttribute("aria-pressed")])
  );
}

function snapshot(app, server) {
  return {
    ...JSON.parse(
      app.run(`JSON.stringify({
        puzzleId: state.puzzleId,
        puzzleLanguage: state.puzzleLanguage,
      })`)
    ),
    chips: chipState(app),
    serverPreference: server.preference,
    commits: [...server.commits],
  };
}

/** 전환 뒤 제출이 그 퍼즐에 들어가는지 — 갈라져 있으면 409 가 돌아온다. */
async function submitAfter(app) {
  await app.run('submitGuess(document.getElementById("guess-input"), "사과")');
  return {
    message: app.el("message").textContent,
    ...JSON.parse(
      app.run(`JSON.stringify({
        puzzleId: state.puzzleId,
        puzzleLanguage: state.puzzleLanguage,
      })`)
    ),
  };
}

const results = {};

// (A) D-17-5 — 같은 칩을 두 번 누른 뒤 다른 칩을 누른다. 첫 쓰기가 가장 늦게
//     적용돼도 마지막 선택(ko)이 서버 선호로 남아야 한다.
{
  const { app, server, release } = appWithServer({ holdPatch: 1 });

  const first = app.run('handleLanguageChange("en")');
  await app.run('handleLanguageChange("en")');
  await app.run('handleLanguageChange("ko")');
  release();
  await first;

  const after = snapshot(app, server);
  results.duplicate_clicks_then_switch = { ...after, submit: await submitAfter(app) };
}

// (B) 쓰기가 도는 사이 다른 칩을 누르면 그 선택이 삼켜지면 안 된다 — 칩은 응답이
//     와야 바뀌니 `state.puzzleLanguage` 만 보면 ko 클릭이 "이미 ko" 로 보인다.
{
  const { app, server, release } = appWithServer({ holdPatch: 1 });

  const first = app.run('handleLanguageChange("en")');
  await tick();
  await app.run('handleLanguageChange("ko")');
  release();
  await first;

  results.switch_during_write = snapshot(app, server);
}

// (C) 같은 칩을 연달아 눌러도 쓰기는 한 번이다(중복 PATCH 자체를 만들지 않는다).
{
  const { app, server } = appWithServer();

  await Promise.all([
    app.run('handleLanguageChange("en")'),
    app.run('handleLanguageChange("en")'),
    app.run('handleLanguageChange("en")'),
  ]);

  results.duplicate_clicks_only = snapshot(app, server);
}

// (D) 대조군 — 겹치지 않는 평범한 전환은 그대로 한 번 쓰고 반영한다.
{
  const { app, server } = appWithServer();

  await app.run('handleLanguageChange("en")');

  results.plain_switch = { ...snapshot(app, server), submit: await submitAfter(app) };
}

console.log(JSON.stringify(results));
