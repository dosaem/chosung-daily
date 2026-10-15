# 티켓 32 구현 증거 — 구독 구매 흐름(스트림·서버 검증·완료·복원)·Paywall S5·S4 구독 카드

**브랜치:** `dosaem/t32-app-subscription-purchase-paywall` · **날짜:** 2026-10-15
**범위:** Flutter 앱(`mobile/`) + README "설계 판단" `### 32.`·Flutter 절 한 단락 ·
`docs/RELEASE.md` `### 32.`. 백엔드·웹은 한 줄도 건드리지 않았다
(`app/`·`web/`·`migrations/`·`tests/` 변경 0건 — **마이그레이션을 만들지 않았다**).
스펙·티켓·디자인 파일도 건드리지 않았다(`.scratch/` 변경 0건 — 이 티켓이 확정한
"미정 항목" 이 없다. 미정 20 은 티켓 26 이 이미 확정했고 이 티켓은 그 이름을 쓴다).

## 0. 한 줄 요약

Paywall(S5)에서 **스토어 현지화 가격**으로 월 구독을 시작하면 구매 스트림 → (pending
대기, 버튼 비활성 "결제 확인 중") → `POST /subscriptions/verify` → **성공 응답 뒤에만**
`completePurchase` 순서로 끝나고, verify 응답의 `entitlement` 가 31 의
`entitlementProvider` 에 바로 들어가 배너 슬롯이 사라진다. 검증 실패·앱 종료로 끊긴
구매는 완료하지 않아 다음 시작의 스트림·`restorePurchases` 동기화로 다시 올라가고,
"구매 복원" 은 같은 길을 수동으로 한 번 더 탄다. S4 구독 카드는 미구독/구독 중/유예
중 세 얼굴을 보여준다. 앱 테스트 **733개 통과**(이 티켓이 더한 건 60개 — 골든 3장 포함, records 골든 4장 갱신),
`flutter analyze` 0건 · `dart format` 변경 없음 · 백엔드 `ruff check` 통과 ·
`pytest` 1509개 통과(§6).

## 1. 티켓 체크박스 ↔ 증거

| 체크박스 | 증명하는 테스트/명령 | 위치 |
|---|---|---|
| ApiClient 에 `POST /subscriptions/verify` 추가(Dio + Fake) | `test/api/dio_api_client_test.dart` "POST /subscriptions/verify 는 스토어·영수증을 보내고 권한을 돌려준다"·"…RECEIPT_INVALID 예외다"·"…STORE_UNAVAILABLE 예외다"(3) + `test/api/api_models_test.dart` `Entitlement.fromJson`(3). Fake 는 `test/fakes/fake_api_client.dart`(`verifyResponse`·`verifiedReceipts`·`verifySubscriptionError`·`verifySubscriptionGate`) | §3.1 |
| `in_app_purchase`(StoreKit2 활성화, Android release merged manifest 에서 Play Billing 8+ 확인 절차를 RELEASE.md 자기 절에). 상품 `adfree_monthly`, 가격은 `ProductDetails.price` 그대로(상수 금지) | `pubspec.yaml`(`in_app_purchase ^3.3.1` + `in_app_purchase_storekit ^0.4.13`), `test/config/bootstrap_test.dart` "iOS 는 StoreKit 2 로 돈다", Billing 절차는 `docs/RELEASE.md "### 32."`(실측: 플러그인이 `billing:8.0.0` 을 가져온다 — §3.2), 상품 ID 는 `test/subscription/subscription_state_test.dart` "상품 ID 는 스펙 §B.23 의 하나뿐이다", 가격 상수 금지는 `test/subscription/paywall_sheet_test.dart` "S5: …"(`₩1,500` 이 Fake 상품에서 온다)·"가격을 못 읽으면 구독 시작을 잠근다" | §3.2 |
| 구매 스트림 → pending 대기(버튼 비활성) → verify → 성공 후에만 `completePurchase`. 실패·종료 시 다음 시작에 재전송. 시작·복귀의 `restorePurchases`/`queryPurchases` 결과도 verify 로 재전송. verify 응답 `entitlement` 로 31 의 Provider 즉시 갱신(새 Provider 금지) | `test/subscription/purchase_controller_test.dart`(15) — "구매 → 서버 검증 성공 → 그때서야 completePurchase", "검증이 떠 있는 동안은 verifying", "스토어가 결제를 붙잡고 있으면 pending — 검증은 아직 안 올린다", "검증 실패(스토어 장애)면 완료하지 않고 사유를 남긴다", "시작하면 상품 가격을 읽고 스토어와 동기화한다", "복원된 구매도 같은 길로 검증·완료된다", "같은 거래가 여러 번 올라와도 검증은 한 번만", "검증 중 계정이 바뀌면 권한도 완료도 건너뛴다". Provider 갱신은 `test/ads/entitlement_test.dart` + `test/subscription/purchase_entitlement_test.dart`(실제 앱 트리에서 배너 슬롯 제거) | §3.3 |
| 구매 상태→UI 판정 순수 함수(idle/pending/verifying/active/grace/error) 단위 테스트 | `test/subscription/subscription_state_test.dart`(15) — 6개 상태 전부 + 우선순위 3건(verifying > pending, 권한 > 실패, 취소 ≠ 실패) + 경계 2건(유예 종료·보류는 권한 없음) | §3.4 |
| S5 Paywall: 제목·혜택 3줄("광고 없이 힌트 미리 보기" 포함)·가격 카드·`primary-button` 구독 시작·구매 복원·약관/개인정보 링크·자동 갱신 안내. `paywall_view`·`subscribe_start` 발화 | `test/subscription/paywall_sheet_test.dart` "S5: 제목·혜택 3줄·가격 카드·구독 시작·구매 복원·링크", "진입에 paywall_view, 구독 시작 탭에 subscribe_start 를 찍는다"(no-op Analytics 로 확인), "약관·방침 링크는 UI 언어로 웹 문서를 연다" | §3.5 |
| 자동 갱신 안내·링크 문구가 16 의 체크리스트 필수 요소 6개를 전부 담고 ko/en 이 약관 구독 절과 같은 표현(위젯 테스트: 요소 6개). 태블릿: 폭 744 가운데 다이얼로그(위젯 테스트 1건) | `test/subscription/paywall_sheet_test.dart` "자동 갱신 고지의 필수 요소 6개가 다 있다 (legal-checklist \"4.\")"(키 6개 + 약관과 같은 문구 5건)·"영어 UI 는 영문 약관과 같은 표현을 쓴다"·"태블릿 폭(744)에서는 가운데 다이얼로그로 뜬다 (SCREENS T2)" | §3.5 |
| 27 의 S4 구독 카드 자리를 채움: 미구독 → Paywall / 구독 중 "광고 제거 · 갱신일" / 유예 중 "결제 확인 중 · 유예 …까지" + "관리"(스토어로) | `test/screens/records_subscription_test.dart`(6) — 세 얼굴 + "관리" 가 **권한이 온 스토어**를 여는지(Apple·Google 각 1건) + 가격 미확인 + 보류(hold) + en | §3.6 |
| 위젯 테스트: 구독자 배너 제거, pending 버튼 비활성, 복원 성공, 분석 이벤트 2개 | 순서대로 `test/subscription/purchase_entitlement_test.dart` "구매가 서버 검증을 통과하면 배너 슬롯이 바로 사라진다", `paywall_sheet_test.dart` "pending 이면 구독 시작이 비활성이고…"·"서버 검증 중에도 버튼이 잠긴다", "구매 복원이 성공하면 권한이 들어오고 확인 화면으로 바뀐다", "진입에 paywall_view, 구독 시작 탭에 subscribe_start 를 찍는다" | §3 |
| `audit.native`(태블릿 폭 포함) 통과 + audit 표 | §4 (5축 18/20, 태블릿 폭 744·1024) | §4 |
| 목업 `e5_paywall`·`e4_records`(구독 카드) 대비 기록 | §5 (Paywall 골든 3장 신규 + records 골든 4장 갱신 + 차이 3건 기록) | §5 |
| README Flutter 절에 구독 상태 흐름 한 단락 | `README.md` "### 22. Flutter 앱" 의 **"구독 상태 흐름(티켓 32)"** 단락. 설계 판단은 "### 32.", 사람 작업은 `docs/RELEASE.md "### 32."` | §2 |

