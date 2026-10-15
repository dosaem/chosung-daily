# 티켓 41 구현 증거 — Phase 6 배포 준비 최종 점검·보완

- 대상: `dosaem/t41-phase6-release-readiness`, 로컬 `main` `a766bc0`(티켓 01~40 전부 머지됨) 위.
- 한 일: Phase 6 기준표로 레포를 **전수** 대조하고(§1), 누락·부분 4건을 채웠다(§2~§5),
  미수정 MINOR 를 모아 "알려진 한계" 와 대조했다(§6), 티켓 40 머지로 거짓이 된 서술
  3곳을 고쳤다(§7). 앱·서버 기능은 바꾸지 않았다.
- 판단 6건은 코디네이터에게 한 번에 물어 답을 받고 그대로 했다(§9).
- 시크릿 값은 적지 않는다 — 이름만. DB 접속 문자열은 호스트·DB 이름만 적는다.

## 1. Phase 6 기준표 전수 대조

TARGET = web + mobile, SERVER = nas. 표본이 아니라 기준표의 **모든** 항목이다.
"근거" 는 내가 직접 열어 확인한 파일·줄이다.

### 1.1 공통

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| 1 | `docs/RELEASE.md` 에 사람 단계 체크리스트 | 충족 | `docs/RELEASE.md:33`(첫 배포 prod) · `:51`(develop) · `:61`(사람 작업 순서 D0~D3) · `:269`(실기기 체크리스트 통합). 티켓 37 이 통합한 세 목차가 다 있다 |
| 2 | 시크릿 **이름** 목록 | 충족 | `docs/RELEASE.md:215` 표 21행(secret) + `:246` 표 10행(variable). 값은 없다 — `tests/test_release_docs.py::test_secret_index_does_not_carry_values` 가 지킨다 |
| 3 | 목록이 워크플로 실제 사용과 일치 | 충족(이 티켓이 갱신) | `test_secret_index_covers_every_secret_the_workflows_use`·`..._variable_...` 가 `.github/workflows/*.yml` 의 `secrets.*`·`vars.*` 를 전수로 비교한다. 새 워크플로 4개가 쓰는 `vars.TESTFLIGHT_TESTER_EMAIL` 을 표에 더했다(§4) |
| 4 | `.env.example`(백엔드 있음) | 충족 | `.env.example`(140행) + `.env.prod.example` + `.env.develop.example` 3개 |
| 5 | CI 트리거 = 브랜치 푸시 | 충족 | `ci.yml:3-6`·`flutter-ci.yml:3-12`·`flutter.yml:11-14` 전부 `push: branches: [main, develop]`(+ `pull_request`). `deploy.yml:9-13` 은 `workflow_run`(CI 성공 뒤) |
| 6 | develop → 테스트 배포 | 충족 | `flutter.yml:157` APK → `:177` Firebase App Distribution(`is_prod == 'false'`). 서버는 `deploy.yml:30` `TARGET=develop` → `deploy/deploy.sh:81-86` |
| 7 | main → 스토어 내부 트랙 | 충족 | `flutter.yml:161` AAB → `:197` `r0adkll/upload-google-play`, `track: internal` |
| 8 | **태그 푸시 배포 없음** | 충족 | 워크플로 **10개 전체**에서 `tags:` 0건(전수 grep, 이 티켓이 더한 4개 포함). 트리거는 `push:branches` 3개(`ci`·`flutter-ci`·`flutter`) · `pull_request` 2개 · `workflow_run` 1개 · `workflow_dispatch` 6개뿐 |
| 9 | PR 대상 `flutter analyze` + `flutter test` 잡 | 충족 | `flutter-ci.yml:9-12`(`pull_request`, paths `mobile/**`) · `:48` analyze · `:51` test |
| 10 | 그 잡이 `ubuntu-latest` | 충족 | `flutter-ci.yml:16` |
| 11 | 그 잡이 **빌드 잡과 분리** | 충족 | 별 파일이다. `flutter.yml:7-8` 이 이유를 적었다("러너가 사용자 맥 한 대라서 PR 마다 그 맥을 묶지 않으려고 나눴다"). `flutter.yml` 에 analyze·test 스텝 0건 |

### 1.2 mobile — `flutter.yml`

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| 12 | Android develop = APK → Firebase App Distribution | 충족 | `flutter.yml:157`·`:177` (위 6) |
| 13 | Android main = AAB → Play internal | 충족 | `flutter.yml:161`·`:197` (위 7) |
| 14 | AAB strip 검증 블록 **유지** | 충족 | `flutter.yml:161-176` — `rm -f` 로 지난 AAB 먼저 지우고, `|| echo` 로 오탐 삼킨 뒤 `test -f` + `python3 tool/verify_appbundle.py`(`:175`) |
| 15 | iOS `match appstore --readonly` | 충족 | `flutter.yml:313-316`, `--readonly` 와 `--keychain_name`·`--api_key_path` 함께 |
| 16 | 격리 keychain | 충족 | `flutter.yml:301-311` — `ci-$GITHUB_RUN_ID.keychain` 생성 → `$GITHUB_ENV` 로 이름 넘김 → `:355` `if: always()` 에서 `security delete-keychain` |
| 17 | `build ipa` | 충족 | `flutter.yml:322-325`, `--export-options-plist=ios/ExportOptions.plist` |
| 18 | `altool` TestFlight | 충족 | `flutter.yml:327-344` — `api_key.json` 에서 P8 을 꺼내 `trap` 으로 지우고 `xcrun altool --upload-app`(`:342`). fastlane pilot 폴링 버그 회피 |
| 19 | self-hosted 러너 | 충족 | `flutter.yml:35`(setup) · `:85`(android) · `:231`(ios) |
| 20 | `appstore-metadata`(dispatch) | 충족 | `.github/workflows/appstore-metadata.yml:11-12`, 업로드 전 `verify_store_screenshots.py ios`(`:53`) |
| 21 | `asc-submit`(dispatch) | 충족 | `.github/workflows/asc-submit.yml:14-28`(`build_number`·`app_version`·`dry_run` 입력) |
| 22 | `asc-status`(dispatch) | **누락 → 채웠다** | §3. `.github/workflows/asc-status.yml` 신규 |
| 23 | `asc-build-compliance`(dispatch) | **누락 → 채웠다** | §3. `.github/workflows/asc-build-compliance.yml` 신규 |
| 24 | `asc-diagnose`(dispatch) | **누락 → 채웠다** | §3. `.github/workflows/asc-diagnose.yml` 신규 |
| 25 | `testflight-tester`(dispatch) | **누락 → 채웠다** | §3. `.github/workflows/testflight-tester.yml` 신규 |

