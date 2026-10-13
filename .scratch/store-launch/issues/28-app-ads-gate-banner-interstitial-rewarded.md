# 28: 광고 — UMP/ATT 게이트·배너 슬롯·전면(결과 후 1회)·보상형 힌트 미리 보기·광고 개인정보 설정

**What to build:** 앱 시작마다 UMP 동의 상태를 확인해 필요하면 폼을 띄우고, `canRequestAds` 일 때만 광고 SDK 를 초기화한다. 배너는 탭 바 아래 예약 슬롯에 뜨고, 전면 광고는 결과 시트 확인 후 퍼즐당 1회, 첫 제출 전엔 절대 안 뜬다. 보상형 광고를 끝까지 보면 힌트가 미리 열린다. EEA 사용자는 설정에서 광고 개인정보 선택을 바꿀 수 있다. 구독자(29) 는 모든 광고가 꺼지고 배너 슬롯이 사라진다.

**Blocked by:** 06, 24, 25

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §A.5, §B.21 광고 게이트, §B.23, US 4·5·5a·23~25·33·34. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 광고 게이트 순수 함수: (UMP 상태 required/notRequired/obtained/error, ATT 상태, 구독 권한) → {광고 로드 가능, 개인정보 설정 항목 표시}. 단위 테스트 4종 + 오류 시 이번 세션 광고 없음·다음 시작 재시도
- [ ] `google_mobile_ads` UMP `requestConsentInfoUpdate` → 폼 → `canRequestAds` 후 `MobileAds.initialize`. iOS 는 25 의 ATT 결과 이후. 광고 ID `--dart-define`, 디버그는 테스트 ID
- [ ] 배너: 슬롯 상시 예약(높이 고정), 로드 실패해도 레이아웃 불변. 전면: 결과 시트 닫힘 후 퍼즐당 1회(로컬 플래그 puzzle_id 기준), 첫 제출 전 금지(테스트)
- [ ] 보상형: HintCard 버튼 → 광고 완료 콜백 → `POST /puzzles/today/hint-unlock {puzzle_id}` → 힌트 표시, 409 처리. 광고 로드 실패 시 버튼 비활성 + 안내
- [ ] S4 "광고 개인정보 설정" 항목은 `privacyOptionsRequirementStatus == required` 일 때만 표시 → `showPrivacyOptionsForm`
- [ ] 광고 서비스 클래스는 인터페이스 + no-op 테스트 구현. 위젯 테스트: 게이트 상태별 배너 슬롯, 전면 타이밍, 보상형 → 힌트. `audit.native` 통과