## 2. 무엇을 어디에 뒀는가

| 파일 | 하는 일 |
|---|---|
| `lib/subscription/subscription_state.dart` | 상품 ID 상수 · `SubscriptionPhase` · `subscriptionPhaseFor`(순수) · `subscriptionStoreFor`(영수증 출처 → `store`) · `subscriptionManagementUrl` |
| `lib/subscription/purchase_service.dart` | `PurchaseService` 인터페이스 · `NoopPurchaseService`(provider 기본값) · `StorePurchaseService`(실제 `in_app_purchase`) |
| `lib/subscription/purchase_controller.dart` | `purchaseServiceProvider` · `PurchaseFlow` · `PurchaseFlowNotifier`(스트림·검증·완료·복원·복귀 동기화) · `subscriptionPhaseProvider` |
| `lib/subscription/paywall_sheet.dart` | S5 Paywall(`showPaywallSheet` + `PaywallSheet`) · `PaywallKeys`(고지 요소 6개 포함) · `entitlementDateLabel` |
| `lib/subscription/entitlement_provider.dart` | **(31 소유, 이 티켓이 넓힘)** `bool?` → `Entitlement?`. 권한·갱신일·유예가 한 자리에 |
| `lib/widgets/subscription_card.dart` | S4 구독 카드 세 얼굴 + "관리" |
| `test/golden/paywall_golden_test.dart` | S5 골든 3장(라이트·다크·태블릿 744) |
| `lib/api/api_models.dart` | `SubscriptionStore` · `SubscriptionStatus` · `Entitlement`(UTC 정규화) |
| `lib/api/api_client.dart` · `dio_api_client.dart` | `verifySubscription({store, receipt})` |
| `lib/api/api_exception.dart` | `ReceiptInvalidApiException`(400) · `StoreUnavailableApiException`(503) + `code` 표 2줄 |
| `lib/ads/ad_providers.dart` | 게이트에 `entitlement?.active` 만 넘긴다 |
| `lib/screens/records_tab.dart` | 자리(`RecordsSlot.subscription`)를 `SubscriptionCard` 로 교체 |
| `lib/app.dart` | 구매 흐름을 앱 수명에 매단다(`ref.listen`, 알림과 같은 방식) |
| `lib/main.dart` | `purchaseServiceProvider` → `StorePurchaseService` override |
| `pubspec.yaml`/`.lock` | `in_app_purchase ^3.3.1` · `in_app_purchase_storekit ^0.4.13` |
| `assets/translations/{ko,en}.json` | `subscription.*` 34키(고지 문구는 웹 약관 `terms#subscription` 과 같은 표현) |

설계 판단은 README "### 32." 에, 사람이 해야 하는 일(상품 등록·유예 설정·Sandbox
확인·Billing 8+ 확인 절차)은 `docs/RELEASE.md` "### 32." 에 적었다.

## 3. 실제로 확인한 것

### 3.1 ApiClient (Dio + Fake)

`POST /subscriptions/verify` 는 `{store, receipt}` 를 보내고 Bearer 를 붙인다. 응답은
`{active, until, status, source, next_check_at}` 이고, 시각은 **받는 즉시 UTC 로
정규화**한다(서버가 타임존을 붙여 보낸다 — `app/schemas/subscription.py`). 모르는
`status`·`source` 라벨은 null 로 떨어뜨리되 `active` 는 그대로 쓴다(서버 판정이 권한의
정본이라, 라벨을 모른다고 광고를 켜면 안 된다).

실패는 `code` 로 두 갈래다 — 400 `RECEIPT_INVALID`(다시 올려도 같은 답), 503
`STORE_UNAVAILABLE`(일시적). 503 이지만 `ServerApiException` 이 아니라 전용 타입으로
떨어지는지까지 테스트가 못 박았다(기존 `apiExceptionOf` 가 `code` 를 먼저 본다).

### 3.2 패키지·StoreKit 2·Play Billing 8+

```
$ flutter pub add in_app_purchase    # → ^3.3.1 (in_app_purchase_android 0.5.0, _storekit 0.4.13)
$ grep -n billing ~/.pub-cache/hosted/pub.dev/in_app_purchase_android-0.5.0/android/build.gradle.kts
79:    implementation("com.android.billingclient:billing:8.0.0")
```

**Billing 8+ 는 충족**이다(플러그인이 8.0.0 을 가져온다). 다만 **앱이 버전을 직접
선언하지 않으므로** release merged manifest 로 다시 확인하는 절차를
`docs/RELEASE.md "### 32."` 에 적었다 — 이 머신에서 `flutter build appbundle
--release` 는 돌리지 않았다(디스크 여유 수 GB, Android 릴리스 빌드 산출물이 그걸
넘긴다). **이건 건너뛴 항목이고 숨기지 않는다**: 티켓이 요구한 것은 "확인 절차를
RELEASE.md 자기 절에" 이고 그건 했다.

StoreKit 2 는 `in_app_purchase_storekit` 0.4.13 에서 **기본값**이고
`enableStoreKit2()` 는 그래서 deprecated 다(`_useStoreKit2 = true` 만 세우는
no-op). 그래서 호출을 넣는 대신 기본값이 바뀌면 깨지는 테스트를 뒀다 —
`test/config/bootstrap_test.dart` "iOS 는 StoreKit 2 로 돈다". StoreKit 1 로
떨어지면 `serverVerificationData` 가 JWS 가 아니라 base64 수신확인서가 되어 서버
검증(`app/clients/app_store.py` 가 JWS 를 기대한다)이 전부 실패한다.

### 3.3 구매 흐름 — 순서와 재전송

| 확인한 것 | 테스트 |
|---|---|
| 성공 응답 **뒤에야** `completePurchase` | "구매 → 서버 검증 성공 → 그때서야 completePurchase" / "검증이 떠 있는 동안은 verifying"(게이트를 열기 전 `completed` 가 비어 있다) |
| pending 은 대기 — verify 를 올리지 않는다 | "스토어가 결제를 붙잡고 있으면 pending" |
| 검증 실패 시 **완료하지 않는다** → 다음 시작 재전송 | "검증 실패(스토어 장애)면 완료하지 않고 사유를 남긴다" / "영수증을 인정하지 않으면 그 사유를 보여준다" |
| 시작 때 상품 조회 + 스토어 동기화(미완료 구매 재전송 경로) | "시작하면 상품 가격을 읽고 스토어와 동기화한다" |
| 복원·복귀로 같은 거래가 다시 와도 verify 는 한 번 | "같은 거래가 여러 번 올라와도 검증은 한 번만 뜬다" |
| `restored` 도 같은 길 | "복원된 구매도 같은 길로 검증·완료된다" |
| 우리 상품·아는 스토어가 아니면 올리지 않는다 | "우리 상품이 아닌 거래는 올리지 않는다" / "어느 스토어 영수증인지 모르면 올리지 않는다" |
| 계정 경계(29 의 세대 장치) | "검증 중 계정이 바뀌면 권한도 완료도 건너뛴다 (D-29-5 와 같은 경계)" |
| 취소는 실패가 아니다 | "사용자가 결제 창을 닫은 것은 실패가 아니다" |

포그라운드 복귀 동기화는 `AppLifecycleListener`(29·30 과 같은 자리)로 걸었다.
구매 흐름 자체는 **앱 수명**에 매달려 있다(`app.dart` 의 `ref.listen`) — 지난 실행에서
끊긴 거래는 첫 프레임 직후 스트림으로 올라오므로, Paywall 을 열 때 듣기 시작하면
놓친다. `purchase_entitlement_test.dart` 가 **홈 탭만 띄운 상태에서** 구매를 올려
그 사실을 증명한다(구독 카드를 한 번도 열지 않았다).

