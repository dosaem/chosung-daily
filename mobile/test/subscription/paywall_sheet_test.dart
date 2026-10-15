import 'dart:async';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_sheet.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/paywall_sheet.dart';
import 'package:chosung/subscription/purchase_controller.dart';
import 'package:chosung/subscription/subscription_state.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_purchase_service.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// S5 를 실제로 `showAdaptiveSheet` 로 띄운다 — 폭에 따른 시트/다이얼로그
/// 분기(SCREENS T2)까지 같은 길로 보려면 위젯만 pump 해서는 안 된다.
Future<void> _openPaywall(
  WidgetTester tester, {
  required FakeApiClient api,
  required FakePurchaseService store,
  required NoopAnalyticsService analytics,
  required List<String> openedUrls,
  Entitlement? entitlement,
  Size size = const Size(390, 844),
  Locale locale = const Locale('ko'),
}) async {
  setViewSize(tester, size);

  await tester.runAsync(() async {
    await tester.pumpWidget(
      _harness(
        api: api,
        store: store,
        analytics: analytics,
        openedUrls: openedUrls,
        entitlement: entitlement,
        locale: locale,
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
  await tester.tap(find.text('열기'));
  await tester.pumpAndSettle();
}

Widget _harness({
  required FakeApiClient api,
  required FakePurchaseService store,
  required NoopAnalyticsService analytics,
  required List<String> openedUrls,
  required Entitlement? entitlement,
  required Locale locale,
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    purchaseServiceProvider.overrideWithValue(store),
    analyticsServiceProvider.overrideWithValue(analytics),
    webLinkLauncherProvider.overrideWithValue((url) async {
      openedUrls.add(url);
    }),
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
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () => showPaywallSheet(context: context),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  ),
);

void main() {
  late FakeApiClient api;
  late FakePurchaseService store;
  late NoopAnalyticsService analytics;
  late List<String> openedUrls;

  setUp(() {
    api = FakeApiClient();
    store = FakePurchaseService();
    analytics = NoopAnalyticsService();
    openedUrls = [];
  });

  tearDown(() => store.dispose());

  Future<void> open(
    WidgetTester tester, {
    Entitlement? entitlement,
    Size size = const Size(390, 844),
    Locale locale = const Locale('ko'),
  }) => _openPaywall(
    tester,
    api: api,
    store: store,
    analytics: analytics,
    openedUrls: openedUrls,
    entitlement: entitlement,
    size: size,
    locale: locale,
  );

  testWidgets('S5: 제목·혜택 3줄·가격 카드·구독 시작·구매 복원·링크', (tester) async {
    await open(tester);

    expect(find.text('광고 없이, 매일 30초'), findsOne);
    expect(find.text('배너·전면 광고 제거'), findsOne);
    // 스펙 §B.21 이 못 박은 문구다.
    expect(find.text('광고 없이 힌트 미리 보기'), findsOne);
    expect(find.text('어느 기기에서든 유지'), findsOne);
    // 가격 카드는 SCREENS S5 의 "월 {스토어 현지화 가격}" — 가격 문자열
    // 자체는 스토어가 알려준 것 그대로다(상수 금지).
    expect(find.text('월 ₩1,500'), findsOne);
    expect(find.byKey(PaywallKeys.start), findsOne);
    expect(find.byKey(PaywallKeys.restore), findsOne);
    expect(find.text('이용약관'), findsOne);
    expect(find.text('개인정보처리방침'), findsOne);
  });

  testWidgets('자동 갱신 고지의 필수 요소 6개가 다 있다 (legal-checklist "4.")', (
    tester,
  ) async {
    await open(tester);

    for (final element in const [
      PaywallKeys.productName, // 상품명
      PaywallKeys.period, // 기간(결제 주기)
      PaywallKeys.price, // 가격
      PaywallKeys.autoRenew, // 자동 갱신 조건
      PaywallKeys.cancelHow, // 해지 방법
      PaywallKeys.legalLinks, // 약관·개인정보처리방침 링크
    ]) {
      expect(find.byKey(element), findsOne, reason: '$element 고지가 없다');
    }

    // 문구는 웹 약관 `terms#subscription` 과 같은 말을 쓴다(티켓 16).
    expect(find.textContaining('광고 제거 구독'), findsOne);
    expect(find.textContaining('1개월'), findsOne);
    expect(find.textContaining('24시간'), findsOne);
    expect(find.textContaining('Apple 계정 > 구독'), findsOne);
    expect(find.textContaining('Google Play > 구독'), findsOne);
  });

  testWidgets('영어 UI 는 영문 약관과 같은 표현을 쓴다', (tester) async {
    await open(tester, locale: const Locale('en'));

    expect(find.text('No ads, 30 seconds a day'), findsOne);
    expect(find.textContaining('Ad-free subscription'), findsOne);
    expect(find.textContaining('automatically renews'), findsOne);
    expect(find.textContaining('24 hours'), findsOne);
    expect(find.textContaining('Google Play > Subscriptions'), findsOne);
    expect(find.text('₩1,500 / month'), findsOne);
    expect(find.text('Restore purchases'), findsOne);
  });

  testWidgets('진입에 paywall_view, 구독 시작 탭에 subscribe_start 를 찍는다', (
    tester,
  ) async {
    await open(tester);

    expect(analytics.logged.map((event) => event.name), ['paywall_view']);

    await tester.tap(find.byKey(PaywallKeys.start));
    await tester.pumpAndSettle();

    expect(analytics.logged.map((event) => event.name), [
      'paywall_view',
      'subscribe_start',
    ]);
    expect(store.bought.single.id, adFreeMonthlyProductId);
  });

  testWidgets('pending 이면 구독 시작이 비활성이고 "결제 확인 중" 이 뜬다', (tester) async {
    await open(tester);

    store.emit([fakePurchase(status: PurchaseStatus.pending)]);
    await tester.pumpAndSettle();

    expect(find.text('결제 확인 중'), findsOne);
    expect(
      tester.widget<FilledButton>(find.byKey(PaywallKeys.start)).onPressed,
      isNull,
    );
    // 복원도 같이 잠근다 — 결제 중에 복원을 걸면 같은 영수증이 두 길로 온다.
    expect(
      tester.widget<TextButton>(find.byKey(PaywallKeys.restore)).onPressed,
      isNull,
    );
  });

  testWidgets('서버 검증 중에도 버튼이 잠긴다', (tester) async {
    await open(tester);
    final gate = api.verifySubscriptionGate = Completer<void>();

    store.emit([fakePurchase()]);
    await tester.pumpAndSettle();

    expect(find.text('결제 확인 중'), findsOne);
    expect(
      tester.widget<FilledButton>(find.byKey(PaywallKeys.start)).onPressed,
      isNull,
    );

    gate.complete();
    await tester.pumpAndSettle();
  });

  testWidgets('구매 복원이 성공하면 권한이 들어오고 확인 화면으로 바뀐다', (tester) async {
    await open(tester);
    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );
    // 재설치 뒤 스토어에 살아 있는 구독. 시작 때의 자동 동기화는 빈손이었다.
    store.restorable = [fakePurchase(status: PurchaseStatus.restored)];

    await tester.tap(find.byKey(PaywallKeys.restore));
    await tester.pumpAndSettle();

    expect(api.verifiedReceipts, hasLength(1));
    expect(find.byKey(PaywallKeys.entitled), findsOne);
    expect(find.text('광고가 꺼졌어요'), findsOne);
    expect(find.byKey(PaywallKeys.start), findsNothing);
  });

  testWidgets('구매가 끝나면 갱신일과 함께 확인 화면이 뜬다', (tester) async {
    await open(tester);
    api.verifyResponse = fakeEntitlement(
      active: true,
      until: DateTime.utc(2026, 11),
    );

    store.emit([fakePurchase()]);
    await tester.pumpAndSettle();

    expect(find.byKey(PaywallKeys.entitled), findsOne);
    expect(
      find.textContaining(
        DateFormat.yMMMd('ko').format(DateTime.utc(2026, 11).toLocal()),
      ),
      findsOne,
    );
  });

  testWidgets('검증이 실패하면 사유를 버튼 아래 한 줄로 둔다 (토스트 금지)', (tester) async {
    await open(tester);
    api.verifySubscriptionError = const StoreUnavailableApiException(
      code: 'STORE_UNAVAILABLE',
      message: '스토어에 연결할 수 없습니다.',
    );

    store.emit([fakePurchase()]);
    await tester.pumpAndSettle();

    expect(find.byKey(PaywallKeys.error), findsOne);
    expect(find.text('스토어에 연결하지 못했어요. 잠시 뒤 다시 시도해주세요'), findsOne);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('가격을 못 읽으면 구독 시작을 잠근다', (tester) async {
    store.product = null;
    await open(tester);

    expect(find.text('가격을 불러오는 중…'), findsOne);
    expect(
      tester.widget<FilledButton>(find.byKey(PaywallKeys.start)).onPressed,
      isNull,
    );
  });

  testWidgets('약관·방침 링크는 UI 언어로 웹 문서를 연다', (tester) async {
    await open(tester, locale: const Locale('en'));

    // 고지가 길어 링크는 시트 아래쪽에 있다 — 실제 사용자처럼 먼저 스크롤한다.
    await tester.ensureVisible(find.text('Terms of service'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Terms of service'));
    await tester.pumpAndSettle();

    expect(openedUrls.single, endsWith('/terms?lang=en'));
  });

  testWidgets('태블릿 폭(744)에서는 가운데 다이얼로그로 뜬다 (SCREENS T2)', (tester) async {
    await open(tester, size: const Size(744, 1133));

    expect(find.byType(Dialog), findsOne);
    expect(find.byType(BottomSheet), findsNothing);
    expect(find.text('광고 없이, 매일 30초'), findsOne);
    expect(
      tester.getSize(find.byKey(PaywallKeys.price)).width,
      lessThanOrEqualTo(AdaptiveSheet.maxDialogWidth),
    );
  });
}
