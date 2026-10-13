# 30: 구독 — 구매 흐름(스트림·서버 검증·완료·복원)·Paywall S5·S4 구독 카드

**What to build:** 플레이어가 Paywall 에서 스토어 현지화 가격으로 월 구독을 시작하면 서버 검증 성공 후에만 구매가 완료되고, verify 응답의 권한이 즉시 광고 게이트에 들어가 광고가 꺼진다. 결제 중 앱이 죽어도 다음 시작에 마무리되고, "구매 복원" 으로 재설치 후 권한을 되찾는다. S4 구독 카드가 미구독/구독 중/유예 중을 보여준다.

**Blocked by:** 13, 29

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8(Flutter 구매 흐름), ADR 0003, §B.21 S4·S5, US 26~30·30d·34a, 미정 20. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `POST /subscriptions/verify` 추가(Dio + Fake)
- [ ] `in_app_purchase`(StoreKit2 활성화, Android release merged manifest 에서 Play Billing Library 8+ 확인 절차를 RELEASE.md 자기 절에). 상품 `adfree_monthly`, 가격은 `ProductDetails.price` 그대로(상수 금지)
- [ ] 구매 스트림 → pending 대기(버튼 비활성 "결제 확인 중") → `POST /subscriptions/verify {store, receipt}` → 성공 후에만 `completePurchase`. 실패·종료 시 다음 시작에서 미완료 구매 재전송. 시작·복귀 시 `restorePurchases`/`queryPurchases` 결과도 verify 로 재전송. verify 응답 `entitlement` 를 29 의 게이트 입력으로 즉시 반영
- [ ] 구매 상태→UI 판정 순수 함수(idle/pending/verifying/active/grace/error) 단위 테스트
- [ ] S5 Paywall: 제목·혜택 3줄("광고 없이 힌트 미리 보기" 포함)·가격 카드·`primary-button` 구독 시작·구매 복원·약관/개인정보 링크·자동 갱신 안내. 진입 시 `paywall_view`, 구독 시작 탭 시 `subscribe_start`(no-op Analytics 검증)
- [ ] 25 의 S4 구독 카드 자리를 채움: 미구독 → Paywall / 구독 중 "광고 제거 · 갱신일" / 유예 중 "결제 확인 중 · 유예 …까지" + "관리"(스토어로)
- [ ] 위젯 테스트: 구독자 배너 제거, pending 버튼 비활성, 복원 성공, 분석 이벤트 2개. `audit.native` 통과, 목업 `e5_paywall`·`e4_records`(구독 카드) 대비 기록. README Flutter 절에 구독 상태 흐름 한 단락

## 리뷰 노트 (plan-review r1)

- P1-14/P2-14: 구 29 를 30(구매·Paywall) / 31(권한 반영·타이머) 로 분할
- P1-18: `paywall_view`·`subscribe_start` 발화를 여기에 명시
