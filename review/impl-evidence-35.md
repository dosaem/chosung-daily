# 티켓 35 구현 증거 — 스토어 자산·메타데이터·스크린샷·업로드 워크플로

**브랜치:** `dosaem/t35-store-assets-metadata-screenshots` · **날짜:** 2026-10-15
**범위:** 앱 아이콘·스플래시(OVERRIDES §8), 스토어 스크린샷 5장 x ko/en, fastlane
메타데이터·심사 노트, 업로드 워크플로 2개, 스토어 라벨 1:1 대조.
마이그레이션 0건(`migrations/` 변경 없음), 앱 화면 코드(`mobile/lib/`) 변경 0건 —
스크린샷은 **실제 화면 위젯을 그대로** 띄워 찍는다.

## 0. 한 줄 요약

아이콘·스플래시가 OVERRIDES §8 의 라이트 타일 3칸으로 바뀌었고(가운데 칸은 30px
가독성 때문에 `#A8A29E` 로 한 단계 어둡게 — 1.43:1 → 2.41:1), 스토어 스크린샷
5장 x ko/en 을 iPhone 6.9"/6.5"/iPad 13" 에서 스크립트로 찍었으며(총 54개
PNG), ko/en 메타데이터·심사 노트·업로드 워크플로 2개가 레포에 들어왔고, ASC 라벨과
Play 데이터 보안을 방침과 1:1 대조해 **차이 3건**을 찾아 2건을 고치고 1건을 사람
확인 항목으로 남겼다. **Android 에뮬레이터 캡처는 실패했다**(에뮬레이터 /data 가
가득 참) — BASELINE 과 같은 방식으로 iPhone 6.9" 캡처를 Play 폰 세트로 썼고 §7 에
그대로 적었다.

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| 아이콘·스플래시를 OVERRIDES §8 그대로(120 뷰박스·배경 `#FAFAF9`·타일 30x34 `rx=7` x=12/46/80·y=43, 글자 없음) + `flutter_launcher_icons`(iOS 1024, Android adaptive 분리)·`flutter_native_splash`(같은 배경·같은 마크, 라이트/다크 동일) | `mobile/test/store/app_icon_test.dart` 9개 — 원본 SVG 좌표/색, 글자 없음, 1024 래스터 픽셀, adaptive 전경 안전 영역, pubspec 설정, Android `colors.xml`·`values-v31`·`values-night-v31` | §3.1 |
| "ㅊ" 대신 언어 중립 타일을 쓰는 이유를 README Flutter 절에 한 줄 | README "22. Flutter 앱" 끝 + 새 절 "35." | §5 |
| **30px 렌더에서 세 칸 구분 확인** + 안 되면 가운데 칸을 어둡게 하고 근거(대비비) 기록 | `.scratch/store-launch/design/icon-30px.png`(30x30), `app_icon_test.dart` "세 칸이 배경과 구분된다 — 측정한 대비비" 가 **실제 래스터 픽셀**로 1.43:1 → 2.41:1 / brand 3.41:1 을 다시 잰다. 근거는 OVERRIDES §8 + README "35." | §3.1·§5 |
| `integration_test/store_screenshots_test.dart` + `scripts/store_screenshots.sh` 복사·재작성(라이트 모드 강제, 5장 = S1/S2/S3/S4/S6, ko·en, Fake ApiClient, S5 제외) | `mobile/test/store/store_screenshot_scenes_test.dart` 14개(ko·en x 폰·태블릿) + 실제 캡처 로그 | §3.2·§6 |
| fastlane 메타데이터 ko/en + `review_information`(Sandbox 안내·구독 테스트·계정 삭제 경로, 계정 정보는 플레이스홀더) | `tests/test_store_metadata.py` 47개 — 글자 수 한도, 앱 이름, URL, 심사 노트 항목, 플레이스홀더 | §3.3 |
| `appstore-metadata.yml`·`asc-submit.yml` 복사·치환(수동 디스패치, `mobile/` 경로) | 같은 파일의 워크플로 테스트 8개 — 트리거·working-directory·번들 ID·키 삭제·심사 연락처 secret | §3.3 |
| iPad 13" 5장이 **태블릿 레이아웃**(rail + 재배치)으로 찍힌다 — 폰 레이아웃이면 불합격 | 캡처 **전에** `store_screenshots_test.dart` 가 폭 ≥600 에서 `NavigationRail` 을 단언(없으면 파일이 안 남는다) + `store_screenshot_scenes_test.dart` "태블릿 폭의 셸 장면은 rail 로 찍힌다" + 실제 PNG(2064x2752) | §3.2·§6 |
| privacy/support URL 은 `/privacy`·`/terms`, 34 의 `app_privacy_details.json`·Play Data safety 를 16 의 체크리스트와 1:1 대조해 다르면 둘 다 고침(대조 결과를 "스토어 라벨" 절에 표로) | `tests/test_store_labels.py` 9개 + `docs/legal-checklist.md` "9. 스토어 라벨" + `docs/play-data-safety.md` | §3.4 |
| 스크린샷 스크립트 로컬 실행 결과 파일 목록 기록(업로드는 사람) | §6 파일 목록 54개 + 실행 로그 | §6 |

