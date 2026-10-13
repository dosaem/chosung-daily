# 07: 리더보드 익명화·내 순위·최근 7일 기록

**What to build:** 리더보드에서 모든 플레이어가 "게스트 #xxxx" 로 보이고 내 행만 강조되며, 21위 밖이어도 내 순위가 내려온다. 내 기록 화면을 위해 최근 7일의 언어별 성공/실패/진행 중/미플레이가 조회된다.

**Blocked by:** 03

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A' 리더보드·history, US 13·16a·16b. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `GET /puzzles/today/leaderboard?language=&limit=20` 응답이 `entries [{rank, display, attempts, seconds, is_me}]` + `me {rank, attempts, seconds} | null`(ZRANK) 이고 기존 `guest_id`·`solved_in_seconds` 는 제거된다. `display` = `"게스트 #" + guest.id 16진 4자리`
- [ ] 테스트: 25명 정답 중 내가 23위일 때 `entries` 20개 + `me.rank == 23`; 미정답이면 `me == null`; 기존 `test_leaderboard.py` 를 새 필드로 수정
- [ ] `GET /me/history?days=7` 이 `[{date, results: {ko, en}}]` 를 KST 날짜 기준으로 돌려주고 각 값은 success|fail|in_progress|none. days 상한 31
- [ ] README API 표 갱신, "설계 판단" 에 "리더보드 익명 표시" 추가
