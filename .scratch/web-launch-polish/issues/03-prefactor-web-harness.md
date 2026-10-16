# 03: 프리팩터 — 웹 node 대역 확장과 카운트다운 일반화

**What to build:** 동작 변화 없음. 번들을 돌리는 node 대역이 `sessionStorage`·`dialog.showModal/close`·`location.search` 조작·`history.replaceState` 를 지원하고, 카운트다운 렌더 함수가 대상 요소·문구 키를 인자로 받는다(상태 카드는 지금과 같은 결과).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 기존 웹 JS 시나리오 전부 그대로 통과
- [ ] 대역에서 `sessionStorage` 저장/복원, `<dialog>` 열기/닫기(ESC), `?vs=` 쿼리 읽기, `replaceState` 가 동작하는 스모크 시나리오
- [ ] 카운트다운이 두 요소에 다른 문구 키로 그려지는 시나리오
