import 'dart:async';

import 'package:chosung/subscription/purchase_service.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/billing_client_wrappers.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';

/// 스토어가 알려줄 상품. 가격은 **스토어 현지화 문자열**이라 테스트도 숫자가
/// 아니라 문자열을 그대로 본다(상수로 박지 않는 것이 이 티켓의 요구다).
ProductDetails fakeProduct({
  String id = adFreeMonthlyProductId,
  String price = '₩1,500',
  double rawPrice = 1500,
  String currencyCode = 'KRW',
}) => ProductDetails(
  id: id,
  title: '광고 제거 구독',
  description: '배너·전면 광고 제거',
  price: price,
  rawPrice: rawPrice,
  currencyCode: currencyCode,
);

/// 스토어가 올려줄 거래 하나. [pendingComplete] 가 true 면 "아직 완료되지
/// 않은" 구매다(iOS finish / Android acknowledge 가 남았다).
///
/// `google_play` 는 플러그인이 올리는 것과 **같은 타입**([GooglePlayPurchaseDetails])
/// 으로 만든다 — Play 의 조회가 pending 거래에 `restored` 를 덮어쓰는 길
/// (D-32-5)은 그 안의 `billingClientPurchase.purchaseState` 없이는 테스트에
/// 나타나지 않는다.
PurchaseDetails fakePurchase({
  PurchaseStatus status = PurchaseStatus.purchased,
  String productID = adFreeMonthlyProductId,
  String receipt = 'receipt-1',
  String source = 'google_play',
  String? purchaseID = 'tx-1',
  bool pendingComplete = true,
}) {
  if (source == 'google_play') {
    return _playPurchase(
      status: status,
      productID: productID,
      receipt: receipt,
      purchaseID: purchaseID,
      pendingComplete: pendingComplete,
    );
  }
  return PurchaseDetails(
    productID: productID,
    purchaseID: purchaseID,
    verificationData: PurchaseVerificationData(
      localVerificationData: receipt,
      serverVerificationData: receipt,
      source: source,
    ),
    transactionDate: '1760000000000',
    status: status,
  )..pendingCompletePurchase = pendingComplete;
}

/// Play 거래. `purchaseState` 가 Play 쪽 원본 상태이고 [status] 는 플러그인이
/// 스트림에 얹어 주는 값이다 — 조회에서는 둘이 어긋난다
/// ([FakePurchaseService.restore]).
GooglePlayPurchaseDetails _playPurchase({
  required PurchaseStatus status,
  required String productID,
  required String receipt,
  required String? purchaseID,
  required bool pendingComplete,
  PurchaseStateWrapper? purchaseState,
}) => GooglePlayPurchaseDetails(
  productID: productID,
  purchaseID: purchaseID,
  verificationData: PurchaseVerificationData(
    localVerificationData: receipt,
    serverVerificationData: receipt,
    source: 'google_play',
  ),
  transactionDate: '1760000000000',
  status: status,
  billingClientPurchase: PurchaseWrapper(
    orderId: purchaseID ?? '',
    packageName: 'com.tpzstudio.chosung',
    purchaseTime: 1760000000000,
    purchaseToken: receipt,
    signature: 'signature',
    products: [productID],
    isAutoRenewing: true,
    originalJson: receipt,
    // 생성자가 `pendingCompletePurchase = !isAcknowledged` 로 받는다.
    isAcknowledged: !pendingComplete,
    purchaseState:
        purchaseState ??
        (status == PurchaseStatus.pending
            ? PurchaseStateWrapper.pending
            : PurchaseStateWrapper.purchased),
  ),
);

/// 플러그인 경계를 대신한다. 스트림에 무엇을 올릴지 테스트가 직접 정하고,
/// `complete`·`restore` 가 **언제** 불렸는지를 기록한다 — "성공 뒤에만 완료"
/// 는 그 순서로만 증명된다.
class FakePurchaseService implements PurchaseService {
  final _purchases = StreamController<List<PurchaseDetails>>.broadcast();

  ProductDetails? product = fakeProduct();
  Exception? loadProductError;
  Exception? buyError;
  Exception? restoreError;
  Exception? completeError;

  int loadProductCalls = 0;
  int restoreCalls = 0;
  final List<ProductDetails> bought = [];
  final List<PurchaseDetails> completed = [];

  /// `restore()` 가 스토어에서 되찾아 스트림에 올릴 거래들.
  List<PurchaseDetails> restorable = [];

  /// 스토어가 거래를 올린다. 구매 창·복원과 무관하게 아무 때나 올 수 있다.
  void emit(List<PurchaseDetails> purchases) => _purchases.add(purchases);

  void dispose() => _purchases.close();

  @override
  Stream<List<PurchaseDetails>> get purchases => _purchases.stream;

  @override
  Future<ProductDetails?> loadProduct() async {
    loadProductCalls++;
    if (loadProductError case final error?) throw error;
    return product;
  }

  @override
  Future<void> buy(ProductDetails product) async {
    bought.add(product);
    if (buyError case final error?) throw error;
  }

  @override
  Future<void> restore() async {
    restoreCalls++;
    if (restoreError case final error?) throw error;
    if (restorable.isNotEmpty) emit(restorable.map(_asQueried).toList());
  }

  /// 조회가 올리는 모양으로 바꾼다. `in_app_purchase_android` 0.5.0
  /// `restorePurchases` 는 `queryPurchases` 결과 **전부**에
  /// `details..status = PurchaseStatus.restored` 를 씌운다 — 아직 결제 대기인
  /// 거래도 예외가 아니고, Play 쪽 원본 상태는 `purchaseState` 에만 남는다
  /// (D-32-5). iOS 는 `currentEntitlements` 만 올리므로 그대로 둔다.
  PurchaseDetails _asQueried(PurchaseDetails purchase) =>
      purchase is GooglePlayPurchaseDetails
      ? _playPurchase(
          status: PurchaseStatus.restored,
          productID: purchase.productID,
          receipt: purchase.verificationData.serverVerificationData,
          purchaseID: purchase.purchaseID,
          pendingComplete: purchase.pendingCompletePurchase,
          purchaseState: purchase.billingClientPurchase.purchaseState,
        )
      : purchase;

  @override
  Future<void> complete(PurchaseDetails purchase) async {
    completed.add(purchase);
    if (completeError case final error?) throw error;
  }
}
