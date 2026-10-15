import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/subscription/entitlement_refresh.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';

/// 재확인이 실제로 **화면**을 바꾸는지 본다. 배너 슬롯은 셸
/// (`AdaptiveScaffold`)이 들고 있어서 앱 트리를 통째로 띄워야 "슬롯 자체가
/// 생겼다/사라졌다" 를 증명할 수 있다(`test/ads/banner_slot_gate_test.dart` 와
/// 같은 이유).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late DateTime now;
  late FakeApiClient api;
  late FakeAdService ads;

  const hour = Duration(hours: 1);

  setUp(() {
    now = DateTime.utc(2026, 10, 15, 12);
    api = FakeApiClient();
    ads = FakeAdService(
      consent: const UmpStatus(
        consent: ConsentStatus.obtained,
        privacyOptionsRequired: false,
      ),
    );
  });

  Future<void> pumpApp(WidgetTester tester) async {
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
            clockProvider.overrideWithValue(() => now),
          ],
          child: const AppLocalizationScope(
            startLocale: Locale('ko'),
            child: ChosungApp(),
          ),
        ),
      );
      await tester.pump();
    });
    await tester.runAsync(() => tester.pumpAndSettle());
  }

  /// `next_check_at` 타이머가 깨는 순간에 하는 일 그대로 — `/me/stats` 를 다시
  /// 읽는다.
  ///
  /// 여기서 가짜 시계로 타이머를 터뜨리지 않는 이유: 앱 트리를 띄우려면
  /// `runAsync`(실제 비동기 구역)가 필요한데(`easy_localization` 이 번역 자산을
  /// 읽는다) 그 구역에서 만들어진 `Timer` 는 `tester.pump(간격)` 이 건드리지
  /// 못한다. 타이머가 **정확히 그 시각에** 깨는지는 앱 트리 없이 가짜 시계로
  /// 돌리는 `entitlement_refresh_test.dart` 가 본다.
  Future<void> wakeUp(WidgetTester tester) async {
    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChosungApp)),
    );
    now = now.add(hour);

    await tester.runAsync(() async {
      await container.read(entitlementRefreshProvider.notifier).refresh();
      await tester.pump();
    });
    await tester.runAsync(() => tester.pumpAndSettle());
  }

  testWidgets('권한이 사라지면 배너 슬롯이 돌아오고 배너를 다시 요청한다', (tester) async {
    // 시작 응답은 구독자 — 슬롯이 없다(US 31).
    api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour));

    await pumpApp(tester);

    expect(find.byType(AdBannerSlot), findsNothing);
    expect(ads.bannerWidths, isEmpty);
    expect(api.fetchMyStatsCalls, 1, reason: '시작 때 한 번');

    // 환불이 확인돼 서버가 권한 없음을 돌려주기 시작했다(US 30c).
    api.stats = fakeMyStats();
    await wakeUp(tester);

    expect(api.fetchMyStatsCalls, 2);
    expect(find.byType(AdBannerSlot), findsOne);
    expect(ads.bannerWidths, hasLength(1));
  });

  testWidgets('권한이 생기면 배너 슬롯이 사라지고 배너를 버린다', (tester) async {
    api.stats = fakeMyStats(nextCheckAt: now.add(hour));

    await pumpApp(tester);

    expect(find.byType(AdBannerSlot), findsOne);
    expect(ads.bannerWidths, hasLength(1));

    // 다른 기기에서 구독을 샀다 — 서버가 먼저 안다.
    api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour * 2));
    await wakeUp(tester);

    expect(find.byType(AdBannerSlot), findsNothing);
    // 네이티브 쪽에 배너가 남지 않아야 한다.
    expect(ads.bannerDisposals, 1);
  });

  testWidgets('구독 행이 없으면 시작 응답 뒤로 타이머가 없다', (tester) async {
    await pumpApp(tester);

    expect(find.byType(AdBannerSlot), findsOne);
    expect(api.fetchMyStatsCalls, 1);

    final container = ProviderScope.containerOf(
      tester.element(find.byType(ChosungApp)),
    );
    expect(container.read(entitlementRefreshProvider), isNull);
  });
}
