import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_controller.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/notifications/system_notification_settings.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/settings_row.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import '../fakes/fake_api_client.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/fake_permissions.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// S4 의 알림 두 줄(일일 시각 picker · 리마인더 스위치 · 권한 꺼짐 안내).
/// 동기화도 실제로 돌려서 "설정을 바꾸면 예약이 따라간다" 까지 같이 본다.
/// 동기화는 가짜 저장소·예약기 위에서도 **실제 이벤트 루프**에서 돈다
/// (`await` 가 여러 번 있다). 그래서 탭·시작 뒤에 `runAsync` 로 큐를 비워야
/// 예약까지 끝난 상태를 본다.
Future<void> settle(WidgetTester tester) async {
  await tester.runAsync(pumpEventQueue);
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late tz.Location seoul;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
  });

  late FakeNotificationScheduler scheduler;
  late InMemoryNotificationSettingsStore settings;
  late FakeNotificationPermissionRequester permission;
  late NotificationTaps taps;
  late List<String> openedSettings;

  setUp(() {
    scheduler = FakeNotificationScheduler();
    settings = InMemoryNotificationSettingsStore();
    permission = FakeNotificationPermissionRequester(
      currentResult: NotificationPermission.granted,
    );
    taps = NotificationTaps(launchedByNotification: false);
    openedSettings = [];
    addTearDown(taps.dispose);
  });

  Future<void> pumpRecords(
    WidgetTester tester, {
    Size size = const Size(390, 844),
    Locale locale = const Locale('ko'),
  }) async {
    setViewSize(tester, size);
    await tester.runAsync(() async {
      await tester.pumpWidget(
        ProviderScope(
          retry: noAutoRetry,
          overrides: [
            apiClientProvider.overrideWithValue(FakeApiClient()),
            startupStatsProvider.overrideWithValue(fakeMyStats()),
            appVersionProvider.overrideWith((ref) async => '1.0.0'),
            notificationSchedulerProvider.overrideWithValue(scheduler),
            notificationSettingsStoreProvider.overrideWithValue(settings),
            completedPuzzleDateStoreProvider.overrideWithValue(
              InMemoryCompletedPuzzleDateStore(),
            ),
            deviceTimeZoneProvider.overrideWithValue(
              FakeDeviceTimeZone(seoul),
            ),
            notificationPermissionRequesterProvider.overrideWithValue(
              permission,
            ),
            notificationBootstrapProvider.overrideWithValue(
              NotificationBootstrap(available: true, taps: taps),
            ),
            openNotificationSettingsProvider.overrideWithValue(() async {
              openedSettings.add('notification');
            }),
          ],
          child: AppLocalizationScope(
            startLocale: locale,
            child: Builder(
              builder: (context) => MaterialApp(
                theme: appTheme(Brightness.light),
                locale: context.locale,
                supportedLocales: context.supportedLocales,
                localizationsDelegates: context.localizationDelegates,
                home: const Scaffold(
                  body: Column(
                    children: [
                      SizedBox(height: 0, child: _LiveNotificationSync()),
                      Expanded(child: RecordsTab()),
                    ],
                  ),
                ),
              ),
            ),
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

  Finder row(Key key) => find.byKey(key);

  /// picker 안의 한 줄. 뒤에 깔린 설정 행에도 같은 문자열이 있다.
  Finder pickerChoice(String label) => find.descendant(
    of: find.byKey(RecordsSlot.reminderPicker),
    matching: find.text(label),
  );

  Future<void> scrollPickerTo(WidgetTester tester, String label) =>
      tester.scrollUntilVisible(
        pickerChoice(label),
        200,
        scrollable: find.descendant(
          of: find.byKey(RecordsSlot.reminderPicker),
          matching: find.byType(Scrollable),
        ),
      );

  group('일일 알림 시각', () {
    testWidgets('저장된 시각이 행에 보인다', (tester) async {
      settings.settings = const NotificationSettings(
        dailyTime: TimeOfDay(hour: 7, minute: 30),
      );

      await pumpRecords(tester);

      expect(
        tester.widget<SettingsRow>(row(RecordsSlot.dailyNotification)).value,
        '오전 7:30',
      );
    });

    testWidgets('picker 에서 고른 시각이 저장되고 예약이 따라간다', (tester) async {
      await pumpRecords(tester);
      expect(scheduler.pending, contains(NotificationPlan.dailyId));

      await tapAndSettle(tester, row(RecordsSlot.dailyNotification));
      await scrollPickerTo(tester, '오후 9:00');
      await tapAndSettle(tester, pickerChoice('오후 9:00'));

      expect(settings.settings.dailyTime, const TimeOfDay(hour: 21, minute: 0));
      expect(
        tester.widget<SettingsRow>(row(RecordsSlot.dailyNotification)).value,
        '오후 9:00',
      );
      final daily = scheduler.scheduled.lastWhere(
        (entry) => entry.kind == NotificationKind.daily,
      );
      expect(daily.when.hour, 21);
    });

    testWidgets('같은 시각을 다시 골라도 쓰지 않는다', (tester) async {
      await pumpRecords(tester);

      await tapAndSettle(tester, row(RecordsSlot.dailyNotification));
      await tapAndSettle(tester, pickerChoice('오전 9:00'));

      expect(settings.writes, 0);
    });

    testWidgets('폭 744 에서는 바텀시트가 아니라 다이얼로그로 뜬다', (tester) async {
      await pumpRecords(tester, size: const Size(744, 1133));

      await tapAndSettle(tester, row(RecordsSlot.dailyNotification));

      expect(find.byType(Dialog), findsOneWidget);
      expect(find.byType(BottomSheet), findsNothing);
      expect(pickerChoice('오전 9:00'), findsOneWidget);
    });
  });

  group('리마인더 스위치', () {
    testWidgets('끄면 저장되고 걸려 있던 리마인더가 취소된다', (tester) async {
      await pumpRecords(tester);
      expect(scheduler.pendingReminders, hasLength(7));

      await tapAndSettle(tester, find.byType(Switch));

      expect(settings.settings.reminderEnabled, isFalse);
      expect(scheduler.pendingReminders, isEmpty);
    });

    testWidgets('스위치는 저장된 값으로 그려진다', (tester) async {
      settings.settings = const NotificationSettings(reminderEnabled: false);

      await pumpRecords(tester);

      expect(tester.widget<Switch>(find.byType(Switch)).value, isFalse);
      expect(scheduler.pendingReminders, isEmpty);
    });
  });

  group('권한 꺼짐 안내', () {
    testWidgets('권한이 허용이면 안내가 없다', (tester) async {
      await pumpRecords(tester);

      expect(row(RecordsSlot.notificationOff), findsNothing);
    });

    testWidgets('거부면 안내가 뜨고 누르면 시스템 알림 설정을 연다', (tester) async {
      permission.currentResult = NotificationPermission.denied;

      await pumpRecords(tester);

      expect(find.text('알림 꺼짐 — 시스템 설정에서 켜기'), findsOneWidget);
      // 못 뜰 알림을 걸어두지 않는다.
      expect(scheduler.pending, isEmpty);

      await tapAndSettle(tester, row(RecordsSlot.notificationOff));

      expect(openedSettings, ['notification']);
    });

    testWidgets('아직 묻지 않은 상태도 같은 안내를 쓴다', (tester) async {
      // Android 는 "안 물어봤다" 와 "거부" 가 구분되지 않는다 — 두 경우 모두
      // 사용자가 할 수 있는 일은 시스템 설정에서 켜는 것뿐이다.
      permission.currentResult = NotificationPermission.notDetermined;

      await pumpRecords(tester);

      expect(find.text('알림 꺼짐 — 시스템 설정에서 켜기'), findsOneWidget);
    });
  });

  testWidgets('영어 UI 에서도 같은 두 줄이 보인다', (tester) async {
    permission.currentResult = NotificationPermission.denied;

    await pumpRecords(tester, locale: const Locale('en'));

    expect(
      tester.widget<SettingsRow>(row(RecordsSlot.dailyNotification)).value,
      '9:00 AM',
    );
    expect(find.text('Nudge if unsolved'), findsOneWidget);
    expect(
      find.text('Notifications are off — turn them on in system settings'),
      findsOneWidget,
    );
  });
}

/// 앱에서는 `ChosungApp` 이 동기화를 살려 둔다(화면이 아니라 앱 수명에 매달려
/// 있다). 탭 하나만 띄우는 테스트에서는 이 자리가 그 역할을 한다.
class _LiveNotificationSync extends ConsumerWidget {
  const _LiveNotificationSync();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen(notificationSyncProvider, (_, _) {});
    return const SizedBox.shrink();
  }
}
