# 32: 구독 — 구매 흐름(스트림·서버 검증·완료·복원)·Paywall S5·S4 구독 카드

**What to build:** 플레이어가 Paywall 에서 스토어 현지화 가격으로 월 구독을 시작하면 서버 검증 성공 후에만 구매가 완료되고, verify 응답의 권한이 즉시 광고 게이트에 들어가 광고가 꺼진다. 결제 중 앱이 죽어도 다음 시작에 마무리되고, "구매 복원" 으로 재설치 후 권한을 되찾는다. S4 구독 카드가 미구독/구독 중/유예 중을 보여준다.

**Blocked by:** 13, 16, 31

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8(Flutter 구매 흐름), ADR 0003, §B.21 S4·S5, US 26~30·30d·34a, 미정 20. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `POST /subscriptions/verify` 추가(Dio + Fake)
- [ ] `in_app_purchase`(StoreKit2 활성화, Android release merged manifest 에서 Play Billing Library 8+ 확인 절차를 RELEASE.md 자기 절에). 상품 `adfree_monthly`, 가격은 `ProductDetails.price` 그대로(상수 금지)
- [ ] 구매 스트림 → pending 대기(버튼 비활성 "결제 확인 중") → `POST /subscriptions/verify {store, receipt}` → 성공 후에만 `completePurchase`. 실패·종료 시 다음 시작에서 미완료 구매 재전송. 시작·복귀 시 `restorePurchases`/`queryPurchases` 결과도 verify 로 재전송. verify 응답 `entitlement` 로 31 이 만든 구독 권한 상태 Provider 를 즉시 갱신(새 Provider 를 만들지 않는다)
- [ ] 구매 상태→UI 판정 순수 함수(idle/pending/verifying/active/grace/error) 단위 테스트
- [ ] S5 Paywall: 제목·혜택 3줄("광고 없이 힌트 미리 보기" 포함)·가격 카드·`primary-button` 구독 시작·구매 복원·약관/개인정보 링크·자동 갱신 안내. 진입 시 `paywall_view`, 구독 시작 탭 시 `subscribe_start`(no-op Analytics 검증)
- [ ] 자동 갱신 안내·링크 문구는 16 의 `docs/legal-checklist.md` "자동 갱신 구독 고지" 행이 정한 필수 요소(상품명·기간·가격·자동 갱신·해지 방법·약관/방침 링크)를 전부 담고, ko/en 표현을 16 의 약관 구독 절과 같게 쓴다(위젯 테스트: 요소 6개 존재). 태블릿: Paywall 은 24 의 `showAdaptiveSheet`(폭 744 에서 가운데 다이얼로그) — 위젯 테스트 1건
- [ ] 27 의 S4 구독 카드 자리를 채움: 미구독 → Paywall / 구독 중 "광고 제거 · 갱신일" / 유예 중 "결제 확인 중 · 유예 …까지" + "관리"(스토어로)
- [ ] 위젯 테스트: 구독자 배너 제거, pending 버튼 비활성, 복원 성공, 분석 이벤트 2개. `audit.native`(태블릿 폭 포함, `review/impl-evidence-32.md` audit 표) 통과, 목업 `e5_paywall`·`e4_records`(구독 카드) 대비 기록. README Flutter 절에 구독 상태 흐름 한 단락

## 리뷰 노트 (plan-review r1)

- P1-14/P2-14: 구 29 를 30(구매·Paywall) / 31(권한 반영·타이머) 로 분할
- P1-18: `paywall_view`·`subscribe_start` 발화를 여기에 명시
- (r2) P1-27/P2-22/P3-20: 권한 Provider 는 29 소유, 이 티켓은 갱신만

## 리뷰 노트 (plan-add r1)

- 번호 구 30 → 신 32. 위 노트의 번호는 당시 번호(구 25·29·31 은 각각 신 27·31·33)
- Blocked by 에 16 추가(Paywall 고지 문구가 16 의 체크리스트·약관 문구를 따름), 태블릿 조건 추가
- (plan-add 리뷰 1) PA-9: `audit.native` 에 "(태블릿 폭 포함)" 추가, 기록 위치는 22 와 같은 impl-evidence audit 표
