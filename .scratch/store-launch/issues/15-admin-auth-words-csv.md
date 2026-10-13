# 15: 운영자 페이지 — 구글 로그인 인증·단어 CRUD·CSV 업로드

**What to build:** 운영자(허용 이메일 두 개)만 기존 구글 로그인 세션으로 `/admin` 에 들어가 단어를 검색·추가·수정·삭제하고, `language,category,answer,hint` CSV 를 올려 추가/중복/오류 행 결과를 바로 본다. 다른 이메일은 403.

**Blocked by:** 02, 09

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.11(인증+CRUD+CSV), US 50~53, Further Notes 운영자 계정. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `ADMIN_EMAILS` 설정(기본값 없음, `.env.example` 에 두 운영자 이메일 주석). 판정 경로: 세션 `current_guest_id` → Guest → `Account.email ∈ ADMIN_EMAILS`(세션에 이메일이 없으므로 Account 에서 꺼낸다). 운영자 아닌 이메일 403, 세션 없음은 `/` 로 보내 "웹에서 구글 로그인 후 /admin 으로" 안내(현행 OAuth 진입이 Bearer `session/sync` 를 전제하므로 운영자 페이지에서 직접 로그인 시작하지 않는다). 테스트 3종
- [ ] 모든 `/admin` POST 는 01 의 CSRF 데코레이터를 거친다(테스트: 토큰 없으면 403)
- [ ] 단어 목록(언어·카테고리·검색어 필터, 페이지네이션)·추가·수정·삭제 Jinja 페이지, 09 의 토큰 CSS 사용. 저장 시 `mask` 재계산(02 의 순수 함수). 이미 퍼즐로 배정된 단어 삭제는 막는다
- [ ] CSV 업로드: UTF-8(BOM 허용), 헤더 검증, 행별 결과(추가/중복/오류+사유) 표 렌더. 서비스 함수는 파일 객체가 아닌 행 리스트를 받아 테스트 가능
- [ ] 운영자 페이지 `impeccable detect` 0건(목업 없음 — 명세+토큰)
- [ ] README "설계 판단" 에 "운영자 인증 = 기존 OAuth + 이메일 허용 목록" 추가, 운영 절에 CSV 포맷·LLM 생성 가이드 한 단락

## 리뷰 노트 (plan-review r1)

- P1-08: 운영자 판정 경로와 비로그인 처리를 현행 OAuth 세션 구조에 맞춰 확정
- P2-18: Blocked by 를 02, 09 로 줄임(CSRF 는 01, 토큰 CSS 는 09) — D0 단어 적재를 일찍 할 수 있음
