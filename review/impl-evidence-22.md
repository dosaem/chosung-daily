# 티켓 22 구현 증거 — Flutter 앱 골격(`mobile/`)

- 브랜치: `dosaem/t22-flutter-scaffold-config-maintenance`, 로컬 `main` **b43567e**
  (티켓 11 머지) 위로 `git rebase main` 완료 — 충돌 없음, 작업 트리 clean
- 커밋 7개, `main..HEAD` 175파일 (+6541 / -5)
- Flutter 3.38.6 / Dart 3.10.7 (`flutter --version`, 로컬에 이미 설치돼 있어 설치 시도 없음)
- 백엔드 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t22`, Redis DB **10**,
  마이그레이션 왕복용 `chosung_daily_test_t22_migrations`
  (`TEST_DATABASE_URL`, `TEST_REDIS_URL`, `TEST_MIGRATION_DATABASE_URL` 로 지정).
  공용 `chosung_daily_test`·Redis 1 과 다른 워커의 자원은 건드리지 않았다.
  이 티켓은 Python 코드를 한 줄도 바꾸지 않았고 마이그레이션도 만들지 않았다.
- **외부 서비스 호출 0건.** Firebase·Sentry·AdMob·스토어·Slack 어디에도 연결하지
  않았다. Sentry 는 DSN 이 비면 초기화 자체를 하지 않고, 테스트는 초기화 함수를
  가짜로 받아 "불렸는가" 만 본다. 네트워크를 탄 건 두 가지뿐이다: pub.dev 패키지
  해석(`flutter pub get`)과 Pretendard 폰트 1회 다운로드(아래 출처·해시).
  NAS 접속·배포·`git push` 없음.
- 시크릿 값은 어떤 파일·로그에도 쓰지 않았다. 추가한 빌드 설정은 이름만:
  `API_BASE_URL`, `SENTRY_DSN`(둘 다 `--dart-define`). `.env`, `.env.prod*` 는
  열지도 않았다. Firebase 설정 파일은 gitignore + 자리표시자 `.example` 만 커밋했다.

## 코디네이터 확정 사항

1. (`ask`) **앱 버전은 `package_info_plus` 로 런타임에 읽는다.** `--dart-define` 으로
   따로 주입하면 `pubspec.yaml` 과 어긋날 수 있고, 강제 업데이트 판정이 틀리면
   사용자가 앱에 못 들어온다. 티켓 패키지 목록 밖 추가라 README "설계 판단 > 22" 에
   이유를 적었다. 비교는 순수 함수 `isUpdateRequired` 로 분리.
2. (`ask`) **Pretendard 를 지금 번들한다.** 공식 배포처에서만 받고 OFL 라이선스를
   함께 커밋, 버전·출처·해시를 여기 적는다(아래 "폰트 출처").
3. (`check`) **`/config` 경로는 `/api/v1/config`** — `AppEnv.apiBaseUrl` 기본값이
   `.../api/v1` 로 끝나고 `ApiClient` 가 `/config` 를 붙인다.
4. (`check`) Firebase 설정 파일·서명 키·스토어 계정이 필요한 단계는 시도하지 않고
   `docs/RELEASE.md` "### 22." 사람 체크리스트로 넘겼다.
5. (`check`) PRODUCT.md 의 Platform 재판단 — 아래 "판단 1" 에 결론과 근거.

## 판단 1: PRODUCT.md 의 Platform 은 `web` 으로 유지했다 (코디네이터 확인 요청)

코디네이터 메모는 "audit.native 가 `mobile/` 을 대상으로 돌 수 있게 필요하면
갱신하라" 였다. 값을 `adaptive` 로 바꾸면 impeccable 의 routing 규칙상
**`impeccable detect` 가 꺼진다**(`reference/routing.md`: platform 이
`ios`/`android`/`adaptive` 면 detect 를 돌리지 않는다). 웹 티켓 17·18 의 완료
조건이 "detect 0건" 이라 그 게이트를 잃는다. 게다가 `init.md` 의 `adaptive` 정의는
"OS 별로 **디자인 언어를 바꾸는** 하나의 제품" 인데, 이 앱은 웹과 같은 OVERRIDES
토큰 하나를 쓰므로 정의에도 맞지 않는다.

그래서 **값은 `web` 으로 두고, 같은 절에 "앱(`mobile/`)은 네이티브로 다루며
`audit.native` 로 `ios.md`·`android.md` 를 둘 다 읽고 점수를 매긴다" 를 명시**했다
(PRODUCT.md "Platform"). 아래 §4 가 그 첫 기록이다. 코디네이터가 `adaptive` 쪽을
원하면 PRODUCT.md 한 절만 고치면 되고, 그때 17·18 의 detect 게이트를 어떻게 지킬지
같이 정해야 한다.

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 무엇이 증명하는가 |
|---|---|
| Flutter 루트 `mobile/` 확정, flutter-ci `working-directory: mobile` | `mobile/` 디렉터리 존재(레포 `app/` 은 Flask 그대로), `.github/workflows/flutter-ci.yml` 의 `defaults.run.working-directory: mobile`. CI 실행 자체는 아래 §2 의 로컬 동일 명령 3개로 대신 확인 |
| 패키지 목록 | `mobile/pubspec.yaml` — Riverpod·go_router·dio·flutter_secure_storage·easy_localization·sentry_flutter·firebase_core/analytics·url_launcher·package_info_plus·lucide_icons(런타임), flutter_native_splash·flutter_launcher_icons·very_good_analysis(dev). `grep -r "hive\|freezed" pubspec.yaml` → 0건 |
| 번들/패키지 `com.dosaem.chosung`, 앱 이름 2개 | `android/app/build.gradle.kts`(namespace·applicationId), `ios/.../project.pbxproj`(PRODUCT_BUNDLE_IDENTIFIER 3곳), `values/strings.xml`="Hidden Vowels" + `values-ko/strings.xml`="오늘의 초성", `Info.plist` CFBundleDisplayName + `ko.lproj/InfoPlist.strings` |
| Firebase 파일 gitignore + `.example` + 없으면 초기화 스킵 | `mobile/.gitignore` 두 줄 + `google-services.json.example`·`GoogleService-Info.plist.example` 커밋. `test/config/bootstrap_test.dart` 3개(정상 초기화 / PlatformException → skipped / MissingPluginException → skipped). 빌드 쪽은 `android/app/build.gradle.kts` 의 `if (file("google-services.json").exists())` 와 §2 의 **실제 APK 디버그 빌드 성공**(파일 없는 상태) |
| analyze/test 가 파일 없이 통과 | §2 `flutter analyze` 0건 / `flutter test` 81 passed. 작업 트리에 두 설정 파일이 없다(`flutter-ci.yml` 첫 단계가 그걸 매번 확인한다) |
| `ApiClient` 가 `POST /guests`·`GET /config`·`GET /me/stats` 만 + Dio 구현 + Fake | `lib/api/api_client.dart`(메서드 3개), `lib/api/dio_api_client.dart`, `test/fakes/fake_api_client.dart`. `test/api/dio_api_client_test.dart` 9개가 경로·바디·헤더·에러 매핑을 본다 |
| `--dart-define=API_BASE_URL` | `lib/config/app_env.dart` 의 `String.fromEnvironment('API_BASE_URL', ...)`, `DioApiClient.withBaseUrl` |
| 에러 코드→도메인 예외 매핑 골격 | `lib/api/api_exception.dart`(sealed + 코드표 + status 폴백), `test/api/dio_api_client_test.dart` "에러 매핑" 5개(401/400/5xx/연결실패/JSON 아닌 본문) |
| 토큰 secure storage 보관, 없으면 `POST /guests {puzzle_language}`(기기 언어 en → en) | `lib/guest/guest_token_store.dart`(Keychain/Android), `test/startup/startup_controller_test.dart` "저장된 토큰이 없으면 게스트를 발급해 저장한다" / "기기 언어가 en 이면 en 게스트로 발급한다" / "저장된 토큰이 있으면 발급하지 않는다", `test/app_startup_branch_test.dart` "토큰이 없으면 게스트를 발급하고 홈으로 간다" |
| 401 이면 새 게스트 | `test/startup/startup_controller_test.dart` "내 기록이 401 이면 새 게스트를 발급하고 다시 읽는다"(`fetchMyStatsCalls == 2`, 저장소 토큰 교체) + "새 게스트로도 401 이면 예외를 올린다"(무한 재시도 없음) |
| 토큰 상태를 Provider 로 노출(27 교체·28 구독), ApiClient 에 숨기지 않음 | `lib/guest/guest_token_provider.dart`. `test/guest/guest_token_provider_test.dart` 6개 — 복원 / `replaceWith`(27) / `clear` / **변경 구독**(28) / 동기 읽기(Bearer 용). `dio_api_client_test.dart` 의 "같은 클라이언트가 요청마다 토큰을 다시 읽는다" 가 같은 Dio 인스턴스에서 토큰 교체 전후 두 요청의 `Authorization` 헤더를 비교(수정 라운드 1 에서 추가) |
| OVERRIDES 토큰 → ThemeData(라이트/다크), 토큰 이름 상수, 그림자 없음 | `lib/theme/app_colors.dart`(필드 이름 = 토큰 이름), `lib/theme/app_theme.dart`. `test/theme/app_theme_test.dart` 10개 — 표 값 일치, brand 를 면·글자색으로 안 씀, 배경색, **그림자 전부 0**, Pretendard+Inter 폴백, 본문 16/1.5, 모서리 10·20, 터치 타깃 ≥48, ThemeExtension |
| Pretendard, Lucide | `pubspec.yaml` fonts 3종 + `assets/fonts/Pretendard-LICENSE.txt`, `lucide_icons` 의존성 + 화면에서 `LucideIcons.*` 사용 |
| iPad 중앙 정렬 최대 600px 래퍼 | `lib/widgets/max_width_body.dart`, `test/app_startup_branch_test.dart` "본문은 600px 를 넘지 않는다 (iPad)"(1668×2388 뷰에서 화면 폭 834, 본문 600) |
| S7 점검/업데이트 화면 + 분기 3종 위젯 테스트 | `lib/screens/maintenance_screen.dart`, `update_required_screen.dart`, 순수 함수 `lib/startup/startup_plan.dart`. `test/app_startup_branch_test.dart` "점검 중이면 점검 화면이 뜬다" / "구버전이면 업데이트 화면 + 스토어 버튼이 뜬다" / "정상이면 3탭 홈과 배너 슬롯이 뜬다" + `test/startup/startup_plan_test.dart` 7개, `startup_controller_test.dart` 10개 |
| 3탭 뼈대 + 탭 바 아래 배너 슬롯 상시 예약 | `lib/screens/home_shell.dart`, `lib/widgets/ad_banner_slot.dart`. "정상이면 3탭 홈과 배너 슬롯이 뜬다"가 슬롯 높이(50+8)를 실제로 잰다, "탭을 옮기면 해당 탭이 보인다" |
| `.github/workflows/flutter-ci.yml`(ubuntu-latest, analyze + test) | 파일 커밋. 로컬에서 같은 명령 3개를 돌린 출력이 §2 |
| `flutter analyze` 0건 | §2 |
| `audit.native` 체크리스트 통과 기록 | §4 |
| README Flutter 절(상태 흐름·SDK 선택·테스트 경계 각 한 단락) | `README.md` "### 22. Flutter 앱(`mobile/`) — 상태 흐름·SDK 선택·테스트 경계" |

## 2. 실행한 명령과 출력

### Flutter 분석 (0건이어야 한다)

```
$ cd mobile && flutter analyze
Analyzing mobile...
No issues found! (ran in 5.5s)
```

### Flutter 포맷 (CI 와 같은 명령)

```
$ dart format --set-exit-if-changed lib test
Formatted 44 files (0 changed) in 0.09 seconds.
```

### Flutter 테스트

```
$ flutter test
00:19 +81: All tests passed!
```

81개 전부 신규다(`flutter create` 가 만든 `test/widget_test.dart` 는 지웠다).

| 파일 | 개수 | 내용 |
|---|---|---|
| `test/startup/app_version_test.dart` | 7 | 버전 비교 — 같음/높음/낮음, 숫자 비교(1.10 > 1.9), 마디 수 차이, 빌드 번호 무시, 못 읽으면 막지 않음 |
| `test/startup/startup_plan_test.dart` | 7 | 점검 우선, 메시지 없음, 점검+구버전 동시, 플랫폼별 최소 버전·스토어 링크, 링크 없음, 정상 |
| `test/startup/startup_controller_test.dart` | 10 | 세 분기 + 토큰 발급·복원·기기 언어 + 401 재발급 + 두 번째 401 + `/config` 실패 + retry |
| `test/api/api_models_test.dart` | 7 | `/config`·`/me/stats` 응답 파싱, null 필드, 모르는 언어 코드 무시, 기기 언어 매핑 |
| `test/api/dio_api_client_test.dart` | 9 | 세 엔드포인트의 경로·메서드·바디·Bearer 유무, 토큰 없을 때 네트워크 미접촉, 에러 매핑 5종 |
| `test/guest/guest_token_provider_test.dart` | 6 | 복원·없음·`replaceWith`·`clear`·변경 구독·동기 읽기 |
| `test/config/bootstrap_test.dart` | 5 | Firebase 초기화/스킵 2종, Sentry DSN 빈 값/있는 값 |
| `test/routing/startup_redirect_test.dart` | 6 | 로딩·에러·점검·업데이트·준비(탭 유지)·게이트에서 탭으로 |
| `test/theme/app_theme_test.dart` | 10 | OVERRIDES 토큰 값·brand 금지·배경·그림자 0·폰트·본문 스케일·모서리·터치 타깃·ThemeExtension |
| `test/app_startup_branch_test.dart` | 14 | 앱 트리 통째로: 3분기, 점검 기본 문구, 스토어 버튼 유무, 탭 이동, 내 기록 streak, en 로케일, 에러 카드+재시도, 게스트 발급, 다크 모드, 글자 1.3배, 접근성 레이블, iPad 폭 |

가짜로 바꾼 건 **`ApiClient` 와 `GuestTokenStore` 둘뿐**이다. Riverpod provider
그래프·`go_router`·테마·위젯·Dio 는 실제 코드가 그대로 돈다(Dio 는 가짜
`HttpClientAdapter` 로 전송 계층만 막는다 — 네트워크를 타지 않는다).

### Android 디버그 빌드 (Firebase 설정 파일 **없이**)

analyze·test 만으로는 "google-services.json 없이 빌드가 된다" 를 증명할 수 없어서
실제로 돌렸다. `JAVA_HOME` 은 이미 설치돼 있던 `openjdk@17` 을 가리켰다(설치 없음).

```
$ cd mobile && test ! -f android/app/google-services.json && echo "설정 파일 없음"
설정 파일 없음
$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                             94.2s
✓ Built build/app/outputs/flutter-apk/app-debug.apk
```

**이 과정에서 실제 버그를 하나 잡았다.** 처음 `flutter pub add` 가 고른
`sentry_flutter` 8.14.2 의 Android 모듈은 Kotlin language version 1.6 을 쓰는데,
`flutter create` 템플릿의 Kotlin 2.2.20 이 그걸 더 이상 지원하지 않아
`:sentry_flutter:compileDebugKotlin` 에서 빌드가 깨졌다
(`e: Language version 1.6 is no longer supported; please, use version 1.8 or greater.`).
`sentry_flutter` 를 `^9.30.1` 로 올려 해결했다(10.x 는 Dart ≥3.12 가 필요한데
이 환경은 3.10.7). `flutter analyze`·`flutter test` 만 돌렸으면 못 봤을 문제라,
빌드를 한 번 돌린 값을 했다.

### 백엔드 전체 테스트 스위트 (rebase 후)

이 티켓은 Python 코드를 바꾸지 않았지만 완료 조건이라 그대로 돌렸다.

```
$ TEST_DATABASE_URL=...chosung_daily_test_t22 \
  TEST_REDIS_URL=redis://127.0.0.1:6379/10 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t22_migrations \
  uv run pytest -q