왜 22~25 가 비어 있었나: 티켓 35 가 "BASELINE 복사 목록 중 티켓이 지정한 대상만"
가져왔고(`review/impl-evidence-35.md:29`·`:49`), 네 개는 `.scratch/store-launch/spec.md`
에도 이름이 없다(전수 grep 0건). 기준표에만 있던 항목이다.

### 1.3 mobile — fastlane · 네이티브 설정 · 스토어 자산

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| 26 | android fastlane | 충족 | `mobile/android/fastlane/{Appfile,Fastfile}`. `Appfile` 은 `package_name("com.dosaem.chosung")`, 키 파일은 gitignore |
| 27 | android metadata(ko/en) | 충족 | `metadata/android/{ko-KR,en-US}/` 각각 `title.txt`·`short_description.txt`·`full_description.txt` + `images/{icon,featureGraphic}.png` + `phoneScreenshots` 5장 + `tenInchScreenshots` 5장 |
| 28 | ios fastlane | 충족 | `mobile/ios/fastlane/{Appfile,Fastfile,Matchfile,app_privacy_details.json}`. `Matchfile` = `git_url` + `type("appstore")` + `app_identifier("com.dosaem.chosung")` |
| 29 | ios metadata(ko/en) | 충족 | `metadata/{ko,en-US}/` 각 8파일(description·keywords·name·subtitle·promotional_text·release_notes·privacy_url·support_url) + 공용 `copyright.txt`·카테고리 3개 + `review_information/` |
| 30 | `ios/ExportOptions.plist` | 충족 | `mobile/ios/ExportOptions.plist` — `method=app-store-connect`, `signingStyle=manual`, 프로파일 이름 `match AppStore com.dosaem.chosung`(워크플로·`project.pbxproj` 와 같은 문자열) |
| 31 | `build.gradle.kts` key.properties | 충족 | `mobile/android/app/build.gradle.kts:12-18` — 있으면 읽고 없으면 빈 Properties |
| 32 | 〃 `signingConfigs.release` | 충족 | 같은 파일 `:50-61`, `:70` 이 없을 때 debug 키로 떨어진다(로컬·새 클론용) |
| 33 | 〃 `debugSymbolLevel FULL` | 충족 | 같은 파일 `:72-77` (위 14 의 strip 오탐과 한 쌍) |
| 34 | `android/key.properties.example` | 충족 | `mobile/android/key.properties.example` 8행, 값은 자리표시자 |
| 35 | 스크린샷 스크립트 | 충족 | `scripts/store_screenshots.sh`(iOS 시뮬 3종 + Android 에뮬) + `mobile/tool/verify_store_screenshots.py`(업로드 전 검사) |
| 36 | iPad 13" 스크린샷 | 충족 | `mobile/ios/fastlane/screenshots/{ko,en-US}/ipad13_*.png` 각 5장(2064×2752). 내가 돌린 검사 `ios`·`play` 둘 다 종료 0(§8.1) |
| 37 | 수출 규정(암호화) 신고 | **누락 → 채웠다** | §5. `mobile/ios/Runner/Info.plist` 에 `ITSAppUsesNonExemptEncryption=false`. 기준표의 "ASC 개인정보 라벨/첫 출시 버튼" 과 같은 제출 선행 조건인데 레포·RELEASE 양쪽에 없었다 |

### 1.4 백엔드 (SERVER = nas)

