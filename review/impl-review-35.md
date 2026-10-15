# 티켓 35 최종 리뷰 — 라운드 1

- 대상 HEAD: `f243b61c6234070701096c43ce212a2163bdb512`.
- 기준: 로컬 `main`(`b11f011`), `git diff main...HEAD` 및 `git log main..HEAD`의 9개 커밋. merge-base는 `1172b9b`. `origin/main`은 사용하지 않았다.
- 요구사항: 티켓 35의 8개 체크박스, spec §B.25·BASELINE·US 67·미정 4/25, SCREENS S1~S6/T0~T4와 OVERRIDES §8.
- 구현 증거는 참고만 하고 파일·이미지·테스트·오프라인 재현으로 재확인했다. 앱/테스트/설정/`.scratch`는 수정하지 않았다. 외부 제출·실서비스 API 호출·NAS 접근은 하지 않았다. 정책 확인은 공개 공식 문서 열람만 했다.
- 코디네이터 추가 지시: 29~33 머지 후 최종 재촬영은 별도 작업이므로 그 화면 변경 미반영은 결함에서 제외한다. Android/iOS 차이와 캡처 스크립트 자체의 오류는 해당 유예와 별개다.

## 체크박스별 판정

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 아이콘·스플래시, SVG·런처/adaptive·라이트/다크 동일, README 이유 | 충족 | SVG 좌표/색·pubspec·생성 PNG 및 Android 리소스를 대조. 가운데 색 변경은 티켓이 허용하고 OVERRIDES/README에 근거가 있다. 아이콘 테스트 통과. README Flutter 절에 언어 중립 이유가 있다. |
| 30px 렌더·필요 시 가운데 칸 대비 조정 | 충족 | `design/icon-30px.png`를 직접 열어 세 칸을 확인. 30×30이며 픽셀/대비 테스트 통과. `#A8A29E` 및 대비 수치가 OVERRIDES와 README에 기록됨. |
| 5장×ko/en, 라이트·Fake API·S5 제외, 캡처 스크립트 | 미충족 | 장면 5개·양 언어·라이트·실제 위젯 테스트는 충족. 그러나 부분 실패를 성공 처리(D-35-1), Android도 iOS 장면 강제(D-35-5), 재촬영 때 세트 누적(D-35-6). |
| 양 스토어 메타데이터·이름·심사 노트·계정 플레이스홀더 | 충족 | 두 로케일 텍스트, 길이, 이름, Sandbox·구독·삭제 안내 및 플레이스홀더 확인. 대체명은 RELEASE 35에 기록. 단, 콘솔에 채운 노트를 제출 때 덮는 통합 결함은 D-35-7. |
| 수동 업로드 워크플로·mobile 경로·BASELINE 치환 | 미충족 | 수동 trigger·경로·bundle ID·secret cleanup은 충족. 라벨 부분 삭제 후 계속 제출(D-35-2), 입력 버전 미반영(D-35-3), 수동 노트 유실(D-35-7)로 반복 가능한 제출을 보장하지 못함. |
| iPad 13인치 태블릿 레이아웃·rail 단언 | 충족 | ko/en 각 5장, 모두 2064×2752. 실제 홈 PNG에서 rail·보드/힌트 2열 확인. widget 테스트가 폰/태블릿 장면을 실제 렌더하고 capture 테스트도 셸 장면에 rail을 단언. S6은 명세상 rail 예외. |
| privacy/support URL·라벨/Data safety 대조표·EULA | 미충족 | `/privacy`·`/terms`, 표와 ASC 범주 대조 및 표준 EULA 경로는 확인. 다만 SDK 수집 위치를 신고 대상에서 잘못 제외(D-35-4). 문서끼리 일치한다는 테스트만으로 실제 신고 정확성을 보장하지 못함. |
| 로컬 실행 결과 파일 목록·사람이 업로드 | 충족 | 증거 §6 목록과 실제 파일을 대조: iOS 30장, Play 20장, 아이콘/그래픽 4개. Play 폰 10장은 iPhone 파일과 바이트까지 동일하며 Android 성공 증거로 인정하지 않음(D-35-5). 업로드는 실행하지 않음. |

## 직접 실행한 검증

