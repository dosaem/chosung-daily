import { expect, test } from "@playwright/test";
import { guess, openGame, scene, showSection, todaysPuzzle, waitForPuzzle } from "../lib/game.mjs";
import { stack } from "../lib/env.mjs";
import { format, uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 4 — 하루를 넘겨 재방문하면 연속 기록이 2 가 된다.
 *
 * **이 파일이 마지막에 돌아야 한다.** `advance-day` 가 저장된 날짜를 통째로 하루
 * 되돌리므로(= 하루가 지난 상태), 뒤에 오는 시나리오는 다른 날짜를 보게 된다.
 * 그래서 파일 이름이 10 이다(브리프의 시나리오 번호는 4).
 *
 * 왜 서버 시계를 주입하지 않는가: 코디네이터 결정 2026-10-15 — `datetime.now(KST)`
 * 가 서비스 8곳에 흩어져 있어 주입형 시계를 넣으면 프로덕션 코드에 테스트 전용
 * 경로가 생긴다. 대신 날짜를 데이터로 되돌린다(`scripts/e2e/advance_day.py`).
 *
 * 웹에는 7일 그리드가 없다 — `web/templates/index.html` 주석대로 앱 화면(S4)의
 * 몫이다(티켓 27). 그래서 그리드 대신 그 원천 데이터인 `GET /me/history` 를 본다.
 *
 * ko·en 둘 다 돈다: 연속 기록 판정(`guess_service._record_solve`)이 언어와
 * 무관해야 한다는 게 스펙(US 14)이고, `/me/history` 의 결과도 언어별 칸이다.
 * **언어마다 한 번씩 하루를 넘긴다** — 날짜 시프트는 언어를 가리지 않으므로
 * 시드가 못박는 날은 (언어 수 × 뷰포트 수 + 1)개여야 한다(`scripts/e2e/seed.py`
 * 의 `PINNED`, 계약은 `tests/test_e2e_scripts.py`).
 */
for (const lang of ["ko", "en"]) {
  test(`[4] 연속 기록: 하루 넘겨 재방문 → streak 2 + 최근 기록 (${lang})`, async ({
    browser,
  }, testInfo) => {
    const art = scene(testInfo, `10-streak-${lang}`);
    const { context, page } = await openGame(browser, { lang });
    const t = await uiStrings(page);

    // --- 1일차: 오늘 퍼즐을 푼다 ---------------------------------------------
    const day1 = await todaysPuzzle(page, lang);
    await guess(page, day1.answer);
    await expect(page.locator("#result")).toBeVisible();
    await expect(page.locator("#streak")).toHaveText(
      format(t.streak_summary, { current: 1, max: 1, solved: 1 }),
    );
    await art.step(page, "1일차-정답-streak1");
    const token = await page.evaluate(() => localStorage.getItem("chosung_token"));

    // --- 하루가 지났다 --------------------------------------------------------
    const output = stack("advance-day");
    art.note(`advance-day: ${output.trim()}`);

    // --- 2일차: 다시 들어온다 -------------------------------------------------
    await page.reload();
    await waitForPuzzle(page);
    const day2 = await todaysPuzzle(page, lang);
    // 어제 푼 문제가 아니라 **다음 문제**다. 달력 날짜는 그대로다 — 서버가 벽시계로
    // "오늘" 을 계산하고 우리는 저장된 날짜를 내렸으니, 바뀌는 건 그 날짜에 배정된
    // 단어다(`scripts/e2e/advance_day.py` 의 설명). 연속 기록 판정은 날짜의 **차이**
    // 만 보므로 이 방식으로도 진짜 경로가 돈다.
    expect(day2.date).toBe(day1.date);
    expect(day2.answer).not.toBe(day1.answer);
    // 어제 보드는 어제에 남는다 — 오늘은 빈 보드에서 다시 시작한다.
    await expect(page.locator("#board .tile-row")).toHaveCount(0);
    await expect(page.locator("#result")).toBeHidden();
    // 아직 오늘 걸 안 풀었으니 streak 은 1 그대로다(어제까지 이어진 기록).
    await expect(page.locator("#streak")).toHaveText(
      format(t.streak_summary, { current: 1, max: 1, solved: 1 }),
    );
    await art.step(page, "2일차-새퍼즐");

    await guess(page, day2.answer);
    await expect(page.locator("#result")).toBeVisible();
    await expect(page.locator("#streak")).toHaveText(
      format(t.streak_summary, { current: 2, max: 2, solved: 2 }),
    );
    await art.step(page, "2일차-정답-streak2");

    // --- 7일 그리드의 원천 데이터 --------------------------------------------
    const history = await page.request.get("/api/v1/me/history?days=7", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(history.status()).toBe(200);
    const days = await history.json();
    art.note(`GET /me/history?days=7 → ${JSON.stringify(days)}`);
    expect(days).toHaveLength(7);
    // 오래된 날짜부터 오늘이 마지막이다(README "07. 최근 7일 기록"). 어제 칸이
    // 1일차의 정답, 오늘 칸이 2일차의 정답이다 — 연속 2일이 서버 기록으로 남았다.
    // 칸은 언어별이다: 푼 언어에만 success 가 찍혀야 한다.
    expect(days.at(-1).date).toBe(day2.date);
    expect(days.at(-1).results[lang]).toBe("success");
    expect(days.at(-2).results[lang]).toBe("success");
    // 안 푼 날은 빈칸이 아니라 `none` 으로 서버가 채운다.
    expect(days.at(-3).results[lang]).toBe("none");

    await showSection(page, "records");
    await art.step(page, "내기록-섹션");
    art.note(
      "웹 '내 기록' 섹션에는 7일 그리드가 없다(앱 S4 의 몫, 티켓 27) — " +
        "연속 기록은 머리말 배지가, 최근 7일은 위 /me/history 응답이 증거다.",
    );

    await context.close();
  });
}
