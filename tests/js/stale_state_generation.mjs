/** D-17-1(REPEAT) · D-17-3 재현: 상태를 폐기한 뒤 도착한 "이전 세대" 응답.
 *
 * 퍼즐 ID 비교만으로는 ko→en→ko 왕복처럼 **같은 ID 로 돌아오는** 경우를 가려내지
 * 못한다. 조회(`/me/stats`·순위·통계) 응답에는 ID 비교조차 없어서, 전환 전에
 * 시작한 응답이 지금 화면의 언어·칩·순위를 되돌린다
 * (review/impl-review-17.md 라운드 2).
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { loadApp, okResponse } from "./harness.mjs";

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

// 돌아온 ko 퍼즐은 서버가 이미 1회 시도를 들고 있다 — 보류 중인 제출이 그 시도다.
const KO_PUZZLE_AFTER_RETURN = {
  ...KO_PUZZLE,
  attempts: [{ guess: "사자", feedback: [true, false] }],
  attempts_left: 4,
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

const KO_STATS = {
  puzzle_language: "ko",
  current_streak: 3,
  max_streak: 7,
  solved_count: 12,
  linked_account: null,
};

/** ko 퍼즐을 그려둔 앱. */
function appOnKoPuzzle() {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.run(`applyPuzzle(${JSON.stringify(KO_PUZZLE)})`);
  return app;
}

/** 언어 전환이 부르는 PATCH·today·순위·통계를 받아주는 fetch.
 *
 * @param {function(): object} currentPuzzle 지금 서버가 내려줄 "오늘 내 퍼즐"
 */
function serveSwitch(currentPuzzle) {
  return async (url, options) => {
    if (options?.method === "PATCH") {
      return okResponse({ puzzle_language: JSON.parse(options.body).puzzle_language });
    }
    if (url.endsWith("/puzzles/today")) return okResponse(structuredClone(currentPuzzle()));
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
        attempts: state.attempts,
        attemptsLeft: state.attemptsLeft,
      })`)
    ),
    chips: chipState(app),
    boardRows: app.el("board").children.length,
    streak: app.el("streak").textContent,
    normalizedLatin: app.run('normalizeGuess("ab")'),
  };
}

const results = {};

// (A) D-17-1 REPEAT — ko 제출 보류 → en 전환 → ko 복귀(서버 1행) → 제출 응답 도착.
{
  const app = appOnKoPuzzle();
  const release = app.holdFetch();
  const pending = app.run(`submitGuess(document.getElementById("guess-input"), "사자")`);

  let current = EN_PUZZLE;
  app.setFetch(serveSwitch(() => current));
  await app.run('handleLanguageChange("en")');
  current = KO_PUZZLE_AFTER_RETURN;
  await app.run('handleLanguageChange("ko")');

  release(okResponse({ is_correct: false, feedback: [true, false], attempts_left: 4 }));
  await pending;
  results.round_trip_submit = snapshot(app);
}

// (B) D-17-3 — ko 에서 시작한 /me/stats 응답이 en 전환 뒤에 도착한다.
{
  const app = appOnKoPuzzle();
  const release = app.holdFetch();
  const pending = app.run("loadStats()");

  app.setFetch(serveSwitch(() => EN_PUZZLE));
  await app.run('handleLanguageChange("en")');

  release(okResponse(KO_STATS));
  await pending;
  const afterStaleStats = snapshot(app);

  // 선택 상태가 ko 로 되돌아가면 다음 한국어 클릭까지 막힌다 — 요청 0건이면 갇힌 것이다.
  let requests = 0;
  app.setFetch(async (url, options) => {
    requests += 1;
    return serveSwitch(() => KO_PUZZLE)(url, options);
  });
  await app.run('handleLanguageChange("ko")');

  results.stale_stats = { ...afterStaleStats, koClickRequests: requests };
}

// (C) 대조군 — 전환이 없으면 stats 응답은 평소처럼 칩과 연속 기록에 반영된다.
{
  const app = appOnKoPuzzle();
  app.setFetch(async () => okResponse(KO_STATS));
  await app.run("loadStats()");
  results.fresh_stats = snapshot(app);
}

// (D) 전환 전에 시작한 순위·오늘 통계 응답도 지금 화면을 덮어쓰면 안 된다.
{
  const app = appOnKoPuzzle();
  const release = {};
  app.setFetch(
    (url) =>
      new Promise((resolve) => {
        release[url.includes("leaderboard") ? "leaderboard" : "stats"] = resolve;
      })
  );
  const pending = Promise.all([app.run("loadLeaderboard()"), app.run("loadTodayStats()")]);

  app.setFetch(serveSwitch(() => EN_PUZZLE));
  await app.run('handleLanguageChange("en")');

  release.leaderboard(
    okResponse({
      entries: [{ rank: 1, display: "ko-player", attempts: 2, seconds: 30, is_me: false }],
      me: { rank: 9, attempts: 3, seconds: 90 },
    })
  );
  release.stats(okResponse({ total_solved: 10, by_attempt: { 1: 0.5 } }));
  await pending;

  results.stale_leaderboard = {
    entryRows: app.el("leaderboard-entries").children.length,
    myRank: app.el("my-rank").textContent,
    statsText: app.el("today-stats").text,
  };
}

console.log(JSON.stringify(results));
