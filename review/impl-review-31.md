# 티켓 31 최종 리뷰 — 라운드 1

## 범위와 결론

- 기준: 로컬 `main` = `8ddc8fdb03dddd9cfd7fb44ba14cf394d8bec7ab`, 구현 HEAD = `dc6e14e9254d43f679e0d9ecb89d48f13d51b1a5`.
- `git log main..HEAD`의 구현·수정·증거 커밋 5개와 `git diff main...HEAD`를 검토했다. `origin/main`은 사용하지 않았다.
- 티켓, 스펙 §A.5·§B.21·§B.23 및 관련 US, SCREENS S1/S2/S4/S6/T0/T1, OVERRIDES §5~7, `e1_home`·`e7_home_dark`, 구현 증거와 실제 테스트를 대조했다.
- **BLOCKER 0 / MAJOR 3 / MINOR 0.** 아래 결함은 코드 경로로 확인한 재현 절차이며, 새 회귀 테스트를 추가하거나 실기기 광고를 호출하지 않았다. 기존 테스트 통과와 결함 부재를 동일시하지 않는다.

## 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient `POST /puzzles/today/hint-unlock` — Dio + Fake | 충족 | `api_client.dart`, `dio_api_client.dart:89`, Fake의 요청 기록·응답 제어 구현을 확인했다. `dio_api_client_test.dart`는 메서드·경로·puzzle_id·Authorization 헤더와 409 전용 예외를 검사한다. |
| 광고 게이트 순수 함수, UMP 4종·구독자·오류 세션/재시작 테스트, entitlement Provider | 충족 | `ad_gate.dart`는 UMP·ATT·권한으로 출력하고 `entitlement_provider.dart` 초기값은 null이다. `ad_gate_test.dart`, `ad_consent_test.dart`, `entitlement_test.dart`가 전체 Flutter 실행에서 통과했다. 갱신·타이머 구현은 티켓 33 소유이므로 누락으로 세지 않았다. |
| UMP update → 폼 → SDK `canRequestAds` → initialize, ATT 뒤 실행, define/디버그 ID | 증거 부족 | update·폼·ATT 대기·initialize 배선과 define/테스트 ID는 확인했다. 다만 `google_ad_service.dart:28`은 SDK `ConsentInformation.canRequestAds()`를 읽지 않고 `getConsentStatus()`를 읽으며, `ad_gate.dart:30`의 자체 getter가 광고 가능 여부를 계산한다. 기존 테스트는 FakeAdService를 쓰므로 SDK 허용값과 자체 계산의 일치를 검증하지 않는다. 이 차이만으로 실제 잘못된 노출을 단정하지 않아 별도 결함 수에는 넣지 않았다. |
| 배너 예약/실패/구독자 제거/태블릿 폭 재요청 + 전면 퍼즐당 1회 | 미충족 | 배너의 폭 변경·이전 광고 해제·고정 예약 높이는 `banner_slot_gate_test.dart`에서 확인했다. 시트 닫힘 뒤·첫 제출 전 차단·구독자 차단도 검사한다. 그러나 전면 기록은 마지막 ID 하나뿐이라 언어를 왕복하면 같은 퍼즐에 다시 노출된다(D-31-1). 실제 SDK 배너 높이 실측은 증거에도 미실시로 명시되어 있다. |
| 보상형 완료 후 힌트, 구독자 무광고 힌트, 409, 로드 실패 비활성/안내 | 미충족 | 정상 두 경로·중도 닫힘·광고 불가·409 이미 열림은 `today_tab_ads_test.dart`에서 통과한다. 제출과 힌트의 응답 경합(D-31-2), 광고 실패 뒤 구독 전환 시 영구 비활성(D-31-3)을 처리하지 않는다. |
| S4 required일 때만 개인정보 설정 표시 → 폼 호출 | 충족 | `records_tab.dart:316`의 조건부 행과 실제 서비스 폼 호출을 확인했다. `records_ad_privacy_test.dart`의 required/비required/구독자 및 탭 시 호출 검증이 통과했다. 실제 UMP 재선택과 변경 결과는 실기기 검증 범위로 남는다. |
| 광고 서비스 인터페이스/no-op, 위젯 테스트, native audit·목업 대비 | 증거 부족 | `AdService`·`NoopAdService`·Fake 경계, 게이트/슬롯/시트/힌트 위젯 테스트가 있다. 골든 3장을 직접 열어 라이트·다크·태블릿의 HintCard와 슬롯을 확인했고 목업 HTML/OVERRIDES를 대조했다. 증거의 audit 표는 소스·위젯 기반 평가이며 실제 광고 렌더링·SDK 크기 실측 증거는 없다. 테스트가 아래 전환/경합을 놓치므로 모든 동작의 완료 증거로 사용할 수 없다. |

## 결함

### D-31-1 — MAJOR — ko/en 왕복 시 같은 퍼즐에 전면 광고 재노출

- 위치: `mobile/lib/ads/interstitial_store.dart:26`, `mobile/lib/ads/interstitial_store.dart:29`, `mobile/lib/ads/result_interstitial.dart:32`.
- 요구: 티켓의 “퍼즐당 1회(로컬 플래그 puzzle_id 기준)”, US 24. 오늘 퍼즐은 언어별로 별도 ID다.
- 재현 입력: 광고 가능 비구독자가 한국어 퍼즐 A를 끝내고 결과 시트를 닫는다 → 설정에서 영어로 바꿔 퍼즐 B를 끝내고 시트를 닫는다 → 한국어로 돌아와 A의 “결과 보기”를 열었다 닫는다. `PuzzleLanguageNotifier.change`는 오늘 퍼즐을 다시 읽지만 `resultInterstitialProvider`의 제출 플래그는 유지한다.
- 기대: A 1회, B 1회로 총 2회. A 재열기에서는 광고가 없어야 한다.
- 실제 코드 경로: `markShown(B)`가 A의 기록을 덮는다. A 재열기에서 `lastShownPuzzleId() == A`가 false여서 세 번째 광고를 요청한다. A↔B를 계속 바꾸면 반복된다.
- 테스트 공백: 기존 테스트는 A→A, A→B만 확인하고 A→B→A는 확인하지 않는다. 적어도 동시에 접근 가능한 두 언어 퍼즐의 노출 여부를 각각 유지해야 한다.

