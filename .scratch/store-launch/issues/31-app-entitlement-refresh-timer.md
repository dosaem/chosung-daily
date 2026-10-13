# 31: 구독 권한 반영 — 시작/복귀 `/me/stats`·`next_check_at` 타이머·권한 해제 시 광고 복구

**What to build:** 앱이 시작·포그라운드 복귀 때 `/me/stats` 를 불러 `entitlement` 를 광고 게이트에 반영하고, 포그라운드에 머무는 동안 `next_check_at` 에 맞춰 타이머로 다시 불러 환불·hold 가 확인되면 최대 1시간 안에 배너 슬롯이 복구되고 전면 광고가 재개된다. 백그라운드에서는 타이머를 멈추고 복귀 때 즉시 호출한다.

**Blocked by:** 13, 29

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.8 재조회(a), ADR 0003, US 30a~30c, Testing 순수 함수(구독 재확인 타이머), 미정 19. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 권한 새로고침 스케줄 순수 함수: (지금, `next_check_at`, 앱 상태 foreground/background) → 다음 호출 시각 | 없음. 단위 테스트: 경계 포함(`now >= next_check_at`, 미정 19), 백그라운드 정지, 복귀 즉시
- [ ] 앱 시작·복귀·타이머 만료 시 `GET /me/stats` → `entitlement` → 29 의 게이트 재평가. 권한 사라지면 배너 슬롯 복구·전면 재개, 생기면 제거(위젯 테스트)
- [ ] 가짜 시계 테스트: 포그라운드에 둔 채 `next_check_at` 정확히 그 시각에 `/me/stats` 가 자동 호출되고 Fake 가 권한 없음을 돌려주면 광고 상태가 바뀐다
- [ ] 30 의 verify 응답 반영과 충돌하지 않도록 권한 상태의 단일 소유 Provider 를 두고 두 경로가 같은 곳을 갱신한다
- [ ] README Flutter 절에 "권한 재확인 타이머" 한 단락

## 리뷰 노트 (plan-review r1)

- P1-14/P2-14: 구 29 에서 분리된 절반
