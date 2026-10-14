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

const STATS = {
  current_streak: 0,
  max_streak: 0,
  solved_count: 0,
  linked_account: null,
  puzzle_language: "ko",
};

/** 게스트 발급까지 포함한 서버 대역. `init()` 을 처음부터 돌리는 시나리오가 쓴다 —
 *  `fetchFor` 는 토큰이 이미 있다고 보고 `/guests` 를 빈 응답으로 돌려준다. */
function serverFor(today) {
  return async (url) => {
    if (url.includes("/guests")) return okResponse({ token: "issued-token" });
    if (url.includes("/me/stats")) return okResponse(STATS);
    if (url.includes("/puzzles/today/leaderboard")) return okResponse(EMPTY_LEADERBOARD);
    if (url.includes("/puzzles/today/stats")) return okResponse(EMPTY_STATS);
    if (url.includes("/puzzles/today")) return today();
    return okResponse({});
  };
}

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

// --- D-18-1: 첫 방문의 게스트 발급이 실패해도 스켈레톤에 갇히지 않는다 -------
//
// 예전에는 `ensureToken()` 의 예외가 `init()` 을 끊어서, 그 뒤에 있던
// `bindEvents()`·`renderOffline()` 이 아예 안 돌았다 — 배너도 재시도 버튼도
// `online` 이벤트도 없는 스켈레톤이 영구 상태였다(review/impl-review-18.md D-18-1).
// 핸들러를 손으로 붙이지 않고 **`init()` 을 그대로** 돌려서 그 순서를 본다.
{
  const app = loadApp({ strings, lang });
  app.context.navigator.onLine = false;
  app.setFetch(UNREACHABLE);
  let threw = null;
  try {
    await app.run("init()");
  } catch (error) {
    threw = String(error);
  }
  results.first_visit_offline = {
    threw,
    ...snapshot(app),
    retryHandlers: (app.el("puzzle-state-retry").listeners.click ?? []).length,
  };

  // 같은 재시도 버튼 하나로 **발급부터** 다시 시작한다.
  app.context.navigator.onLine = true;
  app.setFetch(serverFor(() => okResponse(PUZZLE)));
  await app.el("puzzle-state-retry").listeners.click[0]();
  results.first_visit_offline_after_retry = {
    ...snapshot(app),
    token: app.run("state.token"),
    stored: app.context.localStorage.getItem("chosung_token"),
    streak: app.el("streak").textContent,
  };
}

// --- D-18-1: 연결이 돌아오면 발급도 알아서 다시 한다 -------------------------
{
  const app = loadApp({ strings, lang });
  app.context.navigator.onLine = false;
  app.setFetch(UNREACHABLE);
  await app.run("init()");

  app.setFetch(serverFor(() => okResponse(PUZZLE)));
  await app.emitWindow("online");
  results.first_visit_online_recovery = { ...snapshot(app), token: app.run("state.token") };
}

// --- D-18-1: 5xx 발급 실패도 같은 인라인 카드다 ------------------------------
{
  const app = loadApp({ strings, lang });
  app.setFetch(async (url) =>
    url.includes("/guests")
      ? errorResponse(500, { code: "INTERNAL_ERROR", message: "서버 오류" })
      : okResponse({})
  );
  await app.run("init()");
  results.first_visit_server_error = {
    ...snapshot(app),
    retryHandlers: (app.el("puzzle-state-retry").listeners.click ?? []).length,
  };
}