........................................................................ [ 12%]
...
...................................................                      [100%]
555 passed in 372.72s (0:06:12)
```

**실패·skip·xfail 0건.**

### 린트 (백엔드)

```
$ uv run ruff check .
All checks passed!
```

`mobile/tool/make_placeholder_icon.py` 도 레포 루트 ruff 설정(`PL,RUF,SIM,PT`)에
걸린다 — 통과한다.

### 마이그레이션 head

이 티켓은 마이그레이션을 만들지 않았다. 확인만 했다.

```
$ FLASK_APP=wsgi.py DATABASE_URL=...chosung_daily_test_t22_migrations \
  ./scripts/check_migration_heads.sh
ff06a1bf5afc (head)
OK: Alembic head 1개
```

## 3. 폰트 출처 (코디네이터 요구)

- 출처: `https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip`
  (공식 릴리스, **v1.3.9**). 라이선스 OFL — 같은 zip 의 `LICENSE.txt` 를
  `mobile/assets/fonts/Pretendard-LICENSE.txt` 로 함께 커밋했다.
- 가변 폰트 한 파일(`PretendardVariable.ttf`, 6.7MB) 대신 **정적 3종**을 골랐다.
  Flutter 는 `fontWeight` 로 **에셋을 고르는** 방식이라, 가변 폰트 하나만 등록하면
  `TextStyle` 마다 `fontVariations` 로 wght 축을 직접 지정해야 한다. 정적 3종은
  합계 4.6MB 로 더 작기까지 하다. 코디네이터 답(`Variable 한 파일`)과 다른 선택이라
  여기에 근거를 남긴다.
- SHA-256:

```
2e91915fab54df71cc9598ebf608b2bdb54c6fe3c066ac61dff0bc44fca71cc7  Pretendard-Bold.otf
3ffbacde6ab8411f1d2db54bb9b1f0b3ee2a738932033722cf0388c06aed1c93  Pretendard-Regular.otf
c89bc43027dc7cde5726e96223376f8eec09302b2fc1f8147fd5b57cfc376118  Pretendard-SemiBold.otf
b04538c9abec39a3db75108cf0af0fd9c77032fe8aa2cf38345b4d250e98e38e  Pretendard-LICENSE.txt
```

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

**브라우저 도구·`impeccable detect` 는 쓰지 않는다**(HTML/CSS 용이다). 소스를
`reference/ios.md` + `reference/android.md` 기준으로 읽고 5개 축에 점수를 매겼다.
앱이 두 OS 로 나가므로 두 레퍼런스를 모두 적용했다.

| # | 축 | 점수 | 핵심 소견 |
|---|---|---|---|
| 1 | Accessibility | 3 | 탭·버튼 레이블 있음, 글자 1.3배 통과. StreakBadge 가 "연속 기록" 문맥 없이 숫자만 읽힘 |
| 2 | Performance | 3 | 시작 시 네트워크 2회 + 스켈레톤. 긴 목록·이미지 없음. 번들 폰트 4.6MB 가 가장 큰 자산 |
| 3 | Appearance & Theming | 4 | raw hex 가 `app_colors.dart` 한 파일에만 있고, 라이트/다크가 각각 1급 |
| 4 | Platform Conformance | 3 | Material 컴포넌트만 쓰고 시스템 back·edge-swipe 를 건드리지 않음. 아이콘은 Lucide(의도된 이탈) |
| 5 | Adaptivity | 2 | 태블릿에서도 하단 탭 바 — Material 은 expanded 폭에 navigation rail 을 요구한다(의도된 이탈) |
| **합계** | | **15/20** | **Good** (약한 축: Adaptivity) |

**Platform Conformance 판정: 통과.** 웹을 옮겨온 앱으로 읽히지 않는다. 전역 내비는
Material `NavigationBar` 3개(2~5 범위, 섹션만 — 액션 없음)이고, 모든 화면이
`SafeArea` 안에 그려지며 하단 탭 바 + 배너도 통째로 inset 위에 올린다. `PopScope` 나
커스텀 제스처로 시스템 Back / iOS edge-swipe back 을 막는 코드가 없다. 웹 모양
버튼·hover 의존 요소·커스텀 토글이 없고, Material 리플(누름 피드백)은 처음에
`NoSplash` 로 껐다가 **이 점검에서 되살렸다** — 안드로이드에서 "눌렸다" 를 알리는
유일한 신호다.

### 의도된 이탈 3개 (근거 문서 있음)

1. **아이콘이 Lucide** — SF Symbols/Material Symbols 가 아니다. OVERRIDES §8 이
   웹과 앱이 같은 아이콘 세트를 쓰도록 정했다(한 디자인 시스템을 두 표면이 공유).
   **P2**, 바꾸려면 OVERRIDES 를 먼저 고쳐야 한다.
2. **그림자 0 / tonal elevation 미사용** — OVERRIDES §4 "그림자 없음, 섹션 구분은
   헤어라인 1px 과 여백으로만". Material 의 tonal elevation 대신 `border` 토큰으로
   층을 표현한다. **P3**.
3. **Dynamic Color(Material You) 미사용** — 브랜드 색이 고정이고(OVERRIDES §2) 벽지
   색을 따라가면 "brand 는 디테일에만" 규칙이 깨진다. 정적 스킴만 쓴다. **P3**.

### 남은 결함 (뒤 티켓이 받는다)

| 심각도 | 위치 | 내용 | 받는 곳 |
|---|---|---|---|
| P2 | `lib/screens/home_shell.dart` | 태블릿(expanded 폭)에서도 하단 탭 바. `android.md` 는 navigation rail 을 요구한다. 지금은 스펙 §B.19("iPad 중앙 정렬 최대 600px")를 따랐다 | 스펙 판단 필요 — 코디네이터/티켓 25 |
| P3 | `lib/screens/today_tab.dart` | `StreakBadge` 가 "3일" 만 읽힌다. `Semantics(label: '연속 기록 3일')` 필요 | 티켓 23(홈 화면) |
| P3 | `lib/widgets/skeleton_box.dart` | 스켈레톤이 스크린 리더에 노출된다. `ExcludeSemantics` 필요 | 티켓 23·25 |
| P3 | 전역 | Reduce Motion 대응 코드가 아직 없다(커스텀 모션 자체가 없어서 지금은 위반이 아니다). 타일 뒤집기 350ms 가 들어오는 순간 필요 | 티켓 23 |
| P2 | — | **시뮬레이터·에뮬레이터 스크린샷 없음**(아래) | 티켓 32·34 실기기 체크리스트 |

### 돌리지 못한 것 (숨기지 않는다)

- **시뮬레이터/에뮬레이터 캡처 없음.** `audit.native` 의 "Verifying the build" 는
  `xcrun simctl io booted screenshot` / `adb exec-out screencap` 을 요구하는데, 이
  세션은 기기·시뮬레이터를 띄우지 않았다(워커 환경에 부팅된 기기가 없고,
  `flutter devices` 는 네트워크 상의 실기기만 보였다 — 실기기 설치는 티켓 범위 밖).
  대신 위젯 테스트로 다크 모드·글자 1.3배·iPad 폭(1668×2388)·접근성 레이블을 코드
  수준에서 확인했다. **실기기 캡처는 티켓 32·34 의 사람 체크리스트로 넘긴다.**
- **iOS 빌드 미실행.** `flutter build ios --simulator` 는 CocoaPods 설치·Xcode
  빌드가 필요해 돌리지 않았다. Android 디버그 빌드는 실제로 돌렸고(위 §2) 그 과정에서
  `sentry_flutter` 버전 문제를 잡았다. iOS 쪽 동일 확인은 티켓 32 가 받는다.
- **`impeccable detect` 미실행** — 네이티브 코드에는 적용되지 않는다
  (`audit.native.md`: "no browser tooling or `impeccable detect` applies").
  웹(`web/`)은 이 티켓이 건드리지 않았다.

## 5. 디자인 파일과 다르게 구현한 것

- **S7 점검/강제 업데이트 화면은 목업이 없다**(SCREENS "목업 파일 매핑" 표가
  "목업 없음 — 명세대로 구현"). SCREENS 의 "아이콘 + 제목 + 예상 시각 / 스토어 버튼"
  과 OVERRIDES 토큰만으로 만들었다. 스토어 링크가 null 이면(스토어 등록 전)
  버튼을 그리지 않는다 — 누르면 아무 일도 안 하는 버튼보다 낫다.
- **3탭 뼈대의 본문은 스켈레톤**이다. S1/S3 의 실제 구성(PuzzleBoard·HintCard·
  GuessInput·LeaderboardRow)은 티켓 23·25 가 채운다. S4 상단 3칸(현재/최고/누적)만
  시작할 때 읽은 `/me/stats` 로 실제 값을 보여준다 — 그 호출을 "토큰 확인용" 으로만
  쓰고 버리면 사용자에게 보이는 게 없다.
- **활성 탭 표시는 brand 밑줄**(OVERRIDES §2 "활성 탭 밑줄")이고 Material 의 기본
  indicator(면 채움)는 투명으로 껐다 — brand 면 채움 금지 규칙 때문이다.

## 6. 공유 파일에 더한 것 (티켓 공통 규칙)

- `README.md` "기술 스택" 에 한 줄, "설계 판단" 끝에 `### 22.` 소제목 하나.
  API 표는 건드리지 않았다 — 이 티켓은 새 엔드포인트를 만들지 않는다.