### 3.4 UI 판정 순수 함수

입력 셋(스토어 구매 상태 · 검증 중 여부 · 권한) → `idle/pending/verifying/active/
grace/error`. 순서는 **돌고 있는 일 → 서버가 말한 권한 → 실패** 다. 테스트가 못 박은
경계 3개:

- `verifying` 이 `pending` 보다 먼저(둘 다 "결제 확인 중" 이지만 버튼 잠금이 끊기면 안 된다)
- 권한이 실패보다 먼저 — 이미 구독 중인 사람의 두 번째 구매 실패가 광고 없는 화면에 "실패" 를 띄우면 모순이다
- `status == grace` 지만 `active == false`(유예 종료)는 **미구독**이다. `hold` 도 같다

### 3.5 S5 Paywall

제목·부제 · 혜택 3줄 · 가격 카드 · `FilledButton`(= OVERRIDES `primary-button` 토큰,
테마가 입힌다) · 텍스트 버튼 "구매 복원" · 하단 약관·방침 링크.

자동 갱신 고지 **필수 요소 6개**는 키로 하나씩 고정했다(문구를 다듬다 한 줄이 사라지면
심사에서 걸린다): `productName`(상품명) · `period`(기간·결제 주기) · `price`(가격,
`ProductDetails.price`) · `autoRenew`(자동 갱신 조건) · `cancelHow`(해지 방법) ·
`legalLinks`(약관·방침). 문구는 `docs/legal-checklist.md` "4. 스토어 정책(구독 고지)"
행이 가리키는 웹 약관 `terms#subscription` 과 같은 말을 쓴다 — ko 는 "24시간 전까지",
"설정 > Apple 계정 > 구독", "Google Play > 구독", en 은 "automatically renews",
"24 hours", "Google Play > Subscriptions". 테스트가 양쪽을 문자열로 확인한다.

분석 이벤트는 **진입 시 `paywall_view`, "구독 시작" 탭 시 `subscribe_start`** 하나씩.
`NoopAnalyticsService.logged` 로 이름과 순서까지 본다(미정 20 이 확정한 이름 표는
티켓 26 의 `analytics_event.dart` 한 곳이고 이 티켓은 그 상수를 쓴다).

폭 744 는 `showAdaptiveSheet`(티켓 24)가 가운데 다이얼로그로 바꾼다 — `Dialog` 1개 ·
`BottomSheet` 0개 · 내용 폭 ≤ 560 을 테스트가 확인한다.

### 3.6 S4 구독 카드

| 얼굴 | 보이는 것 | 테스트 |
|---|---|---|
| 미구독 | "광고 없이 플레이 · 월 ₩1,500" → 누르면 Paywall | "미구독: 스토어 현지화 가격을 보여주고 누르면 Paywall 이 열린다" |
| 가격 미확인 | "광고 없이 플레이"(금액 없음) | "가격을 못 읽었으면 금액 없이 안내만 한다" |
| 구독 중 | "광고 제거 · 2026. 10. 31. 갱신" + "관리" | "구독 중: …"(Apple → `apps.apple.com/account/subscriptions`) |
| 유예 중 | "결제 확인 중 · 유예 2026. 10. 20. 까지" + "관리" | "유예 중: …"(Google → `play.google.com/store/account/subscriptions`) |
| 보류(hold) | 미구독 얼굴 | "보류(hold)는 권한이 없어 미구독 얼굴이다" |

"관리" 가 여는 주소는 **기기 플랫폼이 아니라 `entitlement.source`** 로 고른다 —
복원으로 다른 스토어 구독을 이어받은 경우에 엉뚱한 앱이 열리지 않게.

## 4. `audit.native` 체크리스트 (impeccable `reference/audit.native.md`)

브라우저 도구·`impeccable detect` 는 쓰지 않는다(HTML/CSS 용). 22·24~28·31 과 같이
소스를 `reference/ios.md`·`android.md` 기준으로 읽고 5축에 점수를 매겼다. 폭 확인은
눈이 아니라 위젯 테스트(390·744)와 골든 4장이다.

| # | 축 | 31 | 32 | 핵심 소견 |
|---|---|---|---|---|
| 1 | Accessibility | 4 | 4 | Paywall 제목·확인 화면 제목은 `Semantics(header: true)`, 혜택 줄의 체크 아이콘은 `ExcludeSemantics`(문구가 혜택을 다 말한다). 버튼 비활성은 색이 아니라 **레이블이 "결제 확인 중" 으로 바뀌어** 같이 알린다. 실패 사유는 토스트가 아니라 버튼 아래 인라인 한 줄(OVERRIDES §7) — 테스트가 `SnackBar` 0개까지 확인한다. S4 카드는 `SettingsRow`(최소 높이 44) 또는 같은 `minHeight` 를 쓴 2줄 행이고, "관리" 는 테마 `TextButton`(최소 44) |
| 2 | Performance | 3 | 4 | 구매 스트림 구독은 앱 수명당 **하나**(`PurchaseFlowNotifier.build`), 같은 영수증의 verify 는 in-flight 집합으로 하나만 띄운다. UI 판정은 순수 함수 + `Provider` 라 입력 셋이 안 바뀌면 다시 계산되지 않는다. 상품 조회는 시작 1회 + 가격이 비었을 때 Paywall 진입 시 1회 |
| 3 | Appearance & Theming | 4 | 4 | 새 UI 는 전부 토큰이다 — `FilledButton`/`TextButton`(primary-button·foreground), 가격 카드 테두리 `colors.brand`, 보조 문구 `mutedForeground`, 실패 `destructive`. raw hex 는 여전히 `app_colors.dart` 한 파일뿐(새 파일에 0건) |
| 4 | Platform Conformance | 3 | 4 | 결제 창·복원은 SDK 가 네이티브로 띄운다. iOS 는 StoreKit 2(테스트로 고정), Android 는 Billing 8.0.0. **자동 갱신 고지 6요소 + 약관·방침 링크**(Apple 3.1.2(a) 필수)를 Paywall 안에 두고, "관리" 는 각 스토어의 표준 구독 관리 URL 로 보낸다. 서버 검증 성공 뒤에만 finish/acknowledge — Play 의 3일 규칙을 거스르지 않는다 |
| 5 | Adaptivity | 4 | 4 | Paywall 은 `showAdaptiveSheet` 하나로 compact 바텀시트 / medium+ 가운데 다이얼로그(최대 560)다. 시트 높이는 화면의 90% 로 묶고 안쪽을 스크롤한다(고지가 길어 폰에서 링크가 화면 밖으로 나가던 것을 고쳤다). 긴 영문 링크 라벨은 `Wrap` 으로 접힌다. S4 카드의 구독 중 얼굴은 2줄 — 폰 폭에서 "광고 제거 · 날짜 갱신" 과 "관리" 가 한 줄에 안 들어간다 |
| **합계** | | **18/20** | **20/20** | **Excellent** |

**추가 항목 "태블릿 폭 포함": 통과.** 744 는 `paywall_sheet_test.dart` 의 다이얼로그
테스트가, 1024(T4 2열에서 구독 카드가 왼쪽 열) 는 27 의
`ranking_records_tablet_test.dart` 와 갱신한 골든 `records_tablet_1024.png` 가 덮는다.
390 은 S4·Paywall 테스트 전부.

## 5. 목업 대비 기록

골든(`mobile/test/golden/`, 갱신은 `flutter test test/golden --update-goldens`):

- **새로 3장** — `paywall_light_390.png` · `paywall_dark_390.png` ·
  `paywall_tablet_744.png`(`paywall_golden_test.dart`). 결과 시트(26)와 같은 방식으로
  목업 `e5_paywall.html` 과 눈으로 대조한다. 744 장은 가운데 다이얼로그(T2)다.
