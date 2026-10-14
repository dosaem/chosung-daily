# 25: S1 오늘 — 퍼즐 보드·제출·피드백·409 새로고침·상태 4종

**What to build:** 플레이어가 홈에서 가림 타일을 보고 답을 제출해 글자별 피드백(색+아이콘)을 받고, 앱을 껐다 켜도 서버 이력으로 보드가 복원되며, 퍼즐이 바뀌었으면 "새 퍼즐이 있어요" 로 새로고침된다. 로딩 스켈레톤·오프라인 배너·퍼즐 없음 카운트다운·인라인 재시도가 있고 "KST 00:00 새 퍼즐" 칩이 보인다(상시 카운트다운은 결과 시트 S2, 26).

**Blocked by:** 04, 22, 24

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21, SCREENS S1, US 1~3·3a·3b·6~8·15. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `GET /puzzles/today`, `POST /puzzles/today/guesses`, `PATCH /me` 추가(Dio + Fake)
- [ ] `PuzzleBoard`(mask 타일 r/h/s, 시도 5행, `tile-empty`/`tile-correct` 토큰), `GuessInput`(글자수 카운터, `primary-button`), `HintCard`(잠김/열림 — 보상형 버튼 동작은 31), StreakBadge(flame 만 brand, 숫자 foreground), 날짜 줄 + "KST 00:00 새 퍼즐" 칩
- [ ] Riverpod 상태: 로딩/정상/오류/오프라인/퍼즐 없음(카운트다운 카드 + 재시도)/완료("결과 보기" 버튼, 시트는 26). 제출 → `puzzle_id` 동봉 → 409 면 재조회 + 인라인 메시지. en 보드 복원 시 `s` 간격 재삽입(미정 13 과 동일 규칙)
- [ ] 앱 시작·포그라운드 복귀 시 `GET /puzzles/today` 재조회(알림 탭 복귀는 30 이 재사용)
- [ ] 위젯 테스트(Fake ApiClient): 홈 상태 4종, 제출→409→새로고침, 완료 상태에서 "결과 보기" 버튼, 다크모드 렌더
- [ ] 태블릿(SCREENS T1): 24 의 `AdaptiveScaffold` 안에서 보드+입력이 `ReadingWidth`(최대 600dp) 가운데 열에 오고, expanded(≥840)에선 HintCard·"남은 기회" 가 오른쪽 열(최대 320dp)로 간다. 타일 크기는 폰과 같다(확대 금지). 위젯 테스트: 폭 390/744/1024 레이아웃 분기, 744→390 폭 변경(Split View) 후 입력 중 텍스트·보드 상태 유지
- [ ] `audit.native` 체크리스트(태블릿 폭 포함) 통과, 목업 `e1_home`/`e7_home_dark` 대비 스크린샷 기록(태블릿은 SCREENS T1 와이어 대비)

## 리뷰 노트 (plan-review r1)

- P2-9/P3-15: S1 은 칩 + 퍼즐 없음 카운트다운만, 상시 카운트다운은 S2(24) 로 정리

## 리뷰 노트 (plan-add r1)

- 번호 구 23 → 신 25. 위 노트의 번호는 당시 번호
- 태블릿 조건 추가(선택지 (a)), Blocked by 에 24 추가
