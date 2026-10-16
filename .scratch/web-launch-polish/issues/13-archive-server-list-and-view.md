# 13: 아카이브 서버 — 목록과 날짜별 조회(잠금 포함)

**What to build:** 지난 퍼즐 목록(`first_date` + 날짜별 상태, 최대 31일)과 날짜별 퍼즐 조회가 된다. 어제~7일 전은 누구나, 그 이전은 구독자(`build_entitlement`)만 — 비구독자는 403 `SUBSCRIPTION_REQUIRED`. 오늘·미래·미배정 날짜는 404. 언어는 게스트 선호 언어, 목록만 `?language=`. 끝난 퍼즐은 정답 포함.

**Blocked by:** 02, 04

**Status:** ready-for-agent

- [ ] 7일 안 열림 / 8일 전 비구독자 403 / 구독자 열림 / 오늘·미래·미배정 404
- [ ] 번호가 그 날짜 기준, 캐시 재사용
- [ ] 잘못된 날짜 문자열 404, `today`·`archive` 정적 라우트와 충돌 없음
- [ ] 새 오류 코드가 문구 사전·`ERROR_STRING_KEYS` 에 있음
