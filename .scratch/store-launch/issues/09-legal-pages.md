# 09: 법적 문서 페이지 `/privacy`·`/terms` (ko/en)

**What to build:** 플레이어·스토어 심사자·구독 화면·Play Data safety 양식이 같은 도메인의 개인정보처리방침·이용약관을 본다. 한국어·영어가 `?lang=` 또는 Accept-Language 로 전환된다.

**Blocked by:** 01

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.15, US 45, 미정 9. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `/privacy`, `/terms` 가 Jinja 로 렌더되고 ko/en 본문이 있다. 개인정보처리방침에 수집 항목(게스트 토큰, 계정 이메일, 애플 refresh token, 시도 기록, 구독 식별자, 광고 ID), 보유 기간, 제3자 제공·위탁(Google, Apple, AdMob, Firebase Analytics, Sentry), 국외 이전, 만 14세 미만, 삭제 방법(`/account/delete` 링크), 연락처(운영자 메일)가 들어간다
- [ ] 이용약관에 구독 자동 갱신·해지 안내(스토어에서 해지)와 EULA 선택(미정 9: Apple 표준 EULA 사용 시 그 링크) 자리가 있다
- [ ] pytest 렌더 테스트(200, 두 언어 핵심 문구 포함), `impeccable detect` 0건(토큰 CSS 는 18 에서 완성되므로 여기선 기본 레이아웃만 — detect 는 18 에서 재실행)
- [ ] README 에 법적 문서 경로와 갱신 책임 메모
