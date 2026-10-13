# 25: S3 순위 · S4 내 기록 — streak 카드·7일 그리드·설정 리스트 뼈대(계정·구독·알림·백업 코드·삭제·하는 법 자리)

**What to build:** 순위 탭이 언어별 익명 리더보드 + 내 순위를 보여주고, 내 기록 탭이 streak 카드·7일 그리드·설정 리스트(퍼즐 언어·법적 문서·오픈소스 라이선스·버전)를 보여준다. 계정·구독·알림·백업 코드·광고 개인정보·삭제·"하는 법" 항목은 자리(비활성 행 또는 placeholder 위젯)만 두고 26~30 이 채운다.

**Blocked by:** 07, 23

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21, SCREENS S3·S4, US 12~14·16a·16b·47·48. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `GET /puzzles/today/leaderboard`, `GET /me/history` 추가(Dio + Fake)
- [ ] S3: 퍼즐 언어 칩은 **표시 전용**(전환은 S4 설정), `entries` 리스트(내 행 강조), 21위 밖 `me` 행 하단 고정, 빈 상태 문구(OVERRIDES §7)
- [ ] S4: StreakBadge 3칸 카드, 7일 그리드(성공/실패/진행 중/미플레이), 설정 리스트 — 퍼즐 언어(`PATCH /me` 후 홈 재조회), 개인정보처리방침·이용약관(웹 링크), 오픈소스 라이선스, 버전. 자리만: AccountCard(27), 구독 카드(30), 일일 알림·리마인더(28), 백업 코드(27), 광고 개인정보 설정(29), 계정 삭제(27), "하는 법"(26) — 각 자리에 담당 티켓 번호 주석
- [ ] 위젯 테스트: 리더보드 `me` 행, 빈 상태, 7일 그리드, 퍼즐 언어 변경 후 재조회
- [ ] `audit.native` 통과, 목업 `e3_leaderboard`·`e4_records` 대비 기록

## 리뷰 노트 (plan-review r1)

- P2-3/P3-5: 26~30 이 올라탈 S4 호스트를 이 티켓이 만들고 자리마다 담당 번호를 적음
- P2-19/P3-14: S3 언어 칩 표시 전용 명시
