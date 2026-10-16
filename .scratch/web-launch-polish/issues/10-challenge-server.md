# 10: 대결 링크 서버 — 발급·조회 API

**What to build:** 퍼즐을 끝낸 게스트가 대결 링크를 발급받고(`POST`, 사실 객체 + url), 다른 게스트가 토큰으로 조회하면(`GET`) 익명 태그·상태·시도 수·소요 시간·`is_today` 를 받는다. 토큰은 Fernet 암호문(`"<guest_id>:<puzzle_id>"`, ttl 48시간)이라 게스트 ID 가 새지 않는다. 미완료면 `NOT_FINISHED`(409), 변조·만료면 404, 발급은 제출과 다른 rate limit 키.

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] 게스트 두 명으로 발급→조회 왕복, 사실은 DB Attempt 행에서(실패자 포함)
- [ ] 미완료 409, 변조/만료 404, 본인 링크 `is_me`, 어제 퍼즐 `is_today=false`
- [ ] 토큰 base64 디코드로 게스트 ID 가 안 보임
- [ ] 발급 10회 초과 429 가 제출 카운터를 안 건드림