- `docs/RELEASE.md` 끝에 `### 22.` 절(사람 체크리스트).
- `PRODUCT.md` "Platform" 절 메모(위 "판단 1").
- `.env.example` 은 건드리지 않았다 — 서버 설정값을 더하지 않는다.
  앱 쪽 주입값(`API_BASE_URL`, `SENTRY_DSN`)은 `--dart-define` 이라 `.env` 가 아니고,
  `mobile/README.md` 와 `docs/RELEASE.md` "22." 에 이름만 적었다.
- 스펙 "미정 항목" 은 건드리지 않았다 — 이 티켓에서 새로 미룬 결정이 없다.

## 수정 라운드 1

최종 리뷰(라운드 1, FAIL)의 **BLOCKER 1 / MAJOR 1 / MINOR 1** 을 전부 고쳤다.
"리뷰어가 틀렸다" 로 넘긴 항목은 없다. 커밋 1개(`fix(22): 수정 라운드 1 …`),
로컬 `main` **abf3e9a**(티켓 12 머지) 위로 `git rebase main` 완료 — 충돌 없음,
작업 트리 clean.

### D-22-1 (BLOCKER) — 국제화 초기화 누락으로 실제 앱 시작 실패

**재현(수정 전).** 리뷰의 재현 코드를 그대로 레포 밖에 두고 돌렸다.