- `uv run ruff check .`: 통과, `All checks passed!`.
- `uv run pytest -q tests/test_store_metadata.py tests/test_store_labels.py tests/test_app_deploy_workflow.py`: **170 passed in 3.69s**.
- `cd mobile && flutter test test/store`: **25 passed**.
- `cd mobile && flutter analyze`: **No issues found**.
- `cd mobile && flutter test`: **428 passed**, 약 40초.
- 전체 백엔드 `uv run pytest -q`: **1468 passed in 1421.92s (0:23:41)**, 종료 코드 0. `TEST_DATABASE_URL`/`TEST_REDIS_URL`/`TEST_MIGRATION_DATABASE_URL`로 기존 `chosung_daily_test_t35`와 Redis DB 9, 기존 `chosung_daily_test_t35_migrations`를 사용했으며 새 DB를 만들지 않았다. 접속 실패·기본 DB fallback·간헐 실패·재실행은 없었다. 접속 문자열/비밀번호는 기록하지 않는다.
- `git diff --check main...HEAD`: 통과.
- `migrations/` 변경 없음: 이 티켓의 새 migration/head 확인 대상 없음.
- 스크린샷은 파일 수·PNG IHDR 해상도·iOS/Play 바이트 동일성을 Python으로 확인했다. 시뮬레이터 재촬영은 추적 자산을 덮으므로 실행하지 않았으며, 캡처 함수는 임시 디렉터리에서 추출 실행했다.
- 아래 워크플로 재현은 YAML에서 해당 Python 블록만 추출하고 `api`/`iris`를 메모리 대역으로 교체했다. 실제 API·키·계정 입력은 사용하지 않았다.

## 결함 목록

### D-35-1 — MAJOR — 한 장만 찍고 실패해도 캡처 성공 처리

- 위치: `scripts/store_screenshots.sh:83`, `scripts/store_screenshots.sh:93`.
- 재현: 파일의 `capture()`만 추출해 임시 폴더에서 호출하고 `flutter()`를 `touch "$STORE_SHOT_DIR/ko_01_home.png"; return 1`로 대체한다.
- 기대: 5개 장면 중 1개만 생성되고 drive가 실패했으므로 실패 반환, 기존 완성 세트 보존.
- 실제: `capture_exit=0`, 홈 한 장을 결과 폴더로 이동한다. `|| true`로 실패를 무시하고 개수가 0인지밖에 보지 않는다. 기존 세트가 있으면 새 홈과 과거 4장이 혼합된다. iPad rail 단언이 두 번째 이후 장면에서 실패해도 같은 문제다.
- 영향: 티켓의 결정적인 5장 세트 및 실패 시 불합격 조건을 우회한다. 업로드 쪽 검사도 전체 PNG가 0장인지뿐이어서 차단하지 못한다.

### D-35-2 — MAJOR — 개인정보 라벨 삭제 후 실패를 삼켜 부분 상태로 제출 진행

- 위치: `.github/workflows/asc-submit.yml:188` 및 `:215`.
- 재현: 해당 `try/except` 블록에 기존 라벨 1개를 반환하는 메모리 `iris`를 주고, DELETE는 성공·첫 POST는 예외를 발생시킨다.
- 기대: 기존 상태 복원 또는 명확한 실패 중단으로 불완전한 개인정보 라벨의 제출을 막는다.
- 실제 실행 결과: 호출 순서 `GET, DELETE, POST`, 남은 라벨 `[]`, 예외 밖으로 정상 진행. 로그는 `privacy labels: SKIPPED (iris auth 미지원 — ASC UI 값 유지): RuntimeError`로 실제 상태와 반대다.
- 영향: 초기 인증 실패와 삭제 이후 쓰기 실패를 구분하지 않아 기존 신고 데이터를 잃고, `dry_run=false`이면 이후 심사 제출까지 진행할 수 있다.

### D-35-3 — MAJOR — 입력한 app_version과 다른 버전에 빌드/심사정보를 붙임

- 위치: `.github/workflows/asc-submit.yml:136`.
- 재현: `app_version=1.0.0` 입력을 가정하고 버전 GET 대역이 `0.9.0 / REJECTED`를 첫 행으로 반환하게 한 뒤 실제 버전 선택 블록을 실행한다.
- 기대: 입력한 `versionString=1.0.0`의 iOS 버전을 선택하거나 명시적으로 실패.
- 실제: `requested=1.0.0 selected=0.9.0`. `APP_VERSION`은 앞선 deliver 스텝에만 전달되고 Python 스텝에는 없다. 선택 쿼리는 상태와 `limit=1`만 사용하며 fallback은 상태 조건도 없다.
- 영향: deliver로 갱신한 버전과 심사 노트·빌드 첨부·제출 대상이 달라지거나, 엉뚱한 기존 버전을 수정한 후 제출에 실패한다.

