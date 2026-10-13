# 14: 계정 삭제 — API·웹 페이지·CSRF·애플 연결 철회

**What to build:** 플레이어가 앱(`DELETE /me`) 또는 웹 `/account/delete` 에서 계정과 모든 기록을 지울 수 있다. 웹은 로그인된 세션 + 확인 폼 + CSRF 토큰을 거치고 GET 으로는 절대 삭제되지 않는다. 애플 계정이면 애플 쪽 연결(Sign in with Apple)도 실제로 철회되며, 철회 실패는 매일 재시도하고 7일 뒤 폐기한다. 삭제 후 옛 토큰은 401 이고 웹은 새 게스트로 시작한다.

**Blocked by:** 06, 10, 12

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.7, §A.11(CSRF 공유), US 21·22·22a, 미정 11. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 삭제 서비스 함수 하나가 Attempt, GuestStats, Account, HintUnlock, Subscription, 오늘 리더보드 `ZREM`(언어별), Guest 삭제를 한 트랜잭션으로 수행하고 커밋한다. 삭제 후 Bearer 요청 401
- [ ] CSRF 헬퍼: 세션에 1회용 토큰을 심고 폼 hidden 으로 받아 검증, 불일치 403 `FORBIDDEN`. 15 가 재사용할 수 있게 데코레이터/헬퍼로 분리
- [ ] `GET /account/delete`: 로그인 세션이면 확인 폼(ko/en, "되돌릴 수 없음·구독은 스토어에서 따로 해지"), 아니면 안내 + 운영자 메일. `POST /account/delete`: 세션 없음 401, CSRF 불일치 403, 성공 시 세션 비우고 `/` 리다이렉트. GET 은 상태 변경 없음(테스트)
- [ ] 애플 revoke: `clients/apple.py` 에 revoke 래퍼 추가, 저장된 `refresh_token` 과 `provider_client_id` 에 맞는 client_id·client_secret(iOS 연결 = 번들 ID, 웹 연결 = Services ID; 11 의 접근자 사용)으로 호출. 테스트: 두 경우 각각 올바른 client_id 로 호출됨
- [ ] revoke 실패 시 삭제는 진행하고 `AppleRevocationRetry(refresh_token_enc, client_id, created_at)` 행 생성(마이그레이션), Beat 매일 재시도, 7일 초과 폐기 + `notify_operator`
- [ ] 웹 프론트: 삭제 성공 리다이렉트 후 localStorage 토큰을 버리고 새 게스트를 발급한다(JS + 수동 체크리스트 항목)
- [ ] README "설계 판단" 에 "삭제 한 커밋·CSRF·애플 revoke 재시도" 추가, Play Data safety 삭제 URL 로 `/account/delete` 명시
