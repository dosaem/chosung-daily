import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/settings_row.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_permissions.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// S4 의 "광고 개인정보 설정" 행만 본다(27 이 자리를 만들고 31 이 채운다).
Future<void> pumpRecords(
  WidgetTester tester, {
  required FakeAdService ads,
  required bool privacyOptionsRequired,
  bool? entitled = false,
}) async {
  setViewSize(tester, const Size(390, 844));
  ads.consent = UmpStatus(
    consent: ConsentStatus.obtained,
    privacyOptionsRequired: privacyOptionsRequired,
  );

  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(FakeApiClient()),
          appVersionProvider.overrideWith((ref) async => '1.2.3'),
          isIosProvider.overrideWithValue(false),
          trackingAuthorizationProvider.overrideWithValue(
            FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
          ),
          adServiceProvider.overrideWithValue(ads),
          entitlementProvider.overrideWith(
            () => FakeEntitlement(initial: entitled),
          ),
        ],
        child: AppLocalizationScope(
          startLocale: const Locale('ko'),
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

void main() {
  testWidgets('EEA 면 행이 뜨고 누르면 UMP 폼을 띄운다 (US 34)', (tester) async {
    final ads = FakeAdService();

    await pumpRecords(tester, ads: ads, privacyOptionsRequired: true);

    final row = find.byKey(RecordsSlot.adPrivacy);
    expect(row, findsOne);
    expect(find.text('광고 개인정보 설정'), findsOne);
    // 27 이 남긴 "준비 중" 문구는 사라진다.
    expect(tester.widget<SettingsRow>(row).value, isNull);

    await tester.tap(row);
    await tester.pumpAndSettle();

    expect(ads.privacyOptionsForms, 1);
  });

  testWidgets('required 가 아니면 행 자체가 없다', (tester) async {
    final ads = FakeAdService();

    await pumpRecords(tester, ads: ads, privacyOptionsRequired: false);

    expect(find.byKey(RecordsSlot.adPrivacy), findsNothing);
    expect(find.text('광고 개인정보 설정'), findsNothing);
  });

  // 광고가 없는 구독자라도 받은 동의는 바꿀 수 있어야 한다.
  testWidgets('구독자도 EEA 면 행이 남는다', (tester) async {
    final ads = FakeAdService();

    await pumpRecords(
      tester,
      ads: ads,
      privacyOptionsRequired: true,
      entitled: true,
    );

    expect(find.byKey(RecordsSlot.adPrivacy), findsOne);
  });
}
