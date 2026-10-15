import 'dart:async';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_purchase_service.dart';
import '../fakes/in_memory_guest_token_store.dart';

void main() {
  // AppLifecycleListener(포그라운드 복귀 동기화)는 binding 이 있어야 만들어진다.
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakeApiClient api;
  late FakePurchaseService store;
  late NoopAnalyticsService analytics;

  setUp(() {
    api = FakeApiClient();
    store = FakePurchaseService();
    analytics = NoopAnalyticsService();
  });

  tearDown(() => store.dispose());

  /// [token] 이 null 이면 아직 게스트 토큰이 없는 실행이다(재설치 첫 시작 —
  /// `StartupNotifier` 가 `POST /guests` 로 발급하는 중).
  ProviderContainer containerWith({String? token = 'guest-token'}) {
    final container = ProviderContainer(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        purchaseServiceProvider.overrideWithValue(store),
        analyticsServiceProvider.overrideWithValue(analytics),
        guestTokenStoreProvider.overrideWithValue(
          InMemoryGuestTokenStore(token),
        ),
      ],
    );
    addTearDown(container.dispose);
    // 첫 빌드가 스트림을 듣고 상품을 읽는다.
    container.read(purchaseFlowProvider);
    return container;
  }

  /// 스트림·검증·완료가 전부 마이크로태스크라 한 틱 양보해야 끝난다.
  Future<void> settle() => Future<void>.delayed(Duration.zero);

  test('시작하면 상품 가격을 읽고 스토어와 동기화한다 — 미완료 구매 재전송 경로', () async {
    final container = containerWith();
    await settle();

    expect(store.loadProductCalls, 1);
    // 지난 실행에서 끊긴 구매는 이 동기화와 구매 스트림으로 다시 올라온다.
    expect(store.restoreCalls, 1);
    expect(container.read(purchaseFlowProvider).product?.price, '₩1,500');
  });

  test('구매 → 서버 검증 성공 → 그때서야 completePurchase', () async {
    final container = containerWith();
    await settle();
    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );

    final purchase = fakePurchase();
    store.emit([purchase]);
    await settle();

    expect(api.verifiedReceipts, [
      (store: SubscriptionStore.google, receipt: 'receipt-1'),
    ]);
    expect(store.completed, [purchase]);
    // verify 응답의 권한이 그대로 31 의 provider 로 들어간다 → 광고가 꺼진다.
    expect(container.read(entitlementProvider)?.active, isTrue);
    expect(container.read(entitlementProvider)?.until, DateTime.utc(2026, 11));
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.active);
  });

  test('검증이 떠 있는 동안은 verifying — 버튼이 잠긴다', () async {
    final container = containerWith();
    await settle();
    final gate = api.verifySubscriptionGate = Completer<void>();

    store.emit([fakePurchase()]);
    await settle();

    expect(container.read(purchaseFlowProvider).verifying, isTrue);
    expect(container.read(purchaseFlowProvider).busy, isTrue);
    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.verifying,
    );
    // 아직 완료하지 않았다 — 응답이 오기 전에 완료하면 환불 불가 상태로 남는다.
    expect(store.completed, isEmpty);

    gate.complete();
    await settle();
    expect(container.read(purchaseFlowProvider).verifying, isFalse);
    expect(store.completed, hasLength(1));
  });

  test('스토어가 결제를 붙잡고 있으면 pending — 검증은 아직 안 올린다', () async {
    final container = containerWith();
    await settle();

    store.emit([fakePurchase(status: PurchaseStatus.pending)]);
    await settle();

    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );
    expect(container.read(purchaseFlowProvider).busy, isTrue);
    expect(api.verifiedReceipts, isEmpty);
    expect(store.completed, isEmpty);
  });

  test('검증 실패(스토어 장애)면 완료하지 않고 사유를 남긴다 — 다음 시작에 재시도', () async {
    final container = containerWith();
    await settle();
    api.verifySubscriptionError = const StoreUnavailableApiException(
      code: 'STORE_UNAVAILABLE',
      message: '스토어에 연결할 수 없습니다.',
    );

    store.emit([fakePurchase()]);
    await settle();

    expect(store.completed, isEmpty);
    expect(
      container.read(purchaseFlowProvider).error,
      'subscription.error_store',
    );
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.error);
    expect(container.read(entitlementProvider), isNull);
  });

  test('영수증을 인정하지 않으면 그 사유를 보여준다', () async {
    final container = containerWith();
    await settle();
    api.verifySubscriptionError = const ReceiptInvalidApiException(
      code: 'RECEIPT_INVALID',
      message: '영수증을 확인할 수 없습니다.',
    );

    store.emit([fakePurchase()]);
    await settle();

    expect(
      container.read(purchaseFlowProvider).error,
      'subscription.error_receipt',
    );
    expect(store.completed, isEmpty);
  });

  test('같은 거래가 여러 번 올라와도 검증은 한 번만 뜬다', () async {
    containerWith();
    await settle();
    final gate = api.verifySubscriptionGate = Completer<void>();

    // 복원·포그라운드 복귀는 같은 거래를 다시 올려준다.
    store
      ..emit([fakePurchase()])
      ..emit([fakePurchase()]);
    await settle();

    expect(api.verifiedReceipts, hasLength(1));
    gate.complete();
    await settle();
  });

  test('복원된 구매도 같은 길로 검증·완료된다', () async {
    final container = containerWith();
    await settle();
    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );
    store.restorable = [fakePurchase(status: PurchaseStatus.restored)];

    await container.read(purchaseFlowProvider.notifier).restore();
    await settle();

    expect(api.verifiedReceipts, hasLength(1));
    expect(store.completed, hasLength(1));
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.active);
    expect(container.read(purchaseFlowProvider).restoring, isFalse);
  });

  test('복원이 실패하면 사유를 남기고 "복원 중" 을 내린다', () async {
    final container = containerWith();
    await settle();
    store.restoreError = Exception('billing unavailable');

    await container.read(purchaseFlowProvider.notifier).restore();

    expect(container.read(purchaseFlowProvider).restoring, isFalse);
    expect(
      container.read(purchaseFlowProvider).error,
      'subscription.error_restore',
    );
  });

  test('우리 상품이 아닌 거래는 올리지 않는다', () async {
    final container = containerWith();
    await settle();

    store.emit([fakePurchase(productID: 'other_product')]);
    await settle();

    expect(api.verifiedReceipts, isEmpty);
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.idle);
  });

  test('어느 스토어 영수증인지 모르면 올리지 않는다', () async {
    final container = containerWith();
    await settle();

    store.emit([fakePurchase(source: 'amazon')]);
    await settle();

    expect(api.verifiedReceipts, isEmpty);
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.error);
  });

  test('검증 중 계정이 바뀌면 권한도 완료도 건너뛴다 (D-29-5 와 같은 경계)', () async {
    final container = containerWith();
    await settle();
    final gate = api.verifySubscriptionGate = Completer<void>();

    store.emit([fakePurchase()]);
    await settle();
    // 백업 코드·계정 연결로 토큰이 바뀐 순간.
    container.read(accountEpochProvider.notifier).bump();
    gate.complete();
    await settle();

    // 요청은 이미 나갔을 수 있다(서버가 `store_key` 로 멱등하다). 중요한 건
    // 그 권한을 새 계정 화면에 쓰지 않고, 구매를 완료하지 않는 것이다 —
    // 완료하지 않으면 다음 시작에 지금 계정으로 다시 올라간다.
    expect(store.completed, isEmpty);
    expect(container.read(entitlementProvider), isNull);
  });

  test('구독 시작은 subscribe_start 를 찍고 결제 창을 띄운다', () async {
    final container = containerWith();
    await settle();

    await container.read(purchaseFlowProvider.notifier).start();

    expect(analytics.logged.map((event) => event.name), ['subscribe_start']);
    expect(store.bought.single.id, adFreeMonthlyProductId);
  });

  test('가격을 모르면 결제 창을 띄우지 않고 사유를 남긴다', () async {
    store.product = null;
    final container = containerWith();
    await settle();

    await container.read(purchaseFlowProvider.notifier).start();

    expect(store.bought, isEmpty);
    expect(
      container.read(purchaseFlowProvider).error,
      'subscription.error_product',
    );
  });

  test('완료 처리가 플랫폼 예외로 실패해도 권한은 남고 사유만 붙는다', () async {
    final container = containerWith();
    await settle();
    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );
    store
      ..completeError = Exception('platform channel down')
      ..emit([fakePurchase()]);
    await settle();

    // 권한은 이미 서버가 준 것이라 그대로 둔다 — 다음 시작의 재전송이 완료를
    // 다시 시도한다.
    expect(container.read(entitlementProvider)?.active, isTrue);
    expect(
      container.read(purchaseFlowProvider).error,
      'subscription.error_failed',
    );
  });

  test('사용자가 결제 창을 닫은 것은 실패가 아니다', () async {
    final container = containerWith();
    await settle();

    store.emit([fakePurchase(status: PurchaseStatus.canceled)]);
    await settle();

    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.idle);
    expect(container.read(purchaseFlowProvider).error, isNull);
  });

  // --- D-32-1: 게스트 토큰이 아직 없을 때의 시작 동기화 ---

  test('게스트 토큰이 아직 없으면 시작 동기화를 미루고, 토큰이 오면 그때 맞춘다', () async {
    // 재설치 첫 실행: secure storage 는 비어 있고 `StartupNotifier` 가
    // `POST /guests` 로 토큰을 받아 오는 중이다.
    final container = containerWith(token: null);
    store.restorable = [fakePurchase(status: PurchaseStatus.restored)];
    await settle();

    // verify 는 Bearer 가 필요하다. 토큰 없이 올리면 서버에 가지도 못하고
    // 401 이라 아무것도 보내지 않는다.
    expect(store.restoreCalls, 0);
    expect(api.verifiedReceipts, isEmpty);
    expect(container.read(purchaseFlowProvider).error, isNull);

    await container.read(guestTokenProvider.notifier).replaceWith('guest-1');
    await settle();

    expect(store.restoreCalls, 1);
    expect(api.verifiedReceipts, [
      (store: SubscriptionStore.google, receipt: 'receipt-1'),
    ]);
    expect(container.read(entitlementProvider)?.active, isTrue);
  });

  test('토큰 없이 올라온 거래는 실패가 아니라 보류다 — 토큰이 오면 다시 올린다', () async {
    // 스토어는 복원 요청과 무관하게 미완료 거래를 올린다(SK2
    // `Transaction.updates`). 토큰보다 먼저 올 수 있다.
    final container = containerWith(token: null);
    api.verifySubscriptionError = const UnauthorizedApiException(
      code: 'UNAUTHORIZED',
      message: '게스트 토큰이 없습니다.',
    );
    final purchase = fakePurchase();
    store
      ..restorable = [purchase]
      ..emit([purchase]);
    await settle();

    // "결제를 끝내지 못했어요" 를 띄우면 안 된다 — 보낸 적도 없다.
    expect(container.read(purchaseFlowProvider).error, isNull);
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.idle);
    expect(store.completed, isEmpty);

    api.verifySubscriptionError = null;
    await container.read(guestTokenProvider.notifier).replaceWith('guest-1');
    await settle();

    expect(container.read(entitlementProvider)?.active, isTrue);
    // 조회는 거래를 **새 객체**로 올린다(플러그인과 같다) — 같은 영수증인지
    // 로 본다.
    expect(
      store.completed.single.verificationData.serverVerificationData,
      'receipt-1',
    );
  });

  test('secure storage 읽기가 늦게 끝나도 그 뒤에 verify 를 올린다 (지연 Fake)', () async {
    // 재설치가 아니라 "토큰은 있는데 아직 안 읽혔다" 쪽 경쟁이다 — 첫 빌드의
    // 동기화가 이 읽기를 앞지르면 verify 가 서버에 가지도 못하고 401 이었다.
    final slow = _SlowGuestTokenStore('guest-token');
    final container = ProviderContainer(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        purchaseServiceProvider.overrideWithValue(store),
        analyticsServiceProvider.overrideWithValue(analytics),
        guestTokenStoreProvider.overrideWithValue(slow),
      ],
    );
    addTearDown(container.dispose);
    store.restorable = [fakePurchase(status: PurchaseStatus.restored)];
    container.read(purchaseFlowProvider);
    await settle();

    expect(store.restoreCalls, 0);
    expect(api.verifiedReceipts, isEmpty);
    expect(container.read(purchaseFlowProvider).error, isNull);

    slow.release();
    await settle();
    await settle();

    expect(store.restoreCalls, 1);
    expect(api.verifiedReceipts, hasLength(1));
    expect(container.read(entitlementProvider)?.active, isTrue);
    // 계정 경계(29)는 그대로다 — 세대가 바뀌지 않았으니 권한이 들어온다.
    expect(container.read(accountEpochProvider), 0);
  });

  test('토큰이 그대로면 복귀 전까지 시작 동기화를 두 번 돌리지 않는다', () async {
    final container = containerWith();
    await settle();
    expect(store.restoreCalls, 1);

    // 같은 토큰을 다시 쓰는 길(401 복구가 같은 값을 돌려주는 경우 등).
    await container
        .read(guestTokenProvider.notifier)
        .replaceWith('guest-token');
    await settle();

    expect(store.restoreCalls, 1);
  });

  // --- D-32-4: 스토어 쪽에서 포기된 pending ---

  test('Play 조회에서 사라진 pending 은 내린다 — 세션 내내 잠기지 않는다', () async {
    final container = containerWith();
    await settle();
    store.emit([fakePurchase(status: PurchaseStatus.pending)]);
    await settle();
    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );

    // 사용자가 편의점 결제를 포기했다. Play 는 이벤트를 주지 않고 다음
    // `queryPurchases` 에서 그 거래를 빼기만 한다.
    store.restorable = [];
    await container.read(purchaseFlowProvider.notifier).sync();
    await settle();

    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.idle);
    expect(container.read(purchaseFlowProvider).busy, isFalse);
  });

  test('조회에 pending 이 그대로 있으면 내리지 않는다', () async {
    final container = containerWith();
    await settle();
    final pending = fakePurchase(status: PurchaseStatus.pending);
    store
      ..restorable = [pending]
      ..emit([pending]);
    await settle();

    await container.read(purchaseFlowProvider.notifier).sync();
    await settle();

    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );
  });

  // --- D-32-5: Play 조회가 pending 거래에 `restored` 를 덮어쓴다 ---

  test('구매 대기 중 복귀해도 "결제 확인 중" 이다 — 조회의 restored 에 속지 않는다', () async {
    // 편의점·계좌이체 결제는 몇 시간 걸린다. 그 사이 앱을 내렸다 올리면
    // `queryPurchases` 가 같은 거래를 `restored` 로 올리는데(플러그인이 전부
    // 덮어쓴다), `status` 만 보면 대기가 풀리고 권한 없는 응답에
    // acknowledge 까지 나갔다.
    final container = containerWith();
    await settle();
    final pending = fakePurchase(status: PurchaseStatus.pending);
    store.emit([pending]);
    await settle();
    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );

    // 결제가 아직 안 끝났으니 서버는 행을 만들지 않고 200 + active:false 다
    // (`_verify_google`, 스펙 "미정 항목" 14).
    api.verifyResponse = fakeEntitlement();
    store.restorable = [pending];
    await container.read(purchaseFlowProvider.notifier).sync();
    await settle();

    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );
    expect(container.read(purchaseFlowProvider).busy, isTrue);
    // 결제가 끝나기 전에는 올릴 것도, 완료할 것도 없다.
    expect(api.verifiedReceipts, isEmpty);
    expect(store.completed, isEmpty);
    expect(container.read(purchaseFlowProvider).error, isNull);
  });

  test('결제가 끝나면 같은 거래가 purchased 로 올라와 검증·완료된다', () async {
    // 위 테스트의 뒷부분 — 대기를 유지해도 결제 완료를 놓치지 않는다.
    final container = containerWith();
    await settle();
    store.emit([fakePurchase(status: PurchaseStatus.pending)]);
    await settle();

    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );
    store.emit([fakePurchase()]);
    await settle();

    expect(api.verifiedReceipts, hasLength(1));
    expect(store.completed, hasLength(1));
    expect(container.read(subscriptionPhaseProvider), SubscriptionPhase.active);
  });

  test('서버가 구독 행을 만들지 못한 응답에는 completePurchase 를 부르지 않는다', () async {
    // `status == null` = 서버에 이 게스트의 구독 행이 없다 = 권한을 돌려준
    // 것이 아니다(규칙 1). 결제가 끝나지 않은 토큰을 acknowledge 하면 Play
    // 쪽에서 조용히 무시되고 복귀마다 같은 호출이 반복된다.
    final container = containerWith();
    await settle();
    api.verifyResponse = fakeEntitlement();

    store.emit([fakePurchase()]);
    await settle();

    expect(api.verifiedReceipts, hasLength(1));
    expect(store.completed, isEmpty);
    // 권한은 서버가 말한 그대로 반영한다 — 완료만 하지 않는다.
    expect(container.read(entitlementProvider)?.active, isFalse);
  });

  test('App Store 승인 대기는 복원 조회에 없어도 내리지 않는다', () async {
    // StoreKit 2 복원은 `currentEntitlements`(이미 권한이 생긴 거래)만 올린다
    // — 승인 대기가 거기 없는 것은 정상이지 포기가 아니다.
    final container = containerWith();
    await settle();
    store.emit([
      fakePurchase(status: PurchaseStatus.pending, source: 'app_store'),
    ]);
    await settle();

    store.restorable = [];
    await container.read(purchaseFlowProvider.notifier).sync();
    await settle();

    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );
  });

  test('조회 자체가 실패하면 pending 을 내리지 않는다', () async {
    final container = containerWith();
    await settle();
    store.emit([fakePurchase(status: PurchaseStatus.pending)]);
    await settle();

    store.restoreError = Exception('store unreachable');
    await container.read(purchaseFlowProvider.notifier).sync();
    await settle();

    expect(
      container.read(subscriptionPhaseProvider),
      SubscriptionPhase.pending,
    );
  });
}

/// 읽기가 **늦게** 끝나는 토큰 저장소. 재설치가 아니라 "secure storage 가 아직
/// 안 읽혔다" 쪽 경쟁을 그대로 만든다(D-32-1 재현).
class _SlowGuestTokenStore implements GuestTokenStore {
  _SlowGuestTokenStore(this._token);

  final String? _token;
  final _gate = Completer<void>();

  void release() => _gate.complete();

  @override
  Future<String?> read() async {
    await _gate.future;
    return _token;
  }

  @override
  Future<void> write(String token) async {}

  @override
  Future<void> delete() async {}
}
