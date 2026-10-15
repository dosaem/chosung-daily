import 'dart:async';

import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_client.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/purchase_service.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/billing_client_wrappers.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';

/// 결제 접점. 기본값이 no-op 인 이유는 `adServiceProvider` 와 같다 —
/// `main.dart` 가 실제 구현으로 덮고(`test/config/bootstrap_test.dart` 가
/// 지킨다), 위젯 테스트·골든은 덮지 않아 플랫폼 채널을 타지 않는다.
final purchaseServiceProvider = Provider<PurchaseService>(
  (ref) => const NoopPurchaseService(),
);

/// 지금 이 기기에서 돌고 있는 구매 흐름. **권한은 여기 없다** —
/// 권한의 주인은 `entitlementProvider` 하나다(티켓 31).
@immutable
class PurchaseFlow {
  const PurchaseFlow({
    this.purchase,
    this.verifying = false,
    this.restoring = false,
    this.product,
    this.error,
  });

  /// 구매 스트림이 마지막으로 알려준 상태. null 이면 이번 실행에 아무 거래도
  /// 올라오지 않았다.
  final PurchaseStatus? purchase;

  /// `POST /subscriptions/verify` 가 떠 있는가.
  final bool verifying;

  /// "구매 복원" 을 눌러 스토어 동기화가 떠 있는가. 시작·복귀의 자동 동기화는
  /// 사용자가 기다리는 일이 아니므로 켜지 않는다.
  final bool restoring;

  /// 스토어가 알려준 상품(=표시 가격의 출처). null 이면 가격을 모른다.
  final ProductDetails? product;

  /// 실패 문구의 번역 키. 성공하면 null 이고, Paywall 은 버튼 아래 한 줄로
  /// 둔다(토스트로 흘려보내지 않는다, OVERRIDES §7).
  final String? error;

  /// 결제·검증·복원 중 하나라도 돌고 있으면 버튼을 잠근다.
  bool get busy => verifying || restoring || purchase == PurchaseStatus.pending;

  PurchaseFlow copyWith({
    PurchaseStatus? purchase,
    bool? verifying,
    bool? restoring,
    ProductDetails? product,
    String? error,
    bool clearError = false,
    bool clearPurchase = false,
  }) => PurchaseFlow(
    purchase: clearPurchase ? null : (purchase ?? this.purchase),
    verifying: verifying ?? this.verifying,
    restoring: restoring ?? this.restoring,
    product: product ?? this.product,
    error: clearError ? null : (error ?? this.error),
  );
}

/// 구매 스트림 → (pending 대기) → 서버 검증 → 완료. 스펙 §A.8 "검증·완료
/// 순서" 를 그대로 따른다.
///
/// 규칙 셋만 지킨다.
/// 1. **서버가 권한을 돌려준 뒤에만** `completePurchase` 를 부른다. 그래서
///    검증 실패·앱 종료로 끊긴 구매는 완료되지 않은 채 남고, 다음 시작의
///    스트림과 [sync] 가 다시 올린다(Play 는 3일 내 acknowledge 가 없으면
///    자동 환불한다 — 끊긴 구매를 잃지 않는 쪽이 사용자에게 안전하다).
/// 2. **같은 영수증의 검증은 하나만** 띄운다([_inFlight]). 스트림은 복원·
///    포그라운드 복귀마다 같은 거래를 다시 올려준다.
/// 3. 검증 중 계정이 바뀌면 권한을 반영하지도, 구매를 완료하지도 않는다 —
///    그 영수증은 남의 게스트에 붙을 수 있다(29 의 세대 장치, D-29-5).
class PurchaseFlowNotifier extends Notifier<PurchaseFlow> {
  /// 검증이 떠 있는 영수증들. 키는 거래 ID(없으면 영수증 자체)다.
  final Set<String> _inFlight = {};

