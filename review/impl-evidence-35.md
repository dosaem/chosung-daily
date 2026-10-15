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
| `review/ocr-store-shots-35.py` | (리뷰 전 보정) en 스크린샷 OCR 검사 — 한글 글자 수와 잘못된 단수/복수를 센다. 10.4 참고 |

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
| (리뷰 전 보정) `mobile/integration_test/store_screenshot_scenes.dart` | 리더보드 fake 를 `display`(한글 하드코딩) → `anonTag` 로. 10.2 |
| (리뷰 전 보정) `mobile/test/store/store_screenshot_scenes_test.dart` | 로케일마다 "리더보드 글자는 UI 언어뿐" 단언 추가. 10.2 |
| (리뷰 전 보정) `mobile/ios/fastlane/screenshots/en-US/**`, `mobile/android/fastlane/metadata/android/en-US/images/**` | en 10장 재캡처(결과·리더보드 × 3기기 + Play 복사본). 10.3 |

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
2. ~~**en 리더보드 스크린샷에 한글 라벨이 보인다.**~~ **해소됨 — 아래 "10. 리뷰
   전 보정" 참고.** 서버(`app/services/puzzle_metrics.py` `display_name`)가 UI
   언어와 무관하게 "게스트 #a3f1" 를 줘서, 앱이 실제로 만드는 화면을 그대로 올리는
   쪽(= 당시)과 보기 좋게 바꾸는 쪽 중 **코디네이터에게 물었고**
   (`orca orchestration ask`, msg_362190935e4e) 거짓이 없는 쪽으로 찍어 두었다.
   사용자가 **"서버를 고쳐서 다시 찍는다"** 로 정해 **티켓 38**(`1172b9b`)이 응답을
   언어 중립 `anon_tag` 로 바꿨고, 이 티켓은 그 위로 rebase 해 다시 찍었다.
3. ~~**en 번역의 복수형**: 리더보드가 "1 tries" 로 나온다.~~ **해소됨 — 같은
   티켓 38 이 `ranking.attempts` 를 `one`/`other` plural 로 바꿨다**(en "1 try" /
   "2 tries"). 당시 이 티켓에서 고치지 않은 이유(번역 파일·복수 처리는 다른 티켓
   소관, 여기서 고치면 테스트가 겹친다)는 그대로 유효하고, 실제로 그 티켓이 고쳤다.
   아래 "10. 리뷰 전 보정" 에 다시 찍은 그림과 확인 기록이 있다.
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

rebase 는 no-op 이었다(main 이 움직이지 않았다) — 전체 스위트를 돌린 트리가 지금
트리와 같다. 그 뒤에 더한 건 문서 커밋뿐이라(`spec.md` 한 줄, 이 증거 문서) **문서를
읽는 테스트만** 다시 돌렸다:

```
$ uv run pytest tests/test_store_labels.py tests/test_store_metadata.py \
    tests/test_app_deploy_workflow.py tests/test_legal_checklist.py -q
304 passed in 150.84s (0:02:30)

$ uv run ruff check .
All checks passed!
```

rebase 뒤 `git status` 는 깨끗하고 `git log main..HEAD` 에 이 티켓의 커밋 6개만 있다:

```
b14a6e1 문서 35: README "설계 판단" 35. · RELEASE 사람 작업 · 구현 증거
feed263 자산 35: App Store 스크린샷 ko/en (iPhone 6.9"/6.5" · iPad 13")
7cb128d 수정 35: 스토어 라벨 1:1 대조 — ASC 라벨 2건 추가, Play 데이터 보안 답안
7f7c54d 티켓 35: 스토어 텍스트·심사 노트·스크린샷·업로드 워크플로
9a01597 티켓 35: 스토어 스크린샷 장면·드라이버·캡처 스크립트
36bad91 티켓 35: 앱 아이콘·스플래시를 OVERRIDES §8 라이트 타일 3칸으로
```

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

## 10. 리뷰 전 보정 (티켓 38 머지 후)

리뷰 전에 코디네이터가 낸 보정 작업(`fix-35-r0`). 7 의 2·3 번으로 남겨 두었던 두
MINOR 가 **티켓 38**(`1172b9b`, 로컬 `main`)에서 서버·번역 쪽으로 고쳐졌다 —
리더보드 응답이 `display` 대신 언어 중립 `anon_tag` 를 주고, 접두사("게스트 #" /
"Guest #")와 en 복수형은 앱이 자기 UI 언어로 붙인다. 사용자 결정은 **"서버를
고쳐서 다시 찍는다"** 였다.

### 10.1 rebase — 충돌 0건

```
$ git log --oneline main -1
1172b9b Merge 티켓 38: 리더보드 익명 이름 언어 중립화·en 복수형

$ git rebase main
Successfully rebased and updated refs/heads/dosaem/t35-store-assets-metadata-screenshots
```

**충돌은 없었다.** 겹치는 파일은 `README.md` 하나뿐인데 38 은 끝에 "### 38." 절을
더하고 35 는 그 앞에 "### 35." 절과 "22. Flutter 앱" 끝 한 줄을 더해서 자리가
겹치지 않는다. 자동 병합이 양쪽 뜻을 모두 살렸는지는 38 의 절을 `main` 과 직접
비교해 확인했다:

```
$ diff <(git show main:README.md  | sed -n '/^### 38\./,/^### /p') \
       <(sed -n '/^### 38\./,/^### /p' README.md)
(차이 없음)
```

`git log main..HEAD` 는 이 티켓의 커밋만 담고 있고 `main` 의 38 커밋은 조상으로
들어갔다.

### 10.2 스크린샷 fake 데이터를 `anon_tag` 로

`fakeLeaderboardEntry` 의 인자가 38 에서 `display` → `anonTag` 로 바뀌었다(서버
응답과 같은 모양). 장면 파일이 들고 있던 **하드코딩된 한글 이름 5개**를 태그 5개로
바꿨다 — 접두사는 이제 화면이 붙인다.

```dart
// 보정 전 (mobile/integration_test/store_screenshot_scenes.dart)
const _leaderboardNames = ['게스트 #a3f1', '게스트 #7b20', ...];
fakeLeaderboardEntry(rank: 1, display: _leaderboardNames[0]),

// 보정 후
const _leaderboardTags = ['a3f1', '7b20', '1c08', '92de', '4f61'];
fakeLeaderboardEntry(rank: 1, anonTag: _leaderboardTags[0]),
```

