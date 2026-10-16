# 01: 프리팩터 — rate limit 데코레이터를 키 접두사 팩토리로

**What to build:** 동작 변화 없음. 분당 제한 데코레이터가 키 접두사를 인자로 받는 팩토리가 되어, 제출(`guess`)과 다른 용도(`challenge`)가 서로 예산을 안 나눠 쓴다. 기존 제출 경로는 같은 키·같은 한도를 유지한다.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 기존 제출 rate limit 테스트가 수정 없이(또는 호출 모양만 바꿔) 그대로 통과
- [ ] 다른 접두사로 두 번 장식한 두 엔드포인트가 서로 카운터를 공유하지 않는 테스트
- [ ] 분당 한도 초과 시 429 응답 모양 불변
