const API_BASE = "/api/v1";
const TOKEN_KEY = "chosung_token";
// 보드를 localStorage 에 쌓던 시절의 키 접두사. 이제 보드는 서버 `attempts` 로만
// 복원하니(README "04. 시도 이력을 서버가 돌려주는 이유"), 남아 있으면 지운다.
const LEGACY_HISTORY_PREFIX = "chosung_history_";
const MAX_ATTEMPTS = 5;

// 공유 텍스트 끝에 붙는 웹 링크(US 11). 받은 사람이 어디서 왔는지 보이게
// `?utm_source=share` 를 달아 둔다 — 티켓 18 이 받은 값 그대로다.
const SHARE_URL = "https://chosung.dosaem.com/?utm_source=share";

// 다음 KST 자정까지를 셀 때 쓴다. KST 는 서머타임이 없어서 고정 오프셋으로
// 계산해도 서버의 자정 배정(ADR 0001)과 어긋나지 않는다.
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

// 가림 타일 종류. app/utils/mask.py 와 같은 이름을 쓴다.
const REVEALED = "r";
const HIDDEN = "h";
const SEPARATOR = "s";

// UI 문구 사전. 서버가 기기 언어(Accept-Language)로 고른 한 벌을 페이지에 인라인
// JSON 으로 심어준다(app/i18n.py) — 추가 요청도, 언어가 바뀌는 깜빡임도 없다.
const STRINGS = JSON.parse(document.getElementById("ui-strings").textContent);

function t(key, vars = {}) {
  return STRINGS[key].replace(/\{(\w+)\}/g, (_, name) => vars[name]);
}

// API 오류 응답의 `message` 는 한국어 한 벌뿐이다(app/errors.py) — 기기 언어가
// en 이면 그대로 띄울 수 없다. 그래서 화면 문구는 `code` 로 UI 사전에서 고른다.
// 사전에 없는 code(INTERNAL_ERROR 등)는 부른 쪽이 준 기본 문구로 눕힌다.
const ERROR_STRING_KEYS = {
  // 웹에서 닿는 VALIDATION_ERROR 는 길이 불일치 하나다 — 빈 답은 handleSubmit 이,
  // 50자 초과는 입력창 maxLength 가 미리 막는다(app/schemas/guess.py).
  VALIDATION_ERROR: "error_guess_length",
  ALREADY_FINISHED: "error_already_finished",
  RATE_LIMITED: "error_rate_limited",
  NO_PUZZLE_TODAY: "error_no_puzzle_today",
  UNAUTHORIZED: "error_unauthorized",
};

function errorText(body, fallbackKey) {
  const key = ERROR_STRING_KEYS[body.code];
  return key ? t(key, { length: state.length }) : t(fallbackKey);
}

const state = {
  token: null,
  today: null,
  // 화면이 들고 있는 플레이 상태의 "세대". 언어 전환·409 재조회·백업 코드
  // 전환처럼 상태를 통째로 폐기할 때마다 1 올린다(discardLocalPlayState).
  // 요청을 보낼 때 세대를 적어두고, 응답이 왔을 때 달라졌으면 그 응답은 이미
  // 없는 화면의 것이라 버린다 — 퍼즐 ID 비교만으로는 ko→en→ko 왕복처럼 **같은
  // ID 로 돌아오는** 경우를 가려내지 못한다(review/impl-review-17.md D-17-1).
  generation: 0,
  // 화면에 그린 퍼즐의 ID. 제출에 같이 보내서, 자정이 지났거나 다른 기기에서
  // 언어를 바꾼 뒤의 제출이 엉뚱한 퍼즐에 들어가지 않게 한다(409 PUZZLE_CHANGED).
  puzzleId: null,
  // 플레이 중인 퍼즐의 언어. 칩 표시와 통계·리더보드 조회에 쓴다.
  puzzleLanguage: null,
  // 사용자가 **마지막으로 고른** 퍼즐 언어와, 그걸 서버에 쓰는 중인지 여부.
  // 칩(puzzleLanguage)은 서버 응답이 와야 바뀌니, 쓰는 사이의 클릭을 가려내고
  // 마지막 선택으로 수렴시키려면 이 둘이 따로 필요하다(handleLanguageChange).
  languageWanted: null,
  languageWriting: false,
  // 가림 타일 목록. 문제 행도, 시도 행의 구분자 위치도 전부 여기서 나온다.
  mask: [],
  length: 0,
  // 아래 둘은 서버 응답(renderPuzzle/submitGuess/showResult)에서만 설정한다.
  // 로컬 이력으로 성공/실패·시도 횟수를 되짚으면, 다른 기기에서 이미 끝난 퍼즐을
  // 열었을 때 공유 텍스트가 틀린 결과를 말한다.
  attemptsLeft: MAX_ATTEMPTS,
  finalStatus: null,
  // 서버가 돌려준 시도 이력. 공유 그리드도 이걸로 만든다.
  attempts: [],
  // 상단 오프라인 배너가 떠 있는지. `navigator.onLine` 과 "요청이 아예 못
  // 나갔다" 를 둘 다 반영한다(renderOffline).
  offline: false,
};

/** 요청을 보내기 직전의 세대를 집어 둔다.
 *
 * 돌려준 함수는 "응답이 오는 사이에 상태가 폐기됐는가" 를 답한다. 비동기 요청은
 * 전부 이 한 경로로 거른다 — 응답마다 다른 조건(퍼즐 ID 비교 같은)을 덧대면
 * ko→en→ko 왕복처럼 그 조건이 다시 같아지는 순서에서 또 새어 들어온다
 * (review/impl-review-17.md D-17-1 REPEAT · D-17-3).
 */
function sinceGeneration() {
  const generation = state.generation;
  return () => state.generation !== generation;
}

