# 35: 스토어 자산 — 앱 아이콘·스플래시(OVERRIDES §8, 라이트 타일 3칸)·라이트 모드 스크린샷 5장×ko/en·메타데이터·업로드 워크플로

**What to build:** 앱 아이콘·스플래시가 OVERRIDES §8 콘셉트(라이트 배경 `#FAFAF9` 에 글자 없는 타일 3칸 — 양끝 brand `#EA580C`, 가운데 `tile-wrong` `#D6D3D1`; 영문 스토어도 같은 아이콘, 스플래시 같은 배경 + 같은 마크)로 들어가고, 시뮬레이터 스크린샷(iPhone 6.9"/6.5", iPad 13", Android phone)이 라이트 모드 기준 5장(홈/결과/리더보드/내 기록/언어 선택) × ko/en 으로 스크립트로 생성되며, 스토어 텍스트(ko/en)·심사 노트가 레포에 있고 워크플로로 업로드된다.

**Blocked by:** 16, 26, 27, 28, 34

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.25, BASELINE, US 67, 미정 4, OVERRIDES §8, 디자인 부족 항목. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] 아이콘·스플래시: OVERRIDES §8 그대로 — 120 뷰박스에 배경 `#FAFAF9` 120×120, 타일 30×34 `rx=7` 을 x=12/46/80, y=43 에 brand `#EA580C` / `#D6D3D1` / brand `#EA580C`, 글자 없음; SVG 원본 + `flutter_launcher_icons`(iOS 1024, Android adaptive foreground/background 분리)·`flutter_native_splash`(같은 배경 + 같은 마크, 라이트/다크 동일) 적용. "ㅊ" 대신 언어 중립 타일을 쓰는 이유를 README Flutter 절에 한 줄(OVERRIDES §8 근거)
- [ ] **30px 렌더에서 세 칸이 구분되는지 확인**(아이콘을 30×30 으로 래스터해 `.scratch/store-launch/design/icon-30px.png` 로 남긴다). 가운데 칸 `#D6D3D1` 과 배경 `#FAFAF9` 의 대비가 낮아 구분이 안 되면 가운데 칸을 한 단계 어둡게(예 `#A8A29E`) 조정하고 OVERRIDES §8 과 README 에 근거(대비비 수치)를 기록한다
- [ ] `mobile/integration_test/store_screenshots_test.dart` + `~/Code/Habitopia/scripts/store_screenshots.sh` 복사·시나리오 재작성: 라이트 모드 강제(앱 기본 톤과 일치 — OVERRIDES §8), 5장 = 홈(S1)/결과(S2)/리더보드(S3)/내 기록(S4)/언어 선택(S6 온보딩 1장), ko·en 각각 — Fake ApiClient 로 결정적 데이터. 구독(S5) 은 포함하지 않는다(OVERRIDES §8 목록 기준)
- [ ] `mobile/android/fastlane/metadata/android/{ko-KR,en-US}`, `mobile/ios/fastlane/metadata/{ko,en-US}`, `review_information`(Sandbox 테스터 안내·구독 테스트 방법·계정 삭제 경로 — 계정 정보는 플레이스홀더, 실제 값은 사람이 ASC 콘솔에 입력) 작성. 이름 "오늘의 초성"/"Hidden Vowels"(미정 4 대체명 메모)
- [ ] `appstore-metadata.yml`·`asc-submit.yml` 등 BASELINE 워크플로 복사·치환(수동 디스패치, `mobile/` 경로)
- [ ] iPad 13" 스크린샷 5장은 **태블릿 레이아웃**(24 의 rail + SCREENS 태블릿 절의 재배치)으로 찍힌다 — 폰 레이아웃을 가운데 띄운 결과는 불합격(스크립트가 폭 ≥600 에서 `NavigationRail` 존재를 단언)
- [ ] 메타데이터의 privacy/support URL 은 `/privacy`·`/terms`. 34 의 `app_privacy_details.json` 과 Play Data safety 답안 초안을 16 의 `docs/legal-checklist.md` 수집 항목·국외 이전 표와 1:1 대조해 다르면 여기서 둘 다 고친다(대조 결과를 체크리스트 "스토어 라벨" 절에 표로). ASC EULA 는 16 의 결정대로(표준이면 입력 없음)
- [ ] 스크린샷 스크립트 로컬 실행 결과 파일 목록 기록. 업로드 실행은 사람(D3)

## 리뷰 노트 (plan-review r1)

- P1-03/P2-4/P3-3: 아이콘·스플래시·스크린샷을 OVERRIDES §8 그대로로 교체(DESIGN_DIR 우선). 콘셉트를 Editorial Light 로 바꾸려면 OVERRIDES §8 을 먼저 고쳐야 함 — 사용자 확인 항목으로 응답 문서에 기록
- P1-06/P3-4: 구독 스크린샷을 빼서 30 의존 불필요. 언어 선택 장면은 S6(26) 이라 Blocked by 에 25·26 추가(24 는 r2 에서 추가 — 아래 r2 노트)
- P2-16: review_information 자격 증명은 플레이스홀더
- (r2) P1-25/P2-21/P3-19: 결과(S2) 장면은 24 산출물 — Blocked by 에 24 추가
- (r3) 리뷰어 2: r1 노트가 r2 변경을 소급 반영하던 문구를 이력대로 되돌림

## 리뷰 노트 (plan-add r1)

- 번호 구 33 → 신 35. 위 노트의 번호는 당시 번호(구 24·25·26·30·32 는 각각 신 26·27·28·32·34)
- Blocked by 에 16 추가(개인정보 라벨·Data safety 대조), iPad 스크린샷 태블릿 레이아웃 조건 추가(24 는 26~28 을 통해 전이 의존)
- (요구 3, 2026-10-14) r1 노트의 "사용자 확인 항목"(아이콘·스크린샷 톤) 은 **사용자가 확정**: 다크 배경 + "ㅊ" 아이콘을 버리고 라이트 배경 타일 3칸(언어 중립)으로, 스크린샷은 라이트 모드 기준으로. OVERRIDES §8 을 먼저 고쳤고 이 티켓의 제목·본문·완료 조건을 그에 맞췄다. 30px 가독성 확인 조건 추가. 미정 25 해소
