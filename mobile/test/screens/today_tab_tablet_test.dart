import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/layout/reading_width.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/guess_input.dart';
import 'package:chosung/widgets/hint_card.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../fakes/fake_api_client.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 실제 셸과 같은 자리에 오늘 탭을 넣는다 — 폭 판정이 rail 을 뺀 콘텐츠 열
/// 기준이 되는지까지 보려면 `AdaptiveScaffold` 안이어야 한다(SCREENS T0·T1).
Widget _shell(FakeApiClient api) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(fakeMyStats(currentStreak: 7)),
  ],
  child: AppLocalizationScope(
    startLocale: const Locale('ko'),
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(Brightness.light),
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

Future<void> _pumpShell(
  WidgetTester tester, {
  required FakeApiClient api,
  required Size size,
}) async {
  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(_shell(api));
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

Future<void> _resizeTo(WidgetTester tester, Size size) async {
  setViewSize(tester, size);
  await tester.pumpAndSettle();
}

void main() {
  group('SCREENS T1 레이아웃 분기', () {
    testWidgets('폰 폭(390): 1열, 힌트는 보드 아래', (tester) async {
      await _pumpShell(
        tester,
        api: FakeApiClient(),
        size: const Size(390, 844),
      );

      final board = tester.getRect(find.byType(PuzzleBoard));
      final hint = tester.getRect(find.byType(HintCard));
      final input = tester.getRect(find.byType(GuessInput));

      expect(hint.top, greaterThan(board.bottom));
      expect(input.top, greaterThan(hint.bottom));
      expect(board.width, lessThanOrEqualTo(390));
    });

    testWidgets('medium(744): rail + 1열, 읽기 폭 600 가운데', (tester) async {
      await _pumpShell(
        tester,
        api: FakeApiClient(),
        size: const Size(744, 1133),
      );

      expect(find.byType(NavigationRail), findsOne);
      final rail = tester.getSize(find.byType(NavigationRail)).width;
      final board = tester.getRect(find.byType(PuzzleBoard));
      final hint = tester.getRect(find.byType(HintCard));

      // 한 열이다 — 힌트가 아직 보드 아래에 있다.
      expect(hint.top, greaterThan(board.bottom));
      expect(
        board.width,
        lessThanOrEqualTo(ReadingWidth.defaultMaxWidth),
      );
      // rail 을 뺀 콘텐츠 열 안에서 가운데 — 좌우 여백이 같다.
      final content = 744 - rail;
      expect(
        board.left - rail,
        closeTo(content - (board.right - rail), 1),
      );
    });

    testWidgets('expanded(1024): 보드·입력 왼쪽 열, 힌트·남은 기회 오른쪽 열', (
      tester,
    ) async {
      await _pumpShell(
        tester,
        api: FakeApiClient(),
        size: const Size(1024, 768),
      );

      final board = tester.getRect(find.byType(PuzzleBoard));
      final input = tester.getRect(find.byType(GuessInput));
      final hint = tester.getRect(find.byType(HintCard));
      final attemptsLeft = tester.getRect(find.byType(AttemptsLeftLabel));

      // 오른쪽 열(≤320)에 힌트와 "남은 기회" 가 같이 간다.
      expect(hint.left, greaterThanOrEqualTo(board.right));
      expect(hint.width, lessThanOrEqualTo(320));
      expect(attemptsLeft.left, greaterThanOrEqualTo(board.right));
      expect(attemptsLeft.top, greaterThan(hint.bottom));
      // 왼쪽 열은 보드와 입력을 같이 들고 폭이 600 을 넘지 않는다.
      expect(input.top, greaterThan(board.bottom));
      expect(input.left, lessThan(hint.left));
      expect(board.width, lessThanOrEqualTo(ReadingWidth.defaultMaxWidth));
      // 두 열 합이 920 을 넘지 않는다(미정 24 확정값).
      expect(hint.right - board.left, lessThanOrEqualTo(920));
    });

    // OVERRIDES §4 의 타일 크기는 폭이 아니라 글자 수로만 정해진다.
    testWidgets('타일 크기는 폰과 태블릿이 같다(확대 금지)', (tester) async {
      await _pumpShell(
        tester,
        api: FakeApiClient(),
        size: const Size(390, 844),
      );
      final phone = tester.getSize(find.byType(BoardTile).first);

      await _resizeTo(tester, const Size(1024, 768));
      final tablet = tester.getSize(find.byType(BoardTile).first);

      expect(phone, const Size(48, 48));
      expect(tablet, phone);
    });
  });

  // iPad Split View 로 폭을 줄이는 경우. 보드는 서버 이력이라 다시 읽지 않아도
  // 되지만, 치고 있던 답은 위젯이 들고 있어서 잃기 쉽다.
  testWidgets('744 → 390 폭 변경에도 입력 중 텍스트와 보드가 남는다', (tester) async {
    final api = FakeApiClient(
      puzzle: fakeTodayPuzzle(
        attemptsLeft: 4,
        attempts: const [
          PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
        ],
      ),
    );
    await _pumpShell(tester, api: api, size: const Size(744, 1133));

    await tester.enterText(find.byType(TextField), '지하철역');
    await tester.pump();
    expect(find.text('4/4'), findsOne);

    await _resizeTo(tester, const Size(390, 844));

    expect(find.byType(NavigationBar), findsOne);
    expect(find.text('지하철역'), findsOne);
    expect(find.text('4/4'), findsOne);
    // 보드는 서버 이력 그대로 — 다시 읽지 않았다.
    expect(find.text('남은 기회 4/5'), findsOne);
    expect(api.fetchTodayPuzzleCalls, 1);
  });

  // 1024 ↔ 744 는 2열 ↔ 1열이라 입력창이 다른 열로 옮겨 간다.
  testWidgets('1024 → 744 로 열 수가 바뀌어도 입력 중 텍스트가 남는다', (tester) async {
    await _pumpShell(
      tester,
      api: FakeApiClient(),
      size: const Size(1024, 768),
    );

    await tester.enterText(find.byType(TextField), '지하철역');
    await tester.pump();

    await _resizeTo(tester, const Size(744, 1133));

    expect(find.text('지하철역'), findsOne);
    expect(find.text('4/4'), findsOne);
  });
}