### D-31-2 — MAJOR — 제출 중 힌트 요청이 제출 응답과 입력 잠금을 손상

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:145`, `mobile/lib/puzzle/today_puzzle_controller.dart:147`, `mobile/lib/puzzle/today_puzzle_controller.dart:151`; 진입점 `mobile/lib/screens/today_tab.dart:321`.
- 요구: 힌트 미리 보기는 시도·순위에 영향을 주지 않고(US 5), 제출된 시도 이력과 화면 상태를 유지해야 한다. 기존 submit/refresh 경합 보호를 새 힌트 경로가 우회한다.
- 재현 입력: 구독 권한 true, 아직 힌트가 없는 진행 중 퍼즐에서 답을 제출하고 응답을 지연시킨다 → 제출 대기 중에도 활성인 “힌트 미리 보기”를 누른다 → 힌트 응답과 제출 응답을 차례로 완료한다. 기존 Fake의 `submitGuessGate`·`unlockHintGate`로 이 순서를 구성할 수 있다.
- 기대: 두 동작을 직렬화하거나 서버 상태를 병합/재조회하여 소비된 시도·보드·힌트가 모두 일치하고 제출 잠금이 정상 해제되어야 한다.
- 실제 코드 경로: `unlockHint()`는 `current.submitting`/`_submitting`을 검사하지 않고 `_generation`을 증가시킨다. 그러면 먼저 보낸 submit 응답은 103행에서 폐기된다. 힌트 성공은 제출 전 `puzzle.copyWith(hint: ...)`를 써서 소비된 시도 행·남은 기회를 화면에 반영하지 않으며, `TodayPuzzleReady`의 submitting 기본값 false로 제출 잠금도 일찍 푼다.
- 더 강한 실패 재현: 같은 순서에서 힌트 요청을 `NetworkApiException`으로 실패시키면 172~174행은 상태를 복구하지 않는다. 제출 응답은 이미 세대가 달라 폐기되고 `finally`는 내부 `_submitting`만 false로 바꾸므로 화면의 `submitting: true`가 남아 재조회/재시작 전까지 입력이 잠긴다.
- 테스트 공백: 기존 controller 테스트는 submit↔refresh 경합을 검사하지만 submit↔unlockHint를 검사하지 않는다. 정상 힌트 테스트의 즉시 Fake 응답으로는 이 문제가 드러나지 않는다.

### D-31-3 — MAJOR — 광고 실패 후 구독 권한이 생겨도 무광고 힌트가 계속 잠김

- 위치: `mobile/lib/screens/today_tab.dart:293`, `mobile/lib/screens/today_tab.dart:315`.
- 요구: US 32 및 티켓의 “구독자는 ‘힌트 미리 보기’로 광고 없이 바로 hint-unlock”. 권한 Provider의 갱신을 현재 화면이 반영해야 한다.
- 재현 입력: 진행 중 퍼즐에서 비구독자로 힌트 버튼을 눌러 `RewardedOutcome.unavailable`을 받는다 → 같은 화면/퍼즐을 유지한 채 `entitlementProvider.notifier.update(active: true)`를 호출한다. 이는 이 티켓이 32·33에 제공한 실제 권한 갱신 인터페이스이며 FakeEntitlement도 같은 update를 상속한다.
- 기대: 레이블이 “힌트 미리 보기”로 바뀌고 버튼이 활성화된다. 탭하면 광고 요청 없이 hint-unlock을 호출해야 한다.
- 실제 코드 경로: `_adUnavailable`이 true로 남고 `blocked = !gate.canPreviewHint || _adUnavailable`이 구독 여부와 무관하게 이를 적용한다. 레이블만 바뀌고 버튼은 계속 null이며 “지금은 광고를 불러올 수 없어요”도 남는다. 같은 puzzle_id의 `_HintSlot` 상태가 유지되는 동안 구독 혜택을 사용할 수 없다.
- 테스트 공백: 구독자를 처음부터 true로 주입한 테스트와 비구독자 광고 실패 테스트는 각각 있지만 실패→구독 전환 테스트는 없다.

## 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| `uv run ruff check .` | `All checks passed!`, exit 0 |
| `cd mobile && flutter analyze` | `No issues found!`, exit 0 |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | `Formatted 145 files (0 changed)`, exit 0; 파일 수정 없음 |
| `cd mobile && flutter test` | `00:26 +457: All tests passed!`, exit 0 |
| 지정 테스트 자원으로 `uv run pytest -q` | `1403 passed in 1329.31s (0:22:09)`, exit 0; 재실행 없이 통과 |
| `git diff --check main...HEAD` | exit 0 |

백엔드는 `TEST_DATABASE_URL`의 로컬 DB 이름을 `chosung_daily_test_t31`, `TEST_REDIS_URL`을 `redis://127.0.0.1:6379/5`, `TEST_MIGRATION_DATABASE_URL`의 로컬 DB 이름을 `chosung_daily_test_t31_migrations`로 지정했다. 접속 문자열의 인증 값은 이 문서에 싣지 않는다. 기존 전용 DB에 접속했고 새 DB는 만들지 않았으며 기본 DB로 전환하지 않았다.

이번 diff에 마이그레이션 변경이 없으므로 조건부 `flask db heads` 검사는 해당하지 않는다. `app/`, `web/`, `tests/`, `migrations/`, `.env.example` 변경도 없다. 네이티브 빌드 성공 주장은 이번 리뷰에서 재실행하지 않았으며 실제 외부 광고·스토어·프로덕션에 접속하지 않았다.

## 보안·범위·공유 파일 확인

- 새 hint-unlock 요청은 기존 `_authorized()`를 사용한다. 이 변경에 서버 인증/CSRF 우회, 새 비밀 값 저장, 서버 데이터 삭제 경로는 발견하지 못했다. D-31-2는 서버의 시도 소비와 클라이언트 표시가 어긋나는 문제이며 서버 행 삭제로 단정하지 않는다.
- README와 RELEASE는 `### 31.`만 기존 섹션 끝에 추가했고 스펙도 자기 번호의 미정 항목만 추가했다. 다른 티켓 행을 덮어쓰지 않았다. ATT 기존 선택 복구와 네이티브 SDK 빌드 설정은 광고 연동 범위에 해당한다.
- 추가된 AdMob 값은 명시된 Google 테스트 식별자이며 시크릿 값이 아니다. 변경 파일과 증거 문서에서 실제 키·토큰·비밀번호를 발견하지 못했다.

