# 티켓 41 최종 리뷰 — 라운드 1 (Phase 6 배포 준비 최종 점검·보완)

- 대상: `dosaem/t41-phase6-release-readiness` `42ff9a2`(로컬 `main` `a766bc0` 위 3 커밋, `git merge-base --is-ancestor main HEAD` 참). `origin/main` 은 쓰지 않았다.
- 읽은 것: 티켓 원문(이어하기 지시 + 코디네이터 결정 6건), `.scratch/store-launch/spec.md`(Phase 6 기준표·보조 워크플로 4개·티켓 41 은 스펙에 **이름이 없다** — grep 0건, 증거 §1.2 의 서술과 같다), `git diff main...HEAD` 12 파일 전부, `review/impl-evidence-41.md`, 새 워크플로 4개 전문, BASELINE(`~/Code/BuildUrPalace/.github/workflows/`) 4개와의 heredoc diff, `review/impl-review-40.md`(D-40-1·D-40-2), 인용된 리뷰 파일 9개의 D 항목 제목.
- UI 변경 없음 → 디자인 디렉터리·`impeccable detect`·`audit.native` 는 대상 아님.
- 코드·테스트·설정·`.scratch/` 는 바꾸지 않았다. 빌드 산출물(`mobile/build`·`mobile/ios/Pods`·`.symlinks`)은 확인 뒤 지웠고 트리는 clean 이다(§2.1).
- 시크릿은 적지 않는다. DB 접속 문자열은 호스트·DB 이름만 적는다.

## 1. 요구(코디네이터 결정 6건 + 원 지시 검증)별 충족 여부

| # | 요구 | 판정 | 근거 |
|---|---|---|---|
| 1 | ASC 보조 워크플로 4개 전부 포팅, 테스터 이메일 = 입력 + `vars.TESTFLIGHT_TESTER_EMAIL`, 실제 이메일 레포에 없음, RELEASE variables 표·테스트 갱신 | 충족 | `.github/workflows/{asc-status,asc-build-compliance,asc-diagnose,testflight-tester}.yml` 신규. `testflight-tester.yml:32`·`asc-diagnose.yml:31` 이 `github.event.inputs.email \|\| vars.TESTFLIGHT_TESTER_EMAIL`. BASELINE 의 `default: '<운영자 주소>'` 는 `default: ''` 로 바뀌었고 네 파일에 `@` 주소 0건(§2.3). `docs/RELEASE.md:263` variables 표에 행 추가, `test_variable_index_covers_every_variable_the_workflows_use` 가 전수 비교(통과) |
| 2 | `Info.plist` `ITSAppUsesNonExemptEncryption=<false/>`, 근거(OS HTTPS 만·자체 암호 라이브러리 없음)를 코드·pubspec 으로 확인해 적고, RELEASE 근거 + 운영자 첫 제출 확인 체크 | 충족 | `mobile/ios/Runner/Info.plist:65-66` (`plutil -lint` OK, `PlistBuddy Print` → `false`, §2.1). 근거를 내가 다시 확인: `mobile/pubspec.yaml` 에 `crypto`·`pointycastle`·`encrypt`·`cryptography` 0건, `mobile/lib` grep 에서 `package:crypto`·AES·Hmac·sha256 호출 0건(유일한 일치는 `guest_token_store.dart:32` 주석). RELEASE `#### 41.2` 근거 + D3 `docs/RELEASE.md:204-208` 체크 항목 |
| 3 | `Podfile.lock`·`project.pbxproj`·`xcworkspace` 세 파일 커밋, 서명 설정 보존 확인을 증거에 | 충족 | 세 파일 모두 diff 에 있다. 보존을 내가 다시 확인: `xcodebuild -project Runner.xcodeproj -target Runner -configuration Release -showBuildSettings` → `CODE_SIGN_IDENTITY = Apple Distribution` / `CODE_SIGN_STYLE = Manual` / `DEVELOPMENT_TEAM = J8QUD7B666` / `PROVISIONING_PROFILE_SPECIFIER = match AppStore com.dosaem.chosung`. pbxproj 전후 개수 `InfoPlist.strings` 6/6 · `PROVISIONING_PROFILE_SPECIFIER` 1/1 · `CODE_SIGN_STYLE` 4/4 · `Apple Distribution` 3/3 · `LaunchScreen.storyboard` 6/6 · `[CP]` 0→12. 절대 경로·사용자명 0건. **재현성**: `flutter build ios` 가 돌린 `pod install` 뒤 `git status` 가 clean — lock·pbxproj 가 같은 내용으로 다시 생성된다(§2.1). 증거 §7.2 에 기록됨 |
| 4 | `### 41.` cloudflared 절: 대시보드 관리형·`config.yml` 두 방식, prod→`127.0.0.1:8089`, develop→`127.0.0.1:8090`, 현재 방식 확인은 사람 | 충족 | `docs/RELEASE.md` `#### 41.1`. 두 방식·두 포트·`http_status:404` 마지막·`route dns`·`ingress validate` 다 있다. 포트 바인딩 서술은 `docker-compose.prod.yml:70`(`127.0.0.1:${APP_PORT}:5000`)과, `API_BASE_URL_DEV` 비면 멈춘다는 서술은 `flutter.yml:49-60` 과 맞다. "어느 쪽인지 확인하는 것은 사람 몫" 명시, D3 `:164-166` 체크 항목이 이 절을 가리킨다 |
| 5 | 알려진 한계에 2행(공유 파일 규칙 위반 7건 / §19 재현성 2건, ID 나열) | 충족 | `docs/RELEASE.md:372-373`. 나열된 ID 9개가 전부 인용된 리뷰 파일에 `### D-..` 제목으로 실재한다(§2.4). D-39-2 를 "해소" 로 뺀 판단도 맞다(`spec.md` 범위 `01~40`) |
| 6 | 티켓 40 머지로 거짓이 된 RELEASE 서술 3곳을 현재 상태로 | 충족 | 알려진 한계 Play 행(`:371`), D3 재촬영 항목(`:199-203`, `[x]`+취소선), `### 37.` 마지막 문단(`:1451-1454`). `d73b1b2` 가 "Merge 티켓 40" 이고 `main` 의 조상임을 확인. 내가 돌린 `verify_store_screenshots.py ios`·`play` 둘 다 exit 0(§2.1). `진행 중`·`40 머지 후` 잔존 문구 0건(`:74` 의 상태 범례 설명만 남는다) |
| 검증 | pytest·ruff·flutter analyze(info 포함 0)·flutter test·apk --debug·build ios --no-codesign, 산출물 삭제, 커밋 | 충족 | §2.1 전부 내가 다시 돌렸다 |
| 제약 | 앱·서버 기능 변경 없음, `.scratch/` 변경 없음, push·외부 호출 없음 | 충족 | diff 12 파일에 `mobile/lib/`·`app/`·`web/`·`migrations/`·`.scratch/` 없음. `Info.plist` 새 키는 제출 신고값. 커밋 3개 전부 로컬 |

