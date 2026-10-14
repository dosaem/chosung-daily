# 티켓 34 구현 증거 — 앱 배포 워크플로·fastlane·서명 (`mobile/` 기준)

- 브랜치: `dosaem/t34-app-deploy-workflows-signing`, 로컬 `main` **008a35a**
  (티켓 22 머지) 위로 `git rebase main` — 아래 §6
- Flutter 3.38.6 / Dart 3.10.7, JDK 17(`/opt/homebrew/opt/openjdk@17`),
  Xcode(기본), fastlane 2.x, apksigner 36.1.0 — 전부 로컬에 이미 있던 것(설치 없음)
- 백엔드 테스트 자원(다른 워커와 분리): DB `chosung_daily_test_t34`, Redis DB **8**,
  마이그레이션 왕복용 `chosung_daily_test_t34_migrations`
  (`TEST_DATABASE_URL`·`TEST_REDIS_URL`·`TEST_MIGRATION_DATABASE_URL`).
  공용 `chosung_daily_test`·Redis 1 과 다른 워커 자원은 건드리지 않았다. 이 티켓은
  Python 애플리케이션 코드·마이그레이션을 한 줄도 바꾸지 않았다(새 테스트 1개만 추가).
- **외부 서비스 호출 0건.** Firebase·Apple·Google·Play·AdMob·Slack·NAS 어디에도
  붙지 않았고 `git push` 도 없다. 네트워크를 탄 것은 `flutter pub get`(pub.dev)과
  `pod install`(CocoaPods 스펙 저장소)뿐이다. 스토어 업로드·match 조회는 D2 산출물이
  필요해 실행하지 않았다(§5 에 멈추는 지점을 적었다).
- **자원 사용 중 한 가지 이탈.** 전체 스위트가 내 Redis DB 8 을 쓰고 있는 동안 "테스트
  1개당 체감 시간" 을 재려고 작은 파일 2개(`test_mask.py`, `test_guess_flow.py`)를 내
  `chosung_daily_test_t34_migrations` DB + **Redis DB 9** 로 돌렸다. conftest 가 Redis
  를 `flushdb` 하므로 9번을 쓰는 워커가 있었다면 영향을 줄 수 있었다(직후 확인한
  `redis-cli info keyspace` 는 전 DB 가 비어 있어 흔적은 없었다). 이후로는 8번만 썼다.
- **시크릿 값은 어떤 파일·로그·이 문서에도 없다.** 이름과 경로만 적었다
  (`docs/RELEASE.md` "### 34." 의 secrets/variables 표). `.env`, `.env.prod*` 는 열지
  않았다. §3 의 서명 검증에 쓴 임시 keystore 는 `openssl rand` 로 만든 비밀번호를
  셸 변수로만 쓰고 검증 직후 keystore·`key.properties` 를 함께 지웠다(둘 다
  gitignore 대상이라 커밋 후보에도 올라오지 않았다 — `git status` 로 확인).

## 1. 체크박스별 근거

| 티켓 체크박스 | 증명 |
|---|---|
| BASELINE 복사·치환 (`flutter.yml` `working-directory: mobile`, fastlane, ExportOptions, build.gradle.kts 서명·심볼, key.properties.example) | `tests/test_app_deploy_workflow.py::test_copied_files_have_no_other_app_identifiers`(10파일), `::test_identifiers_are_substituted`, `::test_export_options_points_at_the_match_profile_of_this_bundle`(plist 파싱), `::test_match_uses_the_shared_certificate_repository`, `::test_flutter_commands_run_inside_the_mobile_directory`, `::test_action_inputs_use_workspace_relative_mobile_paths`, `::test_flutter_version_matches_the_ci_workflow` + §2 의 `ruby -c`·`fastlane lanes`·`plutil -lint` |
| AAB 스텝의 strip false-positive 처리 유지 | `::test_aab_step_keeps_the_strip_false_positive_handling` + **§4 에서 실제 재현**: `flutter build appbundle --release` 가 exit 1, AAB 는 정상 생성, 워크플로 스텝 로직을 그대로 돌려 exit 0 + `AAB sanity OK` |
| `app_privacy_details.json` 재작성(게스트 식별자·이메일·시도 기록·구독·광고 ID·진단) | `::test_privacy_details_lists_exactly_what_the_app_collects`, `::test_privacy_details_entries_use_valid_asc_values`, `::test_account_bound_data_is_declared_as_linked_to_the_user`, `::test_advertising_identifiers_are_declared_as_tracking`, `::test_diagnostics_are_declared_as_not_linked` + §7 의 `/privacy` 1절 대조표 |
| `--dart-define=API_BASE_URL`(develop→8090 인스턴스, main→prod) | `::test_api_base_url_comes_from_the_branch_target`, `::test_build_stops_when_the_api_base_url_is_not_configured`, `::test_every_build_passes_the_dart_defines`, `::test_api_base_url_define_matches_the_app_constant` + **§3 에서 실제 확인**: release APK 의 `libapp.so` 에 넘긴 값이 들어 있다 |
| 광고 ID·`serverClientId` dart-define 전달 | `::test_dart_defines_cover_api_ads_and_login`(5개 × 2잡), `::test_ad_unit_ids_are_platform_specific`, `::test_dart_define_names_are_documented` |
| flutter-ci.yml 과 분리 유지, 러너 `self-hosted` | `::test_analyze_and_test_stay_in_the_ci_workflow`, `::test_distribute_workflow_does_not_duplicate_analyze_or_test`, `::test_distribute_workflow_runs_on_the_self_hosted_runner`, `::test_distribute_workflow_triggers_on_the_two_branches`. `flutter-ci.yml` 은 한 글자도 바꾸지 않았다(`git diff main..HEAD -- .github/workflows/flutter-ci.yml` 비어 있음) |
| 필요한 secrets·match 레포·App Distribution 그룹을 `docs/RELEASE.md` 자기 절에 표로 | `docs/RELEASE.md` "### 34." (secrets 13개 / variables 9개 / dart-define 6개 표 + match 레포 + 그룹 `testers`). `::test_workflow_secrets_and_variables_are_documented`(워크플로가 쓰는 이름 ⊆ 표), `::test_documented_secrets_cover_signing_stores_and_firebase`, `::test_release_doc_names_the_match_repository_and_tester_group` |
| 로컬 확인: D0·D2 없이 `flutter build apk --debug` 성공(Firebase 스킵 경로) | **§3 실행 출력** — 설정 파일 3개가 없는 상태에서 `✓ Built build/app/outputs/flutter-apk/app-debug.apk` |
| `--release`·`build ipa` 는 D0·D2 전제로 적고 RELEASE.md 사람 체크로, 실제 푸시·업로드는 사람 | `docs/RELEASE.md` "### 34." 의 "D2. 앱 배포 — 사람이 해야 하는 일" 체크리스트 7항목, `::test_release_doc_separates_what_only_a_human_can_do`. 실제 업로드·푸시는 하지 않았다(§5) |
| 서명 블록이 실제로 동작 | **§3** — 임시 keystore + `key.properties` 로 release APK 를 빌드해 `apksigner verify --print-certs` 가 그 인증서를 보여준다. keystore 가 없으면 `Android Debug` 로 떨어진다(두 경우 모두 실측) |
| `run:` 블록이 실제로 도는 셸인가 | `::test_every_run_step_is_valid_shell`(17개 스텝 `bash -n`) |
| 심볼 블록(`debugSymbolLevel = "FULL"`) | **§4** — AAB 의 `BUNDLE-METADATA/com.android.tools.build.debugsymbols/<abi>/*.dbg` 목록 |

