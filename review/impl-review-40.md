# 티켓 40 최종 리뷰 — 라운드 1 (최종 스토어 스크린샷 재촬영)

- 대상: `dosaem/t40-final-store-screenshots` `eea3202`(로컬 `main` `3463865` 위 1 커밋, `git merge-base --is-ancestor main HEAD` 참).
- 읽은 것: 티켓 원문, 스펙 §B.19·§B.25·미정 25, 티켓 35 원문·`review/impl-review-35.md`(최종 재촬영 유예 문구)·`review/impl-evidence-40.md`, `git diff main...HEAD`, `scripts/store_screenshots.sh`, `mobile/tool/verify_store_screenshots.py`, 장면·테스트 diff 전체.
- 코디네이터 리뷰 메모(msg_627d797ea88e) 5개 항목을 §4 에 따로 답했다.
- 코드·테스트·설정·`.scratch/` 는 바꾸지 않았다. 뮤테이션 확인 2건은 파일을 잠깐 바꿨다가 `git checkout --` 으로 되돌렸고 끝난 뒤 트리는 clean 이다(§2.4).
- 시크릿은 적지 않는다. DB 접속 문자열은 호스트·DB 이름만 적는다.

## 1. 티켓 체크박스별 충족 여부

| # | 요구 | 판정 | 근거 |
|---|---|---|---|
| 1 | 장면이 29~33·38 머지 후 실제 화면과 맞는지 확인, 기기 상태에 따라 달라지면 결정론 보정 | 충족 | 증거 §1 표의 7개 항목을 PNG 로 직접 확인(§2.3). 보정 4개(광고 게이트·알림 권한·알림 설정·시계)+`MediaQuery` 고정이 `store_screenshot_scenes.dart:353-392`·`420-428`·`445-451` 에 있고, 각각을 잡는 테스트 6종×ko/en 이 `test/store/store_screenshot_scenes_test.dart:278-436` 에 있다. 테스트가 실제로 결함을 잡는지 뮤테이션 2건으로 확인(§2.4) |
| 2 | iOS 세트(6.9"·6.5"·iPad 13", ko·en 각 5장) 재촬영 | 충족 | `mobile/ios/fastlane/screenshots/{ko,en-US}/` 에 기기별 5장, 해상도 1320×2868 / 1242×2688 / 2064×2752 로 세트 안 혼재 없음(§2.2). 12장은 바이트가 바뀌었고 18장(01·03·06)은 재촬영 결과가 바이트까지 같다 — 30~33 이 그 화면을 바꾸지 않았다는 증거 설명과 맞다 |
| 3 | Play 폰·태블릿을 Android 구성으로 재촬영, 검사 폰·태블릿 통과, 사용자 AVD 보존 | 충족 | 폰 `android_*` 1080×2400(네이티브 에뮬레이터, 온보딩 점 3개·`Apple 로 연결` 없음), 태블릿 `androidtablet_*` 2064×2752(iPad + `SHOT_IS_IOS=false`, 점 3개). 사용자 AVD `Medium_Phone_API_36.1` 은 남아 있고 `chosung_t40_shots` 는 없다(`emulator -list-avds`) |
| 4 | 업로드 전 검사 iOS·Play 0건 + 세트마다 1장 이상 눈 확인 기록 | 충족 | 내가 직접 돌린 결과 둘 다 exit 0(§2.1). 증거 §6 의 눈 확인 표는 10세트 전부를 다루고, 내가 세트마다 2장씩 다시 열어 같은 내용을 봤다(§2.3) |
| 5 | `review/impl-evidence-40.md` 에 파일 목록·검사 출력·눈 확인·한계 | 충족 | §3(52개 변경 내역·해상도), §5(검사 출력), §6(눈 확인), §9(한계 7개). 시크릿 없음 |
| 제약 | 앱 기능·메타데이터 문구 변경 금지 | 충족(조건부) | 메타데이터 문구 변경 없음. `lib/` 변경은 `today_tab.dart` 7줄(시계 주입)뿐이고 동작이 같다(§4-4). 증거는 코디네이터 허용이라 적었고 코디네이터 메모 1) 이 그 결정을 확인한다 |
| 제약 | 전체 flutter test·analyze·format·ruff·pytest 통과 | 충족 | §2.5. pytest 는 전용 DB `chosung_daily_test_t40`·Redis 14 로 돌렸다 |
| 제약 | 빌드 산출물 정리, 사용자 AVD 보존, push·외부 호출 없음 | 증거로 충족 | 커밋에 빌드 산출물 없음(`git status` clean, `Podfile.lock` 등 미변경). 업로드 흔적 없음. AVD 는 위 3 참조 |
| 수용 | 검사 0건, 장면 테스트 통과, 로컬 main 위 clean 트리, 커밋 | 충족 | §2 전부 |