## 2. 바뀐 파일

**새로 만든 것**

| 파일 | 역할 |
|---|---|
| `mobile/assets/icon/app_icon.svg` | 아이콘 원본 한 장(OVERRIDES §8 좌표 그대로). PNG 는 전부 여기서 나온다 |
| `mobile/tool/make_app_icon.py` | SVG 의 `<rect>` 를 읽어 1024 아이콘·adaptive 전경·30px 래스터·Play 등록 자산을 그린다 (`make_placeholder_icon.py` 대체) |
| `mobile/integration_test/store_screenshot_scenes.dart` | 스크린샷 5장의 장면 정의(라이트 강제, Fake ApiClient). 시뮬레이터 캡처와 CI 위젯 테스트가 공유한다 |
| `mobile/integration_test/store_screenshots_test.dart` | 시뮬레이터에서 찍는 진입점. 찍기 전에 태블릿 rail 을 단언한다 |
| `mobile/test_driver/integration_test.dart` | `flutter drive` 드라이버 — 스크린샷 바이트를 파일로 떨어뜨린다 |
| `mobile/test/store/app_icon_test.dart` | 아이콘 계약(원본·래스터·설정) |
| `mobile/test/store/store_screenshot_scenes_test.dart` | 장면 계약(5장·내용·rail/탭바·라이트) |
| `scripts/store_screenshots.sh` | 캡처 스크립트(iOS 3종 + Android, ko/en) |
| `.github/workflows/appstore-metadata.yml` | 메타데이터·스크린샷 업로드(수동) |
| `.github/workflows/asc-submit.yml` | 가격·연령등급·개인정보 라벨·심사 노트·빌드 첨부·제출(수동) |
| `mobile/ios/fastlane/metadata/**` | iOS 스토어 텍스트 ko/en + 카테고리 + 심사 노트 |
| `mobile/android/fastlane/metadata/android/**` | Play 텍스트 ko-KR/en-US + 등록 아이콘·그래픽 + 스크린샷 |
| `mobile/ios/fastlane/screenshots/**` | App Store 스크린샷 ko/en |
| `docs/play-data-safety.md` | Play 데이터 보안 설문 답안(콘솔 입력은 사람) |
| `tests/test_store_metadata.py`, `tests/test_store_labels.py` | 메타데이터·워크플로·라벨 대조 테스트 |
| `mobile/ios/Podfile.lock` | 이 티켓이 처음으로 iOS 를 로컬 빌드하면서 생겼다. pod 버전을 고정해 두는 쪽이 CI 와 로컬이 갈리지 않아 커밋한다(`Pods/` 는 그대로 gitignore) |

**고친 것**