// --- D-18-2: 제출이 못 나갔을 때 재시도 경로가 보인다 ------------------------
//
// `navigator.onLine` 은 계속 true 다(일시적 DNS·연결 실패) — `online` 이벤트가
// 영영 안 오므로, 입력만 잠그고 안내만 띄우면 새로고침 말고는 빠져나올 수 없었다
// (review/impl-review-18.md D-18-2).
{
  const app = loadApp({ strings, lang });
  app.context.localStorage.setItem("chosung_token", "stored-token");
  app.setFetch(serverFor(() => okResponse(PUZZLE)));
  await app.run("init()");

  app.el("guess-input").value = "사과";
  app.setFetch(async (url) => {
    if (url.includes("/guesses")) throw new TypeError("Failed to fetch");
    return serverFor(() => okResponse(PUZZLE))(url);
  });
  await app.el("guess-form").listeners.submit[0]({ preventDefault() {} });
  results.submit_unreachable = {
    ...snapshot(app),
    online: app.context.navigator.onLine,
    message: app.el("message").textContent,
  };

  // fetch 가 죽은 사이에 제출이 서버에 **닿았을 수도** 있다 — 재시도는 그 이력까지
  // 서버에서 다시 받아와야 화면이 서버와 맞는다.
  const CONSUMED = {
    ...PUZZLE,
    attempts: [{ guess: "사과", feedback: [true, false] }],
    attempts_left: 4,
  };
  app.setFetch(serverFor(() => okResponse(CONSUMED)));
  await app.el("puzzle-state-retry").listeners.click[0]();
  results.submit_unreachable_after_retry = {
    ...snapshot(app),
    attempts: app.run("state.attempts"),
    boardRows: app.el("board").children.length,
    attemptsLeft: app.run("state.attemptsLeft"),
  };
}