| # | 기준 | 판정 | 근거 |
|---|---|---|---|
| 38 | docker-compose prod | 충족 | `docker-compose.prod.yml` 6서비스(mysql·redis·app·worker·beat·backup) |
| 39 | docker-compose develop | 충족 | **같은 파일을 공유한다** — 환경 차이는 프로젝트명·`APP_PORT`·env 파일 3개뿐(`docker-compose.prod.yml:1-17` 머리말, `docs/RELEASE.md:7` 표) |
| 40 | compose 프로젝트명(`-p`) 명시 | 충족 | `docker-compose.prod.yml:7-10`(실행 예시) · `deploy/deploy.sh:93`(`-p "$project"`) · `docs/RELEASE.md:19-27`. 최상위 `name:`·`container_name` 을 **일부러 안 둔다**(`:12-16`) |
| 41 | 배포 스크립트 | 충족 | `deploy/deploy.sh` 190행 — fetch → CI sha 가 아직 브랜치 끝인지 확인 → `merge --ff-only` → `up -d --build` → 마이그레이션 → 서비스 전수 확인 → `/health` |
| 42 | webhook/Tailscale | 충족 | `.github/workflows/deploy.yml:42-45` `tailscale/github-action@v3` → `:64-70` `ssh … bash -s` 로 스크립트를 **표준입력으로** 넘긴다(`deploy.sh:13-23` 이 이유) |
| 43 | 헬스체크 | 충족 | `deploy/deploy.sh:159`·`:171-182` — 상태 코드를 **직접 비교**(`curl -f` 로는 302 가 성공으로 끝난다), 10회 재시도. compose 쪽 `mysql`·`redis` healthcheck + `depends_on: service_healthy`. app 은 `deploy.sh:147-152` 가 `config --services` 전수와 `ps --filter status=running` 을 비교해 본다 |
| 44 | DB 마이그레이션 절차 | 충족 | 자동: `deploy/deploy.sh:142`. 사람: `docs/RELEASE.md:46`. 헤드 1개 보장: `ci.yml:59` → `scripts/check_migration_heads.sh`. 왕복 검증: `tests/test_migrations.py`(별도 DB) |
| 45 | cloudflared 라우팅 절차 문서 | **부분 → 채웠다** | §2. 전에는 `docs/RELEASE.md:47` 한 줄("8089 로 붙는지 확인")과 `docker-compose.prod.yml:65` 주석뿐이고, develop 호스트네임을 터널에 붙이는 절차가 없었다 → `### 41.1` |
| 46 | 포트가 ENV 사용 중 목록과 안 겹침 | 충족(사람 확인 항목) | `docs/RELEASE.md:14` 표(prod 8089 / develop 8090, "NAS 실측으로 확정, 스펙 미정 8") + `:57` develop 첫 배포 체크("`APP_PORT` 가 prod 와 겹치지 않는지 NAS 에서 확인"). 레포에 NAS 포트 대장은 없다 — 프로덕션 접근 금지라 내가 확인할 수 없고, `### 41.1` 에 `lsof` 로 다시 보는 명령을 적었다 |

### 1.5 사람 항목이 RELEASE 에 빠짐없이 있는가

| 사람 항목 | RELEASE 위치 | user-todo 번호 |
|---|---|---|
| Apple(Developer 가입·App ID·Sign in with Apple·Server API 키·Sandbox) | `:102-107` D1 | `#10` |
| Play(앱 생성·서비스 계정·라이선스 테스터·첫 AAB 수동 업로드) | `:108-110` D1 | `#11` |
| keystore(생성·백업·잃으면 재설정) | `:151-154` D2 | `#14` |
| GitHub secrets / variables | `:215`·`:246` 두 표 + D2 `:151` | `#14` |
| self-hosted 러너 | `:151-154` D2 | `#14` |
| 테스터(TestFlight·Firebase 그룹·Play 라이선스) | `:108` D1 · `### 34.`·`### 41.3` | `#10`·`#11` |
| ASC 개인정보 라벨 | `:155-157` D2(`app_privacy_details.json`·`docs/play-data-safety.md`) + `:182` D3 대조 | `#18` |
| 첫 출시 버튼 | `:212-214` D3("사용자만 누른다") | `#18` |
| 수출 규정 답변 확인 | **`:204-208` D3(이 티켓이 더했다)** | `#18` |

빠진 사람 항목은 없다. `tests/test_release_docs.py` 가 ① 워크플로가 쓰는 secret·
variable 전부가 목차에 있는지 ② D0~D3·목차가 가리키는 `### NN.` 절이 실재하는지
③ 실기기 항목마다 기대 결과(`→`)가 있는지 ④ D0~D3 가 user-todo `#1~#18` 을 전부
가리키는지를 본다 — 내가 더한 줄도 그 검사를 통과한다(§8.2).

## 2. 보완 ① cloudflared 라우팅 절차 (`### 41.1`)

`docs/RELEASE.md` 에 `### 41.` 절을 더하고 그 안 `41.1` 에 적었다. NAS 에 접근하지
않았으므로 **현재 터널이 어느 방식인지 내가 단정하지 않는다** — 먼저 방식을 가르는
방법(`docker ps | grep cloudflared` 의 실행 명령에 `--config` 가 있는지)을 적고, 두
방식을 다 적었다.

- 대시보드 관리형: Zero Trust → Networks → Tunnels → Public Hostnames 에 추가, DNS 자동.
- `config.yml`: `ingress` 에 `service: http_status:404` **앞**으로 넣고(그 줄이 마지막이
  아니면 뒤의 규칙이 영원히 안 맞는다), `cloudflared tunnel ingress validate` 로 보고,
  호스트네임마다 `cloudflared tunnel route dns` 를 한 번 돌려 CNAME 을 만든다.
- 레포가 정하는 값만 못박았다: prod `chosung.dosaem.com` → `http://127.0.0.1:8089`,
  develop(호스트네임은 운영자) → `http://127.0.0.1:8090`. 정해진 develop 주소는
  `API_BASE_URL_DEV` variable 로 간다(비면 `flutter.yml` setup 이 빌드를 멈춘다).
- 붙었는지 확인: NAS 안 `curl 127.0.0.1:8090/health` 와 바깥 `curl https://<호스트>/health`
  를 **둘 다** 본다 — 바깥만 실패면 터널, 둘 다 실패면 컨테이너다.
- 포트 재확인 명령(`lsof -nP -iTCP -sTCP:LISTEN | grep 809`)과 "겹치면 `APP_PORT` 와
  터널 라우팅을 **같이** 고친다(한쪽만 고치면 502)" 를 같이 적었다.

관련 줄 2곳도 이 절을 가리키게 했다: `docs/RELEASE.md:47`(prod 첫 배포) ·
`:164-166`(D3 "NAS develop 폴더·DNS·터널").

## 3. 보완 ② ASC 보조 워크플로 4개

BASELINE(`~/Code/BuildUrPalace/.github/workflows/`)을 복사해 번들 ID 를
`com.dosaem.chosung` 으로 바꾸고, JWT·`api()` 모양은 이 레포의 `asc-submit.yml:85-137`
과 같게 맞췄다. 전부 `workflow_dispatch` 전용 · `self-hosted` · 기존
`APP_STORE_CONNECT_API_KEY` 하나만 쓴다.

