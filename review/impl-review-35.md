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
