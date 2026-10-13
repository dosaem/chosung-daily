# 24: S2 결과 시트·공유 / S3 순위 / S4 내 기록(7일 그리드·설정 리스트 뼈대) / 분석 이벤트

**What to build:** 정답·실패 후 결과 시트에서 시도별 정답자 분포와 내 위치, 다음 퍼즐 카운트다운을 보고 네이티브 공유 시트로 웹 링크가 붙은 결과를 공유한다. 순위 탭은 언어별 익명 리더보드 + 내 순위, 내 기록 탭은 streak 카드·7일 그리드·설정 리스트(법적 문서·라이선스·버전·퍼즐 언어)를 보여준다. Firebase Analytics 이벤트 4개가 찍힌다.

**Blocked by:** 07, 23

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.21·24, SCREENS S2·S3·S4, US 9~14·16a·16b·47·48. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] S2 바텀시트: 결과 헤더, 분포 막대 + 내 위치(`/puzzles/today/stats`), KST 카운트다운, 공유 버튼(`share_plus`, 텍스트에 `?utm_source=share` 링크), 첫 완료 후 "기록을 지키려면 연결하세요" 1회 안내 자리(동작은 26)
- [ ] S3: 언어 칩, `entries` 리스트(내 행 강조), 21위 밖 `me` 행 하단 고정, 빈 상태
- [ ] S4: StreakBadge 3칸 카드, `GET /me/history?days=7` 그리드(성공/실패/진행 중/미플레이), 설정 리스트 — 퍼즐 언어(`PATCH /me` 후 홈 재조회), 개인정보처리방침·이용약관(웹 링크), 오픈소스 라이선스, 버전. 계정·구독·알림·백업 코드·삭제 항목은 자리만(26·27·29)
- [ ] 분석 이벤트 4개 확정·구현: `puzzle_complete(language, success, attempts)`, `share`, `paywall_view`, `subscribe_start` — 스펙 미정 항목 20 에 확정 결과 기록. 테스트는 no-op Analytics 서비스로 호출 검증
- [ ] 위젯 테스트: 결과 시트 렌더(성공/실패), 리더보드 `me` 행, 7일 그리드. `audit.native` 통과, 목업 `e2`·`e3`·`e4` 대비 기록