| 파일 | 하는 일 | BASELINE 과 **다르게** 한 것 |
|---|---|---|
| `asc-status.yml` | 버전·제출 상태 조회(읽기 전용) | 빈 secret 가드, 앱이 ASC 에 없을 때 `data[0]` IndexError 대신 "먼저 앱을 만든다" 로 멈춘다 |
| `asc-build-compliance.yml` | 최신 10빌드의 `usesNonExemptEncryption` 이 **비어 있을 때만** `false` 로 채운다 | 값이 이미 있는 빌드를 건드리지 않는다(사람이 콘솔에서 `true` 로 답한 빌드를 `false` 로 뒤집으면 거짓 신고다). 빌드 0개면 조용히 끝낸다, `patched N` 을 찍는다 |
| `testflight-tester.yml` | 내부 베타 그룹을 찾거나 만들고 테스터 1명을 넣는다 | 이메일 기본값을 **레포에서 뺐다**(아래). 이미 등록된 테스터의 409 를 실패로 보지 않고 그룹에만 붙인다 — 다시 돌릴 수 있다 |
| `asc-diagnose.yml` | 그룹·테스터·최신 빌드 상태를 찍고 초대를 다시 보낸다 | 같은 이메일 규칙. 테스터가 없을 때의 오류 문구가 `testflight-tester.yml` 을 가리킨다 |

세 가지를 BASELINE 과 다르게 했다.

1. **개인 이메일을 레포에 안 둔다.** BASELINE 은 운영자 주소를 워크플로 `default:` 에
   박아 뒀다. 입력을 비우면 `vars.TESTFLIGHT_TESTER_EMAIL` 을 쓰고 둘 다 비면 멈춘다
   (`asc-submit.yml` 이 심사 연락처를 secret 으로 옮긴 것과 같은 이유). 그 variable 을
   `docs/RELEASE.md:246` 표에 더했다.
2. **ASC 키를 파일로 떨어뜨리지 않는다.** 네 개는 fastlane 을 안 쓰므로 환경변수에서
   바로 읽는다. self-hosted 러너는 잡이 끝나도 사용자 맥이 남기 때문에, 지울 필요가
   없는 쪽이 `Cleanup key` 스텝을 믿는 쪽보다 안전하다(`appstore-metadata.yml:68-70`
   은 fastlane 때문에 파일이 필요해서 그 스텝을 둔다).
3. **빈 secret 가드.** 없으면 `json.loads('')` 가 뜻 모를 예외로 죽는다 —
   `::error::APP_STORE_CONNECT_API_KEY secret 이 없다` 로 먼저 멈춘다.
4. `urllib.error`·`urllib.parse` 를 **명시적으로 import** 했다. BASELINE 은
   `import urllib.request` 만 하고 `urllib.error` 를 쓴다 — `urllib.request` 가 내부에서
   끌어오기 때문에 우연히 도는 코드다.

## 4. 보완 ③ 테스트 (글자 검사 + 실제 실행)

`tests/test_asc_helper_workflows.py` 36개. 리뷰 35 가 "워크플로 **글자**만 보는 테스트
는 실패 경로를 하나도 못 잡았다" 고 적었으므로, 쓰기를 하는 하나는 **돌려 본다**.

- 구조(네 개 공통 8종 × 4): `workflow_dispatch` 전용(푸시로도 돌면 ASC 쓰기가 자동으로
  나간다) · `self-hosted` · 번들 ID 가 `com.dosaem.chosung` 이고 `buildurpalace` 가 없음 ·
  빈 secret 가드 · `api_key.json` 을 안 씀 · `@gmail.com`/`@dosaem.com` 문자열 0건 ·
  이메일이 variable 로 떨어짐(2개) · heredoc Python 이 `compile` 됨.
- 실행(`asc-build-compliance.yml` 6종): YAML 의 heredoc 을 꺼내 `exec` 한다(복사본을
  두면 워크플로가 바뀔 때 조용히 낡는다). 바깥으로 나가는 `urllib.request.urlopen`
  하나만 메모리 대역으로 막고, JWT 서명은 테스트가 그 자리에서 만든 EC 키로 진짜
  `openssl` 을 쓴다 — 네트워크·계정 없음. 검사: 비어 있는 빌드만 채운다 / **사람이
  답한 값을 안 뒤집는다** / 만료 빌드를 건너뛴다 / 앱이 없으면 exit 1 / 빌드 0개면
  exit 0 / 빈 secret 이면 호출 0건으로 exit 1.

`tests/test_release_docs.py` 에 13개를 더했다 — `### 41.` 이 두 관리 방식·두 포트·
`API_BASE_URL_DEV`·`http_status:404`·`route dns` 를 적었는지, 포트 재확인 방법이 있는지,
수출규정 `false` 의 **근거**(OS 제공 HTTPS·`flutter_secure_storage`)가 적혀 있는지,
`Info.plist` 에 그 키가 `<false/>` 로 있는지, 네 워크플로가 실재하고 문서에 색인됐는지,
D-40-2 기록이 있는지. 절을 자를 때는 **줄 머리의** `\n### 41.` 로 끊는다 — 다른 절이
`"### 41."` 을 가리키기만 해도 거기서 자르면 엉뚱한 토막을 읽는다.

"알려진 한계" 수집 테스트의 parametrize 에 이 티켓이 더한 ID 9개를 넣었다(§6).

## 5. 보완 ④ 수출 규정(암호화) 신고

