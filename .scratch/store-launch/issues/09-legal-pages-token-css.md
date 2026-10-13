# 09: 법적 문서 페이지 `/privacy`·`/terms` (ko/en) + 웹 디자인 토큰 CSS

**What to build:** 플레이어·스토어 심사자·구독 화면·Play Data safety 양식이 같은 도메인의 개인정보처리방침·이용약관을 본다. 한국어·영어가 `?lang=` 또는 Accept-Language 로 전환된다. 이 티켓이 OVERRIDES 토큰을 CSS 변수(라이트/다크)로 옮긴 공용 스타일시트를 만들고, 운영자 페이지(15·16)와 메인 페이지(18)가 그걸 재사용한다.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.15, §A.16(토큰 CSS), US 45, 미정 9, OVERRIDES. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] OVERRIDES 토큰(배경·전경·brand·primary-button·tile-*·간격·폰트)을 CSS 변수로 옮긴 공용 스타일시트 1개(`prefers-color-scheme` 다크 포함, 그림자 없음, Pretendard). 기존 메인 페이지 스타일은 건드리지 않는다(18 에서 교체)
- [ ] `/privacy`, `/terms` 가 Jinja 로 렌더되고 ko/en 본문이 있다. 개인정보처리방침에 수집 항목(게스트 토큰, 계정 이메일, 애플 refresh token, 시도 기록, 구독 식별자, 광고 ID), 보유 기간, 제3자 제공·위탁(Google, Apple, AdMob, Firebase Analytics, Sentry), 국외 이전, 만 14세 미만, 삭제 방법(`/account/delete` 링크), 연락처(운영자 메일)가 들어간다
- [ ] 이용약관에 구독 자동 갱신·해지 안내(스토어에서 해지)와 EULA 선택(미정 9: Apple 표준 EULA 사용 시 그 링크) 자리가 있다
- [ ] pytest 렌더 테스트(200, 두 언어 핵심 문구 포함), 두 페이지에 `impeccable detect` 0건(공용 토큰 CSS 기준)
- [ ] README 에 법적 문서 경로와 갱신 책임 메모, "설계 판단" 에 "웹 토큰 CSS 를 법적 페이지에서 먼저 도입" 한 줄

## 리뷰 노트 (plan-review r1)

- P2-11: detect 0건을 이 티켓 자체 조건으로 확정(토큰 CSS 가 여기서 생기므로 모순 해소)
- P1-05/P2-5/P3-7: 토큰 CSS 소유자를 이 티켓으로 정해 15·16·18 이 재사용 — 18 이 운영자 페이지에 의존하지 않게 됨
