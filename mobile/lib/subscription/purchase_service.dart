import 'package:chosung/subscription/subscription_state.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

/// 결제 접점(스펙 §B.20 — 서비스 클래스 하나 + 테스트 no-op).
///
/// 플러그인 타입([PurchaseDetails]·[ProductDetails]·[PurchaseStatus])은 그대로
/// 노출한다 — 같은 값을 앱 전용 타입으로 베끼면 `in_app_purchase` 문서와
/// 대조할 수 없고(광고 쪽 `UmpStatus` 와 같은 판단), 둘 다 플랫폼 채널 없이
/// 만들 수 있는 평범한 Dart 객체라 테스트가 직접 들고 온다.
abstract interface class PurchaseService {
  /// 구매·복원·**지난 실행의 미완료 거래**가 올라오는 스트림. 앱이 뜬 뒤
  /// 늦게 듣기 시작하면 그 사이 거래를 놓치므로 구독 흐름이 첫 빌드에서 바로
  /// 듣는다(스펙 §A.8 "실패·앱 종료 시 다음 시작에서 다시 올린다").
  Stream<List<PurchaseDetails>> get purchases;

  /// 스토어에서 [adFreeMonthlyProductId] 하나를 읽어온다. 스토어에 상품이
  /// 없거나(심사 전·미등록) 조회가 실패하면 null — 가격을 모르면 Paywall 은
  /// 구매 버튼을 잠근다(현지화 가격을 상수로 박지 않기 때문에).
  Future<ProductDetails?> loadProduct();

  /// 스토어 결제 창을 띄운다. 결과는 [purchases] 로 온다.
  Future<void> buy(ProductDetails product);

  /// 스토어 구매 동기화(`restorePurchases`/`queryPurchases`). 결과도
  /// [purchases] 로 온다.
  Future<void> restore();

  /// **서버 검증이 성공한 뒤에만** 부른다(iOS finish / Android acknowledge).
  Future<void> complete(PurchaseDetails purchase);
}

/// 아무 것도 사지 않는 구현. 결제 플러그인을 끼우지 않은 트리(위젯 테스트·
/// 골든)가 기본으로 쓴다 — 스트림이 비어 있어 구독 흐름이 돌지 않는다.
class NoopPurchaseService implements PurchaseService {
  const NoopPurchaseService();

  @override
  Stream<List<PurchaseDetails>> get purchases =>
      const Stream<List<PurchaseDetails>>.empty();

  @override
  Future<ProductDetails?> loadProduct() async => null;

  @override
  Future<void> buy(ProductDetails product) async {}

  @override
  Future<void> restore() async {}

  @override
  Future<void> complete(PurchaseDetails purchase) async {}
}

/// 실제 `in_app_purchase` 구현. `InAppPurchase.instance` 를 필드에 담지 않는다 —
/// 처음 읽는 순간 플랫폼이 등록되므로(`registerPlatform`), 생성만 하고 쓰지
/// 않는 트리(`bootstrap_test`)가 채널을 타지 않게 메서드 안에서 읽는다.
class StorePurchaseService implements PurchaseService {
  const StorePurchaseService();

  @override
  Stream<List<PurchaseDetails>> get purchases =>
      InAppPurchase.instance.purchaseStream;

  @override
  Future<ProductDetails?> loadProduct() async {
    final response = await InAppPurchase.instance.queryProductDetails({
      adFreeMonthlyProductId,
    });
    // `notFoundIDs`·`error` 를 따로 다루지 않는다 — 어느 쪽이든 앱이 할 수
    // 있는 일은 "가격을 모른다" 하나다(조회는 다음 시작에 다시 한다).
    return response.productDetails.firstOrNull;
  }

  @override
  Future<void> buy(ProductDetails product) async {
    // 구독은 소모성이 아니다 — `buyConsumable` 로 사면 Android 가 구매를
    // 소비해 버려 다음 조회에서 사라진다.
    await InAppPurchase.instance.buyNonConsumable(
      purchaseParam: PurchaseParam(productDetails: product),
    );
  }

  @override
  Future<void> restore() => InAppPurchase.instance.restorePurchases();

  @override
  Future<void> complete(PurchaseDetails purchase) =>
      InAppPurchase.instance.completePurchase(purchase);
}