| 파일 | 무엇 |
|---|---|
| `mobile/pubspec.yaml` | `integration_test` dev 의존성, launcher icons/splash 를 라이트 배경·분리 전경으로 |
| `mobile/assets/icon/*.png`, `mobile/android/app/src/main/res/**`, `mobile/ios/Runner/Assets.xcassets/**` | 생성물 재생성(아이콘·스플래시·Android 12 스플래시 배경) |
| `mobile/ios/fastlane/app_privacy_details.json` | 1:1 대조에서 찾은 2건 추가(`OTHER_DATA_TYPES`, `OTHER_DIAGNOSTIC_DATA`) |
| `tests/test_app_deploy_workflow.py` | 위 2건을 34 의 `COLLECTED` 표에 반영 |
| `docs/legal-checklist.md` | "9. 스토어 라벨" 절(대조표·차이 3건) |
| `docs/RELEASE.md` | "### 35." 사람 작업·secret·체크박스 |
| `README.md` | "22." 한 줄 + "### 35." 설계 판단 |
| `.scratch/store-launch/design-system/hidden-vowels/OVERRIDES.md` | §8 에 30px 확인 결과·대비비(티켓이 명시적으로 지시) |
| `.github/workflows/flutter-ci.yml` | 포맷 검사 대상에 `integration_test test_driver` 추가 |

## 3. 체크박스별 실행 증거

### 3.1 아이콘·스플래시 (OVERRIDES §8) + 30px 확인

원본은 `mobile/assets/icon/app_icon.svg` 한 장이고, `tool/make_app_icon.py` 가 그
`<rect>` 들을 **읽어서** 그린다 — 좌표를 두 벌로 적지 않으려고 파싱한다.

```
$ python3 tool/make_app_icon.py
wrote .../assets/icon/app_icon.png, app_icon_foreground.png, .../design/icon-30px.png
wrote android/.../metadata/android/{ko-KR,en-US}/images/{icon,featureGraphic}.png

$ dart run flutter_launcher_icons
• Creating adaptive icons Android
• Updating colors.xml with color for adaptive icon background
✓ Successfully generated launcher icons

$ dart run flutter_native_splash:create
[Android] Updating styles...  [iOS] Creating dark mode images
✅ Native splash complete.
```

**red → green 을 실제로 확인했다.** 테스트를 쓴 뒤 HEAD(티켓 22 의 다크 "ㅊ"
아이콘)를 되돌려 돌려 보면 깨진다:

```
$ git show HEAD:mobile/assets/icon/app_icon.png > assets/icon/app_icon.png
$ flutter test test/store/app_icon_test.dart
  Expected: '#FAFAF9'
    Actual: '#0F172A'
00:01 +8 -1: Some tests failed.
$ python3 tool/make_app_icon.py && flutter test test/store/app_icon_test.dart
00:00 +9: All tests passed!
```

**30px 대비.** `design/icon-30px.png`(30x30)의 실제 픽셀을 테스트가 다시 잰다:

| 칸 | 색 | 배경 `#FAFAF9` 와 대비 | 판정 |
|---|---|---|---|
| 양끝(brand) | `#EA580C` | **3.41:1** | 통과(3:1 이상) |
| 가운데(원래 값) | `#D6D3D1` | **1.43:1** | **실패** — 30px 에서 배경에 녹는다 |
| 가운데(채택) | `#A8A29E` | **2.41:1** | 통과(2:1 이상, brand 보다 가볍다) |
| (후보) 더 어둡게 | `#78716C` | 4.59:1 | 쓰지 않음 — brand(3.41)보다 **무거워져** 마크의 뜻이 뒤집힌다 |

앱 안의 `tile-wrong` 토큰은 `#D6D3D1` 그대로다(보드 타일은 글자가 대비를 만든다) —
`app_icon_test.dart` 가 `AppColors.light.tileWrong` 로 그걸 못 박는다.

### 3.2 스크린샷 장면 (라이트 강제·5장·태블릿 rail)

