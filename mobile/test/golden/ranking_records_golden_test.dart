import 'dart:io';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
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
      fakeLeaderboardEntry(rank: 1, display: '게스트 #a3f1'),
      fakeLeaderboardEntry(rank: 2, display: '게스트 #7b20', seconds: 63),
      fakeLeaderboardEntry(
        rank: 3,
        display: '게스트 #1c08',
        attempts: 2,
        seconds: 95,
      ),
      fakeLeaderboardEntry(
        rank: 4,
        display: '게스트 #92de',
        attempts: 3,
        seconds: 188,
      ),
      fakeLeaderboardEntry(
        rank: 5,
        display: '게스트 #4f61',
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

Widget _shell({required Widget tab, required int selectedIndex}) =>
    ProviderScope(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(_api()),
        startupStatsProvider.overrideWithValue(
          fakeMyStats(currentStreak: 12, maxStreak: 30, solvedCount: 41),
        ),
        appVersionProvider.overrideWith((ref) async => '1.0.0'),
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
}