### D-35-4 — MAJOR — AdMob SDK의 대략적 위치 수집을 Data safety에서 제외

- 위치: `docs/play-data-safety.md:49`.
- 재현: 이 답안대로 콘솔 위치 항목을 미수집으로 입력한다고 가정하고, 같은 문서가 수집/공유한다고 선언한 AdMob의 공식 데이터 공개 설명과 대조한다.
- 기대: SDK가 기기 밖으로 전송하고 IP로 추정하는 위치도 수집 신고에 포함해 관련 문서/라벨과 일치시킨다.
- 실제: “SDK 가 직접 받고 우리가 수집하지 않는다”는 이유로 정확한 위치와 **대략적인 위치 모두 제외**한다. 자체 서버 저장 여부나 위치 권한 유무는 SDK의 신고 제외 근거가 아니다.
- 공식 근거(2026-10-15 확인): [AdMob 데이터 공개](https://developers.google.com/admob/android/privacy/play-data-disclosure)는 IP 수집과 위치 추정 용도를 명시하며, [Play Data safety 설명](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en)은 IP에서 추정한 대략적 위치도 공개하도록 명시한다.
- 영향: 배포용 답안 정본이 실제 광고 SDK 수집을 축소 신고한다. 기존 테스트는 표끼리의 범주 일치만 검사하므로 이 잘못된 제외를 잡지 못한다.

### D-35-5 — MAJOR — Android 캡처까지 iOS 온보딩을 강제해 실제 Android와 다름

- 위치: `mobile/integration_test/store_screenshot_scenes.dart:317`, `scripts/store_screenshots.sh:176`.
- 재현: Play `phoneScreenshots/iphone69_en_06_language.png`를 열면 페이지 표시가 4개다. `mobile/lib/onboarding/onboarding_pages.dart:26`은 Android에서 3개, iOS에서만 ATT를 더해 4개를 반환한다. 캡처 루트는 플랫폼에 상관없이 `isIosProvider=true`를 주입한다.
- 기대: 요구된 Android phone 캡처는 실제 Android 3페이지 온보딩과 일치해야 한다.
- 실제: ko/en 폰 파일 10개 전부 iPhone 원본과 바이트가 같고, Android에서 다시 찍어도 provider 강제값 때문에 4페이지 구성이 유지된다.
- 정책 판단: iPhone에서 생성했다는 사실만으로 금지라고 단정하지 않는다. 문제는 실제 UI가 다르다는 것이다. [Google Play 스크린샷 지침](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)은 실제 앱 경험을 보여 주도록 요구한다. 네이티브 캡처 요구 미충족과 플랫폼 차이가 직접 확인되어 결함으로 판정한다.
- 29~33 이후 재촬영 유예와 별개로, 재촬영 전에 장면의 플랫폼 판정을 고쳐야 한다.

### D-35-6 — MAJOR — Android 정상 재촬영 시 폰 세트가 10장으로 누적

- 위치: `scripts/store_screenshots.sh:97`, `scripts/store_screenshots.sh:171`.
- 재현: 현재 커밋된 Play 폰 세트 5개(`iphone69_*`)를 임시 결과 디렉터리에 복사하고, 추출한 `capture()`를 `android` prefix로 호출한다. `flutter()` 대역은 정상 장면 5개를 생성한다.
- 기대: 이전 대체 세트를 교체한 Android 5장만 남음.
- 실제 실행 결과: `capture_exit=0`, PNG **10개**. `iphone69_*`와 `android_*` 이름이 달라 덮어쓰지 않고 함께 남는다. 반대 방향 fallback에서도 같은 누적이 가능하다.
- 영향: 문서대로 AVD를 준비해 재촬영해도 Play 기기 유형별 최대 8장 제한을 초과한다([공식 지침](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en)). 캡처 완료 시 출력 디렉터리를 세트 단위로 교체하는 처리가 필요하다.

### D-35-7 — MAJOR — 사람이 콘솔에 채운 Sandbox 심사 노트를 제출 때 플레이스홀더로 덮음

- 위치: `.github/workflows/asc-submit.yml:240`, `docs/RELEASE.md:792`.
- 재현: App Review Detail GET 대역에 사람이 입력한 노트 식별 문자열을 넣고 실제 심사정보 블록을 실행한다. POST/PATCH는 메모리 상태에만 적용한다.
- 기대: RELEASE 지시대로 콘솔에 직접 채운 Sandbox 정보가 제출까지 보존됨.
- 실제: `manual_note_preserved=False`, `placeholder_written=True`. 기존 `rd.attributes.notes`를 읽거나 병합하지 않고 매번 레포의 플레이스홀더 노트로 PATCH한다. 앞선 deliver도 같은 notes 파일을 업로드한다.
- 영향: 권장 순서인 dry run → 콘솔 정보 확인/입력 → 실제 제출을 따르면 마지막 실행에서 다시 지워진다. 레포에 비밀을 넣지 않는 원칙을 지키면서 수동 입력과 자동 업로드의 소유권/순서를 분리해야 한다.

## 테스트·범위·보안 검토

- 장면 테스트는 실제 화면 위젯을 렌더하고 Fake API로 서버 경계만 대체하므로 의미가 있다. 다만 모든 플랫폼을 iOS로 고정하므로 Android 일치 검증은 없다.
- 새 Python 테스트는 메타데이터 길이·내용·경로·트리거 및 표 일치에는 유효하다. 워크플로 실패 경로는 실행하지 않는다. 특히 `test_the_metadata_workflow_refuses_to_upload_without_screenshots`는 경로 문자열 존재만 검사하여 제목의 거부 동작을 증명하지 못한다. 이 검증 공백은 D-35-1~3/7의 근거에 포함하며 별도 중복 결함으로 세지 않는다.
- README 설계 판단에는 `### 35.`, RELEASE에는 `### 35.`, 스펙 미정에는 티켓 35 행을 끝에 추가했다. README 기존 Flutter 절의 3줄 추가는 티켓이 명시적으로 요구한 이유 설명이다. 다른 번호의 공유 행/절을 바꾸는 위반은 발견하지 못했다.
- 앱 런타임 API·인증·CSRF 처리 변경은 없다. 변경 파일에서 실제 비밀 키/토큰/비밀번호를 발견하지 못했고 Sandbox 값은 플레이스홀더다. 구체적인 데이터 손상 위험은 D-35-2, 수동 입력 유실은 D-35-7이다.
- 의존성 lock과 integration_test 추가는 캡처 실행 범위에 해당한다. 취향/스타일 제안은 결함에 포함하지 않았다.

## 참고

- 스크린샷의 29~33 화면 변경 미반영은 코디네이터가 별도 최종 재촬영 작업으로 지정했으므로 결함이 아니다.
- 업로드·ASC/Play 콘솔·실제 Sandbox 구매는 실행하지 않았다. 외부 동작을 검증 완료라고 주장하지 않는다.
- 집계: BLOCKER 0, MAJOR 7, MINOR 0.

판정: FAIL

## 라운드 2

- 대상 HEAD: `2dff1deae3c13dba2b23211dea1bce5b4a59baed`; 기준 로컬 `main`은 확인 시 `d78e082`, merge-base `1172b9b`. `git diff main...HEAD`, `git log main..HEAD`(11개 커밋) 및 이전 리뷰 이후 수정 커밋을 확인했다. `origin/main`은 사용하지 않았다.
- 티켓 35, spec §B.25·BASELINE·US 67·미정 4/25, SCREENS S6/T0~T4, OVERRIDES §8과 구현 증거를 직접 대조했다. 하위 에이전트 없이 검토했다.
- 코디네이터의 이번 라운드 메모를 적용했다: rebase 미실행, 29~33 화면의 최종 재촬영, 커밋된 Play 폰 복사본 교체, 방침 본문의 대략적 위치 추가는 별도 작업이다. **현재 이미지가 낡았다는 이유로 결함을 올리지 않는다.** 다만 재촬영 스크립트 자체가 다시 잘못된 플랫폼 장면을 생성하는 경로는 D-35-8로 보고한다.

### 체크박스별 판정

| 티켓 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| 아이콘·스플래시 SVG/런처/adaptive 및 README 언어 중립 이유 | 충족 | SVG의 120 뷰박스·타일 좌표·색, pubspec와 생성 리소스를 대조했다. 아이콘 테스트 9개 통과. README Flutter 절에 이유가 있다. |
| 30px 가독성과 가운데 색 조정 근거 | 충족 | 30×30 PNG를 직접 열어 세 칸을 확인했다. 실제 픽셀 대비 테스트 통과, OVERRIDES §8·README 35에 1.43→2.41:1 기록이 있다. |
| 5장×ko/en·라이트·Fake API·S5 제외·캡처 스크립트 | 미충족 | 장면과 실패/교체 처리는 검증됐지만 Play 태블릿 경로는 재실행해도 iOS 전용 온보딩을 복사한다(D-35-8). 현재 Play 폰 재촬영 유예와 구별한다. |
| 양 스토어 메타데이터·앱 이름·심사 노트·플레이스홀더 | 충족 | 이름·길이·URL·Sandbox/구독/삭제 안내·예약 파일명 변경을 확인했다. 영문 예시의 글자 수 오류는 D-35-9(MINOR). |
| 수동 업로드 워크플로와 mobile 경로 | 충족 | 수동 트리거·경로·키 정리 및 실제 Python 블록 실행 테스트 통과. 버전 선택·라벨 실패 중단·수동 노트 보존 수정 확인. Play 태블릿 검증 공백은 D-35-8에 포함한다. |
| iPad 13인치 태블릿 레이아웃·rail 단언 | 충족 | ko/en 각 5장, 모두 2064×2752. 홈 PNG에서 rail·2열을 직접 확인했고, 장면 테스트와 캡처 전 rail 단언도 확인했다. S6은 SCREENS T0에 따른 rail 예외다. |
| privacy/support URL·ASC/Play/법적 체크리스트 대조·EULA | 충족 | `/privacy`·`/terms`, 표준 EULA 경로, `COARSE_LOCATION`과 Play 대략적인 위치 수집/공유 행·대조표를 확인했다. 방침 본문 추가는 코디네이터 지정 사람 확인 항목이다. |
| 로컬 캡처 실행 결과 파일 목록·업로드는 사람 | 충족 | 증거 목록과 실제 PNG 54개(iOS 30, Play 스크린샷 20, 등록 자산 4)를 대조했다. 신규 네이티브 캡처 성공으로 해석하지 않는다. 외부 업로드는 실행하지 않았다. |

### 이전 결함 판정

이전 7개 ID의 심각도는 라운드 1의 MAJOR를 유지하되, 아래 FIXED 항목은 이번 라운드 잔존 결함 수에 포함하지 않는다.

| ID | 판정 | 직접 확인한 수정과 재현 결과 |
|---|---|---|
| D-35-1 | FIXED | `scripts/store_screenshots.sh:102`의 `capture`가 drive 종료 코드와 정확히 5장을 모두 검사한다. 실제 bash 함수를 source한 테스트에서 0/1/4장 실패와 5장 후 비정상 종료 모두 거부하고 기존 세트를 보존한다. 업로드 검증기도 불완전 세트를 거부한다. |
| D-35-2 | FIXED | `.github/workflows/asc-submit.yml:205`에서 최초 GET과 쓰기를 분리했다. 네트워크 경계만 대체한 실제 Python 블록 실행에서 DELETE 후 POST 실패는 예외로 종료하고 빌드 첨부/제출하지 않았다. 401이면 DELETE 자체가 없다. 삭제 후 자동 복원은 없지만 명시적 실패 중단이라는 기존 기대를 충족한다. |
| D-35-3 | FIXED | `.github/workflows/asc-submit.yml:92`, `:148`에서 입력 버전을 받고 필터 및 재대조한다. 구버전이 앞에 있는 재현에서 요청 버전만 수정하고, 요청 버전이 없으면 중단한다. |
| D-35-4 | FIXED | `docs/play-data-safety.md:37`, `mobile/ios/fastlane/app_privacy_details.json:65`, `docs/legal-checklist.md:188`에 대략적 위치를 수집/공유·광고 목적 범주로 추가했다. 위치 제외 문구는 정확한 위치만 남겼다. 관련 12개 라벨 테스트 통과. |
| D-35-5 | FIXED | 이전 지적의 폰 경로는 `Platform.isIOS` 또는 `SHOT_IS_IOS=false`를 장면에 전달한다. 실제 플랫폼별 위젯 테스트와 fallback 인자 테스트가 통과했다. 현재 폰 복사본은 `verify_store_screenshots.py play`가 2건 오류/종료 1로 차단한다. 기존 자산 교체는 유예 범위다. 별도 태블릿 복사 경로는 새 D-35-8이다. |
| D-35-6 | FIXED | `scripts/store_screenshots.sh:88`의 세트 교체와 Play 호출의 `*.png` 소유 패턴을 확인했다. 양방향 재촬영 재현에서 5장만 남고 iOS의 다른 기기 세트는 보존된다. |
| D-35-7 | FIXED | `.github/workflows/asc-submit.yml:277`에서 사람이 채운 노트에는 notes 필드를 보내지 않는다. 템플릿은 `notes.template.txt`로 옮겨 deliver 예약 파일에서 제외했다. 수동 노트 보존·빈 값/플레이스홀더 최초 채움 테스트 5개 통과. |

### 새 결함

#### D-35-8 — MAJOR — Play 태블릿 재촬영 경로가 iOS 전용 온보딩을 다시 복사하고 검사도 허용함

- 위치: `scripts/store_screenshots.sh:190`, `scripts/store_screenshots.sh:195`, `mobile/tool/verify_store_screenshots.py:102`, `tests/test_store_metadata.py:354`(태블릿 재사용 허용 테스트).
- 기대: Play 태블릿에도 실제 Android 구성의 언어 선택 장면이 들어가야 한다. SCREENS S6은 ATT 안내를 **iOS만** 추가하며, `mobile/lib/onboarding/onboarding_pages.dart:26`은 화면 폭과 무관하게 Android 3장/iOS 4장을 반환한다.
- 실제: iPad 캡처는 플랫폼 override 없이 iOS 구성으로 생성되고, 그 5장을 Play `tenInchScreenshots`로 통째로 복사한다. 폰에는 적용한 Android 구성 fallback을 태블릿에는 적용하지 않았다. 검증기는 `phoneScreenshots`만 iOS 온보딩과 비교하고, 태블릿은 “같은 그림”이라는 잘못된 전제로 통과시킨다.
- 재현 1: 현재 `.../images/tenInchScreenshots/ipad13_en_06_language.png`를 열면 하단 페이지 표시가 **4개**다. ko/en 태블릿 10개 모두 iPad 원본과 바이트가 동일하다. 기존 플랫폼 위젯 테스트의 임시 사본에서 `setViewSize(tester, phone)`만 `tablet`(1024×1366)로 바꾸어 실행했다: ko/en × iOS/Android **4 passed**, 실제 Android 점 3개/iOS 점 4개를 확인했다. 레포 테스트는 수정하지 않았다.
- 재현 2: `tests/test_store_metadata.py`의 `_fake_mobile`로 임시 정상 폰 세트를 만들고, 양 로케일 `tenInchScreenshots`만 실제 iPad PNG 5장씩으로 교체하여 `_verify(root, 'play')` 실행 → 기대는 iOS 전용 태블릿 장면 거부, 실제는 **종료 0, `screenshots OK: play`**. 기존 `test_the_verifier_allows_the_tablet_set_to_reuse_the_ipad_captures`도 이 잘못된 허용을 고정한다.
- 영향: 최종 재촬영을 지금 스크립트로 수행해도 Android 태블릿과 다른 온보딩 이미지가 다시 생성되며, 폰을 고치고 나면 업로드 검사까지 통과한다. **기존 PNG 교체를 유예한 것과 다른, 생성/검증 경로의 결함**이다. 플랫폼 장면 차이를 처리한 뒤 태블릿 세트도 재촬영해야 한다.

#### D-35-9 — MINOR — 영문 스토어 설명이 6칸 예시를 5글자로 안내함

- 위치: `mobile/ios/fastlane/metadata/en-US/description.txt:11`, `mobile/android/fastlane/metadata/android/en-US/full_description.txt:11`.
- 재현: 두 파일의 `P _ R P L _`를 공백 기준으로 세면 6칸이다. 같은 문장은 `for a five-letter word`라고 설명한다.
- 기대: 실제 보드처럼 칸 수와 단어 길이가 일치하는 설명. 실제: 양 스토어 영문 본문에 6칸을 5글자라고 적었다. 홈 스크린샷도 같은 예시를 `6 letters`로 표시한다.
- 영향: 게임 규칙을 설명하는 구체적인 예시가 틀렸다. 문체나 취향 지적이 아니라 수치 오류이며, 업로드 동작 자체를 막지는 않는다.

### 직접 실행한 검증

- `uv run ruff check .`: **All checks passed!**
- `uv run pytest -q tests/test_store_metadata.py tests/test_store_labels.py tests/test_store_screenshot_script.py tests/test_asc_submit_workflow.py tests/test_app_deploy_workflow.py`: **206 passed in 4.60s**.
- `uv run pytest -q tests/test_legal_checklist.py`: **134 passed in 166.98s (0:02:46)**.
- 두 Python 실행 모두 `TEST_DATABASE_URL`은 기존 `chosung_daily_test_t35`, `TEST_REDIS_URL`은 로컬 Redis DB 9로 지정했다. 법적 체크리스트 테스트의 실제 Flask/DB fixture가 정상 동작했으며 새 DB 생성·기본 DB fallback·간헐 실패·재실행은 없었다. `TEST_MIGRATION_DATABASE_URL`도 기존 전용 migrations DB로 지정했지만 이번 선택 테스트는 마이그레이션 테스트를 포함하지 않는다. 접속 자격 증명은 문서에 기록하지 않는다.
- `cd mobile && flutter test test/store --reporter expanded`: **29 passed**.
- `cd mobile && flutter analyze --no-pub`: **No issues found**, 4.6초.
- `cd mobile && flutter test --no-pub --reporter compact`: **432 passed**, 약 30초.
- 임시 태블릿 폭 플랫폼 재현: `flutter test --no-pub /tmp/t35_tablet_platform_review_test.dart --plain-name '온보딩 장 수가 그 플랫폼과 같다'`: **4 passed**. 원래 테스트의 두 상대 import를 절대 URI로 바꾸고 폰 폭을 태블릿 폭으로 바꾼 임시 사본이며, 실제 장면/화면은 레포 코드를 그대로 사용했다.
- `python3 mobile/tool/verify_store_screenshots.py ios`: 종료 0. `... play`: **종료 1, 현재 폰 복사본 2건 차단**(코디네이터 지정 기대 결과).
- `git diff --check main...HEAD`: 통과. `git diff --name-only main...HEAD -- migrations`: 출력 없음. 마이그레이션 변경이 없으므로 `flask db heads` 추가 실행 대상 없음.

### 범위·테스트 품질·보안·참고

- 새 테스트는 실제 shell 함수/Python 워크플로 블록/Flutter 위젯을 실행한다. ASC 테스트는 외부 네트워크 경계만 메모리 대역으로 바꿔 실패 후 제출 여부까지 검사한다. 무조건 성공하는 테스트는 아니지만, 태블릿 재사용 허용 테스트는 틀린 요구를 단언한다(D-35-8).
- 앱 런타임(`app/`, `mobile/lib/`)과 `.env.example` 변경은 없다. README의 기존 Flutter 절 추가는 티켓의 명시 요구이며, 공유 문서 추가는 자기 `35.` 절/행이다. 34의 라벨 테스트 변경은 새 위치 범주와 신고 항목 대조를 유지하는 관련 변경이다. 별도 범위 이탈·공유 파일 규칙 위반은 발견하지 못했다.
- 실제 키·토큰·비밀번호가 추가된 증거는 발견하지 못했다. 심사 노트는 플레이스홀더이며 워크플로 키 파일은 always 정리한다. 인증/CSRF 런타임 변경은 없다. D-35-2의 실패 시 부분 라벨 상태는 로그와 중단으로 드러나며, 자동 복원까지 보장한다고 해석하지 않는다.
- NAS/프로덕션/실제 ASC·Play·결제·인증 API 호출, 외부 업로드와 push는 하지 않았다. 시뮬레이터 전체 캡처는 추적 자산을 덮으므로 실행하지 않았다. 전체 백엔드 스위트는 이번 라운드에 재실행하지 않았으며, 이전 증거의 1504 passed를 직접 검증 결과로 인용하지 않는다.
- 최종 재촬영 및 방침 본문 사람 확인은 별도 후속 작업으로 유지한다. 코드·테스트·설정·`.scratch`를 수정하지 않고 리뷰 문서만 변경한다.
- 집계: 이전 결함 **FIXED 7, REPEAT 0**; 새 결함 **BLOCKER 0, MAJOR 1, MINOR 1**.

판정: FAIL
