import 'package:chosung/api/api_models.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../fakes/fake_api_client.dart';

void main() {
  group('subscriptionPhaseFor', () {
    test('아무 일도 없고 권한도 없으면 idle', () {
      expect(
        subscriptionPhaseFor(
          purchase: null,
          verifying: false,
          entitlement: null,
        ),
        SubscriptionPhase.idle,
      );
    });

    test('스토어가 결제를 붙잡고 있으면 pending', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.pending,
          verifying: false,
          entitlement: null,
        ),
        SubscriptionPhase.pending,
      );
    });

    test('서버 검증 중이면 verifying — pending 보다 먼저다', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.purchased,
          verifying: true,
          entitlement: null,
        ),
        SubscriptionPhase.verifying,
      );
    });

    test('verify 가 권한을 주면 active', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.purchased,
          verifying: false,
          entitlement: fakeEntitlement(
            active: true,
            until: DateTime.utc(2026, 11),
          ),
        ),
        SubscriptionPhase.active,
      );
    });

    test('유예 중이면 grace — 권한은 있지만 결제가 밀렸다', () {
      expect(
        subscriptionPhaseFor(
          purchase: null,
          verifying: false,
          entitlement: fakeEntitlement(
            active: true,
            status: SubscriptionStatus.grace,
            until: DateTime.utc(2026, 10, 20),
          ),
        ),
        SubscriptionPhase.grace,
      );
    });

    test('권한이 있으면 직전 실패보다 권한이 먼저다', () {
      // 이미 구독 중인 사람이 두 번째 구매를 시도해 실패한 경우 — 사실은
      // "구독 중" 이다. 실패 문구를 띄우면 광고가 없는 화면에 모순이 남는다.
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.error,
          verifying: false,
          entitlement: fakeEntitlement(active: true),
        ),
        SubscriptionPhase.active,
      );
    });

    test('권한 없이 실패면 error', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.error,
          verifying: false,
          entitlement: fakeEntitlement(),
        ),
        SubscriptionPhase.error,
      );
    });

    test('사용자가 결제를 취소한 것은 실패가 아니라 idle 이다', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.canceled,
          verifying: false,
          entitlement: null,
        ),
        SubscriptionPhase.idle,
      );
    });

    test('status 가 grace 라도 권한이 끝났으면 미구독(idle)이다', () {
      // 유예가 끝난 행은 `active: false` 로 온다 — 라벨이 아니라 서버 판정을
      // 따른다(스펙 §A.8 판정표).
      expect(
        subscriptionPhaseFor(
          purchase: null,
          verifying: false,
          entitlement: fakeEntitlement(status: SubscriptionStatus.grace),
        ),
        SubscriptionPhase.idle,
      );
    });

    test('보류(hold)는 권한이 없어 미구독으로 보인다', () {
      expect(
        subscriptionPhaseFor(
          purchase: null,
          verifying: false,
          entitlement: fakeEntitlement(status: SubscriptionStatus.hold),
        ),
        SubscriptionPhase.idle,
      );
    });

    test('복원된 구매도 purchased 와 같은 길을 탄다', () {
      expect(
        subscriptionPhaseFor(
          purchase: PurchaseStatus.restored,
          verifying: true,
          entitlement: null,
        ),
        SubscriptionPhase.verifying,
      );
    });
  });

  group('subscriptionStoreFor', () {
    test('플러그인이 알려주는 출처로 스토어를 고른다', () {
      expect(subscriptionStoreFor('app_store'), SubscriptionStore.apple);
      expect(subscriptionStoreFor('google_play'), SubscriptionStore.google);
    });

    test('모르는 출처면 null — 어느 스토어인지 추측해서 올리지 않는다', () {
      expect(subscriptionStoreFor('amazon'), isNull);
      expect(subscriptionStoreFor(''), isNull);
    });
  });

  group('subscriptionManagementUrl', () {
    test('스토어의 구독 관리 화면을 연다', () {
      expect(
        subscriptionManagementUrl(SubscriptionStore.apple),
        'https://apps.apple.com/account/subscriptions',
      );
      expect(
        subscriptionManagementUrl(SubscriptionStore.google),
        'https://play.google.com/store/account/subscriptions',
      );
    });
  });

  test('상품 ID 는 스펙 §B.23 의 하나뿐이다', () {
    expect(adFreeMonthlyProductId, 'adfree_monthly');
  });
}
