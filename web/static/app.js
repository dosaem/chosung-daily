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
    `연속 ${stats.current_streak}일 (최고 ${stats.max_streak}일) · 누적 ${stats.solved_count}문제`;
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

async function handleSubmit(event) {
  event.preventDefault();

  const input = document.getElementById("guess-input");
  const guess = input.value.trim();
  if (!guess) return;

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

async function handleShare() {
  const text = buildShareText();
  try {
    await navigator.clipboard.writeText(text);
    const copied = document.getElementById("share-copied");
    copied.classList.remove("hidden");
    setTimeout(() => copied.classList.add("hidden"), 2000);
  } catch {
    showMessage(`클립보드 복사를 지원하지 않는 환경이에요. 직접 복사해주세요:\n\n${text}`);
  }
}

async function init() {
  state.token = await ensureToken();

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
  document.getElementById("share-button").addEventListener("click", handleShare);
}

init();