`mobile/ios/Runner/Info.plist` 에 `ITSAppUsesNonExemptEncryption=false` 를 넣었다
(주석으로 근거 포함). 없으면 TestFlight 에 올라간 빌드가 전부 "Missing Compliance" 로
들어가고, 사람이 빌드마다 ASC 콘솔에서 답할 때까지 심사 제출이 열리지 않는다.

**`false` 인 근거(전수 확인).** 이 앱이 쓰는 암호화는 OS 가 제공하는 것뿐이다.

- `pubspec.yaml` 20개 의존성에 암호 라이브러리가 **없다** — `crypto`·`pointycastle`·
  `encrypt`·`cryptography` 전부 0건.
- `mobile/lib/` 전체 grep 에서 `package:crypto`·AES·`sha256`·`Hmac` 호출 0건. 유일한
  일치는 `lib/guest/guest_token_store.dart:32` 의 **주석**이고, 그 저장은
  `flutter_secure_storage`(iOS Keychain / Android KeyStore)에 맡긴다.
- 네트워크는 `dio` → `URLSession` 의 HTTPS 뿐이다.

둘 다 Apple 의 면제 범주다. BASELINE(같은 개발자의 광고 포함 Flutter 앱)도 같은
구성에서 `<false/>` 로 출시했다(`~/Code/BuildUrPalace/ios/Runner/Info.plist:29-30`).
`plutil -lint` 통과, `PlistBuddy -c "Print :ITSAppUsesNonExemptEncryption"` → `false`.

판단이라서 두 가지를 같이 뒀다: ① `### 41.2` 에 근거와 "자체 암호화를 들이면 이 값과
이 절을 같이 고치고 연간 자기분류 보고 필요 여부를 다시 본다" ② D3 체크리스트
(`docs/RELEASE.md:204-208`)에 "첫 제출 때 콘솔의 답이 면제로 들어갔는지 한 번 보고,
그 전에 올린 빌드가 Missing Compliance 로 남아 있으면 `asc-build-compliance.yml` 로
메운다".

**안 한 것**: `SKAdNetworkItems`(BASELINE 에는 있다). 광고 기여도 측정용이고 제출을
막지 않는다 — 광고를 맡는 티켓 31 의 영역이라 이 티켓에서 넣지 않았다(§10-2).

## 6. 미수정 MINOR 전수 수집 → "알려진 한계" 대조

`review/impl-review-*.md` 40개에서 `D-NN-M` 전부(76개)를 뽑아, 같은 ID 가 어느
문서에서 `FIXED` 로 판정됐는지 기계적으로 가른 뒤 한 건씩 눈으로 확인했다.

**고치지 않고 머지한 MINOR 17건**: D-01-3(일부) · D-03-1 · D-04-1 · D-05-1 · D-07-1 ·
D-17-6 · D-19-1 · D-19-2 · D-19-3 · D-31-8 · D-33-3 · D-38-1 · D-38-2 · D-39-1 ·
D-39-2 · D-40-1 · D-40-2.

| 상태 | ID | 처리 |
|---|---|---|
| 이미 표에 있다 | D-31-8 · D-33-3 · D-38-1 · D-38-2 · D-39-1 · D-17-6 | 그대로 뒀다 |
| 이미 해소됐다 | D-39-2 | 티켓 37 이 스펙 범위를 `01~40` 으로 고쳤다(`spec.md:404`, `test_the_spec_ticket_range_includes_the_tickets_added_after_planning` 이 지킨다) → 한계가 아니다 |
| 이 티켓이 고쳤다 | D-40-2 | §7.2 → 한계가 아니다 |
| **빠져 있었다 → 더했다** | D-01-3(일부)·D-03-1·D-04-1·D-05-1·D-07-1·D-19-3·D-40-1 | 1행으로 묶었다 — "공유 파일 규칙 위반 7건". 전부 티켓이 공유 파일(README·RELEASE)의 자기 번호 절 밖을 고친 건으로 사용자 영향 0 이고, 이미 표에 있는 D-38-2 와 같은 종류다 |
| **빠져 있었다 → 더했다** | D-19-1·D-19-2 | 1행으로 묶었다 — "`### 19.` 검증 명령 재현성". 이미 끝난 1회 로컬 검증 기록의 명령을 지금 그대로 재현할 수 없다. 배포 절차는 그 명령을 쓰지 않는다 |

묶은 이유: 9행을 따로 넣으면 운영자가 출시일에 읽는 표가 "사용자 영향 0 인 문서
경계 위반" 으로 절반을 차지한다. 코디네이터에게 묻고 2행으로 하라는 답을 받았다(§9-5).
두 행 모두 근거 리뷰 파일을 가리켜서 `test_known_limitations_rows_cite_where_the_judgement_is_written`
을 지킨다.

**기능 결함은 찾지 못했다.** 이 티켓 범위(배포 준비)에서 앱·서버 기능 결함을 새로
발견한 것은 없다. 위 표의 미수정 MINOR 중 기능 영향이 있는 것(D-31-8·D-33-3·D-17-6·
D-39-1)은 이미 표에 있고 전부 해당 리뷰가 MINOR·PASS 로 판정한 것이다.

## 7. 티켓 40 머지로 거짓이 된 서술 3곳 + D-40-2

### 7.1 거짓이 된 서술 (고쳤다)

티켓 40 은 머지됐다(`d73b1b2`). 그런데 RELEASE 는 아직 "진행 중" 으로 적고 있었고,
그중 한 줄은 **출시를 막는 거짓**이었다.