장면 정의는 `integration_test/store_screenshot_scenes.dart` 한 곳이고,
시뮬레이터 캡처(`store_screenshots_test.dart`)와 CI 위젯 테스트
(`test/store/store_screenshot_scenes_test.dart`)가 같은 걸 쓴다. CI 가 `flutter drive`
를 못 돌리므로(시뮬레이터 필요) **장면이 깨졌는지는 위젯 테스트가 먼저 잡는다.**

```
$ flutter test test/store
00:09 +23: All tests passed!
```

- ko·en x 폰(430x932)·태블릿(1024x1366) = 4조합에서 5장이 모두 그려지고, 장면마다
  그 화면의 내용(제출 버튼 / `ResultSheet` / 리더보드 6줄 / 최근 7일·설정 / 언어 칩)이 보인다
- 태블릿 폭: 셸 4장은 `NavigationRail` 1개 + `NavigationBar` 0개, 온보딩은 rail 없음(SCREENS T0)
- 폰 폭: 셸 4장은 `NavigationBar` 1개 + rail 0개
- 기기 밝기를 dark 로 바꿔도 모든 장면의 `Theme.of(context).brightness` 가 light

같은 단언이 **캡처 직전에도** 돈다(`store_screenshots_test.dart`) — 폭 ≥600 에서
rail 이 없으면 거기서 실패해 **그 그림이 파일로 남지 않는다**(티켓의 불합격 기준).

### 3.3 메타데이터·심사 노트·워크플로

```
$ uv run pytest tests/test_store_metadata.py -q
47 passed in 0.07s
```

- iOS ko/en x (name 30 / subtitle 30 / keywords 100 / promotional 170 /
  description 4000 / release_notes) · Play ko-KR/en-US x (title 30 / short 80 /
  full 4000) 글자 수 한도 안
- 앱 이름 "오늘의 초성" / "Hidden Vowels" 가 두 스토어에서 같다(미정 4 대체명은
  `docs/RELEASE.md` "### 35." 체크박스)
- `privacy_url` = `/privacy`, `support_url` = `/terms`, 설명문에도 두 링크가 있다
- 심사 노트 3,9xx자(한도 4000) — 계정 불필요 안내·구독 Sandbox 테스트·계정 삭제
  경로(앱/웹)·외부 서비스·지역차. 자격 증명은 `<SANDBOX_TESTER_EMAIL>` 플레이스홀더뿐이고
  `demo_user.txt`·`demo_password.txt` 는 **만들지 않았다**(있으면 deliver 가 ASC 를 덮어쓴다)
- 워크플로 2개: `workflow_dispatch` 전용, `working-directory: mobile/ios`,
  `com.dosaem.chosung`, BASELINE 식별자 잔재 없음, 키 파일 `if: always()` 삭제,
  심사 연락처는 secret(`ASC_REVIEW_CONTACT_*`)이고 빈 값이면 ASC 값을 유지

### 3.4 스토어 라벨 1:1 대조 — 차이 3건

```
$ uv run pytest tests/test_store_labels.py -q
9 passed in 0.15s
```

대조표는 `docs/legal-checklist.md` "9. 스토어 라벨". 테스트가 **방침 템플릿 →
대조표 → ASC 라벨 JSON → Play 답안** 네 곳을 묶어서, 한 곳만 고치면 깨진다.

| # | 차이 | 처리 |
|---|---|---|
| 1 | 애플 refresh token 이 ASC 라벨에 없었다(34 는 "대응 범주 없음" 으로 판단) | **고침** — ASC 에 `OTHER_DATA_TYPES`(기타 데이터) 자리가 있다. `APP_FUNCTIONALITY` / `DATA_LINKED_TO_YOU` |
| 2 | 접속기록(티켓 36 이 만든 DB 감사 로그·접근 로그)이 ASC 라벨에 없었다 — 34 당시엔 없던 수집이다 | **고침** — `OTHER_DIAGNOSTIC_DATA` / `DATA_LINKED_TO_YOU`(행위자·원격 IP 가 남는다). Sentry 두 행은 그대로 `NOT_LINKED` |
| 3 | "앱 사용 이벤트"(Firebase)가 방침 `#collection` 항목 목록에 없고 `#overseas` 에만 있다 | **안 고침** — 스토어 라벨이 아니라 법적 문서 본문(개보법 §30①3)이고 ko/en 구조·테스트는 티켓 16 소관이다. 근거·영향은 체크리스트 "차이 3번", 사람 확인 항목은 `docs/RELEASE.md` "### 35." |