같은 파일의 주석("지금 서버는 UI 언어와 무관하게 '게스트 #a3f1' 를 주므로 en
스크린샷도 같은 라벨로 찍는다")도 더는 사실이 아니라 38 의 규칙으로 고쳐 썼다.

**다른 언어 글자가 섞이면 스토어 반송 사유라서, 찍기 전에 잡는 테스트를 더했다.**
`test/store/store_screenshot_scenes_test.dart` 에 로케일마다 한 개
(`$language — 리더보드 장면의 글자는 UI 언어뿐이다`): 리더보드 장면을 띄워 **그려진
`Text` 위젯의 문자열을 전부 모아** ① 1위 줄이 그 로케일의 `ranking.guest` + 태그
`a3f1` 인지 ② 1회 시도 줄이 `ranking.attempts.plural(1)` 인지(en "1 try") ③ 반대
언어의 글자(en 화면의 "게스트", ko 화면의 "Guest")가 0건인지 ④ en 에 "1 tries" 가
없는지를 단언한다. 그림이 아니라 **실제 위젯 문자열**을 읽으므로 OCR 보다 정확하고
CI(시뮬레이터 없음)에서 돈다.

### 10.3 다시 찍은 파일 — en 10개, ko 0개

`./scripts/store_screenshots.sh en` (기존 스크립트·기기 세트 그대로). 10개가 바뀌었다:

```
 M mobile/ios/fastlane/screenshots/en-US/iphone69_en_02_result.png
 M mobile/ios/fastlane/screenshots/en-US/iphone69_en_03_leaderboard.png
 M mobile/ios/fastlane/screenshots/en-US/iphone65_en_02_result.png
 M mobile/ios/fastlane/screenshots/en-US/iphone65_en_03_leaderboard.png
 M mobile/ios/fastlane/screenshots/en-US/ipad13_en_02_result.png
 M mobile/ios/fastlane/screenshots/en-US/ipad13_en_03_leaderboard.png
 M mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_02_result.png
 M mobile/android/fastlane/metadata/android/en-US/images/phoneScreenshots/iphone69_en_03_leaderboard.png
 M mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_02_result.png
 M mobile/android/fastlane/metadata/android/en-US/images/tenInchScreenshots/ipad13_en_03_leaderboard.png
```

Play 쪽 4개는 iOS 캡처를 그대로 복사한 것이고(스크립트가 하는 일), 해시가 원본과
같은지 확인했다 — 4개 모두 일치. 해상도도 규격대로다: 6.9" 1320×2868, 6.5"
1242×2688, iPad 13" 2064×2752.

**en 5장 중 3장은 다시 찍었는데도 바이트가 그대로였다**(`01_home`, `04_records`,
`06_language`). 이게 두 가지를 동시에 말해 준다:

1. **캡처가 결정적이다.** 같은 장면을 다시 찍으면 같은 바이트가 나온다 — 가짜
   응답뿐이고 상태바도 고정이라서. 그러니 "바뀐 파일 = 실제로 글자가 바뀐 화면"
   으로 읽어도 된다.
2. **실제로 바뀐 글자는 리더보드뿐이다.** `02_result` 가 같이 바뀐 건 글자가 아니라
   **결과 시트의 다음 퍼즐 카운트다운**(`result.countdown`)이 찍는 순간의 시각을
   보여주기 때문이다 — 찍을 때마다 달라지는 값이라 내용 변화가 아니다.
   `result.stats_row` 도 38 에서 plural 로 바뀌었지만 그건 `Semantics` 라벨이라
   그림에 안 보인다.

**ko 는 한 장도 다시 찍지 않았다 — 글자가 하나도 안 바뀌어서다.** 38 의 ko 번역은
`other` 한 형태뿐이라 보정 전후 문자열이 같다. 보정 전 하드코딩 값과 보정 후
`ko.json` 이 푸는 값을 직접 맞춰 봤다:

| | 보정 전 | 보정 후(ko) | 같은가 |
|---|---|---|---|
| 리더보드 이름 5개 | `게스트 #a3f1` … `게스트 #4f61` | `ranking.guest` + 태그 → `게스트 #a3f1` … `게스트 #4f61` | **같다** |
| 시도 라벨(1회) | `{count}회` → `1회` | `ranking.attempts.other` `{count}회` → `1회` | **같다** |
| 연속/누적 | `{count}일` · `{count}문제` | `streak.days.other` · `streak.puzzles.other` (동일 문자열) | **같다** |

같은 비교에서 en 만 `게스트 #a3f1` → `Guest #a3f1` 로 갈린다. 위 1 번(캡처가
결정적)과 합치면 **ko 를 다시 찍어도 같은 바이트가 나온다**는 뜻이라, 바뀌지 않은
그림을 커밋에 섞지 않으려고 돌리지 않았다. `git status` 에 ko 파일이 0건인 것으로
확인된다.

### 10.4 "en 에 한글이 없다" 직접 확인

세 겹으로 확인했다.

**(1) 위젯 문자열 단언** — 10.2 의 새 테스트. en 리더보드 장면의 `Text` 중
"게스트" 를 담은 것 0건, "1 tries" 0건, 1위 줄 = `Guest #a3f1`, 1회 줄 = `1 try`.

**(2) 그림 OCR** — 찍힌 PNG 를 `tesseract --psm 6` 으로 읽어 한글 코드포인트
(`가-힣`, `ㄱ-ㆎ`)와 잘못된 복수형을 셌다. 검사 스크립트는
`review/ocr-store-shots-35.py`.

```
$ python3 -I review/ocr-store-shots-35.py mobile/ios/fastlane/screenshots/en-US 'iphone69_en_*.png'
--- iphone69_en_01_home.png
    수량 문구: ['12 days', '5 tries']
    한글 0자 · 잘못된 단수/복수 없음
--- iphone69_en_02_result.png
    수량 문구: 없음
    한글 0자 · 잘못된 단수/복수 없음
--- iphone69_en_03_leaderboard.png
    1 Guest #a3f1 1try 00:00:41
    2 Guest #7620 1try 00:01:03
    3 Guest #1c08 2tries 00:01:35
    4 Guest #92de 3tries 00:03:08
    5 Guest #4f61 3tries 00:06:42
    수량 문구: ['4 tries']
    한글 0자 · 잘못된 단수/복수 없음
--- iphone69_en_04_records.png
    수량 문구: ['12 days', '30 days', '41 puzzles', '7 days']
    한글 0자 · 잘못된 단수/복수 없음
--- iphone69_en_06_language.png
    수량 문구: 없음
    한글 0자 · 잘못된 단수/복수 없음

== 한글 + 잘못된 복수형 합계: 0 ==
```

6.5" 와 iPad 13" 의 리더보드도 같은 다섯 줄(`Guest #a3f1` … `Guest #4f61`),
한글 0자, 잘못된 복수형 0건이다.

OCR 에 걸린 두 가지를 짚어 둔다. `#7b20` 이 `#7620` 으로 읽히는 건 `b`/`6` 글리프
혼동이고(위 (1) 의 위젯 단언이 정확한 문자열을 본다), 처음 짠 검사기가
`04_records` 를 "1 puzzles" 로 잡은 건 **"41 puzzles" 의 꼬리**를 부분문자열로
문 것이었다 — 앞에 숫자가 없을 때만 세도록 고쳤다(실제 화면은
`12 days / 30 days / 41 puzzles` 로 전부 맞다). tesseract 에 한국어 traineddata 가
없어서 OCR 은 **한글을 읽지 못하고 깨진 라틴 문자로 떨군다** — 그래서 OCR 은 "한글이
없다" 의 보조 근거이고, 주 근거는 (1) 의 위젯 단언이다.

**(3) 눈으로 보기** — `iphone69_en_03_leaderboard.png` 를 직접 열어 봤다:
`My rank #23 · 4 tries · 00:12:34` 카드 아래로 `Guest #a3f1` `1 try` /
`Guest #7b20` `1 try` / `Guest #1c08` `2 tries` / `Guest #92de` `3 tries` /
`Guest #4f61` `3 tries`, 맨 아래 고정된 내 줄이 `23 You 4 tries 00:12:34`.
한글은 한 글자도 없다.

### 10.5 Android 네이티브 캡처 — 이번에도 실패(폴백)

7 의 1 번과 같은 결론이지만 **실패 신호가 달라졌다.** 지난번은 설치할 공간이
없다는 오류였고(`Requested internal only, but not enough space`), 이번엔 이미 떠
있던 에뮬레이터(`emulator-5554`, `adb devices` 에 `device` 상태)가 **시스템 서비스를
잃은 상태**였다:

```
cmd: Failure calling service activity: Broken pipe (32)
adb: failed to install .../app-debug.apk: cmd: Can't find service: package
Application failed to start on attempt: 1..3
Android 캡처 실패/건너뜀 — iPhone 6.9" 캡처를 Play 폰 세트로 쓴다
```

스크립트의 `android_device()` 는 `adb devices` 에 에뮬레이터가 **이미 보이면** 부팅
대기(`sys.boot_completed` + `service check package`)를 건너뛰고 그 시리얼을 바로
돌려준다. 그래서 반쯤 죽은 에뮬레이터를 그대로 썼다. **고치지 않았다** — 이번
원인은 부팅이 덜 끝난 게 아니라 시스템 서버가 죽어 있는 것이라, 대기 루프를 넣어도
영원히 기다릴 뿐 캡처가 되지는 않는다. 즉 검증할 수 없는 수정이 된다. 남은 AVD 를
비우거나 거기 설치된 **사용자의 다른 앱을 지우는 일은 하지 않았다**(7 의 1 번과 같은
선). 폴백은 설계대로 동작했고 Play 폰 세트는 iPhone 6.9" 캡처(= 같은 Flutter 표면,
OS 상태바 없음)로 채워졌다. 사람이 AVD 를 비우고 다시 돌리면 네이티브 캡처로
덮인다(`docs/RELEASE.md` "### 35." 체크박스). **MINOR 로 코디네이터에게 보고한다.**

