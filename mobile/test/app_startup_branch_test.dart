import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/screens/home_shell.dart';
import 'package:chosung/screens/maintenance_screen.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/splash_screen.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/screens/update_required_screen.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/widgets/ad_banner_slot.dart';
import 'package:chosung/widgets/max_width_body.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fakes/fake_api_client.dart';
import 'fakes/in_memory_guest_token_store.dart';

/// 실제 앱 트리(ProviderScope → EasyLocalization → ChosungApp)를 띄우고,
/// 서버 경계(`ApiClient`)와 secure storage 만 가짜로 바꾼다.
Future<void> _pumpApp(
  WidgetTester tester, {
  required FakeApiClient api,
  GuestTokenStore? store,
  String appVersion = '1.0.0',
  bool isIos = true,
  Locale locale = const Locale('ko'),
  Future<void> Function(String url)? storeLauncher,
}) async {
  // 번역 JSON 은 rootBundle 에서 실제로 읽어온다 — runAsync 안에서 첫 프레임을
  // 돌려야 그 Future 가 완료된다(두 번째 테스트부터 멈추는 걸 막는다).
  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          guestTokenStoreProvider.overrideWithValue(
            store ?? InMemoryGuestTokenStore('guest-token'),
          ),
          appVersionProvider.overrideWith((_) async => appVersion),
          isIosProvider.overrideWithValue(isIos),
          if (storeLauncher != null)
            storeLauncherProvider.overrideWithValue(storeLauncher),
        ],
        child: AppLocalizationScope(
          startLocale: locale,
          child: const ChosungApp(),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 탭 뒤에도 runAsync 가 필요하다 — 가짜 ApiClient 의 Future 는 실제 이벤트
/// 루프에서 완료되므로 pumpAndSettle 만으로는 상태 변화가 들어오지 않는다.
Future<void> _tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('점검 중이면 점검 화면이 뜬다', (tester) async {
    final api = FakeApiClient(
      config: fakeAppConfig(maintenance: true, maintenanceMessage: '오전 3시까지'),
    );

    await _pumpApp(tester, api: api);

    expect(find.byType(MaintenanceScreen), findsOne);
    expect(find.text('잠시 점검 중이에요'), findsOne);
    expect(find.text('오전 3시까지'), findsOne);
    expect(find.byType(HomeShell), findsNothing);
  });

  testWidgets('점검 메시지가 없으면 기본 안내를 보여준다', (tester) async {
    final api = FakeApiClient(config: fakeAppConfig(maintenance: true));

    await _pumpApp(tester, api: api);

    expect(find.text('조금 뒤에 다시 열어주세요.'), findsOne);
  });

  testWidgets('구버전이면 업데이트 화면 + 스토어 버튼이 뜬다', (tester) async {
    final api = FakeApiClient(
      config: fakeAppConfig(minIos: '2.0.0', storeUrlIos: 'https://store/ios'),
    );
    final opened = <String>[];

    await _pumpApp(
      tester,
      api: api,
      storeLauncher: (url) async => opened.add(url),
    );

    expect(find.byType(UpdateRequiredScreen), findsOne);
    expect(find.text('새 버전이 필요해요'), findsOne);

    await tester.tap(find.text('스토어로 이동'));
    await tester.pumpAndSettle();

    expect(opened, ['https://store/ios']);
  });

  testWidgets('스토어 링크가 없으면 버튼을 그리지 않는다', (tester) async {
    final api = FakeApiClient(config: fakeAppConfig(minIos: '2.0.0'));

    await _pumpApp(tester, api: api);

    expect(find.byType(UpdateRequiredScreen), findsOne);
    expect(find.text('스토어로 이동'), findsNothing);
  });

  testWidgets('정상이면 3탭 홈과 배너 슬롯이 뜬다', (tester) async {
    final api = FakeApiClient(
      stats: fakeMyStats(currentStreak: 3, maxStreak: 7, solvedCount: 21),
    );

    await _pumpApp(tester, api: api);

    expect(find.byType(HomeShell), findsOne);
    expect(find.byType(TodayTab), findsOne);
    expect(find.text('오늘'), findsOne);
    expect(find.text('순위'), findsOne);
    expect(find.text('내 기록'), findsOne);
    // 배너 자리는 로드 전에도 높이를 예약한다(OVERRIDES §5).
    expect(find.byType(AdBannerSlot), findsOne);
    expect(
      tester.getSize(find.byType(AdBannerSlot)).height,
      AdBannerSlot.reservedHeight + AdBannerSlot.contentGap,
    );
  });

  testWidgets('탭을 옮기면 해당 탭이 보인다', (tester) async {
    await _pumpApp(tester, api: FakeApiClient());

    await tester.tap(find.text('순위'));
    await tester.pumpAndSettle();
    expect(find.byType(RankingTab), findsOne);

    await tester.tap(find.text('내 기록'));
    await tester.pumpAndSettle();
    expect(find.byType(RecordsTab), findsOne);
  });

  testWidgets('내 기록 탭은 시작할 때 읽은 streak 을 보여준다', (tester) async {
    final api = FakeApiClient(
      stats: fakeMyStats(currentStreak: 3, maxStreak: 7, solvedCount: 21),
    );

    await _pumpApp(tester, api: api);
    await tester.tap(find.text('내 기록'));
    await tester.pumpAndSettle();

    expect(find.text('3일'), findsOne);
    expect(find.text('7일'), findsOne);
    expect(find.text('21문제'), findsOne);
  });

  testWidgets('기기 언어가 en 이면 UI 문구가 영어로 나온다', (tester) async {
    final api = FakeApiClient(config: fakeAppConfig(maintenance: true));

    await _pumpApp(tester, api: api, locale: const Locale('en'));

    expect(find.text("We're under maintenance"), findsOne);
  });

  testWidgets('/config 가 실패하면 스플래시에 에러 카드와 재시도가 남는다', (tester) async {
    final api = FakeApiClient()
      ..fetchConfigError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );

    await _pumpApp(tester, api: api);

    expect(find.byType(SplashScreen), findsOne);
    expect(find.text('연결할 수 없어요'), findsOne);

    api.fetchConfigError = null;
    await _tapAndSettle(tester, find.text('다시 시도'));

    expect(find.byType(HomeShell), findsOne);
  });

  testWidgets('토큰이 없으면 게스트를 발급하고 홈으로 간다', (tester) async {
    final api = FakeApiClient(nextGuestToken: 'issued');
    final store = InMemoryGuestTokenStore();

    await _pumpApp(tester, api: api, store: store);

    expect(api.createGuestCalls, 1);
    expect(store.token, 'issued');
    expect(find.byType(HomeShell), findsOne);
  });

  testWidgets('다크 모드에서도 같은 토큰으로 그린다', (tester) async {
    tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
    addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

    await _pumpApp(tester, api: FakeApiClient());

    final context = tester.element(find.byType(TodayTab));
    expect(Theme.of(context).brightness, Brightness.dark);
    expect(AppColors.from(context), AppColors.dark);
    expect(
      Theme.of(context).scaffoldBackgroundColor,
      AppColors.dark.background,
    );
  });

  // 시스템 글자 크기를 키웠을 때 레이아웃이 넘치면 위젯 테스트가 바로 실패한다
  // (RenderFlex overflow 는 FlutterError 로 잡힌다). audit.native 접근성 항목.
  testWidgets('글자 크기를 1.3배로 키워도 넘치지 않는다', (tester) async {
    tester.platformDispatcher.textScaleFactorTestValue = 1.3;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    await _pumpApp(
      tester,
      api: FakeApiClient(
        stats: fakeMyStats(currentStreak: 3, maxStreak: 7, solvedCount: 21),
      ),
    );

    expect(find.byType(HomeShell), findsOne);
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(find.byType(RecordsTab), findsOne);
  });

  testWidgets('접근성 레이블이 탭마다 붙어 있다', (tester) async {
    final handle = tester.ensureSemantics();

    await _pumpApp(tester, api: FakeApiClient());

    // 탭은 "오늘\nTab 1 of 3" 처럼 상태까지 합쳐 읽히므로 부분 일치로 본다.
    expect(find.bySemanticsLabel(RegExp('오늘')), findsWidgets);
    expect(find.bySemanticsLabel(RegExp('순위')), findsOne);
    expect(find.bySemanticsLabel(RegExp('내 기록')), findsOne);

    handle.dispose();
  });

  testWidgets('본문은 600px 를 넘지 않는다 (iPad)', (tester) async {
    tester.view.physicalSize = const Size(1668, 2388);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);

    await _pumpApp(tester, api: FakeApiClient());

    expect(tester.getSize(find.byType(TodayTab)).width, 834);
    final body = find.descendant(
      of: find.byType(MaxWidthBody),
      matching: find.byType(ConstrainedBox),
    );
    expect(tester.getSize(body.first).width, MaxWidthBody.maxWidth);
  });
}