## 참고와 검증 한계

- 전면 타이밍은 디자인의 “시트가 뜬 뒤”보다 구체적인 티켓의 “닫힘 후”를 따르므로 결함으로 세지 않았다.
- 빈 슬롯의 “광고” 캡션 부재, 기존 전폭 HintCard 버튼, 390 골든에서 제출 버튼이 아래 스크롤로 내려가는 모양은 이 리뷰에서 취향·스타일 결함으로 세지 않았다.
- SDK `canRequestAds` 직접 확인, 개인정보 선택 변경 후 상태 반영, 실제 어댑티브 높이와 네이티브 광고 렌더링은 Fake/골든만으로 입증되지 않는다. 구현 증거의 자체 audit 점수와 실기기 검증을 구별해야 한다.

판정: FAIL

## 라운드 2

### 범위와 결론

- 기준은 로컬 `main` `8ddc8fdb03dddd9cfd7fb44ba14cf394d8bec7ab`, 검토 HEAD는 `c4d2da37317641dba18fe0f6aa9a97a826b599d9`이다. `git log main..HEAD` 9개 커밋과 `git diff main...HEAD`, 이전 리뷰 이후 수정 diff를 직접 확인했다.
- 티켓 체크박스, 스펙 §A.5·§B.21·§B.23/관련 US, SCREENS S1/S2/S4/T0/T1, OVERRIDES §5~7, `e1_home`/`e7_home_dark` HTML과 라이트·다크 390 및 태블릿 1024 골든을 대조했다.
- 이전 결함 3건의 원래 재현 경로는 FIXED다. 신규 **BLOCKER 0 / MAJOR 1 / MINOR 0**, REPEAT 0이다. 신규 D-31-4는 코드 흐름으로 확인했으며, 테스트 파일을 추가·수정하거나 외부 서비스를 호출하지 않았다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient hint-unlock, Dio + Fake | 충족 | `mobile/lib/api/dio_api_client.dart:89`는 기존 인증 옵션으로 puzzle_id를 전송한다. `dio_api_client_test.dart`에서 HTTP 메서드·경로·요청 본문·인증 헤더·409 예외를 검사하며 전체 실행에서 통과했다. |
| 광고 게이트 순수 함수·UMP 4종·구독자·오류/재시작·entitlement Provider | 충족 | `ad_gate.dart`의 입력/출력, 초기 null 권한, ATT와 UMP 분리, `ad_gate_test.dart`·`ad_consent_test.dart`·`entitlement_test.dart`를 확인했다. 갱신 타이머는 티켓 33 소유다. |
| UMP update → 폼 → SDK canRequestAds → initialize, ATT 뒤 실행, 광고 ID | 증거 부족 | update/폼/ATT 순서와 ID define/디버그 테스트 ID 배선은 있다. 여전히 `google_ad_service.dart:28`은 SDK `canRequestAds()`를 읽지 않고 ConsentStatus를 반환하며 `ad_gate.dart:30`이 허용값을 계산한다. Fake 기반 테스트는 실제 SDK 값과 이 계산의 일치를 증명하지 않는다. 라운드 1과 같이 실제 오노출을 확인하지 못했으므로 별도 결함으로 승격하지 않았다. |
| 배너 예약·실패·구독자 제거·태블릿 폭 재요청, 전면 퍼즐당 1회 | 충족 | 실제 셸을 쓰는 `banner_slot_gate_test.dart`가 슬롯 제거·실패 후 높이·rail 제외 폭·회전 시 재요청 1회와 dispose를 검사한다. `result_interstitial_test.dart`의 A→B→A→B와 저장 목록 계산 테스트가 D-31-1을 보완한다. 전면 시트 닫힘/첫 제출/구독자 테스트도 통과했다. 실기기 어댑티브 높이 실측은 여전히 별도 검증 한계다. |
| 보상형 완료→힌트, 구독자 무광고, 409, 로드 실패 안내/비활성 | 미충족 | 정상 경로·중도 닫힘·광고 실패·409와 실패 후 구독 전환은 테스트에서 통과한다. 그러나 힌트 요청 중 제출하면 성공한 힌트를 버리는 D-31-4가 남는다. |
| S4 required 조건부 개인정보 설정 → 폼 | 충족 | `records_tab.dart:316`의 조건과 서비스 호출, `records_ad_privacy_test.dart`의 required/비required/구독자/탭 호출 검증을 확인했다. 실제 UMP 선택 변경 결과까지 검증한 것은 아니다. |
| 서비스 인터페이스/no-op·위젯 테스트·native audit·목업 비교 | 증거 부족 | 인터페이스와 no-op, 실제 화면/컨트롤러를 사용하는 위젯 테스트, 골든은 확인했다. 구현 증거의 audit 표는 소스·위젯 평가이고 실제 광고 렌더링 및 어댑티브 높이 측정은 미실시다. 전체 테스트 통과도 D-31-4의 부재를 증명하지 않는다. |

### 이전 결함 재판정

| ID / 이전 심각도 | 판정 | 근거와 재현 결과 |
|---|---|---|
| D-31-1 / MAJOR | FIXED | `interstitial_store.dart:23,44`가 최대 4개 ID 목록을 저장하고 `result_interstitial.dart:32`가 포함 여부를 확인한다. A→B→A→B에서는 2회만 요청한다는 테스트와 `nextShownPuzzleIds`의 두 언어 보존·중복·용량 테스트가 통과했다. 플랫폼 저장의 실제 재시작 검증은 하지 않았지만, 운영 저장소가 동일 순수 함수를 호출하는 배선도 확인했다. |
| D-31-2 / MAJOR | FIXED | `today_puzzle_controller.dart:101,128,154`의 `_submitDone` 완료와 대기 루프가 원래의 **제출 먼저 → 힌트 나중** 경합을 직렬화한다. 추가된 성공/힌트 실패 두 테스트는 제출 응답 전 hint-unlock 미전송, 시도 1행·남은 기회·힌트·submitting 해제를 실제 컨트롤러 상태로 검사하며 통과했다. 반대 순서는 원래 재현과 구분하여 신규 D-31-4로 기록한다. |
| D-31-3 / MAJOR | FIXED | `today_tab.dart:319`에서 광고 실패 기록을 광고가 필요한 경우에만 적용한다. 같은 화면에서 unavailable → entitlement true 전환 테스트가 안내 제거·버튼 활성·광고 재호출 없음·API 호출과 힌트 표시까지 검사하며 통과했다. |

