import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/banner_ad_view.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';

/// 실제 앱 트리를 띄우고 서버·기기·광고 경계만 가짜로 바꾼다 — 배너 슬롯은
/// 셸(`AdaptiveScaffold`)이 들고 있어서 셸 밖에서 재현하면 "슬롯 자체 제거" 를
/// 증명할 수 없다.
Future<void> pumpApp(
  WidgetTester tester, {
  required FakeAdService ads,
  bool? entitled = false,
  UmpStatus? consent = const UmpStatus(
    consent: ConsentStatus.obtained,
    privacyOptionsRequired: false,
  ),
  Size size = const Size(390, 844),
}) async {
  tester.view
    ..physicalSize = size
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  ads.consent = consent ?? const UmpStatus.failed();

  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          // 서버도 같은 권한을 말해야 한다 — 티켓 33 의 재확인이 시작
          // `/me/stats` 응답으로 `entitlementProvider` 를 덮는다.
          apiClientProvider.overrideWithValue(
            FakeApiClient(stats: fakeMyStats(entitled: entitled ?? false)),
          ),
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
          entitlementProvider.overrideWith(
            () => FakeEntitlement(initial: entitled),
          ),
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

double slotHeight(WidgetTester tester) =>
    tester.getSize(find.byType(AdBannerSlot)).height;

void main() {
  testWidgets('동의한 비구독자는 슬롯 폭으로 배너를 로드한다', (tester) async {
    final ads = FakeAdService();

    await pumpApp(tester, ads: ads);
    await tester.runAsync(() => tester.pumpAndSettle());

    expect(find.byType(AdBannerSlot), findsOne);
    expect(ads.bannerWidths, hasLength(1));
    // 폰은 콘텐츠 열 = 화면 폭이다.
    expect(ads.bannerWidths.single, 390);
    expect(find.byKey(const Key('fake-banner')), findsOne);
  });

  testWidgets('구독자는 배너 슬롯 자체가 없다 (US 31)', (tester) async {
    final ads = FakeAdService();

    await pumpApp(tester, ads: ads, entitled: true);

    expect(find.byType(AdBannerSlot), findsNothing);
    expect(ads.bannerWidths, isEmpty);
  });

  testWidgets('동의를 안 했으면 자리는 예약하고 광고는 요청하지 않는다', (tester) async {
    final ads = FakeAdService();

    await pumpApp(
      tester,
      ads: ads,
      consent: const UmpStatus(
        consent: ConsentStatus.required,
        privacyOptionsRequired: true,
      ),
    );

    expect(find.byType(AdBannerSlot), findsOne);
    expect(
      slotHeight(tester),
      AdBannerSlot.reservedHeight + AdBannerSlot.contentGap,
    );
    expect(ads.bannerWidths, isEmpty);
  });

  testWidgets('로드가 실패해도 예약 높이는 그대로다', (tester) async {
    final ads = FakeAdService(bannerLoads: false);

    await pumpApp(tester, ads: ads);
    await tester.runAsync(() => tester.pumpAndSettle());

    expect(ads.bannerWidths, hasLength(1));
    expect(find.byKey(const Key('fake-banner')), findsNothing);
    expect(
      slotHeight(tester),
      AdBannerSlot.reservedHeight + AdBannerSlot.contentGap,
    );
  });

  // SCREENS T0: 배너는 rail 을 뺀 콘텐츠 열 폭으로 요청한다.
  testWidgets('태블릿은 rail 을 뺀 콘텐츠 열 폭으로 요청한다', (tester) async {
    final ads = FakeAdService();

    await pumpApp(tester, ads: ads, size: const Size(1024, 768));
    await tester.runAsync(() => tester.pumpAndSettle());

    expect(ads.bannerWidths, hasLength(1));
    expect(ads.bannerWidths.single, lessThan(1024));
    expect(
      ads.bannerWidths.single,
      tester.getSize(find.byType(BannerAdView)).width,
    );
    expect(
      slotHeight(tester),
      AdBannerSlot.tabletReservedHeight + AdBannerSlot.contentGap,
    );
  });

  testWidgets('회전으로 폭이 바뀌면 새 폭으로 한 번만 다시 요청한다', (tester) async {
    final ads = FakeAdService();

    await pumpApp(tester, ads: ads, size: const Size(1024, 1366));
    await tester.runAsync(() => tester.pumpAndSettle());
    final before = slotHeight(tester);

    tester.view.physicalSize = const Size(1366, 1024);
    await tester.runAsync(() => tester.pumpAndSettle());

    // 예약 높이 규칙은 24 를 따른다 — 두 폭 모두 728 이상이라 높이는 그대로다.
    expect(slotHeight(tester), before);
    expect(ads.bannerWidths, hasLength(2));
    expect(ads.bannerWidths[1], greaterThan(ads.bannerWidths[0]));
    // 이전 배너는 버린다 — 안 버리면 네이티브 쪽에 배너가 쌓인다.
    expect(ads.bannerDisposals, 1);
  });
}
