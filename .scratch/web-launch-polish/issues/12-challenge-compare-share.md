# 12: 대결 링크 웹 — 비교 카드·공유 텍스트 링크·E2E

**What to build:** 완료하면 결과 시트에 "나 vs 상대" 비교 카드(성공 > 시도 수 > 소요 시간 > 무승부)가 뜨고, 공유 텍스트 마지막 줄이 내 대결 링크(`?vs=…&utm_source=share`)가 된다(발급 실패 시 기존 공유 URL 로 폴백). 이미 끝낸 퍼즐을 열 때도 1회 발급. Playwright 왕복 시나리오(게스트 2명) 추가.

**Blocked by:** 08, 11

**Status:** ready-for-agent

- [ ] 비교 규칙 네 가지 결과(승·패·무승부·둘 다 실패) 시나리오
- [ ] 공유 텍스트 마지막 줄이 링크, 발급 실패 시 폴백
- [ ] E2E `11-challenge-link.spec.mjs` ko·en 통과
