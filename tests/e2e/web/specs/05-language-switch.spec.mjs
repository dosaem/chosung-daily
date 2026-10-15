import { expect, test } from "@playwright/test";
import {
  choosePuzzleLanguage,
  guess,
  openGame,
  scene,
  showSection,
  todaysPuzzle,
  waitForPuzzle,
} from "../lib/game.mjs";
import { LITERALS } from "../lib/i18n-literals.mjs";
import { uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 6 — 언어 전환이 퍼즐·UI·순위 표기에 반영된다.
 *
 * 이 서비스에는 **언어가 둘**이다(CONTEXT.md): 기기 UI 언어와 플레이어가 칩으로
 * 고르는 퍼즐 언어. 둘이 독립이라는 것까지 본다 — ko UI 로 en 퍼즐을 풀 수 있다.
 */
test("[6] 퍼즐 언어 칩 ko↔en + UI 언어 ko↔en 이 각각 따로 반영된다", async ({
  browser,
}, testInfo) => {
  const art = scene(testInfo, "05-language-switch");

  // --- ko UI 로 시작: 퍼즐 칩으로 en 문제로 갈아탄다 --------------------------
  const { context, page } = await openGame(browser, { lang: "ko" });
  const ko = await uiStrings(page);
  expect(ko.app_title).toBe(LITERALS.ko.appTitle);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(LITERALS.ko.appTitle);
  await expect(page.locator("html")).toHaveAttribute("lang", "ko");

  const koPuzzle = await todaysPuzzle(page, "ko");
  await expect(page.locator("#mask-row .tile")).toHaveCount(koPuzzle.length);
  await art.step(page, "koUI-ko퍼즐");

  await choosePuzzleLanguage(page, "en");
  const enPuzzle = await todaysPuzzle(page, "en");
  // 문제가 실제로 바뀌었다: 길이도, 가림 글자도 다른 단어의 것이다.
  await expect(page.locator("#mask-row .tile")).toHaveCount(enPuzzle.length);
  expect(enPuzzle.answer).not.toBe(koPuzzle.answer);
  // UI 는 그대로 ko 다 — 퍼즐 언어는 UI 언어가 아니다.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(LITERALS.ko.appTitle);
  await expect(page.locator("#length-caption")).toHaveText(`${enPuzzle.length}글자`);
  await art.step(page, "koUI-en퍼즐");

  // ko UI 로 en 문제를 푼다. 순위 표기는 ko 접두사다.
  await guess(page, enPuzzle.answer);
  await showSection(page, "leaderboard");
  await expect(page.locator("#leaderboard-entries li.is-me")).toContainText(
    LITERALS.ko.guestPrefix,
  );
  await art.step(page, "koUI-en순위");

  // --- 같은 사람이 UI 언어만 en 으로 바꾼다(`?lang=en`) ----------------------
  const response = await page.goto("/?lang=en");
  // 프록시·CDN 이 ko 페이지를 en 방문자에게 주지 않게 서버가 언어를 명시한다.
  expect(response.headers()["content-language"]).toBe("en");
  await waitForPuzzle(page);
  const en = await uiStrings(page);
  expect(en.app_title).toBe(LITERALS.en.appTitle);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(LITERALS.en.appTitle);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  // 퍼즐 언어 선호는 서버가 들고 있다 — UI 언어를 바꿔도 en 문제 그대로다.
  await expect(page.locator("[data-puzzle-language='en']")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  const stillEn = await todaysPuzzle(page, "en");
  expect(stillEn.answer).toBe(enPuzzle.answer);
  // 칩 라벨도 en 사전으로 바뀐다("한국어" → "Korean").
  await expect(page.locator("[data-puzzle-language='ko']")).toHaveText(
    LITERALS.en.puzzleLanguageChipKo,
  );
  await art.step(page, "enUI-en퍼즐");

  // 순위 표기가 en 접두사로 바뀐다 — 같은 서버 응답(태그만)에 UI 언어가 접두사를 붙인다.
  await showSection(page, "leaderboard");
  await expect(page.locator("#leaderboard-entries li.is-me")).toContainText(
    LITERALS.en.guestPrefix,
  );
  await expect(page.locator("#leaderboard-entries li.is-me")).not.toContainText(
    LITERALS.ko.guestPrefix,
  );
  await art.step(page, "enUI-en순위");

  // --- 퍼즐 칩으로 ko 문제로 되돌아오면 보던 보드가 돌아온다 -----------------
  await showSection(page, "today");
  await choosePuzzleLanguage(page, "ko");
  const backToKo = await todaysPuzzle(page, "ko");
  expect(backToKo.answer).toBe(koPuzzle.answer);
  await expect(page.locator("#length-caption")).toHaveText(`${koPuzzle.length} letters`);
  await art.step(page, "enUI-ko퍼즐");

  await context.close();
});
