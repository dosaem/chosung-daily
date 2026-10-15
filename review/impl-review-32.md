# 티켓 32 최종 리뷰 — 라운드 1

**대상:** 브랜치 `dosaem/t32-app-subscription-purchase-paywall`, `git diff main...HEAD`(커밋 5개 `2ed89d0`…`8a1557a`), 구현 증거 `review/impl-evidence-32.md`
**리뷰어:** Fable (Final Reviewer) · **날짜:** 2026-10-15
**읽은 것:** 티켓 `issues/32-*.md`, 스펙 §A.8·§B.18·§B.20·§B.21·§B.23·US 26~30d·34a·미정 20, `design/SCREENS.md` S4·S5·T2·T4, `design-system/hidden-vowels/OVERRIDES.md` §2·§7, 목업 `e5_paywall`·`e4_records`, `docs/legal-checklist.md` "4.", 웹 약관 `terms.ko/en.html#subscription`, `in_app_purchase_storekit` 0.4.13 · `in_app_purchase_android` 0.5.0 소스(pub-cache), 티켓 33 worktree(읽기만).

## 0. 직접 돌린 것

| 명령 | 결과 |
|---|---|
| `cd mobile && flutter analyze` | **1 issue — `info • cascade_invocations • test/subscription/purchase_controller_test.dart:284`, exit 1.** 증거 문서의 "No issues found" 와 다르다(D-32-2) |
| `cd mobile && dart format --output=none --set-exit-if-changed lib test` | 0 changed, exit 0 |
| `cd mobile && flutter test` | **+733: All tests passed!**, exit 0 (증거와 같음) |
| `cd mobile && flutter build apk --debug` (코디네이터 메모 1) | `✓ Built build/app/outputs/flutter-apk/app-debug.apk`(Gradle `assembleDebug` 99.5s), exit 0. 산출물 `mobile/build` 삭제함 |
| `uv run ruff check .` | All checks passed!, exit 0 |
| `uv run pytest -q` (전용 DB `chosung_daily_test_t32` · Redis DB 6 · `chosung_daily_test_t32_migrations`, 접속 값은 기록하지 않음) | **1509 passed in 945.20s (0:15:45)**, exit 0 (증거와 같음; 이 티켓은 백엔드를 건드리지 않았다) |
| `flask db heads` | 돌리지 않음 — `migrations/` 변경 0건(`git diff --stat main...HEAD -- migrations` 비어 있음) |
| 백엔드·웹·스펙 변경 | `app/`·`tests/`·`web/`·`.env.example`·`.scratch/` 변경 0건 — 증거 §범위 주장과 일치 |

재현용 임시 테스트 1개를 `mobile/test/` 에 잠깐 만들어 돌린 뒤 지웠다(D-32-1 재현, 아래). 커밋에 남지 않았고 `git status` 는 깨끗하다.

## 1. 티켓 체크박스별 판정