| 위치 | 전 | 후 |
|---|---|---|
| "알려진 한계" Play 폰 스크린샷 행 | "레포의 10장이 iPhone 캡처의 바이트 복사본이라 업로드 검사에서 막힌다 / `fastlane release` 가 실패한다 / 40 이 재촬영 중" | **해소됨**(`d73b1b2`, 검사 둘 다 종료 0)으로 바꾸고, 실제로 남은 한계(다시 찍을 때 기본 AVD 는 `/data` 가 차서 `ANDROID_AVD` 로 여유 있는 AVD 를 가리켜야 한다)만 남겼다 |
| D3 체크리스트 "최종 스크린샷 재촬영(티켓 40, 진행 중)" | 미완료 `- [ ]` + "40 머지 후 반영한다" | `- [x]` + 취소선, "사람이 더 찍을 것은 없다 — 업로드로 바로 간다". `### 35.`(이미 `[x]`)와 같은 모양이다 |
| `### 37.` 마지막 문단 | "티켓 40 은 진행 중이라 자리만 두고, 결과는 40 이 머지된 뒤 적는다" | 머지 사실과 `### 40.` 절을 가리키게 하고, 티켓 41 이 `### 41.` 에 적은 것을 한 줄 더했다 |

근거: 내가 돌린 `mobile/tool/verify_store_screenshots.py ios`·`play` 둘 다 종료 0(§8.1),
`review/impl-review-40.md` §2.1·§2.2, `git log` 의 `d73b1b2`.

이 세 곳은 다른 티켓이 쓴 줄이라 고치기 전에 코디네이터에게 물어 답을 받았다(§9-6).

### 7.2 D-40-2 — `Podfile.lock` 이 낡았다 (고쳤다)

`cd mobile/ios && pod install`(네트워크 다운로드 허용) → 40 pods 설치.
`mobile/ios/Podfile.lock` 이 +100행 되고 티켓 30~33 이 더한 플러그인이 다 들어왔다:
`google_mobile_ads`·`google_sign_in_ios`·`sign_in_with_apple`·`in_app_purchase_storekit`·
`flutter_timezone`·`app_settings`·`sentry_flutter`·`share_plus` 각 5회(전에는 0회).

그다음 `flutter build ios --no-codesign` → **exit 0**, `✓ Built build/ios/iphoneos/Runner.app
(42.7MB)`, Xcode build 64.6s(§8.1).

**같이 바뀐 파일 2개와 그 이유.** 커밋된 `Runner.xcodeproj/project.pbxproj` 에
CocoaPods 통합이 **아예 없었다** — `[CP]` 스텝이 HEAD 에 0개다(`git show HEAD:… | grep -c
'\[CP\]'` → 0). `pod install` 이 그걸 채우면서 `project.pbxproj`(+138행: Pods 그룹·
`Pods_Runner.framework`·`[CP] Check Pods Manifest.lock`·`[CP] Embed Pods Frameworks`·
`[CP] Copy Pods Resources`·xcconfig 파일 참조)와
`Runner.xcworkspace/contents.xcworkspacedata`(+3행: `group:Pods/Pods.xcodeproj`)도 바뀐다.

세 파일을 다 커밋했다(코디네이터 답 §9-3). 안 하면 `pod install` 을 돌릴 때마다 트리가
더러워지고(리뷰 40 §7 이 실제로 그랬다) "재현 가능한 빌드" 라는 lock 의 목적이 깨진
채로 남는다.

**서명·현지화 설정이 보존됐는지 직접 확인했다.** diff 의 `-` 줄에
`PROVISIONING_PROFILE_SPECIFIER`·`InfoPlist.strings`·`LaunchScreen.storyboard` 가 보여서
전후 개수를 세고 실제 빌드 설정을 물어봤다.

```
$ for pat in InfoPlist.strings PROVISIONING_PROFILE_SPECIFIER CODE_SIGN_STYLE \
             "Apple Distribution" LaunchScreen.storyboard; do …; done
InfoPlist.strings                 OLD: 6  NEW: 6
PROVISIONING_PROFILE_SPECIFIER    OLD: 1  NEW: 1
CODE_SIGN_STYLE                   OLD: 4  NEW: 4
Apple Distribution                OLD: 3  NEW: 3
LaunchScreen.storyboard           OLD: 6  NEW: 6

$ xcodebuild -project Runner.xcodeproj -target Runner -configuration Release \
    -showBuildSettings | grep -E 'CODE_SIGN|PROVISIONING|DEVELOPMENT_TEAM|IPHONEOS_DEP'
    CODE_SIGN_IDENTITY = Apple Distribution
    CODE_SIGN_STYLE = Manual
    DEVELOPMENT_TEAM = J8QUD7B666
    IPHONEOS_DEPLOYMENT_TARGET = 15.0
    PROVISIONING_PROFILE_SPECIFIER = match AppStore com.dosaem.chosung
```

즉 줄이 **이동·재배치**된 것이고 티켓 34 D-34-1(match 서명)·티켓 22 D-22-3(한국어
`InfoPlist.strings`)의 수정은 그대로다. `mobile/test/config/ios_project_test.dart`·
`native_login_config_test.dart`(pbxproj 를 블록 단위로 파싱한다)와
`tests/test_app_deploy_workflow.py`(Release 블록의 `키 = 값`)도 그대로 통과한다(§8).

**`Pods/` 는 커밋하지 않는다**(`mobile/ios/.gitignore:13`). 그래서 새 클론에서 Xcode 로
열기 전에 `pod install` 을 한 번 돌려야 하고, 안 돌리면 `[CP] Check Pods Manifest.lock`
이 "sandbox is not in sync" 로 빌드를 **세운다** — 조용히 깨진 앱이 나오는 것보다 낫다.
CI 는 `flutter.yml:273-275` 가 빌드 전에 `pod install` 을 돌린다. `### 41.4` 에 적었다.

