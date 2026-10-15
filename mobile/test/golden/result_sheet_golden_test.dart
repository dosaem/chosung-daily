import 'dart:io';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 목업(`design/stitch/e2_result.html`)과 눈으로 대조할 스크린샷. 카운트다운은
/// 가짜 시계로 고정한다 — 초가 흐르면 골든이 매번 달라진다.
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

/// 2번째 시도에 맞춘 결과 — 목업과 같은 장면.
TodayPuzzle _puzzle() => fakeTodayPuzzle(
  attemptsLeft: 3,
  status: PuzzleStatus.success,
  answer: '지하철역',
  attempts: const [
    PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
    PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
  ],
);

Widget _app({required Brightness brightness}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(FakeApiClient()),
    analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
    localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
    startupStatsProvider.overrideWithValue(fakeMyStats()),
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
                onPressed: () => showResultSheet(
                  context: context,
                  puzzle: _puzzle(),
                  onShowRanking: () {},
                  onLinkAccount: () {},
                  // KST 2026-10-13 16:47:27 — 다음 퍼즐까지 07:12:33.
                  now: () => DateTime.utc(2026, 10, 13, 7, 47, 27),
                ),
                child: const Text('결과 보기'),
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
    (name: 'result_light_390', size: const Size(390, 844), dark: false),
    (name: 'result_dark_390', size: const Size(390, 844), dark: true),
    (name: 'result_tablet_744', size: const Size(744, 1024), dark: false),
  ]) {
    testWidgets('골든: ${shot.name}', (tester) async {
      setViewSize(tester, shot.size);
      await tester.runAsync(() async {
        await tester.pumpWidget(
          _app(brightness: shot.dark ? Brightness.dark : Brightness.light),
        );
        await tester.pump();
      });
      await tester.pumpAndSettle();

      await tester.runAsync(() async {
        await tester.tap(find.text('결과 보기'));
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