/** 요청을 보내고, **본문까지 다 읽은 뒤** 세대를 확인해 돌려준다.
 *
 * `await fetch()` 가 끝난 시점은 헤더까지다 — 본문 읽기(`res.json()`)는 또 하나의
 * 비동기 경계라, 그 사이에 상태가 폐기되면 fetch 직후에 통과한 검사는 이미
 * 무효다. 그런데도 본문이 다 오면 검사 없이 화면에 반영했다
 * (review/impl-review-17.md D-17-4). 그래서 세대 검사는 **상태에 반영하기 직전**
 * 인 여기 한 곳에서만 하고, 부른 쪽은 `stale` 만 보면 된다.
 *
 * 요청이 **아예 못 나간 경우**(오프라인·DNS 실패)는 던지지 않고 `offline: true`
 * 로 눕힌다. 던지면 부른 쪽마다 try 를 두거나, 안 두면 로딩 스켈레톤이 그대로
 * 멈춘 화면이 된다 — 그 상태를 화면에 보여주는 게 US 8 이다.
 *
 * @returns {Promise<{stale: boolean, ok: boolean, offline: boolean, body: object}>}
 */
async function fetchJson(url, options) {
  const isStale = sinceGeneration();
  const res = await fetch(url, options).catch(() => null);
  if (res === null) return { stale: isStale(), ok: false, offline: true, body: {} };
  // 본문이 JSON 이 아닌 경우(프록시가 끼워넣은 502 HTML 등)는 던지지 않고 실패로
  // 눕힌다 — 200 이어도 읽을 수 없는 본문은 자료가 아니라 오류다. 부른 쪽은
  // `ok` 와 `code` 로 판단하니 파싱 실패 하나로 화면이 멈추진 않는다.
  const body = await res.json().catch(() => null);
  return { stale: isStale(), ok: res.ok && body !== null, offline: false, body: body ?? {} };
}

function authHeaders() {
  return { Authorization: `Bearer ${state.token}` };
}

function jsonHeaders() {
  return { ...authHeaders(), "Content-Type": "application/json" };
}

// localStorage는 프라이빗 모드 등에서 접근 자체가 던질 수 있다 — 게임 플레이에
// 필수는 아닌 기능(토큰 재사용)이라 항상 이 두 함수로만 접근하고, 실패하면 조용히
// 넘어간다.
function safeStorageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeStorageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 무시 — 저장이 안 돼도 이번 세션 플레이 자체는 계속 돌아가야 한다.
  }
}

// 삭제 후 정리에만 쓴다. 저장과 같은 이유로 접근 자체가 던질 수 있어서 감싼다.
function safeStorageRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // 무시
  }
}

function clearStoredHistory() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(LEGACY_HISTORY_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
  } catch {
    // 무시 — 못 지워도 더 이상 읽지 않는 키다.
  }
}

/** `state.token` 을 채운다. 없으면 게스트를 발급받는다.
 *
 * 던지지 않고 **성공 여부를 돌려준다**. 예전에는 발급 실패가 예외로 `init()` 을
 * 통째로 끊었는데, 그러면 그 뒤에 있던 `bindEvents()`·`renderOffline()` 이 아예
 * 안 돌아서 첫 방문자는 스켈레톤에 갇혔다 — 배너도, 재시도 버튼도, `online`
 * 이벤트도 없었다(review/impl-review-18.md D-18-1). 조회 실패와 같은 인라인
 * 카드로 눕히면 같은 재시도 버튼 하나로 발급부터 다시 시작할 수 있다.
 *
 * @returns {Promise<boolean>} 토큰이 준비됐으면 true.
 */