- **갱신 4장** — `records_light_390.png` · `records_linked_390.png` ·
  `records_notification_off_390.png` · `records_tablet_1024.png`. 넷 다 **구독 자리의
  "준비 중" 이 실제 카드로 바뀐 것**이 유일한 차이다.

목업과 **다르게 구현한 것 3건**:

1. **혜택 가운데 줄**: 목업 `e5_paywall` 은 "힌트 미리 보기 무제한", 구현은 **"광고 없이
   힌트 미리 보기"**. 스펙 §B.21 과 티켓이 이 문구를 못 박았고, "무제한" 은 사실과
   다르다 — 힌트는 **퍼즐당 한 번**이고 구독자도 같다(README "06. 힌트 미리 보기
   공정성"). 스펙·티켓을 따랐다.
2. **S4 구독 카드 모양**: 목업 `e4_records` 는 2줄 텍스트 + 오른쪽 "구독" 외곽선 버튼,
   구현은 미구독일 때 **설정 행 1줄**("구독" + "광고 없이 플레이 · 월 ₩1,500" + 화살표)
   이다. SCREENS S4 의 문구 규격("미구독 → …월 {스토어 현지화 가격} → Paywall")은
   그대로 지키면서, 같은 열의 계정·백업 코드·설정 행(티켓 27·29·30)과 같은
   `SettingsRow` 를 써서 열이 들쭉날쭉하지 않게 했다. 구독 중·유예 중은 "관리" 버튼이
   붙어 목업처럼 2줄이 된다.
3. **Paywall 상단 닫기·streak**: 목업에는 헤더에 불꽃 배지와 닫기 버튼이 있다. 구현은
   바텀시트/다이얼로그라 **닫기는 시트 제스처·바리어**가 하고(결과 시트·백업 코드
   시트와 같은 규칙, SCREENS T2), streak 배지는 Paywall 의 일이 아니라 넣지 않았다.

그 밖(제목·부제·혜택 3줄 체크·테두리 있는 가격 카드·`primary-button` "구독 시작"·
텍스트 버튼 "구매 복원"·하단 약관·방침 링크)은 목업과 같다. 가격 카드에 **자동 갱신
고지 4줄이 더 들어간 것**은 목업의 "자동 갱신 · 언제든 해지" 한 줄로는 16 의 체크리스트
필수 요소를 못 채우기 때문이다(심사 사유).

## 6. 명령과 출력

Flutter(`mobile/`):

```
$ flutter analyze
Analyzing mobile...
No issues found! (ran in 2.9s)

$ dart format lib test
(변경 없음 — 이미 포맷된 상태)

$ flutter test
+733: All tests passed!

$ flutter test test/golden --update-goldens
+20: All tests passed!        # Paywall 3장 추가 · records 4장 갱신(§5)

# 이 티켓이 더한 것만
$ flutter test test/subscription/subscription_state_test.dart      -> +15
$ flutter test test/subscription/purchase_controller_test.dart     -> +15
$ flutter test test/subscription/paywall_sheet_test.dart           -> +12
$ flutter test test/subscription/purchase_entitlement_test.dart    -> +1
$ flutter test test/screens/records_subscription_test.dart         -> +6
$ flutter test test/golden/paywall_golden_test.dart                -> +3
# + test/api(Entitlement 3 · verify 3) + test/config/bootstrap_test(StoreKit 2 1) = 60
```

백엔드(레포 루트, 전용 자원 — DB `chosung_daily_test_t32`, Redis DB 6,
마이그레이션 DB `chosung_daily_test_t32_migrations`):

```
$ uv run ruff check .
All checks passed!

$ TEST_DATABASE_URL=...chosung_daily_test_t32 \
  TEST_REDIS_URL=redis://localhost:6379/6 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t32_migrations \
  uv run pytest -q
1509 passed in 1239.21s (0:20:39)
```

마이그레이션은 만들지 않았으므로 `flask db heads` 는 선행 머지 상태 그대로다
(`migrations/` 변경 0건).

## 7. 알려진 한계 · 넘긴 것

- **Android release merged manifest 확인은 못 돌렸다**(디스크). 절차와 현재 실측값
  (`billing:8.0.0`)은 `docs/RELEASE.md "### 32."` 에 있고, 플러그인을 올릴 때마다
  다시 확인하라고 적었다.
- **실기기·Sandbox 확인은 사람 몫**이다(결제는 시뮬레이터에서 안 돈다) —
  `docs/RELEASE.md "### 32."` 의 체크리스트 6개.
- **"복원할 구독이 없다" 는 따로 안내하지 않는다.** iOS StoreKit 2 는 복원 거래를
  `restorePurchases()` 가 끝난 뒤 한참 늦게 올려줄 수 있어서 "없다" 를 단정할 수
  없다 — 단정했다가 뒤늦게 권한이 들어오면 거짓 안내가 된다. 복원을 누르면 "복원 중…"
  이 돌고, 찾으면 확인 화면으로 바뀌고, 못 찾으면 원래 화면으로 돌아온다.
- **`RECEIPT_INVALID` 도 구매를 완료하지 않는다.** 스펙 §A.8 "성공 응답 후에만
  완료" 를 그대로 지켰고, 그 결과 Play 는 3일 뒤 자동 환불한다 — 서버가 인정하지
  못한 영수증이면 그게 맞는 결말이라고 봤다(README "### 32."). 사용자에게는 스토어
  고객센터 안내 문구를 띄운다.
- 티켓 33(권한 재조회·`next_check_at` 타이머)은 이 티켓 범위가 아니다. `Entitlement`
  에 `nextCheckAt` 자리는 만들어 뒀고 `/me/stats` 파싱은 33 이 더한다.

---

## 수정 라운드 1

`review/impl-review-32.md` 라운드 1(판정 FAIL, MAJOR 2 · MINOR 2). 코디네이터
메모대로 MINOR 2건도 같이 고쳤다. 결함 ID 별로 (원인 / 수정 / 증명).

### D-32-1 (MAJOR) 시작 동기화가 토큰 복원 전에 verify 를 보내 401 로 끝나고 재전송이 없다

**원인** — 두 가지가 겹친 하나의 구멍이다.

1. `PurchaseFlowNotifier.build()` 가 첫 빌드에서 바로 `_bootstrap()` →
   `loadProduct()` → `sync()`(= `restorePurchases`) 를 돌렸다. 같은 시점에
   `guestTokenProvider` 는 secure storage 를 읽는 중이거나(`AsyncLoading`)
   `StartupNotifier._ensureGuestToken` 이 `POST /guests` 를 기다리는 중이다.
   `DioApiClient._bearer` 는 토큰이 비면 **서버에 가기 전에**
   `UnauthorizedApiException` 을 던진다(`dio_api_client.dart:219`).
2. `_verifyThenComplete` 는 그 예외를 `on ApiException` 으로 받아
   `_fail(epoch, 'subscription.error_failed')` 를 불렀다. 보낸 적도 없는 요청이
   "결제를 끝내지 못했어요" 가 됐고, 구매 흐름은 `guestTokenProvider` 를 듣지
   않으므로 토큰이 도착해도 다음 포그라운드 복귀까지 재전송이 없었다.

**수정** — `mobile/lib/subscription/purchase_controller.dart`

- `_bootstrap()` 이 `await ref.read(guestTokenProvider.future)` 로 토큰을 기다린
  뒤에 동기화한다. 읽기가 실패해도(플랫폼 채널 없음 등) 구매 흐름은 떠 있어야
  하므로 `on Exception` 으로 받고 넘어간다 — 값이 뒤늦게 들어오면 아래 `listen`
  이 받는다.
- `build()` 에 `ref.listen(guestTokenProvider, …)` 를 걸어 **토큰이 바뀌는
  자리**(재설치 발급 · 401 복구 · 계정 전환)에서 다시 맞춘다. 알림 동기화
  (`notification_controller.dart:59`)와 같은 모양이다.
- `_syncedToken` 으로 같은 토큰에 두 번 돌지 않게 막는다. 복귀 동기화는
  `AppLifecycleListener` 쪽 그대로다.
- `on UnauthorizedApiException` 을 `on ApiException` **앞**에 따로 두고 아무
  것도 하지 않는다 — "실패" 가 아니라 "아직 못 보냄" 이라, 문구를 띄우지 않고
  거래도 완료하지 않는다. 다음 동기화가 같은 영수증을 다시 올린다.

**증명** — 리뷰의 재현을 테스트로 고정했다
(`mobile/test/subscription/purchase_controller_test.dart`). 토큰 저장소를
`InMemoryGuestTokenStore(null)` 로 덮어 "토큰이 아직 없는 실행" 을 만든다.

수정 전(RED, 실제 출력):

```
00:05 +16 -1: 게스트 토큰이 아직 없으면 시작 동기화를 미루고, 토큰이 오면 그때 맞춘다 [E]
  Expected: <0>
    Actual: <1>                       # store.restoreCalls — 토큰 없이 이미 올렸다
  test/subscription/purchase_controller_test.dart 326:5

00:05 +16 -2: 토큰 없이 올라온 거래는 실패가 아니라 보류다 — 토큰이 오면 다시 올린다 [E]
  Expected: null
    Actual: 'subscription.error_failed'   # 리뷰가 적은 바로 그 문구
  test/subscription/purchase_controller_test.dart 355:5
```

수정 후(GREEN):

```
$ cd mobile && flutter test test/subscription/purchase_controller_test.dart
00:02 +24: All tests passed!
```

추가한 테스트 4개:

| 테스트 | 무엇을 못 박는가 |
|---|---|
| 게스트 토큰이 아직 없으면 시작 동기화를 미루고, 토큰이 오면 그때 맞춘다 | 토큰 전 `restoreCalls == 0`·`verifiedReceipts` 비어 있음·오류 없음 → `replaceWith` 뒤 `restoreCalls == 1`·verify 1건·`entitlement.active` |
| 토큰 없이 올라온 거래는 실패가 아니라 보류다 — 토큰이 오면 다시 올린다 | 401 에 문구 없음·`phase == idle`·`completed` 비어 있음 → 토큰 도착 뒤 권한 들어오고 `completePurchase` 한 번 |
| secure storage 읽기가 늦게 끝나도 그 뒤에 verify 를 올린다 (지연 Fake) | 코디네이터 메모 2 — 읽기가 Completer 로 막힌 저장소(`_SlowGuestTokenStore`). 막힌 동안 `restoreCalls == 0`, 풀면 verify 1건·권한 들어옴·`accountEpoch == 0`(29 의 세대 경계 그대로) |
| 토큰이 그대로면 복귀 전까지 시작 동기화를 두 번 돌리지 않는다 | `_syncedToken` 중복 억제 |

지연 Fake 테스트는 `_bootstrap` 을 원래대로(`loadProduct` → 바로 `sync`)
돌려놓으면 RED 다(실제 출력):

```
00:01 +0 -1: secure storage 읽기가 늦게 끝나도 그 뒤에 verify 를 올린다 (지연 Fake) [E]
  Expected: <0>
    Actual: <1>      # 토큰을 읽는 중인데 이미 restorePurchases 가 나갔다
```

### D-32-2 (MAJOR) `flutter analyze` exit 1 — CI "Analyze" 가 깨져 있다

**원인** — `test/subscription/purchase_controller_test.dart:284` 에서 같은
수신자(`store`)에 대한 두 문장이 캐스케이드로 묶이지 않아
`cascade_invocations`(very_good_analysis) info 가 떴다.
`.github/workflows/flutter-ci.yml:48` 의 `flutter analyze` 는 info 도 fatal 이라
exit 1 이었다.

**수정** — 두 줄을 캐스케이드로 합쳤다.

```dart
store
  ..completeError = Exception('platform channel down')
  ..emit([fakePurchase()]);
```

**증명** — 수정 전:

```
$ cd mobile && flutter analyze
   info • Unnecessary duplication of receiver • test/subscription/purchase_controller_test.dart:284:5 • cascade_invocations
1 issue found. (ran in 2.4s)
```

수정 후(새로 쓴 테스트 7개까지 포함해서):

```
$ cd mobile && flutter analyze
No issues found! (ran in 3.1s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 192 files (0 changed) in 0.29 seconds.      # exit 0
```

### D-32-3 (MINOR) S5 가격 카드가 "월 {가격}" 이 아니라 "{가격}"

**원인** — `paywall_sheet.dart` 의 `_PriceCard` 가 `product?.price` 를 그대로
그렸다. S4 카드는 `subscription.card_idle`("광고 없이 플레이 · 월 {price}")로
기간을 붙이는데 S5 만 빠졌다. `design/SCREENS.md` S5 는 "월 {스토어 현지화
가격}", 목업 `e5_paywall` 도 "월 ₩1,500" 이다.

