const API_BASE = "/api/v1";
const TOKEN_KEY = "chosung_token";

const state = {
  token: null,
  today: null,
  chosung: null,
  length: 0,
  history: [], // [{ guess, feedback: bool[] }], feedback은 항상 채워서 저장한다
  // 아래 둘은 서버 응답(renderPuzzle/handleSubmit/showResult)에서만 설정한다.
  // "다른 기기에서 열어서 history가 비어있는" 경우에도 공유 텍스트가 history로
  // 성공/실패·시도 횟수를 되짚어 틀리지 않도록, 서버가 내려준 값을 그대로 믿는다.
  attemptsLeft: 5,
  finalStatus: null,
};

function authHeaders() {
  return { Authorization: `Bearer ${state.token}` };
}

function historyKey(date) {
  return `chosung_history_${date}`;
}

// localStorage는 프라이빗 모드 등에서 접근 자체가 던질 수 있다 — 게임 플레이에
// 필수는 아닌 기능(기록 저장, 토큰 재사용)이라 항상 이 두 함수로만 접근하고,
// 실패하면 조용히 넘어간다.
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

function loadHistory(date) {
  const raw = safeStorageGet(historyKey(date));
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveHistory() {
  safeStorageSet(historyKey(state.today), JSON.stringify(state.history));
}

async function ensureToken() {
  const existing = safeStorageGet(TOKEN_KEY);
  if (existing) return existing;

  const res = await fetch(`${API_BASE}/guests`, { method: "POST" });
  if (!res.ok) {
    showMessage("게스트 발급에 실패했어요. 새로고침해서 다시 시도해주세요.");
    throw new Error("failed to issue guest token");
  }

  const data = await res.json();
  safeStorageSet(TOKEN_KEY, data.token);
  return data.token;
}

async function loadToday() {
  const res = await fetch(`${API_BASE}/puzzles/today`, { headers: authHeaders() });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    showMessage(body.message || "오늘의 퍼즐을 불러오지 못했어요.");
    return null;
  }
  return res.json();
}

async function loadStats() {
  const streakEl = document.getElementById("streak");
  const res = await fetch(`${API_BASE}/me/stats`, { headers: authHeaders() });
  if (!res.ok) {
    // 게임 자체엔 영향 없는 보조 정보라 #message로 크게 띄우진 않지만, 조용히
    // 묵혀서 "기록이 0일인가?"로 헷갈리게 두지도 않는다.
    streakEl.textContent = "기록을 불러오지 못했어요.";
    return;
  }
  const stats = await res.json();
  streakEl.textContent =
    `🔥 연속 ${stats.current_streak}일 · 최고 ${stats.max_streak}일 · 누적 ${stats.solved_count}문제`;
  renderLinkedAccount(stats.linked_account);
}

// 로그인 버튼은 provider 연결 전까지만 보여준다 — 연결된 뒤엔 어떤 계정으로
// 연결됐는지 보여주고, 같은 게스트에 또 연결 시도할 일이 없게 버튼을 숨긴다.
function renderLinkedAccount(linkedAccount) {
  const el = document.getElementById("linked-account");
  const providerLabel = { google: "구글", apple: "Apple" };

  if (!linkedAccount) {
    el.classList.add("hidden");
    document.getElementById("google-login-button").classList.remove("hidden");
    document.getElementById("apple-login-button").classList.remove("hidden");
    return;
  }

  const label = providerLabel[linkedAccount.provider] ?? linkedAccount.provider;
  el.textContent = linkedAccount.email
    ? `✅ ${label} 계정으로 로그인됨 (${linkedAccount.email})`
    : `✅ ${label} 계정으로 로그인됨`;
  el.classList.remove("hidden");
  document.getElementById("google-login-button").classList.add("hidden");
  document.getElementById("apple-login-button").classList.add("hidden");
}

function renderPuzzle(puzzle) {
  document.getElementById("date").textContent = puzzle.date;
  document.getElementById("category").textContent =
    puzzle.category === "book_title" ? "책 제목" : "일반 단어";
  document.getElementById("chosung").textContent = puzzle.chosung;
  document.getElementById("attempts-left").textContent = `남은 기회 ${puzzle.attempts_left}/5`;
  state.attemptsLeft = puzzle.attempts_left;

  const input = document.getElementById("guess-input");
  input.maxLength = puzzle.length;

  if (puzzle.hint) {
    document.getElementById("hint").textContent = `힌트: ${puzzle.hint}`;
  }

  if (puzzle.status !== "in_progress") {
    document.getElementById("guess-form").classList.add("hidden");
    showResult(puzzle.status, puzzle.answer);
  }
}

function renderHistory() {
  const container = document.getElementById("history");
  container.innerHTML = "";

  for (const { guess, feedback } of state.history) {
    const row = document.createElement("div");
    row.className = "history-row";

    [...guess].forEach((ch, i) => {
      const cell = document.createElement("span");
      cell.className = `cell ${feedback[i] ? "correct" : "wrong"}`;
      cell.textContent = ch;
      row.appendChild(cell);
    });

    container.appendChild(row);
  }
}

