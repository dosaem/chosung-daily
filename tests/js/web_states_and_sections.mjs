/** 티켓 18: 상태 4종(스켈레톤 · 오프라인 · 인라인 오류 · 퍼즐 없음)과 섹션 토글.
 *
 * 마크업이 있는지는 pytest 렌더(`tests/test_web_design.py`)가 본다. 여기서 보는 건
 * **전환**이다 — 스켈레톤이 실제로 걷히는지, 오프라인에서 입력이 잠기는지, 연결이
 * 돌아오면 알아서 다시 받는지. 번들 문자열로는 못 보는 것들이다.
 *
 * 결과를 JSON 한 덩이로 stdout 에 찍고, 판정은 tests/test_web_js.py 가 한다.
 */
import { loadApp, okResponse, errorResponse } from "./harness.mjs";

const strings = JSON.parse(process.argv[2]);
const lang = process.argv[3] ?? "ko";

const PUZZLE = {
  puzzle_id: 1,
  language: "ko",
  date: "2026-10-14",
  category: "general",
  length: 2,
  mask: [
    { t: "h", c: "" },
    { t: "h", c: "" },
  ],
  attempts: [],
  attempts_left: 5,
  status: "in_progress",
  hint: null,
};

const FINISHED = {
  ...PUZZLE,
  attempts: [{ guess: "사자", feedback: [true, false] }],
  attempts_left: 4,
  status: "success",
  answer: "사과",
};

const EMPTY_LEADERBOARD = { entries: [], me: null };
const EMPTY_STATS = { total_solved: 0, by_attempt: {} };

/** 퍼즐 조회만 바꿔 끼우고 나머지 조회는 빈 응답으로 받는 대역. */
function fetchFor(today) {
  return async (url) => {
    if (url.includes("/puzzles/today/leaderboard")) return okResponse(EMPTY_LEADERBOARD);
    if (url.includes("/puzzles/today/stats")) return okResponse(EMPTY_STATS);
    if (url.includes("/puzzles/today")) return today();
    return okResponse({});
  };
}

/** 요청이 아예 못 나가는 상태(오프라인·DNS 실패). 브라우저와 같게 fetch 가 던진다. */
const UNREACHABLE = async () => {
  throw new TypeError("Failed to fetch");
};

function snapshot(app) {
  const hidden = (id) => app.el(id).classList.contains("hidden");
  return {
    skeletonHidden: hidden("puzzle-skeleton"),
    puzzleHidden: hidden("puzzle"),
    formHidden: hidden("guess-form"),
    stateHidden: hidden("puzzle-state"),
    stateText: app.el("puzzle-state-text").textContent,
    countdownHidden: hidden("puzzle-state-countdown"),
    countdownText: app.el("puzzle-state-countdown").textContent,
    bannerHidden: hidden("offline-banner"),
    inputDisabled: app.el("guess-input").disabled,
    submitDisabled: app.el("submit-button").disabled,
    resultHidden: hidden("result"),
  };
}

function started() {
  const app = loadApp({ strings, lang });
  app.run("state.token = 'test-token'");
  // 재시도 버튼과 `online`/`offline` 핸들러를 실제로 붙여서 본다 — 핸들러를 손으로
  // 부르면 "버튼에 연결됐는가" 를 못 본다.
  app.run("bindEvents()");
  return app;
}

const results = {};

// --- 스켈레톤 → 퍼즐 ---------------------------------------------------------
{
  const app = started();
  results.before_load = snapshot(app);

  app.setFetch(fetchFor(() => okResponse(PUZZLE)));
  await app.run("reloadPuzzle()");
  results.after_load = snapshot(app);
}

// --- 네트워크 오류: 인라인 카드 + 배너 + 입력 잠금 ---------------------------
{
  const app = started();
  app.setFetch(UNREACHABLE);
  await app.run("reloadPuzzle()");
  results.unreachable = snapshot(app);

  // 재시도 버튼으로 복구 (연결이 돌아왔다고 알려주는 이벤트가 없는 경우)
  app.setFetch(fetchFor(() => okResponse(PUZZLE)));
  await app.el("puzzle-state-retry").listeners.click[0]();
  results.after_retry = snapshot(app);
}

