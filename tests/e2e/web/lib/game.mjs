import { AxeBuilder } from "@axe-core/playwright";
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { ARTIFACT_ROOT, BASE_URL, puzzleFor } from "./env.mjs";
import { format, uiStrings } from "./strings.mjs";

/**
 * 셀렉터 규칙(브리프: "접근성 라벨·보이는 텍스트 우선")
 *
 * - **누르는 것**은 전부 role + 보이는 이름이다(`getByRole`/`getByPlaceholder`).
 *   버튼 이름은 서버 사전에서 온 실제 문구라, 문구가 바뀌면 테스트가 같이 깨진다.
 * - **읽는 것** 중 역할이 없는 상태 영역(`#attempts-left`, `#board`, `#streak` …)은
 *   id 로 집는다. 이 자리들은 `<p>`·`<div>` 라서 접근성 역할이 없고, 텍스트로
 *   찾으면 "남은 기회 4/5" 같은 값 자체를 셀렉터에 적어야 해서 무엇을 검증하는지가
 *   사라진다. id 로 집어서 **내용을 단정**하는 쪽을 골랐다.
 * - 테스트 전용 속성(`data-testid`)은 쓰지 않는다 — 앱 코드를 건드리지 않는다.
 */

export const MAX_ATTEMPTS = 5;

// 오답을 만들 때 끼워 넣는 글자. 뜻이 있는 단어를 쓰지 않는다 — 길이가 정답과
// 같아야 서버가 길이 검증으로 막지 않고 **오답으로 채점**하고, 그래야 기회가 줄어든다.
const FILLERS = {
  ko: ["가", "나", "다", "라", "마", "바", "사"],
  en: ["x", "y", "z", "q", "w", "k", "v"],
};

/**
 * 정답에서 글자 하나만 바꾼 오답. 피드백 타일이 "맞은 자리 / 틀린 자리" 를 섞어
 * 보여주는지를 보려면 전부 틀린 답으로는 안 된다.
 *
 * 정답을 하드코딩하지 않고 **정답에서 만든다**: 시드가 못박은 단어가 바뀌거나
 * 하루를 넘겨 다음 단어가 오늘이 되면, 적어둔 오답은 길이가 어긋나서 서버가
 * 채점 자체를 안 한다(그러면 이 시나리오는 아무것도 검증하지 않는다).
 */
export function nearMiss(answer, language) {
  const chars = [...answer];
  const position = Math.floor(chars.length / 2);
  const filler = FILLERS[language].find((candidate) => candidate !== chars[position]);
  chars[position] = filler;
  return chars.join("");
}

/** 같은 길이의 서로 다른 오답 `count` 개. `nearMiss` 와 같은 이유로 만들어 쓴다. */
export function wrongGuesses(answer, language, count) {
  const chars = [...answer];
  const out = [];
  for (let step = 0; out.length < count && step < count * FILLERS[language].length; step += 1) {
    const candidate = [...chars];
    candidate[out.length % chars.length] = FILLERS[language][step % FILLERS[language].length];
    const text = candidate.join("");
    if (text !== answer && !out.includes(text)) out.push(text);
  }
  if (out.length < count) throw new Error(`${answer} 로 서로 다른 오답 ${count}개를 못 만들었다`);
  return out;
}

/** 시나리오 하나의 산출물 폴더 + 단계 로그. `e2e-artifacts/web/<시나리오>/<뷰포트>/` */
export function scene(testInfo, scenario) {
  const dir = path.join(ARTIFACT_ROOT, scenario, testInfo.project.name);
  mkdirSync(dir, { recursive: true });
  const logPath = path.join(dir, "steps.log");
  writeFileSync(logPath, `# ${scenario} (${testInfo.project.name})\n`);
  let order = 0;

  return {
    dir,
    /** 사람이 한 동작 하나를 로그에 적고, 그 직후 화면을 남긴다. */
    async step(page, label) {
      order += 1;
      const stamp = new Date().toISOString();
      const slug = `${String(order).padStart(2, "0")}-${label
        .replace(/[^\p{L}\p{N}]+/gu, "-")
        .replace(/^-|-$/g, "")}`;
      appendFileSync(logPath, `${stamp} ${slug}\n`);
      await page.screenshot({ path: path.join(dir, `${slug}.png`), fullPage: true });
      return slug;
    },
    note(line) {
      appendFileSync(logPath, `${new Date().toISOString()} NOTE ${line}\n`);
    },
  };
}

/** 새 브라우저 컨텍스트에서 게임 화면을 연다. 저장소가 비어 있는 = 첫 방문이다.
 *
 * `lang` 은 **기기 언어**다(`locale`). 서버가 `?lang=` 없이 Accept-Language 로
 * UI 언어를 고르는 그 경로를 그대로 타려고 쿼리파라미터를 쓰지 않는다
 * (`?lang=` 경로는 시나리오 6 이 따로 본다).
 */
export async function openGame(browser, { lang = "ko", baseURL = BASE_URL, ...rest } = {}) {
  const context = await browser.newContext({
    // `browser.newContext()` 는 프로젝트의 `use` 를 **물려받지 않는다** — 기본
    // 1280×720 데스크톱으로 열린다. 그러면 mobile-390 프로젝트가 데스크톱을 한 번
    // 더 도는 셈이라, 폭·터치·DPR 을 여기서 직접 가져온다(한 시나리오를 두 뷰포트로
    // 돌리는 게 이 티켓의 요구사항이다).
    ...deviceOptions(),
    baseURL,
    locale: lang === "en" ? "en-US" : "ko-KR",
    timezoneId: "Asia/Seoul",
    permissions: ["clipboard-read", "clipboard-write"],
    ...rest,
  });
  const page = await context.newPage();
  await page.goto("/");
  await waitForPuzzle(page);
  return { context, page };
}