async function ensureToken() {
  if (state.token !== null) return true;

  const existing = safeStorageGet(TOKEN_KEY);
  if (existing) {
    state.token = existing;
    return true;
  }

  // 새 게스트의 퍼즐 언어 기본값은 기기 언어다(CONTEXT.md "퍼즐 언어"). 서버가
  // 이미 고른 UI 언어를 그대로 쓴다 — 지원 언어가 ko/en 으로 같다.
  const { ok, offline, body } = await fetchJson(`${API_BASE}/guests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ puzzle_language: document.documentElement.lang }),
  });
  if (offline) {
    renderOffline(true);
    showPuzzleState(t("network_error"));
    return false;
  }
  // 요청이 나갔다는 건 연결이 돌아왔다는 뜻이다 — 응답이 오류여도 배너는 내린다.
  renderOffline(false);
  if (!ok) {
    showPuzzleState(t("guest_issue_failed"));
    return false;
  }

  state.token = body.token;
  safeStorageSet(TOKEN_KEY, body.token);
  // 응답을 기다릴 필요 없음 — 로그인 버튼 누르기 전까지만 심어지면 된다.
  syncSession();
  return true;
}

async function loadToday() {
  // 칩을 연달아 누르면 재조회가 두 번 날아간다 — 먼저 보낸 쪽이 늦게 도착해
  // 나중 언어의 퍼즐을 덮어쓰지 않게, 폐기 이전 세대의 응답은 없던 일로 한다.
  const { stale, ok, offline, body } = await fetchJson(`${API_BASE}/puzzles/today`, {
    headers: authHeaders(),
  });
  if (stale) return null;
  if (offline) {
    renderOffline(true);
    showPuzzleState(t("network_error"));
    return null;
  }
  // 요청이 나갔다는 건 연결이 돌아왔다는 뜻이다 — 응답이 오류여도 배너는 내린다.
  renderOffline(false);
  if (!ok) {
    // 퍼즐이 아직 없는 날(자정 전환 직후)만 카운트다운을 붙인다(US 7).
    if (body.code === "NO_PUZZLE_TODAY") {
      showPuzzleState(t("no_puzzle_heading"), { countdown: true });
    } else {
      showPuzzleState(errorText(body, "puzzle_load_failed"));
    }
    return null;
  }
  return body;
}

async function loadStats() {
  const streakEl = document.getElementById("streak");
  const { stale, ok, body: stats } = await fetchJson(`${API_BASE}/me/stats`, {
    headers: authHeaders(),
  });
  if (!ok) {
    // 게임 자체엔 영향 없는 보조 정보라 #message로 크게 띄우진 않지만, 조용히
    // 묵혀서 "기록이 0일인가?"로 헷갈리게 두지도 않는다.
    streakEl.textContent = t("streak_load_failed");
    return;
  }
  // 연속 기록·연결 계정은 퍼즐이 아니라 게스트의 것이라 전환과 무관하게 최신이다.
  streakEl.textContent = t("streak_summary", {
    current: stats.current_streak,
    max: stats.max_streak,
    solved: stats.solved_count,
  });
  renderLinkedAccount(stats.linked_account);
  // 선호 언어는 다르다 — 전환 전에 시작한 조회면 이 값은 이미 지난 선택이다.
  // 그걸 그대로 칩에 반영하면 지금 보고 있는 퍼즐과 선택이 어긋나고, 다음 칩
  // 클릭이 "이미 그 언어"로 보여 무시된다(review/impl-review-17.md D-17-3).
  // 퍼즐이 없는 날(자정 전환 직후)에도 칩은 내 선호 언어를 가리켜야 하므로,
  // 퍼즐 유무가 아니라 세대로 판단한다.
  if (!stale) renderLanguageChips(stats.puzzle_language);
}

// 로그인 버튼은 provider 연결 전까지만 보여준다 — 연결된 뒤엔 어떤 계정으로
// 연결됐는지 보여주고, 같은 게스트에 또 연결 시도할 일이 없게 버튼을 숨긴다.
function renderLinkedAccount(linkedAccount) {
  const el = document.getElementById("linked-account");

  if (!linkedAccount) {
    el.classList.add("hidden");
    document.getElementById("google-login-button").classList.remove("hidden");
    document.getElementById("apple-login-button").classList.remove("hidden");
    return;
  }

  const provider =
    { google: t("provider_google"), apple: t("provider_apple") }[linkedAccount.provider] ??
    linkedAccount.provider;
  el.textContent = linkedAccount.email
    ? t("linked_account_with_email", { provider, email: linkedAccount.email })
    : t("linked_account", { provider });
  el.classList.remove("hidden");
  document.getElementById("google-login-button").classList.add("hidden");
  document.getElementById("apple-login-button").classList.add("hidden");
}

// --- 퍼즐 언어 칩 ------------------------------------------------------------

function renderLanguageChips(language) {
  state.puzzleLanguage = language;
  for (const chip of document.querySelectorAll("[data-puzzle-language]")) {
    chip.setAttribute("aria-pressed", String(chip.dataset.puzzleLanguage === language));
  }
}

/** 고른 언어를 서버에 쓴다 — **한 번에 하나만**, 마지막 선택으로 수렴할 때까지.
 *
 * 세대 검사는 늦게 온 *응답* 을 버릴 뿐이고, 이미 보낸 PATCH 는 버려도 서버에
 * 커밋된다. 그래서 쓰기를 겹쳐 보내면 커밋 순서가 클릭 순서와 달라질 수 있고,
 * 화면은 마지막 선택을·서버 선호는 중간 선택을 들고 갈라진다 — 다음 제출이
 * 409 로 그 선택을 취소하고 새 탭도 틀린 언어를 연다
 * (review/impl-review-17.md D-17-5). 쓰기를 직렬화하면 "클릭 순서 = 커밋 순서"가
 * 되고, 쓰는 사이에 더 고른 언어는 응답을 받은 뒤 이어서 쓴다.
 *
 * @returns {Promise<string|null>} 마지막으로 커밋된 언어. 폐기·실패면 null.
 */
async function drainLanguageWrites() {
  while (state.languageWanted !== null) {
    const language = state.languageWanted;
    const { stale, ok, body } = await fetchJson(`${API_BASE}/me`, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify({ puzzle_language: language }),
    });
    // PATCH 가 도는 사이 409 재조회나 백업 코드 전환이 화면을 갈아끼웠을 수 있다.
    // 그 위에 이 전환을 마저 얹으면 사용자가 보고 있는 퍼즐이 한 번 더 바뀐다.
    if (stale) return null;
    if (!ok) {
      showMessage(t("puzzle_language_failed"));
      return null;
    }
    // 쓰는 사이에 또 골랐으면 그 언어로 한 번 더 쓴다. 중간 언어는 칩에 올리지도,
    // 퍼즐을 재조회하지도 않는다 — 헛된 왕복이고 화면만 두 번 바뀐다.
    if (state.languageWanted === language) return body.puzzle_language;
  }
  return null;
}

async function handleLanguageChange(language) {
  // 아직 쓰고 있는 선택까지 보고 비교한다. 칩(`state.puzzleLanguage`)은 응답이
  // 와야 바뀌니, 그것만 보면 같은 칩 연속 클릭이 그대로 중복 PATCH 가 되고
  // (D-17-5) 쓰는 사이의 다른 칩 클릭은 "이미 그 언어"로 보여 삼켜진다.
  if (language === (state.languageWanted ?? state.puzzleLanguage)) return;
  state.languageWanted = language;
  // 이미 도는 쓰기가 있으면 그쪽이 이 선택까지 이어서 쓴다. 여기서 기다리지는
  // 않는다 — 칩 클릭은 앞선 왕복에 묶이지 않아야 한다.
  if (state.languageWriting) return;

  state.languageWriting = true;
  let committed;
  try {
    committed = await drainLanguageWrites();
  } finally {
    state.languageWriting = false;
    state.languageWanted = null;
  }
  if (committed === null) return;

  renderLanguageChips(committed);
  await reloadPuzzle();
}

// --- 화면 상태: 스켈레톤 · 오프라인 · 인라인 오류 · 퍼즐 없음 ---------------
//
// 네 가지가 같은 자리를 쓴다(OVERRIDES §7). 전환을 함수 셋으로 모아 두면 둘이
// 겹쳐 보이거나(오류 카드 밑에 스켈레톤이 남는) 아무것도 안 보이는 조합이 안 생긴다.

function show(id) {
  document.getElementById(id).classList.remove("hidden");
}

function hide(id) {
  document.getElementById(id).classList.add("hidden");
}

/** 퍼즐을 받는 중. 스피너가 아니라 스켈레톤이다(OVERRIDES §7). */
function showSkeleton() {
  show("puzzle-skeleton");
  hide("puzzle-state");
  hide("puzzle");
  hide("guess-form");
  hide("result");
  stopCountdown();
}

/** 퍼즐이 왔다. */
function showPuzzleArea() {
  hide("puzzle-skeleton");
  hide("puzzle-state");
  stopCountdown();
  show("puzzle");
}

/** 인라인 상태 카드(오류·퍼즐 없음). 토스트로 숨기지 않는다(OVERRIDES §7).
 *
 * `countdown` 은 "퍼즐 없음" 전용이다 — 그건 오류가 아니라 "자정까지 기다리면
 * 된다" 라서 남은 시간을 같이 보여준다(US 7).
 */
function showPuzzleState(text, { countdown = false } = {}) {
  hide("puzzle-skeleton");
  hide("puzzle");
  hide("guess-form");
  document.getElementById("puzzle-state-text").textContent = text;
  show("puzzle-state");
  if (countdown) startCountdown();
  else stopCountdown();
}

/** 다음 KST 자정까지 남은 초. */
function secondsUntilKstMidnight(nowMs = Date.now()) {
  return Math.ceil((DAY_MS - ((nowMs + KST_OFFSET_MS) % DAY_MS)) / 1000);
}

let countdownTimer = null;

function renderCountdown() {
  document.getElementById("puzzle-state-countdown").textContent = t("no_puzzle_countdown", {
    time: formatSeconds(secondsUntilKstMidnight()),
  });
}

function startCountdown() {
  renderCountdown();
  show("puzzle-state-countdown");
  countdownTimer ??= setInterval(renderCountdown, 1000);
}

function stopCountdown() {
  if (countdownTimer !== null) clearInterval(countdownTimer);
  countdownTimer = null;
  hide("puzzle-state-countdown");
}

/** 상단 오프라인 배너와 입력 비활성(OVERRIDES §7).
 *
 * `navigator.onLine` 과 "요청이 아예 못 나갔다" 를 둘 다 본다: onLine 은 "랜선이
 * 꽂혀 있다" 수준이라 죽은 Wi-Fi 에서도 true 고, 반대로 요청 실패는 서버 쪽
 * 문제일 수도 있다. 어느 쪽이든 플레이어가 할 일은 같아서(기다리거나 재시도)
 * 한 배너로 묶고, 복구 경로는 `online` 이벤트와 재시도 버튼 둘을 다 둔다.
 */
function renderOffline(offline) {
  state.offline = offline;
  if (offline) show("offline-banner");
  else hide("offline-banner");
  // 보낼 수 없는 제출로 기회를 잃지 않게 입력을 잠근다.
  document.getElementById("guess-input").disabled = offline;
  document.getElementById("submit-button").disabled = offline;
}

// --- 섹션 토글: 오늘 · 순위 · 내 기록 ---------------------------------------

/** 상단 링크가 가리키는 섹션 하나만 보여준다.
 *
 * 주소는 바꾸지 않는다 — 앱의 탭 바 자리를 웹에서는 이 토글 하나가 대신하고
 * (SCREENS "웹" 절), 링크가 아니라 버튼인 이유도 그것이다. 선택 표시는 퍼즐 언어
 * 칩과 같은 `aria-pressed` 다.
 */
function showSection(name) {
  for (const panel of document.querySelectorAll("[data-section-panel]")) {
    if (panel.dataset.sectionPanel === name) panel.classList.remove("hidden");
    else panel.classList.add("hidden");
  }
  for (const link of document.querySelectorAll("[data-section]")) {
    link.setAttribute("aria-pressed", String(link.dataset.section === name));
  }
}

// --- 가림·보드 렌더 ----------------------------------------------------------

/** 구분자(`s`)를 뺀 글자 위치를 mask 자리마다 붙여 돌려준다.
 *
 * 서버의 `attempts[].guess`·`feedback` 은 구분자를 제거한 글자열이라(README
 * "04. 제출 일관성") 간격을 다시 끼우는 건 mask 를 가진 클라이언트 몫이다
 * (스펙 "미정 항목" 13). 문제 행과 시도 행이 같은 자리 계산을 쓰게 여기 모았다.
 */
/** 타이핑한 답을 서버가 저장하는 글자열과 같은 모양으로 만든다.
 *
 * 서버의 `normalize_for_compare`(`app/services/game_rules.py`)와 같은 규칙이다:
 * 구분자(공백·하이픈)를 지우고, en 은 대문자로 통일한다. 판정은 여전히 서버가
 * 하지만, **보드에 그릴 글자는 내가 갖고 있어야** 해서(제출 응답은 정규화된
 * guess 를 돌려주지 않는다) 같은 규칙을 한 번 적용한다. 여기서 정규화한 값을
 * 그대로 제출하니 서버가 한 번 더 정규화해도 결과가 같다.
 */
function normalizeGuess(raw) {
  const stripped = raw.replace(/[ -]/g, "");
  return state.puzzleLanguage === "en" ? stripped.toUpperCase() : stripped;
}

function withSeparatorSlots(mask) {
  let index = 0;
  return mask.map((tile) =>
    tile.t === SEPARATOR ? { separator: tile.c } : { tile, index: index++ }
  );
}

function textSpan(className, text) {
  const el = document.createElement("span");
  el.className = className;
  el.textContent = text;
  return el;
}

function separatorElement(text) {
  return textSpan("tile-gap", text);
}

function renderMaskRow(mask) {
  const row = document.getElementById("mask-row");
  row.innerHTML = "";

  for (const slot of withSeparatorSlots(mask)) {
    if (slot.separator !== undefined) {
      row.appendChild(separatorElement(slot.separator));
      continue;
    }
    row.appendChild(
      slot.tile.t === REVEALED
        ? textSpan("tile tile-revealed", slot.tile.c)
        : textSpan("tile tile-empty", "")
    );
  }
}

function renderBoard(attempts) {
  const container = document.getElementById("board");
  container.innerHTML = "";

  for (const attempt of attempts) {
    container.appendChild(renderAttemptRow(attempt));
  }
}

function renderAttemptRow({ guess, feedback }) {
  const row = document.createElement("div");
  row.className = "tile-row";
  const letters = [...guess];

  for (const slot of withSeparatorSlots(state.mask)) {
    if (slot.separator !== undefined) {
      row.appendChild(separatorElement(slot.separator));
      continue;
    }
    const correct = feedback[slot.index];
    row.appendChild(
      textSpan(`tile ${correct ? "tile-correct" : "tile-wrong"}`, letters[slot.index])
    );
  }

  return row;
}

function renderAttemptsLeft(left) {
  state.attemptsLeft = left;
  document.getElementById("attempts-left").textContent = t("attempts_left", {
    left,
    max: MAX_ATTEMPTS,
  });
}

function renderHint(hint) {
  document.getElementById("hint").textContent = hint ? t("hint", { hint }) : "";
}

function renderPuzzle(puzzle) {
  showPuzzleArea();
  document.getElementById("date").textContent = puzzle.date;
  document.getElementById("category").textContent =
    puzzle.category === "book_title" ? t("category_book_title") : t("category_general");
  document.getElementById("length-caption").textContent = t("length_caption", {
    length: puzzle.length,
  });

  renderMaskRow(puzzle.mask);
  renderAttemptsLeft(puzzle.attempts_left);
  renderHint(puzzle.hint);
  renderBoard(puzzle.attempts);

  // 구분자를 넣어 쓸 수 있게 타일 수가 아니라 mask 길이(구분자 포함)로 제한한다 —
  // `Harry Potter`·`harry-potter`·`harrypotter` 는 같은 답이다(README "04. 제출 일관성").
  document.getElementById("guess-input").maxLength = puzzle.mask.length;

  if (puzzle.status === "in_progress") show("guess-form");
  else showResult(puzzle.status, puzzle.answer);
}

function showResult(status, answer) {
  // 서버가 내려준 진짜 결과를 기억해둔다 — buildShareText가 보드로 성공/실패를
  // 다시 판단하면, 다른 기기에서 이미 끝난 퍼즐을 열었을 때 틀린 결과를 공유한다.
  state.finalStatus = status;

  show("result");
  document.getElementById("result-text").textContent =
    status === "success" ? t("result_success", { answer }) : t("result_fail", { answer });
}

function showMessage(text) {
  document.getElementById("message").textContent = text;
}

// --- 퍼즐 재조회 · 로컬 상태 폐기 ---------------------------------------------

/** 메모리에 들고 있는 플레이 상태와, 옛 버전이 남겨둔 로컬 보드 이력을 버린다.
 *
 * 퍼즐 언어를 바꾸거나 계정·백업 코드로 다른 게스트가 되면 "지금 내 오늘 퍼즐"이
 * 통째로 달라진다. 토큰(TOKEN_KEY)과 백업 패널은 그대로 둔다.
 */
function discardLocalPlayState() {
  clearStoredHistory();

  // 여기서부터는 다른 세대다 — 지금 날아가 있는 요청들의 응답은 전부 남의 것이다.
  state.generation += 1;

  state.today = null;
  state.puzzleId = null;
  state.mask = [];
  state.length = 0;
  state.attemptsLeft = MAX_ATTEMPTS;
  state.finalStatus = null;
  state.attempts = [];

  document.getElementById("board").innerHTML = "";
  document.getElementById("mask-row").innerHTML = "";
  document.getElementById("guess-input").value = "";
  // 새 퍼즐을 받는 동안은 다시 로딩 상태다 — 퍼즐·폼·결과를 치우고 스켈레톤으로.
  showSkeleton();
  renderHint(null);
  showMessage("");
}

async function reloadPuzzle() {
  discardLocalPlayState();

  const puzzle = await loadToday();
  if (!puzzle) return;

  applyPuzzle(puzzle);
  loadLeaderboard();
  loadTodayStats();
}

function applyPuzzle(puzzle) {
  state.today = puzzle.date;
  state.puzzleId = puzzle.puzzle_id;
  state.mask = puzzle.mask;
  state.length = puzzle.length;
  state.attempts = puzzle.attempts;
  renderLanguageChips(puzzle.language);
  renderPuzzle(puzzle);
}

// --- 제출 -------------------------------------------------------------------

// 한글 IME는 마지막 글자를 조합 중일 때 Enter를 누르면 "조합 확정"과 "제출"이
// 겹쳐서 submit이 연달아 여러 번 난다. 응답이 오기 전엔 입력창이 안 비워지니
// 같은 답이 그대로 여러 번 제출돼 기회가 한꺼번에 날아갔다(실제로 겪음).
let isSubmitting = false;

function blockEnterWhileComposing(event) {
  if (event.key === "Enter" && (event.isComposing || event.keyCode === 229)) {
    event.preventDefault();
  }
}

async function handleSubmit(event) {
  event.preventDefault();
  if (isSubmitting) return;

  const input = document.getElementById("guess-input");
  const guess = input.value.trim();
  if (!guess) return;

  isSubmitting = true;
  try {
    await submitGuess(input, guess);
  } finally {
    isSubmitting = false;
  }
}

async function submitGuess(input, raw) {
  const guess = normalizeGuess(raw);
  // 응답을 기다리는 동안 보고 있던 퍼즐이 갈릴 수 있다 — 언어 칩은 제출 중에도
  // 눌리고, 계정·백업 전환이나 409 재조회도 같은 틈을 만든다. 그렇게 폐기한
  // 퍼즐의 응답을 지금 화면에 반영하면 보드·남은 기회·힌트·완료 표시가 전 퍼즐의
  // 답으로 오염된다(서버 기록은 멀쩡한데 화면만 틀린다). 그래서 요청을 보낸
  // 퍼즐 ID 와 상태 세대를 들고 있다가, 돌아왔을 때 둘 중 하나라도 다르면 통째로
  // 버린다. 세대까지 보는 이유: ko→en→ko 로 돌아오면 ID 는 다시 같아지는데,
  // 그 사이 보드는 서버 이력으로 복원됐다 — ID 만 보면 복원된 그 시도를 한 번 더
  // 그려서 같은 행이 두 번 보인다(review/impl-review-17.md D-17-1 REPEAT).
  const requestedPuzzleId = state.puzzleId;
  const { stale, ok, offline, body: data } = await fetchJson(`${API_BASE}/puzzles/today/guesses`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify({ puzzle_id: requestedPuzzleId, guess }),
  });

  if (stale || state.puzzleId !== requestedPuzzleId) return;

  // 제출이 아예 못 나갔다 — "오류" 가 아니라 "다시" 다.
  //
  // 안내만 `#message` 에 띄우면 복구할 길이 없다: `renderOffline(true)` 가 입력과
  // 제출 버튼을 잠그는데, `navigator.onLine` 이 계속 true 인 일시적 실패(DNS·연결
  // 끊김)에서는 `online` 이벤트가 영영 안 온다. 유일한 재시도 버튼은 숨어 있는
  // `#puzzle-state` 안이라, 사용자는 새로고침 말고는 빠져나올 수 없었다
  // (review/impl-review-18.md D-18-2). 그래서 조회 실패와 **같은** 인라인 카드로
  // 눕힌다 — 재시도가 서버에서 오늘 퍼즐과 시도 이력을 다시 받으므로, fetch 가
  // 죽은 사이에 제출이 실제로 서버에 닿았는지까지 화면이 서버와 다시 맞는다.
  if (offline) {
    renderOffline(true);
    showMessage("");
    showPuzzleState(t("network_error"));
    return;
  }

  if (data.code === "PUZZLE_CHANGED") {
    // 자정이 지났거나 다른 기기에서 언어를 바꿨다. 시도는 소비되지 않았으니
    // 보던 화면만 버리고 지금의 "오늘 내 퍼즐"을 다시 받는다. 안내는 재조회가
    // 화면을 비운 뒤에 띄운다 — 먼저 띄우면 discardLocalPlayState 가 지운다.
    await reloadPuzzle();
    showMessage(t("puzzle_changed"));
    return;
  }

  if (!ok) {
    showMessage(errorText(data, "generic_error"));
    return;
  }

  showMessage("");
  input.value = "";

  // 제출 응답은 정답일 때 `feedback: null` 이다 — 보낸 답이 정답이니 전부 맞음이다.
  const feedback = data.is_correct ? [...guess].map(() => true) : data.feedback;
  state.attempts.push({ guess, feedback });
  renderBoard(state.attempts);

  renderAttemptsLeft(data.attempts_left);
  if (data.hint) renderHint(data.hint);

  if (data.answer) {
    hide("guess-form");
    showResult(data.is_correct ? "success" : "fail", data.answer);
    loadStats();
    loadLeaderboard();
    loadTodayStats();
  }
}

// --- 순위 · 통계 -------------------------------------------------------------

function formatSeconds(totalSeconds) {
  const parts = [
    Math.floor(totalSeconds / 3600),
    Math.floor((totalSeconds % 3600) / 60),
    totalSeconds % 60,
  ];
  return parts.map((part) => String(part).padStart(2, "0")).join(":");
}

async function loadLeaderboard() {
  const message = document.getElementById("leaderboard-message");
  // 통계·리더보드는 "내가 안 고른 언어"도 볼 수 있는 엔드포인트라 언어를 명시한다.
  const { stale, ok, body } = await fetchJson(
    `${API_BASE}/puzzles/today/leaderboard?language=${state.puzzleLanguage}`,
    { headers: authHeaders() }
  );
  // 요청에 박아 보낸 언어가 지금 화면의 언어가 아니면, 이 순위표는 남의 퍼즐 것이다.
  if (stale) return;
  if (!ok) {
    message.textContent = t("leaderboard_load_failed");
    return;
  }

  renderLeaderboard(body);
}

function renderLeaderboard(data) {
  const list = document.getElementById("leaderboard-entries");
  const message = document.getElementById("leaderboard-message");
  list.innerHTML = "";
  message.textContent = data.entries.length === 0 ? t("leaderboard_empty") : "";

  for (const entry of data.entries) {
    const row = document.createElement("li");
    row.className = entry.is_me ? "leaderboard-entry is-me" : "leaderboard-entry";
    // 1~3위만 순위 숫자를 굵게 한다(OVERRIDES §2: brand 색 글자는 쓰지 않는다).
    row.appendChild(textSpan(entry.rank <= 3 ? "rank top" : "rank", `#${entry.rank}`));
    row.appendChild(
      textSpan(
        "entry-text",
        t("leaderboard_entry", {
          display: entry.display,
          attempts: entry.attempts,
          time: formatSeconds(entry.seconds),
        })
      )
    );
    list.appendChild(row);
  }

  // 내 순위는 페이지 밖(21위 이하)이어도 서버가 따로 내려준다.
  document.getElementById("my-rank").textContent = data.me
    ? t("my_rank", {
        rank: data.me.rank,
        attempts: data.me.attempts,
        time: formatSeconds(data.me.seconds),
      })
    : t("my_rank_unsolved");
}

async function loadTodayStats() {
  const { stale, ok, body } = await fetchJson(
    `${API_BASE}/puzzles/today/stats?language=${state.puzzleLanguage}`,
    { headers: authHeaders() }
  );
  if (stale) return;
  if (!ok) return;

  renderTodayStats(body);
}

function renderTodayStats(stats) {
  const list = document.getElementById("today-stats");
  list.innerHTML = "";

  if (stats.total_solved === 0) {
    list.appendChild(textSpan("stats-empty", t("stats_empty")));
    return;
  }

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    const ratio = stats.by_attempt[String(attempt)] ?? 0;
    const row = document.createElement("li");
    row.className = "stats-row";
    row.textContent = t("stats_row", { attempt, percent: Math.round(ratio * 100) });
    list.appendChild(row);
  }
}

