import { expect, test } from "@playwright/test";
import {
  axeScan,
  expectAxeClean,
  guess,
  openGame,
  scene,
  showSection,
  todaysPuzzle,
  waitForPuzzle,
} from "../lib/game.mjs";
import { format, uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 5 — 백업 코드로 다른 브라우저에 같은 기록을 가져온다.
 *
 * 브리프가 실제 OAuth 왕복을 금지하므로(실기기 체크리스트로 넘긴다) "기기 이동" 은
 * 이 경로로 본다. 두 번째 컨텍스트는 저장소가 완전히 빈 **다른 브라우저**다 —
 * 쿠키·localStorage 가 하나도 넘어가지 않는다.
 */
for (const lang of ["ko", "en"]) {
  test(`[5] 백업 코드 → 다른 브라우저에서 복원 → 같은 기록 (${lang})`, async ({
    browser,
  }, testInfo) => {
    const art = scene(testInfo, `04-backup-restore-${lang}`);

    // --- 브라우저 A: 풀고 백업 코드를 복사한다 --------------------------------
    const a = await openGame(browser, { lang });
    const t = await uiStrings(a.page);
    const puzzle = await todaysPuzzle(a.page, lang);
    await guess(a.page, puzzle.answer);
    await expect(a.page.locator("#result")).toBeVisible();
    const streakBefore = await a.page.locator("#streak").textContent();
    expect(streakBefore).toBe(format(t.streak_summary, { current: 1, max: 1, solved: 1 }));

    await showSection(a.page, "records");
    await a.page.getByRole("button", { name: t.backup_open }).click();
    await expect(a.page.locator("#backup-panel")).toBeVisible();
    // D-42-1 (티켓 46 에서 수정): 라벨이 `<built-in method copy of dict object at 0x…>`
    // 로 나오던 자리다 — Jinja 의 속성 접근이 사전 키 "copy" 보다 `dict.copy` 메서드를
    // 먼저 집었다. 이제 역할 + 보이는 이름으로 누른다(이 레포의 셀렉터 규칙).
    await a.page.getByRole("button", { name: t.copy, exact: true }).click();
    await expect(a.page.locator("#copy-token-done")).toBeVisible();
    const backupCode = await a.page.evaluate(() => navigator.clipboard.readText());
    // 백업 코드 자체는 비밀이다 — 스크린샷에는 남지만(gitignore 된 폴더) 로그에는 길이만.
    art.note(`백업 코드 길이=${backupCode.length} (값은 로그에 남기지 않는다)`);
    expect(backupCode).toMatch(/^[0-9a-f-]{36}$/);
    await art.step(a.page, "A-백업코드-복사");
    // D-42-2 (티켓 46 에서 수정): 백업 코드 칸에 라벨이 없어 axe `label`(critical)이
    // 걸리던 자리다. 읽기 전용이라 placeholder 를 못 써서 `aria-label` 로 붙였다.
    await expect(a.page.locator("#token-display")).toHaveAttribute(
      "aria-label",
      t.backup_code_label,
    );
    expectAxeClean(await axeScan(a.page, art.dir, "records"));
    await a.context.close();

    // --- 브라우저 B: 빈 브라우저에 코드를 붙여넣는다 ---------------------------
    const b = await openGame(browser, { lang });
    // 복원 전에는 남의 기록이 아니라 자기 새 기록이다.
    await expect(b.page.locator("#board .tile-row")).toHaveCount(0);
    await showSection(b.page, "records");
    await b.page.getByRole("button", { name: t.restore_open }).click();
    await b.page.getByPlaceholder(t.backup_code_placeholder).fill(backupCode);
    await art.step(b.page, "B-코드-붙여넣기");
    await b.page.getByRole("button", { name: t.restore_submit, exact: true }).click();

    // 복원은 페이지를 통째로 다시 그린다 — 다른 게스트의 화면이 한 프레임도 남지 않게.
    await waitForPuzzle(b.page);
    await expect(b.page.locator("#result")).toBeVisible();
    await expect(b.page.locator("#result-text")).toHaveText(
      format(t.result_success, { answer: puzzle.answer }),
    );
    await expect(b.page.locator("#board .tile-row")).toHaveCount(1);
    await expect(b.page.locator("#streak")).toHaveText(streakBefore);
    await art.step(b.page, "B-복원-같은기록");

    // 순위표에서도 같은 사람이다 — 내 행이 하나고, A 가 올린 그 기록이다.
    await showSection(b.page, "leaderboard");
    await expect(b.page.locator("#leaderboard-entries li.is-me")).toHaveCount(1);
    await art.step(b.page, "B-순위-내행");

    await b.context.close();
  });
}
