# 16: 운영자 페이지 — 30일 배정표·잔량·점검/최소 버전 토글·Google Books 검색

**What to build:** 운영자가 언어별 다음 30일 퍼즐 배정표를 보고 특정 날짜의 단어를 바꾸며(캐시 즉시 무효화), 언어별 잔량(며칠치)을 보고, 점검 모드·최소 앱 버전을 토글하고, 영어 책 제목을 Google Books 로 검색해 단어로 추가한다.

**Blocked by:** 05, 08, 15

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.11(배정표·잔량·토글·Books), §A.14, US 54·55·58·59. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 배정표 페이지: 언어 탭, 오늘부터 30일(05 의 `schedule_puzzles(language, days)` 재사용), 각 날짜의 단어(미배정은 "자정에 배정") + 교체 폼. 교체 시 `puzzle:{date}:{lang}` 캐시 무효화, 이미 시도가 있는 날짜(오늘·과거)는 교체 금지(테스트)
- [ ] 잔량 카드: 05 의 서비스 함수 재사용, 14일 미만은 경고 색
- [ ] 점검 모드(on/off + 메시지)·최소 앱 버전(iOS/Android) 토글 → `AppSetting` 갱신 → `GET /config` 캐시 무효화(테스트: 토글 직후 `/config` 반영)
- [ ] `clients/google_books.py` 래퍼(함수 하나) + 카카오 책 검색과 같은 서비스 함수 시그니처, 검색 결과에서 선택 → en 단어 추가(가림 자동). `GOOGLE_BOOKS_API_KEY` 선택 설정(미정 3)
- [ ] `impeccable detect` 0건, README 운영 절 갱신