// --- 공유 · 백업 코드 --------------------------------------------------------

function maskToText(mask) {
  // 공유 텍스트는 타일을 그릴 수 없으니 빈 칸을 "_"로 펼친다 (app/utils/mask.py
  // 의 mask_to_text 와 같은 자리표시자).
  return mask.map((tile) => (tile.t === HIDDEN ? "_" : tile.c)).join("");
}

function buildShareText() {
  // finalStatus/attemptsLeft 는 서버 응답에서만 설정된다 — 보드로 성공/실패나 시도
  // 횟수를 되짚으면, 다른 기기에서 이미 끝난 퍼즐을 열었을 때 틀린 결과를 공유한다.
  const used = MAX_ATTEMPTS - state.attemptsLeft;
  const resultLine =
    state.finalStatus === "success"
      ? t("share_success", { used, max: MAX_ATTEMPTS })
      : t("share_fail", { used, max: MAX_ATTEMPTS });

  const lines = [
    t("share_heading", { date: state.today }),
    t("share_puzzle", { mask: maskToText(state.mask), length: state.length }),
    resultLine,
  ];

  if (state.attempts.length > 0) {
    const grid = state.attempts
      .map(({ feedback }) => feedback.map((ok) => (ok ? "🟩" : "⬜")).join(""))
      .join("\n");
    lines.push("", grid);
  }

  // 받은 사람이 바로 플레이할 수 있게 웹 링크를 마지막 줄에 붙인다(US 11).
  lines.push("", SHARE_URL);

  return lines.join("\n");
}

