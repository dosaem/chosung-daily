# 36: 릴리스 문서 완성 — `docs/RELEASE.md`·README Flutter 절·실기기/Sandbox 체크리스트·설계 판단 항목 점검

**What to build:** 운영자가 `docs/RELEASE.md` 하나로 D0~D3 사람 작업, NAS 첫 배포, 복구 리허설, 실기기 체크(알림·광고·구독 Sandbox·UMP), 심사 제출 순서를 따라갈 수 있다. README 가 백엔드 "설계 판단" 전 항목과 짧은 Flutter 절을 갖추고 면접 설명 범위를 명시한다.

**Blocked by:** 16, 18, 20, 21, 23, 29, 30, 32, 33, 35, 37

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §C.32, §D, Testing 실기기 체크리스트, 미정 항목 전체. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `docs/RELEASE.md` 에 D0~D3 체크리스트(운영자 계정 두 개 명시, 제출일 기준 target SDK·Billing 8+ 재확인, Grace Period 설정, Data safety 삭제 URL, ASC 이름 중복 대응), NAS 첫 배포(프로젝트명·볼륨 확인), 복구 리허설, GitHub secrets 표 통합(각 티켓이 남긴 절을 하나의 목차로 정리)
- [ ] 실기기 체크리스트 통합: 알림 탭 cold/warm·같은 날/다음 날 리마인더(iOS·Android), Sandbox 구매·복원·pending·4040010 폴백·유예, UMP 재선택, ATT, 삭제 후 새 게스트, iPad 가로/세로·Split View 에서 rail·배너·결과 시트 — 각 항목에 기대 결과
- [ ] 16 의 "출시 전 사람이 확인할 법적 항목" 절(통신판매업 신고, 보호책임자, 주소·전화 공개 결정, 전문가 검토, EULA, Data safety 일치)을 D1·D3 체크리스트에 통합
- [ ] README "설계 판단" 항목 체크(§C.32): [ ] 퍼즐 언어 모델(마이그레이션 1단계) [ ] 가림 포맷·puzzle_id 고정·시도 이력 응답 [ ] KST 고정 [ ] id_token 교환·aud 매트릭스·애플 refresh token 보관 [ ] 구독 상태 판정표·유예·Sandbox·완료 순서 [ ] 힌트 미리 보기 공정성 [ ] 로컬 알림 선택 근거와 취소 규칙 [ ] 애플 secret 요청 경로 갱신 [ ] 운영자 인증·CSRF [ ] Slack — 각 항목에 근거·대안 한 단락, 빠진 것은 보강
- [ ] README Flutter 절(상태 흐름·SDK 선택·테스트 경계·권한 재확인 타이머·로컬 알림 근거) 최종, 면접 설명 범위 문장 포함
- [ ] 스펙 미정 항목 중 티켓에서 확정된 것(9·12·13·14·18·19·20·21·22·23·24)이 결과와 함께 갱신돼 있고, 남은 것은 "운영 데이터 후" 로 표시
- [ ] `docs/agents/` 와 `CONTEXT.md`·`docs/adr/` 가 최종 코드와 어긋나지 않는지 대조(용어 추가분 반영)
- [ ] 코드·문서의 옛 티켓 번호 주석 정리: plan-add r1 번호 재배정(구 16→23, 구 23~34→25~36) 이전에 머지된 코드 주석(예 `mobile/lib/screens/home_shell.dart` "티켓 29·30" → 31·32)과 README("티켓 22~31" → 22~33)·RELEASE.md 의 티켓 번호를 신 번호로 갱신(대응표 `review/plan-add-r1-response.md` §2)

## 리뷰 노트 (plan-review r1)

- P3-18: §C.32 항목을 체크박스로 전개

## 리뷰 노트 (plan-add r1)

- 번호 구 34 → 신 36. 위 노트의 번호는 당시 번호(구 16·27·28·30·31·33 은 각각 신 23·29·30·32·33·35)
- Blocked by 에 16 추가, 법적 항목·태블릿 실기기 체크 통합 조건 추가
- (plan-add 리뷰 1) PA-5: 머지된 코드·README 의 옛 티켓 번호 주석 정리를 이 티켓 완료 조건으로 이관(코드는 계획 작업에서 건드리지 않음)
