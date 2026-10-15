import { expect, test } from "@playwright/test";
import { axeScan, expectAxeClean, guess, openGame, scene, todaysPuzzle } from "../lib/game.mjs";
import { BASE_URL_NOSTORE } from "../lib/env.mjs";
import { uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 9 — 앱 설치 배너·CTA 노출 규칙과 법적 문서 링크.
 *
 * 노출 규칙은 "설정값이 있으면 그리고, 없으면 **아예** 안 그린다" 다(없는 앱을
 * 권하지 않는다). 한 프로세스로는 둘 중 하나만 볼 수 있어서, 스택이 같은 앱을
 * 설정만 다르게 두 포트에 띄운다(`scripts/e2e_stack.sh`).
 */
const LEGAL_HEADINGS = {
  ko: { privacy: "개인정보처리방침", terms: "이용약관" },
  en: { privacy: "Privacy Policy", terms: "Terms of Service" },
};

for (const lang of ["ko", "en"]) {
  test(`[9] 스토어 링크가 설정된 앱: 배너·CTA 가 보인다 (${lang})`, async ({
    browser,
  }, testInfo) => {
    const art = scene(testInfo, `08-cta-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);

    // iOS Safari Smart App Banner 는 메타 태그다 — 앱 ID 가 있을 때만 나간다.
    await expect(page.locator('meta[name="apple-itunes-app"]')).toHaveAttribute(
      "content",
      /^app-id=\d+$/,
    );

    // CTA 는 **결과 안에** 있다 — 아직 풀지 않은 사람에게 앱을 권하지 않는다.
    await expect(page.locator(".app-cta")).toBeHidden();
    await guess(page, puzzle.answer);
    await expect(page.locator("#result")).toBeVisible();
    await expect(page.locator(".app-cta")).toBeVisible();
    await expect(page.locator(".app-cta-text")).toHaveText(t.app_cta);

    const ios = page.getByRole("link", { name: t.store_ios });
    const android = page.getByRole("link", { name: t.store_android });
    await expect(ios).toHaveAttribute("href", /^https:\/\/apps\.apple\.com\//);
    await expect(android).toHaveAttribute("href", /^https:\/\/play\.google\.com\//);
    await art.step(page, "CTA-배지2개");

    expectAxeClean(await axeScan(page, art.dir, "cta"));
    await context.close();
  });

  test(`[9] 스토어 링크가 비어 있는 앱: 배너·CTA 를 아예 안 그린다 (${lang})`, async ({
    browser,
  }, testInfo) => {
    const art = scene(testInfo, `08-cta-nostore-${lang}`);
    const { context, page } = await openGame(browser, { lang, baseURL: BASE_URL_NOSTORE });
    const puzzle = await todaysPuzzle(page, lang);

    // `app-id=` 가 빈 배너는 Safari 가 "앱 없음" 으로 그려 버린다 — 태그 자체가 없다.
    await expect(page.locator('meta[name="apple-itunes-app"]')).toHaveCount(0);

    await guess(page, puzzle.answer);
    await expect(page.locator("#result")).toBeVisible();
    // 안내 문구까지 통째로 없다 — 배지만 빠지고 "앱에서 받아보세요" 가 남으면 안 된다.
    await expect(page.locator(".app-cta")).toHaveCount(0);
    await expect(page.locator(".store-badge")).toHaveCount(0);
    await art.step(page, "CTA없음");
    await context.close();
  });

  test(`[9] 법적 문서 링크가 열린다 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `08-legal-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const headings = LEGAL_HEADINGS[lang];

    for (const [name, linkText, heading] of [
      ["privacy", t.footer_privacy, headings.privacy],
      ["terms", t.footer_terms, headings.terms],
    ]) {
      await page.goto("/");
      const link = page.getByRole("link", { name: linkText });
      // 푸터 링크는 UI 언어를 그대로 들고 간다(`?lang=`) — en 방문자가 ko 문서를
      // 받으면 스토어 심사에서 "문서 없음" 으로 읽힌다.
      await expect(link).toHaveAttribute("href", new RegExp(`/${name}\\?lang=${lang}$`));
      await link.click();
      await expect(page).toHaveURL(new RegExp(`/${name}\\?lang=${lang}$`));
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
      // 사업자 정보 블록은 설정값이 비어 있으면 서비스명·연락처만 그린다(티켓 16).
      await expect(page.locator("body")).toContainText("@");
      await art.step(page, `문서-${name}`);
      expectAxeClean(await axeScan(page, art.dir, name));
    }

    await context.close();
  });
}