```
$ flutter test --no-pub /tmp/t22_startup_review_test.dart --reporter expanded
  Expected: null
    Actual: LateError:<LateInitializationError: Field '_deviceLocale@1510168148' has not been initialized.>
00:00 +0 -1: Some tests failed.
```

**원인.** 설치된 `easy_localization 3.0.8` 의
`EasyLocalizationController` 는 기기 언어를 `static late Locale _deviceLocale`
에 담아두고, **`initEasyLocation()`(= `EasyLocalization.ensureInitialized()`)
에서만** 그 값을 채운다
(`~/.pub-cache/.../easy_localization-3.0.8/lib/src/easy_localization_controller.dart:11,:213`).
`startLocale` 이 null 이고 저장된 언어도 없으면 생성자가 바로 그 필드를 읽는다
(같은 파일 `:57-62`). 그래서 `main` 이 초기화를 부르지 않으면 첫 빌드에서 죽는다.
`saveLocale: false` 는 선택 언어 **저장**만 끄는 옵션이라 이 초기화를 대신하지
않는다 — `lib/app.dart` 의 "`ensureInitialized` 도 필요 없다" 주석이 틀렸다.

**수정.** 증상(테스트가 언어를 고정해서 통과하던 것)이 아니라 시작 경로를 고친다.

