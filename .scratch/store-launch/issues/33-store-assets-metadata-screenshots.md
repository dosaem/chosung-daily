# 33: 스토어 자산 — 앱 아이콘·스플래시(OVERRIDES §8)·다크모드 스크린샷 5장×ko/en·메타데이터·업로드 워크플로

**What to build:** 앱 아이콘·스플래시가 OVERRIDES §8 콘셉트(다크 배경 `#0F172A` 에 brand 오렌지 타일 하나 + 흰 초성 "ㅊ", 영문 스토어도 같은 아이콘, 스플래시 같은 색)로 들어가고, 시뮬레이터 스크린샷(iPhone 6.9"/6.5", iPad 13", Android phone)이 다크모드 기준 5장(홈/결과/리더보드/내 기록/언어 선택) × ko/en 으로 스크립트로 생성되며, 스토어 텍스트(ko/en)·심사 노트가 레포에 있고 워크플로로 업로드된다.

**Blocked by:** 24, 25, 26, 32

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.25, BASELINE, US 67, 미정 4, OVERRIDES §8, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 아이콘·스플래시: OVERRIDES §8 그대로 — 다크 배경 `#0F172A`, brand 오렌지 타일 1개, 흰 "ㅊ"; SVG 원본 + `flutter_launcher_icons`·`flutter_native_splash`(스플래시 동색, 라이트/다크 동일) 적용. Editorial Light 와 다른 톤이 의도임을 README Flutter 절에 한 줄(OVERRIDES §8 근거)
- [ ] `mobile/integration_test/store_screenshots_test.dart` + `~/Code/Habitopia/scripts/store_screenshots.sh` 복사·시나리오 재작성: 다크모드 강제, 5장 = 홈(S1)/결과(S2)/리더보드(S3)/내 기록(S4)/언어 선택(S6 온보딩 1장), ko·en 각각 — Fake ApiClient 로 결정적 데이터. 구독(S5) 은 포함하지 않는다(OVERRIDES §8 목록 기준)
- [ ] `mobile/android/fastlane/metadata/android/{ko-KR,en-US}`, `mobile/ios/fastlane/metadata/{ko,en-US}`, `review_information`(Sandbox 테스터 안내·구독 테스트 방법·계정 삭제 경로 — 계정 정보는 플레이스홀더, 실제 값은 사람이 ASC 콘솔에 입력) 작성. 이름 "오늘의 초성"/"Hidden Vowels"(미정 4 대체명 메모)
- [ ] `appstore-metadata.yml`·`asc-submit.yml` 등 BASELINE 워크플로 복사·치환(수동 디스패치, `mobile/` 경로)
- [ ] 스크린샷 스크립트 로컬 실행 결과 파일 목록 기록. 업로드 실행은 사람(D3)

## 리뷰 노트 (plan-review r1)

- P1-03/P2-4/P3-3: 아이콘·스플래시·스크린샷을 OVERRIDES §8 그대로로 교체(DESIGN_DIR 우선). 콘셉트를 Editorial Light 로 바꾸려면 OVERRIDES §8 을 먼저 고쳐야 함 — 사용자 확인 항목으로 응답 문서에 기록
- P1-06/P3-4: 구독 스크린샷을 빼서 30 의존 불필요. 언어 선택 장면은 S6(26) 이라 Blocked by 에 25·26 추가(24 는 r2 에서 추가 — 아래 r2 노트)
- P2-16: review_information 자격 증명은 플레이스홀더
- (r2) P1-25/P2-21/P3-19: 결과(S2) 장면은 24 산출물 — Blocked by 에 24 추가
- (r3) 리뷰어 2: r1 노트가 r2 변경을 소급 반영하던 문구를 이력대로 되돌림