## 2. 직접 확인한 것

### 2.1 업로드 전 검사 (내가 돌린 출력)

```
$ cd mobile && python3 -I tool/verify_store_screenshots.py ios
screenshots OK: ios — 로케일마다 5 장씩          (exit 0)
$ python3 -I tool/verify_store_screenshots.py play
screenshots OK: play — 로케일마다 5 장씩         (exit 0)
```

검사기가 보는 것(`verify_store_screenshots.py:29-56`): 로케일×기기 유형 5장, Play 상한 8장, Play 세트에 iOS **온보딩**(`06_language`) 캡처와 바이트까지 같은 파일 없음. 티켓 35 라운드 3 에서 4건 차단이던 그 검사가 이제 0건이다.

### 2.2 해상도·중복 (전수)

| 세트 | 장 수 | 해상도 |
|---|---|---|
| iphone69 ko/en | 5/5 | 1320×2868 |
| iphone65 ko/en | 5/5 | 1242×2688 |
| ipad13 ko/en | 5/5 | 2064×2752 |
| android ko-KR/en-US | 5/5 | 1080×2400 |
| androidtablet ko-KR/en-US | 5/5 | 2064×2752 |

iOS 와 바이트가 같은 Play 파일은 `androidtablet_{ko,en}_{01,02,03}` 6장이고 전부 iPad 의 홈·결과·순위 장면이다. 이 셋은 플랫폼으로 갈리지 않는 화면이라 **같은 것이 정상**이고(검사기 주석 `verify_store_screenshots.py:42-47` 이 그렇게 정의), 오히려 장면이 결정론적이라는 증거다. 플랫폼으로 갈리는 `04_records`(Apple 카드)·`06_language`(온보딩 점)는 다르다. 결함 아님.

### 2.3 눈으로 확인한 것 (세트마다 2장, 원본을 700px 로 축소해 열었다)

| 세트 | 연 파일 | 본 것 |
|---|---|---|
| iOS ko 6.9" | 03, 04 | S3 `게스트 #a3f1`·`1회`, 내 줄 `23 나`. S4 `구글로 연결`/`Apple 로 연결`, `구독 · 광고 없이 플레이`, `일일 알림 오전 9:00`, `리마인더` 켜짐(초록), 경고 행·광고 개인정보 행 없음 |
| iOS en 6.9" | 01, 02 | S1 힌트 카드 `Watch an ad to peek at the hint`, 오류 안내 없음, `3/5 tries left`. S2 `Next puzzle in 04:45:19`, 계정 연결 안내 없음. 한글 0 |
| iOS ko 6.5" | 01, 03 | S1 `광고 보고 힌트 미리 보기`, 안내 없음. S3 게스트 표기·`나` |
| iOS en 6.5" | 02, 04 | S2 `04:45:19`. S4 `Continue with Apple` 있음, `Nudge if unsolved` 켜짐, `9:00 AM` |
| iOS ko iPad | 01, 04 | rail + 힌트 카드 우측 열. S4 rail + 2열, `Apple 로 연결`, 리마인더 켜짐, `버전 1.0.0`·`계정 삭제` |
| iOS en iPad | 03, 06 | 표 헤더 `Rank/Name/Tries/Time`, `1 try`/`2 tries`. 온보딩 점 **4개**(iOS), 칩 `Korean/English` |
| Play ko 폰 | 01, 04 | S1 동일 레이아웃(안내 없음). S4 `구글로 연결`만(Apple 없음 = 실제 Android), Material 스위치 켜짐, 경고 행 없음 |
| Play en 폰 | 02, 06 | S2 `04:45:19`, 안내 없음. 온보딩 점 **3개**, 한글 0 |
| Play ko 태블릿 | 02, 06 | 결과 다이얼로그(T2) `다음 퍼즐까지 04:45:19`. 온보딩 점 **3개** |
| Play en 태블릿 | 03, 04 | 표 레이아웃. S4 `Continue with Google` 만, `Nudge if unsolved` 켜짐 |

코디네이터 메모 2) 의 항목 중 **광고 슬롯**은 어느 그림에도 없다 — 장면 셸이 `AdBannerSlot` 을 넣지 않는 것은 티켓 35 때부터의 설계(OVERRIDES §8, `store_screenshot_scenes.dart:16-17`)이고 이번 티켓 범위가 아니다. 구독자/비구독자 차이가 그림에 없다는 점은 증거 §9-5 가 한계로 적었다.

### 2.4 테스트가 실제로 결함을 잡는가 (뮤테이션 2건, 되돌림)

