# 18: 웹 디자인 — 토큰·다크모드·상태 화면·앱 CTA·Smart App Banner·법적 링크

**What to build:** 웹이 Editorial Light 디자인(토큰 CSS 변수, 다크모드 자동, 중앙 정렬 카드 최대 480px)으로 바뀌고, 로딩 스켈레톤·오프라인 배너·퍼즐 없음 카운트다운·인라인 재시도가 있으며, 결과 화면에 App Store/Google Play 배지와 "앱에서 연속 기록·알림" 안내, iOS Safari Smart App Banner, 공유 `?utm_source=share` 링크, 푸터에 `/privacy`·`/terms`·`/account/delete` 링크가 붙는다. UI 문자열은 ko/en.

**Blocked by:** 09, 14, 17

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.16(디자인 부분), SCREENS "웹" 절, OVERRIDES, US 8·41~45, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] OVERRIDES 토큰을 CSS 변수로 옮기고(라이트/다크 `prefers-color-scheme`), 주 버튼 `primary-button`, 빈 타일 `tile-empty`, 정답 타일 `tile-correct` 토큰 이름 그대로 사용. 그림자 없음
- [ ] 상태 4종 구현: 스켈레톤, 네트워크 오류 인라인 재시도, 오프라인 상단 배너(`navigator.onLine` + 요청 실패), 퍼즐 없음 카운트다운 + 재시도. 피드백 타일은 색 + 아이콘/굵기 병행(US 3)
- [ ] 결과 화면 앱 CTA(두 배지, `/config` 의 `store_urls` 또는 설정값), `<meta name="apple-itunes-app">` Smart App Banner, 공유 텍스트에 `https://chosung.dosaem.com/?utm_source=share`
- [ ] UI 문자열 ko/en 사전 + 기기 언어 감지(퍼즐 언어와 별개), 모든 폭 중앙 정렬 최대 480px
- [ ] `/privacy`·`/terms`·`/account/delete`·운영자 페이지까지 포함해 `impeccable detect` 0건, 다크모드 스크린샷 수동 확인
- [ ] pytest 렌더 테스트 + 수동 체크리스트(삭제 후 새 게스트 발급 포함) 갱신