산출물은 확인 뒤 지웠다: `mobile/build`(340M) · `mobile/ios/Pods`(110M) ·
`mobile/ios/.symlinks`. `git status` 에 남은 것은 위 3파일뿐이다.

## 8. 검증 (내가 돌린 명령과 출력)

전용 자원만 썼다: DB `chosung_daily_test_t41` · `chosung_daily_test_t41_migrations`
(이 티켓이 만들었다) · Redis DB 3. 레포 기본 DB 로 떨어지지 않았다.

### 8.1 빌드·스크린샷 검사

아래는 **커밋 직전에 다시 처음부터 돌린** 출력이다. 작업 중 워커 세션이 끊겨(터미널
종료) 작업물만 커밋 안 된 채 남았으므로, 산출물을 다 지운 자리에서 `pod install`
부터 전부 재실행했다 — 아래 숫자는 그 재실행의 것이다.

```
$ cd mobile/ios && pod install
Pod installation complete! There are 20 dependencies from the Podfile and 40 total pods installed.   (exit 0)

$ cd mobile && flutter build ios --no-codesign
Running pod install...                                           2,093ms
Xcode build done.                                           64.6s
✓ Built build/ios/iphoneos/Runner.app (42.7MB)                   (exit 0)

$ cd mobile && flutter build apk --debug
Running Gradle task 'assembleDebug'...                             45.5s
✓ Built build/app/outputs/flutter-apk/app-debug.apk               (exit 0)

$ cd mobile && python3 -I tool/verify_store_screenshots.py ios
screenshots OK: ios — 로케일마다 5 장씩                          (exit 0)
$ cd mobile && python3 -I tool/verify_store_screenshots.py play
screenshots OK: play — 로케일마다 5 장씩                         (exit 0)

$ plutil -lint mobile/ios/Runner/Info.plist
mobile/ios/Runner/Info.plist: OK                                 (exit 0)
```

`pod install` 이 경고 2건을 찍는다 — **둘 다 이 티켓이 만든 것이 아니고 빌드를 막지
않는다**(위 두 빌드 다 exit 0).

1. `CocoaPods did not set the base configuration … Pods-Runner.profile.xcconfig`.
   Flutter 템플릿이 **Profile 구성에 `Flutter/Release.xcconfig` 를 쓰기** 때문이다
   (`project.pbxproj:498-500`). Debug·Release 는 각 xcconfig 가 Pods 쪽을
   `#include?` 하므로(`Flutter/Debug.xcconfig:1`·`Release.xcconfig:1`) 영향이 없고,
   `--profile` 빌드도 Release 용 Pods 설정을 받아 돈다. Flutter 기본 앱이 다 내는
   경고라 템플릿을 고치지 않았다.
2. `FirebaseCore has been deprecated in favor of … Swift Package Manager`
   (CocoaPods 신규 배포가 2026-10 로 끝난다). 지금 버전은 계속 쓸 수 있다 —
   SPM 이전은 이 티켓 범위가 아니다(기록만 남긴다).

### 8.2 analyze · format · test · lint

```
$ cd mobile && dart format --output=none --set-exit-if-changed lib test integration_test test_driver
Formatted 201 files (0 changed) in 0.29 seconds.                 (exit 0)
$ cd mobile && flutter analyze --no-pub
No issues found! (ran in 2.8s)                                   (exit 0, info 0)
$ cd mobile && flutter test --no-pub --reporter compact
00:27 +796: All tests passed!                                    (exit 0)

$ uv run ruff check .
All checks passed!                                               (exit 0)

$ TEST_DATABASE_URL=…/chosung_daily_test_t41 \
  TEST_MIGRATION_DATABASE_URL=…/chosung_daily_test_t41_migrations \
  TEST_REDIS_URL=redis://127.0.0.1:6379/3 uv run pytest -q
1693 passed in 916.97s (0:15:16)                                  (exit 0)
```

### 8.3 새 워크플로가 실제로 도는지

```
$ uv run pytest -q tests/test_asc_helper_workflows.py
36 passed in 0.12s                                               (exit 0)
$ uv run pytest -q tests/test_release_docs.py tests/test_app_deploy_workflow.py \
    tests/test_store_metadata.py tests/test_asc_submit_workflow.py
310 passed in 3.07s                                              (exit 0)
```

YAML 문법과 heredoc Python 컴파일도 따로 봤다 — 네 파일 다 `yaml.safe_load` 통과,
트리거가 `['workflow_dispatch']` 하나, `compile()` 통과.

## 9. 코디네이터에게 물은 6건과 받은 답

| # | 물은 것 | 답 | 이 문서 |
|---|---|---|---|
| 1 | 보조 워크플로 4개를 다 포팅할까 | 4개 다. 테스터 이메일은 하드코딩 말고 입력 + `vars.TESTFLIGHT_TESTER_EMAIL` 기본값. RELEASE variables 표·테스트도 갱신 | §3·§4 |
| 2 | `ITSAppUsesNonExemptEncryption=false` 를 넣을까 | 넣어라. 근거 한 줄 + 운영자 확인 체크 항목. 자체 암호화를 쓰는지 코드·pubspec 에서 확인하고 근거에 적어라 | §5 |
| 3 | `pod install` 이 같이 바꾼 pbxproj·xcworkspace 도 커밋할까 | 세 파일 다. 서명 보존 확인 결과를 증거에 | §7.2 |
| 4 | cloudflared 절차를 쓸까 | 써라. 두 방식 다, 레포가 정하는 값만 못박고, 현재 방식 확인은 사람 체크 항목 | §2 |
| 5 | 미수정 MINOR 9건을 몇 행으로 | 묶어서 2행(ID 나열) | §6 |
| 6 | 티켓 40 머지로 거짓이 된 3곳을 고칠까 | 세 곳 다 고쳐라 | §7.1 |