**수정** — 번역 키 `subscription.price_monthly` 를 더했다
(ko `"월 {price}"`, en `"{price} / month"` — S4 카드와 같은 어순). 가격을 아직
모르면 `price_loading` 그대로다. **가격 문자열 자체는 여전히
`ProductDetails.price`** 로, 상수 ₩1,500 은 넣지 않았다.

**증명** — `test/subscription/paywall_sheet_test.dart` 의 S5 구성 테스트가
`find.text('₩1,500')` → `find.text('월 ₩1,500')` 으로 바뀌었고, 영어 테스트에
`find.text('₩1,500 / month')` 를 더했다. 골든 3장을 다시 떴다.

```
$ cd mobile && flutter test test/golden/paywall_golden_test.dart     # 수정 전
Golden "paywall_light_390.png":  Pixel test failed, 0.33%, 1102px diff detected.
Golden "paywall_dark_390.png":   Pixel test failed, 0.33%, 1102px diff detected.
Golden "paywall_tablet_744.png": Pixel test failed, 0.14%, 1102px diff detected.

$ cd mobile && flutter test test/golden --update-goldens
00:04 +20: All tests passed!
```

새 골든 `paywall_light_390.png` 의 가격 줄은 "월 ₩1,500" 이고 목업 `e5_paywall`
과 같다. 차이는 그 한 줄뿐이다(1102px = 가격 텍스트 영역).

### D-32-4 (MINOR) Play pending 이 스토어 쪽에서 포기되면 세션 내내 잠긴다

**원인** — `PurchaseFlow.purchase` 가 **스트림 이벤트로만** 바뀌었다. Play 의
pending(계좌이체·편의점 결제)을 사용자가 포기하면 스토어는 아무 이벤트도 주지
않고 다음 `queryPurchases` 에서 그 거래를 빼기만 한다. 그래서 `pending` 이
눌러앉아 `busy` 가 계속 true 였고(`purchase_controller.dart:55`), Paywall 의 두
버튼과 S4 카드가 앱을 완전히 다시 켤 때까지 "결제 확인 중" 이었다.

**수정** — 조회가 유일한 신호이므로 **조회 결과로 내린다**.

- `sync()` 가 `_pendingSeenSinceSync` 를 내리고 조회한 뒤, 한 틱 양보해
  (브로드캐스트 스트림이 그때 도착한다) `_dropAbandonedPending()` 을 부른다.
- 조회 **자체가 실패**하면(`on Exception`) 바로 `return` 한다 — 못 물어본 것을
  "없다" 로 읽으면 멀쩡한 pending 을 내린다.
- `PurchaseFlow.copyWith` 에 `clearPurchase` 를 더했다(`purchase` 를 null 로
  되돌리는 길이 없었다).
