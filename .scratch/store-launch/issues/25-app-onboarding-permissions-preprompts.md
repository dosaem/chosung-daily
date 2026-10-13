# 25: S6 온보딩 3장·언어 선택·알림/ATT 사전 안내·"하는 법" 다시 보기

**What to build:** 첫 실행에 3장 온보딩(하루 한 문제 / 5번의 기회 / 매일 이어가기)과 언어 칩이 나오고, 알림 권한은 사전 안내 뒤에, iOS 는 ATT 안내 뒤에 시스템 프롬프트가 뜬다. 설정에서 "하는 법" 으로 언제든 다시 볼 수 있다. 실제 알림 예약·광고 초기화는 27·28 이 이 화면의 결과를 쓴다.

**Blocked by:** 22

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21 온보딩, SCREENS S6, US 33·35·46·47, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] S6 페이지뷰 3장 + 언어 칩(선택 시 `PATCH /me`), 완료 플래그 로컬 저장, 설정 "하는 법" 에서 재진입(완료 플래그 유지)
- [ ] 알림 사전 안내 카드 → 허용 시 OS 권한 요청(Android 13+ `POST_NOTIFICATIONS`, iOS) — 결과를 상태로 보관(27 이 사용)
- [ ] iOS ATT 사전 안내 → `app_tracking_transparency` 프롬프트 — 결과를 상태로 보관(28 이 사용). Android 는 생략
- [ ] 위젯 테스트: 온보딩 언어 선택 반영, 완료 후 재실행 시 홈 직행, iOS/Android 분기. `audit.native` 통과, 목업 `e6` 대비 기록(2·3장·ATT 안내는 명세+토큰으로)
