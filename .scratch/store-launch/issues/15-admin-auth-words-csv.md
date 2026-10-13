# 15: 운영자 페이지 — 구글 로그인 인증·단어 CRUD·CSV 업로드

**What to build:** 운영자(허용 이메일 두 개)만 기존 구글 로그인 세션으로 `/admin` 에 들어가 단어를 검색·추가·수정·삭제하고, `language,category,answer,hint` CSV 를 올려 추가/중복/오류 행 결과를 바로 본다. 다른 이메일은 403.

**Blocked by:** 02, 14

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.11(인증+CRUD+CSV), US 50~53, Further Notes 운영자 계정. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `ADMIN_EMAILS` 설정(기본값 없음, `.env.example` 에 두 운영자 이메일 주석) + 세션 연결 이메일로 판정하는 데코레이터. 운영자 아닌 이메일 403, 비로그인은 구글 로그인으로 리다이렉트(테스트)
- [ ] 모든 `/admin` POST 는 14 의 CSRF 헬퍼를 거친다(테스트: 토큰 없으면 403)
- [ ] 단어 목록(언어·카테고리·검색어 필터, 페이지네이션)·추가·수정·삭제 Jinja 페이지. 저장 시 `mask` 재계산(02 의 순수 함수). 이미 퍼즐로 배정된 단어 삭제는 막는다
- [ ] CSV 업로드: UTF-8(BOM 허용), 헤더 검증, 행별 결과(추가/중복/오류+사유) 표 렌더. 서비스 함수는 파일 객체가 아닌 행 리스트를 받아 테스트 가능
- [ ] 운영자 페이지는 디자인 토큰 CSS(OVERRIDES) 를 쓰되 목업 없음 — `impeccable detect` 0건
- [ ] README "설계 판단" 에 "운영자 인증 = 기존 OAuth + 이메일 허용 목록" 추가, 운영 절에 CSV 포맷·LLM 생성 가이드 한 단락