34 의 `tests/test_app_deploy_workflow.py` `COLLECTED` 표도 2건을 반영해 같이 고쳤다
(그 테스트가 "라벨 집합이 정확히 이것" 을 단언한다).

## 4. 설계 판단 (티켓·BASELINE 에 답이 없어 고른 것)

1. **아이콘 원본은 SVG 한 장, PNG 는 파싱해서 그린다.** 좌표를 파이썬에 다시 적으면
   둘이 갈라져도 아무도 모른다. rasterizer(cairosvg·rsvg)를 의존성에 넣지 않은 건
   도형이 사각형 네 개뿐이라서다 — 설치 없이 결과가 고정된다. PIL 은 시스템
   python3 에 있고(생성물은 커밋하므로) CI 는 이 스크립트를 돌리지 않는다.
2. **가운데 칸은 `#A8A29E` 까지만.** §3.1 표 참고 — 더 어둡게 하면 brand 보다
   무거워져 "가려진 칸" 이 주인공이 된다. 숫자는 README "35." 와 OVERRIDES §8 에.
3. **장면(scene)을 integration test 에서 분리했다.** CI(ubuntu)가 `flutter drive` 를
   못 돌리므로, 장면이 위젯 트리로 떨어져 있어야 "스크린샷이 깨졌다" 를 CI 가 잡는다.
4. **스크린샷에 배너 슬롯을 넣지 않았다.** 광고 자리는 구독자에게 사라지는 영역이고
   (OVERRIDES §5), 스토어 그림에 빈 회색 띠를 넣을 이유가 없다.
5. **결과(S2)는 앱의 "결과 보기" 버튼을 실제로 눌러서 띄운다.** 골든 테스트처럼
   시트를 직접 띄우면 앱이 만들지 않는 경로가 찍힌다. 대신 카운트다운이 실시간이라
   다시 찍으면 그 한 줄이 달라진다(의도).
6. **심사 연락처·Sandbox 계정은 레포에 없다.** BASELINE 은 이름·전화번호를
   워크플로에 박아 뒀는데 공개 레포라 secret 으로 옮겼고, **빈 secret 은 보내지
   않는다**(빈 문자열 PATCH 는 ASC 콘솔 값을 지운다). 같은 이유로
   `demo_user.txt`·`demo_password.txt` 를 만들지 않았다.
7. **Play 등록 아이콘·그래픽을 같은 SVG 에서 만들었다.** 티켓에 없지만 Play 스토어
   등록에 필수고(아이콘 512, 그래픽 1024x500) BASELINE 도 갖고 있다. 글자가 없어
   ko-KR·en-US 가 같은 파일이다.
8. **Play 태블릿 세트는 iPad 13" 캡처를 쓴다.** Play 는 규격이 폭·비율만 보고,
   태블릿 레이아웃(rail + 2열)은 같은 Flutter 코드라 그림이 같다.
9. **`capture()` 는 산출물로 성공을 판정한다.** `if ... ; then` 안에서는 bash 가
   `set -e` 를 꺼서 `flutter drive` 가 죽어도 함수가 계속 돈다 — PNG 수를 직접 세지
   않으면 "찍은 게 없는데 성공" 으로 넘어간다(§7 에서 실제로 밟았다).

## 5. 디자인 파일(DESIGN_DIR) 대비

