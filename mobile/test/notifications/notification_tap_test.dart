import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import '../fakes/fake_api_client.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 알림 탭 처리(US 40). 실행 중이든 종료 상태에서 켜졌든 **오늘 탭 + 최신
/// 퍼즐**이어야 한다. 라우팅이 걸린 자리라 실제 앱 트리와 라우터로 본다.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late tz.Location seoul;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
  });

  late FakeApiClient api;
  late NotificationTaps taps;

  setUp(() {
    api = FakeApiClient();
  });

  Future<void> pumpApp(
    WidgetTester tester, {
    required bool launchedByNotification,
  }) async {
    taps = NotificationTaps(launchedByNotification: launchedByNotification);
    addTearDown(taps.dispose);
    setViewSize(tester, const Size(390, 844));
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
            notificationSchedulerProvider.overrideWithValue(
              FakeNotificationScheduler(),
            ),
            notificationSettingsStoreProvider.overrideWithValue(
              InMemoryNotificationSettingsStore(),
            ),
            completedPuzzleDateStoreProvider.overrideWithValue(
              InMemoryCompletedPuzzleDateStore(),
            ),
            deviceTimeZoneProvider.overrideWithValue(
              FakeDeviceTimeZone(seoul),
            ),
            notificationPermissionRequesterProvider.overrideWithValue(
              FakeNotificationPermissionRequester(
                currentResult: NotificationPermission.granted,
              ),
            ),
            notificationBootstrapProvider.overrideWithValue(
              NotificationBootstrap(available: true, taps: taps),
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
    await settle(tester);
  }

  Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
    await tester.runAsync(() async {
      await tester.tap(finder);
      await tester.pump();
    });
    await settle(tester);
  }

  testWidgets('다른 탭에 있다가 알림을 탭하면 오늘 탭으로 가고 퍼즐을 다시 읽는다', (tester) async {
    await pumpApp(tester, launchedByNotification: false);
    await tapAndSettle(tester, find.text('내 기록'));
    expect(find.byType(RecordsTab), findsOneWidget);
    final readsBeforeTap = api.fetchTodayPuzzleCalls;

    taps.add();
    await settle(tester);

    expect(find.byType(TodayTab), findsOneWidget);
    expect(find.byType(RecordsTab), findsNothing);
    expect(find.byType(PuzzleBoard), findsOneWidget);
    expect(api.fetchTodayPuzzleCalls, readsBeforeTap + 1);
  });

  testWidgets('종료 상태에서 알림으로 켜지면 오늘 탭에서 시작한다', (tester) async {
    await pumpApp(tester, launchedByNotification: true);

    expect(find.byType(TodayTab), findsOneWidget);
    expect(find.byType(PuzzleBoard), findsOneWidget);
    // 시작 조회가 이미 최신 퍼즐을 가져온다 — 같은 조회를 또 띄우지 않는다.
    expect(api.fetchTodayPuzzleCalls, 1);
  });
}

/// 동기화·라우팅이 실제 이벤트 루프에서 끝나도록 큐를 비운다.
Future<void> settle(WidgetTester tester) async {
  await tester.runAsync(pumpEventQueue);
  await tester.pumpAndSettle();
}
