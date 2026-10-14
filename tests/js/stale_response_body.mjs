/** D-17-4 재현: 헤더는 받았지만 **본문이 아직 안 온** 응답.
 *
 * `await fetch()` 가 끝난 시점은 헤더까지다 — 본문 읽기(`res.json()`)는 또 하나의
 * 비동기 경계라, 그 사이에 언어 전환·409 재조회가 상태를 폐기하면 fetch 직후에
 * 통과한 세대 검사는 이미 무효다. 그런데도 본문이 다 오면 검사 없이 화면에
 * 반영한다(review/impl-review-17.md D-17-4).
 *
 * 기존 `stale_state_generation.mjs` 는 fetch Promise 자체를 붙잡아서 이 창을
 * 만들지 못한다. 여기서는 실제 `Response` + `ReadableStream` 으로 본문 도착
 * 시점만 늦춘다(`heldBodyResponse`).
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { heldBodyResponse, loadApp, okResponse } from "./harness.mjs";

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

const KO_LEADERBOARD = {
  entries: [{ rank: 1, display: "ko-player", attempts: 2, seconds: 30, is_me: false }],
  me: { rank: 9, attempts: 3, seconds: 90 },
};

const KO_TODAY_STATS = { total_solved: 10, by_attempt: { 1: 50 } };

/** 붙잡아 둔 본문 말고 나머지 await 가 풀릴 틈. */
function tick() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

function appOnPuzzle(puzzle) {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.run(`applyPuzzle(${JSON.stringify(puzzle)})`);
  return app;
}

/** 언어 전환이 부르는 PATCH·today·순위·통계를 받아주는 fetch. */
function serveSwitch(puzzle) {
  return async (url, options) => {
    if (options?.method === "PATCH") {
      return okResponse({ puzzle_language: JSON.parse(options.body).puzzle_language });
    }
    if (url.endsWith("/puzzles/today")) return okResponse(structuredClone(puzzle));
    if (url.includes("leaderboard")) return okResponse({ entries: [], me: null });
    return okResponse({ total_solved: 0, by_attempt: {} });
  };
}

function chipState(app) {
  return Object.fromEntries(
    app.chips.map((chip) => [chip.dataset.puzzleLanguage, chip.getAttribute("aria-pressed")])
  );
}

function snapshot(app) {
  return {
    ...JSON.parse(
      app.run(`JSON.stringify({
        puzzleId: state.puzzleId,
        puzzleLanguage: state.puzzleLanguage,
      })`)
    ),
    chips: chipState(app),
    entryRows: app.el("leaderboard-entries").children.length,
    myRank: app.el("my-rank").textContent,
    statsText: app.el("today-stats").text,
  };
}

/** 한쪽 언어의 조회를 "본문 보류" 로 시작한 뒤 다른 언어로 전환한다.
 *
 * @param {object} options
 * @param {object} options.from 지금 화면에 그려둔 퍼즐
 * @param {object} options.to 전환 뒤 서버가 내려줄 퍼즐
 * @param {string} options.call 보류시킬 조회 호출식
 * @param {object} options.body 늦게 도착할 그 조회의 본문
 */
async function switchWhileBodyPending({ from, to, call, body }) {
  const app = appOnPuzzle(from);
  const held = heldBodyResponse(body);
  app.setFetch(async () => held.response);

  const pending = app.run(call);
  // 헤더는 도착시키고(= fetch 직후의 세대 검사를 통과시키고) 본문만 붙잡아 둔다.
  await tick();

  app.setFetch(serveSwitch(to));
  await app.run(`handleLanguageChange("${to.language}")`);

  held.send();
  await pending;
  return snapshot(app);
}

const results = {};

// (A) today 본문이 전환 뒤에 도착한다 — ko 재조회 보류 → en 전환 → ko 본문 도착.
results.late_today_body = await switchWhileBodyPending({
  from: KO_PUZZLE,
  to: EN_PUZZLE,
  call: "reloadPuzzle()",
  body: KO_PUZZLE,
});

// (B) 반대 방향도 같다 — en 재조회 보류 → ko 전환 → en 본문 도착.
results.late_today_body_reverse = await switchWhileBodyPending({
  from: EN_PUZZLE,
  to: KO_PUZZLE,
  call: "reloadPuzzle()",
  body: EN_PUZZLE,
});

