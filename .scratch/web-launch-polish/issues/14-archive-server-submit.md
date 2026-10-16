# 14: 아카이브 서버 — 날짜별 제출(기록 미반영)

**What to build:** 지난 퍼즐에 정답을 제출할 수 있다. 규칙(5번·힌트·피드백·퍼즐 고정·`ALREADY_FINISHED`)은 오늘과 같지만 연속 기록·누적·리더보드·통계·DailyStats 는 바뀌지 않는다. 안 끝낸 지난 퍼즐은 이어서 풀고, 끝낸 퍼즐은 재제출 409. 잠긴 날짜 제출은 403. 제출 rate limit 은 오늘과 같은 키.

**Blocked by:** 13

**Status:** ready-for-agent

- [ ] 제출 뒤 Attempt 만 늘고 GuestStats·ZSET·통계·DailyStats 불변
- [ ] 이어서 풀기·재제출 409·잠김 403
- [ ] `/me/history` 의 그 날짜 칸이 아카이브 결과로 채워짐