  /// 시작 동기화를 이미 돌린 게스트 토큰. `verify` 는 Bearer 가 필요하므로
  /// **토큰이 있을 때만** 영수증을 올리고, 토큰이 바뀌면 한 번만 다시 맞춘다.
  String? _syncedToken;

  /// 지금 붙잡혀 있는 pending 거래가 어느 스토어 것인가.
  SubscriptionStore? _pendingStore;

  /// 이번 [sync] 조회에 pending 거래가 다시 올라왔는가.
  bool _pendingSeenSinceSync = false;

  /// 가장 최근에 뜬 [sync] 의 번호. 조회가 겹치면(복귀 연타) 뒤엣것만
  /// 판정한다 — 앞엣것은 뒤엣것이 초기화한 플래그를 보게 된다.
  int _syncSeq = 0;

  ApiClient get _api => ref.read(apiClientProvider);

  PurchaseService get _service => ref.read(purchaseServiceProvider);

  @override
  PurchaseFlow build() {
    // 첫 빌드에서 바로 듣는다 — 지난 실행의 미완료 거래가 여기로 온다.
    final subscription = _service.purchases.listen(_onPurchases);
    ref.onDispose(subscription.cancel);

    // 포그라운드 복귀 때 스토어와 다시 맞춘다(스펙 §A.8 재조회 (b)). 권한
    // 쪽 `/me/stats` 재조회는 티켓 33 이 따로 건다.
    final lifecycle = AppLifecycleListener(onResume: () => unawaited(sync()));
    ref
      ..onDispose(lifecycle.dispose)
      // 토큰이 늦게 오는 길이 셋 있다: 재설치 첫 실행의 `POST /guests`,
      // 시작 흐름의 401 복구, 계정 전환. 그 전에 올린 영수증은 서버에
      // 가지도 못하고 401 이라, 토큰이 들어오는 자리에서 다시 맞춘다
      // (알림 동기화 `notification_controller.dart` 와 같은 모양).
      ..listen(
        guestTokenProvider,
        (_, next) => unawaited(_syncWithToken(next.value)),
      );

    unawaited(_bootstrap());
    return const PurchaseFlow();
  }

  Future<void> _bootstrap() async {
    await loadProduct();
    // 저장소에 토큰이 남아 있는 보통의 실행은 여기서 바로 맞춘다. 없으면
    // 위 `listen` 이 발급을 기다린다.
    final String? token;
    try {
      token = await ref.read(guestTokenProvider.future);
    } on Exception {
      // 토큰을 못 읽어도 구매 흐름은 떠 있어야 한다(가격·버튼). 읽기가
      // 끝난 뒤 값이 들어오면 `listen` 이 받는다.
      return;
    }
    if (!ref.mounted) return;
    await _syncWithToken(token);
  }

  /// 토큰이 생겼거나 바뀌었을 때 한 번만 스토어와 맞춘다. 같은 토큰으로
  /// 두 번 돌지 않는다 — 복귀 동기화는 [AppLifecycleListener] 쪽이다.
  Future<void> _syncWithToken(String? token) async {
    if (token == null || token.isEmpty || token == _syncedToken) return;
    _syncedToken = token;
    await sync();
  }

  /// 표시 가격을 읽어온다. 실패해도 오류 문구를 띄우지 않는다 — Paywall 을
  /// 열기 전이라 보여줄 자리가 없고, 열 때 다시 부른다.
  Future<void> loadProduct() async {
    final ProductDetails? product;
    try {
      product = await _service.loadProduct();
    } on Exception {
      return;
    }
    if (!ref.mounted || product == null) return;
    state = state.copyWith(product: product);
  }

