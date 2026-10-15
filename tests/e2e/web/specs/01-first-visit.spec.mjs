import { expect, test } from "@playwright/test";
import {
  axeScan,
  expectAxeClean,
  expectAttemptsLeft,
  guess,
  nearMiss,
  openGame,
  scene,
  showSection,
  todaysPuzzle,
} from "../lib/game.mjs";
import { format, uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 1 — 첫 방문 게스트가 오답 한 번 뒤에 맞추고 결과를 공유한다.
 *
 * 저장소가 빈 새 컨텍스트로 열어서(= 토큰 없음) 게스트 발급 → 오늘 퍼즐 조회까지
 * 실제로 돈다. 정답은 시드 manifest 가 못박은 값이고, 테스트가 DB 를 보지 않는다.
 */

for (const lang of ["ko", "en"]) {
  test(`[1] 첫 방문 게스트: 오답 1회 → 정답 → 결과 → 공유 (${lang})`, async ({
    browser,
  }, testInfo) => {
    const art = scene(testInfo, `01-first-visit-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);
    const puzzle = await todaysPuzzle(page, lang);
    art.note(`오늘=${puzzle.date} 언어=${lang} 정답=${puzzle.answer}`);

    // --- 홈 진입: 오늘 퍼즐의 가림이 보인다 -----------------------------------
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(t.app_title);
    await expect(page.locator("#mask-row .tile")).toHaveCount(puzzle.length);
    await expect(page.locator("#length-caption")).toHaveText(
      format(t.length_caption, { length: puzzle.length }),
    );
    await expectAttemptsLeft(page, 5);
    // 정답이 화면에 평문으로 없어야 한다 — 빈 타일에 글자를 담으면 새어 나간다.
    // `body.textContent` 가 아니라 **보이는 텍스트**를 본다: 페이지에는 UI 문구 사전이
    // 인라인 JSON(`#ui-strings`)으로 심겨 있고 그 안의 키 이름(`login_apple`)이 en
    // 정답과 겹친다 — 플레이어에게 보이는 글자가 아니라 검사의 거짓 양성이다.
    expect(await page.locator("main.card").innerText()).not.toContain(puzzle.answer);
    await art.step(page, "홈-오늘퍼즐");
    expectAxeClean(await axeScan(page, art.dir, "home"));

    // --- 오답 1회: 남은 기회가 줄고 피드백 타일이 섞여 나온다 -----------------
    await guess(page, nearMiss(puzzle.answer, lang));
    await expectAttemptsLeft(page, 4);
    const feedback = await page
      .locator("#board .tile-row")
      .last()
      .locator(".tile")
      .evaluateAll((tiles) => tiles.map((tile) => tile.className));
    expect(feedback.some((cls) => cls.includes("tile-correct"))).toBe(true);
    expect(feedback.some((cls) => cls.includes("tile-wrong"))).toBe(true);
    await expect(page.locator("#result")).toBeHidden();
    await art.step(page, "오답1회-피드백타일");

    // --- 정답: 결과가 뜨고 제출 폼이 사라진다 ---------------------------------
    await guess(page, puzzle.answer);
    await expect(page.locator("#result")).toBeVisible();
    await expect(page.locator("#result-text")).toHaveText(
      format(t.result_success, { answer: puzzle.answer }),
    );
    await expect(page.locator("#guess-form")).toBeHidden();
    await art.step(page, "정답-결과");

    // --- 결과의 시도 수·시간·통계는 "순위" 섹션에 있다 ------------------------
    // 웹은 결과 시트가 따로 없다(앱 S2 의 몫) — 내 순위 줄이 `#순위 · 시도 · 시간`,
    // 그 아래 오늘의 시도 분포가 통계다.
    await showSection(page, "leaderboard");
    // 시간은 "그날 KST 자정부터 걸린 초" 를 HH:MM:SS 로 찍은 값이다
    // (`puzzle_metrics.record_leaderboard` — 같은 시도 수면 빨리 푼 사람이 위다).
    await expect(page.locator("#my-rank")).toHaveText(/^#\d+ · .+ · \d{2}:\d{2}:\d{2}$/);
    await expect(page.locator("#my-rank")).toContainText(
      format(t.attempts_other, { count: 2 }),
    );
    await expect(page.locator("#today-stats li")).not.toHaveCount(0);
    await art.step(page, "순위-내기록과통계");
    expectAxeClean(await axeScan(page, art.dir, "leaderboard"));

    // --- 공유 텍스트 복사 ------------------------------------------------------
    await showSection(page, "today");
    await page.getByRole("button", { name: t.share_open }).click();
    await expect(page.locator("#share-copied")).toBeVisible();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    art.note(`공유 텍스트:\n${copied}`);
    expect(copied).toContain(format(t.share_heading, { date: puzzle.date }));
    expect(copied).toContain(format(t.share_success, { used: 2, max: 5 }));
    // 공유 텍스트에 정답이 들어가면 받는 사람의 퍼즐이 샌다.
    expect(copied).not.toContain(puzzle.answer);
    await art.step(page, "공유-복사완료");

    await context.close();
  });
}
