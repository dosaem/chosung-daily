import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const REPO_ROOT = path.resolve(fileURLToPath(new URL(".", import.meta.url)), "../../../..");
export const ARTIFACT_ROOT = process.env.E2E_ARTIFACTS
  ? path.join(process.env.E2E_ARTIFACTS, "web")
  : path.join(REPO_ROOT, "e2e-artifacts", "web");

const ticket = process.env.E2E_TICKET ?? "42";
// 스택 스크립트와 같은 기본 포트. 두 번째는 스토어 링크가 비어 있는 같은 앱이다.
export const BASE_URL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:50${ticket}`;
export const BASE_URL_NOSTORE = process.env.E2E_BASE_URL_NOSTORE ?? `http://127.0.0.1:51${ticket}`;

const manifestPath =
  process.env.E2E_MANIFEST ?? path.join(REPO_ROOT, "e2e-artifacts", "seed-manifest.json");

/** 시드가 못박은 (날짜, 언어) → 정답. 테스트는 정답을 여기서만 안다 — DB 를
 *  직접 훑지 않고, 화면에 보이는 날짜(`#date`)로 찾는다. */
export function manifest() {
  return JSON.parse(readFileSync(manifestPath, "utf8"));
}

export function puzzleFor(date, language) {
  const found = manifest().puzzles.find((p) => p.date === date && p.language === language);
  if (!found) {
    throw new Error(
      `manifest 에 ${date} ${language} 퍼즐이 없다 — 시드가 못박은 3일을 벗어났다. ` +
        "scripts/e2e_stack.sh seed 를 다시 돌려라.",
    );
  }
  return found;
}

/** 스택 스크립트를 부른다(날짜 넘기기 등). 테스트가 DB 에 직접 SQL 을 쏘지 않고
 *  43·44 와 같은 입구를 쓰게 하려고 스크립트를 거친다. */
export function stack(...args) {
  return execFileSync("bash", [path.join(REPO_ROOT, "scripts", "e2e_stack.sh"), ...args], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
}