## 2. 정적 검증 (파일이 문법적으로 유효한가)

```
$ ruby -c mobile/android/fastlane/Fastfile mobile/ios/fastlane/Fastfile \
        mobile/ios/fastlane/Appfile mobile/ios/fastlane/Matchfile mobile/android/fastlane/Appfile
Syntax OK   (5개 모두)

$ plutil -lint mobile/ios/ExportOptions.plist
mobile/ios/ExportOptions.plist: OK

$ cd mobile/ios && fastlane lanes
----- fastlane ios beta      TestFlight 에 올린다
----- fastlane ios release   App Store 에 올린다 (심사 제출은 사람)

$ cd mobile/android && fastlane lanes
----- fastlane android beta     Play 내부 테스트 트랙에 올린다 (초안)
----- fastlane android release  Play 프로덕션에 올린다 (초안 — 출시 버튼은 사람)
```

`flutter.yml` 은 PyYAML 로 파싱해서 테스트가 잡·스텝 단위로 읽고, 모든 `run:` 블록을
`bash -n` 으로 문법 검사한다(`::test_every_run_step_is_valid_shell`). 17개 스텝 전부
OK — AAB 스텝의 python heredoc 들여쓰기처럼 "푸시해야 알 수 있는" 사고를 여기서 잡는다.

```
setup    env                                           OK
android  Build AAB (prod)                              OK
ios      Setup signing via fastlane match              OK
...      (run: 이 있는 17개 스텝 전부)                      ALL OK
```

`actionlint` 는 이 맥에 없어서 돌리지 못했다 — 설치가 필요한 도구라 시도하지 않았다.
그래서 **GitHub 식(expression) 의 의미는 로컬에서 검증되지 않는다.** 특히 잡 수준
`env:` 에서 `needs`·`vars`·`secrets` 컨텍스트를 쓰는 것은 GitHub 문서의 컨텍스트
가용성 표에 근거한 것이고(`jobs.<job_id>.env` → github, needs, strategy, matrix, vars,
secrets, inputs), 실제 확인은 사람이 `develop` 에 처음 푸시할 때 난다(RELEASE.md
"### 34." 의 마지막 체크 항목이 그 리허설이다).

## 3. Android 빌드 3종 (실제 실행)

### 3.1 D0·D2 없이 디버그 빌드 — 티켓의 워커 조건

```
$ ls mobile/android/app/google-services.json mobile/ios/Runner/GoogleService-Info.plist mobile/android/key.properties
ls: mobile/android/app/google-services.json: No such file or directory
ls: mobile/android/key.properties: No such file or directory
ls: mobile/ios/Runner/GoogleService-Info.plist: No such file or directory

$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --debug
Running Gradle task 'assembleDebug'...                            119.8s
✓ Built build/app/outputs/flutter-apk/app-debug.apk
```

Firebase 설정 파일이 없으니 Gradle 이 google-services 플러그인을 건너뛴 경로다
(`mobile/android/app/build.gradle.kts` 하단, 티켓 22 가 넣은 분기 — 그대로 유지).

### 3.2 keystore 없이 release 빌드 — 디버그 키 폴백

```
$ JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build apk --release \
    --dart-define=API_BASE_URL=https://example.invalid/api/v1
Running Gradle task 'assembleRelease'...                          429.3s
✓ Built build/app/outputs/flutter-apk/app-release.apk (56.9MB)

$ apksigner verify --print-certs build/app/outputs/flutter-apk/app-release.apk
Signer #1 certificate DN: C=US, O=Android, CN=Android Debug
```

`key.properties` 가 없으면 `signingConfigs.findByName("release")` 가 null 이라
디버그 서명으로 떨어진다 — 그래서 keystore 가 없는 로컬·새 클론에서도 release
빌드가 돈다. 스토어로 가는 빌드가 이 경로로 새지 않는 이유는 워크플로가
`KEYSTORE_BASE64` 가 없으면 **빌드 전에 멈추기** 때문이다(§5).

**dart-define 이 바이너리까지 갔는지**도 같은 APK 로 확인했다.

```
$ unzip -p build/app/outputs/flutter-apk/app-release.apk lib/arm64-v8a/libapp.so > /tmp/libapp.so
$ strings /tmp/libapp.so | grep -o "example.invalid[^ ]*" | sort -u
example.invalid/api/v1
```

### 3.3 keystore 가 있을 때 release 빌드 — 업로드 키로 서명

임시 keystore(`CN=t34 temp signing test`, 유효기간 30일, 비밀번호는 `openssl rand`)를
**워크플로가 쓰는 자리와 같은 경로**(`mobile/android/app/upload-keystore.jks`)에 두고
`mobile/android/key.properties` 를 워크플로의 `Create key.properties` 스텝과 같은 4줄로
만들었다.

```
$ keytool -genkeypair -keystore android/app/upload-keystore.jks -alias upload ... (출력 생략)
$ flutter build apk --release --dart-define=API_BASE_URL=https://example.invalid/api/v1
Running Gradle task 'assembleRelease'...                           10.4s
✓ Built build/app/outputs/flutter-apk/app-release.apk (56.9MB)

$ apksigner verify --print-certs build/app/outputs/flutter-apk/app-release.apk
Signer #1 certificate DN: CN=t34 temp signing test, O=chosung-daily, C=KR
```

검증 후 `rm -f android/key.properties android/app/upload-keystore.jks` 로 지웠고
`git status` 에 남은 흔적이 없다(둘 다 `mobile/android/.gitignore` 대상).

## 4. AAB — strip 오탐 재현과 워크플로 스텝 검증

`debugSymbolLevel = "FULL"` 을 넣은 상태에서 BASELINE 이 말하는 오탐이 **이 레포에서도
그대로 난다**는 것을 먼저 확인했다.

```
$ flutter build appbundle --release --dart-define=...
Running Gradle task 'bundleRelease'...                             34.1s
Release app bundle failed to strip debug symbols from native libraries.
...
$ echo "flutter exit=$?"
flutter exit=1
```

그다음 워크플로 `Build AAB (prod)` 스텝의 셸을 **그대로** 돌렸다(`bash -e`).

```
flutter exited nonzero (known strip false-positive with debugSymbolLevel=FULL)
AAB sanity OK: delivered libs are stripped
=== step exit=0
```

즉 ① flutter tool 의 exit 1 은 삼키지만 ② AAB 파일 존재와 ③ 배포 `libapp.so` 가
실제로 스트립됐는지는 확인한다. 진짜 스트립 실패면 `libapp.so is NOT stripped` 로
스텝이 죽는다.

심볼이 AAB 에 들어갔는지:

```
$ unzip -l build/app/outputs/bundle/release/app-release.aab | grep BUNDLE-METADATA
   339240  BUNDLE-METADATA/com.android.tools.build.debugsymbols/arm64-v8a/libdartjni.so.dbg
133121624  BUNDLE-METADATA/com.android.tools.build.debugsymbols/arm64-v8a/libflutter.so.dbg
   255344  BUNDLE-METADATA/com.android.tools.build.debugsymbols/armeabi-v7a/libdartjni.so.dbg
123223300  BUNDLE-METADATA/com.android.tools.build.debugsymbols/armeabi-v7a/libflutter.so.dbg
   326552  BUNDLE-METADATA/com.android.tools.build.debugsymbols/x86_64/libdartjni.so.dbg
132570312  BUNDLE-METADATA/com.android.tools.build.debugsymbols/x86_64/libflutter.so.dbg
```

## 5. iOS — 어디까지 확인했고 어디서 멈췄는가

