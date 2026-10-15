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
