import { expect, test } from "@playwright/test";
import {
  axeScan,
  expectAxeClean,
  guess,
  openGame,
  scene,
  showSection,
  MAX_ATTEMPTS,
  todaysPuzzle,
  wrongGuesses,
} from "../lib/game.mjs";
import { LITERALS } from "../lib/i18n-literals.mjs";

/**
 * 시나리오 3 — 순위표: 익명 표기, 내 행 강조, en 복수형.
 *
 * 다른 사람을 **DB 에 심지 않고** 브라우저 컨텍스트를 더 열어 실제로 풀게 한다 —
 * 순위는 Redis ZSET 에만 있고(README "07."), 심는 쪽을 만들면 테스트가 검증하려는
 * 바로 그 경로(제출 → 점수 기록)를 건너뛴다.
 */

/** 새 사람 한 명이 들어와 `tries` 번째에 맞춘다. */
async function playerSolves(browser, lang, tries) {
  const { context, page } = await openGame(browser, { lang });
  const puzzle = await todaysPuzzle(page, lang);
  const wrongs = wrongGuesses(puzzle.answer, lang, tries);
  for (let i = 0; i < tries - 1; i += 1) await guess(page, wrongs[i]);
  await guess(page, puzzle.answer);
  await expect(page.locator("#result")).toBeVisible();
  await context.close();
}

for (const lang of ["ko", "en"]) {
  test(`[3] 순위표: 익명 표기·내 행 강조·복수형 (${lang})`, async ({ browser }, testInfo) => {
    const art = scene(testInfo, `03-leaderboard-${lang}`);
    const literals = LITERALS[lang];

    // 1회·3회로 맞춘 사람을 먼저 들여보낸다 — en 복수형("1 try" vs "3 tries")을
    // 보려면 1 과 2 이상이 같은 표에 있어야 한다.
    await playerSolves(browser, lang, 1);
    await playerSolves(browser, lang, 3);

    // 내가 2회에 맞춘다.
    const { context, page } = await openGame(browser, { lang });
    const puzzle = await todaysPuzzle(page, lang);
    await guess(page, wrongGuesses(puzzle.answer, lang, 1)[0]);
    await guess(page, puzzle.answer);
    await showSection(page, "leaderboard");
    await expect(page.locator("#leaderboard-entries li")).not.toHaveCount(0);
    await art.step(page, "순위표");

    const rows = await page.locator("#leaderboard-entries li").evaluateAll((items) =>
      items.map((li) => ({
        rank: li.querySelector(".rank").textContent,
        text: li.querySelector(".entry-text").textContent,
        isMe: li.classList.contains("is-me"),
      })),
    );
    art.note(`순위표 ${rows.length}행: ${rows.map((r) => r.text).join(" | ")}`);

    // --- 익명 표기: 서버는 태그만 주고 접두사는 UI 언어가 붙인다(README "38.") ---
    for (const row of rows) {
      expect(row.text.startsWith(literals.guestPrefix), row.text).toBe(true);
      // 이메일·게스트 ID 가 새면 안 된다 — 태그는 16진수 4자리다.
      expect(row.text).toMatch(
        new RegExp(`^${literals.guestPrefix.replace("#", "#")}[0-9a-f]{4} · `),
      );
      expect(row.text).not.toContain("@");
    }

    // --- 복수형: 1회는 단수 키, 3회는 복수 키 ---------------------------------
    const texts = rows.map((row) => row.text);
    expect(texts.some((text) => text.includes(literals.attemptsOne))).toBe(true);
    expect(texts.some((text) => text.includes(literals.attemptsThree))).toBe(true);

    // --- 정렬: 적은 시도 우선, 같으면 빨리 푼 순 --------------------------------
    const keys = rows.map((row) => {
      const [, attempts, time] = row.text.split(" · ");
      return [Number(attempts.match(/\d+/)[0]), time];
    });
    for (let i = 1; i < keys.length; i += 1) {
      expect(
        keys[i - 1][0] < keys[i][0] ||
          (keys[i - 1][0] === keys[i][0] && keys[i - 1][1] <= keys[i][1]),
        `정렬이 깨졌다: ${JSON.stringify(keys)}`,
      ).toBe(true);
    }

    // --- 내 행 강조: 딱 한 행이고, 내 순위 줄과 같은 순위다 ---------------------
    const mine = rows.filter((row) => row.isMe);
    expect(mine).toHaveLength(1);
    await expect(page.locator("#my-rank")).toContainText(mine[0].rank);
    // 클래스만 붙고 보이는 게 같으면 "강조" 가 아니다 — 실제로 굵게 그려지는지 본다
    // (`style.css` 의 `.leaderboard-entry.is-me { font-weight: 700 }`; 색만으로
    // 구분하지 않는 쪽이라 색약 사용자에게도 보인다).
    const weight = await page.locator("#leaderboard-entries li").evaluateAll((items) => {
      const me = items.find((li) => li.classList.contains("is-me"));
      const other = items.find((li) => !li.classList.contains("is-me"));
      return {
        me: getComputedStyle(me).fontWeight,
        other: other ? getComputedStyle(other).fontWeight : null,
      };
    });
    art.note(`내 행 굵기=${weight.me} 남의 행 굵기=${weight.other}`);
    expect(Number(weight.me)).toBeGreaterThan(Number(weight.other));

    // --- 통계: 분포가 5줄(1~5회) ---------------------------------------------
    await expect(page.locator("#today-stats li")).toHaveCount(MAX_ATTEMPTS);
    await expect(page.locator("#today-stats")).toContainText(literals.attemptsOne);
    await art.step(page, "통계분포");

    expectAxeClean(await axeScan(page, art.dir, "leaderboard"));

    await context.close();
  });
}