| 항목 | DESIGN_DIR | 구현 | 차이 |
|---|---|---|---|
| 아이콘 좌표 | OVERRIDES §8 "배경 120x120, 타일 30x34 `rx=7` 을 x=12/46/80, y=43" | `app_icon.svg` 가 그 값 그대로 | 없음(테스트가 값까지 단언) |
| 아이콘 가운데 칸 | `tile-wrong` `#D6D3D1`, "대비가 낮으면 한 단계 어둡게(예 `#A8A29E`)" | `#A8A29E` | **티켓이 지시한 조정** — 근거를 OVERRIDES §8·README "35." 에 기록 |
| 스플래시 | 같은 배경 + 같은 마크, 라이트/다크 동일 | `flutter_native_splash` color·color_dark·android_12 모두 `#FAFAF9` | 없음 |
| 스크린샷 장면 | OVERRIDES §8 "라이트 모드 5장(홈/결과/리더보드/내 기록/언어 선택)" | 같은 5장, S5 제외 | 없음 |
| 태블릿 | SCREENS T0~T4(rail + 재배치) | iPad 13" 캡처가 rail + 2열 | 없음(캡처 전 단언) |

## 6. 스크린샷 스크립트 로컬 실행 결과

```
$ ./scripts/store_screenshots.sh both
===== iPhone 6.9" (ko) =====      ... All tests passed.
===== iPhone 6.5" (ko) =====      created simulator iPhone 11 Pro Max
===== iPad 13" (ko) =====         ... All tests passed.
===== Android phone (ko) =====    설치 실패 → iPhone 6.9" 캡처를 Play 폰 세트로 (§7)
===== iPhone 6.9" (en) =====      ... (같음)
===== iPhone 6.5" (en) =====
===== iPad 13" (en) =====
===== Android phone (en) =====    설치 실패 → 같은 대체
```

해상도: iPhone 6.9" 1320x2868 · iPhone 6.5" 1242x2688 · iPad 13" 2064x2752
(ASC 가 요구하는 규격 그대로). 파일 54개 — 스크린샷 50개 +
Play 등록 자산 4개:

