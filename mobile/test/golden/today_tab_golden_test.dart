import 'dart:io';

import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/screens/today_tab.dart';
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

/// 목업(`design/stitch/e1_home.html`·`e7_home_dark.html`)과 눈으로 대조할
/// 스크린샷을 골든 파일로 남긴다. 실기기·시뮬레이터 없이 같은 그림을 다시
/// 만들 수 있어야 뒤 티켓이 바꾼 게 있는지 알 수 있다.
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

  // 아이콘도 글꼴이다 — 안 불러오면 골든에 네모만 남는다. 패키지 에셋은
  // 테스트 번들에서 `packages/<패키지>/<경로>` 로 읽는다.
  final lucide = FontLoader('packages/lucide_icons/Lucide')
    ..addFont(rootBundle.load('packages/lucide_icons/assets/lucide.ttf'));
  await lucide.load();
}

/// 보드가 한 번은 채워진 상태(시도 2행 + 힌트 잠김)로 찍는다 — 목업과 같은 장면.
FakeApiClient _api() => FakeApiClient(
  puzzle: fakeTodayPuzzle(
    attemptsLeft: 3,
    attempts: const [
      PuzzleAttempt(guess: '지하철역', feedback: [true, true, false, false]),
      PuzzleAttempt(guess: '자하촌역', feedback: [true, false, false, true]),
    ],
  ),
);

Widget _shell({required Brightness brightness}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(_api()),
    startupStatsProvider.overrideWithValue(fakeMyStats(currentStreak: 7)),
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
        home: AdaptiveScaffold(
          selectedIndex: 0,
          onDestinationSelected: (_) {},
          destinations: const [
            AdaptiveDestination(icon: LucideIcons.grid, label: '오늘'),
            AdaptiveDestination(icon: LucideIcons.trophy, label: '순위'),
            AdaptiveDestination(icon: LucideIcons.calendar, label: '내 기록'),
          ],
          body: const TodayTab(),
        ),
      ),
    ),
  ),
);

void main() {
  setUpAll(_loadFonts);

  for (final shot in [
    (name: 'today_light_390', size: const Size(390, 844), dark: false),
    (name: 'today_dark_390', size: const Size(390, 844), dark: true),
    (name: 'today_tablet_1024', size: const Size(1024, 768), dark: false),
  ]) {
    testWidgets('골든: ${shot.name}', (tester) async {
      setViewSize(tester, shot.size);
      await tester.runAsync(() async {
        await tester.pumpWidget(
          _shell(
            brightness: shot.dark ? Brightness.dark : Brightness.light,
          ),
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