// --- D-18-4: 토큰이 바뀌는 **모든** 경로에서 세션 게스트를 같은 값으로 맞춘다 ---
//
// 세션 쿠키가 "이 브라우저 = 이 게스트" 다 — OAuth 로그인과 계정 삭제 페이지는 토큰이
// 아니라 그 쿠키로 대상을 고른다(app/api/oauth.py `sync_session`, app/web.py
// `account_delete`). D-18-1 수정이 `syncSession()` 을 새 게스트 발급 분기 **안으로**
// 옮겨서, 저장된 토큰으로 시작하는 초기화는 동기화를 한 번도 안 했다. 백업 코드로 다른
// 게스트 B 를 복원한 뒤에도 세션은 A 로 남아서, 삭제 페이지가 화면에 없는 A 를 지웠다
// (review/impl-review-18.md D-18-4).
//
// 경로마다 따로 맞추면 또 샌다. 토큰이 바뀌는 경로를 한 표로 묶어, 전부
// `ensureToken()` 이라는 한 지점을 거치는지 본다. 경로별로 두 가지를 센다 —
// `/session/sync` 가 **정확히 1회** 나갔는지, 그 Authorization 이 화면이 실제로 쓰는
// 토큰(`/me/stats` 의 Authorization)과 **같은지**. 둘이 같으면 삭제 폼의 대상(세션
// 게스트)과 화면의 게스트가 어긋날 수 없다.
{
  const recordingApp = ({ stored = null, search = "", fetchFor: fetchImpl } = {}) => {
    const app = loadApp({ strings, lang });
    if (stored) app.context.localStorage.setItem("chosung_token", stored);
    app.context.location.search = search;

    const calls = [];
    const server = fetchImpl ?? serverFor(() => okResponse(PUZZLE));
    app.setFetch(async (url, options) => {
      calls.push({ url, authorization: options?.headers?.Authorization ?? null });
      return server(url, options);
    });
    return { app, calls };
  };

  const authFor = (calls, suffix) =>
    calls.find((call) => call.url.includes(suffix))?.authorization ?? null;

  /** 한 경로의 판정 재료. "몇 번, 누구로, 화면과 같은 게스트인가". */
  const syncReport = (calls) => {
    const sync = calls.filter((call) => call.url.endsWith("/session/sync"));
    const uiAuthorization = authFor(calls, "/me/stats");
    return {
      count: sync.length,
      authorization: sync[0]?.authorization ?? null,
      // 화면이 API 를 부르는 토큰과 세션에 심는 토큰이 같아야 한다.
      matchesUi: sync.length > 0 && sync[0].authorization === uiAuthorization,
      uiAuthorization,
      // 로그인 버튼을 누를 수 있게 되기 전에 심어져야 한다 — 퍼즐 조회보다 먼저 나간다.
      beforePuzzleLoad:
        sync.length > 0 &&
        calls.indexOf(sync[0]) < calls.findIndex((call) => call.url.includes("/puzzles/today")),
    };
  };

  // (1) 첫 발급 — 저장된 토큰이 없다. 발급 뒤에 동기화한다(대조군).
  {
    const { app, calls } = recordingApp();
    await app.run("init()");
    results.sync_on_first_visit = {
      ...syncReport(calls),
      guestIssues: calls.filter((call) => call.url.endsWith("/guests")).length,
    };
  }

  // (2) 저장 토큰으로 시작 — 복원 후의 새로고침, 세션 쿠키만 없는 재방문.
  {
    const { app, calls } = recordingApp({ stored: "restored-guest-token" });
    await app.run("init()");
    results.sync_on_stored_token = {
      ...syncReport(calls),
      guestIssues: calls.filter((call) => call.url.endsWith("/guests")).length,
    };
  }

  // (2b) 저장 토큰 + 오프라인 재방문 — 동기화 요청이 아예 못 나간다. 거부를 받아주지
  //      않으면(부르는 쪽은 응답을 안 기다린다) 받아줄 사람 없는 rejection 이 되고,
  //      다시 보내지도 않아 세션은 옛 게스트로 남는다. 연결이 돌아오면 재시도해야 한다.
  {
    const app = loadApp({ strings, lang });
    app.context.localStorage.setItem("chosung_token", "offline-revisit-token");
    app.context.navigator.onLine = false;
    app.setFetch(UNREACHABLE);

    let threw = null;
    try {
      await app.run("init()");
    } catch (error) {
      threw = String(error);
    }
    const offline = {
      threw,
      syncedToken: app.run("state.syncedToken"),
      bannerHidden: app.el("offline-banner").classList.contains("hidden"),
    };

    const calls = [];
    const server = serverFor(() => okResponse(PUZZLE));
    app.setFetch(async (url, options) => {
      calls.push({ url, authorization: options?.headers?.Authorization ?? null });
      return server(url, options);
    });
    await app.emitWindow("online");
    results.sync_on_stored_token_offline = {
      offline,
      ...syncReport(calls),
      guestIssues: calls.filter((call) => call.url.endsWith("/guests")).length,
      syncedToken: app.run("state.syncedToken"),
    };
  }

  // (3) 백업 코드 복원 — 저장소를 B 로 바꾸고 새로고침한다. 새로고침 **뒤의** 로드가
  //     B 로 동기화해야 한다. 대역의 `location.reload()` 는 아무것도 안 하므로, 그
  //     로드를 (2) 와 같은 길로 한 번 더 실제로 돌려서 본다.
  {
    const { app, calls } = recordingApp({ stored: "guest-a-token" });
    await app.run("init()");
    const beforeRestore = syncReport(calls);

    let reloads = 0;
    app.context.location.reload = () => {
      reloads += 1;
    };
    app.el("token-input").value = "guest-b-token";
    await app.el("restore-submit-button").listeners.click[0]();

    const reloaded = recordingApp({ stored: app.context.localStorage.getItem("chosung_token") });
    await reloaded.app.run("init()");
    results.sync_after_backup_restore = {
      beforeRestore,
      reloads,
      storedAfterRestore: app.context.localStorage.getItem("chosung_token"),
      ...syncReport(reloaded.calls),
    };
  }

  // (4) OAuth 로그인 복귀 — 옛 게스트 토큰 위로 계정 토큰이 쿼리로 들어온다.
  {
    const { app, calls } = recordingApp({
      stored: "old-guest-token",
      search: "?login_token=linked-account-token",
    });
    await app.run("init()");
    results.sync_after_oauth_callback = syncReport(calls);
  }

  // (5) 계정 삭제 후 — 서버가 `/?deleted=1` 로 돌려보낸다. 지워진 토큰을 버리고 새
  //     게스트를 발급받는데, 비워진 세션도 그 새 게스트로 다시 채워야 한다.
  {
    const server = serverFor(() => okResponse(PUZZLE));
    const deletedServer = async (url, options) => {
      // 지워진 옛 토큰으로 부른 이력 조회만 401 이다.
      if (url.includes("/me/history")) {
        return options?.headers?.Authorization === "Bearer deleted-guest-token"
          ? errorResponse(401, { code: "UNAUTHORIZED", message: "유효하지 않은 토큰입니다." })
          : okResponse({ days: [] });
      }
      return server(url, options);
    };
    const { app, calls } = recordingApp({
      stored: "deleted-guest-token",
      search: "?deleted=1",
      fetchFor: deletedServer,
    });
    await app.run("init()");
    results.sync_after_account_deletion = {
      ...syncReport(calls),
      storedToken: app.context.localStorage.getItem("chosung_token"),
    };
  }
}

console.log(JSON.stringify(results));
