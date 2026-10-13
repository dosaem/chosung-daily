# 13: 구독 권한 판정표·1h TTL 재조회·Beat 재검증

**What to build:** 구독자는 해지해도 만료일까지, 결제 실패 중엔 스토어 유예 기간 동안 광고가 없고, 자동 갱신 직후 서버가 아직 모르는 24시간도 권한이 유지된다. 환불(철회)이나 hold 가 확인되면 그 응답부터 권한이 사라지고, 앱을 쓰고 있는 구독자라면 `/me/stats` 의 1시간 TTL 재조회로 최대 1시간 안에 반영된다. 응답의 `next_check_at` 으로 앱이 다음 재확인 시각을 안다.

**Blocked by:** 12, 03

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8(권한 판정·재조회·Beat), ADR 0003, Testing 필수 케이스, 미정 1·15·18·19. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 권한 판정은 순수 함수(상태, expires_at, grace_expires_at, now) → bool: `revoked|hold|expired|replaced` 없음, `grace` → `grace_expires_at > now`, `active` → `expires_at + 24h > now`. 단위 테스트: active 유예 24h, grace 3일째 있음, hold 없음, revoked 없음
- [ ] `GET /me/stats` 가 `entitlement {active, until, status, source, next_check_at}` 를 돌려주고, `status ∈ {active, grace, hold}` 이며 `now >= last_verified_at + 1h`(경계 포함, 미정 19) 면 스토어 재조회 후 응답(타임아웃 3초, 실패 시 저장값 유지 + 실패 카운터). 만료 ±24h 안에서는 재조회 상한을 5분으로 둔다(미정 18 을 여기서 확정하고 스펙 미정 항목에 기록). `next_check_at = last_verified_at + 1h`
- [ ] 테스트: 만료 20일 전 구독의 provider 상태만 revoked 로 바꾸고 `last_verified_at` 을 정확히 1시간 전으로 둔 뒤 `/me/stats` → 권한 제거; 59분 전이면 재조회 없음; 만료 2일 뒤 verify 재전송 즉시 반영; 재조회 1시간 상한
- [ ] Beat 매일: `active|grace|hold` 중 만료 3일 이내 재조회(서비스 함수 직접 호출 테스트 + 배선). 재조회 실패가 연속 3회 누적된 구독이 있으면 `notify_operator`
- [ ] ADR 0003 본문의 "만료 ±24h" 문구를 §A.8 기준(1h TTL + ±24h 무상한→5분 상한)으로 갱신(미정 15)
- [ ] README "설계 판단" 에 "구독 상태 판정표·유예·TTL 재조회·웹훅 미도입 근거" 추가
