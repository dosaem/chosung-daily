# 31: 스토어 자산 — 앱 아이콘·스플래시·스크린샷 자동화·메타데이터(ko/en)·업로드 워크플로

**What to build:** 앱 아이콘·스플래시가 Editorial Light 콘셉트로 들어가고, 시뮬레이터 스크린샷(iPhone 6.9"/6.5", iPad 13", Android phone)이 스크립트로 생성되며, 스토어 텍스트(ko/en)·심사 노트가 레포에 있고 워크플로로 업로드된다.

**Blocked by:** 24, 30

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.25, BASELINE, US 67, 미정 4, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

- [ ] 아이콘·스플래시: OVERRIDES 토큰(off-white 배경, near-black 글리프, brand 는 세부선만) 콘셉트로 SVG/PNG 제작 → `flutter_launcher_icons`·`flutter_native_splash` 적용. 다크 스플래시 포함
- [ ] `integration_test/store_screenshots_test.dart` + `~/Code/Habitopia/scripts/store_screenshots.sh` 복사·시나리오 재작성(홈 ko/en, 결과, 순위, 기록, 구독) — Fake ApiClient 로 결정적 데이터
- [ ] `android/fastlane/metadata/android/{ko-KR,en-US}`, `ios/fastlane/metadata/{ko,en-US}`, `review_information`(Sandbox 테스터 안내·구독 테스트 방법·계정 삭제 경로) 작성. 이름 "오늘의 초성"/"Hidden Vowels"(미정 4 대체명 메모)
- [ ] `appstore-metadata.yml`·`asc-submit.yml` 등 BASELINE 워크플로 복사·치환(수동 디스패치)
- [ ] 스크린샷 스크립트 로컬 실행 결과 파일 목록 기록. 업로드 실행은 사람(D3)