- `mobile/lib/l10n/localization_bootstrap.dart` 신규 — `initializeLocalization()`
  (`EasyLocalization.ensureInitialized()` 래퍼 + 왜 필요한지 주석).
- `mobile/lib/main.dart` — Firebase 다음, `runApp` 앞에서 그 함수를 `await`.
  main 본문은 `bootstrapChosungApp({initializeFirebaseFn, initializeLocalizationFn, start})`
  로 빼서 **시작 순서 자체를 테스트 대상으로** 만들었다.
- `mobile/lib/app.dart` — 틀린 주석을 실제 동작으로 고쳤다(초기화가 먼저 와야 한다).

**고정한 테스트.** 위젯 테스트가 이 결함을 못 본 이유(모두 `startLocale` 을
주입한다)를 그대로 메운다.

- `test/l10n/localization_bootstrap_test.dart`
  - `기기 언어를 강제하지 않는 실제 시작 경로가 예외 없이 뜬다` — 리뷰의 재현과
    같은 구성(`AppLocalizationScope(child: …)`, `startLocale` 없음)을 **앱이 실제로
    하는 초기화 뒤에** 띄우고, 고른 언어가 지원 언어 중 하나인지 본다.
  - `시작 순서: Firebase → 국제화 초기화 → runApp` — `bootstrapChosungApp` 에
    가짜 초기화를 넣어 호출 순서를 확인한다.
