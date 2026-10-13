# 18: 웹 디자인 — 토큰 적용·다크모드·상태 화면·섹션 토글·앱 CTA·Smart App Banner·법적 링크

**What to build:** 웹 메인 페이지가 Editorial Light 디자인(09 의 토큰 CSS, 다크모드 자동, 중앙 정렬 카드 최대 480px)으로 바뀌고, 로딩 스켈레톤·오프라인 배너·퍼즐 없음 카운트다운·인라인 재시도가 있으며, 상단 "순위 · 내 기록" 링크로 섹션을 토글한다. 결과 화면에 App Store/Google Play 배지와 "앱에서 연속 기록·알림" 안내, iOS Safari Smart App Banner, 공유 `?utm_source=share` 링크, 푸터에 `/privacy`·`/terms`·`/account/delete` 링크가 붙는다. 백업/불러오기 패널은 토큰 디자인으로 유지된다.

**Blocked by:** 14, 17

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.16(디자인 부분), SCREENS "웹" 절, OVERRIDES, US 8·41~45, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 메인 페이지 스타일을 09 의 토큰 CSS 로 교체: 주 버튼 `primary-button`, 빈 타일 `tile-empty`, 정답 타일 `tile-correct` 토큰 이름 그대로, 그림자 없음, 모든 폭 중앙 정렬 최대 480px, 다크모드 자동
- [ ] 상태 4종 구현: 스켈레톤, 네트워크 오류 인라인 재시도, 오프라인 상단 배너(`navigator.onLine` + 요청 실패), 퍼즐 없음 카운트다운 + 재시도. 피드백 타일은 색 + 아이콘/굵기 병행(US 3)
- [ ] 상단 "순위 · 내 기록" 텍스트 링크로 같은 페이지 섹션 토글(SCREENS 웹 절). 백업/불러오기 패널 유지(디자인만 토큰), pytest 렌더로 확인
- [ ] 결과 화면 앱 CTA 두 배지 + `<meta name="apple-itunes-app">`: 08 의 `STORE_URL_IOS/ANDROID`·`APP_STORE_ID` 설정값을 쓰고 비어 있으면 배지·메타 태그를 렌더하지 않는다(테스트 2건). 공유 텍스트에 `https://chosung.dosaem.com/?utm_source=share`
- [ ] 푸터에 `/privacy`·`/terms`·`/account/delete` 링크
- [ ] 메인 페이지 `impeccable detect` 0건. 다크모드는 워커가 헤드리스 브라우저 스크린샷(라이트/다크 각 1장)을 `.scratch/store-launch/design/web-shots/` 에 남겨 기록(사람 확인 아님)
- [ ] pytest 렌더 테스트 + 수동 체크리스트(삭제 후 새 게스트 발급 포함) 갱신

## 리뷰 노트 (plan-review r1)

- P1-05/P2-5/P3-7: 완료 조건에서 운영자 페이지 detect 를 제거(15·16 이 각자 책임). 토큰 CSS 는 09 가 소유하고 14(`/account/delete`)→18 로 전이 의존하므로 Blocked by 는 14, 17 로 충분
- P1-17/P3-11: Smart App Banner 앱 ID 는 설정값, 비면 생략
- P3-10: 다크모드 확인을 워커의 헤드리스 스크린샷으로 확정, ko/en 사전은 17 로 이동해 크기를 줄임 — 분할하지 않음