// 공유 버튼과 토큰 백업 버튼이 똑같은 "복사하고 잠깐 체크 표시" 패턴을 쓴다.
async function copyToClipboard(text, feedbackElId) {
  try {
    await navigator.clipboard.writeText(text);
    const feedback = document.getElementById(feedbackElId);
    feedback.classList.remove("hidden");
    setTimeout(() => feedback.classList.add("hidden"), 2000);
  } catch {
    showMessage(`${t("clipboard_unsupported")}\n\n${text}`);
  }
}

async function handleShare() {
  await copyToClipboard(buildShareText(), "share-copied");
}

function togglePanel(panelId, otherPanelId) {
  const panel = document.getElementById(panelId);
  document.getElementById(otherPanelId).classList.add("hidden");
  panel.classList.toggle("hidden");
}

function handleBackupClick() {
  document.getElementById("token-display").value = state.token;
  togglePanel("backup-panel", "restore-panel");
}

function handleRestoreClick() {
  togglePanel("restore-panel", "backup-panel");
}

async function handleCopyToken() {
  await copyToClipboard(state.token, "copy-token-done");
}

async function handleRestoreSubmit() {
  const input = document.getElementById("token-input");
  const token = input.value.trim();
  const restoreMessage = document.getElementById("restore-message");
  if (!token) return;

  // 붙여넣은 코드가 진짜 유효한 토큰인지, 아무 보호된 API나 하나 불러서 확인한다
  // (전용 "토큰 검증" 엔드포인트는 없어서 /me/stats로 겸한다).
  const res = await fetch(`${API_BASE}/me/stats`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    restoreMessage.textContent = t("restore_invalid_code");
    return;
  }

  safeStorageSet(TOKEN_KEY, token);
  // 다른 게스트로 전환된다 — 이전 게스트의 화면이 한 프레임도 남지 않게 통째로
  // 다시 그린다.
  discardLocalPlayState();
  location.reload();
}