### 10.6 범위 밖 변경을 되돌린 것

iOS 빌드가 `pod install` 을 돌리면서 `mobile/ios/Runner.xcodeproj/project.pbxproj`
와 `Runner.xcworkspace/contents.xcworkspacedata` 에 CocoaPods 통합(Pods 그룹·
xcconfig·Embed Pods Frameworks 단계)을 써 넣었다. 이 티켓이 뜻한 변경이 아니고
`main`/HEAD 에도 통합이 안 들어가 있어서 **되돌렸다**(`git checkout --`). 빌드할 때
다시 생성되는 파일이라 되돌려도 캡처·빌드에 지장이 없다(되돌린 뒤
`flutter build apk --debug` 가 exit 0).

### 10.7 보정 후 전체 검증

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 7.8s)

$ dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 127 files (0 changed) in 0.59 seconds.

$ flutter test
00:53 +428: All tests passed!

$ flutter build apk --debug ; echo $?
✓ Built build/app/outputs/flutter-apk/app-debug.apk
0
```

`flutter test` 는 보정 전 416 → **428**이다: 38 이 더한 10개와 이 보정이 더한
**2개**(로케일당 리더보드 라벨 1개)가 들어왔다. `mobile/build` 는 확인 뒤 지웠다.

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t35 \
  TEST_REDIS_URL=redis://localhost:6379/7 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t35_migrations \
  uv run pytest -q
1468 passed in 1589.30s (0:26:29)
```

8.2 의 1459 → **1468**이다. 늘어난 9개는 38 이 더한 것
(`tests/test_ui_strings.py` · `tests/test_web_js.py` · `tests/test_leaderboard.py`)이고
**이 보정은 백엔드 테스트를 더하거나 고치지 않았다**. Redis 는 코디네이터가 지정한
**DB 7** 을 썼다(8.2 의 첫 실행은 DB 9 였다 — 둘 다 이 티켓 전용이고 다른
워크트리와 겹치지 않는다). 같은 시간대에 다른 워크트리(t29·t30·t31·main)의 pytest 가
돌고 있었지만 **DB·Redis 가 티켓별로 갈라져 있어** 서로 건드리지 않는다. 이
worktree 에서 돈 pytest 는 이 하나뿐이다(실행 전 `ps` 로 확인).


### 10.8 이 스크린샷의 기준점 — 29~33 머지 후 최종 재촬영 예정

**여기 커밋된 스크린샷은 로컬 `main` 이 `1172b9b`(티켓 38 머지)일 때 찍은 것이다.**
이 보정을 도는 동안 `main` 이 `b11f011`(티켓 30 머지)로 움직였고, 30 은
`mobile/lib/screens/records_tab.dart` 를 254줄 고쳤다 — 알림 시각 picker·리마인더
스위치·권한 꺼짐 안내가 설정 영역에 들어오는데, 그 영역이 **S4 "내 기록"
스크린샷에 보인다.**

**그래도 지금 다시 찍지 않는다(코디네이터 결정 2026-10-15).** S4 를 바꾸는 앱
티켓이 30 말고도 **29(계정 카드)·31(광고 배너)·32(구독 페이월)·33** 이 남아 있어서
지금 찍어도 또 찍어야 한다. 코디네이터가 **앱 티켓이 전부 머지된 뒤 "최종 스크린샷
재촬영" 작업을 따로** 낸다. 이 티켓이 남기는 것은 **장면 정의·캡처 스크립트·검사
방법**이고, 그 셋은 티켓이 늘어나도 그대로 쓰인다(장면이 코드라서 화면이 바뀌면
`flutter test` 가 먼저 깨진다 — README "### 35." 의 설계 의도 그대로다).

그래서 이 브랜치는 **`1172b9b` 위로 rebase 된 상태로 리뷰에 들어간다.** 그 트리에서
전체 검증을 통과했고(10.7), 지금 `main` 으로 다시 rebase 하는 일은 최종 재촬영
작업이 함께 한다.

### 10.9 남는 MINOR (고치지 않고 적어 둔다)

1. **Android 네이티브 캡처 폴백** — 10.5. 사람이 AVD 를 비우고 다시 돌리는 항목이
   이미 `docs/RELEASE.md` "### 35." 에 있다.
2. **`spec.md` 가 아직 옛 필드를 적고 있다.** `.scratch/store-launch/spec.md` 의
   API 표 아래 줄이 그대로다:
   > 리더보드 `display` = `"게스트 #" + guest.id 16진 4자리`.
   38 이 응답을 `anon_tag` 로 바꾸면서 이 줄을 안 고쳤다. **스펙은 38 소관이고 이
   티켓이 건드릴 자리가 아니라 고치지 않았다** — 코디네이터에게 보고한다.

## 수정 라운드 1

최종 리뷰 라운드 1(`review/impl-review-35.md`, 대상 HEAD `f243b61`)의 MAJOR 7건을
고쳤다. BLOCKER·MINOR·REPEAT 는 없었다. 리뷰 파일은 고치지 않았다.

**코디네이터 범위 메모(2026-10-15)를 따랐다:**

1. **이 라운드는 rebase 하지 않았다** — 베이스는 `1172b9b` 그대로다(스크린샷
   재촬영이 앱 티켓 머지 후 별도 작업이라서). 그래서 과제 지시의 `git rebase main`
   은 **의도적으로 건너뛴다**.
2. **법적 문서(개인정보처리방침) 본문은 건드리지 않았다.** D-35-4 를 고치면서
   방침에 더할 항목이 생겨서 `docs/RELEASE.md` "### 35." 에 "방침에 추가 필요:
   광고 요청 정보(대략적 위치)" 사람 확인 항목으로 남겼다(아래 D-35-4).
3. **Play 세트가 iPhone 복사본으로 나가지 않게 검사로 막았다**(아래 D-35-5).

### 리뷰 전에 없던 것 — 워크플로·스크립트를 "돌려 보는" 테스트

리뷰가 지적한 공백(`워크플로 실패 경로는 실행하지 않는다`)이 D-35-1~3·7 의 공통
원인이다. 그래서 재현 테스트를 **글자 검사가 아니라 실행**으로 만들었다.