**확인한 것**: 서명 없이 기기용 release 빌드가 끝까지 돈다(= Xcode 프로젝트·Podfile·
dart-define 경로는 정상).

```
$ flutter build ios --release --no-codesign --dart-define=API_BASE_URL=https://example.invalid/api/v1
Building com.dosaem.chosung for device (ios-release)...
Running pod install...                                           2,929ms
Xcode build done.                                           90.5s
✓ Built build/ios/iphoneos/Runner.app (31.2MB)
```

`pod install` 이 바꾼 `ios/Runner.xcodeproj/project.pbxproj`·
`Runner.xcworkspace/contents.xcworkspacedata` 와 새로 생긴 `ios/Podfile.lock` 은
**되돌렸다**(티켓 22 와 같은 처리 — CocoaPods 통합 산출물은 커밋하지 않는다).

**안 한 것(D2 전제라 할 수 없음)**:

- `fastlane match appstore --readonly` — `match-certs` 레포 접근과 `MATCH_PASSWORD`
  가 필요하다. 인증서가 없으면 다음 단계(아카이브 서명)가 반드시 실패한다.
- `flutter build ipa --export-options-plist=ios/ExportOptions.plist` — ExportOptions
  가 가리키는 `match AppStore com.dosaem.chosung` 프로파일이 로컬에 없다.
- TestFlight·Play·App Distribution 업로드, `develop`/`main` 푸시 — 전부 사람(D2·D3).
  `docs/RELEASE.md` "### 34." 의 체크리스트로 넘겼다.

## 6. 테스트·린트 전체 실행

```
$ cd mobile && dart format --set-exit-if-changed lib test
Formatted 47 files (0 changed) in 0.12 seconds.    (exit 0)

$ flutter analyze
No issues found! (ran in 4.1s)

$ flutter test
00:11 +87: All tests passed!      # rebase 후 재실행

$ uv run ruff check .
All checks passed!

$ uv run pytest -q    # TEST_DATABASE_URL=...chosung_daily_test_t34, TEST_REDIS_URL=redis://localhost:6379/8,
                      # TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t34_migrations
814 passed in 621.03s (0:10:21)
```

**1차 실행은 89건이 error 였다 — 숨기지 않고 적는다.** 원인과 처리:

```
$ uv run pytest -q    # 1차 (같은 명령)
ERROR tests/test_cli.py::... - sqlalchemy.exc.OperationalError
...  (총 89건, 알파벳 순 test_account_service ~ test_csrf 구간에 몰림)
727 passed, 89 errors in 1156.27s (0:19:16)
```

전부 `app` 픽스처가 DB 에 붙는 단계의 `sqlalchemy.exc.OperationalError` 였고, 테스트
코드가 아니라 **로컬 MySQL 의 연결 한계**였다. 그 시점에 같은 컨테이너에 다른 워커
5개(t13·t14·t17·t24·메인 체크아웃)가 동시에 붙어 있었다.

```
$ docker exec chosung-daily-mysql-1 mysql -e "SHOW VARIABLES LIKE 'max_connections'"
max_connections  500
$ ... SELECT db, COUNT(*) ... GROUP BY db       # 1차 실행 중 실측
chosung_daily_test_t34  60 / t14 64 / t13 68 / t24 55 / chosung_daily_test 31 / t17 14 ...
```

같은 파일을 단독으로 돌리면 통과한다(원인이 이 티켓 변경이 아니라는 확인).

```
$ uv run pytest tests/test_csrf.py -q
10 passed in 27.89s
```

그리고 위의 재실행에서 **814개 전부 통과**했다. 공용 자원 경합이라 재현은 타이밍에
달려 있다 — 워커를 동시에 여러 개 돌릴 때 `max_connections` 가 한계라는 점만 기록해 둔다
(이 티켓에서 고칠 범위는 아니다. conftest 의 엔진 정리나 `max_connections` 상향은
백엔드/인프라 쪽 판단이 필요하다).

마이그레이션은 만들지 않았다 — `flask db heads` 는 이 티켓 때문에 달라지지 않는다
(Python 모델·`migrations/` 변경 0건, `git diff --stat main..HEAD` 참고).

`git rebase main` / 작업 트리 상태:

```
$ git rebase main   # main = 1e764da (티켓 15 머지)
Successfully rebased and updated refs/heads/dosaem/t34-app-deploy-workflows-signing.
(충돌 없음)

$ git log --oneline main..HEAD
e1fce6e 문서 34: RELEASE.md 배포 절 — secrets·variables·dart-define 표와 D2 사람 체크리스트
8e957c7 티켓 34: fastlane·ExportOptions·업로드 키 서명·네이티브 심볼·개인정보 라벨
b5974f2 티켓 34: 배포 워크플로 복사·치환 — develop→App Distribution/TestFlight, main→Play internal/TestFlight
2740666 테스트 34: 앱 배포 워크플로·서명·개인정보 라벨 계약 테스트
(+ 이 증거 문서 커밋)

$ git status --porcelain      # 증거 문서 커밋 전
?? review/impl-evidence-34.md

$ git diff --stat main..HEAD | tail -1
 16 files changed, 1334 insertions(+), 4 deletions(-)

$ git diff main..HEAD -- .github/workflows/flutter-ci.yml .github/workflows/ci.yml \
      .github/workflows/deploy.yml migrations app | wc -l
       0        # 기존 워크플로·백엔드·마이그레이션 변경 0
```

rebase 시점의 `main` 은 작업 시작 시점(008a35a, 티켓 22 머지)보다 티켓 15 만큼 앞서
있었고, 겹치는 파일이 없어 충돌 없이 올라갔다. rebase 후 전체 테스트·린트를 다시
돌린 결과가 위 블록이다.

## 7. `app_privacy_details.json` ↔ `/privacy` 1절 대조

ASC 개인정보 라벨은 `web/templates/legal/privacy.ko.html` 1절 "수집하는 정보" 가
기준이다. 티켓 35 가 티켓 16 의 `docs/legal-checklist.md` 와 1:1 대조할 때 쓸 표.

| `/privacy` 1절 | ASC category | purposes | data_protections | 근거 |
|---|---|---|---|---|
| 게스트 토큰 | `USER_ID` | APP_FUNCTIONALITY | LINKED | 기록의 주인. 계정 연결 시 이메일과 이어진다 |
| 계정 이메일 | `EMAIL_ADDRESS` | APP_FUNCTIONALITY | LINKED | 구글·애플 연결 시에만 수집 |
| 애플 refresh token | — | — | — | 계정 삭제 시 애플 철회용 자격 증명. ASC 라벨 범주(수집 "데이터 유형")에 대응 항목이 없고 `USER_ID` 와 같은 계정 식별 축이라 별도 행을 만들지 않았다 |
| 시도 기록 | `GAMEPLAY_CONTENT` | APP_FUNCTIONALITY | LINKED | 제출 단어·정답 여부·연속 기록 |
| 구독 식별자 | `PURCHASE_HISTORY` | APP_FUNCTIONALITY | LINKED | 스토어 구매 토큰·만료 시각 |
| 광고 ID | `DEVICE_ID` | THIRD_PARTY_ADVERTISING | NOT_LINKED + **USED_TO_TRACK** | AdMob SDK 가 직접 보낸다(서버 저장 없음). ATT 프롬프트를 띄우므로 추적 |
| 광고 ID(노출·클릭 측정) | `ADVERTISING_DATA` | THIRD_PARTY_ADVERTISING | NOT_LINKED + **USED_TO_TRACK** | 〃 |
| 앱 사용 이벤트 | `PRODUCT_INTERACTION` | ANALYTICS, APP_FUNCTIONALITY | NOT_LINKED | Firebase Analytics 집계 이벤트(스펙 §B.24 4개) |
| 접속·오류 기록 | `CRASH_DATA`, `PERFORMANCE_DATA` | APP_FUNCTIONALITY | NOT_LINKED | Sentry. 식별 정보는 마스킹해서 보낸다 |

