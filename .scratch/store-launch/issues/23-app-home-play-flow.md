# 23: S1 오늘 — 퍼즐 보드·제출·피드백·409 새로고침·상태 4종·KST 카운트다운

**What to build:** 플레이어가 홈에서 가림 타일을 보고 답을 제출해 글자별 피드백(색+아이콘)을 받고, 앱을 껐다 켜도 서버 이력으로 보드가 복원되며, 퍼즐이 바뀌었으면 "새 퍼즐이 있어요" 로 새로고침된다. 로딩 스켈레톤·오프라인 배너·퍼즐 없음 카운트다운·인라인 재시도가 있고 KST 자정까지 남은 시간이 보인다.

**Blocked by:** 04, 22

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21, SCREENS S1, US 1~3·3a·3b·6~8·15. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `PuzzleBoard`(mask 타일 r/h/s, 시도 5행, `tile-empty`/`tile-correct` 토큰), `GuessInput`(글자수 카운터, `primary-button`), `HintCard`(잠김/열림 — 보상형 버튼은 28 에서 연결), StreakBadge(flame 만 brand, 숫자 foreground)
- [ ] Riverpod 상태: 로딩/정상/오류/오프라인/퍼즐 없음/완료. 제출 → `puzzle_id` 동봉 → 409 면 재조회 + 인라인 메시지. en 보드 복원 시 `s` 간격 재삽입(미정 13 과 동일 규칙)
- [ ] 앱 시작·포그라운드 복귀 시 `GET /puzzles/today` 재조회(알림 탭 복귀는 27 이 재사용)
- [ ] 위젯 테스트(Fake ApiClient): 홈 상태 4종, 제출→409→새로고침, 완료 상태에서 "결과 보기" 버튼, 다크모드 렌더
- [ ] `audit.native` 체크리스트 통과, 목업 `e1_home`/`e7_home_dark` 대비 스크린샷 수동 비교 기록
