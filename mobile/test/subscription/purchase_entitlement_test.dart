import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/fake_purchase_service.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';

/// verify 응답의 권한이 **광고 게이트까지** 닿는지 본다 — provider 를 가짜로
/// 덮지 않고(31 의 `banner_slot_gate_test` 와 달리) 실제 구매 흐름이 권한을
/// 넣는 길을 그대로 돌린다.
Future<void> _pumpApp(
  WidgetTester tester, {
  required FakeApiClient api,
  required FakePurchaseService store,
  required FakeAdService ads,
}) async {
  tester.view
    ..physicalSize = const Size(390, 844)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          purchaseServiceProvider.overrideWithValue(store),
          guestTokenStoreProvider.overrideWithValue(
            InMemoryGuestTokenStore('guest-token'),
          ),
          onboardingStoreProvider.overrideWithValue(
            InMemoryOnboardingStore(seen: true),
          ),
          appVersionProvider.overrideWith((_) async => '1.0.0'),
          isIosProvider.overrideWithValue(false),
          trackingAuthorizationProvider.overrideWithValue(
            FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
          ),
          adServiceProvider.overrideWithValue(ads),
        ],
        child: const AppLocalizationScope(
          startLocale: Locale('ko'),
          child: ChosungApp(),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('구매가 서버 검증을 통과하면 배너 슬롯이 바로 사라진다', (tester) async {
    final api = FakeApiClient()
      ..verifyResponse = fakeEntitlement(
        active: true,
        until: DateTime.utc(2026, 11),
      );
    final store = FakePurchaseService();
    addTearDown(store.dispose);
    final ads = FakeAdService(
      consent: const UmpStatus(
        consent: ConsentStatus.obtained,
        privacyOptionsRequired: false,
      ),
    );

    await _pumpApp(tester, api: api, store: store, ads: ads);
    // 아직 비구독자 — 슬롯이 예약돼 있고 배너도 올라왔다.
    expect(find.byType(AdBannerSlot), findsOne);

    store.emit([fakePurchase()]);
    await tester.runAsync(() => tester.pumpAndSettle());
    await tester.pumpAndSettle();

    expect(api.verifiedReceipts, hasLength(1));
    // 서버가 권한을 준 뒤에야 완료한다(스펙 §A.8).
    expect(store.completed, hasLength(1));
    expect(find.byType(AdBannerSlot), findsNothing);
  });
}