  /// 스토어 구매 동기화. 올라온 영수증은 스트림을 거쳐 [_onPurchases] 로
  /// 들어가므로 여기서 결과를 다루지 않는다.
  Future<void> sync() async {
    final seq = ++_syncSeq;
    _pendingSeenSinceSync = false;
    try {
      await _service.restore();
    } on Exception {
      // 시작·복귀의 자동 동기화라 사용자에게 말할 것이 없다. 권한은 서버
      // `/me/stats` 가 들고 있고, 다음 복귀에 다시 시도한다. 조회가 실패한
      // 것이므로 "조회에 없다" 로 읽어서도 안 된다.
      return;
    }
    // 올라온 거래는 브로드캐스트 스트림을 한 틱 늦게 탄다([restore] 와 같은
    // 이유). 조회 결과가 다 들어온 뒤에 "없다" 를 판정한다.
    await Future<void>.delayed(Duration.zero);
    if (!ref.mounted || seq != _syncSeq) return;
    _dropAbandonedPending();
  }

  /// Play 의 pending(계좌이체·편의점 결제 등)을 사용자가 포기하면 스토어는
  /// **아무 이벤트도 주지 않고** 다음 `queryPurchases` 에서 그 거래를 빼기만
  /// 한다. 그러면 [PurchaseFlow.purchase] 가 pending 에 눌러앉아 Paywall 의
  /// 두 버튼과 S4 카드가 앱을 다시 켤 때까지 "결제 확인 중" 이다(D-32-4).
  /// 조회에 없으면 내린다 — 조회가 유일한 신호다.
  ///
  /// iOS 는 내리지 않는다: StoreKit 2 의 복원은 `currentEntitlements`(= 이미
  /// 권한이 생긴 거래)만 올리므로, 승인 대기(Ask to Buy)가 거기 **없는 것이
  /// 정상**이다. Play 의 `queryPurchases` 만 pending 을 포함한 전수 조회다.
  void _dropAbandonedPending() {
    if (state.purchase != PurchaseStatus.pending) return;
    if (_pendingSeenSinceSync) return;
    if (_pendingStore != SubscriptionStore.google) return;
    _pendingStore = null;
    state = state.copyWith(clearPurchase: true);
  }

  /// S5 "구독 시작". 가격을 모르면 버튼이 잠겨 있어 여기까지 오지 않는다.
  Future<void> start() async {
    // 탭 자체가 이벤트다(스펙 "미정 항목" 20) — 결제 창이 떴는지와 무관하게
    // "여기서 몇 명이 결제로 넘어갔는가" 를 세는 값이다.
    await ref.read(analyticsServiceProvider).log(subscribeStartEvent);

    final product = state.product;
    if (product == null) {
      state = state.copyWith(error: 'subscription.error_product');
      return;
    }

    state = state.copyWith(clearError: true);
    final bool launched;
    try {
      launched = await _service.buy(product);
    } on Exception {
      if (!ref.mounted) return;
      state = state.copyWith(error: 'subscription.error_failed');
      return;
    }
    // Play 는 결제 창을 띄우지 못해도 예외가 아니라 false 를 돌려주고
    // `onPurchasesUpdated` 도 부르지 않는다 — 여기서 문구를 띄우지 않으면
    // 버튼을 눌러도 아무 일도 일어나지 않는다. iOS(StoreKit 2)는 실패를
    // 예외로 던지므로 위 `on Exception` 으로 온다.
    if (!ref.mounted || launched) return;
    state = state.copyWith(error: 'subscription.error_failed');
  }

  /// S5 "구매 복원". 되찾을 구독이 있으면 스트림으로 올라와 검증을 타고
  /// 권한이 들어온다.
  Future<void> restore() async {
    state = state.copyWith(restoring: true, clearError: true);
    try {
      await _service.restore();
    } on Exception {
      if (!ref.mounted) return;
      state = state.copyWith(
        restoring: false,
        error: 'subscription.error_restore',
      );
      return;
    }
    // 구매 스트림은 브로드캐스트라 `restore()` 가 끝난 **다음 마이크로태스크**에
    // 도착한다. 한 틱 양보해서 검증이 시작된 뒤에 "복원 중" 을 내린다 —
    // 안 그러면 버튼이 한 프레임 깜빡 살아난다.
    await Future<void>.delayed(Duration.zero);
    if (!ref.mounted) return;
    state = state.copyWith(restoring: false);
  }

