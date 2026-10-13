# 12: 구독 DB·스토어 검증 엔드포인트·상태 정규화

**What to build:** 앱이 스토어에서 받은 영수증(iOS JWS / Android purchaseToken)을 `POST /subscriptions/verify` 로 보내면 서버가 공식 라이브러리로 검증해 구독 행을 만들거나 갱신하고 현재 권한을 돌려준다. 같은 영수증을 여러 번 보내도 행이 하나이며, Google 의 구매 교체(linkedPurchaseToken)는 옛 행을 replaced 로 남긴다. Sandbox 영수증은 프로덕션 서버에서도 검증된다(심사용).

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8(DB·검증 엔드포인트), ADR 0003, §A', 미정 14. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `Subscription(guest_id, store, store_key, product_id, environment, status, expires_at, grace_expires_at, last_verified_at)` unique(store, store_key) 마이그레이션. status enum `active|grace|hold|expired|revoked|replaced`
- [ ] `clients/app_store.py`(App Store Server API 공식 라이브러리, JWS 검증, `environment` 로 엔드포인트 선택, Production 4040010 → Sandbox 1회 폴백)·`clients/play.py`(Google Play Developer API 공식 라이브러리) 래퍼 — 각 함수 하나, 타임아웃 3초
- [ ] 상태 매핑은 순수 함수 2개(Apple 응답→status, Google 응답→status): Apple 1→active, 4→grace(+`gracePeriodExpiresDate`), 3→hold, 2→expired, 5→revoked; Google ACTIVE/CANCELED(미만료)→active, IN_GRACE_PERIOD→grace, ON_HOLD→hold, EXPIRED→expired, revoked/환불→revoked, PAUSED→hold, PENDING→행 없음(미정 14 를 fixture 로 확정하고 스펙 미정 항목에 결과 기록)
- [ ] `POST /subscriptions/verify {store, receipt}` (Bearer): 상품 ID `adfree_monthly`·번들/패키지 확인 → 검증 → upsert(멱등) → `entitlement {active, until, status, source, next_check_at}` 응답. 실패 400 `RECEIPT_INVALID` / 스토어 장애 503 `STORE_UNAVAILABLE`. 복원·전환 시 같은 `store_key` 를 현재 게스트로 재지정
- [ ] 테스트(provider 래퍼 monkeypatch, fixture JSON): 멱등 중복 전달, linkedPurchaseToken 교체 → 옛 행 replaced, Sandbox 4040010 폴백, 다른 게스트 복원 재지정, 상품 ID 불일치 400
- [ ] 권한 계산은 이 티켓에서 임시로 `status == active|grace` 만 보고, 판정표·TTL 은 13 에서 완성(여기서 만든 `entitlement` 조립 함수를 13 이 교체)
- [ ] `.env.example` 에 App Store Server API 키·Play 서비스 계정 설정 추가. README "설계 판단" 에 "공식 라이브러리·RevenueCat 미사용·store_key 멱등" 추가