async function syncSession() {
  // "이 브라우저 = 이 게스트"를 서버 세션 쿠키에 남긴다. 로그인 버튼이 더 이상
  // 토큰을 쿼리파라미터로 안 보내는 이유는 app/api/oauth.py의 sync_session
  // 독스트링 참고 — 쿼리파라미터는 아무 값이나 넣은 링크를 피해자가 클릭하게
  // 만들 수 있어서(로그인 CSRF), 세션 쿠키로 바꿨다.
  await fetch(`${API_BASE}/session/sync`, {
    method: "POST",
    headers: authHeaders(),
  });
}

/** 인라인 카드의 재시도 버튼. 오류든 "퍼즐 없음" 이든 하는 일은 같다 —
 *  첫 화면을 처음부터 다시 받아온다(게스트 발급이 실패했으면 발급부터). */
async function handleRetry() {
  await restart();
}

/** 연결이 돌아왔다. 배너를 내리고, 못 받았던 것들을 알아서 다시 받는다 —
 *  재시도 버튼을 누르게 만들지 않는다. */
async function handleOnline() {
  renderOffline(false);
  await restart();
}

function handleOffline() {
  renderOffline(true);
}

function handleOAuthLogin(provider) {
  // provider 로그인 자체가 전체 페이지 이동(리다이렉트)이라 fetch가 아니라
  // location.href로 이동한다. 어느 게스트인지는 서버가 세션 쿠키(syncSession이
  // 미리 심어둠)로 판단하므로 여기서 토큰을 실어 보낼 필요가 없다.
  location.href = `${API_BASE}/auth/${provider}/login`;
}

