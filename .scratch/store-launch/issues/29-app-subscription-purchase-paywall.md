# 29: 구독 — 구매 흐름(스트림·서버 검증·완료·복원)·Paywall S5·권한 반영·next_check_at 타이머

**What to build:** 플레이어가 Paywall 에서 스토어 현지화 가격으로 월 구독을 시작하면 서버 검증 성공 후에만 구매가 완료되고 즉시 모든 광고가 꺼지며 배너 슬롯이 사라진다. 결제 중 앱이 죽어도 다음 시작에 마무리되고, "구매 복원" 으로 재설치 후 권한을 되찾는다. 앱은 시작·복귀·`next_check_at` 타이머로 `/me/stats` 를 불러 권한 변화를 광고 상태에 바로 반영한다.

**Blocked by:** 13, 28

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8(Flutter 구매 흐름), ADR 0003, §B.21 S4·S5, US 26~32·30a~30d·34a, 미정 19. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `in_app_purchase`(StoreKit2 활성화, Android release merged manifest 에서 Play Billing Library 8+ 확인 절차를 RELEASE.md 에). 상품 `adfree_monthly`, 가격은 `ProductDetails.price` 그대로(상수 금지)
- [ ] 구매 스트림 → pending 대기(버튼 비활성 "결제 확인 중") → `POST /subscriptions/verify {store, receipt}` → 성공 후에만 `completePurchase`. 실패·종료 시 다음 시작에서 미완료 구매 재전송. 시작·복귀 시 `restorePurchases`/`queryPurchases` 결과도 verify 로 재전송
- [ ] 구매 상태→UI 판정 순수 함수(idle/pending/verifying/active/grace/error) 단위 테스트
- [ ] S5 Paywall: 제목·혜택 3줄·가격 카드·`primary-button` 구독 시작·구매 복원·약관/개인정보 링크·자동 갱신 안내. S4 구독 카드(미구독/구독 중/유예 중 + 관리 → 스토어)
- [ ] 권한 반영: `/me/stats` 의 `entitlement` → 광고 게이트 입력. 포그라운드에 머무는 동안 `next_check_at` 타이머로 재호출, 백그라운드 정지·복귀 즉시 호출. 가짜 시계 테스트: `next_check_at` 정확히 그 시각(경계 포함, 미정 19)에 호출되고 권한 해제 시 배너 슬롯 복구·전면 재개
- [ ] 위젯 테스트: 구독자 배너 제거, pending 버튼 비활성, 복원 성공. `audit.native` 통과, 목업 `e5` 대비 기록. README Flutter 절에 구독 상태 흐름 한 단락
