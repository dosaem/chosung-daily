# 06: 힌트 미리 보기(HintUnlock) 엔드포인트

**What to build:** 앱에서 보상형 광고를 본 플레이어(또는 구독자)가 3번째 오답 전에도 힌트를 미리 열 수 있고, 그 사실이 시도 횟수·순위에 영향을 주지 않으며, 한 번 열면 재진입·다른 기기에서도 `GET /puzzles/today` 에 힌트가 계속 채워져 온다.

**Blocked by:** 04

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.2 힌트 표시 규칙, §A.5, §A', Testing 필수 케이스. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `HintUnlock(guest_id, puzzle_id, unlocked_at)` PK(guest_id, puzzle_id) 마이그레이션. 머지 직전 `flask db heads` 1개
- [ ] `POST /puzzles/today/hint-unlock {puzzle_id}` 가 `GuestStats FOR UPDATE` 경로로 들어가 행을 넣고 `{hint}` 를 돌려준다. 끝난 퍼즐 409 `ALREADY_FINISHED`, 이미 열림 409 `HINT_ALREADY_UNLOCKED`, 퍼즐 불일치 409 `PUZZLE_CHANGED`. 서버는 광고 시청 여부를 알 수 없으므로(SSV 없음) 구독자·비구독자 구분 없이 같은 엔드포인트
- [ ] `hint` 채움 규칙이 `show_hint OR hint_unlocked` 로 완성돼 `GET /puzzles/today`·제출 응답 둘 다 반영, `hint_unlocked` 가 true 로 내려온다(테스트: 열고 새 client 로 조회)
- [ ] 힌트 열림이 시도 수·`solved_in_seconds`·리더보드에 영향 없음을 테스트로 고정
- [ ] 동시성 테스트(기존 `test_concurrency.py` 패턴): 힌트 미리 보기와 제출을 동시에 보내도 FOR UPDATE 로 직렬화되고 상태가 일관됨
- [ ] README "설계 판단" 에 "힌트 미리 보기 공정성·AdMob SSV 미사용 근거" 추가