## 10. 범위 밖이라 하지 않은 것

1. **앱·서버 기능 변경 0건.** `mobile/lib/`·`app/`·`web/`·`migrations/` 변경 없다.
   `Info.plist` 의 새 키는 스토어 제출 신고값이고 런타임 동작을 바꾸지 않는다.
2. **`SKAdNetworkItems`**(BASELINE 에는 있다) — 광고 기여도 측정용이고 제출을 막지
   않는다. 광고를 맡는 티켓 31 영역이다.
3. **`GADApplicationIdentifier` 는 아직 Google 테스트 앱 ID** 다
   (`mobile/ios/Runner/Info.plist:23-24`). 실제 ID 로 바꾸는 것은 사람 항목이고
   `### 31.`·user-todo `#12` 에 이미 있다 — 이 티켓이 값을 추측해 넣지 않았다.
4. **`.scratch/` 변경 0건.** `spec.md`·`user-todo.md` 는 읽기만 했다.
5. **NAS·프로덕션 접근 0건**, `git push` 0건, 스토어·외부 서비스 호출 0건
   (`pod install` 의 CocoaPods 다운로드만 허용 범위).
6. **하위 워커 0명.**
7. **`impeccable detect` / `audit.native` 는 안 돌렸다** — UI 코드 변경이 없다.
8. **`README.md` 는 바꾸지 않았다.** 이 티켓의 판단 3건(수출규정 `false`, pbxproj
   통합 커밋, cloudflared 절차)은 전부 릴리스·배포 쪽이라 `docs/RELEASE.md`
   `### 41.` 에 적었다 — 티켓 34·35·40 도 배포 판단을 README 가 아니라 RELEASE 에
   적었다. README "설계 판단" 은 앱·서버 동작의 자리다.

## 11. 출시 준비 상태

### 에이전트 쪽 남은 일: **0**

Phase 6 기준표 46항목 중 충족 42 · 이 티켓이 채운 것 4(§1 의 #22~25 묶음 1건, #37,
#45, 그리고 기준표 외 D-40-2). 부분·누락으로 남은 항목은 없다. 미수정 MINOR 17건은
전부 "알려진 한계" 에 모였거나 해소됐다(§6).

한 가지만 에이전트가 못 닫는다: **기준표 #46 "포트가 ENV 사용 중 목록과 안 겹침"** 의
실제 확인은 NAS 에서만 된다(프로덕션 접근 금지). 절차와 명령은 `### 41.1` 에 있고
체크 항목은 `docs/RELEASE.md:57` 이다.

### 사람 쪽 남은 일: **11건** (`.scratch/store-launch/user-todo.md` 번호, 상태는 그 파일이 정본)

| # | 항목 | 왜 사람인가 |
|---|---|---|
| 6 | 단어 CSV 검수·업로드, 심사 전 en 30일 배정 | 후보는 티켓 39 가 만들었고 검수·업로드가 사람. D-39-1 의 en 힌트 9행도 여기서 지운다 |
| 9 | Slack Webhook · Sentry 2개 · UptimeRobot | 가입은 사용자, 설정은 Claude(Chrome) |
| 10 | Apple Developer 가입($99) · App ID · Sign in with Apple · Server API 키 · Sandbox 테스터 | 결제·약관 동의 |
| 11 | Play 개발자 등록($25) · 앱 생성 · 서비스 계정 · 라이선스 테스터 · 한국 판매자 정보 | 결제·판매자 계좌. **첫 AAB 는 콘솔에 손으로 한 번** 올려야 API 업로드가 열린다 |
| 12 | AdMob 앱 2 + 유닛 6 + UMP 메시지 | 계정 승인 대기 |
| 13 | ASC 앱 생성(이름 중복 확인) · 구독 `adfree_monthly` 양쪽 ₩1,500 · Apple Grace Period 16일 | 유료 앱 계약·세금/은행 정보 |
| 14 | match · self-hosted 러너 · 남은 secrets(`APP_STORE_CONNECT_API_KEY`·`MATCH_*`·`FLUTTER_SENTRY_DSN`·`ADMOB_*`) + **새 variable `TESTFLIGHT_TESTER_EMAIL`** | Apple 로그인 뒤. keystore·secrets 9개·variables 2개는 끝 |
| 15 | NAS compose 프로젝트명·볼륨명 확인, develop 폴더·`.env.develop`·DNS·**터널**(`### 41.1`) | Claude 는 NAS 에 접속하지 않는다 |
| 16 | prod `.env` 새 키(`LEGAL_*`·구독 검증 키·`ADMIN_EMAILS`·`STORE_URL_*`·`LOG_DIR`·`BACKUP_ENCRYPTION_CERT_FILE`·`ACCESS_LOG_RETENTION_DAYS`) | 값이 비밀이거나 사업자 정보 |
| 17 | 백업 암호화 개인키 생성·NAS 밖 두 곳 보관 | **개인키를 잃으면 모든 백업이 복구 불가** |
| 18 | Play Data safety · 앱 콘텐츠 설문 · target SDK/Billing 8+ 재확인 · **수출규정 답변 확인**(새 항목) · **첫 출시 버튼** | 출시 버튼은 사용자만 |

이미 끝난 것: `#1`~`#5`(법적 결정, 2026-10-15) · `#7`(Firebase) · `#8`(OAuth 클라이언트).
`#14` 는 일부 끝.

실기기 체크리스트(`docs/RELEASE.md:269`, 알림 10 · 구독 12 · 광고 6 · 계정 8 ·
태블릿 6항목)는 `#10`·`#12`·`#13` 이 열린 뒤에 돌 수 있다 — 코드로 증명할 수 없는
구간이라 "알려진 한계" 가 그렇게 적어 뒀다.
