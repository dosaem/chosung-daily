# 02: 프리팩터 — 제출·조회를 "오늘 퍼즐"에서 "주어진 퍼즐"로 일반화

**What to build:** 동작 변화 없음. 정답 제출과 퍼즐 화면 조회가 "오늘 퍼즐을 찾는다"가 아니라 "주어진 퍼즐을 다룬다"가 되고, `counts_for_records` 플래그가 False 면 연속 기록(GuestStats)·리더보드·통계·DailyStats 반영을 **모두** 건너뛴다(잠금·정답 보관은 그대로). 오늘 경로는 True 로 호출해 지금과 똑같이 동작한다.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] 기존 제출·조회 테스트 전부 그대로 통과
- [ ] 플래그 False 로 제출하면 Attempt 만 남고 GuestStats·리더보드 ZSET·통계·DailyStats 가 바뀌지 않는 테스트
- [ ] 퍼즐 고정(`PUZZLE_CHANGED`)·`ALREADY_FINISHED` 규칙이 두 모드에서 같음
