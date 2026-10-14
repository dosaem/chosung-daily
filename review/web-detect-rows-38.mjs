/** 번들이 실제로 그리는 리더보드·분포 행의 **마크업**을 꺼낸다.
 * 대역의 element 는 appendChild/className/textContent 만 쓰므로, 그 트리를
 * 그대로 HTML 로 직렬화하면 브라우저에서 번들이 만든 것과 같은 DOM 이 된다.
 */
import { loadApp } from "../tests/js/harness.mjs";

const strings = JSON.parse(process.argv[2]);
const lang = process.argv[3];

const BOARD = {
  date: "2026-10-15",
  language: "ko",
  entries: [
    { rank: 1, anon_tag: "a3f1", attempts: 1, seconds: 41, is_me: false },
    { rank: 2, anon_tag: "7b20", attempts: 2, seconds: 221, is_me: true },
    { rank: 3, anon_tag: "1c08", attempts: 2, seconds: 95, is_me: false },
    { rank: 4, anon_tag: "92de", attempts: 3, seconds: 188, is_me: false },
    { rank: 5, anon_tag: "4f61", attempts: 5, seconds: 4021, is_me: false },
  ],
  me: { rank: 2, attempts: 2, seconds: 221 },
};

const escape = (text) =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** 대역 element -> HTML. 자식이 있으면 자식을, 없으면 textContent 를 쓴다. */
function html(node) {
  const classes = [node.className, ...node.classes].filter(Boolean).join(" ");
  const inner =
    node.children.length > 0
      ? node.children.map(html).join("")
      : escape(node.textContent);
  return `<${node.tagName}${classes ? ` class="${classes}"` : ""}>${inner}</${node.tagName}>`;
}

const app = loadApp({ strings, lang });
app.run(`renderLeaderboard(${JSON.stringify(BOARD)})`);
app.run(
  `renderTodayStats(${JSON.stringify({
    total_solved: 8,
    by_attempt: { 1: 0.5, 2: 0.25, 3: 0.125, 4: 0.125, 5: 0 },
  })})`
);

console.log(
  JSON.stringify({
    entries: app.el("leaderboard-entries").children.map(html).join("\n"),
    myRank: escape(app.el("my-rank").textContent),
    stats: app.el("today-stats").children.map(html).join("\n"),
  })
);