| 바꾼 것 | 결과 |
|---|---|
| `store_screenshot_scenes.dart` 의 `SynchronousFuture(...)` → `Future.value(...)` | `ko — S4 리마인더 스위치는 첫 프레임부터 켜져 있다` 실패: `Expected: true / Actual: <false> / 첫 프레임에 리마인더가 꺼져 있다` |
| `today_tab.dart` 의 `now: ref.read(clockProvider),` 두 줄 삭제 | `countdown_clock_test.dart` 2건 모두 실패: `Found 0 widgets with text containing 다음 퍼즐까지 00:12:33` |

둘 다 증거 §2.2·§2.6 의 주장과 같다. 되돌린 뒤 `git status --short` 는 비어 있다.

나머지 테스트 4종(힌트 안내 없음·알림 2행·광고 개인정보 행 없음·기기 저장소 미사용)은 코드로 읽었다. 저장소 미사용 테스트는 `plugins.flutter.io/shared_preferences` 채널에 mock 을 걸고 호출 목록이 비어 있어야 통과하므로, 장면이 override 를 빼면 `getAll` 이 기록돼 실패한다 — 항상 통과하는 테스트가 아니다. 힌트 안내 테스트는 S1 에서 `onPreview != null` 까지 보므로 게이트가 `canLoadAds=false` 로 돌아가면 잡는다.

### 2.5 전체 검증 (내가 돌린 명령)

```
$ cd mobile && flutter pub get                                   (exit 0)
$ dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 201 files (0 changed)                                  (exit 0)
$ flutter analyze --no-pub
No issues found!                                                 (exit 0, info 0)
$ flutter test --no-pub --reporter compact
01:23 +796: All tests passed!                                    (exit 0)

$ uv run ruff check .
All checks passed!                                               (exit 0)

$ TEST_DATABASE_URL=mysql+pymysql://…@localhost:3306/chosung_daily_test_t40?charset=utf8mb4 \
  TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t40_migrations?charset=utf8mb4 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/14 uv run pytest -q
1526 passed in 853.81s (0:14:13)                                (exit 0, 재실행 없음)

$ git diff --check main...HEAD                                   (통과)
$ git diff --name-only main...HEAD -- migrations                 (없음 → flask db heads 대상 아님)
```

전용 DB `chosung_daily_test_t40`·`_t40_migrations`(둘 다 이미 있었다)·Redis 14 를 그대로 썼다. 레포 기본 DB 로 떨어지지 않았다.

## 3. 결함

### D-40-1 — MINOR — `docs/RELEASE.md` 에서 티켓 35 의 행을 고쳤다 (공유 파일 규칙)

- 파일: `docs/RELEASE.md:931-941`
- 재현: `git diff main...HEAD -- docs/RELEASE.md` → `### 35.` 절의 `- [ ] **Play 폰 스크린샷 — 지금은 업로드가 막혀 있다.**` 행이 `[x]` + 취소선으로 바뀌어 있다. 공통 규칙은 "자기 번호 소제목/자기 행만 섹션 끝에 덧붙인다" 다.
- 판단: 35 는 이미 main 에 머지됐고 그 행을 건드리는 병렬 티켓이 없어 충돌 위험은 없다. 증거 §10 이 이유(출시 순서를 잘못 읽지 않게)를 적었고 그 이유는 타당하다. 그래서 MINOR 이고, **이대로 받아도 된다** — 규칙 위반을 기록으로 남기는 것이 목적이다. 고친다면 35 행은 원문대로 두고 `### 40.` 첫 줄에 "35 의 Play 폰 체크박스는 이 절로 해소" 한 줄만 두면 된다.

### D-40-2 — MINOR — `mobile/ios/Podfile.lock` 이 낡았다 (티켓 40 이 만든 결함은 아니다, main 기존)

