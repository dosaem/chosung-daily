/** D-17-2 재현: 기기 언어가 en 인데 서버 오류 문구가 한국어로 나온다.
 *
 * API 오류 응답의 `message` 는 한국어 한 벌뿐이다(app/errors.py). 화면이 그걸
 * 그대로 쓰면 영어 UI 에 한국어가 섞인다 — 문구는 `code` 로 UI 사전에서 골라야
 * 한다.
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { loadApp, errorResponse } from "./harness.mjs";

const strings = JSON.parse(process.argv[2]);
const lang = process.argv[3] ?? "en";

const PUZZLE = {
  puzzle_id: 7,
  language: "en",
  date: "2026-10-14",
  category: "general",
  length: 5,
  mask: [
    { t: "r", c: "A" },
    { t: "h", c: "" },
    { t: "h", c: "" },
    { t: "h", c: "" },
    { t: "h", c: "" },
  ],
  attempts: [],
  attempts_left: 5,
  status: "in_progress",
  hint: null,
};

// 서버가 실제로 돌려주는 payload (app/errors.py · app/services/guess_service.py).
const GUESS_ERRORS = {
  validation: [400, { code: "VALIDATION_ERROR", message: "정답은 5글자입니다." }],
  already_finished: [409, { code: "ALREADY_FINISHED", message: "이미 정답을 맞춘 퍼즐입니다." }],
  rate_limited: [429, { code: "RATE_LIMITED", message: "제출이 너무 많습니다. 잠시 후 다시 시도해주세요." }],
  unauthorized: [401, { code: "UNAUTHORIZED", message: "인증이 필요합니다." }],
  unknown: [500, { code: "INTERNAL_ERROR", message: "서버 오류가 발생했습니다." }],
};

const results = {};

for (const [name, [status, body]] of Object.entries(GUESS_ERRORS)) {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.run(`applyPuzzle(${JSON.stringify(PUZZLE)})`);
  app.setFetch(async () => errorResponse(status, body));
  await app.run(`submitGuess(document.getElementById("guess-input"), "a")`);
  results[`guess_${name}`] = app.el("message").text;
}

// 퍼즐이 없는 날의 today 조회도 같은 우선순위 문제를 갖는다. 티켓 18 부터 이 안내는
// `#message` 가 아니라 인라인 상태 카드(`#puzzle-state-text`)에 뜬다 — 카운트다운과
// 재시도 버튼이 같은 카드에 있어야 해서다(OVERRIDES §7).
{
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.setFetch(async () =>
    errorResponse(404, {
      code: "NO_PUZZLE_TODAY",
      message: "오늘의 퍼즐이 아직 준비되지 않았습니다.",
    })
  );
  await app.run("loadToday()");
  results.today_no_puzzle = app.el("puzzle-state-text").text;
}

console.log(JSON.stringify(results));