- `tests/test_asc_submit_workflow.py` — `asc-submit.yml` 의 `python3 - <<'PYEOF'`
  블록을 **YAML 에서 꺼내 `exec`** 한다(사본을 두지 않는다 — 사본은 워크플로가
  바뀌면 낡는다). 바깥으로 나가는 지점은 `urllib.request.urlopen` 하나라서 그
  자리만 메모리 대역(`FakeAsc`: ASC + iris 라우팅, 호출 순서·상태 기록)으로 막으면
  실제 호출 없이 전체 흐름이 돈다. JWT 서명은 테스트가 그 자리에서 만드는 EC P-256
  키로 진짜 `openssl` 을 쓴다(네트워크·계정·실제 키 없음).
- `tests/test_store_screenshot_script.py` — `scripts/store_screenshots.sh` 를
  `STORE_SHOTS_LIB_ONLY=1` 로 **source** 해 판정 함수만 가져오고 `flutter` 를 shell
  함수로 덮어 "몇 장을 만들고 어떤 코드로 끝났는지" 를 테스트가 정한다. 스크립트
  하단에 lib-only 가드를 넣은 것이 이 때문이다(시뮬레이터·에뮬레이터가 필요한 메인
  흐름은 돌지 않는다).

### D-35-1 — 한 장만 찍고 실패해도 캡처 성공 처리

- **원인**: `capture()` 가 `flutter drive` 의 종료 코드를 `|| true` 로 버리고,
  산출물도 "0장인지" 만 봤다. 업로드 쪽 `appstore-metadata.yml` 도 폴더 전체 PNG 가
  0장인지만 세서 반쪽 세트를 막지 못했다.
