# 32: 릴리스 문서 완성 — `docs/RELEASE.md`·README Flutter 절·실기기/Sandbox 체크리스트·설계 판단 정리

**What to build:** 운영자가 `docs/RELEASE.md` 하나로 D0~D3 사람 작업, NAS 첫 배포, 복구 리허설, 실기기 체크(알림·광고·구독 Sandbox·UMP), 심사 제출 순서를 따라갈 수 있다. README 가 백엔드 "설계 판단" 전 항목과 짧은 Flutter 절을 갖추고 면접 설명 범위를 명시한다.

**Blocked by:** 16, 18, 20, 21, 26, 27, 29, 31

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.32, §D, Testing 실기기 체크리스트, 미정 항목 전체. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] `docs/RELEASE.md` 에 D0~D3 체크리스트(운영자 계정 두 개 명시, 제출일 기준 target SDK·Billing 8+ 재확인, Grace Period 설정, Data safety 삭제 URL, ASC 이름 중복 대응), NAS 첫 배포(프로젝트명·볼륨 확인), 복구 리허설, GitHub secrets 표 통합
- [ ] 실기기 체크리스트 통합: 알림 탭 cold/warm·같은 날/다음 날 리마인더(iOS·Android), Sandbox 구매·복원·pending·4040010 폴백·유예, UMP 재선택, ATT, 삭제 후 새 게스트 — 각 항목에 기대 결과
- [ ] README "설계 판단" 절이 §C.32 목록 전 항목을 갖추고 각 항목에 근거·대안이 한 단락씩 있는지 점검·보강. Flutter 절(상태 흐름·SDK 선택·테스트 경계) 최종
- [ ] 스펙 미정 항목 중 티켓에서 확정된 것(12·13·14·18·19·20)이 결과와 함께 갱신돼 있고, 남은 것은 "운영 데이터 후" 로 표시
- [ ] `docs/agents/` 와 `CONTEXT.md`·`docs/adr/` 가 최종 코드와 어긋나지 않는지 대조(용어 추가분 반영)