## 2. 직접 확인한 것

### 2.1 검증 명령 (내가 돌린 출력)

전용 자원: DB `chosung_daily_test_t41`·`chosung_daily_test_t41_migrations`(이미 있었다) · Redis DB 3(시작 전 `dbsize` 0). 레포 기본 DB 로 떨어지지 않았다.

```
$ uv run ruff check .
All checks passed!                                                (exit 0)

$ uv run pytest -q tests/test_asc_helper_workflows.py tests/test_release_docs.py
162 passed in 0.18s                                               (exit 0)

$ TEST_DATABASE_URL=mysql+pymysql://***@localhost:3306/chosung_daily_test_t41 \
  TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t41_migrations \
  TEST_REDIS_URL=redis://127.0.0.1:6379/3 uv run pytest -q
1693 passed in 874.67s (0:14:34)                                  (exit 0, 재실행 없음)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 201 files (0 changed)                                   (exit 0)
$ flutter analyze --no-pub
No issues found! (ran in 2.8s)                                    (exit 0, info 0)
$ flutter test --no-pub --reporter compact
00:48 +796: All tests passed!                                     (exit 0)

$ flutter build ios --no-codesign        # 안에서 pod install 4.8s 실행
✓ Built build/ios/iphoneos/Runner.app (42.7MB)                    (exit 0, Xcode 65.5s)
$ git status --short                     # pod install 뒤 — lock·pbxproj·xcworkspace 재생성 결과가 커밋과 같다
(비어 있음)
$ flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk               (exit 0)
$ rm -rf mobile/build mobile/ios/Pods mobile/ios/.symlinks && git status --short
(비어 있음)

$ python3 -I tool/verify_store_screenshots.py ios   → screenshots OK: ios   (exit 0)
$ python3 -I tool/verify_store_screenshots.py play  → screenshots OK: play  (exit 0)
$ plutil -lint mobile/ios/Runner/Info.plist → OK
$ /usr/libexec/PlistBuddy -c "Print :ITSAppUsesNonExemptEncryption" → false
$ git diff --check main...HEAD                                    (exit 0)
```

