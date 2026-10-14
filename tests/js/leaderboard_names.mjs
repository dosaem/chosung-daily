/** 티켓 38: 리더보드 행 이름과 시도 횟수를 **웹 UI 언어**로 그린다.
 *
 * 서버는 언어 중립 태그(`anon_tag: "a3f1"`)만 준다 — "게스트 #" / "Guest #" 접두사와
 * 시도 횟수 문구는 번들이 자기 UI 사전에서 만든다(README "38."). 사전에 키가 있는지는
 * `tests/test_ui_strings.py` 가 보고, **그 키로 실제로 그 문구가 나오는지**는 여기서
 * 번들을 돌려서 본다 — en 복수형("1 try" vs "2 tries")은 `t()` 호출 한 번으로는
 * 안 갈리므로 렌더 결과를 봐야 드러난다.
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { loadApp } from "./harness.mjs";

const strings = JSON.parse(process.argv[2]);
const lang = process.argv[3] ?? "ko";

const BOARD = {
  date: "2026-10-15",
  language: "ko",
  entries: [
    { rank: 1, anon_tag: "a3f1", attempts: 1, seconds: 41, is_me: false },
    { rank: 2, anon_tag: "7b20", attempts: 2, seconds: 221, is_me: true },
  ],
  me: { rank: 2, attempts: 2, seconds: 221 },
};

const SOLO_BOARD = {
  ...BOARD,
  entries: [BOARD.entries[0]],
  me: { rank: 1, attempts: 1, seconds: 41 },
};

const app = loadApp({ strings, lang });

function board(data) {
  app.run(`renderLeaderboard(${JSON.stringify(data)})`);
  const rows = app.el("leaderboard-entries").children;
  return {
    rowTexts: rows.map((row) => row.text),
    // 내 행 강조는 CSS 클래스로만 한다 — 이름은 남의 행과 같은 규칙으로 그린다.
    isMeClasses: rows.map((row) => row.className),
    myRank: app.el("my-rank").textContent,
  };
}

const results = {
  lang,
  // 2위가 2회라 "N tries", 1위가 1회라 "1 try" — 한 보드에서 양쪽을 본다.
  two_entries: board(BOARD),
  // 내 순위 카드도 1회일 때 단수가 되어야 한다.
  solo_entry: board(SOLO_BOARD),
};

// 오늘의 시도 분포도 같은 복수형 결함이 있었다(1회 칸이 "1 tries").
app.run(
  `renderTodayStats(${JSON.stringify({
    total_solved: 4,
    by_attempt: { 1: 0.5, 2: 0.25, 3: 0.25, 4: 0, 5: 0 },
  })})`
);
results.stats_rows = app.el("today-stats").children.map((row) => row.textContent);

console.log(JSON.stringify(results));