- **수정**: `capture()` 가 종료 코드를 받아(`|| drive_exit=$?`) **코드와 장 수(5)를
  둘 다** 본다. 하나라도 어긋나면 사유를 찍고 실패를 돌려주며 **기존 세트를
  건드리지 않는다**. 기대 장수는 `EXPECTED_SHOTS`(기본 5)이고
  `tests/test_store_screenshot_script.py` 가 `StoreScene` 장면 수와 갈리지 않는지
  본다. 업로드 쪽은 `mobile/tool/verify_store_screenshots.py` 로 바꿨다 —
  로케일×기기마다 5장을 센다(6.5" 는 선택이라 0 또는 5).
- **증명**: 재현(옛 검사)과 수정 후.

```
# 옛 업로드 검사: 1장만 있어도 통과했다
$ cd <tmp> && bash -c 'count=$(find fastlane/screenshots -name "*.png" | wc -l | tr -d " ")
  echo "screenshots: $count"; [ "$count" -eq 0 ] && exit 1'
screenshots: 1
old check exit=0

$ uv run pytest -q tests/test_store_screenshot_script.py
12 passed in 0.43s
```

`test_capture_fails_when_the_drive_run_did_not_produce_the_whole_set[1]` 은 lib-only
가드를 넣은 직후(판정 수정 전) **실패**했다 — `capture_exit=0` 으로 1장을 결과
폴더로 옮겼다. 수정 후 통과한다.

### D-35-2 — 개인정보 라벨 삭제 후 실패를 삼켜 부분 상태로 제출 진행

- **원인**: `try` 하나가 **인증 확인(GET)과 되돌릴 수 없는 쓰기(DELETE/POST)를 같이**
  감쌌다. 그래서 삭제 뒤의 실패도 "iris auth 미지원 — ASC UI 값 유지" 로 찍고
  넘어가, `dry_run=false` 면 **비었거나 반쪽인 신고 상태로 심사 제출까지** 갔다.
- **수정**: 두 단계로 갈랐다. GET 이 실패하면(팀 키 401) 아무것도 지우지 않고
  `SKIPPED` 로 넘어간다. GET 이 됐으면 거기서부터는 복구가 불가능하므로(지운 라벨의
  id 는 돌아오지 않는다) 실패를 삼키지 않고 `::error::` 로 상태를 알리고 **다시
  raise 해 스텝을 실패시킨다** — 빌드 첨부·제출로 넘어가지 않는다. `docs/RELEASE.md`
  "### 35." 의 라벨 체크박스에 두 로그의 뜻을 적었다.
- **증명**: 재현 테스트가 수정 전 `DID NOT RAISE HTTPError` 로 실패했다(예외를 삼키고
  제출까지 진행). 수정 후:

```
$ uv run pytest -q tests/test_asc_submit_workflow.py -k privacy
3 passed, 7 deselected
```

`test_a_write_failure_after_the_delete_fails_the_step_instead_of_submitting` 이
`fake.submitted is False` · `fake.attached_build is None` · 로그에 `SKIPPED` 없음을
단언한다. `test_privacy_labels_are_left_alone_when_iris_rejects_the_team_key` 는
401 때 `DELETE` 호출이 **아예 없음**을 단언한다.

### D-35-3 — 입력한 app_version 과 다른 버전에 빌드/심사정보를 붙임

- **원인**: ① 워크플로가 `APP_VERSION` 을 deliver 스텝에만 주고 Python 스텝에는
  주지 않았다. ② 버전 선택이 상태 필터 + `limit=1` 이라 목록 앞의 반려된 구버전을
  집었고, fallback 은 상태 조건조차 없었다.
- **수정**: 스텝 `env` 에 `APP_VERSION` 을 넣고(비면 `assert` 로 멈춘다),
  `filter[versionString]={APP_VERSION}` + 편집 가능 상태로 질의한 뒤 **클라이언트에서
  다시 `versionString` 을 대조**한다(서버가 필터를 흘려도 엉뚱한 버전으로 가지
  않게). 없으면 fallback 없이 `assert` 로 멈춘다. `docs/RELEASE.md` 의 업로드 순서에
  `-f app_version=1.0.0` 을 두 명령에 같이 적었다.
- **증명**: 리뷰의 재현(`0.9.0 / REJECTED` 가 첫 행)으로 수정 전 `selected=0.9.0`
  이었고, 수정 후:

```
$ uv run pytest -q tests/test_asc_submit_workflow.py -k version
2 passed, 8 deselected in 0.08s
```

`test_the_step_works_on_the_version_the_dispatch_asked_for` 는 `V-NEW` 를 골랐고
구버전 id(`V-OLD`)가 **어떤 호출 URL 에도 없음**을 단언한다.
`test_the_step_stops_when_the_asked_version_does_not_exist` 는 멈추고 빌드 첨부·제출을
하지 않음을 단언한다. 정상 경로도 막히지 않는지 끝까지 돌려 본다 —
`test_the_whole_step_still_submits_the_asked_version`(`dry_run=false`,
`build_number=42` → `attached_build=B42`, `SUBMITTED FOR REVIEW`).

### D-35-4 — AdMob SDK 의 대략적 위치 수집을 Data safety 에서 제외

- **원인**: "SDK 가 직접 받고 우리가 수집하지 않는다" 를 신고 제외 근거로 썼다.
  자체 서버 저장 여부·위치 권한 유무는 근거가 아니다 — SDK 가 기기 밖으로 보내면
  수집이고 받는 자가 있으면 공유다. 방침 `#overseas` 의 AdMob 행은 **그때도**
  "광고 요청 정보(대략적 위치·기기 종류 등 SDK 가 수집하는 값)" 를 이전 항목으로
  적고 있었다(ko `privacy.ko.html:182`, en `privacy.en.html:198`) — 즉 방침과 스토어
  신고가 어긋난 상태였다. 기존 테스트는 표끼리의 범주 일치만 봐서 못 잡았다.
- **수정**(세 곳을 같이):
  - `docs/play-data-safety.md` §2 에 `위치 > 대략적인 위치`(수집 예 · 공유 예
    Google AdMob · 필수 · 광고 또는 마케팅) 행을 넣고, "이 표에 없는 것" 의
    `정확한 위치 / 대략적인 위치` 행을 **`정확한 위치` 만**으로 좁혔다(공식 근거 링크
    2건 포함).
  - `mobile/ios/fastlane/app_privacy_details.json` 에 `COARSE_LOCATION` /
    `THIRD_PARTY_ADVERTISING` / `NOT_LINKED` + `USED_TO_TRACK` 를 더했다(광고 ID 두
    행과 같은 축).
  - `docs/legal-checklist.md` "스토어 라벨" 대조표에 행을 더하고, "대조에서 찾은
    차이" 에 왜 틀렸는지·무엇으로 고쳤는지를 적었다.
  - 티켓 34 의 `tests/test_app_deploy_workflow.py` 도 같이 고쳤다 — `COLLECTED` 표가
    ASC 범주를 1:1 로 열거하고(`test_privacy_details_lists_exactly_what_the_app_collects`)
    광고 범주의 추적 신고를 지키므로(`test_advertising_identifiers_are_declared_as_tracking`),
    새 범주를 그 두 곳에 넣지 않으면 "신고하지 않은 수집" 쪽으로 깨진다. 34 가
    더한 다른 단언은 건드리지 않았다.
- **법적 문서는 고치지 않았다**(코디네이터 메모 2). 방침 3절 "수집하는 정보" 의 항목
  목록에는 이 항목이 없다 — Firebase "앱 사용 이벤트" 와 같은 성격이라
  `docs/RELEASE.md` "### 35." 에 **"방침에 추가 필요: 광고 요청 정보(대략적 위치)"**
  사람 확인 항목으로 남겼다.
- **증명**: 새 테스트 2개가 수정 전 실패했다(`대략적인 위치를 아직 제외하고 있다`,
  `KeyError: 'COARSE_LOCATION'`). 수정 후:

```
$ uv run pytest -q tests/test_store_labels.py
12 passed in 0.02s

$ uv run pytest -q tests/test_legal_checklist.py
134 passed in 143.36s (0:02:23)
```

### D-35-5 — Android 캡처까지 iOS 온보딩을 강제해 실제 Android 와 다름

- **원인 둘**: ① 장면 루트가 `isIosProvider.overrideWithValue(true)` 로 플랫폼을
  박아, Android 에뮬레이터에서 찍어도 iPhone 구성(ATT 안내 1장 추가 = 4장)이 나왔다.
  ② 에뮬레이터가 없으면 iOS 세트를 **그대로 복사**해 Play 폰 세트로 썼다 — 그림이
  실제 Android 와 다르다.
- **수정**:
  - `storeScreenshotScenes({required Locale locale, required bool isIos})` 로
    바꿨다. 캡처는 `Platform.isIOS` 를 넘긴다.
  - 대체 경로는 복사를 버리고 **iPhone 시뮬레이터에서 Android 구성으로 찍는다**
    (`--dart-define=SHOT_IS_IOS=false`, 세트 prefix `androidui`). Play 는 규격이
    자유롭고 우리 캡처에는 OS 상태바가 없다.
  - 그래도 과거 복사본이 올라가지 않게 **올리기 전 검사**를 넣었다(코디네이터 메모
    3): `mobile/tool/verify_store_screenshots.py` 가 Play 폰 세트에 **iOS 온보딩
    캡처와 바이트까지 같은 파일**이 있으면 실패시킨다. `android/fastlane/Fastfile`
    의 `release` lane 이 `upload_to_play_store` **전에** 이 스크립트를 돌린다.
  - **왜 온보딩 장만 비교하나.** 처음에는 Play 폰 세트의 아무 파일이든 iPhone 세트와
    바이트가 같으면 실패시켰는데, 그러면 위의 정상 대체 경로가 막힌다 — 플랫폼으로
    갈리는 장면은 온보딩 하나고, 나머지 네 장(홈·결과·순위·내 기록)은 두 플랫폼이
    같은 그림이라 **같은 바이트인 것이 정상**이다. 그래서 판정 대상을
    `PLATFORM_DIVERGENT_SCENE`(`06_language`) 로 좁혔다. 전체 복사(지금 레포 상태)는
    온보딩 장도 같이 복사되므로 그대로 걸린다. 양쪽 방향을 테스트로 못 박았다 —
    `test_the_verifier_refuses_a_play_phone_set_copied_from_the_iphone_captures`,
    `test_the_verifier_allows_the_fallback_set_shot_in_the_android_layout`.
  - 태블릿 세트는 반대로 iPad 캡처 재사용이 맞아서(같은 코드·같은 그림, Play 는
    폭·비율만 본다) 통과시킨다
    (`test_the_verifier_allows_the_tablet_set_to_reuse_the_ipad_captures`).
- **지금 상태를 숨기지 않는다**: 레포에 커밋된 Play 폰 10장은 **여전히 iPhone 캡처의
  바이트 복사본**이다(에뮬레이터 없이 돌린 결과). 그래서 지금 `fastlane release` 를
  돌리면 **업로드 전에 실패한다** — 의도한 동작이다. 29~33 머지 후 최종 재촬영에서
  AVD(또는 `androidui` 대체 세트)로 바꾼다. `docs/RELEASE.md` "### 35." 의 Play 폰
  체크박스에 그대로 적었다.

```
$ cd mobile && python3 tool/verify_store_screenshots.py ios
screenshots OK: ios — 로케일마다 5 장씩
ios exit=0

$ cd mobile && python3 tool/verify_store_screenshots.py play
::error::.../ko-KR/images/phoneScreenshots/iphone69_ko_06_language.png: iOS 온보딩 캡처(iphone69_ko_06_language.png)와 바이트까지 같다 — Play 는 실제 앱 경험을 요구하는데 ...
::error::.../en-US/images/phoneScreenshots/iphone69_en_06_language.png: (같은 사유)
스크린샷 세트 2건이 올릴 수 없는 상태다 (docs/RELEASE.md '35.')
play exit=1
```

플랫폼 판정 쪽 재현: 수정 전 상태(`overrideWithValue(true)`)로 되돌려 새 테스트를
돌리면 **실패**한다.

```
$ flutter test test/store --plain-name "Android — 온보딩 장 수가 그 플랫폼과 같다"
Android 에 없는 장이 그려졌다 — 3장이어야 한다
00:02 +0 -2: Some tests failed.
```

수정 후 `flutter test test/store` 는 **29 passed**(리뷰 때 25 + 플랫폼 테스트 4).

### D-35-6 — Android 정상 재촬영 시 폰 세트가 10장으로 누적

- **원인**: `capture()` 가 결과 폴더를 그대로 두고 새 파일만 옮겼다. prefix 가 다르면
  (`iphone69_*` ↔ `android_*`) 덮이지 않아 두 세트가 같이 남는다 — Play 기기
  유형별 상한 8장을 넘는다.
- **수정**: `replace_set <dir> <glob>` 을 넣고, 캡처 성공 시 **그 세트가 소유한
  파일만** 지운 뒤 새로 넣는다. 소유 glob 은 5번째 인자이고, iOS deliver 폴더는 기기
  3종이 prefix 로 같이 사니 기본값 `${prefix}_*.png`, Play 폴더는 기기 유형 하나라
  `'*.png'` 를 넘겨 폴더째 바꾼다. Play 태블릿 복사와 대체 폰 세트도 같은 규칙을
  쓴다. 검사 쪽(`verify_store_screenshots.py`)도 "5장" 과 Play 상한 8장을 센다.
- **증명**: 재현 테스트가 수정 전 10장(`iphone69_* + android_*`)으로 실패했다. 수정 후
  `test_capture_replaces_the_previous_phone_set_instead_of_piling_up` 과
  `test_the_android_fallback_replaces_the_phone_set_too` 가 통과하고,
  `test_capture_keeps_the_other_device_sets_in_the_shared_ios_folder` 가 반대 방향
  (iOS 폴더의 iPad 세트는 남아야 한다)을 지킨다.

### D-35-7 — 사람이 콘솔에 채운 Sandbox 심사 노트를 제출 때 플레이스홀더로 덮음

- **원인 둘**: ① Python 스텝이 기존 `notes` 를 읽지도 않고 매번 레포 노트로 PATCH
  했다. ② `fastlane deliver` 도 `review_information/notes.txt` 를 보면 심사 상세를
  **자기가** PATCH 한다(fastlane 2.232.2 `deliver/lib/deliver/upload_metadata.rb`
  의 `REVIEW_INFORMATION_VALUES` / `review_information(version)` — 폴더에 예약 이름이
  있으면 값을 담아 `update` 한다). 즉 노트 한 칸에 쓰는 쪽이 셋(레포·deliver·사람)
  이었다.
- **수정**: 소유권을 **순서로** 갈랐다.
  - 레포 파일은 **첫 채움**이다. Python 스텝이 콘솔 노트를 먼저 읽고,
    플레이스홀더(`<SANDBOX_TESTER_EMAIL>`·`<SANDBOX_TESTER_PASSWORD>`)가 남아 있거나
    비었을 때만 레포 노트를 올린다. 사람이 채운 뒤에는 `notes` 를 아예 보내지 않고
    `review notes: ASC 콘솔 값 유지` 를 찍는다.
  - deliver 가 끼어들지 못하게 정본 파일 이름을
    `review_information/notes.template.txt` 로 바꿨다(`git mv`). deliver 는 그 폴더의
    **예약 이름만** 읽으므로 이제 심사 상세를 건드리지 않는다(남은 파일
    `demo_required.txt` 는 fastlane 의 인식 목록에 없다 → `app_review_information`
    이 비어 `review_information()` 이 바로 return 한다).
  - `docs/RELEASE.md` "### 35." 에 순서(dry run → 콘솔 입력 → 진짜 제출)와 "콘솔
    노트를 처음부터 다시 받고 싶으면 그 칸을 비우고 다시 돌린다" 를 적었다.
- **증명**: 수정 전 `manual_note_preserved=False` / `placeholder_written=True`.
  수정 후:

```
$ uv run pytest -q tests/test_asc_submit_workflow.py -k notes
5 passed, 5 deselected
```

`test_the_step_does_not_overwrite_review_notes_a_human_filled_in` 이 콘솔 값이 그대로
남는 것을, `test_the_step_fills_empty_or_placeholder_review_notes_from_the_repo` 가
반대 방향(빈 값·플레이스홀더면 올린다)을, `test_fastlane_deliver_cannot_touch_the_review_notes`
가 `review_information/` 에 deliver 예약 이름이 없다는 것을 지킨다.

### 리뷰어 지적이 틀렸다고 본 것

없다. MAJOR 7건 모두 재현되어 전부 고쳤다.

### 미수정 MINOR

리뷰 라운드 1 은 MINOR 0건이었다. 10.9 에 적어 둔 두 건(Android 네이티브 캡처 폴백 ·
`spec.md` 의 옛 `display` 필드)은 그대로 남는다 — 첫 건은 이번 수정으로 **검사가
막는 상태**가 됐고(D-35-5), 둘째는 38 소관이라 이 티켓이 건드리지 않는다.

### 수정 라운드 1 — 전체 재실행

```
$ uv run ruff check .
All checks passed!

$ cd mobile && flutter analyze
No issues found!

$ cd mobile && flutter test
All tests passed!   # 432 (리뷰 때 428 + 플랫폼 테스트 4)

$ TEST_DATABASE_URL=...chosung_daily_test_t35 \
  TEST_REDIS_URL=redis://localhost:6379/9 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t35_migrations \
  uv run pytest -q
1504 passed in 1167.41s (0:19:27)

$ uv run flask db heads
b1c7d4e0a932 (head)

$ git diff --check
(출력 없음)
```

리뷰 때 1468 → **1504**다. 늘어난 36개가 이번 라운드의 재현 테스트다
(`tests/test_asc_submit_workflow.py` 11 + `tests/test_store_screenshot_script.py` 12 +
`tests/test_store_metadata.py` 에 더한 13). 전용 자원만 썼다 — DB
`chosung_daily_test_t35`, Redis **DB 9**, 마이그레이션 DB
`chosung_daily_test_t35_migrations`. 공용 테스트 DB 는 건드리지 않았고 새 DB 도 만들지
않았다. 실행 전 `ps` 로 이 worktree 의 고아 pytest 가 없는 것을 확인했다(다른
worktree 의 pytest 는 돌고 있었지만 DB·Redis 가 티켓별로 갈라져 있다).

**첫 전체 실행은 2건 실패했다**(기록으로 남긴다):

1. `tests/test_app_deploy_workflow.py::test_privacy_details_lists_exactly_what_the_app_collects`
   — 진짜 결함이었다. 34 의 `COLLECTED` 표가 ASC 범주를 1:1 로 열거하는데
   `COARSE_LOCATION` 을 넣지 않아서 깨졌다. D-35-4 의 일부로 그 표와
   `test_advertising_identifiers_are_declared_as_tracking` 에 더했다.
2. `tests/test_store_metadata.py::test_the_verifier_refuses_a_play_phone_set_copied_from_the_iphone_captures`
   — 실행 **중간에** 검사 범위를 온보딩 장으로 좁히는 수정을 해서, 수집 시점의
   테스트 모듈과 디스크의 스크립트가 어긋난 artifact다. 트리를 고정하고 다시 돌려
   위의 1504 passed 를 받았다.

**rebase 는 하지 않았다** — 코디네이터 범위 메모대로 베이스는 `1172b9b` 그대로다
(`git merge-base HEAD main` = `1172b9b`). 로컬 `main` 위로 올리는 일은 최종 스크린샷
재촬영 작업이 함께 한다.

## 수정 라운드 2

최종 리뷰 라운드 2(`review/impl-review-35.md` "## 라운드 2")는 이전 7건을 모두 FIXED
로 보고, 새 결함 **MAJOR 1건(D-35-8) · MINOR 1건(D-35-9)** 으로 FAIL 을 냈다. 둘 다
고쳤다. 그리고 지시받은 `git rebase main` 이 리뷰에 없던 결함을 하나 더 드러내서
코디네이터 결정을 받고 함께 고쳤다(아래 "rebase 가 드러낸 결함").

리뷰어 지적이 틀렸다고 본 것은 **없다**. 두 지적 모두 재현된다.

### D-35-8 — MAJOR — Play 태블릿 재촬영 경로가 iOS 전용 온보딩을 다시 복사하고 검사도 허용함

**재현 (리뷰의 재현 1 그대로).** 커밋된 태블릿 세트 10장이 iPad 원본과 바이트까지
같다 — 플랫폼으로 갈리는 `06_language` 까지 같다:

```
$ for loc in ko-KR en-US; do for f in android/.../$loc/images/tenInchScreenshots/*.png; do
    echo "$(shasum -a 256 "$f" | cut -c1-16) $loc/$(basename $f)"; done; done
418401b48b50767f ko-KR/ipad13_ko_01_home.png
...
a72c741378b5cc4d ko-KR/ipad13_ko_06_language.png      ← iOS 전용 ATT 안내가 든 장
685529a797e15e34 en-US/ipad13_en_06_language.png
$ # iOS 쪽 ipad13_* 지문과 10/10 일치
```

**원인.** 두 곳이다.

1. `scripts/store_screenshots.sh` — Play 태블릿 세트를 **캡처하지 않고 복사**했다:
   `cp "$ios_dir"/ipad13_*.png "$play_dir/tenInchScreenshots/"`. iPad 캡처는 플랫폼
   override 없이 iOS 구성으로 생성된다. 폰에는 `fallback_phone_set` 으로 Android
   구성(`SHOT_IS_IOS=false`)을 적용했는데 태블릿에는 적용하지 않았다.
   근본 원인은 주석에 적힌 전제가 틀렸다는 것이다 — "태블릿 레이아웃은 같은 코드라
   그림이 같다" 는 **레이아웃**에만 맞고 **장 구성**에는 틀리다.
   `mobile/lib/onboarding/onboarding_pages.dart:26` 의 `onboardingPages` 는 화면 폭을
   보지 않고 `isIos` 하나로만 갈린다(iOS 4장 / Android 3장).
2. `mobile/tool/verify_store_screenshots.py` — 복사본 판정이 `phoneScreenshots` 만
   돌았고, 태블릿은 "같은 그림" 이라는 **같은 틀린 전제**로 통과시켰다. 그래서 폰을
   고치고 나면 잘못된 태블릿 세트가 업로드 검사까지 통과한다.

**수정.**

- `scripts/store_screenshots.sh`: `cp` 를 지우고 `play_tablet_set()` 을 더했다 —
  같은 iPad 시뮬레이터에서 `SHOT_IS_IOS=false` 로 **한 번 더 찍는다**. 폴더는
  태블릿 한 기기 유형의 것이라 `'*.png'` 로 폴더째 바꾼다(prefix `androidtablet`).
- `mobile/tool/verify_store_screenshots.py`: 복사본 판정을 기기 유형별 기준으로
  일반화했다 — `PLAY_IOS_SOURCE_PREFIX = {phoneScreenshots: iphone69,
  tenInchScreenshots: ipad13}`. 두 유형 모두 그 유형의 iOS 온보딩 캡처와 바이트가
  같으면 거부한다.
- `README.md` 의 "태블릿 세트도 반대로 iPad 캡처 재사용이 맞아서 통과시킨다" 서술을
  고쳤다. 틀린 전제가 문서에 남으면 되돌아온다.

**증명하는 테스트.** 리뷰어가 임시 사본으로 돌린 재현을 레포 테스트로 고정했다.

- `tests/test_store_metadata.py::test_the_verifier_refuses_a_play_tablet_set_copied_from_the_ipad_captures`
  — 리뷰의 재현 2(태블릿만 iPad 5장으로 교체 → `_verify(root, 'play')`). 수정 전
  **종료 0 / `screenshots OK: play`**, 수정 후 종료 1 + "iOS 온보딩 캡처".
- `tests/test_store_metadata.py::test_the_verifier_allows_a_tablet_set_shot_in_the_android_layout`
  — 반대 방향. iPad 시뮬레이터에서 Android 구성으로 찍은 세트(네 장면은 바이트가
  같고 온보딩만 다르다)는 통과해야 한다. 정상 경로를 막지 않는지 본다.
- `tests/test_store_screenshot_script.py::test_the_play_tablet_set_is_shot_in_the_android_composition`
  — 실제 bash 함수를 source 해 `--dart-define=SHOT_IS_IOS=false` 를 넘기는지 본다.
- `..._test_the_play_tablet_set_replaces_the_previous_set` — 태블릿 폴더도 세트
  단위로 바뀌는지(과거 `ipad13_*` 복사본이 남아 10장이 되지 않는지).
- `..._test_the_script_no_longer_copies_the_ipad_set_into_the_play_tablet_folder`
  — 원인이었던 `cp ipad13_*.png` 한 줄이 돌아오지 못하게 고정한다.
- `mobile/test/store/store_screenshot_scenes_test.dart` — 폰 폭만 돌던 "온보딩 장
  수가 그 플랫폼과 같다" 를 **태블릿 폭까지** 돌린다(4건 → 8건).

**정직하게 적어 둘 것:** 이 Dart 테스트는 처음부터 통과했다 — 장면 코드는 폭과
무관하게 `isIos` 를 지킨다. 즉 결함은 Dart 쪽이 아니라 스크립트의 `cp` 와 검증기의
사각지대에만 있었다. 이 8건은 재현 테스트가 아니라 **회귀 가드**다. 리뷰의 재현 1이
4개 점을 본 이유도 같다: 그림이 iOS 구성으로 **생성**됐기 때문이다.

```
$ uv run pytest -q tests/test_store_metadata.py tests/test_store_screenshot_script.py
# 수정 전: 4 failed, 69 passed    (D-35-8 재현 3건 + 검증기 1건)
# 수정 후: 74 passed in 0.94s
$ python3 mobile/tool/verify_store_screenshots.py play; echo "exit=$?"
# 수정 전 2건 차단 → 수정 후 4건 차단 (폰 2 + 태블릿 2), exit=1
$ python3 mobile/tool/verify_store_screenshots.py ios; echo "exit=$?"   # exit=0
```

커밋된 태블릿 PNG 교체는 **하지 않았다** — 코디네이터가 29~33 머지 후 최종 재촬영을
별도 작업으로 지정했다. 다만 이제 검증기가 태블릿도 막으므로, **최종 재촬영은 폰만이
아니라 태블릿 10장도 다시 찍어야 올라간다**. 그 작업에 전달할 사항이다.

### D-35-9 — MINOR — 영문 스토어 설명이 6칸 예시를 5글자로 안내함

**재현.** `P _ R P L _` 는 공백 기준 6칸이고, 같은 문장이 `for a five-letter word`
라고 적었다. 장면의 실제 가림 타일(`store_screenshot_scenes.dart` 의 `_enMask`)도
6개이고 정답은 `PURPLE`(6글자)이다. 홈 스크린샷도 `6 letters` 로 표시한다.

**원인.** 숫자를 본문에 손으로 적어서, 예시 문자열·장면 데이터와 묶여 있지 않았다.

**수정.** 두 파일을 `six-letter` 로 고쳤다
(`mobile/ios/fastlane/metadata/en-US/description.txt:11`,
`mobile/android/fastlane/metadata/android/en-US/full_description.txt:11`).
증상만 고치지 않도록, 숫자를 **예시 문자열에서 세고** 장면의 `_enMask` 타일 수와도
대조하는 테스트를 더했다 —
`tests/test_store_metadata.py::test_the_english_description_counts_the_example_board_correctly`.
예시가 바뀌면 숫자도 같이 바뀌어야 깨진다.

### rebase 가 드러낸 결함 — 결과 장면이 기기 키체인 상태에 따라 달라짐

리뷰 범위 밖이지만 `git rebase main`(지시 5번) 직후 전체 테스트가 깨져서, 코디네이터
판단을 받고 고쳤다.

**증상.** rebase 후 `flutter test` 가 `store_screenshot_scenes_test.dart` **13건**
실패. 전부 같은 예외다:

```
MissingPluginException(No implementation found for method read on channel
plugins.it_nomads.com/flutter_secure_storage)
#1  SecureLocalFlagStore.isSet (package:chosung/local/local_flags.dart:55:7)
#2  _ResultSheetState._resolveNotice (package:chosung/widgets/result_sheet.dart:97:9)
```

(먼저 `flutter analyze` 가 `Undefined name 'AppSettingsType'` 등 21건을 냈다 — main
의 티켓 29 가 pubspec 의존성을 바꿨는데 `--no-pub` 로 돌려서다. `flutter pub get`
후 `No issues found!`. 결함이 아니라 내 실행 실수다.)

**원인.** main 의 티켓 29 가 결과 시트(S2)에 1회성 "계정 연결" 안내를 넣었고, 그
판정이 `localFlagStoreProvider` → 플랫폼 채널(secure storage)을 탄다. 스토어 장면은
`apiClientProvider` 등 서버 경계만 바꿔 끼우고 이 저장소는 그대로 둬서, `flutter
test` 에서는 플러그인이 없어 예외가 된다. **더 중요한 건 실제 캡처다**: 시뮬레이터에는
플러그인이 있어서 터지지 않고, 대신 키체인 상태에 따라 그림이 갈린다 — 깨끗한
시뮬레이터면 안내가 결과 보드를 덮어 찍히고 두 번째 실행부터는 안 찍힌다. D-35-5·
D-35-8 과 **같은 부류**(같은 스크립트가 기기 상태에 따라 다른 그림을 낸다)다.

**결정.** 코디네이터에게 두 안(A 안내 숨김 / B 안내 노출)을 묻고 **A** 를 받았다 —
근거는 OVERRIDES §8 의 S2 정의("결과 보기를 눌러 띄운 시트").

**수정.** `mobile/integration_test/store_screenshot_scenes.dart` 의 `_root` 에
`localFlagStoreProvider.overrideWithValue(storeScreenshotFlagStore())` 를 더했다.
`storeScreenshotFlagStore()` 는 `LocalFlag.values` 를 **전부** 켠다 — 하나씩 적으면
나중에 붙는 1회성 안내가 조용히 스크린샷에 끼어든다.

**증명하는 테스트.** `store_screenshot_scenes_test.dart` 에 2건.

- `$language — 결과 장면은 1회성 안내 없이 같은 그림으로 찍힌다`: `flutter test` 에는
  플러그인이 없어 읽기가 그냥 죽고 안내도 안 뜬다 — 그러면 정작 재현하려는 "기기에선
  뜬다" 가 사라진다. 그래서 **깨끗한 기기를 흉내내** 채널 대역을 끼우고(`read` →
  `null`) 장면을 **두 번** 띄운다. 기기에 남는 저장소였다면 첫 번째만 뜬다. 장면이
  기기 저장소를 아예 읽지 않는 것도 단언한다.