### 신규 결함

#### D-31-4 — MAJOR — 힌트 응답 대기 중 제출하면 성공한 힌트가 폐기되고 광고를 다시 요구한다

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:99`, `mobile/lib/puzzle/today_puzzle_controller.dart:154`, `mobile/lib/puzzle/today_puzzle_controller.dart:165`; UI 진입과 후속 동작은 `mobile/lib/screens/today_tab.dart:197,287,301`.
- 요구: 광고 완료 후 힌트를 열고(US 4), 한 번 열린 힌트에 광고를 다시 요구하지 않아야 한다(US 5a). 구독자도 성공한 hint-unlock 결과가 표시되어야 한다(US 32).
- 재현 입력: 힌트가 없는 진행 중 퍼즐에서 보상형을 완료하거나 구독자 힌트 버튼을 누른다 → hint-unlock의 성공 응답 전달을 지연한다 → 여전히 활성인 답 입력/제출 버튼으로 유효한 답을 제출한다 → 제출 요청만 네트워크 오류로 끝낸다 → 앞서 성공한 hint-unlock 응답을 전달한다. 요청별 지연·실패는 독립적으로 발생할 수 있으며, 서버 성공 후 응답 전달 지연도 이 순서를 만든다.
- 기존 Fake로 구성 가능한 정확한 순서: `api.unlockHintGate = Completer<void>()`, `api.submitGuessError = NetworkApiException(...)` 설정 → `final opening = notifier.unlockHint()` → `await notifier.submit('지하촌역')` → `api.unlockHintGate!.complete()` → `await opening`과 `TodayPuzzleReady.puzzle.hint` 확인. 이는 재현 절차이며 이번 리뷰에서 새 테스트를 실행했다는 주장은 아니다.
- 기대: 제출 실패와 무관하게 성공한 힌트가 현재 같은 퍼즐에 남아야 한다. 입력을 직렬화하거나 최신 보드에 힌트를 병합/재조회해서 광고 없이 복구해야 한다.
- 실제 코드 경로: 힌트가 세대 N으로 출발하지만 힌트 진행 잠금은 `_HintSlot._busy`에만 있어 답 제출을 막지 않는다. submit은 세대를 N+1로 올린다. 제출 실패는 힌트가 없던 `puzzle` 스냅샷에 notice만 붙이고, 힌트 성공 응답은 168행 `_canCommit(N)`에서 false로 버려진다. `unlockHint()`는 false, 화면 hint는 null이며 UI는 “힌트를 열지 못했어요”를 표시한다. 비구독자가 다시 힌트 버튼을 누르면 `_preview()`가 보상형부터 재생한 뒤에야 서버의 이미 열림 409를 받아 재조회한다.
- 추가로 네트워크 실패 없이도, 먼저 발송한 힌트 요청이 서버에 늦게 도착해 제출이 먼저 처리되면 hint 없는 제출 응답이 남고 뒤의 힌트 성공이 같은 이유로 폐기된다. 서버 `guess_service.py:88,101`은 그 제출 처리 시점의 잠금 해제 상태만 응답하므로 클라이언트 발송 순서를 보장하지 않는다.
- 테스트 공백: 수정된 두 경합 테스트는 모두 `submit()`부터 시작한다. `_submitDone`은 이미 진행 중인 제출만 기다리므로 **unlockHint → submit** 순서는 보호하지 않는다. 세대 번호로 오래된 응답을 버리는 것만으로는 같은 퍼즐의 서로 다른 변경(시도/힌트)을 보존할 수 없다.

### 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| 루트 `uv run ruff check .` | `All checks passed!`, exit 0 |
| `cd mobile && flutter analyze` | `No issues found!`, exit 0 |
| `cd mobile && flutter test --reporter expanded` | `00:21 +465: All tests passed!`, exit 0 |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | `Formatted 146 files (0 changed)`, exit 0 |
| 지정 전용 자원으로 `uv run pytest -q` | `1403 passed in 1922.34s (0:32:02)`, exit 0; 재실행 없이 통과 |
| `git diff --check main...HEAD` | exit 0 |

백엔드 실행은 `TEST_DATABASE_URL`의 로컬 DB를 `chosung_daily_test_t31`, `TEST_REDIS_URL`을 `redis://127.0.0.1:6379/5`, `TEST_MIGRATION_DATABASE_URL`의 DB를 기존 `chosung_daily_test_t31_migrations`로 지정했다. 인증 값은 기록하지 않는다. 신규 DB를 생성하지 않았고 기본 DB로 전환하지 않았다. `app/`, `web/`, `tests/`, `migrations/`, `.env.example` diff는 비어 있다. 마이그레이션 변경이 없으므로 조건부 `flask db heads`는 해당하지 않는다.

### 보안·범위·공유 파일 및 참고

- hint-unlock은 기존 인증 옵션을 재사용한다. 서버 인증/CSRF 우회, 서버 행 삭제나 시도 중복 기록, 실제 비밀 값 커밋은 발견하지 못했다. D-31-4는 서버의 힌트 성공 상태를 클라이언트가 놓치는 결함이다.
- README/RELEASE는 `### 31.`만 추가했고 스펙도 자기 번호의 미정 항목만 덧붙였다. 기존 다른 티켓 행을 바꾸지 않았다. AdMob 식별자는 Google 테스트용 공개 ID이며 키·토큰·비밀번호가 아니다.
- 라이트·다크 390 및 태블릿 1024 골든을 직접 열어 HintCard 레이블·슬롯·rail/2열을 확인했다. 빈 슬롯 캡션, 기존 전폭 버튼 등 취향 차이는 결함으로 세지 않는다.
- 실제 SDK `canRequestAds`, UMP 재선택 후 상태 반영, 배너 실측·네이티브 광고 렌더링에 관한 기존 한계는 해결되지 않았다. 실기기·외부 광고·스토어·프로덕션은 호출하지 않았으며 네이티브 빌드 성공 주장도 이번 라운드에서 재검증하지 않았다.

판정: FAIL

## 라운드 3

### 범위와 결론

