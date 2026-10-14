# 24: 태블릿 적응형 뼈대 — breakpoint 헬퍼·NavigationRail·읽기 폭·AdaptiveSheet·배너 슬롯 위치·회전/Split View

**What to build:** iPad·Android 태블릿(폭 ≥600dp)에서 앱이 폰 화면을 가운데 띄우는 대신 왼쪽 NavigationRail + 넓은 콘텐츠 영역으로 보인다. 폰에서는 22 의 하단 탭 바 그대로다. 가로/세로 회전과 iPad Split View 로 폭이 바뀌면 상태를 잃지 않고 레이아웃만 바뀐다. 이 티켓은 뼈대와 헬퍼만 만들고(탭 내용은 placeholder), 각 화면 티켓(25~32)이 SCREENS "태블릿 레이아웃" 절(T0~T4)대로 자기 화면을 재배치한다.

**Blocked by:** 22

**Status:** ready-for-agent

**스펙 참조:** `.scratch/store-launch/spec.md` §B.19·21, US 15a, 미정 24, SCREENS "앱 탭 구조"·"태블릿 레이아웃", OVERRIDES §4(카드 패딩 태블릿 24)·§5(배너). 22 의 `audit.native` P2 "태블릿에서도 하단 탭 바" 가 출발점. 용어는 `CONTEXT.md`, 디자인은 `design/SCREENS.md` + `design-system/hidden-vowels/OVERRIDES.md`(충돌 시 OVERRIDES 우선).

공통 규칙(병렬 티켓 충돌 방지): README "설계 판단"·API 표, `.env.example`, `docs/RELEASE.md`, 스펙 "미정 항목" 은 자기 번호 소제목(`### NN.`)/자기 행만 섹션 끝에 덧붙인다(파일·절이 없으면 만든다). 코디네이터는 번호순으로 머지한다. 마이그레이션을 만드는 티켓은 머지 직전 `flask db heads` 가 1개여야 하고, 아니면 선행 머지 리비전 위로 `down_revision` 을 재설정한다.

- [ ] `AppBreakpoint` 헬퍼: `MediaQuery.sizeOf(context).width` 기준 compact(<600) / medium(600~839) / expanded(≥840) 3단. **기기 종류·OS 가 아니라 현재 폭**으로만 판정(Split View·회전 대응). 단위 테스트: 경계 599/600/839/840
- [ ] `AdaptiveScaffold`: compact = 22 의 `NavigationBar`(하단 탭 3개) 유지, medium 이상 = 왼쪽 `NavigationRail`(아이콘+라벨, 선택 상태는 OVERRIDES 토큰 — brand 는 아이콘·밑줄만, 하단 탭과 같은 3항목·같은 go_router 경로). 22 의 "iPad 중앙 정렬 최대 600px 래퍼" 는 제거하고 `ReadingWidth`(기본 최대 600dp, 화면별 `maxWidth` 인자) 로 대체 — 22 의 완료 조건(3탭·배너 슬롯·S7 분기)과 테스트는 그대로 통과
- [ ] 배너 슬롯 위치: compact = 탭 바 위(현행), medium 이상 = **콘텐츠 영역 하단(rail 제외 폭)**, safe area 위, 높이는 그 폭의 어댑티브 배너 높이로 예약(OVERRIDES §5 레이아웃 점프 금지). 슬롯이 현재 폭을 `bannerWidth` 로 노출해 31 이 그 폭으로 로드한다(광고 로드 자체는 31)
- [ ] `showAdaptiveSheet`: compact = 바텀시트, medium 이상 = 가운데 다이얼로그(최대 폭 560dp, 상하 여백 — SCREENS T2) — 26(S2)·29(백업 코드·삭제)·32(Paywall) 가 사용
- [ ] 회전·Split View: 폭이 compact↔medium 을 넘나들 때 현재 탭·입력 중 텍스트·스크롤 위치가 유지된다(위젯 테스트: `tester.binding.setSurfaceSize` 390→744→390 후 상태 동일). iPad Split View 최소 폭(약 320dp)은 compact 로 떨어진다
- [ ] 위젯 테스트: 폭 390 = NavigationBar·rail 없음 / 744·1024 = rail·NavigationBar 없음, 세 탭 전환이 양쪽에서 같은 경로. `flutter analyze` 0건, `audit.native` 체크리스트에 "태블릿 폭(744·1024·1366) 포함" 항목을 추가해 통과 기록
- [ ] README Flutter 절에 "태블릿 대응 = 폰 레이아웃 + rail + 폭에 따른 재배치, 기기 종류가 아닌 폭 기준" 한 단락. 2열 세부 폭·Split View 최소 폭 등 미정 24 결과 기록

## 리뷰 노트 (plan-add r1)

- 사용자 요구 "태블릿에 그래도 맞게끔은 하자"(2026-10-14) 로 추가. 선택지 (a) "뼈대 1장 + 화면 티켓별 태블릿 조건" 채택 — 근거는 `review/plan-add-r1-response.md`
- 22 는 리뷰 수정 중이라 티켓 수정 금지 — 22 가 만든 3탭 뼈대·600px 래퍼의 교체는 이 티켓이 22 머지 후 한다
