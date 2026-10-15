/** 서버가 페이지에 심어 내려보낸 UI 문구 사전(`#ui-strings`)을 그대로 읽는다.
 *
 * 테스트가 문구를 또 적지 않는 이유: 사전의 주인은 서버다(README "17.").
 * 여기서 보는 건 "그 자리에 **어느 키**가 쓰였는가" 이고, 번역문 자체를 검증해야
 * 하는 몇 군데(게스트 접두사·en 복수형)는 `lib/i18n-literals.mjs` 에 테스트가
 * 따로 적어 둔 문자열로 본다 — 사전에서 기대값을 뽑으면 사전이 틀려도 통과한다.
 */
export async function uiStrings(page) {
  return JSON.parse(await page.locator("#ui-strings").textContent());
}

/** app.js 의 `t()` 와 같은 치환 규칙(`{name}`). */
export function format(template, vars = {}) {
  return template.replace(/\{(\w+)\}/g, (_, name) => vars[name]);
}