| # | 체크박스 | 판정 | 근거 |
|---|---|---|---|
| 1 | ApiClient `POST /subscriptions/verify`(Dio + Fake) | 충족 | `dio_api_client.dart:177` `verifySubscription` — `{store, receipt}` + Bearer. 테스트 3건이 경로·메서드·본문·헤더·`RECEIPT_INVALID`(400)·`STORE_UNAVAILABLE`(503→전용 예외)을 본다. Fake 는 `verifiedReceipts`·`verifySubscriptionGate`·`verifySubscriptionError`. wire 값(`apple`/`google`, `receipt`)이 서버 `VerifyReceiptRequest` 와 같다 |
| 2 | `in_app_purchase`(StoreKit 2 · Billing 8+ 절차 RELEASE.md · `adfree_monthly` · 가격 상수 금지) | 충족 | `pubspec.yaml` `in_app_purchase ^3.3.1`·`in_app_purchase_storekit ^0.4.13`. StoreKit 2 는 플러그인 기본값(`_useStoreKit2 = true`, 플러그인 소스 34행)이고 `bootstrap_test` "iOS 는 StoreKit 2 로 돈다" 가 못 박는다. iOS 배포 타깃 15.0(StoreKit 2 최소). Billing 8+ 절차는 `docs/RELEASE.md "### 32."`(실측 `billing:8.0.0` 을 pub-cache 에서 확인했다). 가격은 `ProductDetails.price` 만 쓰고 `₩1,500` 리터럴은 `lib/` 에 없다(`grep` 0건) |
| 3 | 스트림 → pending 대기 → verify → 성공 후에만 `completePurchase` · 재전송 · `restorePurchases` 결과 verify · 31 의 Provider 즉시 갱신 | **미충족(일부)** | 순서 자체는 `purchase_controller.dart:174` `_verifyThenComplete` 한 곳이고 테스트 15건이 "성공 뒤에만 완료"·pending 대기·중복 억제·복원 경로·계정 경계를 본다. 새 Provider 를 만들지 않고 31 의 `entitlementProvider` 를 넓혔다. **그러나 "시작 시 `restorePurchases` 결과를 verify 로 재전송" 이 게스트 토큰 복원 전에 나가면 401 로 끝나고 다시 보내지 않는다 — D-32-1** |
| 4 | 구매 상태→UI 순수 함수(idle/pending/verifying/active/grace/error) 단위 테스트 | 충족 | `subscription_state.dart:46` `subscriptionPhaseFor`, 테스트 15건(6상태 + 우선순위 3 + 경계 2 + store/URL/상품 ID) |
| 5 | S5 Paywall 구성 + `paywall_view`/`subscribe_start` | 충족 | `paywall_sheet_test.dart` "S5: …"·"진입에 paywall_view, 구독 시작 탭에 subscribe_start" — `NoopAnalyticsService.logged` 로 이름·순서까지. 혜택 가운데 줄 "광고 없이 힌트 미리 보기" 확인. 가격 카드 문구는 D-32-3 참고(MINOR) |
| 6 | 고지 6요소 + ko/en 이 약관 구독 절과 같은 표현 + 태블릿 744 다이얼로그 | 충족 | `PaywallKeys` 6개 → 테스트가 하나씩 존재 확인. ko/en 문구를 `web/templates/legal/terms.{ko,en}.html#subscription` 과 대조: "24시간 전까지"·"설정 > Apple 계정 > 구독"·"Google Play > 구독" / "automatically renews"·"24 hours"·"Google Play > Subscriptions" 동일. 744: `Dialog` 1·`BottomSheet` 0·폭 ≤ 560 |
| 7 | S4 구독 카드 세 얼굴 + "관리" | 충족 | `subscription_card.dart`, `records_subscription_test.dart` 6건(미구독→Paywall, 가격 미확인, 구독 중 Apple URL, 유예 중 Google URL, hold, en). "관리" 는 `entitlement.source` 기준 |
| 8 | 위젯 테스트 4종 · `audit.native`(태블릿 폭) · 목업 대비 · README Flutter 절 | 충족 | 배너 제거 `purchase_entitlement_test.dart`(실제 `ChosungApp` 트리), pending 비활성·복원 성공·이벤트 2개 `paywall_sheet_test.dart`. audit 표 증거 §4(소스 읽기 자가 채점, 390/744/1024 는 테스트·골든). 목업 차이 3건 기록(증거 §5). README `### 22.` "구독 상태 흐름(티켓 32)" 단락 + `### 32.` |

공통 규칙: README `### 32.` 는 "설계 판단" 절 끝(`### 31.` 뒤, `## 부하 테스트 요약` 앞), `docs/RELEASE.md` `### 32.` 는 파일 끝 — 자기 번호 소제목만 덧붙였다. `.env.example`·스펙 "미정 항목" 은 건드리지 않았다(확정한 미정 항목 없음). 마이그레이션 없음.

## 2. 결함

### D-32-1 (MAJOR) 시작 동기화가 게스트 토큰 복원 전에 verify 를 보내면 401 로 실패하고, 토큰이 와도 다시 보내지 않는다