- 로컬 `main` = `b11f0111356faab7abe5551127f3bf71a7248180`, 구현 HEAD = `99c8305b0f1b6e0a9446884cdcb69516e2208e3e`. `git log main..HEAD`의 13개 커밋과 `git diff main...HEAD`를 확인했다. origin/main은 사용하지 않았다.
- 티켓, 스펙 §A.5·§B.21·§B.23/관련 US, SCREENS S1/S2/S4/S6/T0/T1/T4, OVERRIDES §5~7, e1_home/e7_home_dark 목업 및 구현 증거를 대조했다. 티켓 30 통합의 알림 초기화·설정 행·새 골든도 검토했다.
- 기존 D-31-1~4의 원래 재현은 모두 FIXED. 신규 **BLOCKER 0 / MAJOR 2 / MINOR 0**, REPEAT 0이다. 신규 두 건은 아래 실제 소스의 비동기 실행 순서로 확인한 결함이며, 새 재현 테스트를 작성·실행했다는 뜻은 아니다. 앱·테스트·설정·스펙은 수정하지 않았다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 근거 |
|---|---|---|
| ApiClient hint-unlock — Dio + Fake | 충족 | `dio_api_client.dart:89`가 기존 인증 옵션과 puzzle_id를 전달한다. API 테스트는 메서드·경로·본문·인증 헤더·409 타입을 검사하며 통과한다. |
| 순수 광고 게이트·UMP 4종·구독자·오류/재시작·entitlement Provider | 충족 | `ad_gate.dart`, `ad_providers.dart`, 초기 null 권한 및 관련 테스트를 확인했다. 권한 갱신·타이머는 티켓 33 소유다. |
| UMP update → 폼 → canRequestAds → initialize, ATT 후 실행, 광고 ID | 증거 부족 | update/폼/ATT 대기/initialize 및 define/디버그 ID 배선은 있다. `google_ad_service.dart:28`은 SDK canRequestAds 대신 getConsentStatus를 반환하고 `ad_gate.dart:30`이 허용값을 계산한다. 실제 SDK 값과의 일치는 Fake 테스트로 검증되지 않았다. 이전 라운드처럼 실제 오노출을 단정해 별도 결함으로 세지 않았다. |
| 배너 예약·실패·구독자 제거·태블릿 폭 변경, 전면 퍼즐당 1회 | 미충족 | 배너 폭 변경·dispose·예약 높이·구독자 제거 및 전면 순차 재진입/언어 왕복 테스트는 통과한다. 전면 로드 중 다시 결과 시트를 열고 닫으면 같은 퍼즐의 동시 요청이 모두 통과한다(D-31-5). |
| 보상형 완료→힌트·구독자 무광고·409·실패 안내/비활성 | 미충족 | 정상 두 경로·중도 닫힘·광고 불가·구독 전환·제출과 힌트 양방향 경합 테스트는 통과한다. 힌트 요청 중 시작된 재조회가 성공한 힌트를 되돌리는 D-31-6은 남아 있다. |
| S4 required 조건부 개인정보 설정 → 폼 | 충족 | `records_tab.dart:312`의 조건부 행/구분선과 폼 호출을 확인했다. required/비required/구독자/탭 호출 테스트가 통과하며 알림 행과 함께 배치된다. |
| 서비스 인터페이스/no-op·위젯 테스트·native audit·목업 비교 | 증거 부족 | 인터페이스·no-op·실제 화면/컨트롤러 테스트와 골든을 확인했고 Android APK도 직접 빌드했다. audit 18/20은 소스·위젯 기반이며 실제 광고 렌더링·어댑티브 높이 실측은 없다. |

### 이전 결함 재판정

| ID / 이전 심각도 | 판정 | 근거 |
|---|---|---|
| D-31-1 / MAJOR | FIXED | `interstitial_store.dart:23,44`의 ID 목록 저장 및 `result_interstitial.dart:32`의 포함 여부 확인. A→B→A→B 테스트가 2회만 요청함을 검사하고 통과한다. D-31-5는 저장 용량이 아니라 동시 진입의 다른 원인이다. |
| D-31-2 / MAJOR | FIXED | `today_puzzle_controller.dart:162`의 제출 완료 대기가 제출 먼저→힌트 나중 요청을 직렬화한다. 성공/실패 테스트가 시도·남은 기회·잠금 해제를 확인하며 통과한다. |
| D-31-3 / MAJOR | FIXED | `today_tab.dart:319`가 광고 실패를 광고가 필요한 동안에만 적용한다. unavailable→entitlement true 전환 테스트가 안내 제거·활성화·추가 광고 없음·힌트 표시까지 확인하며 통과한다. |
| D-31-4 / MAJOR | FIXED | `today_puzzle_controller.dart:111,183,267`이 최신 보드에 제출/힌트/실패 안내를 병합한다. 힌트 대기 중 제출 성공·실패, 힌트 먼저 응답, 409 재조회 등 컨트롤러 4개 및 화면 1개 회귀 테스트가 통과한다. 원래 제출 경합은 고쳐졌으며 D-31-6은 refresh와의 별도 경합이다. |

### 신규 결함

#### D-31-5 — MAJOR — 전면 로드 중 결과 시트 재진입으로 같은 퍼즐 광고 중복 노출

- 위치: `mobile/lib/ads/result_interstitial.dart:32`, `mobile/lib/ads/result_interstitial.dart:34`, `mobile/lib/screens/today_tab.dart:94`, `mobile/lib/screens/today_tab.dart:122`, `mobile/lib/ads/google_ad_service.dart:85`.
- 요구: US 24 및 티켓의 결과 확인 후 **퍼즐당 최대 1회**.
- 재현 입력: 광고 가능 비구독자가 퍼즐을 끝내고 결과 시트를 닫는다 → 첫 전면 로드를 지연한다 → 활성 상태인 “결과 보기”를 다시 열고 닫는다 → 첫 광고의 로드/표시/닫힘을 완료한 뒤 두 번째 광고 로드 성공을 전달한다.
- 기대: 같은 퍼즐의 로드/표시가 진행 중이면 두 번째 요청을 합치거나 무시하여 최대 한 번만 표시한다.
- 실제: 첫 호출은 hasShown=false 후 showInterstitial을 기다린다. 기록은 광고가 닫힌 후 35행에서 남는다. 그 사이 두 번째 호출도 false를 읽어 별도 로드를 시작한다. GoogleAdService는 로드가 끝나면 바로 show하며 기록을 다시 검사하지 않으므로 두 번째 로드가 첫 광고 닫힘 뒤 완료되면 두 번 표시한다. `_openResult`의 await는 해당 호출만 기다릴 뿐 onShowResult를 비활성화하거나 다른 호출을 막지 않는다.
- 재현 구성: 기존 컨테이너에서 markSubmitted 후 같은 puzzleId의 showAfterResultSheet 두 호출을 await 없이 시작하여 Future.wait로 모으면 두 호출이 저장 전 검사를 통과할 수 있다. 실제 표시 순서는 위처럼 두 로드 완료 시점을 제어한다. 기존 `result_interstitial_test.dart`는 첫 호출을 **await한 뒤** 두 번째를 부르고 Fake 광고도 즉시 성공하므로 로드 중 재진입을 검증하지 않는다.