function showResult(status, answer) {
  // 서버가 내려준 진짜 결과를 기억해둔다 — buildShareText가 로컬 history로
  // 성공/실패를 다시 판단하면, history가 없는 환경(다른 기기, 지워진
  // localStorage)에서 이미 끝난 퍼즐을 열었을 때 틀린 결과를 공유하게 된다.
  state.finalStatus = status;

  document.getElementById("result").classList.remove("hidden");
  document.getElementById("result-text").textContent =
    status === "success" ? `정답은 "${answer}"였어요!` : `아쉬워요, 정답은 "${answer}"였어요.`;
}

function showMessage(text) {
  document.getElementById("message").textContent = text;
}

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

async function submitGuess(input, guess) {
  const res = await fetch(`${API_BASE}/puzzles/today/guesses`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ guess }),
  });
  const data = await res.json();

  if (!res.ok) {
    showMessage(data.message || "오류가 발생했어요.");
    return;
  }

  showMessage("");
  input.value = "";

  const feedback = data.is_correct ? [...guess].map(() => true) : data.feedback;
  state.history.push({ guess, feedback });
  saveHistory();
  renderHistory();

  document.getElementById("attempts-left").textContent = `남은 기회 ${data.attempts_left}/5`;
  state.attemptsLeft = data.attempts_left;
  if (data.hint) {
    document.getElementById("hint").textContent = `힌트: ${data.hint}`;
  }

  if (data.answer) {
    document.getElementById("guess-form").classList.add("hidden");
    showResult(data.is_correct ? "success" : "fail", data.answer);
    loadStats();
  }
}

function buildShareText() {
  // finalStatus/attemptsLeft는 서버 응답(showResult, renderPuzzle/handleSubmit)에서만
  // 설정된다 — 로컬 history로 성공/실패나 시도 횟수를 되짚으면, history가
  // 비어있는 환경(다른 기기, 지워진 localStorage)에서 이미 끝난 퍼즐을 열었을 때
  // 틀린 결과를 공유할 수 있다. attemptsLeft는 history 없이도 서버가 늘 내려주므로
  // 항상 정확하다.
  const attemptsUsed = 5 - state.attemptsLeft;
  const resultLine =
    state.finalStatus === "success" ? `${attemptsUsed}/5 성공` : `${attemptsUsed}/5 실패`;

  const lines = [`오늘의 초성 ${state.today}`, `${state.chosung} (${state.length}글자)`, resultLine];

  if (state.history.length > 0) {
    const grid = state.history
      .map(({ feedback }) => feedback.map((ok) => (ok ? "🟩" : "⬜")).join(""))
      .join("\n");
    lines.push("", grid);
  }

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
    showMessage(`클립보드 복사를 지원하지 않는 환경이에요. 직접 복사해주세요:\n\n${text}`);
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
    restoreMessage.textContent = "올바르지 않은 백업 코드예요. 다시 확인해주세요.";
    return;
  }

  safeStorageSet(TOKEN_KEY, token);
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

function handleOAuthLogin(provider) {
  // provider 로그인 자체가 전체 페이지 이동(리다이렉트)이라 fetch가 아니라
  // location.href로 이동한다. 어느 게스트인지는 서버가 세션 쿠키(syncSession이
  // 미리 심어둠)로 판단하므로 여기서 토큰을 실어 보낼 필요가 없다.
  location.href = `${API_BASE}/auth/${provider}/login`;
}

// 로그인 콜백이 끝나면 /?login_token=<새 토큰>으로 돌아온다. 있으면 저장하고
// URL에서 지운다(새로고침해도 다시 안 보이게, 그리고 주소창에 토큰이 안 남게).
function applyLoginTokenFromUrl() {
  const params = new URLSearchParams(location.search);
  const loginToken = params.get("login_token");
  if (!loginToken) return;

  safeStorageSet(TOKEN_KEY, loginToken);
  params.delete("login_token");
  const query = params.toString();
  history.replaceState({}, "", location.pathname + (query ? `?${query}` : ""));
}

async function init() {
  applyLoginTokenFromUrl();
  state.token = await ensureToken();
  syncSession(); // 응답을 기다릴 필요 없음 — 로그인 버튼 누르기 전까지만 심어지면 된다.

  const puzzle = await loadToday();
  if (!puzzle) return;

  state.today = puzzle.date;
  state.chosung = puzzle.chosung;
  state.length = puzzle.length;
  state.history = loadHistory(puzzle.date);

  renderPuzzle(puzzle);
  renderHistory();
  loadStats();

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
  document
    .getElementById("restore-submit-button")
    .addEventListener("click", handleRestoreSubmit);
}

init();