```
mobile/android/fastlane/metadata/android/en-US/images/featureGraphic.png
mobile/android/fastlane/metadata/android/en-US/images/icon.png
mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_01_home.png
mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_02_result.png
mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_03_leaderboard.png
mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_04_records.png
mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_06_language.png
mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_01_home.png
mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_02_result.png
mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_03_leaderboard.png
mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_04_records.png
mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_06_language.png
mobile/android/fastlane/metadata/android/ko-KR/images/featureGraphic.png
mobile/android/fastlane/metadata/android/ko-KR/images/icon.png
mobile/android/fastlane/metadata/android/ko-KR/images/phoneScreenshots/iphone69_ko_01_home.png
mobile/android/fastlane/metadata/android/ko-KR/images/phoneScreenshots/iphone69_ko_02_result.png
mobile/android/fastlane/metadata/android/ko-KR/images/phoneScreenshots/iphone69_ko_03_leaderboard.png
mobile/android/fastlane/metadata/android/ko-KR/images/phoneScreenshots/iphone69_ko_04_records.png
mobile/android/fastlane/metadata/android/ko-KR/images/phoneScreenshots/iphone69_ko_06_language.png
mobile/android/fastlane/metadata/android/ko-KR/images/tenInchScreenshots/ipad13_ko_01_home.png
mobile/android/fastlane/metadata/android/ko-KR/images/tenInchScreenshots/ipad13_ko_02_result.png
mobile/android/fastlane/metadata/android/ko-KR/images/tenInchScreenshots/ipad13_ko_03_leaderboard.png
mobile/android/fastlane/metadata/android/ko-KR/images/tenInchScreenshots/ipad13_ko_04_records.png
mobile/android/fastlane/metadata/android/ko-KR/images/tenInchScreenshots/ipad13_ko_06_language.png
mobile/ios/fastlane/screenshots/en-US/ipad13_en_01_home.png
mobile/ios/fastlane/screenshots/en-US/ipad13_en_02_result.png
mobile/ios/fastlane/screenshots/en-US/ipad13_en_03_leaderboard.png
mobile/ios/fastlane/screenshots/en-US/ipad13_en_04_records.png
mobile/ios/fastlane/screenshots/en-US/ipad13_en_06_language.png
mobile/ios/fastlane/screenshots/en-US/iphone65_en_01_home.png
mobile/ios/fastlane/screenshots/en-US/iphone65_en_02_result.png
mobile/ios/fastlane/screenshots/en-US/iphone65_en_03_leaderboard.png
mobile/ios/fastlane/screenshots/en-US/iphone65_en_04_records.png
mobile/ios/fastlane/screenshots/en-US/iphone65_en_06_language.png
mobile/ios/fastlane/screenshots/en-US/iphone69_en_01_home.png
mobile/ios/fastlane/screenshots/en-US/iphone69_en_02_result.png
mobile/ios/fastlane/screenshots/en-US/iphone69_en_03_leaderboard.png
mobile/ios/fastlane/screenshots/en-US/iphone69_en_04_records.png
mobile/ios/fastlane/screenshots/en-US/iphone69_en_06_language.png
mobile/ios/fastlane/screenshots/ko/ipad13_ko_01_home.png
mobile/ios/fastlane/screenshots/ko/ipad13_ko_02_result.png
mobile/ios/fastlane/screenshots/ko/ipad13_ko_03_leaderboard.png
mobile/ios/fastlane/screenshots/ko/ipad13_ko_04_records.png
mobile/ios/fastlane/screenshots/ko/ipad13_ko_06_language.png
mobile/ios/fastlane/screenshots/ko/iphone65_ko_01_home.png
mobile/ios/fastlane/screenshots/ko/iphone65_ko_02_result.png
mobile/ios/fastlane/screenshots/ko/iphone65_ko_03_leaderboard.png
mobile/ios/fastlane/screenshots/ko/iphone65_ko_04_records.png
mobile/ios/fastlane/screenshots/ko/iphone65_ko_06_language.png
mobile/ios/fastlane/screenshots/ko/iphone69_ko_01_home.png
mobile/ios/fastlane/screenshots/ko/iphone69_ko_02_result.png
mobile/ios/fastlane/screenshots/ko/iphone69_ko_03_leaderboard.png
mobile/ios/fastlane/screenshots/ko/iphone69_ko_04_records.png
mobile/ios/fastlane/screenshots/ko/iphone69_ko_06_language.png
```

업로드 실행은 사람(D3)이다 — `docs/RELEASE.md` "### 35." 의 순서.

## 7. 실패·건너뛴 것 (숨기지 않는다)

1. **Android 에뮬레이터 캡처 실패.** AVD `Medium_Phone_API_36.1` 은 뜨고 앱도
   빌드되지만 설치가 깨진다:
   `adb: failed to install ... java.io.IOException: Requested internal only, but not enough space`
   에뮬레이터 `/data` 가 5.8G 중 5.3G 사용(329M 여유)이고 디버그 APK 는 95M 다.
   `pm trim-caches` 로는 아무것도 못 비웠고, **거기 설치된 다른 앱(사용자 것)을
   지우거나 AVD 를 wipe 하는 건 하지 않았다.** BASELINE(`Habitopia`)이 원래 하던
   대로 **iPhone 6.9" 캡처를 Play 폰 세트로** 썼다 — 우리 캡처는 Flutter 표면만
   담아서(OS 상태바가 없다) 기기 흔적이 없고 Play 는 규격이 자유롭다. 사람이
   AVD 를 비우고 `./scripts/store_screenshots.sh both` 를 다시 돌리면 네이티브
   캡처로 덮인다(`docs/RELEASE.md` "### 35." 체크박스).
   - 처음에는 `sys.boot_completed` 만 기다려서 "Can't find service: package" 로
     죽었다 — 스크립트가 **패키지 매니저 서비스**까지 기다리도록 고쳤다.