// (C) 순위 본문이 전환 뒤에 도착하면 전 언어의 순위가 새 화면에 뜬다.
results.late_leaderboard_body = await switchWhileBodyPending({
  from: KO_PUZZLE,
  to: EN_PUZZLE,
  call: "loadLeaderboard()",
  body: KO_LEADERBOARD,
});

// (D) 오늘 통계 본문도 같다.
results.late_today_stats_body = await switchWhileBodyPending({
  from: KO_PUZZLE,
  to: EN_PUZZLE,
  call: "loadTodayStats()",
  body: KO_TODAY_STATS,
});

// (E) PATCH /me 본문이 도는 사이 409 재조회가 화면을 갈아끼우면 그 전환은 접는다.
{
  const app = appOnPuzzle(KO_PUZZLE);
  const held = heldBodyResponse({ puzzle_language: "en" });
  let todayCalls = 0;
  app.setFetch(async (url, options) => {
    if (options?.method === "PATCH") return held.response;
    if (url.endsWith("/puzzles/today")) {
      todayCalls += 1;
      return okResponse(structuredClone(KO_PUZZLE));
    }
    if (url.includes("leaderboard")) return okResponse({ entries: [], me: null });
    return okResponse({ total_solved: 0, by_attempt: {} });
  });

  const pendingEn = app.run('handleLanguageChange("en")');
  await tick();
  await app.run("reloadPuzzle()");
  const todayAfterReload = todayCalls;

  held.send();
  await pendingEn;

  results.late_patch_body = {
    ...snapshot(app),
    refetchesAfterReload: todayCalls - todayAfterReload,
  };
}

// (F) `/me/stats` 본문이 전환 뒤에 도착한다 — 칩은 지난 선호를 따라가지 않지만,
//     퍼즐이 아니라 게스트의 것인 연속 기록은 그대로 갱신한다(D-17-3 과 같은 기준).
{
  const app = appOnPuzzle(KO_PUZZLE);
  const held = heldBodyResponse({
    puzzle_language: "ko",
    current_streak: 3,
    max_streak: 7,
    solved_count: 12,
    linked_account: null,
  });
  app.setFetch(async () => held.response);

  const pending = app.run("loadStats()");
  await tick();

  app.setFetch(serveSwitch(EN_PUZZLE));
  await app.run('handleLanguageChange("en")');

  held.send();
  await pending;

  results.late_stats_body = { ...snapshot(app), streak: app.el("streak").textContent };
}

// (G) 대조군 — 전환이 없으면 늦게 온 본문도 평소처럼 전부 반영된다.
{
  const app = appOnPuzzle(KO_PUZZLE);
  const held = heldBodyResponse(KO_LEADERBOARD);
  app.setFetch(async () => held.response);

  const pending = app.run("loadLeaderboard()");
  await tick();
  held.send();
  await pending;

  results.fresh_leaderboard_body = snapshot(app);
}

// (I) 제출 응답 본문이 전환 뒤에 도착한다 — 여섯 요청 중 마지막 경로다.
//     (today · PATCH /me · /me/stats · 순위 · 오늘 통계 · 제출)
{
  const app = appOnPuzzle(KO_PUZZLE);
  const held = heldBodyResponse({ is_correct: false, feedback: [true, false], attempts_left: 4 });
  app.setFetch(async () => held.response);

  const pending = app.run(`submitGuess(document.getElementById("guess-input"), "사자")`);
  await tick();

  app.setFetch(serveSwitch(EN_PUZZLE));
  await app.run('handleLanguageChange("en")');

  held.send();
  await pending;

  results.late_submit_body = {
    ...snapshot(app),
    ...JSON.parse(
      app.run(`JSON.stringify({ attempts: state.attempts, attemptsLeft: state.attemptsLeft })`)
    ),
    boardRows: app.el("board").children.length,
  };
}

// (H) 200 인데 본문이 JSON 이 아니면(프록시가 끼워넣은 HTML 등) 던지지 않고
//     불러오기 실패로 눕는다 — 본문을 한 곳에서 읽게 되면서 생긴 경로다.
{
  const app = appOnPuzzle(KO_PUZZLE);
  app.setFetch(async () => new Response("<html>502</html>", { status: 200 }));

  await app.run("reloadPuzzle()");

  results.unparsable_body = { message: app.el("puzzle-state-text").textContent };
}

console.log(JSON.stringify(results));
