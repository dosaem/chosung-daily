import { expect, test } from "@playwright/test";
import { axeScan, expectAxeClean, guess, openGame, scene, todaysPuzzle, waitForPuzzle } from "../lib/game.mjs";
import { uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 7 — 계정 삭제 뒤 새 게스트로 시작한다.
 *
 * 삭제 페이지(`/account/delete`)는 Play Data safety 가 가리키는 URL 이고, 세션
 * 쿠키가 있는 브라우저에만 확인 폼을 그린다. 여기서 보는 것:
 *  - GET 만으로는 아무것도 지워지지 않는다(심사자·링크 프리뷰가 먼저 열어본다)
 *  - 삭제 뒤 돌아온 홈이 **새 게스트**로 시작한다(옛 토큰을 들고 401 을 맞지 않는다)
 */
const DELETE_BUTTON = { ko: "계정과 모든 기록 삭제", en: "Delete my account and all records" };
const DELETE_HEADING = { ko: "계정 삭제", en: "Delete account" };

for (const lang of ["ko", "en"]) {
  test(`[7] 계정 삭제 → 새 게스트로 시작 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `06-account-delete-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);

    // 지울 기록을 만든다.
    await guess(page, puzzle.answer);
    await expect(page.locator("#result")).toBeVisible();
    const tokenBefore = await page.evaluate(() => localStorage.getItem("chosung_token"));
    await art.step(page, "삭제전-기록있음");

    // --- 푸터의 "계정 삭제" 로 들어간다 ---------------------------------------
    await page.getByRole("link", { name: t.footer_delete }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(DELETE_HEADING[lang]);
    await art.step(page, "삭제확인페이지");
    expectAxeClean(await axeScan(page, art.dir, "delete-page"));

    // GET 으로 열어본 것만으로는 기록이 살아 있어야 한다 — 같은 토큰이 아직 통한다.
    const aliveProbe = await page.request.get("/api/v1/me/stats", {
      headers: { Authorization: `Bearer ${tokenBefore}` },
    });
    expect(aliveProbe.status()).toBe(200);
    art.note("GET /account/delete 만으로는 삭제되지 않는다 (me/stats 200)");

    // --- 확인 버튼을 누른다 ----------------------------------------------------
    await page.getByRole("button", { name: DELETE_BUTTON[lang] }).click();
    await waitForPuzzle(page);
    // 서버가 `/?deleted=1` 로 돌려보내고, 프론트가 토큰이 정말 지워졌는지 확인한 뒤
    // 버린다. 주소창에 신호가 남아 있으면 안 된다(확인에 성공했으므로).
    await expect(page).toHaveURL(/\/$/);
    // D-42-3 (티켓 46 에서 수정): 안내가 `restart()` 에 지워져 한 번도 안 보이던
    // 자리다. 되돌릴 수 없는 작업의 유일한 확인이라, 첫 화면이 다 그려진 **뒤에도**
    // 남아 있어야 한다.
    await expect(page.locator("#message")).toHaveText(t.account_deleted);
    await art.step(page, "삭제후-새게스트");

    // 새 게스트다: 보드가 비어 있고, 기록이 0 이고, 토큰이 갈렸다.
    await expect(page.locator("#board .tile-row")).toHaveCount(0);
    await expect(page.locator("#result")).toBeHidden();
    await expect(page.locator("#guess-form")).toBeVisible();
    const tokenAfter = await page.evaluate(() => localStorage.getItem("chosung_token"));
    expect(tokenAfter).not.toBe(tokenBefore);
    expect(tokenAfter).toMatch(/^[0-9a-f-]{36}$/);

    // 옛 토큰은 서버에서 정말 사라졌다.
    const goneProbe = await page.request.get("/api/v1/me/stats", {
      headers: { Authorization: `Bearer ${tokenBefore}` },
    });
    expect(goneProbe.status()).toBe(401);

    await context.close();
  });
}