// --- 연결 복구: `online` 이벤트가 알아서 다시 받는다 -------------------------
{
  const app = started();
  app.setFetch(UNREACHABLE);
  await app.run("reloadPuzzle()");
  const offline = snapshot(app);

  app.setFetch(fetchFor(() => okResponse(PUZZLE)));
  await app.emitWindow("online");
  results.online_recovery = { offline, after: snapshot(app) };
}

// --- `navigator.onLine` 만으로도 배너가 뜬다(첫 요청 전) ---------------------
{
  const app = started();
  app.context.navigator.onLine = false;
  app.run("renderOffline(!navigator.onLine)");
  results.offline_before_first_request = snapshot(app);
}

// --- 퍼즐 없음: "곧 새 퍼즐" + 카운트다운 + 재시도 ---------------------------
{
  const app = started();
  // KST 2026-10-14 00:30:00 = 2026-10-13T15:30:00Z — 자정까지 23:30:00 남았다.
  app.run(`Date.now = () => ${Date.parse("2026-10-13T15:30:00Z")}`);
  app.setFetch(
    fetchFor(() =>
      errorResponse(404, {
        code: "NO_PUZZLE_TODAY",
        message: "오늘의 퍼즐이 아직 준비되지 않았습니다.",
      })
    )
  );
  await app.run("reloadPuzzle()");
  results.no_puzzle = snapshot(app);

  // 자정 직전으로 시계를 옮기고 한 틱 그린다 — 타이머를 기다리지 않고 같은 함수를 부른다.
  app.run(`Date.now = () => ${Date.parse("2026-10-13T14:59:59Z")}`);
  app.run("renderCountdown()");
  results.no_puzzle_next_tick = app.el("puzzle-state-countdown").textContent;

  // 퍼즐이 올라왔다 — 카운트다운이 멈추고 자리를 비켜야 한다.
  app.setFetch(fetchFor(() => okResponse(PUZZLE)));
  await app.el("puzzle-state-retry").listeners.click[0]();
  results.no_puzzle_then_ready = snapshot(app);
}

// --- 카운트다운 계산 ---------------------------------------------------------
results.countdown_seconds = {
  just_after_midnight: app_seconds("2026-10-13T15:00:01Z"),
  half_hour_in: app_seconds("2026-10-13T15:30:00Z"),
  one_second_before_midnight: app_seconds("2026-10-14T14:59:59Z"),
};

function app_seconds(iso) {
  const app = started();
  return app.run(`secondsUntilKstMidnight(${Date.parse(iso)})`);
}

// --- 섹션 토글 ---------------------------------------------------------------
{
  const app = started();
  const sections = () => ({
    panels: Object.fromEntries(
      app.sectionPanels.map((panel) => [
        panel.dataset.sectionPanel,
        !panel.classList.contains("hidden"),
      ])
    ),
    pressed: Object.fromEntries(
      app.sectionLinks.map((link) => [link.dataset.section, link.getAttribute("aria-pressed")])
    ),
  });

  results.sections_at_first = sections();

  await app.sectionLinks[1].listeners.click[0]();
  results.sections_after_leaderboard = sections();

  await app.sectionLinks[2].listeners.click[0]();
  results.sections_after_records = sections();

  await app.sectionLinks[0].listeners.click[0]();
  results.sections_back_to_today = sections();
}

// --- 공유 텍스트의 웹 링크 ---------------------------------------------------
{
  const app = started();
  app.setFetch(fetchFor(() => okResponse(FINISHED)));
  await app.run("reloadPuzzle()");
  results.share_text = app.run("buildShareText()");
  results.share_result = snapshot(app);
}

console.log(JSON.stringify(results));
