# 17: 웹 플레이 흐름 — 퍼즐 언어 칩·서버 이력 복원·puzzle_id·409·리더보드 섹션·UI 문자열 ko/en

**What to build:** 웹 방문자가 퍼즐 언어 칩으로 ko/en 을 고르면 해당 퍼즐이 나오고, 보드는 서버 `attempts` 로 그려지며(로컬 history 제거), 제출에 `puzzle_id` 가 붙고 409 면 "새 퍼즐이 있어요" 와 함께 새로고침된다. 리더보드 섹션이 신설돼 익명 표시 + 내 순위를 보여주고, UI 문자열이 기기 언어(ko/en)로 나온다. 백업 코드 패널은 유지된다.

**Blocked by:** 04, 07

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.16(로직·i18n 부분), §A', 미정 13. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 언어 칩 → `PATCH /me` → `GET /puzzles/today` 재조회. 영어 퍼즐은 `mask` 로 타일 렌더(`r` 글자, `h` 빈 타일, `s` 간격), `chosung` 의존 제거
- [ ] 보드 복원이 서버 `attempts` 기반이고 localStorage 의 history 키만 제거한다 — 토큰 저장(`TOKEN_KEY`)과 "내 기록 백업/불러오기" 패널은 유지(스펙 §A.16 "백업 코드 유지"). en 보드 복원 시 `s` 위치 간격을 `mask` 로 다시 끼운다(미정 13 확정, 스펙 미정 항목에 기록)
- [ ] 제출에 `puzzle_id` 동봉(04 의 최소 변경을 정식화), 409 `PUZZLE_CHANGED` 처리 인라인 메시지 + 재조회. 언어 변경·계정 전환·백업 코드 전환 시 로컬 상태 폐기
- [ ] 리더보드 섹션 신설(현행 템플릿에 없음): `entries.display`·`is_me`·`me` 렌더, 통계 섹션은 `?language=` 명시. 섹션 전환 링크("순위 · 내 기록" 토글) 의 디자인은 18
- [ ] UI 문자열 ko/en 사전 + 기기 언어 감지(퍼즐 언어와 별개), 기존 문구 전부 사전으로 이동
- [ ] pytest 렌더 테스트 + 수동 체크리스트(README 또는 docs): 언어 전환, 새 탭 복원, 자정 경과 409, 계정 전환 후 상태 초기화, 백업 코드 복원

## 리뷰 노트 (plan-review r1)

- P2-8/P3-17: history 키만 제거하고 토큰·백업 패널은 유지한다고 명시
- P1-17: 리더보드 섹션 신설을 이 티켓에 명시
- P1-14/P2-14: ko/en 문자열 사전을 18 에서 이쪽으로 옮겨 18 크기를 줄임
