import 'dart:async';

import 'package:chosung/subscription/purchase_service.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

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
PurchaseDetails fakePurchase({
  PurchaseStatus status = PurchaseStatus.purchased,
  String productID = adFreeMonthlyProductId,
  String receipt = 'receipt-1',
  String source = 'google_play',
  String? purchaseID = 'tx-1',
  bool pendingComplete = true,
}) => PurchaseDetails(
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
    if (restorable.isNotEmpty) emit(restorable);
  }

  @override
  Future<void> complete(PurchaseDetails purchase) async {
    completed.add(purchase);
    if (completeError case final error?) throw error;
  }
}