// 저장된 토큰이 서버에서 이미 지워졌는지 확인한다. 401이면 "지워졌다"가 확실하다.
// 확인 자체를 못 했으면(오프라인·5xx) null — 모르는 상태와 지워진 상태를 섞으면
// 네트워크가 끊겼을 때 멀쩡한 토큰을 버린다.
async function guestTokenIsGone(token) {
  try {
    const res = await fetch(`${API_BASE}/me/history?days=1`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) return true;
    if (res.ok) return false;
    return null;
  } catch {
    return null;
  }
}

// 계정 삭제(/account/delete)가 끝나면 서버가 /?deleted=1로 돌려보낸다. 지워진
// 토큰을 그대로 들고 있으면 모든 API가 401이라, 저장된 토큰과 이 기기에 남은
// 보드 기록을 버린다 — 그러면 아래 ensureToken()이 새 게스트를 발급받는다.
// 옛 보드 기록(LEGACY_HISTORY_PREFIX)까지 지우는 이유: 토큰만 버리면 그 키가
// 남아 다음 정리까지 옛 게스트의 흔적이 기기에 남는다.
//
// 쿼리파라미터는 "신호"일 뿐 증거가 아니다. 다른 사이트가 보낸 /?deleted=1 링크를
// 누르기만 해도 같은 분기를 타는데(삭제 POST의 CSRF 방어를 안 거친다), 계정 연결도
// 백업 코드도 없는 플레이어에게 이 토큰은 유일한 복구 수단이다. 그래서 서버에
// 토큰을 들이밀어 정말 지워졌는지(401) 확인한 뒤에만 버린다.
async function discardDeletedAccountState() {
  const params = new URLSearchParams(location.search);
  if (!params.has("deleted")) return;

  const token = safeStorageGet(TOKEN_KEY);
  const gone = token ? await guestTokenIsGone(token) : false;
  // 확인을 못 했으면 아무것도 지우지 않고 신호도 주소창에 남긴다 — 새로고침이나
  // 다음 방문에서 다시 확인해야 지워진 계정의 토큰을 계속 들고 돌지 않는다.
  if (gone === null) return;

  params.delete("deleted");
  const query = params.toString();
  history.replaceState({}, "", location.pathname + (query ? `?${query}` : ""));
  // 가짜 신호였다 — 살아 있는 게스트의 토큰·기록은 그대로 둔다.
  if (!gone) return;

  safeStorageRemove(TOKEN_KEY);
  clearStoredHistory();

  showMessage(t("account_deleted"));
}