BASELINE(BuildUrPalace)의 5개 항목은 광고·분석·진단뿐이었다 — 계정과 기록이 없는
오프라인 앱이라서. 이 앱은 게스트 토큰·이메일·시도 기록·구독 4개가 늘고, 그 4개는
`DATA_LINKED_TO_YOU` 다. 파일에는 각 항목에 `_comment` 로 `/privacy` 대응을 적어 뒀다
(소비자인 `asc-submit.yml`(티켓 35)은 `category`/`purposes`/`data_protections` 만 읽어
알 수 없는 키를 무시한다).

## 8. 설계 판단 (티켓·BASELINE 에 답이 없어 고른 것)

1. **서버 주소·광고 유닛 ID·`serverClientId` 는 secret 이 아니라 GitHub variable.**
   세 값 모두 APK·IPA 를 뜯으면 그대로 보이는 공개 식별자라 secret 으로 두면
   "비밀을 지키는 것처럼" 보이기만 하고 로그 마스킹 때문에 디버깅만 어려워진다.
   비밀인 것(keystore·서비스 계정·match·ASC 키·Sentry DSN)만 secret 이다.
2. **develop 도메인을 하드코딩하지 않았다.** 스펙 D3 에 NAS develop 폴더·DNS·터널이
   사람 작업으로 남아 있어 주소가 아직 없다(미정 8 은 포트만 확정). 추측해 적는
   대신 `API_BASE_URL_DEV` variable 로 받고, **비어 있으면 setup 잡에서 멈춘다** —
   빈 주소로 빌드된 앱은 CI 가 초록이고 테스터 손에서만 깨지기 때문이다. prod 는
   값이 이미 있어서(`https://chosung.dosaem.com/api/v1`) 표에 적어 뒀다.
3. **광고 유닛 dart-define 이름은 플랫폼 접미사가 없다.** AdMob 유닛은 플랫폼마다
   다르지만 잡이 이미 플랫폼별로 갈려 있어서, 각 잡이 자기 플랫폼 variable 을
   공통 이름(`ADMOB_*_AD_UNIT_ID`)으로 넘긴다. Dart 쪽에 `Platform.isIOS` 분기가
   생기지 않는다. 티켓 31·29 가 읽을 이름은 `docs/RELEASE.md` "### 34." 표에 고정.
4. **keystore secret 이 없으면 멈추고, Firebase 설정 secret 이 없으면 경고만 한다.**
   서명이 없으면 디버그 키로 서명된 APK 가 스토어·테스터에게 가므로 멈춰야 하고,
   Firebase 가 없으면 Analytics 만 빠진 멀쩡한 앱이라 멈출 이유가 없다(티켓이 요구한
   "Firebase 스킵 경로" 와 같은 선택).
5. **커밋 메시지를 `${{ }}` 로 명령줄에 끼우지 않았다.** BASELINE 은 릴리스 노트에
   `${{ github.event.head_commit.message }}` 를 그대로 넣는데, 메시지 안의 `"` 나
   `$(...)` 가 러너(사용자 맥)에서 실행된다. 환경변수(`RELEASE_NOTES`)로 받아서 넘긴다.
   `github.run_id` 도 같은 이유로 `$GITHUB_RUN_ID` 를 쓴다.
6. **BASELINE 이 레포에 커밋해 둔 `fastlane/google-play-key.json`·`api_key.json` 은
   따라가지 않았다.** 둘 다 gitignore 에 넣고 워크플로는 secret 으로 만들어 쓴다.
7. **Play 서비스 계정·ASC 키 파일을 쓰는 fastlane lane 은 남겨 뒀다**(사람이 맥에서
   손으로 올릴 때 쓴다). 자동 배포 경로는 lane 을 타지 않는다 — Android 는
   `r0adkll/upload-google-play` 액션, iOS 는 match + `xcrun altool` 이다(BASELINE 의
   fastlane pilot 폴링 버그 회피 그대로).
8. **빌드 번호 자동 증가를 넣지 않았다.** `pubspec.yaml` 의 `version:` 한 곳만
   진실로 두면 앱이 런타임에 읽는 값(강제 업데이트 판정, 티켓 22)과 스토어에 올라간
   값이 갈라지지 않는다. 올릴 때마다 `+N` 을 올리는 것을 RELEASE.md 체크로 넣었다.

## 9. 범위 밖이라 하지 않은 것

- `appstore-metadata.yml`·`asc-submit.yml`·`asc-*`·`testflight-tester.yml`,
  `fastlane/metadata/`, 스크린샷 스크립트 — **티켓 35**(스토어 자산·메타데이터).
  이 티켓은 BASELINE 복사 목록 중 티켓이 지정한 7개 대상만 가져왔다.
- `flutter-ci.yml`, `ci.yml`, `deploy.yml` 변경 0건.
- README "설계 판단"·`.env.example`·스펙 "미정 항목" 은 손대지 않았다(이 티켓은
  백엔드 설정값을 추가하지 않고, 앱 쪽 주입값은 `--dart-define` 이라 `.env` 가
  아니다). 설계 판단은 `docs/RELEASE.md` "### 34." 와 이 문서에 남겼다.
- `mobile/README.md` 에 "배포" 절 3줄과 `mobile/lib/config/app_env.dart` 주석의
  "티켓 32 의 워크플로" → 실제 파일 경로 수정만 했다(워크플로가 생겼으므로).

## 수정 라운드 1

Codex 최종 리뷰(`review/impl-review-34.md` 라운드 1, BLOCKER 0 / MAJOR 3 / MINOR 0)의
MAJOR 3건을 고쳤다. 세 건 모두 **리뷰의 재현 방법 그대로 먼저 재현**하고, 그 재현을
실패하는 테스트로 고정한 뒤 고쳤다. 고치기 전 새 테스트 31개가 실패하고 기존 71개가
통과(`31 failed, 71 passed`), 고친 뒤 **102 passed** 다. 리뷰어 지적 3건 모두 맞았다 —
틀렸다고 판단해 안 고친 건은 없다.

### D-34-1 — iOS 아카이브가 match App Store 서명 구성을 사용하지 않는다

**재현(수정 전)** — 리뷰의 명령 그대로:

```
$ xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner \
    -configuration Release -showBuildSettings | grep -E 'CODE_SIGN|PROVISIONING|DEVELOPMENT_TEAM'
    CODE_SIGN_IDENTITY = iPhone Developer
    DEVELOPMENT_TEAM = J8QUD7B666
```

`CODE_SIGN_STYLE`·`PROVISIONING_PROFILE_SPECIFIER` 가 아예 없다(= Automatic).

**원인.** 워크플로·`ExportOptions.plist`·fastlane 은 복사·치환했지만
`mobile/ios/Runner.xcodeproj/project.pbxproj` 는 복사 목록에 없어 `flutter create`
기본값(`"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Developer"`, 서명 스타일
Automatic)이 그대로 남았다. `ExportOptions.plist` 의 manual 서명은 **이미 만들어진
archive 의 export 단계**에만 적용되므로 archive 자체는 개발용 인증서를 요구한다.
BASELINE 원본(`~/Code/BuildUrPalace/ios/Runner.xcodeproj/project.pbxproj`)에는
프로젝트·타깃 Release 양쪽에 `Apple Distribution` / `CODE_SIGN_STYLE = Manual` /
`PROVISIONING_PROFILE_SPECIFIER = "match AppStore <bundle>"` 가 있다(462·491–503·
647·702–714행). 즉 치환 누락이 아니라 **복사 누락**이다.