#### D-31-6 — MAJOR — 힌트 요청 중 복귀 재조회가 성공한 힌트를 다시 잠근다

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:69`, `mobile/lib/puzzle/today_puzzle_controller.dart:175`, `mobile/lib/puzzle/today_puzzle_controller.dart:185`, `mobile/lib/puzzle/today_puzzle_controller.dart:308`; 재광고 진입은 `mobile/lib/screens/today_tab.dart:287`.
- 요구: US 4·5a — 열린 힌트가 유지되고 같은 힌트를 위해 광고를 다시 보지 않아야 한다.
- 재현 입력: 힌트 없는 퍼즐에서 광고 완료 후 hint-unlock 요청을 지연한다 → 앱을 백그라운드로 보냈다 복귀하여 refresh 시작(GET은 아직 힌트 없는 서버 상태를 읽고 응답 전달만 지연) → hint-unlock 성공을 먼저 전달해 힌트를 표시한다 → 앞서 읽은 GET 응답을 전달한다. 서버 `puzzle_service.py:51`의 조회는 힌트 쓰기 완료를 기다리는 잠금이 없으므로 이 처리/응답 순서는 가능하다.
- 기대: 현재 같은 퍼즐에서 이미 성공한 힌트는 보존되거나 최신 상태를 다시 읽어야 한다.
- 실제: refresh는 `_submitting`만 검사하므로 힌트 진행 중에도 세대를 N+1로 올리고 GET을 보낸다. 힌트 성공은 같은 퍼즐에 병합하지만 세대를 바꾸지 않는다. 뒤늦은 GET은 최신 N+1로 인정되어 `_commitLoad`가 보드 전체를 hint=null / hintUnlocked=false로 교체한다. HintCard는 다시 광고 버튼을 표시하고 다음 탭은 보상형부터 재실행한다.
- 기존 Fake 재현 순서: 첫 보드 로드 후 unlockHintGate와 fetchTodayPuzzleGate 설정 → `opening = notifier.unlockHint()` → `refreshing = notifier.refresh()` → hint gate 완료 및 opening 대기(힌트 표시) → fetch gate 완료 및 refreshing 대기(힌트 null). Fake GET은 262행에서 호출 당시 puzzle을 캡처하므로 이 순서를 표현할 수 있다. 이는 재현 절차이며 이번 리뷰에서 테스트 파일을 추가하지 않았다.
- 테스트 공백: 이번 수정은 submit↔hint 양방향, 기존 조회 테스트는 submit↔refresh를 확인한다. hint↔refresh에서 성공한 힌트가 뒤늦은 GET으로 사라지는 순서는 없다. 서버 행 삭제가 아닌 클라이언트 표시와 재광고 문제다.

### 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| `uv run ruff check .` | All checks passed, exit 0 |
| `cd mobile && flutter analyze` | No issues found, exit 0 |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | Formatted 166 files (0 changed), exit 0 |
| `cd mobile && flutter test --reporter expanded` | 00:42 +550 -1, exit 1. 실패는 아래 티켓 30 참고 1건 |
| `cd mobile && flutter test --no-pub test/ads test/puzzle/today_puzzle_controller_test.dart test/screens/today_tab_ads_test.dart test/screens/records_ad_privacy_test.dart test/api/dio_api_client_test.dart --reporter expanded` | 00:09 +115: All tests passed, exit 0 |
| `cd mobile && flutter build apk --debug` | Built build/app/outputs/flutter-apk/app-debug.apk, exit 0; 확인 후 코디네이터 지시대로 mobile/build 삭제 |
| 지정 전용 자원으로 `uv run pytest -q` | 1412 passed in 1336.55s (0:22:16), exit 0; 재실행 없이 통과 |
| `git diff --check main...HEAD` | exit 0 |

백엔드는 기존 chosung_daily_test_t31, Redis DB 5, chosung_daily_test_t31_migrations를 각각 TEST_DATABASE_URL / TEST_REDIS_URL / TEST_MIGRATION_DATABASE_URL로 지정했다. 인증 값은 기록하지 않는다. 새 DB를 만들지 않았으며 기본 DB로 전환하지 않았다. app/, web/, tests/, migrations/, .env.example의 main 대비 diff는 비어 있고 마이그레이션 변경이 없으므로 조건부 flask db heads는 해당하지 않는다.

### 보안·범위·공유 파일 및 참고

- hint-unlock은 기존 인증 옵션을 사용한다. 서버 인증·CSRF 우회, 서버 데이터 삭제, 실제 키·토큰·비밀번호의 신규 기록은 발견하지 못했다. AdMob 값은 공개 테스트 식별자다.
- README와 RELEASE는 자기 `### 31.` 절만 덧붙였고 스펙은 자기 번호의 미정 항목만 추가했다. 티켓 30의 알림 초기화/리시버/설정 행이 유지됐으며 광고와 함께 Android 빌드가 통과했다.
- records_light_390, records_tablet_1024, records_notification_off_390, today_light_390, today_dark_390 골든을 직접 열었다. 알림 행·권한 거부 안내, 조건부 개인정보 행 제거, 폰/태블릿 배치 및 HintCard/예약 슬롯을 확인했다. 빈 광고 캡션 등 취향 차이는 결함으로 세지 않는다.
- Flutter 전체의 유일한 실패는 `mobile/test/notifications/notification_controller_test.dart:110`에서 daily-first 고정 순서와 현재 시간에 따른 reminder-first 실제 순서의 차이다. 테스트 파일은 main 대비 변경되지 않았고 코디네이터도 티켓 30의 알려진 결함으로 별도 수정을 지시했으므로 티켓 31 결함 수에 넣지 않는다. 공유 DB 충돌에 따른 간헐 실패가 아니다.
- 실제 광고·UMP 재선택·어댑티브 높이 실측·iOS 네이티브 실행은 확인하지 않았다. 프로덕션/NAS/스토어에는 접속하지 않았다. 기존 audit 점수를 실제 SDK 동작 검증으로 대체하지 않는다.