참고: 내가 `flutter pub get` 없이 먼저 돌린 수동 `pod install` 은 Flutter 템플릿의 `Generated.xcconfig must exist` 로 실패했다 — 레포 결함이 아니라 순서 문제고, `flutter build ios` 가 돌린 `pod install` 로 위 재현성 확인을 했다. `#### 41.4` 의 "새 클론에서 `pod install` 한 번" 서술에 `flutter pub get` 선행이 빠져 있다(§5 참고).

### 2.2 워크플로 4개 — BASELINE 과의 실제 차이 (heredoc diff, 주석 제외)

증거 §3 이 "다르게 한 것" 으로 적은 네 가지가 diff 에 그대로 보이고, 그 외의 로직 변경은 없다.

- 공통: 번들 ID `com.dosaem.buildurpalace` → `com.dosaem.chosung`; `json.loads(os.environ['API_KEY_JSON'])` → 빈 secret 가드; `exp` 600 → 900(`asc-submit.yml` 과 동일); `api()` 가 `ok=()` 로 허용 코드를 받고 빈 응답 본문을 `{}` 로 처리; `apps['data']` 빈 배열 가드; `urllib.error` 명시 import.
- `asc-build-compliance`: BASELINE 은 `expired` 만 건너뛰고 `usesNonExemptEncryption is None` 일 때만 PATCH — 새 코드는 같은 조건을 `continue` 한 줄로 합쳤다(동작 동일). `patched N` 카운트 추가.
- `testflight-tester`: BASELINE 은 `POST /v1/betaTesters` 409 에서 그냥 죽는다 → 새 코드는 `ok=(409,)` 로 받아 `GET /v1/betaTesters?filter[email]&filter[apps]` 뒤 그룹 relationship 에 붙인다(재실행 가능).
- `asc-diagnose`: 테스터 없음 메시지가 `::error::` + `testflight-tester.yml` 안내로 바뀌었다. 초대 재발송 로직 동일.
- 네 파일 다 `on: workflow_dispatch` 만(`yaml.safe_load` → `{'workflow_dispatch': None}`), `runs-on: self-hosted`, `tags:` 0건.

### 2.3 테스트가 실제 동작을 보는가

- `tests/test_asc_helper_workflows.py` 의 compliance 6종은 YAML heredoc 을 **그 자리에서 꺼내 `exec`** 하고 `urllib.request.urlopen` 만 대역으로 바꾼다. JWT 는 테스트가 만든 진짜 EC 키로 `openssl dgst -sign` 을 돌린다 — "사람이 답한 값을 안 뒤집는다"(`non_exempt=True`·`False` 둘 다 PATCH 0건), "만료 건너뜀", "앱 없음 exit 1", "빌드 0 exit 0", "빈 secret 이면 호출 0건" 을 각각 결과로 검사한다. 글자 검사가 아니다.
- 나머지 세 워크플로는 구조 검사(트리거·러너·번들 ID·가드 문구·`compile`)만 있다. 쓰기를 하는 `testflight-tester`(POST betaGroups/betaTesters)·`asc-diagnose`(POST betaTesterInvitations)의 409 재실행 경로는 실행 테스트가 없다 — 증거 §4 가 "쓰기를 하는 하나는 돌려 본다" 고 했지만 쓰기를 하는 워크플로는 셋이다(§3 D-41-3).
- `tests/test_release_docs.py` 13개: `### 41.` 절을 **줄 머리** 제목으로 자른다(`re.split(r"\n### \d")`). `Info.plist` 검사는 키 바로 다음 토큰이 `<false/>` 임을 본다(`<true/>` 로 바꾸면 실패한다 — 코드로 확인).

### 2.4 알려진 한계 2행의 ID 실재 확인

| ID | 파일 | 제목(앞부분) |
|---|---|---|
| D-01-3 | `impl-review-01.md` | 공유 파일의 끝에 추가해야 하는 규칙 위반 |
| D-03-1 | `-03` | README 공통 영역을 덧붙이기 대신 직접 수정함 |
| D-04-1 | `-04` | README 공유 API 표의 기존 행 직접 수정 |
| D-05-1 | `-05` | README 공통 설계 판단의 덧붙이기 전용 규칙 위반 |
| D-07-1 | `-07` | 공유 API 표의 끝에만 덧붙이기 규칙 위반 |
| D-19-1 · D-19-2 | `-19` | 임시 env 복사본 검증 명령 `ENV_FILE` 누락 · 변경 전 compose 추출 명령이 현재 HEAD |
| D-19-3 | `-19` | RELEASE 의 공통 본문을 자기 번호 소제목 밖에 작성 |
| D-40-1 | `-40` | `docs/RELEASE.md` 에서 티켓 35 의 행을 고쳤다 |

