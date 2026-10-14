/** 헤드리스 크롬으로 메인 페이지를 라이트·다크 각 1장 찍는다 (티켓 18 완료 조건).
 *
 * 사람이 눈으로 확인한 스크린샷이 아니라 **기록**이다: 다크모드가 토큰만으로 따라오는지
 * (OVERRIDES §9, 수동 토글 없음)를 렌더된 그림으로 남겨 둔다. `prefers-color-scheme` 은
 * CDP `Emulation.setEmulatedMedia` 로 바꾼다 — 크롬 플래그(`--force-dark-mode`)는
 * 브라우저가 색을 **임의로 반전**시키는 기능이라 우리 다크 토큰을 보는 게 아니다.
 *
 * 쓰는 법:
 *   "$CHROME" --headless=new --remote-debugging-port=9333 --user-data-dir=<temp> about:blank &
 *   node review/web-shots-18.mjs http://127.0.0.1:9333 http://127.0.0.1:5118/ <출력 디렉터리>
 *
 * 티켓 17 의 `review/web-smoke-17.mjs` 와 같은 최소 CDP 드라이버다(의존성 없음).
 */
import fs from "node:fs";
import path from "node:path";

const [debugBase, pageUrl, outDir] = process.argv.slice(2);
const VIEWPORT = { width: 1000, height: 1200 };

const targets = await (await fetch(`${debugBase}/json/list`)).json();
const target = targets.find((t) => t.type === "page");
const ws = new WebSocket(target.webSocketDebuggerUrl);

let nextId = 0;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message);
    pending.delete(message.id);
  }
});
await new Promise((resolve) => ws.addEventListener("open", resolve));

function send(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", {
  ...VIEWPORT,
  deviceScaleFactor: 1,
  mobile: false,
});

fs.mkdirSync(outDir, { recursive: true });

for (const scheme of ["light", "dark"]) {
  await send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-color-scheme", value: scheme }],
  });
  await send("Page.navigate", { url: pageUrl });
  // 게스트 발급 → 오늘 퍼즐 → 순위·통계까지 네 번 왕복한다. 폰트(CDN)도 기다린다.
  await sleep(4000);

  const shot = await send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
  });
  const file = path.join(outDir, `home-${scheme}.png`);
  fs.writeFileSync(file, Buffer.from(shot.result.data, "base64"));
  console.log(`wrote ${file} (${fs.statSync(file).size} bytes)`);
}

ws.close();