판정: FAIL

## 라운드 4

### 범위와 결론

- 로컬 main `d78e0820ab8bcc3af785df86d589fdf32386bb15`, 검토 HEAD `45bd130eca51fb9fc7cfe9caf0a9c0cb431ed028`. `git diff main...HEAD`, `git log main..HEAD` 16개 커밋, 티켓·스펙 §A.5/§B.21/§B.23·관련 US·CONTEXT·구현 증거·이전 리뷰를 대조했다. origin/main은 사용하지 않았다.
- SCREENS S1/S2/S4/T0/T1, OVERRIDES 우선 규칙, e1_home/e7_home_dark를 확인했다. records_light_390/records_tablet_1024/records_notification_off_390와 today_light_390/today_dark_390/today_tablet_1024 골든을 직접 열어 계정 카드·알림 행·조건부 광고 개인정보 행·HintCard·예약 슬롯을 확인했다.
- 기존 D-31-1~6은 원래 재현 기준 모두 FIXED, REPEAT 0. 신규 **BLOCKER 0 / MAJOR 1 / MINOR 0**. D-31-7은 소스 실행 순서로 확인했으며 아래 재현 절차를 새 테스트 파일로 작성·실행한 것은 아니다. 앱·테스트·설정·스펙은 수정하지 않았다.

### 티켓 체크박스별 판정

| 체크박스 | 판정 | 직접 확인한 근거 |
|---|---|---|
| ApiClient hint-unlock — Dio + Fake | 충족 | dio_api_client.dart:89의 POST·puzzle_id·기존 인증 옵션과 Fake 확인. Dio 테스트는 메서드·본문·Authorization·409 예외 타입을 검사한다. |
| 순수 광고 게이트·UMP 4종·구독자·오류/재시작·entitlement 초기 null | 충족 | ad_gate.dart/ad_providers.dart/entitlement_provider.dart 및 관련 테스트 확인. 권한 갱신·타이머는 33 소유다. |
| UMP update → 폼 → SDK canRequestAds → initialize, ATT 이후, 광고 ID | 증거 부족 | update/폼/ATT 대기·복구/initialize·define/디버그 ID 배선은 있다. google_ad_service.dart:28은 SDK canRequestAds 대신 ConsentStatus를 반환하고 ad_gate.dart:30은 자체 허용값을 계산한다. Fake로 SDK 값과의 일치를 증명하지 못한다. 이전 라운드와 같은 한계이며 실제 오노출로 단정해 신규 결함으로 세지 않았다. |
| 배너 예약·실패·구독자 제거·태블릿 폭 재요청, 전면 퍼즐당 1회 | 충족 | 실제 셸 테스트의 폭·높이·dispose 검증, 첫 제출 전/구독자 차단, 언어 왕복, 같은 퍼즐 동시 요청 합치기와 요청 전 영속 예약 확인. 실기기 배너 높이 실측은 별도 한계다. |
| 보상형 완료→힌트·구독자 무광고·409·실패 안내/비활성 | 미충족 | 정상 두 경로·중도 닫힘·409·실패 후 구독 전환과 제출/조회 경합 테스트는 통과한다. 계정 경계×힌트의 누락으로 새 계정 보드에 이전 계정 응답을 섞는다(D-31-7). |
| S4 required일 때 개인정보 설정 → 폼 | 충족 | records_tab.dart:314의 조건부 행·구분선과 폼 호출, required/비required/구독자 테스트 확인. 실제 UMP 재선택 결과까지 검증한 것은 아니다. |
| 인터페이스/no-op·위젯 테스트·native audit·목업 대비 | 증거 부족 | 실제 화면/컨트롤러 테스트, no-op 경계, 골든과 Android APK 빌드 확인. audit 18/20은 소스·위젯 기반이며 실제 광고 렌더링·어댑티브 높이 실측은 없다. 증거의 “모든 경로 쌍” 주장에는 계정 경계×힌트가 빠졌다. |

### 이전 결함 재판정

| ID / 이전 심각도 | 판정 | 직접 확인한 근거 |
|---|---|---|
| D-31-1 / MAJOR | FIXED | interstitial_store.dart의 최대 4개 ID 목록·중복 제거, A→B→A→B 테스트가 두 퍼즐의 예약을 유지한다. |
| D-31-2 / MAJOR | FIXED | today_puzzle_controller.dart:256의 제출 완료 대기와 235행의 완료 처리가 제출 먼저→힌트 나중을 직렬화한다. 성공/실패 회귀 테스트가 시도·남은 기회·입력 잠금을 검사한다. |
| D-31-3 / MAJOR | FIXED | today_tab.dart:319는 광고가 필요한 동안만 실패 상태를 적용한다. unavailable→entitlement true 테스트가 안내 제거·활성화·광고 재호출 없음·힌트 표시까지 검사한다. |
| D-31-4 / MAJOR | FIXED | today_puzzle_controller.dart:215,278이 현재 보드에 제출과 힌트를 병합한다. 힌트 중 제출 성공/실패, 힌트 먼저 응답, 409 재조회 회귀 테스트 통과. |
| D-31-5 / MAJOR | FIXED | result_interstitial.dart:45의 퍼즐별 진행 Future와 58행의 요청 전 예약이 같은 퍼즐 동시 진입을 막는다. 지연 광고·완료 전 예약 테스트 통과. 실제 저장소도 setStringList 완료 뒤 광고를 요청한다. |
| D-31-6 / MAJOR | FIXED | today_puzzle_controller.dart:59,165,302가 힌트 중 refresh를 미루고 종료 후 실행한다. 지연 hint/fetch 테스트가 중간 GET 미발송과 이후 재조회·힌트 보존을 검사한다. 계정 discard 경합은 별개로 D-31-7에 기록한다. |

### 신규 결함

#### D-31-7 — MAJOR — 계정 전환 전에 요청한 힌트 응답이 새 계정 보드를 연다