**수정.** `project.pbxproj` 의 Release 설정 2개만 BASELINE 과 같게 맞췄다.

- 프로젝트 레벨 Release(`97C147041CF9000F007C117D`):
  `"CODE_SIGN_IDENTITY[sdk=iphoneos*]"` → `Apple Distribution`
- Runner 타깃 Release(`97C147071CF9000F007C117D`): `CODE_SIGN_IDENTITY` /
  `"CODE_SIGN_IDENTITY[sdk=iphoneos*]"` = `Apple Distribution`,
  `CODE_SIGN_STYLE = Manual`,
  `PROVISIONING_PROFILE_SPECIFIER = "match AppStore com.dosaem.chosung"`

**Debug·Profile 설정은 건드리지 않았다.** BASELINE 은 Profile 에도 배포 identity 를
넣어 뒀지만, 그러면 로컬 실기기 `flutter run --profile` 이 배포 인증서를 요구한다.
배포 경로(`flutter build ipa`)가 쓰는 설정은 Release 뿐이고 결함도 archive 에 있으므로
Release 만 고쳤다.

**증명(수정 후)**:

```
$ xcodebuild -project mobile/ios/Runner.xcodeproj -target Runner \
    -configuration Release -showBuildSettings | grep -E 'CODE_SIGN|PROVISIONING|DEVELOPMENT_TEAM'
    CODE_SIGN_IDENTITY = Apple Distribution
    CODE_SIGN_STYLE = Manual
    DEVELOPMENT_TEAM = J8QUD7B666
    PROVISIONING_PROFILE_SPECIFIER = match AppStore com.dosaem.chosung

$ xcodebuild ... -configuration Debug -showBuildSettings | grep CODE_SIGN_IDENTITY
    CODE_SIGN_IDENTITY = iPhone Developer      # 로컬 개발은 그대로
```

고정한 테스트(`tests/test_app_deploy_workflow.py`, pbxproj 를 직접 파싱해 Xcode 없이도
돈다):

- `test_release_archive_signs_with_a_distribution_identity[97C147041…]`,
  `[97C147071…]` — Release 의 모든 `CODE_SIGN_IDENTITY*` 가 `Apple Distribution`
- `test_release_archive_uses_the_match_app_store_profile` — `CODE_SIGN_STYLE = Manual`,
  프로파일 이름, 팀 ID
- `test_archive_and_export_name_the_same_profile` — archive 쪽 프로파일 이름과
  `ExportOptions.plist` 의 이름이 같다(갈라지면 export 에서 죽는다)

**남은 사람 검증.** 실제 인증서가 필요한 archive 는 D2(인증서·match 준비) 뒤 사람
단계다. 이 수정은 "설정이 배포 서명을 가리키는지"까지 증명한다.

### D-34-2 — 수동 fastlane 배포가 서버·광고·로그인 설정 없이 앱을 다시 빌드한다

**재현(수정 전)** — 원본 Fastfile 의 빌드 함수만 평가해 `sh` 가 받는 명령을 포착하는
Ruby 하네스(외부 호출·실제 빌드 없음, `sh`/`UI`/platform 블록 전부 스텁):

```
$ ruby capture.rb mobile/android/fastlane/Fastfile build_appbundle
CMD: flutter build appbundle --release || echo 'flutter exited nonzero (…)'
dart-define count: 0
$ ruby capture.rb mobile/ios/fastlane/Fastfile build_flutter_ios
CMD: flutter build ios --release --no-codesign
dart-define count: 0
```

**원인.** `DART_DEFINES` 를 워크플로 잡의 `env:` 에만 정의했다. 수동 lane 은 그 값을
읽을 데가 없고 `build_appbundle`/`build_flutter_ios` 가 매번 새로 빌드하므로, 앞서
올바른 인자로 만든 바이너리도 덮어쓴다. 그래서 `mobile/lib/config/app_env.dart:8` 의
에뮬레이터 기본 주소(`http://10.0.2.2:8089/api/v1`)가 들어간 바이너리가 스토어로 간다.
광고 유닛·`GOOGLE_SERVER_CLIENT_ID` 도 빈 값이 된다.

**수정.** 두 Fastfile 에 같은 `dart_defines` 함수를 두고 **환경변수에서 읽어** 빌드
명령에 붙인다. 필수 5개(`API_BASE_URL`, `GOOGLE_SERVER_CLIENT_ID`,
`ADMOB_{BANNER,INTERSTITIAL,REWARDED}_AD_UNIT_ID`) 중 하나라도 비어 있으면
`UI.user_error!` 로 **빌드 전에** 멈춘다(`clean` 으로 기존 산출물을 지우기 전에
검사한다 — 멈춘 뒤 되돌릴 게 없도록 빌드 함수 진입 직후에 호출한다).
`SENTRY_DSN` 만 비워 둘 수 있다(워크플로도 빈 값을 넘긴다). 값은
`Shellwords.escape` 로 감싼다. 사람이 넘길 이름·예시 명령은 `docs/RELEASE.md`
"### 34." 의 dart-define 표 아래에 넣었다.

**증명(수정 후)** — 같은 하네스, 값을 환경변수로 주고:

```
$ API_BASE_URL=https://example/api/v1 GOOGLE_SERVER_CLIENT_ID=gsc \
  ADMOB_BANNER_AD_UNIT_ID=b ADMOB_INTERSTITIAL_AD_UNIT_ID=i ADMOB_REWARDED_AD_UNIT_ID=r \
  ruby capture.rb mobile/android/fastlane/Fastfile build_appbundle
CMD: flutter build appbundle --release --dart-define=API_BASE_URL=https://example/api/v1
     --dart-define=GOOGLE_SERVER_CLIENT_ID=gsc --dart-define=ADMOB_BANNER_AD_UNIT_ID=b
     --dart-define=ADMOB_INTERSTITIAL_AD_UNIT_ID=i --dart-define=ADMOB_REWARDED_AD_UNIT_ID=r
     || echo 'flutter exited nonzero (…)'
dart-define count: 5
$ … ruby capture.rb mobile/ios/fastlane/Fastfile build_flutter_ios
CMD: flutter build ios --release --no-codesign --dart-define=API_BASE_URL=… (5개)
dart-define count: 5
```

고정한 테스트 — 같은 하네스를 pytest 안에서 돌린다(`ruby` 가 없으면 skip, 정적
검사는 항상 돈다):

- `test_manual_lane_build_passes_the_dart_defines[이름-Fastfile-함수]` 10개 —
  두 플랫폼 × 필수 5개가 실제 빌드 명령에 값까지 붙어 나온다
- `test_manual_lane_stops_when_a_dart_define_is_missing[…]` 10개 — 하나를 비우면
  exit 2(`UI.user_error!`)로 멈추고 **`flutter build` 가 아예 포착되지 않는다**
- `test_manual_lane_dart_define_names_are_documented[…]` 2개 — 이름이 Fastfile 과
  `docs/RELEASE.md` 양쪽에 있다

### D-34-3 — self-hosted 러너의 인증 파일과 keychain 이 실패 후 남는다

**재현(수정 전)** — 리뷰 방법 그대로. ① Firebase 업로드 `run` 블록을 임시
`RUNNER_TEMP` + 비인증 더미 문자열로 돌리고 `npx` 를 exit 1 함수로 대체:

```
$ bash drive.sh        # npx() { return 1; }
npx stub: simulated upload failure
exit=1
--- runner_temp 잔존 ---
firebase-key-repro1.json          # 서비스 계정 JSON 이 남는다
```

② match 스텝을 `security`/`openssl` 무해 스텁 + `fastlane` exit 1 로 돌리고 임시
`GITHUB_ENV` 를 주면:

```
$ bash drive_match.sh
security stub: create-keychain … fastlane stub: simulated match failure
exit=1
--- GITHUB_ENV ---
                                   # 비어 있다 — KEYCHAIN_NAME 이 안 넘어간다
```

**원인.** 정리를 **성공 경로의 마지막 줄**에 뒀다. Actions 는 `bash -e` 로 돌리므로
업로드가 실패하면 뒤의 `rm` 까지 가지 않는다(Firebase 서비스 계정 JSON, 홈 디렉터리의
ASC P8). Android keystore·`key.properties` 와 `ios/fastlane/api_key.json` 은 성공 시에도
지우는 코드가 없었다. keychain 은 `always()` 정리 스텝이 있었지만 이름을
`$GITHUB_ENV` 에 넘기는 줄이 `fastlane match` **뒤**라, match 가 실패하면 이미 만든
keychain 을 못 찾는다. self-hosted 러너는 잡이 끝나도 호스트(사용자 맥)가 폐기되지
않으므로 후속 잡·프로세스가 이 자료에 접근할 수 있다. `.gitignore` 는 커밋만 막는다.

**수정.** 제어 흐름 자체를 바꿨다 — 성공 경로에 의존하지 않는다.

1. Firebase 업로드: `trap 'rm -f "$KEY_FILE"' EXIT INT TERM` 으로 바꾸고 끝의 `rm`
   제거(취소도 덮는다).
2. TestFlight 업로드: 꺼낸 P8 경로를 `P8_FILE` 로 잡고 같은 trap, 끝의 `rm` 제거.
3. match 스텝: `echo "KEYCHAIN_NAME=…" >> $GITHUB_ENV` 를 keychain 을 **만든 직후**
   (`fastlane match` 앞)로 옮겼다.
4. android 잡 끝에 `Cleanup signing material` (`if: always()`) 추가 —
   `android/app/upload-keystore.jks`, `android/key.properties`,
   `$RUNNER_TEMP/firebase-key-$GITHUB_RUN_ID.json` 제거.
5. ios 잡의 `Cleanup keychain` 을 `Cleanup signing material` 로 확장 —
   keychain 삭제 + `ios/fastlane/api_key.json` 제거(둘 다 `if: always()`).

**증명(수정 후)** — 같은 재현 스크립트:

```
$ bash drive.sh
npx stub: simulated upload failure
exit=1
--- runner_temp 잔존 ---
(비어 있으면 정상)                  # 남은 파일 0개

$ bash drive_match.sh
… fastlane stub: simulated match failure
exit=1
--- GITHUB_ENV ---
KEYCHAIN_NAME=ci-repro2.keychain   # always() 정리가 찾을 수 있다
```

고정한 테스트 — 워크플로의 `run` 블록을 스텁과 함께 **실제로 `bash -e` 로 돌린다**
(`$HOME`·`RUNNER_TEMP`·`GITHUB_ENV` 를 `tmp_path` 로 돌려 실제 홈·실제 keychain 은
건드리지 않고, 실제 키·외부 호출도 없다):

- `test_firebase_key_is_removed_when_the_upload_fails` — `npx` 실패 후
  `RUNNER_TEMP` 가 비어 있다
- `test_keychain_name_reaches_the_cleanup_step_even_if_match_fails` — `fastlane`
  실패 후에도 `GITHUB_ENV` 에 `KEYCHAIN_NAME=ci-<run id>.keychain` 이 있다
- `test_extracted_p8_is_removed_when_the_testflight_upload_fails` — `xcrun` 실패 후
  임시 홈 아래 `*.p8` 이 0개다
- `test_android_signing_material_is_deleted_after_the_job`,
  `test_asc_api_key_file_is_deleted_after_the_job` — `always()` 스텝이 keystore·
  `key.properties`·`api_key.json`·keychain 을 지운다

### 전체 검증

고치기 전 → 고친 뒤 (같은 테스트 파일):

```
$ uv run pytest tests/test_app_deploy_workflow.py -q     # 구현 원본 + 새 테스트
31 failed, 71 passed in 1.65s
$ uv run pytest tests/test_app_deploy_workflow.py -q     # 수정 후
102 passed in 1.76s
```

`ruff format` 은 이 레포의 게이트가 아니다(기존 `tests/` 46개 중 17개가 미준수) —
`ruff check` 만 맞췄다.

#### 미수정 MINOR

리뷰 라운드 1 은 MINOR 0건이다. 수정 중에 새로 적어 둘 만한 것:

- BASELINE 은 Profile 설정에도 배포 identity 를 넣어 뒀지만 따라가지 않았다
  (로컬 `flutter run --profile` 이 배포 인증서를 요구하게 된다). 배포 경로는
  Release 만 쓴다 — D-34-1 절 참조.

#### rebase 후 재검증 (로컬 `main` = `a520223`, 티켓 17 머지까지 위)

전체 스위트가 한 번에 11~12분이라 그 사이 로컬 `main` 이 계속 앞으로 갔다. rebase 후
전체 재실행을 네 번 했고 **네 번 모두 exit 0** 이다 — `b8f63cc` 위 `845 passed`,
`7df7809`(티켓 14) 위 `902 passed`, `4d83feb`(티켓 13) 위 `967 passed`,
`a520223`(티켓 17) 위 `1026 passed`. 아래가 최종(`a520223` 위) 상태다. 충돌은 네 번
모두 0건이었다 — 이 티켓이 건드리는 파일 중 다른 티켓과 겹칠 수 있는 것은
`docs/RELEASE.md` 뿐이고 자기 번호 절(`### 34.`)만 쓴다.

```
$ git -c core.editor=true rebase main          # 로컬 main. origin/main 아님
Successfully rebased and updated refs/heads/dosaem/t34-app-deploy-workflows-signing
$ git status --short
(비어 있음 — clean)

$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=…/chosung_daily_test_t34 TEST_REDIS_URL=redis://…/8 uv run pytest -q
1026 passed in 663.81s (0:11:03)       # exit 0 (머지된 티켓들 995 + 새 테스트 31)

$ uv run pytest tests/test_app_deploy_workflow.py -q
102 passed in 1.55s                    # 기존 71 + 이번 라운드 31

$ uv run flask db heads
d7a1f0ca0a29 (head)                    # 1줄(머지된 티켓의 head). 이 티켓은 마이그레이션 변경 없음

$ flutter analyze --no-pub             # 레포 루트
No issues found! (ran in 3.2s)
$ flutter test --no-pub                # mobile/
00:22 +120: All tests passed!          # main 의 티켓 24 테스트가 들어와 87 → 120

$ plutil -lint mobile/ios/Runner.xcodeproj/project.pbxproj
mobile/ios/Runner.xcodeproj/project.pbxproj: OK
$ xcodebuild -project mobile/ios/Runner.xcodeproj -list
Build Configurations: Debug / Release / Profile    # 설정 목록 그대로
```

- 테스트 DB 는 기존 `chosung_daily_test_t34`(+ 파생 `_t34_migrations`), Redis 는 DB 8.
  공용 `chosung_daily_test` 와 다른 티켓 DB 는 건드리지 않았고 새로 만들지도 않았다.
  접속 문자열·비밀번호는 기록하지 않는다.