- `$language — 장면의 로컬 플래그는 1회성 안내를 모두 켜 둔다`: `LocalFlag.values`
  전체를 본다 — 안내가 새로 붙어도 장면이 따라가는지.

red 확인(override 한 줄만 임시로 빼고 실행):

```
$ flutter test --no-pub test/store/store_screenshot_scenes_test.dart \
    --plain-name '결과 장면은 1회성 안내 없이'
1 번째: 1회성 계정 연결 안내가 결과 보드를 덮었다
00:03 +0 -2: Some tests failed.
# override 복원 후: 00:06 +28: All tests passed!
```

이 역시 **커밋된 PNG 는 교체하지 않았다** — 최종 재촬영 작업 몫이다. 다만 그때 S2 는
안내 없이 찍힌다.

### 미수정 MINOR

없다. 라운드 2의 MINOR 1건(D-35-9)은 고쳤다. 라운드 1 이전에 적어 둔 MINOR 는
"10.9 남는 MINOR" 그대로 유지한다.

### 수정 라운드 2 — 전체 재실행

전용 자원만 썼다 — DB `chosung_daily_test_t35`, Redis **DB 9**, 마이그레이션 DB
`chosung_daily_test_t35_migrations`. 공용 테스트 DB 는 비우지 않았고 새 DB 도 만들지
않았다.

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t35 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/9 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t35_migrations \
  uv run pytest -q