- 조회가 겹치면(복귀 연타) `_syncSeq` 로 **마지막 조회만** 판정한다 — 앞선
  조회가 뒤엣것이 초기화한 플래그를 보고 멀쩡한 pending 을 내리는 길을 막는다.
- **iOS 는 내리지 않는다.** pending 거래의 `verificationData.source` 를
  `_pendingStore` 에 적어 두고 `google_play` 일 때만 내린다. StoreKit 2 의
  복원은 `currentEntitlements`(이미 권한이 생긴 거래)만 올리므로 승인 대기
  (Ask to Buy)가 조회에 **없는 것이 정상**이고, 내렸다가는 승인을 기다리는
  사람의 버튼이 다시 살아난다. Play 의 `queryPurchases` 만 pending 을 포함한
  전수 조회다.

**증명** — 테스트 4개를 더했다. 수정(= `_dropAbandonedPending()` 호출)을 빼고
돌리면 RED 다(실제 출력):

```
00:01 +19 -1: Play 조회에서 사라진 pending 은 내린다 — 세션 내내 잠기지 않는다 [E]
00:01 +22 -1: Some tests failed.
```

| 테스트 | 무엇을 못 박는가 |
|---|---|
| Play 조회에서 사라진 pending 은 내린다 — 세션 내내 잠기지 않는다 | 포기 뒤 `phase == idle`·`busy == false` |
| 조회에 pending 이 그대로 있으면 내리지 않는다 | 살아 있는 pending 을 잘못 내리지 않는다 |
| App Store 승인 대기는 복원 조회에 없어도 내리지 않는다 | SK2 `currentEntitlements` 의미 차이 |
| 조회 자체가 실패하면 pending 을 내리지 않는다 | 조회 실패 ≠ 거래 없음 |

### 리뷰어 지적 중 고치지 않은 것

없다. BLOCKER 0 · MAJOR 2 · MINOR 2 를 모두 고쳤고, §4 "참고" 5건은 결함이
아니라는 리뷰어 판단에 동의해 그대로 뒀다. `entitlement_provider.dart` ·
`api_models.dart` 의 32 설계(`Entitlement?` 상위집합)는 코디네이터 지시대로
유지했다 — 33 이 머지 뒤 그 위로 통합한다.

### 문서

`README.md` "### 32." 설계 판단에 두 단락을 더했다: ① 영수증은 게스트 토큰이
생긴 뒤에 올린다(D-32-1 의 근거와 `ref.listen` 선택), ② 스토어가 붙잡은
pending 은 스토어마다 다르게 푼다(D-32-4 의 Play/iOS 비대칭). 다른 절은
건드리지 않았다.

`docs/RELEASE.md` "### 32." 의 **실기기·Sandbox 체크리스트에 2줄**을 더했다:
재설치 첫 실행에서 "구매 복원" 을 누르지 않아도 권한이 돌아오는지(D-32-1),
Play pending 포기 뒤 복귀하면 버튼이 살아나는지 / iOS 승인 대기는 반대로
그대로인지(D-32-4). 둘 다 코드로는 못 돌리는 사람 확인이다.

### 재실행 결과

```
$ cd mobile && flutter analyze
No issues found! (ran in 2.4s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 192 files (0 changed) in 0.26 seconds.

$ cd mobile && flutter test
00:36 +741: All tests passed!          # 733 → 741 (D-32-1 4건 · D-32-4 4건)

$ uv run ruff check .
All checks passed!
```

백엔드(전용 자원 — DB `chosung_daily_test_t32`, Redis DB 6, 마이그레이션 DB
`chosung_daily_test_t32_migrations`; 접속 값은 기록하지 않는다):

```
$ TEST_DATABASE_URL=...chosung_daily_test_t32 \
  TEST_REDIS_URL=redis://localhost:6379/6 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t32_migrations \
  uv run pytest -q
1509 passed in 740.85s (0:12:20)
```

`migrations/` 변경 0건이라 `flask db heads` 는 선행 머지 상태 그대로다
(`git diff --stat main...HEAD -- migrations` 비어 있음). 이번 라운드도 백엔드
(`app/`·`tests/`)·웹·스펙은 건드리지 않았다. 로컬 `main`(`4afda89`) 바로 위에
올라가 있어 rebase 로 옮길 커밋이 없었다.

## 수정 라운드 2

최종 리뷰 라운드 2(Fable, 판정 FAIL)의 **MAJOR 1건(D-32-5)** 을 고쳤다. MINOR·
BLOCKER·REPEAT 는 없었고, "참고 1"(RELEASE 체크리스트 줄이 D-32-5 상태에선
판별이 안 된다)은 D-32-5 수정의 일부라 같이 고쳤다. 리뷰의 지적은 플러그인·
서버 소스를 직접 확인한 결과 **전부 맞았다** — 반박한 항목은 없다.

### D-32-5 (MAJOR) Play 의 pending 거래가 조회에서 `restored` 로 올라와 대기가 풀리고 acknowledge 까지 나갔다

**원인 (둘)**

1. `_onPurchases` 가 `PurchaseDetails.status` 만 보고 분기했다. 그런데
   `in_app_purchase_android` 0.5.0 의 조회는 결과 **전부**에 `restored` 를
   덮어쓴다 — 직접 확인한 소스(`~/.pub-cache/.../in_app_purchase_android-0.5.0`):

   ```dart
   // lib/src/in_app_purchase_android_platform.dart:255-266  restorePurchases()
   final List<PurchaseDetails> pastPurchases = responses
       .expand((PurchasesResultWrapper response) => response.purchasesList)
       .expand((PurchaseWrapper w) => GooglePlayPurchaseDetails.fromPurchase(w))
       .map((GooglePlayPurchaseDetails details) =>
               details..status = PurchaseStatus.restored)   // ← pending 도 예외 아님
       .toList();
   ```

   `fromPurchase` 가 `purchaseStatusFromWrapper(purchase.purchaseState)` 로
   일단 `pending` 을 만들고(`lib/src/pigeon_converters.dart:247-253`) 위 `map`
   이 그 위에 `restored` 를 씌운다. Play 쪽 원본 상태가 남는 곳은
   `billingClientPurchase.purchaseState` 하나뿐이다. 그래서 편의점·계좌이체
   결제(몇 시간) 중에 앱을 한 번 내렸다 올리면 `sync()` 의 조회가 같은 거래를
   `restored` 로 올려 `_verifyThenComplete` 로 들어갔다.