- 위치: `mobile/lib/puzzle/today_puzzle_controller.dart:272`, `mobile/lib/puzzle/today_puzzle_controller.dart:278`, `mobile/lib/puzzle/today_puzzle_controller.dart:360`. 전환 진입: `mobile/lib/account/account_controller.dart:153`.
- 요구: 힌트 미리 보기는 현재 게스트의 퍼즐 상태에 반영되어야 하고(US 4·5a·32), 계정 전환 뒤에는 전환한 게스트의 기록이어야 한다(US 19). 날짜·언어별 puzzle_id는 게스트 간 공용이며 계정 식별자가 아니다.
- 재현 입력: A의 진행 중 퍼즐 P에서 보상형 완료 후 또는 구독자 경로로 hint-unlock 전송 → 서버는 A의 힌트를 열되 응답 전달 지연 → 내 기록에서 백업 코드/계정 연결로 B로 전환 → B의 같은 P 보드(hint=null, hintUnlocked=false)를 먼저 로드 → A의 성공 응답 전달. 힌트 대기 중 탭 이동·계정 전환은 막혀 있지 않다.
- 기대: A 응답은 B 보드를 변경하지 않는다. B가 열지 않은 힌트는 잠긴 상태로 남는다.
- 실제: `_adopt`는 토큰 교체 후 discard로 세대를 올리고 B 보드를 읽는다. 그러나 unlockHint는 요청 당시 계정 epoch를 보관하거나 응답에서 검사하지 않으며 `_boardFor`도 puzzleId만 검사한다. 같은 P이므로 282행이 B 보드에 A 응답의 hint 및 hintUnlocked=true를 쓴다. B 서버에는 unlock 기록이 없어 다음 재조회에서 다시 잠긴다. 서버 데이터 삭제가 아니라 현재 계정 표시·힌트 상태의 혼합이다. 서버의 hint_service.py는 HintUnlock을 guest_id+puzzle_id로 기록하고 puzzle_service.py도 같은 조합으로 조회하므로 B의 서버 상태와 불일치함을 확인했다.
- 기존 Fake 재현 구성: A 보드 로드 → `api.unlockHintGate = Completer<void>()` → `opening = notifier.unlockHint()` → guestTokenProvider의 replaceWith로 가짜 B 토큰 채택 → `await notifier.discard()`로 같은 puzzle_id의 잠긴 B 보드 로드 → hint gate 완료 → `await opening` → B의 hintUnlocked가 true가 된다. 실제 계정·인증 정보를 입력하지 않았고 이 절차를 새 테스트로 실행하지 않았다.
- 같은 누락의 쓰기 입구: submit은 204행의 `_account.sendIfSameAccount(_accountEpoch, ...)`로 옛 보드의 새 계정 쓰기를 막지만 unlockHint 272행은 API를 직접 호출한다. 401 복구 등 토큰만 교체된 입구에서는 옛 보드의 힌트 요청이 새 토큰으로 나간다. 제출 대기 뒤 실행하는 힌트도 최초 요청 계정을 고정하지 않는다.
- 테스트 공백: 증거의 마지막 경로 쌍은 “계정 경계 × 조회·제출”뿐이다. 티켓 29 테스트는 조회/제출을 검사하며 새 힌트 쓰기·늦은 힌트 응답의 계정 격리는 검사하지 않는다. discard에 `_unlockingHint=false`를 추가해도 응답 소유 계정 검증을 대신하지 못한다. 일반 submit↔hint·refresh↔hint 테스트 통과로 이 조합을 대신할 수 없다.

### 직접 실행한 검증

| 명령 | 결과 |
|---|---|
| `uv run ruff check .` (루트) | All checks passed, exit 0 |
| `cd mobile && flutter analyze` | No issues found, exit 0 |
| `cd mobile && dart format --output=none --set-exit-if-changed .` | Formatted 178 files (0 changed), exit 0 |
| `cd mobile && flutter test --reporter expanded` | 01:19 +629: All tests passed, exit 0. 티켓 30 이전 벽시계 실패도 없다. |
| `cd mobile && flutter build apk --debug` | Built build/app/outputs/flutter-apk/app-debug.apk, exit 0; 코디네이터 지시대로 확인 후 mobile/build 삭제 |
| 지정 전용 자원으로 `uv run pytest -q` | 1412 passed in 1091.54s (0:18:11), exit 0; 재실행 없이 통과 |
| `git diff --check main...HEAD` | exit 0 |

백엔드는 기존 로컬 DB chosung_daily_test_t31, Redis DB 5, 마이그레이션 DB chosung_daily_test_t31_migrations를 TEST_DATABASE_URL / TEST_REDIS_URL / TEST_MIGRATION_DATABASE_URL로 지정했다. 인증 값은 기록하지 않는다. 새 DB를 만들지 않았고 기본 DB로 전환하지 않았다. main 대비 app/, web/, tests/, migrations/, .env.example 변경은 없어 조건부 flask db heads는 해당하지 않는다.

### 보안·범위·공유 파일과 참고

- 새 HTTP 쓰기는 기존 Bearer 인증 옵션을 쓰고 서버 인증/CSRF를 바꾸지 않는다. 클라이언트 계정 격리의 누락은 D-31-7에 명시했다. 서버 데이터 삭제 경로·실제 시크릿의 신규 기록은 발견하지 못했다. AdMob 값은 공개 테스트 식별자다.
- README·RELEASE는 자기 `### 31.` 절, 스펙 미정 항목은 티켓 31 자기 항목만 추가했다. 계정 예외·클라이언트 ID·Secrets include, 알림 초기화·행과 광고 설정이 함께 유지됨을 diff에서 확인했다. 범위 밖 기능 변경은 발견하지 못했다.
- README 31절의 “로드 실패 시 플래그를 남기지 않는다”는 최신 요청 전 예약·실패 시 유지 정책과 달라 문서 갱신이 필요하다. 런타임 결함 수에는 추가하지 않는다.
- 빈 슬롯 캡션·기존 버튼 폭·스크롤 배치 등 취향 차이는 결함으로 세지 않았다. UMP canRequestAds 직접 확인, 실제 재선택·광고 렌더링·iOS 실행·어댑티브 크기 실측은 별도 검증 한계다. 프로덕션·NAS·실제 외부 서비스에는 접속하지 않았다.

판정: FAIL