- **파일:** `mobile/lib/subscription/purchase_controller.dart:88-101` (`build` → `_bootstrap` → `sync`), `:174-196` (`_verifyThenComplete` → `on ApiException` → `_fail`), `mobile/lib/api/api_providers.dart:17` (`readToken: () => ref.read(guestTokenProvider).value`), `mobile/lib/api/dio_api_client.dart:219-227` (`_bearer` — 토큰 없으면 `UnauthorizedApiException`)
- **무엇:** 구매 흐름은 `ChosungApp` 첫 빌드에서 바로 `loadProduct()` → `sync()`(= `restorePurchases`) 를 돌린다. 같은 시점에 `guestTokenProvider`(AsyncNotifier) 는 secure storage 를 읽는 중이고, 재설치라면 `StartupNotifier._ensureGuestToken` 이 `POST /guests` 를 기다리는 중이다. 그 사이 스토어가 미완료·복원 거래를 올리면 `_api.verifySubscription` 이 `_authorized()` 에서 **서버에 가지도 않고** `UnauthorizedApiException` 을 던지고, `_verifyThenComplete` 는 그걸 `on ApiException` 으로 받아 `error_failed`("결제를 끝내지 못했어요. 다시 시도해주세요") 를 띄운 채 끝난다. 토큰이 도착해도 구매 흐름은 `guestTokenProvider` 를 듣지 않으므로(알림 동기화 `notification_controller.dart:59` 는 듣는다) 다음 **포그라운드 복귀**까지 재전송이 없다.
- **영향:** US 28(재설치 뒤 복원)·US 30d(결제 중 종료 → 다음 시작에 마무리) 의 "다음 시작" 경로가 시작 1회에선 비결정적으로 실패한다. 재설치 직후 Paywall 을 열면 구독자에게 실패 문구가 보이고, "구매 복원" 을 직접 눌러야 권한이 돌아온다. 토큰이 서버에서 무효가 되어 시작 흐름이 재발급하는 경우(`_fetchStats` 의 401 복구)도 같은 길이다.
- **재현(임시 테스트, 삭제함):** `guestTokenStoreProvider` 를 `read()` 가 Completer 를 기다리는 저장소로, `purchaseServiceProvider` 를 `FakePurchaseService(restorable: [fakePurchase(status: restored, source: 'app_store')])` 로 덮고 **`apiClientProvider` 는 실제 `DioApiClient` 그대로** 둔 뒤 `purchaseFlowProvider` 를 읽고 마이크로태스크 3틱 → `error == 'subscription.error_failed'`, `phase == error`, `entitlementProvider == null`. 이어서 Completer 를 완료하고 5틱 → 여전히 `error`, `restoreCalls == 1`(재동기화 없음). 기대: 토큰이 준비된 뒤 verify 가 나가 `active` 가 되거나, 최소한 토큰 도착 시 재동기화.
- **고치는 방향(제안):** `_bootstrap` 에서 `await ref.read(guestTokenProvider.future)` 뒤에 `sync()`; 또는 알림 동기화처럼 `ref.listen(guestTokenProvider, …)` 로 토큰이 바뀔 때 `sync()`. `UnauthorizedApiException` 을 `_fail` 로 보내지 않고 "아직 못 보냄" 으로 두는 것도 같이.

### D-32-2 (MAJOR) `flutter analyze` 가 exit 1 — CI "Analyze" 단계가 이 브랜치에서 실패한다

- **파일:** `mobile/test/subscription/purchase_controller_test.dart:284`
- **재현:** `cd mobile && flutter analyze` → `info • Unnecessary duplication of receiver • …:284:5 • cascade_invocations`, `1 issue found`, exit 1. `.github/workflows/flutter-ci.yml:48` 이 `flutter analyze`(infos fatal 기본) 를 돌리므로 CI 가 빨간불이다. 증거 §6 의 "No issues found!" 는 현재 HEAD 와 다르다.
- **기대:** 0 issues. 고침은 `store.completeError = …; store.emit(…)` 두 줄을 캐스케이드(`store..completeError = … ..emit(…)`)로 합치는 한 줄이다. 심각도를 MAJOR 로 둔 이유는 코드 품질이 아니라 **머지 게이트(CI)가 깨진 상태**이기 때문이다.

