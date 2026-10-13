# 17: 웹 플레이 흐름 — 퍼즐 언어 칩·서버 이력 복원·puzzle_id·409 새로고침

**What to build:** 웹 방문자가 퍼즐 언어 칩으로 ko/en 을 고르면 해당 퍼즐이 나오고, 보드는 서버 `attempts` 로 그려지며(로컬 history 제거), 제출에 `puzzle_id` 가 붙고 409 면 "새 퍼즐이 있어요" 와 함께 새로고침된다. 리더보드는 익명 표시 + 내 순위. 언어 변경·계정 전환 시 로컬 상태를 버린다.

**Blocked by:** 04, 07

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.16(로직 부분), §A', 미정 13. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 언어 칩 → `PATCH /me` → `GET /puzzles/today` 재조회. 영어 퍼즐은 `mask` 로 타일 렌더(`r` 글자, `h` 빈 타일, `s` 간격), `chosung` 의존 제거
- [ ] 보드 복원이 서버 `attempts` 기반이고 localStorage history 코드가 삭제된다. en 보드 복원 시 `s` 위치 간격을 `mask` 로 다시 끼운다(미정 13 확정, 스펙 미정 항목에 기록)
- [ ] 제출·(웹엔 없음) 힌트 요청에 `puzzle_id` 동봉, 409 `PUZZLE_CHANGED` 처리 인라인 메시지 + 재조회
- [ ] 리더보드가 `entries.display`·`is_me`·`me` 를 쓰고, 통계가 `?language=` 를 명시한다
- [ ] pytest 렌더 테스트 + 수동 체크리스트(README 또는 docs): 언어 전환, 새 탭 복원, 자정 경과 409, 계정 전환 후 상태 초기화
