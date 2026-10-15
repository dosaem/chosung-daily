import { defineConfig } from "@playwright/test";
import { ARTIFACT_ROOT, BASE_URL } from "./lib/env.mjs";

// 데스크톱 1280 과 모바일 390 을 **같은 시나리오로** 두 번 돈다(브리프). 모바일은
// 폭만 바꾸는 게 아니라 터치·DPR 까지 iPhone 13 프로필을 쓴다 — 반응형 분기는
// 기기 종류가 아니라 현재 폭이 기준이지만(README "24."), 사람이 폰으로 누르는
// 상황을 재현하려면 입력 방식도 같아야 한다.
const VIEWPORTS = [
  { name: "desktop-1280", use: { viewport: { width: 1280, height: 900 } } },
  {
    name: "mobile-390",
    // `devices["iPhone 13"]` 을 그대로 쓰지 않는다 — 그 프리셋은 WebKit 을 기본
    // 브라우저로 끌고 와서 브라우저 한 벌을 더 받아야 한다. 이 티켓이 보는 건
    // **폭**이고(README "24. 태블릿 대응 — 기기 종류가 아니라 현재 폭"), 사람이
    // 폰으로 누르는 상황은 터치·DPR 로 충분히 재현된다. 실기기 Safari 왕복은
    // RELEASE 실기기 체크리스트의 몫이다.
    use: {
      viewport: { width: 390, height: 844 },
      deviceScaleFactor: 3,
      isMobile: true,
      hasTouch: true,
    },
  },
];

export default defineConfig({
  testDir: "./specs",
  // **전부 직렬이다.** 시나리오가 한 DB·한 Redis·한 서버를 공유하고, 연속 기록
  // 시나리오는 저장된 날짜를 통째로 하루 되돌린다(`scripts/e2e/advance_day.py`).
  // 병렬로 돌리면 남의 시나리오가 다른 날짜를 보게 된다.
  fullyParallel: false,
  workers: 1,
  // 재시도 없음: 실제 스택을 쓰는 E2E 에서 재시도는 결함을 가린다. 깨지면 깨진
  // 채로 증거에 남긴다(브리프: 테스트를 결함에 맞춰 느슨하게 바꾸지 않는다).
  retries: 0,
  // 한 판 10분 안에 끝나야 한다 — 서버가 벽시계를 쓰므로 KST 자정을 넘기면 안 된다.
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: `${ARTIFACT_ROOT}/report`, open: "never" }],
    ["json", { outputFile: `${ARTIFACT_ROOT}/report/results.json` }],
  ],
  outputDir: `${ARTIFACT_ROOT}/test-output`,
  use: {
    baseURL: BASE_URL,
    // 공유 텍스트 복사가 `navigator.clipboard` 를 쓴다 — 권한이 없으면 사람이
    // 쓰는 경로가 아니라 폴백(직접 복사해주세요)만 보게 된다.
    permissions: ["clipboard-read", "clipboard-write"],
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
    // 서버가 `?lang=` 없이 받으면 Accept-Language 로 UI 언어를 고른다. 기본은
    // ko 로 두고, en 시나리오가 컨텍스트마다 덮어쓴다.
    locale: "ko-KR",
    timezoneId: "Asia/Seoul",
  },
  projects: VIEWPORTS,
});