/** 지금 프로젝트의 기기 옵션만 골라낸다. `screenshot`·`trace` 같은 테스트 러너
 *  전용 옵션은 `newContext` 가 받지 않으므로 화이트리스트로 집는다. */
function deviceOptions() {
  const use = test.info().project.use ?? {};
  const picked = {};
  for (const key of ["viewport", "deviceScaleFactor", "isMobile", "hasTouch", "userAgent", "screen"]) {
    if (use[key] !== undefined) picked[key] = use[key];
  }
  return picked;
}

/** 문제 타일이 그려질 때까지 기다린다 — 스켈레톤이 걷히고 플레이할 수 있는 상태. */
export async function waitForPuzzle(page) {
  await expect(page.locator("#mask-row .tile").first()).toBeVisible();
  await expect(page.locator("#date")).not.toBeEmpty();
}

/** 화면에 보이는 날짜의 (시드가 못박은) 정답·힌트. */
export async function todaysPuzzle(page, language) {
  const date = (await page.locator("#date").textContent()).trim();
  return { date, ...puzzleFor(date, language) };
}

/** 사람처럼 답을 적어 제출한다 — 입력창에 타이핑하고 제출 버튼을 누른다. */
export async function guess(page, text) {
  const t = await uiStrings(page);
  const before = await page.locator("#board .tile-row").count();
  await page.getByPlaceholder(t.guess_placeholder).fill(text);
  await page.getByRole("button", { name: t.submit }).click();
  // 제출 결과는 보드에 한 행으로 쌓인다. 행이 늘어난 것으로 "서버가 답했다" 를 안다.
  await expect(page.locator("#board .tile-row")).toHaveCount(before + 1);
}

/** 남은 기회 문구가 서버 사전의 `attempts_left` 와 맞는지. */
export async function expectAttemptsLeft(page, left) {
  const t = await uiStrings(page);
  await expect(page.locator("#attempts-left")).toHaveText(
    format(t.attempts_left, { left, max: MAX_ATTEMPTS }),
  );
}

/** 보드 마지막 행의 타일 판정(맞은 자리 true / 틀린 자리 false). */
export async function lastRowFeedback(page) {
  return page.locator("#board .tile-row").last().locator(".tile").evaluateAll((tiles) =>
    tiles.map((tile) => tile.classList.contains("tile-correct")),
  );
}

export async function showSection(page, key) {
  const t = await uiStrings(page);
  const name = { today: t.nav_today, leaderboard: t.nav_leaderboard, records: t.nav_records }[key];
  await page.getByRole("button", { name, exact: true }).click();
  await expect(page.getByRole("button", { name, exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
}

/** 퍼즐 언어 칩을 눌러 문제 언어를 바꾼다(UI 언어와 별개). */
export async function choosePuzzleLanguage(page, language) {
  const t = await uiStrings(page);
  const label = language === "en" ? t.puzzle_language_en : t.puzzle_language_ko;
  await page.getByRole("button", { name: label, exact: true }).click();
  await expect(page.locator(`[data-puzzle-language="${language}"]`)).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await waitForPuzzle(page);
}

/**
 * axe 검사. 위반이 있으면 **테스트를 실패시키지 않고** 결과를 파일로 남기고
 * 돌려준다 — 접근성 위반은 "앱 결함" 이라 고치지 말고 기록하라는 브리프 규칙을
 * 따른다(증거 문서 `## 발견한 결함`). 부르는 쪽이 0건을 단정한다.
 */
export async function axeScan(page, dir, name) {
  const results = await new AxeBuilder({ page })
    // WCAG 2.1 A/AA 만 본다 — best-practice 규칙은 디자인 결정과 부딪친다.
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const violations = results.violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    help: v.help,
    nodes: v.nodes.map((n) => n.target.join(" ")),
  }));
  writeFileSync(
    path.join(dir, `axe-${name}.json`),
    JSON.stringify({ url: results.url, violations }, null, 2),
  );
  return violations;
}

/**
 * axe 결과를 단정한다. **이미 기록한 결함**(`known`)은 soft 로 — 테스트는 여전히
 * 실패하지만(결함이 가려지지 않는다) 시나리오의 나머지는 계속 돈다. 기록에 없는
 * 새 위반은 그 자리에서 hard 로 끊는다.
 *
 * `known` 은 `[{ id, target, defect }]` 다. 결함이 고쳐지면 여기서 지우면 된다 —
 * 지우지 않으면 "고쳐졌는데 known 에 남아 있다" 가 아래 단정에서 걸린다.
 */
export function expectAxeClean(violations, known = []) {
  const matches = (violation, entry) =>
    violation.id === entry.id && violation.nodes.some((node) => node.includes(entry.target));

  const unexpected = violations.filter((v) => !known.some((k) => matches(v, k)));
  expect(unexpected, `기록에 없는 접근성 위반:\n${JSON.stringify(unexpected, null, 2)}`).toEqual(
    [],
  );

  for (const entry of known) {
    const hit = violations.find((v) => matches(v, entry));
    expect.soft(
      hit ? `${entry.defect}: ${hit.id} @ ${entry.target}` : null,
      `${entry.defect} 이 고쳐졌다면 이 known 항목을 지워라`,
    ).toBe(null);
  }
}