  void _onPurchases(List<PurchaseDetails> purchases) {
    for (final purchase in purchases) {
      // 우리 상품이 아닌 거래는 올리지 않는다 — 서버가 상품 ID 를 확인하고
      // 400 `RECEIPT_INVALID` 로 거절한다(`app/services/subscription_service.py`).
      if (purchase.productID != adFreeMonthlyProductId) continue;

      final status = _statusOf(purchase);
      switch (status) {
        case PurchaseStatus.pending:
          // 어느 스토어가 붙잡고 있는지 적어 둔다 — 포기 판정이 스토어마다
          // 다르다([_dropAbandonedPending]).
          _pendingStore = subscriptionStoreFor(
            purchase.verificationData.source,
          );
          _pendingSeenSinceSync = true;
          state = state.copyWith(purchase: status, clearError: true);
        case PurchaseStatus.canceled:
          state = state.copyWith(purchase: status, clearError: true);
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          unawaited(_verifyThenComplete(purchase, status));
        case PurchaseStatus.error:
          state = state.copyWith(
            purchase: PurchaseStatus.error,
            error: 'subscription.error_failed',
          );
      }
    }
  }

  /// 이 거래가 **정말** 어느 상태인가.
  ///
  /// Play 의 조회(`restorePurchases`)는 `queryPurchases` 결과 전부에
  /// `status = restored` 를 덮어쓴다(`in_app_purchase_android` 0.5.0
  /// `in_app_purchase_android_platform.dart` `restorePurchases`) — 아직 결제
  /// 대기인 거래도 예외가 아니다. 그래서 `status` 만 보면 편의점·계좌이체
  /// 결제 중에 앱을 한 번 내렸다 올리는 것만으로 "결제 확인 중" 이 풀리고,
  /// 결제가 끝나지도 않은 토큰에 acknowledge 가 나갔다(D-32-5). Play 쪽 원본
  /// 상태는 `billingClientPurchase.purchaseState` 에만 남아 있다.
  ///
  /// `canceled`·`error` 는 스토어가 뜻을 담아 덮은 값이라 그대로 둔다 —
  /// 사용자가 창을 닫은 거래를 pending 으로 되돌리면 버튼이 잠긴다.
  PurchaseStatus _statusOf(PurchaseDetails purchase) {
    if (purchase.status != PurchaseStatus.purchased &&
        purchase.status != PurchaseStatus.restored) {
      return purchase.status;
    }
    if (purchase is GooglePlayPurchaseDetails &&
        purchase.billingClientPurchase.purchaseState ==
            PurchaseStateWrapper.pending) {
      return PurchaseStatus.pending;
    }
    return purchase.status;
  }