- 이번 수정의 변경 범위는 Android 빌드 그래프와 무관해서(iOS pbxproj·fastlane Ruby·
  워크플로 YAML·테스트·문서) `flutter build apk --debug` 는 다시 돌리지 않았다 —
  디스크 여유가 적다는 코디네이터 메모에 따라 `mobile/build` 도 비워 뒀다. pbxproj
  변경은 `plutil -lint` + `xcodebuild -showBuildSettings`/`-list` 로 검증했다.
- 실제 서명·match·업로드는 시크릿이 없어 실행하지 않았다. 프로덕션 접근·`git push`·
  외부 서비스 호출·인증 정보 입력 없음. BASELINE(`~/Code/BuildUrPalace`)은 읽기만 했다.

## 수정 라운드 2

리뷰 `review/impl-review-34.md` "라운드 2" 의 **D-34-4 (MAJOR) 1건**을 고쳤다.
BLOCKER·REPEAT·MINOR 는 없다. 미수정 MINOR 도 없다. 리뷰의 지적은 그대로
재현됐고, 틀렸다고 판단한 항목은 없다.

### D-34-4 — 수동 Android 배포가 빌드 실패 후 이전 AAB 를 업로드한다

**재현 (수정 전).** 리뷰가 적은 방법대로, 이전 AAB 가 남아 있는 상태에서 빌드만
실패시켰다. 임시 트리에 원본 Fastfile 을 놓고, PATH 앞의 가짜 `flutter` 로
컴파일 실패(`exit 1`)를 만들고, 외부 호출인 `upload_to_play_store` 만 출력으로
바꿔 `beta` lane 을 끝까지 평가했다.

```
$ printf 'stale-aab-from-previous-build' > .../build/app/outputs/bundle/release/app-release.aab
$ cat bin/flutter
#!/bin/sh
echo "compilation-failed: lib/main.dart:1: error" >&2
exit 1
$ ruby harness.rb Fastfile beta        # 필수 dart-define 5개는 모두 정상 지정
compilation-failed: lib/main.dart:1: error
flutter exited nonzero (known strip false-positive with debugSymbolLevel=FULL)
UPLOAD_REACHED: internal               # ← 업로드 진입
EXIT=0                                 # ← 실패가 성공으로
--- AAB still: stale-aab-from-previous-build   # 지난 빌드의 바이너리 그대로
```

**원인.** 증상은 "실패했는데 올라간다" 지만, 원인은 두 가지가 겹친 것이다.

1. `sh("flutter build appbundle ... || echo ...")` 가 **모든** 실패를 삼킨다.
   삼키는 근거는 `debugSymbolLevel=FULL` 의 스트립 오탐뿐인데, 종료 코드로는
   오탐과 진짜 실패를 구별할 수 없다.
2. 그래서 성공 판정을 산출물에 맡기는데, `File.exist?` 는 **누가 만들었는지**를
   모른다. `clean:` 은 선택이고 문서의 기본 명령(`fastlane beta`)에는 없으므로
   `mobile/build` 의 지난 AAB 가 그대로 남아 검사를 통과한다.

즉 "종료 코드를 산출물로 대체" 한 설계는 맞지만, 그 산출물이 **이번 실행의 것**
이라는 보장과 **내용이 멀쩡하다**는 확인이 빠져 있었다. 둘 중 하나만 고치면
증상만 가려진다(빌드 전 삭제만 하면 쓰다 만 파일이 통과하고, 내용 검사만 하면
지난 정상 AAB 가 통과한다).

**수정.**

- `mobile/android/fastlane/Fastfile` — 빌드 **전에** 대상 AAB 를 지운다
  (`FileUtils.rm_f`). 이후 "파일이 있다" = "이번 빌드가 만들었다" 가 된다.
  그 다음 새 파일의 내용을 검사한다.
- `mobile/tool/verify_appbundle.py` (신규) — 삼킨 종료 코드 대신 산출물을 본다.
  ① 열리는 zip 이고 `base/manifest/AndroidManifest.xml` 이 있다(= 온전한 AAB),
  ② `base/lib/*/libapp.so` 가 있고 전부 스트립돼 있다(= exit 1 이 오탐이었고
  스트립이 진짜 실패한 게 아니다). 실패 사유를 한국어로 stderr 에 적고 exit 1.
- `.github/workflows/flutter.yml` — **같은 원인이 Actions 쪽에도 있다.**
  self-hosted 러너는 작업 디렉터리가 호스트에 남으므로 빌드 전 `rm -f` 를 넣었다.
  AAB 스텝에 인라인돼 있던 python 검사는 위 스크립트 호출로 바꿨다 — 두 경로가
  다른 검사를 쓰면 한쪽만 조용히 느슨해진다(테스트로 고정).
- `docs/RELEASE.md` "34." — 수동 lane 의 이 동작과 `python3` 필요를 적고, 러너
  준비물 목록에도 `python3` 을 넣었다.

**증명 1 — 회귀 테스트 (red → green).** 새 테스트 12개. 먼저 수정 전 코드
(`git show HEAD:...`)로 돌려 빨간 것을 확인했다.

```
$ git show HEAD:mobile/android/fastlane/Fastfile > mobile/android/fastlane/Fastfile
$ git show HEAD:.github/workflows/flutter.yml > .github/workflows/flutter.yml
$ uv run pytest tests/test_app_deploy_workflow.py -q -k "stale_aab or ..."
FAILED test_manual_lane_does_not_upload_a_stale_aab_when_the_build_fails[beta]
FAILED test_manual_lane_does_not_upload_a_stale_aab_when_the_build_fails[release]
FAILED test_manual_lane_rejects_a_new_but_unstripped_aab
FAILED test_aab_step_removes_the_previous_bundle_before_building
FAILED test_workflow_and_manual_lane_share_the_aab_check
FAILED test_aab_step_keeps_the_strip_false_positive_handling
6 failed, 2 passed
```

실패 본문이 리뷰의 재현과 같다:

```
E  AssertionError: ('fake flutter build appbundle --release --dart-define=API_BASE_URL=...
E    flutter exited nonzero (known strip false-positive with debugSymbolLevel=FULL)
E    UPLOAD_REACHED: internal
E    ', '')
E  assert 0 != 0
```

통과한 2개는 대조군이다(`..._uploads_the_aab_this_build_produced`,
`..._still_tolerates_the_strip_false_positive`) — 수정 전에도 통과해야 맞다.
새 검사가 "항상 실패" 가 아니라 **산출물의 출처와 내용**을 본다는 증거다.

수정 후:

```
$ uv run pytest tests/test_app_deploy_workflow.py -q
114 passed in 4.37s                    # 라운드 2 기준 102 + 신규 12
```

테스트 구성 — lane 은 원본 Fastfile 을 `platform`/`lane` DSL 째로 평가하고 `sh`
는 **실제 셸**을 돌린다(기존 `CAPTURE_RB` 는 `File.exist?` 를 항상 true 로 만들고
`sh` 를 돌리지 않아 이 경로를 못 봤다 — 리뷰 지적 그대로다):