## 3. 결함

### D-41-1 — MINOR — "키를 파일로 떨어뜨리지 않는다" 는 서술이 과장이고, 테스트가 그 주장을 검증하지 않는다

- 파일: `.github/workflows/asc-status.yml:12`·`:56-60`(네 파일 동일 위치), `docs/RELEASE.md` `#### 41.3` 첫 문단, `tests/test_asc_helper_workflows.py:94-101`.
- 재현: `token()` 은 P8 개인키를 `tempfile.NamedTemporaryFile(delete=False)` 로 **디스크에 쓰고** `openssl dgst -sign` 뒤 `os.unlink` 한다. 정상 경로에서는 수 ms 뒤 지워지지만, `subprocess.run` 이 예외를 내면(`openssl` 없음 → `FileNotFoundError`) `os.unlink` 에 못 가 `/tmp/*.p8` 가 self-hosted 맥에 남는다. 기대: 문서가 "지울 것이 없다" 고 말하려면 파일을 안 쓰거나 `try/finally` 로 지워야 한다. 실제: 문서·머리말은 "파일로 떨어뜨리지 않는다 / 지울 필요가 없는 쪽" 이라 적고, `test_no_helper_writes_the_api_key_to_disk` 는 `api_key.json` 문자열 부재만 본다 — 임시 P8 는 못 잡는다.
- 영향: `asc-submit.yml` 도 같은 `token()` 을 쓰므로 새로 생긴 위험은 아니고, self-hosted 맥에 `openssl` 은 있다. 사용자 영향 0. 서술을 "fastlane 용 `api_key.json` 을 만들지 않는다(JWT 서명용 P8 임시 파일은 서명 직후 지운다)" 로 정확히 하거나 `try/finally` 로 바꾸면 끝.

### D-41-2 — MINOR — RELEASE 가 더한 사람 항목 2건이 정본 `user-todo.md` 에 없고, 증거 §11 은 있는 것처럼 적었다

- 파일: `docs/RELEASE.md:204-208`(D3 "수출 규정 답변 확인"), `:263`(variables 표 `TESTFLIGHT_TESTER_EMAIL`), `review/impl-evidence-41.md` §11 표 `#14`·`#18` 행.
- 재현: `grep -n -E "수출|암호화|TESTFLIGHT_TESTER" .scratch/store-launch/user-todo.md` → 0건. 그런데 증거 §11 은 `#14` 에 "**새 variable `TESTFLIGHT_TESTER_EMAIL`**", `#18` 에 "**수출규정 답변 확인**(새 항목)" 을 적어 정본에 이미 있는 듯 읽힌다. 또 새 D3 항목은 이웃 항목들과 달리 `(\`#18\`)` 꼬리가 없다(`:204-208`; 같은 블록의 다른 항목은 `:197`·`:208 전후` 처럼 번호를 단다).
- 영향: `user-todo.md` 가 "상태의 정본" 이라(`test_the_human_order_does_not_duplicate_user_todo_state`) 운영자가 그 파일만 보면 두 일을 모른다. 티켓 41 은 `.scratch/` 수정 금지였으므로 **고칠 자리는 코디네이터**다 — `#14` 에 variable 1개, `#18` 에 수출규정 확인을 더하고, RELEASE D3 항목에 `(\`#18\`)` 을 달면 끝. 증거 §11 두 행의 문구도 "정본 반영 필요" 로 고치는 게 맞다.

### D-41-3 — MINOR — 쓰기를 하는 워크플로 셋 중 하나만 실행 테스트가 있다

- 파일: `tests/test_asc_helper_workflows.py`(compliance 만 `exec`), `.github/workflows/testflight-tester.yml:119-140`, `asc-diagnose.yml:129-137`.
- 재현: `testflight-tester` 의 409 → `GET filter[email]` → `POST relationships/betaTesters` 분기는 이 티켓이 BASELINE 에 **새로 쓴 로직**인데, 테스트는 `compile()` 과 문구 검사만 한다. 예컨대 `existing['data']` 가 비었을 때 `sys.exit(1)` 로 가는지, 그룹을 새로 만든 경로에서 `group_id` 가 relationship 에 들어가는지 돌려 보지 않는다. `asc-diagnose` 의 초대 POST 도 같다. 기대(증거 §4·리뷰 35 인용): "글자만 보는 테스트는 실패 경로를 못 잡는다" 는 원칙을 쓰기 워크플로 전부에 적용. 실제: 하나만.
- 영향: 두 워크플로는 사람이 수동으로 부르고 결과를 로그로 보며, 실패해도 ASC 상태를 망가뜨리진 않는다(그룹 생성·테스터 추가·초대는 멱등에 가깝다). 다음 라운드에서 compliance 와 같은 `FakeAsc` 로 2~3 케이스 더하면 된다.

