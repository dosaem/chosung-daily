import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
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
import { manifest } from "../lib/env.mjs";
import { uiStrings } from "../lib/strings.mjs";

/**
 * 시나리오 10 — 운영자 흐름: 로그인 → CSV 업로드 → 배정 확인·교체.
 *
 * 운영자 로그인에는 별도 화면이 없다(README "설계 판단 15."): 구글 OAuth 세션의
 * 연결된 이메일이 `ADMIN_EMAILS` 에 있으면 운영자다. 브리프가 실제 OAuth 왕복을
 * 금지하므로, 시드가 **계정이 이미 연결된** 게스트를 하나 만들어 두고, 브라우저는
 * "내 기록 > 다른 기기 기록 불러오기" 에 그 백업 코드를 넣어 운영자 브라우저가
 * 된다 — 세션 쿠키는 프론트가 페이지 로드마다 부르는 `POST /session/sync` 가 심는다.
 *
 * 업로드하는 CSV 는 일부러 네 갈래를 섞는다: 새 단어 2개 · 이미 있는 단어 1개 ·
 * 카테고리가 틀린 줄 1개. 행별 결과 표가 진짜로 갈라 보여주는지를 봐야 한다.
 */
// 올리는 새 단어는 **뷰포트마다 다르다.** 두 프로젝트(desktop/mobile)가 같은 DB 를
// 공유하므로, 같은 단어를 올리면 뒤에 도는 프로젝트에서 "추가 0개 · 중복 2개" 가
// 되어 행별 결과 표가 검증하려던 네 갈래가 사라진다.
const NEW_WORDS_BY_PROJECT = {
  "desktop-1280": [
    ["ko", "general", "노트북", "무릎에 올려놓고 쓰는 컴퓨터"],
    ["ko", "general", "손수건", "주머니에 넣고 다니는 작은 천"],
  ],
  "mobile-390": [
    ["ko", "general", "빗자루", "바닥을 쓰는 도구"],
    ["ko", "general", "주전자", "물을 끓여 따르는 그릇"],
  ],
};
// 이미 시드에 있는 단어 — "중복" 줄이 나와야 한다.
const DUPLICATE_WORD = ["ko", "general", "사과", "빨갛고 아삭한 과일"];
// 카테고리가 틀린 줄 — 그 줄만 "오류" 로 빠지고 나머지는 들어가야 한다.
const BROKEN_ROW = ["ko", "없는카테고리", "깨진줄", "카테고리가 틀렸다"];

