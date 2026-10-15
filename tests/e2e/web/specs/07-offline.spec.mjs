import { expect, test } from "@playwright/test";
import {
  axeScan,
  expectAttemptsLeft,
  expectAxeClean,
  openGame,
  scene,
  todaysPuzzle,
  waitForPuzzle,
} from "../lib/game.mjs";
import { uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 8 — 오프라인·서버 오류 화면과 복구.
 *
 * 둘을 나눠 본다: **연결이 끊긴 것**(상단 배너 + 입력 잠금, 돌아오면 자동 복구)과
 * **서버가 오류를 준 것**(인라인 카드 + 재시도 버튼). 토스트로 숨기지 않고 화면에
 * 남는 게 설계다(OVERRIDES §7).
 *
 * ko·en 둘 다 돈다: 배너·오류 카드·재시도 버튼의 문구는 서버 사전에서 오고
 * (`uiStrings`), en 사전에 `offline_banner`·`puzzle_load_failed`·`retry` 가 빠져
 * 있으면 ko 만 돌 때는 아무도 모른다.
 */
for (const lang of ["ko", "en"]) {
  test(`[8] 오프라인 배너 → 연결 복구 자동 재조회 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `07-offline-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);

    await expect(page.locator("#offline-banner")).toBeHidden();

    // --- 랜선을 뽑는다 ---------------------------------------------------------
    // `setOffline` 은 브라우저의 `navigator.onLine` 과 `offline` 이벤트를 **실제로**
    // 바꾼다 — 테스트가 이벤트를 쏘아 흉내내지 않는다(확인: 이벤트 디스패치 없이 통과).
    await context.setOffline(true);
    await expect(page.locator("#offline-banner")).toBeVisible();
    await expect(page.locator("#offline-banner")).toHaveText(t.offline_banner);
    // 배너는 역할이 status 라 스크린리더가 읽는다(그냥 색만 바뀌는 게 아니다).
    await expect(page.locator("#offline-banner")).toHaveAttribute("role", "status");
    await art.step(page, "오프라인-배너");
    expectAxeClean(await axeScan(page, art.dir, `offline-${lang}`));

    // 끊긴 동안은 입력 자체가 잠긴다 — 보낼 수 없는 제출로 기회를 잃지 않게
    // (`renderOffline`). 배너만 띄우고 입력을 열어두면 사람은 제출을 눌러 본다.
    await expect(page.getByPlaceholder(t.guess_placeholder)).toBeDisabled();
    await expect(page.getByRole("button", { name: t.submit })).toBeDisabled();
    await expect(page.locator("#board .tile-row")).toHaveCount(0);
    await expectAttemptsLeft(page, 5);
    await art.step(page, "오프라인-입력잠김");

    // --- 연결이 돌아온다: 재시도 버튼을 누르지 않아도 복구된다 -----------------
    await context.setOffline(false);
    await expect(page.locator("#offline-banner")).toBeHidden();
    await waitForPuzzle(page);
    await expect(page.locator("#date")).toHaveText(puzzle.date);
    await art.step(page, "복구-퍼즐다시보임");

    await context.close();
  });

  test(`[8] 서버 오류 → 인라인 카드 → 재시도로 복구 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `07-server-error-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);

    // 오늘 퍼즐 조회만 500 으로 막는다 — "연결은 되는데 서버가 아프다" 상태다.
    let failing = true;
    await page.route("**/api/v1/puzzles/today", async (route) => {
      if (failing) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ code: "INTERNAL_ERROR", message: "서버 오류" }),
        });
        return;
      }
      await route.fallback();
    });

    await page.reload();
    await expect(page.locator("#puzzle-state")).toBeVisible();
    await expect(page.locator("#puzzle-state-text")).toHaveText(t.puzzle_load_failed);
    // 오프라인 배너가 아니다 — 연결은 살아 있다.
    await expect(page.locator("#offline-banner")).toBeHidden();
    await expect(page.locator("#puzzle")).toBeHidden();
    await art.step(page, "서버오류-인라인카드");
    expectAxeClean(await axeScan(page, art.dir, `server-error-${lang}`));

    // --- 서버가 회복된 뒤 재시도 버튼 ------------------------------------------
    failing = false;
    await page.getByRole("button", { name: t.retry }).click();
    await waitForPuzzle(page);
    await expect(page.locator("#puzzle-state")).toBeHidden();
    await expect(page.locator("#date")).toHaveText(puzzle.date);
    await art.step(page, "재시도-복구");

    await context.close();
  });
}