### D-41-4 — MINOR — 코디네이터 결정 밖의 공유 영역 수정 3곳 (공유 파일 규칙)

- 파일: `docs/RELEASE.md:47-49`(prod 첫 배포 체크 항목에 `### 41.` 포인터 추가), `:164-166`(D3 "NAS develop 폴더" 항목에 포인터 추가), `:237`(secrets 표 `APP_STORE_CONNECT_API_KEY` 기존 행의 "쓰는 곳" 칸 수정).
- 재현: 결정 5(알려진 한계 2행)·6(3곳) 이 허용한 자리와 자기 절 `### 41.`·새 표 행·새 D3 항목을 빼면 위 세 곳이 남는다. 규칙(`impl-review-01.md` D-01-3): 공유 파일은 자기 절/행을 **덧붙이고** 공통 위치 수정은 코디네이터에게.
- 영향: 셋 다 내용이 맞고(포인터 2개는 유용, 표 수정은 정확성에 필요) 병렬 티켓이 더 없어 충돌 위험도 없다. 결함으로 올리는 이유는 일관성이다 — 이 티켓이 바로 그 종류의 위반 7건을 "알려진 한계" 로 집계하면서 자기 몫을 세지 않았다. 코디네이터가 승인하고 그 행을 "8건(+D-41-4)" 로 바꾸거나, 승인 기록만 남기면 끝.

BLOCKER 0, MAJOR 0, MINOR 4.

## 4. 결함이 아닌 것 (살펴본 뒤 넘긴 것)

- **보조 워크플로 4개가 스펙에 없다**: Phase 6 기준표 항목이고 코디네이터 결정 1 이 포팅을 지시했다. 범위 밖 변경이 아니다.
- **`asc-build-compliance` 가 `True` 인 빌드를 안 건드린다**: 결정대로. 테스트가 실제로 잡는다(§2.3).
- **`testflight-tester` 의 `filter[apps]` 조회가 비면 exit 1**: 테스터가 다른 앱에만 등록된 경우 409 인데 이 앱 필터로는 0건일 수 있다. BASELINE 은 그냥 죽었으니 후퇴가 아니고, 메시지가 콘솔 확인을 안내한다.
- **`asc-diagnose` 가 돌 때마다 초대를 다시 보낸다**: 이름·머리말·RELEASE 표가 "초대 (재)발송" 이라 적어 의도가 드러난다.
- **알려진 한계 표에 "해소됐다" 행이 남아 있다**: `test_known_limitations_section_collects_the_merged_minors` 가 `티켓 40` 문자열을 요구하고, 행에 실제 남은 한계(기본 AVD `/data` 가득)가 있다. 적절하다.
- **`Info.plist` 주석 안의 `**` 마크다운**: XML 주석이라 무해, `plutil -lint` OK.
- **`SKAdNetworkItems`·`GADApplicationIdentifier` 테스트 ID 미변경**: 티켓 31·user-todo `#12` 영역, 증거 §10 이 이유를 적었다. 동의.
- **`webview_flutter_wkwebview` 가 lock 에 새로 들어왔다**: D-40-2 가 나열하지 않은 플러그인이지만 `pubspec.lock` 의 기존 의존성이라 정상.

## 5. 참고 (취향·다음 사람을 위한 메모)

- `#### 41.4` "새 클론에서 Xcode 로 열기 전에 `pod install` 한 번" — 그 앞에 `flutter pub get` 이 없으면 Podfile 이 `Generated.xcconfig must exist` 로 멈춘다(§2.1 에서 실제로 겪었다). 한 줄 보강하면 좋다.
- `github.event.inputs.email` 대신 `inputs.email` 로 써도 같다. 스타일.
- 네 워크플로가 JWT·`api()` 60여 줄을 각자 복사하고 있다(`asc-submit.yml` 포함 5벌). 헬퍼 액션/스크립트로 모을 수 있지만 "워크플로 하나가 자기 안에서 다 보인다" 는 장점도 있어 결함으로 안 본다.
- `pod install` 경고 2건(Profile xcconfig·FirebaseCore SPM 권고)은 증거 §8.1 설명대로 빌드를 막지 않는다. 내 빌드에서도 같은 경고, exit 0.

판정: PASS
