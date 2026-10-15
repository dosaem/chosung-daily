import 'dart:io';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/subscription/paywall_sheet.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_purchase_service.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 목업(`design/stitch/e5_paywall.html`)과 눈으로 대조할 스크린샷. 가격은
/// 가짜 스토어 상품에서 오므로(₩1,500) 골든이 흔들리지 않는다.
///
/// 갱신: `flutter test test/golden --update-goldens`
Future<void> _loadFonts() async {
  final pretendard = FontLoader('Pretendard');
  for (final path in [
    'assets/fonts/Pretendard-Regular.otf',
    'assets/fonts/Pretendard-SemiBold.otf',
    'assets/fonts/Pretendard-Bold.otf',
  ]) {
    pretendard.addFont(
      File(path).readAsBytes().then((bytes) => ByteData.view(bytes.buffer)),
    );
  }
  await pretendard.load();

  final lucide = FontLoader('packages/lucide_icons/Lucide')
    ..addFont(rootBundle.load('packages/lucide_icons/assets/lucide.ttf'));
  await lucide.load();
}

Widget _app({
  required Brightness brightness,
  required FakePurchaseService store,
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(FakeApiClient()),
    purchaseServiceProvider.overrideWithValue(store),
    analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
    webLinkLauncherProvider.overrideWithValue((_) async {}),
  ],
  child: AppLocalizationScope(
    startLocale: const Locale('ko'),
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(brightness),
        debugShowCheckedModeBanner: false,
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: TextButton(
                onPressed: () => showPaywallSheet(context: context),
                child: const Text('구독'),
              ),
            ),
          ),
        ),
      ),
    ),
  ),
);

void main() {
  setUpAll(_loadFonts);

  for (final shot in [
    (name: 'paywall_light_390', size: const Size(390, 844), dark: false),
    (name: 'paywall_dark_390', size: const Size(390, 844), dark: true),
    (name: 'paywall_tablet_744', size: const Size(744, 1024), dark: false),
  ]) {
    testWidgets('골든: ${shot.name}', (tester) async {
      final store = FakePurchaseService();
      addTearDown(store.dispose);
      setViewSize(tester, shot.size);

      await tester.runAsync(() async {
        await tester.pumpWidget(
          _app(
            brightness: shot.dark ? Brightness.dark : Brightness.light,
            store: store,
          ),
        );
        await tester.pump();
      });
      await tester.pumpAndSettle();

      await tester.runAsync(() async {
        await tester.tap(find.text('구독'));
        await tester.pump();
      });
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('${shot.name}.png'),
      );
    });
  }
}