- `test/app_startup_branch_test.dart` — `언어를 고정하지 않는 실제 시작 경로로도
  홈이 뜬다`(`locale: null`). 가짜 `ApiClient` 만 두고 앱 트리를 통째로 띄운다.

**증명(수정 후).**

```
$ flutter test --no-pub test/l10n/localization_bootstrap_test.dart --reporter expanded
00:00 +0: 기기 언어를 강제하지 않는 실제 시작 경로가 예외 없이 뜬다
00:00 +1: 시작 순서: Firebase → 국제화 초기화 → runApp
00:00 +2: All tests passed!

# 순서 테스트가 회귀를 실제로 잡는지 — main 에서 초기화 한 줄만 주석 처리하고
$ flutter test --no-pub test/l10n/localization_bootstrap_test.dart
  Expected: ['firebase', 'localization', 'runApp']
    Actual: ['firebase', 'runApp']
00:02 +1 -1: Some tests failed.      # 주석을 되돌림
```

**리뷰 재현 코드를 그대로 다시 돌리면 여전히 실패한다 — 의도된 결과다.** 그
스니펫은 `AppLocalizationScope` 만 띄우고 앱의 초기화 단계를 건너뛴다.
`easy_localization` 은 그 초기화를 `main` 에서 하도록 문서화돼 있고
(`easy_localization_app.dart:158` "ensureInitialized needs to be called in main"),
위젯 안에서 `await` 하려면 첫 프레임을 빈 화면으로 내보내야 해서(네이티브
스플래시가 그 프레임에 사라진다) 시작 화면이 깜빡인다. 그래서 초기화는 `main`
에 두고, **같은 재현을 "앱이 하는 초기화 + 언어 고정 없음" 으로 바꿔** 위 두
테스트로 고정했다. 초기화를 빼먹는 회귀는 순서 테스트가 잡는다.

