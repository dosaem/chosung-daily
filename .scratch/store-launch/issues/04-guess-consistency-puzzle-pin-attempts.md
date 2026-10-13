# 04: 제출 일관성·퍼즐 고정·시도 이력 복원

**What to build:** 플레이어가 영어 퍼즐에 공백·하이픈·대소문자를 섞어 입력해도 정답이 바르게 판정되고, 글자별 피드백이 구분자를 뺀 위치로 1:1 돌아온다. 보고 있던 퍼즐이 바뀐 상태(자정 경과, 다른 기기에서 언어 변경)로 제출하면 시도를 잃지 않고 409 `PUZZLE_CHANGED` 를 받는다. 앱을 껐다 켜거나 다른 기기에서 열어도 `GET /puzzles/today` 의 `attempts` 로 오늘 제출한 행이 그대로 복원된다.

**Blocked by:** 03

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.2 퍼즐 고정·시도 이력 복원·힌트 표시 규칙, §A', Testing 필수 케이스, 미정 12·13. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `POST /puzzles/today/guesses {puzzle_id, guess}` 에서 `puzzle_id` 가 없거나 "요청 시점 KST 오늘 × 게스트 현재 언어" 의 퍼즐과 다르면 409 `PUZZLE_CHANGED`, 시도 행·GuestStats 모두 변화 없음(테스트: 자정 경과 시나리오, 언어 변경 시나리오)
- [ ] 정답 비교: guess 의 공백·하이픈 제거 → `s` 제외 정답 글자열과 비교, en 은 대소문자 무시; 길이 불일치는 `VALIDATION_ERROR` 로 시도 미소비. `feedback` 길이 = `length`
- [ ] `GET /puzzles/today` 응답에 순서 있는 `attempts: [{guess, feedback}]` 와 `hint_unlocked`(이 티켓에서는 항상 false) 가 있고, 정답 행의 `feedback` 는 전부 true 로 채운다(미정 12 를 여기서 확정하고 스펙 미정 항목에 결과를 적는다)
- [ ] `hint` 는 `show_hint(3번째 오답 후)` 일 때 `GET /puzzles/today` 와 제출 응답 둘 다에 채워진다(`hint_unlocked` OR 조건은 06 에서 합류)
- [ ] 테스트: 시도 2회 후 새 test client 로 조회하면 같은 `attempts`; en 에서 `Harry Potter`/`harry-potter` 입력이 같은 결과; 기존 제출 테스트가 `puzzle_id` 동봉으로 수정돼 통과
- [ ] README "설계 판단" 에 "puzzle_id 고정과 409", "시도 이력을 서버가 돌려주는 이유" 추가
