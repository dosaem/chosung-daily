# 28: S6 온보딩 3장·언어 선택·알림/ATT 사전 안내·"하는 법" 다시 보기

**What to build:** 첫 실행에 3장 온보딩(하루 한 문제 / 5번의 기회 / 매일 이어가기)과 언어 칩이 나오고, 알림 권한은 사전 안내 뒤에, iOS 는 ATT 안내 뒤에 시스템 프롬프트가 뜬다. S4 설정의 "하는 법" 자리에서 언제든 다시 볼 수 있다. 실제 알림 예약·광고 초기화는 30·31 이 이 화면의 결과를 쓴다.

**Blocked by:** 22, 27

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21 온보딩, SCREENS S6, US 33·35·46·47, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] S6 페이지뷰 3장 + 언어 칩(선택 시 `PATCH /me`), 완료 플래그 로컬 저장, 27 의 S4 "하는 법" 자리를 실제 진입점으로 채움(완료 플래그 유지)
- [ ] 알림 사전 안내 카드 → 허용 시 OS 권한 요청(Android 13+ `POST_NOTIFICATIONS`, iOS) — 결과를 상태로 보관(30 이 사용)
- [ ] iOS ATT 사전 안내 → `app_tracking_transparency` 프롬프트 — 결과를 상태로 보관(31 이 사용). Android 는 생략
- [ ] 태블릿(SCREENS T0): 온보딩 페이지뷰·ATT/알림 안내 카드는 `ReadingWidth`(600dp) 가운데, 가로 모드에서도 타일·삽화 크기는 폰과 같다. 위젯 테스트: 폭 1024 가로에서 3장 스와이프·언어 칩 동작
- [ ] 위젯 테스트: 온보딩 언어 선택 반영, 완료 후 재실행 시 홈 직행, iOS/Android 분기, 설정에서 재진입. `audit.native`(태블릿 폭 포함) 통과, 목업 `e6_onboarding` 대비 기록(2·3장·ATT 안내·알림 안내는 목업 없음 — 명세+토큰)

## 리뷰 노트 (plan-review r1)

- P3-5: Blocked by 에 25 추가("하는 법" 진입점이 S4 설정 리스트에 있음)

## 리뷰 노트 (plan-add r1)

- 번호 구 26 → 신 28. 위 노트의 번호는 당시 번호
- 태블릿 조건 추가(ReadingWidth 가운데 — 24 는 27 을 통해 전이 의존)