test("[10] 운영자: 로그인 → CSV 업로드 → 배정표 확인 → 단어 교체", async ({
  browser,
}, testInfo) => {
  const art = scene(testInfo, "09-admin");
  const seed = manifest();
  const newWords = NEW_WORDS_BY_PROJECT[testInfo.project.name];
  if (!newWords) throw new Error(`프로젝트 ${testInfo.project.name} 의 업로드 단어가 없다`);
  const firstWord = newWords[0][2];
  const { context, page } = await openGame(browser, { lang: "ko" });
  const t = await uiStrings(page);

  // --- 운영자 브라우저가 된다 (백업 코드 복원) --------------------------------
  // 로그인 안 된 브라우저가 /admin 에 들어가면 403 이 아니라 홈 + 안내다.
  await page.goto("/admin/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator(".notice")).toContainText("구글 로그인");
  await art.step(page, "비로그인-admin-안내");

  await waitForPuzzle(page);
  await showSection(page, "records");
  await page.getByRole("button", { name: t.restore_open }).click();
  await page.getByPlaceholder(t.backup_code_placeholder).fill(seed.admin.backup_code);
  await page.getByRole("button", { name: t.restore_submit, exact: true }).click();
  await waitForPuzzle(page);
  // 연결된 계정이 있는 게스트다 — 로그인 버튼 대신 연결 표시가 나온다.
  await showSection(page, "records");
  await expect(page.locator("#linked-account")).toContainText(seed.admin.email);
  await art.step(page, "운영자계정-연결확인");

  // --- 운영자 페이지가 열린다 ------------------------------------------------
  await page.goto("/admin/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("단어 목록");
  await art.step(page, "운영자-단어목록");
  expectAxeClean(await axeScan(page, art.dir, "admin-words"));

  // --- CSV 업로드 -------------------------------------------------------------
  const csvPath = path.join(art.dir, "upload.csv");
  mkdirSync(art.dir, { recursive: true });
  writeFileSync(
    csvPath,
    ["language,category,answer,hint", ...[...newWords, DUPLICATE_WORD, BROKEN_ROW].map((row) => row.join(","))].join("\n") +
      "\n",
    "utf8",
  );

  await page.getByRole("link", { name: "CSV 업로드" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("CSV 업로드");
  await page.locator('input[type="file"]').setInputFiles(csvPath);
  await art.step(page, "CSV-파일선택");
  await page.getByRole("button", { name: "업로드" }).click();

  await expect(page.getByRole("heading", { level: 2 })).toHaveText("업로드 결과");
  // 요약 한 줄이 네 갈래를 정확히 센다. 이 수는 **빈 DB 에서 시작했을 때**의 값이다 —
  // `scripts/e2e_web.sh` 가 매번 down → up → seed 로 DB 를 새로 만들어 보장한다.
  // (같은 DB 에 두 번 돌리면 새 단어가 "중복" 으로 넘어가 추가 0개가 된다.)
  await expect(page.locator(".admin-meta").filter({ hasText: "추가" })).toContainText(
    "추가 2개 · 중복 1개 · 오류 1개",
  );
  // 행별 결과: 줄 번호가 CSV 파일의 줄 번호(헤더가 1행)여야 운영자가 그 줄을 찾는다.
  const rows = await page.locator(".admin-table tbody tr").evaluateAll((trs) =>
    trs.map((tr) => [...tr.querySelectorAll("td")].map((td) => td.textContent.trim())),
  );
  art.note(`업로드 행별 결과: ${JSON.stringify(rows, null, 1)}`);
  expect(rows[0][0]).toBe("2");
  expect(rows[0][1]).toBe(firstWord);
  expect(rows[0][2]).toBe("추가");
  expect(rows[2][1]).toBe("사과");
  expect(rows[2][2]).toBe("중복");
  expect(rows[3][2]).toBe("오류");
  expect(rows[3][3]).toContain("category");
  await art.step(page, "CSV-행별결과");
  expectAxeClean(await axeScan(page, art.dir, "admin-import"));

  // 올린 단어가 목록 검색으로 찾힌다.
  await page.getByRole("link", { name: "단어 목록" }).click();
  await page.locator('input[name="q"]').fill(firstWord);
  await page.getByRole("button", { name: "검색" }).click();
  await expect(page.locator(".admin-cell-answer").first()).toHaveText(firstWord);
  await art.step(page, "단어목록-검색");

  // --- 배정표: 오늘은 시드가 못박은 단어, 잔량이 올라간다 ---------------------
  // 먼저 플레이어 한 명이 오늘 문제에 한 번 제출한다 — "시도가 있는 날짜는 단어를
  // 바꿀 수 없다" 규칙을 보려면 시도가 있어야 한다. 이 시나리오가 혼자 돌아도
  // 같은 것을 검증하게 하려고, 앞 시나리오의 플레이에 기대지 않고 직접 만든다.
  const player = await openGame(browser, { lang: "ko" });
  await guess(player.page, "가나다");
  await player.context.close();

  await page.getByRole("link", { name: "배정표" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("30일 배정표");
  const todayPinned = seed.puzzles.find((p) => p.offset === 0 && p.language === "ko");
  const todayRow = page.locator("tbody tr").filter({ hasText: todayPinned.date });
  await expect(todayRow.locator(".admin-cell-answer")).toContainText(todayPinned.answer);
  // 오늘은 이미 누가 풀었다 — 시도가 있는 날짜는 단어를 못 바꾼다.
  await expect(todayRow.locator(".admin-cell-actions")).toContainText("교체 불가");
  await expect(page.locator(".admin-stock-card")).toHaveCount(2);
  await art.step(page, "배정표-오늘과잔량");
  expectAxeClean(await axeScan(page, art.dir, "admin-schedule"));

  // --- 교체: 방금 올린 단어를 먼 미래 날짜에 배정한다 ------------------------
  const lastRow = page.locator("tbody tr").last();
  const targetDate = (await lastRow.locator(".admin-cell-date").textContent()).trim().split(" ")[0];
  const replaceLink = lastRow.getByRole("link", { name: /교체|배정/ });
  const href = await replaceLink.getAttribute("href");

  // D-42-4 (결함, 390 폭에서만): 배정표가 뷰포트보다 넓어서 가로 스크롤이 생기고,
  // 마지막 열(관리)의 교체/배정 링크를 **누를 수 없다** — 옆으로 밀어 가운데에 둬도
  // 다른 행의 칸이 그 자리의 포인터 이벤트를 가로챈다. 운영자 화면은 폭이 디자인
  // 시스템 §10 을 의도적으로 벗어난다는 결정이 있지만(README "15."), 그 결과가 폰에서
  // "누를 수 없는 버튼" 이면 기록할 결함이다. 고치지 않고 두 가지로 남긴다:
  //   ① 넘침 자체를 단정으로 (아래 soft)
  //   ② 무엇이 가로채는지 단계 로그에 (art.note)
  // 그리고 나머지 흐름(교체가 실제로 되는가)은 주소로 들어가 계속 검증한다.
  const layout = await page.evaluate(() => ({
    doc: document.documentElement.scrollWidth,
    table: document.querySelector(".admin-table").scrollWidth,
  }));
  const viewportWidth = page.viewportSize().width;
  art.note(`배정표 폭: 문서 ${layout.doc}px · 표 ${layout.table}px · 뷰포트 ${viewportWidth}px`);
  expect.soft(
    layout.doc,
    `D-42-4: ${viewportWidth}px 뷰포트에서 배정표가 가로로 넘친다 (문서 ${layout.doc}px)`,
  ).toBeLessThanOrEqual(viewportWidth);

  // 사람처럼 옆으로 밀어 그 칸을 가운데에 둔 뒤, 누를 수 있는지만 본다(실제로 누르지 않는다).
  await replaceLink.evaluate((el) => el.scrollIntoView({ block: "center", inline: "center" }));
  const tappable = await replaceLink
    .click({ trial: true, timeout: 3000 })
    .then(() => true, () => false);
  if (!tappable) {
    const blocker = await replaceLink.evaluate((el) => {
      const box = el.getBoundingClientRect();
      const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
      return {
        link: `${Math.round(box.x)},${Math.round(box.y)} ${Math.round(box.width)}x${Math.round(box.height)}`,
        hit: hit ? `${hit.tagName}.${hit.className}`.trim() : null,
      };
    });
    art.note(`D-42-4 링크를 가로채는 요소: ${JSON.stringify(blocker)}`);
  }
  expect.soft(tappable, `D-42-4: ${viewportWidth}px 에서 교체/배정 링크를 탭할 수 없다`).toBe(
    true,
  );
  if (tappable) await replaceLink.click();
  else await page.goto(href);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(targetDate);
  await page.locator('input[name="q"]').fill(firstWord);
  await page.getByRole("button", { name: "검색" }).click();
  const candidate = page.locator("tbody tr").filter({ hasText: firstWord });
  await expect(candidate).toHaveCount(1);
  await art.step(page, "교체-단어검색");
  await candidate.getByRole("button", { name: "이 단어로" }).click();

  // 배정표로 돌아와서 그 날짜가 바뀐 것을 확인한다.
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("30일 배정표");
  await expect(
    page.locator("tbody tr").filter({ hasText: targetDate }).locator(".admin-cell-answer"),
  ).toContainText(firstWord);
  await art.step(page, "교체-배정확인");
  art.note(`${targetDate} ko 배정을 '${firstWord}' 으로 교체 확인`);

  await context.close();
});