// 로그인 콜백이 끝나면 /?login_token=<새 토큰>으로 돌아온다. 있으면 저장하고
// URL에서 지운다(새로고침해도 다시 안 보이게, 그리고 주소창에 토큰이 안 남게).
function applyLoginTokenFromUrl() {
  const params = new URLSearchParams(location.search);
  const loginToken = params.get("login_token");
  if (!loginToken) return;

  safeStorageSet(TOKEN_KEY, loginToken);
  // 계정 전환이면 게스트가 바뀐다 — 옛 게스트의 로컬 보드 이력을 들고 있지 않는다.
  clearStoredHistory();
  params.delete("login_token");
  const query = params.toString();
  history.replaceState({}, "", location.pathname + (query ? `?${query}` : ""));
}

function bindEvents() {
  document.getElementById("guess-form").addEventListener("submit", handleSubmit);
  document.getElementById("guess-input").addEventListener("keydown", blockEnterWhileComposing);
  document.getElementById("share-button").addEventListener("click", handleShare);
  document
    .getElementById("google-login-button")
    .addEventListener("click", () => handleOAuthLogin("google"));
  document
    .getElementById("apple-login-button")
    .addEventListener("click", () => handleOAuthLogin("apple"));
  document.getElementById("backup-button").addEventListener("click", handleBackupClick);
  document.getElementById("restore-button").addEventListener("click", handleRestoreClick);
  document.getElementById("copy-token-button").addEventListener("click", handleCopyToken);
  document.getElementById("restore-submit-button").addEventListener("click", handleRestoreSubmit);

  document.getElementById("puzzle-state-retry").addEventListener("click", handleRetry);

  for (const chip of document.querySelectorAll("[data-puzzle-language]")) {
    chip.addEventListener("click", () => handleLanguageChange(chip.dataset.puzzleLanguage));
  }

  for (const link of document.querySelectorAll("[data-section]")) {
    link.addEventListener("click", () => showSection(link.dataset.section));
  }

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);
}

/** 첫 화면 한 벌: 게스트 발급 → 통계 → 오늘 퍼즐 → 순위·오늘 통계.
 *
 * `init()` 과 재시도 버튼·`online` 이벤트가 **같은** 함수를 쓴다. 발급이 실패한
 * 첫 방문도 복구는 똑같이 "처음부터 다시" 라서, 재시도 경로를 퍼즐 재조회
 * (`reloadPuzzle`)에만 걸어두면 토큰이 없는 화면은 영영 못 빠져나온다
 * (review/impl-review-18.md D-18-1).
 *
 * 어느 단계가 실패하든 그 단계가 인라인 상태 카드를 띄우고 멈춘다 — 카드의
 * 재시도 버튼이 다시 여기로 들어온다.
 */
async function restart() {
  // 다시 받는 동안은 로딩 상태다. 들고 있던 플레이 상태도 같이 버린다 —
  // 끊겼던 사이에 다른 기기에서 푼 시도가 서버에 있을 수 있다.
  discardLocalPlayState();

  if (!(await ensureToken())) return;
  loadStats();

  const puzzle = await loadToday();
  if (!puzzle) return;

  applyPuzzle(puzzle);
  loadLeaderboard();
  loadTodayStats();
}

async function init() {
  // 재시도 버튼과 `online`/`offline` 은 **첫 요청보다 먼저** 살아 있어야 한다 —
  // 뒤에 두면 게스트 발급이 실패한 첫 방문에서 복구 수단이 하나도 없다(D-18-1).
  bindEvents();
  // 비행기 모드로 들어온 방문자는 첫 요청이 실패하기 전에 이유를 알아야 한다.
  renderOffline(!navigator.onLine);

  await discardDeletedAccountState(); // 삭제가 확인되면 옛 토큰을 먼저 버린다
  applyLoginTokenFromUrl();
  clearStoredHistory();

  await restart();
}

init();