### D-22-2 (MAJOR) — iOS 최소 버전이 Firebase 의존성과 호환되지 않음

**재현·원인(수정 전).** 리뷰와 같은 방법(설치된 podspec + CocoaPods 판정).

```
$ rg -n 'IPHONEOS_DEPLOYMENT_TARGET' mobile/ios/Runner.xcodeproj/project.pbxproj
349,476,527:  IPHONEOS_DEPLOYMENT_TARGET = 13.0;
$ grep -n deployment_target ~/.pub-cache/.../firebase_core-4.15.0/ios/firebase_core.podspec
30:  s.ios.deployment_target = '15.0'      # firebase_analytics-12.6.0 도 15.0

$ ruby -e '... Pod::Platform.new(:ios, v).supports?(required) ...'
app=iOS 13.0, dependency=iOS 15.0, compatible=false
app=iOS 15.0, dependency=iOS 15.0, compatible=true
```

Podfile 의 `platform` 선언은 주석이었고(`# platform :ios, '13.0'`), Xcode 세
구성과 `AppFrameworkInfo.plist` 는 13.0 이었다. Firebase 설정 파일이 없어도
네이티브 플러그인은 설치 대상이라 런타임 스킵으로 가려지지 않는다.

**수정.** 프로젝트의 iOS 플랫폼을 **15.0** 으로 올리고, 세 군데가 같은 값을
갖도록 한다 — `project.pbxproj` Debug/Release/Profile 3곳, Podfile 의
`platform :ios, '15.0'`(주석 해제 + 이유), `Flutter/AppFrameworkInfo.plist` 의
`MinimumOSVersion`. 스펙·티켓에 최소 OS 버전 지정이 없어 의존성이 요구하는
값으로 맞췄고, 근거는 README `### 22.` "SDK 선택" 에 한 문장으로 남겼다.

**고정한 테스트.** `test/config/ios_project_test.dart`
`iOS 최소 버전 — 프로젝트·Podfile·앱 프레임워크가 한 값이고 pod 요구치를 만족한다`:
세 설정을 읽어 값이 하나인지 보고, `.dart_tool/package_config.json` 으로 풀린
패키지들의 podspec(`s.ios.deployment_target` / `s.platform = :ios, '…'`)을 모두
읽어 그 최대치 이상인지 확인한다. Dart analyze·위젯 테스트·Android 빌드는 이
설정을 보지 않으므로 설정 파일을 직접 읽는 테스트로 지킨다.

```
# 수정 전(빨강)
  Expected: an object with length of <1>
    Actual: Set:['13.0', null]        # Podfile 선언이 주석이라 null
# 수정 후
$ flutter test --no-pub test/config/ios_project_test.dart --reporter expanded
00:00 +1: 한국어 앱 이름 …
00:00 +2: All tests passed!
```

### D-22-3 (MINOR) — 한국어 iOS 앱 이름 파일이 번들에 포함되지 않음

**원인.** `ko.lproj/InfoPlist.strings` 파일만 있고 Runner 타깃에 연결돼 있지
않았다(`rg 'InfoPlist.strings|ko.lproj' project.pbxproj` → 일치 없음). 파일을
디렉터리에 두는 것만으로는 번들에 들어가지 않는다.

**수정.** `project.pbxproj` 에 직접 넣었다(손으로 할 일로 남기지 않는다).

- `PBXFileReference` `ko` → `ko.lproj/InfoPlist.strings`
- `PBXVariantGroup` `InfoPlist.strings`(자식 = 위 참조) + Runner 그룹에 추가
- `PBXBuildFile` → Runner 의 `PBXResourcesBuildPhase` 에 등록
- `knownRegions` 에 `ko` 추가
- `docs/RELEASE.md` `### 22.` 의 "Xcode 에서 ko.lproj 를 추가" 체크박스를 빼고,
  "사람이 할 일이 아니다 — 보이는지만 확인" 으로 바꿨다. 리소스 파일 주석도 고쳤다.