2. **en 리더보드 스크린샷에 한글 라벨이 보인다.** 서버
   (`app/services/puzzle_metrics.py` `display_name`)가 UI 언어와 무관하게
   "게스트 #a3f1" 를 주고 앱은 그 문자열을 그대로 찍는다. 앱이 실제로 만드는 화면을
   그대로 올리는 쪽(= 지금)과 보기 좋게 바꾸는 쪽 중 **코디네이터에게 물었고
   (`orca orchestration ask`, msg_362190935e4e) 답을 기다리는 중**이라, 거짓이 없는
   쪽으로 찍어 두었다. 서버 라벨을 언어 중립으로 바꾸는 건 백엔드 응답 변경이라 이
   티켓 범위 밖이다.
3. **en 번역의 복수형**: 리더보드가 "1 tries" 로 나온다(`ranking.attempts` =
   `{count} tries`). 스토어 스크린샷에 그대로 보이지만 **고치지 않았다** — 번역
   파일과 복수 처리는 티켓 27 소관이고, 여기서 고치면 그 티켓의 테스트와 겹친다.
   코디네이터에게 보고한다(MINOR).
4. **`impeccable detect` / `audit.native` 는 돌리지 않았다.** 이 티켓의 완료 조건에
   없고(웹 UI·Flutter 화면을 바꾸지 않았다), 화면 코드 변경이 0건이다.

## 8. 전체 검증 (실행 명령과 출력)

### 8.1 Flutter

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 9.4s)

$ dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 127 files (0 changed) in 0.31 seconds.

$ flutter test
00:35 +416: All tests passed!
```

416개 중 이 티켓이 더한 건 **23개**(아이콘 9 + 스크린샷 장면 14)다.

### 8.2 백엔드 (전용 자원: DB `chosung_daily_test_t35`, Redis DB 9)

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t35 \
  TEST_REDIS_URL=redis://localhost:6379/9 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t35_migrations \
  uv run pytest -q
1459 passed in 1182.49s (0:19:42)
```

1459개 중 이 티켓이 더한 건 **56개**(`tests/test_store_metadata.py` 47 +
`tests/test_store_labels.py` 9)이고, 34 의 `tests/test_app_deploy_workflow.py`
114개도 새 라벨 2건을 반영한 채로 통과한다.

### 8.3 마이그레이션

이 티켓은 마이그레이션을 만들지 않았다.

```
$ uv run flask db heads
b1c7d4e0a932 (head)
```

### 8.4 로컬 `main` 위로 rebase

```
$ git log --oneline main -1
8ddc8fd Merge 티켓 28: 앱 온보딩·권한 사전 안내

$ git rebase main
(이미 main 위에 있다 — 충돌 없음)
```

rebase 뒤 `git status` 는 깨끗하고 `git log main..HEAD` 에 이 티켓의 커밋만 있다.

## 9. 다른 티켓과 공유하는 파일

자기 번호 소제목/자기 행만 덧붙였다.

| 파일 | 더한 것 |
|---|---|
| `README.md` | "### 35." 절 하나 + "22. Flutter 앱" 끝에 아이콘 한 줄(티켓이 지정한 자리) |
| `docs/RELEASE.md` | "### 35." 절 하나 |
| `docs/legal-checklist.md` | "## 9. 스토어 라벨" 절 하나(티켓이 지시한 "스토어 라벨" 절) |
| `.scratch/store-launch/spec.md` | "미정 항목" 끝에 자기 행 하나 |
| `.scratch/store-launch/design-system/hidden-vowels/OVERRIDES.md` | §8 의 30px 확인 결과(티켓이 명시적으로 지시) |
| `.github/workflows/flutter-ci.yml` | 포맷 검사 경로 한 줄 |
| `tests/test_app_deploy_workflow.py` | 34 의 `COLLECTED` 표에 라벨 2건 |
| `.env.example` | 건드리지 않았다 — 이 티켓은 새 설정값이 없다(스토어 쪽은 GitHub secret) |
