import 'dart:io';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/fake_permissions.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 목업(`design/stitch/e3_leaderboard.html`·`e4_records.html`)과 태블릿 와이어
/// (SCREENS T3·T4)에 눈으로 대조할 스크린샷을 골든으로 남긴다.
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

/// 21위 밖 내 순위까지 보이는 장면 — S3 의 규칙이 다 들어간다.
FakeApiClient _api() => FakeApiClient(
  leaderboard: fakeLeaderboard(
    entries: [
      fakeLeaderboardEntry(rank: 1, anonTag: 'a3f1'),
      fakeLeaderboardEntry(rank: 2, anonTag: '7b20', seconds: 63),
      fakeLeaderboardEntry(
        rank: 3,
        anonTag: '1c08',
        attempts: 2,
        seconds: 95,
      ),
      fakeLeaderboardEntry(
        rank: 4,
        anonTag: '92de',
        attempts: 3,
        seconds: 188,
      ),
      fakeLeaderboardEntry(
        rank: 5,
        anonTag: '4f61',
        attempts: 3,
        seconds: 402,
      ),
    ],
    me: const MyRank(rank: 23, attempts: 4, seconds: 754),
  ),
  history: fakeHistory(
    results: const [
      {PuzzleLanguage.ko: DayResult.success, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.success, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.fail, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.success, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.success, PuzzleLanguage.en: DayResult.none},
      {
        PuzzleLanguage.ko: DayResult.inProgress,
        PuzzleLanguage.en: DayResult.none,
      },
    ],
  ),
);

Widget _shell({
  required Widget tab,
  required int selectedIndex,
  // S4 알림 행(티켓 30)은 저장된 설정을 읽어 그린다. 권한이 꺼진 장면은
  // 안내 한 줄이 더 붙으므로 따로 한 장 찍는다.
  bool notificationsGranted = true,
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(_api()),
    startupStatsProvider.overrideWithValue(
      fakeMyStats(currentStreak: 12, maxStreak: 30, solvedCount: 41),
    ),
    appVersionProvider.overrideWith((ref) async => '1.0.0'),
    notificationSettingsStoreProvider.overrideWithValue(
      InMemoryNotificationSettingsStore(),
    ),
    notificationPermissionProvider.overrideWith(
      () => FixedNotificationPermissionNotifier(
        notificationsGranted
            ? NotificationPermission.granted
            : NotificationPermission.denied,
      ),
    ),
  ],
  child: AppLocalizationScope(
    startLocale: const Locale('ko'),
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(Brightness.light),
        debugShowCheckedModeBanner: false,
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: AdaptiveScaffold(
          selectedIndex: selectedIndex,
          onDestinationSelected: (_) {},
          destinations: const [
            AdaptiveDestination(icon: LucideIcons.grid, label: '오늘'),
            AdaptiveDestination(icon: LucideIcons.trophy, label: '순위'),
            AdaptiveDestination(icon: LucideIcons.calendar, label: '내 기록'),
          ],
          body: tab,
        ),
      ),
    ),
  ),
);

void main() {
  setUpAll(_loadFonts);

  for (final shot in [
    (
      name: 'ranking_light_390',
      size: const Size(390, 844),
      tab: const RankingTab(),
      index: 1,
    ),
    (
      name: 'ranking_tablet_1024',
      size: const Size(1024, 768),
      tab: const RankingTab(),
      index: 1,
    ),
    (
      name: 'records_light_390',
      size: const Size(390, 844),
      tab: const RecordsTab(),
      index: 2,
    ),
    (
      name: 'records_tablet_1024',
      size: const Size(1024, 768),
      tab: const RecordsTab(),
      index: 2,
    ),
  ]) {
    testWidgets('골든: ${shot.name}', (tester) async {
      setViewSize(tester, shot.size);
      await tester.runAsync(() async {
        await tester.pumpWidget(
          _shell(tab: shot.tab, selectedIndex: shot.index),
        );
        await tester.pump();
      });
      await tester.pumpAndSettle();

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('${shot.name}.png'),
      );
    });
  }

  // 권한이 꺼진 S4(티켓 30) — 일일 알림 행 아래에 "알림 꺼짐" 안내가 붙는다.
  testWidgets('골든: records_notification_off_390', (tester) async {
    setViewSize(tester, const Size(390, 844));
    await tester.runAsync(() async {
      await tester.pumpWidget(
        _shell(
          tab: const RecordsTab(),
          selectedIndex: 2,
          notificationsGranted: false,
        ),
      );
      await tester.pump();
    });
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('records_notification_off_390.png'),
    );
  });
}