**증명.** 파일 문법(`plutil -lint`)과 실제 구조(CocoaPods 의 `xcodeproj` 1.27.0)
둘 다 확인했다.

```
$ plutil -lint mobile/ios/Runner.xcodeproj/project.pbxproj
Runner.xcodeproj/project.pbxproj: OK

$ ruby -e '... Xcodeproj::Project.open("Runner.xcodeproj") ...'
resource: LaunchScreen.storyboard (PBXVariantGroup) children=Base:Base.lproj/LaunchScreen.storyboard
resource: AppFrameworkInfo.plist (PBXFileReference) children=Flutter/AppFrameworkInfo.plist
resource: Assets.xcassets (PBXFileReference) children=Assets.xcassets
resource: Main.storyboard (PBXVariantGroup) children=Base:Base.lproj/Main.storyboard
resource: InfoPlist.strings (PBXVariantGroup) children=ko:ko.lproj/InfoPlist.strings
knownRegions=["en", "Base", "ko"]
project Debug/Release/Profile: 15.0
```

**고정한 테스트.** `test/config/ios_project_test.dart`
`한국어 앱 이름 — ko.lproj/InfoPlist.strings 가 Runner 타깃 Resources 에 들어 있다`:
파일 참조 → variant group → build file → Resources 단계까지 ID 사슬을 따라가고
`knownRegions` 에 `ko` 가 있는지 본다(주석 문자열이 아니라 구조를 본다).
수정 전에는 파일 참조 자체가 없어 빨강이었다.

### 리뷰의 "테스트 경계" 지적 (결함 미집계 항목)

리뷰가 "증거 문서의 설명이 과장" 이라고 지적한 한 줄
(`Dio 가 매 요청마다 토큰을 읽는 것을 테스트한다`)을 **테스트를 더해 사실로**
만들었다: `test/api/dio_api_client_test.dart` 의
`같은 클라이언트가 요청마다 토큰을 다시 읽는다` 가 같은 Dio 인스턴스로 두 번
호출하면서 중간에 토큰을 바꾸고 `Authorization` 헤더 두 개를 비교한다
(`['Bearer first-token', 'Bearer second-token']`). 위 §3 표의 해당 문구도
새 테스트 이름으로 고쳤다.

### 미수정 MINOR

없다. 리뷰의 MINOR(D-22-3)는 고쳤고, 리뷰가 결함으로 집계하지 않은 지적도
위와 같이 처리했다. 리뷰가 남긴 **검증 한계**(iOS 전체 빌드·실기기·시뮬레이터
캡처 없음)는 이 라운드에서도 그대로다 — `pod install`/Xcode 빌드와 실기기는
티켓 32·34 의 사람 체크리스트다. iOS 쪽은 위처럼 podspec·CocoaPods 판정과
프로젝트 파일 구조로만 확인했다.

### 라운드 1 수정 후 전체 재검증 (로컬 `main` abf3e9a 위에서)

| 명령 | 결과 |
|---|---|
| `flutter analyze` (mobile/) | `No issues found!` (3.0s) |
| `dart format --output=none --set-exit-if-changed .` | `Formatted 47 files (0 changed)` |
| `flutter test --no-pub` (mobile/) | `All tests passed!` — **87 passed** (리뷰 시점 81 → +6) |
| `uv run ruff check .` (루트) | `All checks passed!` |
| `TEST_DATABASE_URL=…/chosung_daily_test_t22 TEST_REDIS_URL=redis://localhost:6379/10 uv run pytest -q` | **668 passed** in 365.98s |
| `uv run flask db heads` | `a5bab2f58a7b (head)` — 1개 |
| `git diff --check` / `git status --short` | 출력 없음(clean), `main` 위로 rebase 됨 |

Python 코드·마이그레이션은 이 라운드에서도 한 줄도 바꾸지 않았다(pytest 는
rebase 로 들어온 `main`(티켓 12 머지)과 함께 돌려 확인만 했다). 테스트는 이
티켓 전용 자원(DB `chosung_daily_test_t22`, Redis DB 10)만 썼고 공용 테스트 DB·
다른 워커의 자원은 건드리지 않았다. 외부 서비스 호출·배포·`git push` 없음,
시크릿 값을 적지 않았다. `review/impl-review-22.md` 는 수정하지 않았다.

**패키지 변경 1건:** `shared_preferences` 를 **dev_dependencies** 에만 더했다
(이미 `easy_localization` 의 전이 의존성). 앱 코드는 쓰지 않는다 — 초기화가
내부에서 읽는 저장소를 테스트에서 `setMockInitialValues({})` 로 비워두기
위해서다. 없으면 `flutter test` 가 그 플랫폼 채널 응답을 기다리며 멈춘다
(직접 확인: 4분 넘게 출력 없음 → 강제 종료).