### D-32-3 (MINOR) 가격 카드 문구가 SCREENS S5 와 다르다 — "월 {가격}" 이 아니라 "{가격}"

- **파일:** `mobile/lib/subscription/paywall_sheet.dart:247-251` (`product?.price ?? …`)
- **재현:** Paywall 390 골든 `paywall_light_390.png` — 가격 줄이 `₩1,500`. `design/SCREENS.md` S5 는 가격 카드 "월 {스토어 현지화 가격}", 목업 `e5_paywall` 도 "월 ₩1,500". S4 카드는 "월 ₩1,500" 으로 맞게 그리면서 S5 만 빠졌다. 증거 §5 의 "목업과 다르게 구현한 것 3건" 에도 없다. 아래 "구독 기간 1개월" 줄이 있어 뜻은 전달되지만 스펙 문구 규격과 어긋난다.
- **기대:** `subscription.card_idle` 처럼 "월 {price}"(en "{price} / month") 로.

### D-32-4 (MINOR) Android 에서 pending 거래가 스토어 쪽에서 취소·만료되면 그 세션 내내 "결제 확인 중" 으로 잠긴다

- **파일:** `mobile/lib/subscription/purchase_controller.dart:150-154` (`pending` → `state.purchase = pending`), `:55` (`busy`), `subscription_card.dart:44-46`
- **무엇:** `state.purchase` 는 스트림 이벤트로만 바뀐다. Play 의 pending(계좌이체·편의점 결제 등) 이 사용자가 포기해 취소되면 `queryPurchases` 가 그 거래를 **더 이상 돌려주지 않을 뿐** 어떤 이벤트도 오지 않으므로, `pending` 이 남아 Paywall 의 두 버튼과 S4 카드가 앱을 완전히 다시 시작할 때까지 "결제 확인 중" 이다.
- **재현(논리):** `store.emit([fakePurchase(status: pending)])` → `restore()` 가 빈 목록을 올림 → `phase` 는 여전히 `pending`. 기대: 복귀 동기화 결과에 그 거래가 없으면 `pending` 을 내린다(또는 S4 카드에서만이라도 Paywall 을 열 수 있게 — 지금도 열리긴 한다).
- 스펙이 "pending 이면 대기" 만 정했고 포기 경로는 안 정했으므로 MINOR.

## 3. 코디네이터 메모 항목

**1) APK 빌드:** 위 §0 표 참고. `flutter build apk --debug` exit 0 — Android 빌드는 통과한다(in_app_purchase_android 0.5.0 + Billing 8.0.0 포함). release 빌드·merged manifest 확인은 RELEASE.md "### 32." 의 사람 절차로 남겨 둔 상태 그대로다.

**2) 티켓 33 과의 통합 위험(`entitlement_provider.dart` 충돌)** — 32 단독 정확성과는 별개로, 머지 때 사람이 봐야 할 것:

| 파일 | 32 | 33 | 머지 시 |
|---|---|---|---|
| `lib/subscription/entitlement_provider.dart` | 타입 `bool?` → `Entitlement?`, `update(Entitlement)` | 타입 `bool?` 유지, `update({required bool active, DateTime? observedAt})` + `_observedAt` 비교, `clear()` | **텍스트 충돌 + 의미 병합 필요**: `Notifier<Entitlement?>` 에 `update(Entitlement entitlement, {DateTime? observedAt})` + `clear()` 로 합쳐야 한다. 32 의 구매 경로는 `observedAt` 없이 부르면 되고(33 의 "늘 이긴다" 규칙과 맞다), 33 의 `_applied` 는 `active:` 가 아니라 `stats.entitlement` 객체를 넘기게 바꿔야 한다 |
| `lib/api/api_models.dart` | `Entitlement{active, until, status, source, nextCheckAt}` + `SubscriptionStore`·`SubscriptionStatus` enum, 시각 `toUtc()` | `Entitlement{active, nextCheckAt}`, `DateTime.parse` 그대로, `MyStats.entitlement` **required** | **같은 이름 클래스 2개 → 컴파일 충돌**. 32 의 상위집합을 남기고 33 의 `MyStats.entitlement` 필드만 가져오면 된다. 33 쪽을 남기면 S4 카드의 갱신일·"관리" 스토어가 `/me/stats` 경로에서 전부 null 이 된다 |
| `lib/ads/ad_providers.dart` | `entitled: ref.watch(entitlementProvider)?.active` | 변경 없음(`bool?` 그대로) | 32 쪽 유지 |
| `lib/app.dart` | `..listen(purchaseFlowProvider, …)` | `..listen(entitlementRefreshProvider, …)` | 같은 캐스케이드에 줄 하나씩 — 둘 다 넣는다 |
| 테스트 fakes (`fake_entitlement.dart`·`fake_api_client.dart` `fakeMyStats`) | `FakeEntitlement(value:)`, `fakeEntitlement()` | 33 이 `fakeMyStats(entitlement:)` 를 더했을 가능성 | 33 의 `MyStats` 생성자 변경이 32 의 `FakeApiClient`·records 테스트에 닿는다 |

의미 쌍(머지 뒤 확인할 것):
- 33 의 타이머는 **`myStatsProvider` 응답의 `next_check_at` 으로만** 걸린다. 32 의 verify 응답에도 `next_check_at` 이 오지만 33 은 그걸 보지 않으므로, **구매 직후의 포그라운드 세션**에선 다음 복귀까지 재확인 타이머가 없다(구매 전 `/me/stats` 는 `next_check_at: null`). 스펙 §A.8 (a) 문면("`/me/stats` 응답의 `next_check_at`")에는 맞지만 US 30c(환불 1시간 내 감지) 가 구매 직후 세션엔 비는 구간. 32 의 `PurchaseFlowNotifier` 가 verify 성공 뒤 `entitlementRefreshProvider.notifier.refresh()` 를 부르거나, 33 이 `entitlementProvider` 변화를 듣게 하면 메워진다.
- 33 의 `observedAt` 규칙(조회 떠난 시각 ≤ 기존 관측이면 버림)은 32 의 "verify 응답은 지금 관측" 과 맞물려 **구매 응답을 구매 전 `/me/stats` 응답이 덮는 순서를 막는다** — 병합 때 `update(Entitlement, {observedAt})` 시그니처만 지키면 그대로 산다.
- 계정 경계: 32 는 epoch 검사로 남의 권한을 **넣지 않을** 뿐 기존 값을 비우지 않는다. 비우는 건 33 의 `clear()`(`MyStatsNotifier.discard` 경로)다. 둘 다 머지돼야 "계정 전환 뒤 옛 권한이 남는" 구간이 없다.
- 복귀 때 32 의 `sync()`(→ verify → 서버 스토어 조회) 와 33 의 `refresh()`(→ `/me/stats` → 서버 재조회) 가 **동시에** 나간다. 서버 쪽 1h TTL·±24h 5분 상한이 스토어 API 중복 호출을 막는다(티켓 13 확정). 앱 쪽 요청 2건은 스펙 §A.8 (a)(b) 가 요구하는 것이라 결함 아님.

**3) 비동기 경로 쌍 표(32 범위):**

