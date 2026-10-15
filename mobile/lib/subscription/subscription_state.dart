import 'package:chosung/api/api_models.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

/// 스토어에 등록한 월 구독 상품(스펙 §B.23). 이름이 여기 한 곳에만 있어야
/// 조회(`queryProductDetails`)와 구매가 같은 상품을 가리킨다.
///
/// **가격은 여기 없다** — 표시 가격은 `ProductDetails.price`(스토어 현지화
/// 가격)이고 ₩1,500 은 한국 Tier 설정값일 뿐이다(스펙 §A.8).
const String adFreeMonthlyProductId = 'adfree_monthly';

/// 구독 UI 가 보여줄 얼굴 하나. S5 Paywall 과 S4 구독 카드가 같은 값을 읽는다.
enum SubscriptionPhase {
  /// 미구독, 아무것도 돌지 않는다 → "구독 시작" 을 누를 수 있다.
  idle,

  /// 스토어가 결제를 붙잡고 있다(계좌 이체·보호자 승인 등) → 버튼 비활성.
  pending,

  /// 영수증을 서버에 올리는 중 → 버튼 비활성. 성공해야 구매가 완료된다.
  verifying,

  /// 권한이 있다 → "광고 제거 · 갱신일".
  active,

  /// 권한은 있지만 결제가 밀렸다(Billing Grace Period) → "결제 확인 중 · 유예".
  grace,

  /// 구매·검증이 실패했고 권한도 없다 → 사유 한 줄 + 다시 시도.
  error,
}

/// 스토어 구매 상태 + 서버 권한 → 화면 하나. 입력이 셋뿐인 순수 판정이라
/// Paywall·S4 카드가 각자 조건문을 쓰지 않는다(스펙 §B.20 "구독 UI 판정은
/// 순수 함수").
///
/// [purchase] 는 구매 스트림이 마지막으로 알려준 상태(null = 아직 없음),
/// [verifying] 은 `POST /subscriptions/verify` 가 떠 있는가, [entitlement] 는
/// 서버가 돌려준 권한(null = 아직 모른다)이다.
///
/// 순서가 뜻을 만든다: **돌고 있는 일**이 먼저고(버튼을 잠가야 두 번 결제가
/// 안 된다), 그 다음이 **서버가 말한 권한**, 실패는 마지막이다. 권한을 실패
/// 뒤로 밀면 이미 구독 중인 사람이 두 번째 구매에 실패했을 때 광고 없는
/// 화면에 "실패" 가 뜬다.
SubscriptionPhase subscriptionPhaseFor({
  required PurchaseStatus? purchase,
  required bool verifying,
  required Entitlement? entitlement,
}) {
  if (verifying) return SubscriptionPhase.verifying;
  if (purchase == PurchaseStatus.pending) return SubscriptionPhase.pending;

  if (entitlement != null && entitlement.active) {
    // 라벨이 아니라 `active` 가 권한이다 — 유예가 끝난 행도 `status` 는
    // grace 로 오지만 `active` 는 false 다(스펙 §A.8 판정표).
    return entitlement.status == SubscriptionStatus.grace
        ? SubscriptionPhase.grace
        : SubscriptionPhase.active;
  }

  // 취소는 실패가 아니다 — 사용자가 결제 창을 닫은 것이라 아무 문구도 띄우지
  // 않고 "구독 시작" 으로 돌아간다.
  if (purchase == PurchaseStatus.error) return SubscriptionPhase.error;
  return SubscriptionPhase.idle;
}

/// `PurchaseVerificationData.source` → 서버에 올릴 `store`.
///
/// `defaultTargetPlatform` 이 아니라 영수증이 들고 온 출처를 쓴다 — 올리는
/// 값과 영수증이 어긋나면 서버가 엉뚱한 스토어 API 로 조회한다. 모르는
/// 출처면 null 이고, 구매 흐름은 그 영수증을 올리지 않는다.
SubscriptionStore? subscriptionStoreFor(String source) => switch (source) {
  'app_store' => SubscriptionStore.apple,
  'google_play' => SubscriptionStore.google,
  _ => null,
};

/// S4 구독 카드의 "관리" 가 여는 스토어 화면.
///
/// Android 는 `?sku=&package=` 로 상품까지 딥링크할 수 있지만 패키지명을
/// Dart 쪽에 한 벌 더 두게 된다(지금은 `build.gradle.kts` 한 곳이다) —
/// 구독이 하나뿐이라 목록 화면으로 보내도 사용자가 할 일은 같다.
String subscriptionManagementUrl(SubscriptionStore store) => switch (store) {
  SubscriptionStore.apple => 'https://apps.apple.com/account/subscriptions',
  SubscriptionStore.google =>
    'https://play.google.com/store/account/subscriptions',
};
