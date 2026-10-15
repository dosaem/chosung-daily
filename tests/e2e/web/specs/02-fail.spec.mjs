import { expect, test } from "@playwright/test";
import {
  axeScan,
  expectAxeClean,
  expectAttemptsLeft,
  guess,
  MAX_ATTEMPTS,
  openGame,
  scene,
  todaysPuzzle,
  wrongGuesses,
} from "../lib/game.mjs";
import { format, uiStrings } from "../lib/strings.mjs";

/** 시나리오 2 — 5회 모두 틀리면 정답을 공개하고 실패 결과를 보여준다. */

for (const lang of ["ko", "en"]) {
  test(`[2] 실패: 5회 오답 → 정답 공개 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `02-fail-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);
    art.note(`오늘=${puzzle.date} 언어=${lang} 정답=${puzzle.answer}`);
    // 길이가 정답과 다르면 서버가 VALIDATION_ERROR 로 막아서 기회가 줄지 않는다 —
    // "오답 5회" 가 아니라 "제출 실패 5회" 가 된다. 그래서 정답에서 만든다.
    const wrongs = wrongGuesses(puzzle.answer, lang, MAX_ATTEMPTS);
    expect(wrongs).not.toContain(puzzle.answer);
    expect(new Set(wrongs).size).toBe(MAX_ATTEMPTS);
    art.note(`오답 5개: ${wrongs.join(", ")}`);

    for (const [index, wrong] of wrongs.entries()) {
      await guess(page, wrong);
      const left = MAX_ATTEMPTS - (index + 1);
      await expectAttemptsLeft(page, left);
      if (left > 0) await expect(page.locator("#result")).toBeHidden();
    }
    await art.step(page, "오답5회");

    await expect(page.locator("#result")).toBeVisible();
    await expect(page.locator("#result-text")).toHaveText(
      format(t.result_fail, { answer: puzzle.answer }),
    );
    // 끝난 퍼즐에는 제출 폼이 없다 — 6번째 시도가 불가능하다.
    await expect(page.locator("#guess-form")).toBeHidden();
    await expect(page.locator("#board .tile-row")).toHaveCount(MAX_ATTEMPTS);
    await art.step(page, "실패결과-정답공개");

    expectAxeClean(await axeScan(page, art.dir, "fail-result"));

    await context.close();
  });
}