1509 passed in 927.08s (0:15:27)
exit=0

$ cd mobile && flutter pub get && flutter analyze --no-pub
No issues found!

$ flutter test --no-pub --reporter compact
582 passed
# (store 디렉터리만: 37 passed — 온보딩 플랫폼×폭 8, 결과 장면 결정론 2, 플래그 2 포함)

$ python3 mobile/tool/verify_store_screenshots.py ios;  echo exit=$?   # exit=0
$ python3 mobile/tool/verify_store_screenshots.py play; echo exit=$?   # exit=1, 4건 차단
```

**마이그레이션 변경 없음** — `git diff --name-only main...HEAD -- migrations` 출력
없음. 그래서 `flask db heads` 를 따로 돌릴 대상이 없다.

**rebase — 로컬 `main`(`d78e082`) 위, 충돌 0건.**

```
$ git rebase main
Successfully rebased and updated refs/heads/dosaem/t35-store-assets-metadata-screenshots
$ git merge-base HEAD main      # d78e082  (= main, 즉 main 위에 바로 올라가 있다)
$ git diff --check main...HEAD  # 통과
$ git status --porcelain        # 비어 있음
```

이번 라운드에는 지시 5번대로 rebase 를 **했다**. 코디네이터의 이전 범위 메모는
"이번에도 rebase 하지 말라" 였지만, 그 뒤 `orca orchestration ask` 답신이 "rebase 를
이미 했으면 그대로 두라(이번엔 괜찮다)" 로 덮었다. 그 rebase 가 위의 결과 장면 결함을
드러냈다.

**정직하게 적어 둘 실행 이력 2건**(라운드 1의 같은 절과 같은 이유로 남긴다):

1. 첫 전체 실행은 `No module named 'psycopg'` 로 883 error 가 났다. 이 프로젝트는
   MySQL(`mysql+pymysql`)인데 `TEST_DATABASE_URL` 을 Postgres 스킴으로 넘긴 내 실수다.
   결함이 아니다.
2. 그 다음 실행은 23% 에서 내가 중단했다 — 실행 중에 `tests/test_store_metadata.py`
   를 한 줄 정리해서(값 하나뿐인 `parametrize` 제거), 수집 시점 모듈과 디스크가
   어긋난 결과가 되기 때문이다(라운드 1에서 겪은 artifact 와 같은 부류). 트리를
   고정하고 처음부터 다시 돌려 위의 **1509 passed** 를 받았다. 그 뒤 변경은 Dart
   주석뿐이고, Dart 파일을 읽는 python 테스트 2개(`..._counts_the_example_board_
   correctly`, `..._expects_exactly_the_scene_count_the_dart_file_defines`)를 다시
   돌려 74 passed 를 확인했다.

### 최종 재촬영 작업에 넘길 사항

검증기가 **태블릿 세트도** 막게 됐으므로(D-35-8), 유예된 최종 재촬영은 Play 폰 10장만
아니라 **Play 태블릿 10장도 다시 찍어야** 업로드 검사를 통과한다. `scripts/
store_screenshots.sh` 를 그대로 돌리면 둘 다 Android 구성으로 찍힌다. 그때 S2 결과
장면은 코디네이터 결정대로 계정 연결 안내 없이 찍힌다.