2. verify 가 **행을 만들지 못한 200 응답**에도 완료를 불렀다. 서버는 결제가
   끝나지 않은 Play 구매에 행을 만들지 않고(`app/services/subscription_service.py:88-95`
   `_verify_google` → `normalized.status is None` → `return None`), 그대로
   `build_entitlement(find_by_guest(...))` 를 돌려주므로 **200 + `active:false`
   + `status:null`** 이다(`app/services/subscription_service.py:46-51`,
   `app/services/entitlement.py:89-90` `NO_ENTITLEMENT`). 컨트롤러는
   `entitlement == null`(계정 전환)만 걸렀기 때문에, 권한을 받지 못한 응답에도
   `pendingCompletePurchase`(= `!isAcknowledged`, pending 거래는 true)만 보고
   `acknowledgePurchase(결제 전 토큰)` 을 냈다. 규칙 1("서버가 권한을 돌려준
   뒤에만 완료")이 코드에서 느슨했던 자리다.

**재현을 먼저 테스트로 고정했다 (tdd)**

테스트가 이 결함을 못 본 이유가 입력이었다 — `fakePurchase` 가 밋밋한
`PurchaseDetails` 를 만들고 `FakePurchaseService.restore()` 가 `restorable` 을
**그대로** 올려서, 실기기에는 없는 "조회 결과에 `status == pending`" 이라는
모양을 가정하고 있었다. 먼저 Fake 를 플러그인과 같은 모양으로 바꿨다
(`test/fakes/fake_purchase_service.dart`):

- `source: 'google_play'` 는 플러그인이 올리는 것과 **같은 타입**
  `GooglePlayPurchaseDetails` 로 만든다 — `purchaseState` 가 Play 쪽 원본
  상태, `status` 가 플러그인이 스트림에 얹는 값이다.
- `restore()` 는 플러그인처럼 Play 거래 전부에 `restored` 를 씌워 올린다
  (`_asQueried`). iOS 는 `currentEntitlements` 만 올리므로 그대로 둔다.

그 입력으로 컨트롤러를 고치기 **전에** 돌린 출력(= 리뷰의 재현을 재현한 것):

```
$ cd mobile && flutter test test/subscription/purchase_controller_test.dart
00:01 +20 -2: 조회에 pending 이 그대로 있으면 내리지 않는다 [E]
  Expected: SubscriptionPhase:<SubscriptionPhase.pending>
    Actual: SubscriptionPhase:<SubscriptionPhase.active>

00:01 +20 -3: 구매 대기 중 복귀해도 "결제 확인 중" 이다 — 조회의 restored 에 속지 않는다 [E]
  Expected: SubscriptionPhase:<SubscriptionPhase.pending>
    Actual: SubscriptionPhase:<SubscriptionPhase.idle>

00:01 +21 -4: 서버가 구독 행을 만들지 못한 응답에는 completePurchase 를 부르지 않는다 [E]
  Expected: empty
    Actual: [Instance of 'GooglePlayPurchaseDetails']

00:01 +23 -4: Some tests failed.
```

라운드 1 에 넣은 "조회에 pending 이 그대로 있으면 내리지 않는다" 가 **진짜
입력으로는 실패한다** — 리뷰가 "플러그인이 만들지 않는 입력으로만 통과했다" 고
한 그대로다. `active` 로 끝난 것은 조회로 올라온 pending 거래를 verify 로 올려
Fake 의 기본 응답(권한 있음)을 받았기 때문이다.

**수정 내용**

- `mobile/lib/subscription/purchase_controller.dart` — `_statusOf(purchase)` 를
  더해 `_onPurchases` 가 그 값으로 분기한다. `purchased`·`restored` 로 올라온
  Play 거래는 `billingClientPurchase.purchaseState == PurchaseStateWrapper.pending`
  이면 pending 으로 다룬다(그러면 `_pendingSeenSinceSync` 도 그때 올라가
  D-32-4 의 "그대로 있으면 내리지 않는다" 가 실제로 성립한다).
  `canceled`·`error` 는 스토어가 뜻을 담아 덮은 값이라 건드리지 않는다 —
  사용자가 창을 닫은 거래를 pending 으로 되돌리면 버튼이 잠긴다.
- 같은 파일 — `entitlement.status != null` 일 때만 `_service.complete()` 를
  부른다. 행이 없는 응답은 권한을 돌려준 것이 아니다. 권한 자체는 서버가 말한
  대로 `entitlementProvider` 에 반영한다(완료만 하지 않는다).
- `mobile/pubspec.yaml` — `in_app_purchase_android: ^0.5.0` 을 직접 의존성으로
  올렸다(`in_app_purchase` 의 전이 의존성이라 받는 버전은 그대로고,
  `depend_on_referenced_packages` 를 지키려면 선언이 필요하다). 옆줄
  `in_app_purchase_storekit` 과 같은 이유·같은 모양이다.
- `docs/RELEASE.md` "### 32." — 리뷰 §5 참고 1 대로 사람 확인 줄을 **셋**으로
  나눴다: ① 결제를 끝내지 않은 채 복귀하면 계속 "결제 확인 중"(D-32-5)
  ② 이어서 포기한 뒤 복귀하면 버튼이 살아남(D-32-4) ③ iOS 승인 대기는 복귀해도
  그대로. 순서를 못 박아야 "유지" 와 "풀림" 이 구분된다.

**증명하는 테스트**

새 테스트 3건(`mobile/test/subscription/purchase_controller_test.dart`):

| 테스트 | 보는 것 |
|---|---|
| `구매 대기 중 복귀해도 "결제 확인 중" 이다 — 조회의 restored 에 속지 않는다` | pending → `sync()`(조회가 `restored` 로 올림) 뒤에도 `phase == pending`·`busy`, `verifiedReceipts` 비어 있음, `completed` 0, 오류 null |
| `결제가 끝나면 같은 거래가 purchased 로 올라와 검증·완료된다` | 대기를 유지해도 결제 완료를 놓치지 않는다 — verify 1건·`completed` 1건·`phase == active` |
| `서버가 구독 행을 만들지 못한 응답에는 completePurchase 를 부르지 않는다` | `status == null` 응답에 verify 1건·`completed` 0·권한은 `active:false` 로 반영 |

라운드 1 의 `조회에 pending 이 그대로 있으면 내리지 않는다` 는 손대지 않았고,
이제 **플러그인이 실제로 올리는 입력**으로 통과한다.

```
$ cd mobile && flutter test test/subscription/
00:05 +55: All tests passed!
```

### 재실행 결과 (라운드 2)

```
$ cd mobile && flutter analyze
No issues found! (ran in 2.2s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 192 files (0 changed) in 0.23 seconds.

$ cd mobile && flutter test
00:39 +744: All tests passed!          # 741 → 744 (D-32-5 3건)
```

### Fake ↔ 실제 플러그인 대조표 (코디네이터 요청)

D-32-5 는 "Fake 가 실제와 다른 입력을 만든다" 에서 나왔다. 그래서
`test/fakes/fake_purchase_service.dart` 의 모든 면을 플러그인 소스와 한 줄씩
대조했다 — `in_app_purchase_android` 0.5.0, `in_app_purchase_storekit` 0.4.13
(StoreKit **2**, 스펙 §B.18 · `bootstrap_test` 가 지킨다), 읽은 파일은
`lib/src/in_app_purchase_android_platform.dart`,
`lib/src/types/google_play_purchase_details.dart`,
`lib/src/pigeon_converters.dart`,
`lib/src/billing_client_wrappers/purchase_wrapper.dart`,
`lib/src/in_app_purchase_storekit_platform.dart`,
`lib/src/store_kit_2_wrappers/sk2_transaction_wrapper.dart`,
`lib/src/types/app_store_purchase_details.dart`,
`darwin/.../StoreKit2/InAppPurchasePlugin+StoreKit2.swift`.

| # | 자리 | 실제 플러그인 | 라운드 2 전 Fake | 처리 |
|---|---|---|---|---|
| 1 | 조회가 올리는 `status` | Android: `queryPurchases` 결과 **전부**에 `restored` 를 덮어쓴다(pending 포함, `restorePurchases` 255-266행) | `restorable` 을 그대로 올렸다 → 조회 결과에 `pending` 이 있을 수 있다고 가정 | **고침** — `_asQueried` 가 Play 거래에 `restored` 를 씌운다. D-32-5 의 뿌리 |
| 2 | 거래 객체 타입 | Android 는 `GooglePlayPurchaseDetails`(원본 상태가 `billingClientPurchase.purchaseState` 에 남는다), iOS(SK2)는 `SK2PurchaseDetails`. 두 플랫폼의 `completePurchase` 가 **타입을 assert 한다**(android 208-214행, storekit 221-225행) | 양쪽 다 밋밋한 `PurchaseDetails` → 실기기라면 `complete` 가 assert 로 죽는 입력이었고, Play 원본 상태를 읽을 길이 없었다 | **고침** — `google_play`→`GooglePlayPurchaseDetails`, `app_store`→`SK2PurchaseDetails`, 모르는 출처만 밋밋한 `PurchaseDetails` |
| 3 | `pendingCompletePurchase` | Android: `!billingClientPurchase.isAcknowledged`(pending 거래도 true). iOS(SK2): **`status == purchased` 로 고정된 getter** — 복원·승인 대기 거래는 false | Fake 가 `pendingComplete` 로 아무 값이나 넣을 수 있었다(iOS 복원 거래에 true) | **고침** — Android 는 `isAcknowledged` 로 받고, iOS 는 getter 그대로(인자를 받지 않는다) |
| 4 | `buy()` 실패 | Android: 결제 창을 못 띄워도 **던지지 않고 false**(`launchBillingFlow` non-OK, 179-194행). 그때 `onPurchasesUpdated` 도 안 와서 스트림이 조용하다. iOS(SK2): `SK2Product.purchase` 가 던지고 늘 `true` | `buyError` 로 **던지는 길만** 있었다 → Android 의 false 를 아무도 못 봤다 | **발견 → 고침** (코디네이터 판단, 아래 §"결제 창을 못 띄우는 길") |
| 5 | `complete()` 실패 | Android: non-OK `BillingResult` 를 **값으로** 돌려주고 던지지 않는다. 이미 acknowledge 된 거래는 바로 ok. iOS(SK2): `SK2Transaction.finish` 가 플랫폼 예외를 던질 수 있다 | `completeError` 로 던지는 길만 | **미수정(의도)** — `PurchaseService.complete` 가 `Future<void>` 로 Android 의 결과를 버린다. 앱이 acknowledge 실패를 알 길이 없는 건 플러그인 한계이고, 우리 처리는 "완료하지 않은 채 둔다"(다음 시작의 재전송, Play 는 3일 미acknowledge 자동 환불)로 이미 안전한 쪽이다. 고치려면 서비스 반환형·문구 정책이 바뀌어 범위 밖 |
| 6 | `restore()` 실패 | Android: 조회 응답 중 하나라도 non-OK 면 `InAppPurchaseException` 을 던지고 **스트림에 아무 것도 올리지 않는다**(throw 가 `add` 보다 앞, 268-276행). iOS(SK2): 네이티브가 `sendTransactionUpdates` **먼저** 하고 검증 실패 건이 있으면 그 뒤에 실패를 돌려준다 | `restoreError` 를 `emit` 보다 먼저 던진다 | **일치(Android)** — iOS 의 "일부 올린 뒤 실패" 는 우리 쪽에서 더 보수적으로 끝난다(`sync()` 가 `_pendingSeenSinceSync` 를 내리지 않아 pending 유지). 안전한 방향이라 그대로 |
| 7 | `loadProduct()` 실패 | 양쪽 다 **던지지 않고** `notFoundIDs`·`error` 를 담은 응답을 돌려준다(Android 는 `PlatformException` 을 응답으로 바꿔 담는다, 113-131행) | `product = null` 과 `loadProductError`(던짐) 둘 다 | **일치** — 실제 경로는 `product = null` 쪽이고(`StorePurchaseService` 가 `firstOrNull`), 던지는 길은 채널 예외용 여분이다. 둘 다 "가격을 모른다" 하나로 끝난다 |
| 8 | 구매 스트림 | 양쪽 다 broadcast — 늦게 듣기 시작하면 그 사이 거래를 놓친다. 같은 거래를 복원·복귀마다 다시 올린다 | broadcast `StreamController`, 같은 거래 재방출을 테스트가 직접 한다 | **일치** (`_inFlight` 가 중복 verify 를 막는다 — 테스트 "같은 거래가 여러 번 올라와도…") |
| 9 | `purchaseID` | Android = `purchase.orderId`(Play 는 pending 거래에 주지 않을 수 있다). iOS(SK2) = `id > 0 ? id.toString() : null` 인 **숫자 문자열** | `'tx-1'` 고정, 테스트가 `null` 도 넣는다 | **일치(영향 없음)** — `_inFlight` 키가 `purchaseID ?? receipt` 라 null 이어도 영수증으로 떨어진다. SK2 의 숫자 문자열은 `complete` 쪽 `int.parse` 용이고 우리 코드는 파싱하지 않는다 |
| 10 | iOS 복원 범위 | 네이티브 `restorePurchases` 는 `Transaction.currentEntitlements`(= 이미 권한이 생긴 거래)만 `.restored` 로 올린다(Swift 285-305행) | `restorable` 을 테스트가 직접 정한다 | **일치** — D-32-4 의 "iOS 는 조회에 없어도 pending 을 내리지 않는다" 비대칭이 이 소스로 확인된다 |

### 결제 창을 못 띄우는 길 (대조표 4 — 발견 → 수정)

**원인:** `PurchaseService.buy` 가 `Future<void>` 라 `InAppPurchase.instance
.buyNonConsumable` 의 반환값을 버렸다. Android 는 `launchBillingFlow` 가
non-OK 면 예외가 아니라 `false` 를 돌려주고(`in_app_purchase_android_platform
.dart:179-194` `return billingResultWrapper.responseCode == BillingResponse.ok`)
`onPurchasesUpdated` 도 부르지 않는다. `start()` 는 `on Exception` 만 보고
있었으므로 **"구독 시작" 을 눌러도 아무 문구 없이 아무 일도 일어나지 않는다.**
iOS(SK2)는 반대로 실패를 던지므로 기존 처리가 맞다.

**수정:** `buy` 를 `Future<bool>`("결제 창을 띄웠는가")로 바꾸고, `start()` 가
false 면 `subscription.error_failed`("결제를 끝내지 못했어요")를 띄운다.
`NoopPurchaseService` 는 창을 띄운 적이 없으니 false 다(실제 트리는
`main.dart` 가 덮고 `bootstrap_test` 가 지킨다). Fake 에 `buyLaunched` 를 더해
그 길을 테스트가 만든다.

**증명(고치기 전 → 후):**

```
$ cd mobile && flutter test test/subscription/purchase_controller_test.dart \
    --plain-name '결제 창을 띄우지 못하면'
  Expected: 'subscription.error_failed'
    Actual: <null>
00:03 +0 -1: Some tests failed.          # start() 고치기 전

$ cd mobile && flutter test
00:51 +745: All tests passed!            # 744 → 745
```

### 재실행 결과 (라운드 2 최종)

```
$ cd mobile && flutter analyze
No issues found! (ran in 5.0s)

$ cd mobile && dart format --output=none --set-exit-if-changed lib test
Formatted 192 files (0 changed) in 0.24 seconds.

$ cd mobile && flutter test
00:51 +745: All tests passed!            # 741 → 745 (D-32-5 3건 · buy false 1건)

$ cd mobile && flutter build apk --debug
✓ Built build/app/outputs/flutter-apk/app-debug.apk
apk exit=0                               # `mobile/build` 는 다시 지웠다

$ uv run ruff check .
All checks passed!
```

백엔드(전용 자원 — DB `chosung_daily_test_t32`, Redis DB 6, 마이그레이션 DB
`chosung_daily_test_t32_migrations`; 접속 값은 기록하지 않는다). 이 티켓은
`app/`·`tests/` 를 건드리지 않았고(`git diff --name-only main...HEAD -- app
tests web .scratch migrations .env.example` 빈 출력), 로컬 `main`(`4501286`)
위로 rebase 한 뒤에 돌렸다:

```
$ TEST_DATABASE_URL=...chosung_daily_test_t32 \
  TEST_REDIS_URL=redis://localhost:6379/6 \
  TEST_MIGRATION_DATABASE_URL=...chosung_daily_test_t32_migrations \
  uv run pytest -q
1509 passed in 998.57s (0:16:38)
```

`migrations/` 변경 0건이라 `flask db heads` 는 선행 머지 상태 그대로다
(`git diff --stat main...HEAD -- migrations` 빈 출력).

### 미수정 MINOR

없다. 라운드 2 리뷰의 MINOR 는 0건이었고, "참고 1"(RELEASE 체크리스트)은
고쳤다. 대조표 5번(Android acknowledge 실패를 앱이 알 수 없다)만 의도적으로
남겼다 — 플러그인이 결과를 예외로 주지 않고, 우리 처리("완료하지 않은 채
두고 다음 시작에 재전송")가 이미 안전한 쪽이라 반환형을 바꿀 이유가 없다.