| 테스트 | 입력 | 기대 |
|---|---|---|
| `..._does_not_upload_a_stale_aab_when_the_build_fails[beta/release]` | 이전 AAB 있음 + `flutter` exit 1, 새 산출물 없음 | exit≠0, `UPLOAD_REACHED` 없음 |
| `..._uploads_the_aab_this_build_produced` | 새 AAB 생성 + exit 0 | exit 0, `UPLOAD_REACHED: internal` |
| `..._still_tolerates_the_strip_false_positive` | 이전 AAB 있음 + exit 1 + **새** 정상 AAB | exit 0, 업로드 진입 (수동 배포를 막지 않는다) |
| `..._rejects_a_new_but_unstripped_aab` | exit 1 + 새 AAB 지만 lib 미스트립 | exit≠0, 업로드 없음 |
| `test_verify_appbundle_*` 5개 | 정상 / 미스트립 / lib 없음 / 잘린 zip / 파일 없음 | 0 / 1 / 1 / 1 / 1 |
| `test_aab_step_removes_the_previous_bundle_before_building` | 워크플로 YAML | `rm -f` 가 `flutter build` **앞** |
| `test_workflow_and_manual_lane_share_the_aab_check` | YAML + Fastfile | 같은 스크립트를 쓴다 |

ELF 픽스처는 테스트가 로컬 NDK 나 커밋한 바이너리에 기대지 않도록 최소
aarch64 ELF 를 직접 만든다(`.symtab` 섹션 유무 → `file` 의 "not stripped").
같은 검사를 실제 NDK 바이너리로도 교차 확인했다:

```
$ file -b .../ndk/28.2.13676358/.../aarch64-linux-android/libc++_shared.so
ELF 64-bit LSB shared object, ARM aarch64, ..., with debug_info, not stripped
$ python3 mobile/tool/verify_appbundle.py <그 .so 를 넣은 AAB>
AAB 검사 실패: base/lib/arm64-v8a/libapp.so 이 스트립되지 않았다 — 스트립 오탐이 아니라 실제 실패다
exit=1
$ llvm-strip -o real-stripped.so <같은 .so>   &&  python3 .../verify_appbundle.py <그걸 넣은 AAB>
AAB 검사 통과: ... (manifest 있음, 배포 lib 스트립됨)
exit=0
```

**증명 2 — 실제 AAB.** 가짜 산출물만으로 끝내지 않고 진짜 release AAB 를 만들어
오탐을 **실측**했다. keystore 가 없어 디버그 키로 폴백되는 경로다(§3.2).

```
$ flutter pub get && JAVA_HOME=/opt/homebrew/opt/openjdk@17 flutter build appbundle --release
Release app bundle failed to strip debug symbols from native libraries.
FLUTTER_EXIT=1                          # ← 오탐. 그런데
$ ls -la mobile/build/app/outputs/bundle/release/
-rw-r--r--  1 saem  staff  130309073 Oct 14 13:45 app-release.aab     # ← AAB 는 정상 생성

$ python3 mobile/tool/verify_appbundle.py mobile/build/.../app-release.aab
AAB 검사 통과: ... (manifest 있음, 배포 lib 스트립됨)
exit=0                                  # ← 오탐을 막지 않는다
```

배포 lib 18개(3 ABI × 6) 전부 `stripped`, 심볼은 `BUNDLE-METADATA` 에 들어간다 —
워크플로 주석의 주장이 실제로 맞다:

```
base/lib/arm64-v8a/libapp.so -> ELF 64-bit ... ARM aarch64, ..., stripped
base/lib/armeabi-v7a/libapp.so -> ELF 32-bit ... ARM, EABI5 ..., stripped
base/lib/x86_64/libapp.so -> ELF 64-bit ... x86-64, ..., stripped
... (libflutter/libdartjni/libsentry/libsentry-android/libdatastore_shared_counter 동일)
BUNDLE-METADATA/com.android.tools.build.debugsymbols/arm64-v8a/libflutter.so.dbg
```

그 **실제** AAB 로 lane 을 끝까지 돌린 결과(이전 AAB 가 남아 있고, `flutter` 는
실제와 같은 오탐 메시지로 exit 1):

```
Release app bundle failed to strip debug symbols from native libraries.
flutter exited nonzero (known strip false-positive with debugSymbolLevel=FULL)
AAB 검사 통과: build/app/outputs/bundle/release/app-release.aab (manifest 있음, 배포 lib 스트립됨)
UPLOAD_REACHED: internal               # 오탐 + 새 산출물 = 업로드. 지난 AAB 는 대체됐다
```

**수정 후 원래 재현 입력**(이전 AAB 있음 + 진짜 빌드 실패)은 막힌다:

```
compilation-failed: lib/main.dart:1: error
flutter exited nonzero (known strip false-positive with debugSymbolLevel=FULL)
USER_ERROR: AAB was not produced — 이번 빌드가 실패했다 (build/app/outputs/bundle/release/app-release.aab)
EXIT=1                                 # 업로드 미진입
--- stale AAB present: no              # 지난 바이너리는 빌드 전에 지워졌다
```

빌드 검증에 쓴 `mobile/build`(4.1GB)는 디스크 여유 메모에 따라 삭제하고 부재를
확인했다. iOS 수동 lane 은 같은 결함이 없다 — `sh("flutter build ios ...")` 에
`|| echo` 가 없어 실패가 그대로 올라가고, `build_app` 이 IPA 를 매번 새로 만든다
(`mobile/ios/fastlane/Fastfile:46`, `:57`).

### 전체 검증 (라운드 2)

로컬 `main` = `82e59ea`(티켓 23 머지가 들어왔다) 위로 rebase 한 뒤 전부 다시 돌렸다.
`review/impl-review-34.md` 는 수정하지 않았다. 이번 수정이 건드린 파일은
`mobile/android/fastlane/Fastfile`, `mobile/tool/verify_appbundle.py`(신규),
`.github/workflows/flutter.yml`, `tests/test_app_deploy_workflow.py`,
`docs/RELEASE.md`(자기 번호 절 `### 34.` 과 러너 준비물 한 줄).

```
$ git rebase main                      # 로컬 main. origin/main 아님
Successfully rebased and updated refs/heads/dosaem/t34-app-deploy-workflows-signing
$ git status --short
(비어 있음 — clean)
$ git diff --check main...HEAD
(통과)

$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=…/chosung_daily_test_t34 TEST_REDIS_URL=redis://…/8 uv run pytest -q
1110 passed in 707.26s (0:11:47)       # exit 0. 라운드 2 의 1026 + main 의 티켓 23 + 신규 12
$ uv run pytest tests/test_app_deploy_workflow.py -q
114 passed in 3.42s                    # 102 + 신규 12

$ uv run flask db heads
d7a1f0ca0a29 (head)                    # 1줄. 이 티켓은 마이그레이션 변경 없음

$ flutter analyze --no-pub             # 레포 루트
No issues found! (ran in 9.8s)
$ flutter test --no-pub                # mobile/
00:22 +120: All tests passed!
```

- 테스트 DB 는 기존 `chosung_daily_test_t34`(+ 파생 `_t34_migrations`), Redis 는 DB 8.
  공용 `chosung_daily_test` 와 다른 티켓 DB 는 건드리지 않았고 새로 만들지도 않았다.
  접속 문자열·비밀번호는 기록하지 않는다.
- 기존 `_capture_lane_build` 하네스는 빈 임시 디렉터리에서 돌리도록 바꿨다. 빌드
  함수가 `Dir.chdir("../..")` 로 올라가 이전 AAB 를 지우므로, 레포 안에서 돌리면
  레포 밖 경로를 가리킨다(테스트가 레포 밖을 건드리지 않게).
- 실제 서명·match·스토어 업로드는 시크릿이 없어 실행하지 않았다. D-34-4 의 실측은
  디버그 키 폴백 경로의 release AAB 빌드까지다. 프로덕션 접근·`git push`·외부 서비스
  호출·인증 정보 입력 없음. 시크릿 값은 파일·로그·문서에 남기지 않았다.
