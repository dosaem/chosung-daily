# 26: S2 결과 시트 — 분포·카운트다운·공유·연결 안내 자리·분석 이벤트

**What to build:** 정답·실패 후 결과 시트에서 시도별 정답자 분포와 내 위치, 다음 퍼즐까지 KST 카운트다운을 보고 네이티브 공유 시트로 웹 링크가 붙은 결과를 공유한다. Firebase Analytics 이벤트 4개의 정의와 서비스가 생기고 이 화면이 `puzzle_complete`·`share` 를 찍는다.

**Blocked by:** 07, 25

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21·24, SCREENS S2, US 6·9~11·20, 미정 20. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `GET /puzzles/today/stats` 추가(Dio + Fake)
- [ ] S2 바텀시트: 결과 헤더(성공/실패), 분포 막대 + 내 위치, KST 카운트다운, 공유 버튼(`share_plus`, 텍스트에 `https://chosung.dosaem.com/?utm_source=share`), "기록을 지키려면 연결하세요" 1회 안내 자리(동작·플래그는 29)
- [ ] Analytics 서비스 인터페이스 + Firebase 구현 + no-op 테스트 구현. 이벤트 4개 확정: `puzzle_complete(language, success, attempts)`, `share`, `paywall_view`, `subscribe_start`(뒤 둘은 32 가 발화). 스펙 미정 항목 20 에 확정 결과 기록
- [ ] 위젯 테스트: 결과 시트 렌더(성공/실패), 공유 텍스트 구성, `puzzle_complete`·`share` 호출(no-op Analytics 검증)
- [ ] 태블릿(SCREENS T2): 결과 시트는 24 의 `showAdaptiveSheet` 로 띄워 compact 는 바텀시트, medium 이상은 가운데 다이얼로그(최대 560dp). 위젯 테스트: 폭 744 에서 다이얼로그로 렌더, 공유·순위 버튼 동작 동일
- [ ] `audit.native`(태블릿 폭 포함) 통과, 목업 `e2_result` 대비 기록

## 리뷰 노트 (plan-review r1)

- P1-14/P2-14/P3-8: 구 24(S2+S3+S4+분석) 를 24(S2+분석) / 25(S3+S4) 로 분할 — 세 화면 + 이벤트가 한 세션 상한을 넘는다는 세 리뷰어 공통 지적 수용. 이후 번호 +1
- P1-18: `paywall_view`·`subscribe_start` 발화 주체를 30 으로 명시

## 리뷰 노트 (plan-add r1)

- 번호 구 24 → 신 26. 위 노트의 번호는 당시 번호
- 태블릿 조건 추가(24 의 AdaptiveSheet 사용; 24 는 25 를 통해 전이 의존)
