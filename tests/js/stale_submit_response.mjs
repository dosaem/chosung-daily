/** D-17-1 재현: 퍼즐 언어를 바꾼 뒤 도착한 "이전 퍼즐" 제출 응답.
 *
 * 언어 칩은 제출 중에도 눌린다. ko 제출의 POST 응답이 늦게 오면, 그 사이에
 * 폐기한 ko 퍼즐의 결과가 새 en 보드·남은 기회·완료 표시를 덮어쓴다.
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
    { t: "h", c: "" },
  ],
  attempts: [],
  attempts_left: 5,
  status: "in_progress",
  hint: null,
};

const EN_PUZZLE = {
  puzzle_id: 2,
  language: "en",
  date: "2026-10-14",
  category: "book_title",
  length: 5,
  mask: [
    { t: "h", c: "" },
    { t: "r", c: "P" },
    { t: "s", c: " " },
    { t: "r", c: "L" },
    { t: "h", c: "" },
    { t: "h", c: "" },
  ],
  attempts: [],
  attempts_left: 5,
  status: "in_progress",
  hint: null,
};

const WRONG = { is_correct: false, feedback: [true, false], attempts_left: 4 };
const CORRECT = { is_correct: true, feedback: null, attempts_left: 4, answer: "사과" };

function snapshot(app) {
  return {
    ...JSON.parse(
      app.run(`JSON.stringify({
        puzzleId: state.puzzleId,
        puzzleLanguage: state.puzzleLanguage,
        attempts: state.attempts,
        attemptsLeft: state.attemptsLeft,
        finalStatus: state.finalStatus,
      })`)
    ),
    boardRows: app.el("board").children.length,
    attemptsLeftText: app.el("attempts-left").textContent,
    message: app.el("message").text,
    guessFormHidden: app.el("guess-form").classList.contains("hidden"),
    resultHidden: app.el("result").classList.contains("hidden"),
  };
}

/** ko 퍼즐에 제출해 응답을 붙잡아 둔 앱. */
function submitOnKoPuzzleWithHeldResponse() {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  app.run(`applyPuzzle(${JSON.stringify(KO_PUZZLE)})`);

  const release = app.holdFetch();
  const pending = app.run(`submitGuess(document.getElementById("guess-input"), "사과")`);
  return { app, release, pending };
}

/** 언어 칩 전환이 하는 일: 로컬 상태 폐기 + 새 퍼즐 적용. */
function switchToEnglishPuzzle(app) {
  app.run(`discardLocalPlayState(); applyPuzzle(${JSON.stringify(EN_PUZZLE)})`);
}

const results = {};

// (A) 오답 응답이 전환 뒤에 도착한다.
{
  const { app, release, pending } = submitOnKoPuzzleWithHeldResponse();
  switchToEnglishPuzzle(app);
  release(okResponse(WRONG));
  await pending;
  results.stale_wrong = snapshot(app);
}

// (B) 정답 응답이 전환 뒤에 도착한다 — 새 퍼즐이 ko 정답으로 끝나버리는지.
{
  const { app, release, pending } = submitOnKoPuzzleWithHeldResponse();
  switchToEnglishPuzzle(app);
  // 응답을 버리지 않는 구현은 여기서 통계·순위를 다시 불러온다. 그 요청이 터지지
  // 않게만 받아준다(검증 대상이 아니다).
  app.setFetch(async () => okResponse({ entries: [], me: null, total_solved: 0, by_attempt: {} }));
  release(okResponse(CORRECT));
  await pending;
  results.stale_correct = snapshot(app);
}

// (C) 대조군: 전환이 없으면 제출 응답은 그대로 반영돼야 한다.
{
  const { app, release, pending } = submitOnKoPuzzleWithHeldResponse();
  release(okResponse(WRONG));
  await pending;
  results.fresh_wrong = snapshot(app);
}

console.log(JSON.stringify(results));
