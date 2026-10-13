# 29: 광고 — UMP/ATT 게이트·배너 슬롯·전면(결과 후 1회)·보상형 힌트 미리 보기·구독자 광고 없는 힌트·광고 개인정보 설정

**What to build:** 앱 시작마다 UMP 동의 상태를 확인해 필요하면 폼을 띄우고, `canRequestAds` 일 때만 광고 SDK 를 초기화한다. 배너는 탭 바 아래 예약 슬롯에 뜨고, 전면 광고는 결과 시트 확인 후 퍼즐당 1회, 첫 제출 전엔 절대 안 뜬다. 보상형 광고를 끝까지 보면 힌트가 미리 열리고, 구독 권한이 있으면 광고 없이 바로 열린다(US 32). EEA 사용자는 설정에서 광고 개인정보 선택을 바꿀 수 있다. 구독 권한은 `/me/stats` 의 `entitlement` 를 입력으로 받는다(갱신·타이머는 31).

**Blocked by:** 06, 24, 25, 26

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.5, §B.21 광고 게이트, §B.23, US 4·5·5a·23~25·31~34. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] ApiClient 에 `POST /puzzles/today/hint-unlock` 추가(Dio + Fake)
- [ ] 광고 게이트 순수 함수: (UMP 상태 required/notRequired/obtained/error, ATT 상태, 구독 권한) → {배너·전면 로드 가능, 힌트 미리 보기에 광고 필요 여부, 개인정보 설정 항목 표시}. 단위 테스트: UMP 4종 + 구독자(모든 광고 없음·힌트 광고 불필요) + 오류 시 이번 세션 광고 없음·다음 시작 재시도
- [ ] `google_mobile_ads` UMP `requestConsentInfoUpdate` → 폼 → `canRequestAds` 후 `MobileAds.initialize`. iOS 는 26 의 ATT 결과 이후. 광고 ID `--dart-define`, 디버그는 테스트 ID
- [ ] 배너: 22 의 슬롯에 로드(높이 고정, 로드 실패해도 레이아웃 불변), 구독 권한 있으면 슬롯 자체 제거. 전면: 결과 시트 닫힘 후 퍼즐당 1회(로컬 플래그 puzzle_id 기준), 첫 제출 전 금지, 구독자 없음(테스트)
- [ ] 보상형: HintCard 버튼 — 비구독자는 "광고 보고 힌트 미리 보기" → 광고 완료 콜백 → `hint-unlock`; **구독자는 레이블 "힌트 미리 보기" 로 광고 없이 바로 `hint-unlock`**. 409 처리, 광고 로드 실패 시 버튼 비활성 + 안내(위젯 테스트 두 경로)
- [ ] 25 의 S4 "광고 개인정보 설정" 자리: `privacyOptionsRequirementStatus == required` 일 때만 표시 → `showPrivacyOptionsForm`
- [ ] 광고 서비스 클래스는 인터페이스 + no-op 테스트 구현. 위젯 테스트: 게이트 상태별 배너 슬롯, 전면 타이밍, 보상형 → 힌트, 구독자 힌트 무광고. `audit.native` 통과, 목업 `e1_home`/`e7_home_dark`(HintCard·배너 슬롯) 대비

## 리뷰 노트 (plan-review r1)

- P1-04: US 32(구독자 광고 없는 힌트 미리 보기)를 게이트 출력 + HintCard 두 경로 + 테스트로 추가
- P1-15/P3-16: 참조 목업 명시
- 구 29 의 '권한 반영·next_check_at 타이머' 는 31 로 분리