| 쌍 | 처리 | 판정 |
|---|---|---|
| 구매 × 복원(동시) | busy 면 두 버튼 모두 잠김; 같은 거래가 두 길로 와도 `_inFlight` 가 하나만 올림 | OK (테스트 "같은 거래가 여러 번…") |
| 구매 × verify 진행 중 앱 종료 | 완료 안 됨 → SK2 `Transaction.updates`/Android `queryPurchases` 가 다음 시작에 다시 올림 | OK, 단 **D-32-1** 경쟁 |
| 시작 동기화 × 토큰 미복원 | — | **D-32-1** |
| verify × 계정 전환(epoch) | 보내기 전 바뀌면 안 보냄, 보낸 뒤 바뀌면 반영·완료 안 함 → 다음 복귀 재전송 | OK (테스트 "검증 중 계정이 바뀌면…") |
| verify 성공 × `completePurchase` 예외 | 권한 유지 + 사유, 다음 시작 재완료 | OK (테스트) |
| verify × `RECEIPT_INVALID` | 완료 안 함, 매 시작·복귀마다 재전송 → 매번 400 + Paywall 에 사유 | 설계 결정(README "32.")대로. "참고" 1 |
| pending × 스토어 쪽 취소 | 이벤트 없음 → 세션 내 잠김 | **D-32-4** |
| pending × 앱 재시작 | `queryPurchases` 가 pending 을 다시 올림 → 같은 상태, 완료되면 purchased → verify | OK |
| 복원 × 되찾을 것 없음 | `restoring` 내리고 무안내 | 설계 결정(증거 §7) |
| 복원 × SK2 `currentEntitlements` 의 `restored` | `pendingCompletePurchase` 가 false 라 verify 만, finish 없음 — 미완료 거래는 `Transaction.updates` 가 따로 `purchased` 로 올려 finish 됨 | OK(플러그인 `app_store_purchase_details.dart:108` 확인) |
| verify × 33 타이머 응답 교차 | 33 의 `observedAt` | 머지 뒤 확인(위 §3-2) |
| 구매 직후 × 33 타이머 미장전 | — | 머지 뒤 확인(위 §3-2) |

**4) 자동 갱신 고지 — 스토어 정책 대조:** Apple App Review 3.1.2(a) + Apple Developer Program License Agreement Schedule 2 §3.8(b)(구독 제목 · 기간 · 가격 · 약관/개인정보 링크) 와 Google Play 구독 정책(가격 · 결제 주기/청구 시점 · 자동 갱신 조건 · 해지 방법) 이 요구하는 항목이 `PaywallKeys` 6개(상품명·기간·가격·자동 갱신·해지 방법·링크)에 전부 있고, 테스트가 존재를 하나씩 본다. 가격은 결제 시트와 같은 문자열(`ProductDetails.price`)이라 "표시 가격 ≠ 청구액" 사유도 없다. 빠진 것 없음. 참고: Apple 은 결제 전 화면 어디서든 보이면 되고 Google 은 "구독 시작" 버튼 근처에 있기를 권하는데, 가격 카드(버튼 바로 위)에 모여 있어 둘 다 만족한다.

## 4. 참고 (결함 아님)

1. **`RECEIPT_INVALID` 영구 재전송:** 서버가 거절한 영수증은 완료하지 않기로 했으므로(README "32.") 그 기기는 매 시작·복귀마다 같은 400 을 받고 Paywall 에 "스토어 고객센터 문의" 가 뜬다. Play 는 3일 뒤 환불하지만 iOS 는 환불 없이 미완료 거래가 계속 남는다. 서버 설정 사고(번들 ID·키)로 정상 영수증이 400 을 받는 경우 영향이 커서, 운영 중 400 비율 모니터링(Sentry 태그)을 33/운영 티켓에서 고려할 만하다.
2. **`subscribe_start` 는 가격을 못 읽어 결제 창이 안 떠도 찍힌다** — 미정 20 의 "탭 자체가 이벤트" 해석을 따랐고 코드 주석에 근거가 있다. 전환율 분모가 조금 부풀 수 있다는 점만 적어 둔다.
3. **증거 §4 audit 표는 소스 읽기 자가 채점**이다(브라우저 도구 없음). 폭 분기는 테스트·골든이 실제로 덮으므로 "통과" 판정은 받아들였다.
4. **`_EntitledRow` 의 "관리" 는 `source` 가 null 이면 숨는다** — 서버가 상태 라벨을 늘려 `source` 를 모르는 값으로 보내는 경우. 권한은 유지되므로 안전한 쪽이다.
5. 목업 대비 차이 3건(혜택 문구 "무제한" 제거, S4 설정 행 1줄, 헤더 닫기·streak 생략)은 스펙·OVERRIDES 근거가 있고 증거 §5 에 기록돼 있다 — 이의 없음.

판정: FAIL