  Future<void> _verifyThenComplete(
    PurchaseDetails purchase,
    PurchaseStatus status,
  ) async {
    final receipt = purchase.verificationData.serverVerificationData;
    final store = subscriptionStoreFor(purchase.verificationData.source);
    if (store == null || receipt.isEmpty) {
      // 올릴 수 없는 영수증이다. 완료하지 않는다 — 스토어가 다음에 제대로
      // 된 값을 주면 그때 올라간다.
      state = state.copyWith(
        purchase: PurchaseStatus.error,
        error: 'subscription.error_failed',
      );
      return;
    }

    final key = purchase.purchaseID ?? receipt;
    if (!_inFlight.add(key)) return;

    state = state.copyWith(
      purchase: status,
      verifying: true,
      clearError: true,
    );
    final epoch = ref.read(accountEpochProvider);
    try {
      final entitlement = await ref
          .read(accountEpochProvider.notifier)
          .sendIfSameAccount(
            epoch,
            () => _api.verifySubscription(store: store, receipt: receipt),
          );
      // null = 보내기 전에 계정이 바뀌었다. 보낸 뒤에 바뀌는 길도 있어서
      // 응답을 받고 한 번 더 본다 — 어느 쪽이든 **이 권한은 남의 것**이라
      // 반영하지도 완료하지도 않고, 다음 시작에서 지금 계정으로 다시 올린다
      // (서버는 같은 `store_key` 를 현재 게스트로 재지정한다, 스펙 §A.8).
      if (!_appliesTo(epoch) || entitlement == null) return;

      ref.read(entitlementProvider.notifier).update(entitlement);
      // 여기까지 와서야 완료다(스펙 §A.8 검증·완료 순서). 단 **행이 없는**
      // 응답(`status == null`)은 권한을 돌려준 것이 아니다 — 서버는 결제가
      // 끝나지 않은 Play 구매에 행을 만들지 않고 200 + `active: false` 를
      // 준다(`_verify_google`, 스펙 "미정 항목" 14). 그걸 완료로 읽으면
      // 결제 전 토큰에 acknowledge 가 나간다(규칙 1, D-32-5).
      if (entitlement.status != null && purchase.pendingCompletePurchase) {
        await _service.complete(purchase);
      }
    } on UnauthorizedApiException {
      // 아직 **보내지 못한** 것이지 실패한 것이 아니다 — `_authorized()` 가
      // 토큰이 없으면 서버에 가기 전에 던진다. 실패 문구를 띄우면 재설치
      // 직후 구독자에게 "결제를 끝내지 못했어요" 가 보인다. 거래는 완료하지
      // 않은 채 두고, 토큰이 들어오면 위 `listen` 의 동기화가 다시 올린다.
    } on ReceiptInvalidApiException {
      _fail(epoch, 'subscription.error_receipt');
    } on StoreUnavailableApiException {
      _fail(epoch, 'subscription.error_store');
    } on NetworkApiException {
      _fail(epoch, 'subscription.error_network');
    } on ApiException {
      _fail(epoch, 'subscription.error_failed');
    } on Exception {
      // `completePurchase` 가 플랫폼 예외를 낼 수 있다. 여기서 안 받으면
      // `unawaited` 한 이 future 의 오류가 어디서도 처리되지 않는다 —
      // 권한은 이미 들어갔고 완료만 남은 상태이므로, 다음 시작의 재전송이
      // 같은 자리에서 다시 완료를 시도한다.
      _fail(epoch, 'subscription.error_failed');
    } finally {
      _inFlight.remove(key);
      if (ref.mounted) {
        state = state.copyWith(verifying: _inFlight.isNotEmpty);
      }
    }
  }

  /// [epoch] 에서 떠난 응답을 지금 화면에 써도 되는가.
  bool _appliesTo(int epoch) =>
      ref.mounted && epoch == ref.read(accountEpochProvider);

  void _fail(int epoch, String key) {
    if (!_appliesTo(epoch)) return;
    state = state.copyWith(purchase: PurchaseStatus.error, error: key);
  }
}

final purchaseFlowProvider =
    NotifierProvider<PurchaseFlowNotifier, PurchaseFlow>(
      PurchaseFlowNotifier.new,
    );

/// 화면이 읽는 구독 UI 상태 하나. 입력 셋(구매 상태·검증 여부·권한)이 바뀌면
/// 다시 계산된다 — S5 Paywall 과 S4 구독 카드가 같은 값을 본다
/// (`adGateProvider` 와 같은 모양).
final subscriptionPhaseProvider = Provider<SubscriptionPhase>((ref) {
  final flow = ref.watch(purchaseFlowProvider);
  return subscriptionPhaseFor(
    purchase: flow.purchase,
    verifying: flow.verifying,
    entitlement: ref.watch(entitlementProvider),
  );
});