- 파일: `mobile/ios/Podfile.lock` (PODS 절)
- 재현: `pubspec.yaml` 의 iOS 플러그인 중 `google_mobile_ads`·`google_sign_in`(ios)·`sign_in_with_apple`·`in_app_purchase_storekit`·`flutter_timezone`·`app_settings` 가 lock 의 PODS 목록에 없다(`grep -c google_mobile_ads ios/Podfile.lock` → 0). 티켓 35 가 커밋한 뒤 30~33 이 더한 플러그인이다.
- 코디네이터 메모 5) 의 심각도 판단: **iOS 릴리스 빌드를 막지 않는다.** `.github/workflows/flutter.yml:273-275` 가 빌드 전에 `pod install` 을 `--deployment` 없이 돌리고, `flutter build ipa`(같은 파일 `:324`) 도 pubspec 변경을 감지하면 `pod install` 을 다시 돌린다 — lock 은 그 자리에서 갱신된다. 막히는 경우는 `pod install --deployment` 를 쓰거나 lock 을 소스 오브 트루스로 삼는 캐시 키를 둘 때인데 둘 다 없다. 다만 로컬에서 `pod install` 을 돌리면 lock·`project.pbxproj` 가 +250줄 바뀌어 매번 되돌리게 되고(증거 §7 이 실제로 그랬다), 재현 가능한 빌드라는 lock 의 목적은 지금 깨져 있다. → MINOR. 이번 티켓 범위(스크린샷·결정론)가 아니므로 **티켓 40 에서 고칠 일이 아니고**, iOS 빌드 설정을 맡는 티켓(또는 37 릴리스 문서 쪽)에서 `pod install` 한 번 돌려 lock 만 커밋하면 된다.

BLOCKER 0, MAJOR 0, MINOR 2.

## 4. 코디네이터 리뷰 메모에 대한 답

1. **비EEA 기준·clockProvider 고정 결정**: 결함으로 올리지 않았다. 구현이 그 결정대로 결정론적인지만 봤다 — 네 override 가 전부 `_root` 의 `ProviderScope.overrides` 에 상수/고정 notifier 로 들어가고(`store_screenshot_scenes.dart:420-428`), 기기 설정(24시간제·텍스트 배율)은 `MediaQuery` 로 고정(`:445-451`). 같은 세트 안에서 ko·en 카운트다운이 모두 `04:45:19`, Play 태블릿 3장이 iPad 와 바이트까지 같다는 것이 결정론의 실측 증거다.
2. **PNG 세트마다 2장 이상**: §2.3, 10세트×2장 = 20장. 계정 카드·구독 카드·알림 2행·`Guest #xxxx` 전부 확인. 언어 혼입·오류/경고 문구 없음. 광고 슬롯은 설계상 장면에 없다(§2.3 끝).
3. **업로드 전 검사 직접 실행**: §2.1, iOS·Play 둘 다 exit 0.
4. **`lib` 변경이 앱 동작을 바꾸지 않는가**: 엄격히 봤다. 바뀐 두 호출부(`today_tab.dart:104`·`:536`)는 `now:` 인자를 추가로 넘길 뿐이고, 받는 쪽의 기본값은 `showResultSheet(... now = DateTime.now)`(`result_sheet.dart:32`), `PuzzleCountdown({this.now = DateTime.now})`(`puzzle_countdown.dart:13`), `clockProvider` 기본값도 `DateTime.now`(`config/clock.dart:13`) 라 override 가 없는 앱에서는 **같은 함수 객체**가 흘러간다. `lib` 의 다른 `PuzzleCountdown(`/`showResultSheet(` 호출부는 없다(grep). `_NoPuzzleCard.build` 안의 `ref.read` 는 값이 바뀌지 않는 `Provider` 라 재빌드 누락 문제가 없다. 전체 796 테스트가 그대로 통과한다.
5. **Podfile.lock 심각도**: D-40-2, MINOR, 티켓 40 결함 아님. 근거는 위.

## 5. 참고 (결함 아님)

- **`lib/` 변경은 "앱 기능 변경 금지" 제약의 문자 그대로는 벗어난다**(7줄). 동작이 같고 코디네이터 메모 1) 이 승인한 결정이라 결함으로 올리지 않는다. 다음 재촬영 티켓에서는 이런 주입을 먼저 ask 로 올린 뒤 하는 흐름이 유지되면 된다.
- **Android 폰 S4 의 스위치는 Material(남색), iOS 는 Cupertino(초록)** 로 다르게 찍힌다. `Switch.adaptive` 의 실제 플랫폼 모습이라 Play 가 요구하는 "실제 앱 경험" 과 맞다.
- **Play 태블릿 01·02·03 은 iPad 와 같은 파일**이다(§2.2). 검사기 설계상 정상.
- **`ref.read` 를 build 안에서 쓴 것**(`today_tab.dart:536`)은 riverpod_lint 가 있으면 경고할 자리지만 이 레포는 그 린트를 안 쓰고(analyze 0건), 값이 고정인 `Provider` 라 실질 문제가 없다. 스타일 영역.
- **구독 카드에 가격이 없다**(증거 §9-3). `NoopPurchaseService` 라 그렇고 스펙 §A.8 대로 앱이 금액을 임의로 적지 않는다. 결함 아님.
- 내가 돌린 `flutter pub get` 이 `mobile/.dart_tool`·`pubspec.lock` 변경 없이 끝났고(gitignore 대상 외 변경 없음) 트리는 clean 이다.

판정: PASS
