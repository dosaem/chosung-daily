import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/paywall_sheet.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/subscription_card.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/fake_purchase_service.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// S4 구독 카드만 본다 — 탭 전체(`records_tab_test.dart`)와 달리 권한 상태를
/// 바꿔 가며 세 얼굴을 확인하는 쪽이다.
Future<void> _pumpRecords(
  WidgetTester tester, {
  required FakeApiClient api,
  required FakePurchaseService store,
  required List<String> openedUrls,
  Entitlement? entitlement,
  Locale locale = const Locale('ko'),
}) async {
  setViewSize(tester, const Size(390, 844));
  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          purchaseServiceProvider.overrideWithValue(store),
          startupStatsProvider.overrideWithValue(fakeMyStats()),
          appVersionProvider.overrideWith((ref) async => '1.2.3'),
          webLinkLauncherProvider.overrideWithValue((url) async {
            openedUrls.add(url);
          }),
          localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
          notificationSettingsStoreProvider.overrideWithValue(
            InMemoryNotificationSettingsStore(),
          ),
          entitlementProvider.overrideWith(
            () => FakeEntitlement(value: entitlement),
          ),
        ],
        child: AppLocalizationScope(
          startLocale: locale,
          child: Builder(
            builder: (context) => MaterialApp(
              theme: appTheme(Brightness.light),
              locale: context.locale,
              supportedLocales: context.supportedLocales,
              localizationsDelegates: context.localizationDelegates,
              home: const Scaffold(body: RecordsTab()),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

Finder _card() => find.byKey(RecordsSlot.subscription);

void main() {
  late FakeApiClient api;
  late FakePurchaseService store;
  late List<String> openedUrls;

  setUp(() {
    api = FakeApiClient();
    store = FakePurchaseService();
    openedUrls = [];
  });

  tearDown(() => store.dispose());

  Future<void> pump(
    WidgetTester tester, {
    Entitlement? entitlement,
    Locale locale = const Locale('ko'),
  }) => _pumpRecords(
    tester,
    api: api,
    store: store,
    openedUrls: openedUrls,
    entitlement: entitlement,
    locale: locale,
  );

  testWidgets('미구독: 스토어 현지화 가격을 보여주고 누르면 Paywall 이 열린다', (tester) async {
    await pump(tester);

    expect(_card(), findsOne);
    expect(find.text('광고 없이 플레이 · 월 ₩1,500'), findsOne);

    await tester.ensureVisible(_card());
    await tester.tap(_card());
    await tester.pumpAndSettle();

    expect(find.byType(PaywallSheet), findsOne);
  });

  testWidgets('가격을 못 읽었으면 금액 없이 안내만 한다', (tester) async {
    store.product = null;
    await pump(tester);

    expect(find.text('광고 없이 플레이'), findsOne);
  });

  testWidgets('구독 중: "광고 제거 · 갱신일" 과 "관리"(스토어로)', (tester) async {
    await pump(
      tester,
      entitlement: fakeEntitlement(
        active: true,
        until: DateTime.utc(2026, 10, 31),
        source: SubscriptionStore.apple,
      ),
    );

    final date = DateFormat.yMMMd(
      'ko',
    ).format(DateTime.utc(2026, 10, 31).toLocal());
    expect(find.text('광고 제거 · $date 갱신'), findsOne);

    await tester.ensureVisible(find.byKey(manageSubscriptionKey));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(manageSubscriptionKey));
    await tester.pumpAndSettle();

    // 기기 플랫폼이 아니라 **권한이 온 스토어**로 보낸다.
    expect(openedUrls.single, 'https://apps.apple.com/account/subscriptions');
  });

  testWidgets('유예 중: "결제 확인 중 · 유예 …까지"', (tester) async {
    await pump(
      tester,
      entitlement: fakeEntitlement(
        active: true,
        status: SubscriptionStatus.grace,
        until: DateTime.utc(2026, 10, 20),
        source: SubscriptionStore.google,
      ),
    );

    final date = DateFormat.yMMMd(
      'ko',
    ).format(DateTime.utc(2026, 10, 20).toLocal());
    expect(find.text('결제 확인 중 · 유예 $date 까지'), findsOne);

    await tester.ensureVisible(find.byKey(manageSubscriptionKey));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(manageSubscriptionKey));
    await tester.pumpAndSettle();

    expect(
      openedUrls.single,
      'https://play.google.com/store/account/subscriptions',
    );
  });

  testWidgets('보류(hold)는 권한이 없어 미구독 얼굴이다', (tester) async {
    await pump(
      tester,
      entitlement: fakeEntitlement(status: SubscriptionStatus.hold),
    );

    expect(find.text('광고 없이 플레이 · 월 ₩1,500'), findsOne);
    expect(find.byKey(manageSubscriptionKey), findsNothing);
  });

  testWidgets('영어 UI 에서도 같은 세 얼굴이 뜬다', (tester) async {
    await pump(
      tester,
      entitlement: fakeEntitlement(
        active: true,
        until: DateTime.utc(2026, 10, 31),
        source: SubscriptionStore.google,
      ),
      locale: const Locale('en'),
    );

    final date = DateFormat.yMMMd(
      'en',
    ).format(DateTime.utc(2026, 10, 31).toLocal());
    expect(find.text('Ads removed · renews $date'), findsOne);
    expect(find.text('Manage'), findsOne);
  });
}
