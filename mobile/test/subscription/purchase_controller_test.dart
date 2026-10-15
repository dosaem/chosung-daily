import 'dart:async';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_purchase_service.dart';

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

  ProviderContainer containerWith() {
    final container = ProviderContainer(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        purchaseServiceProvider.overrideWithValue(store),
        analyticsServiceProvider.overrideWithValue(analytics),
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
    store.completeError = Exception('platform channel down');

    store.emit([fakePurchase()]);
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
}
