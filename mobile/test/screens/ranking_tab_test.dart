import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/leaderboard_row.dart';
import 'package:chosung/widgets/offline_banner.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 순위 탭만 띄운다 — 서버 경계(`ApiClient`)와 시작할 때 읽은 내 기록만 가짜다.
Widget _app({
  required FakeApiClient api,
  Brightness brightness = Brightness.light,
  Locale locale = const Locale('ko'),
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(fakeMyStats(currentStreak: 7)),
  ],
  child: AppLocalizationScope(
    startLocale: locale,
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(brightness),
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: const Scaffold(body: RankingTab()),
      ),
    ),
  ),
);

Future<void> _pumpRanking(
  WidgetTester tester, {
  required FakeApiClient api,
  Size size = const Size(390, 844),
  Locale locale = const Locale('ko'),
}) async {
  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(_app(api: api, locale: locale));
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 상위 20명 — `rank` 20 까지 채운다(내 행은 없다).
List<LeaderboardEntry> _topTwenty() => [
  for (var rank = 1; rank <= 20; rank++) fakeLeaderboardEntry(rank: rank),
];

void main() {
  testWidgets('정상: 날짜 줄·언어 칩·목록·내 순위 카드가 다 있다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(
          entries: [
            fakeLeaderboardEntry(rank: 1),
            fakeLeaderboardEntry(
              rank: 2,
              display: '게스트 #7b20',
              attempts: 2,
              seconds: 221,
              isMe: true,
            ),
          ],
          me: const MyRank(rank: 2, attempts: 2, seconds: 221),
        ),
      ),
    );

    expect(find.text('10월 13일'), findsOneWidget);
    // 칩은 표시 전용이다 — 누를 수 있는 위젯이 아니다(전환은 S4 설정).
    expect(find.text('한국어'), findsOneWidget);
    expect(find.byType(LeaderboardRow), findsNWidgets(2));
    expect(find.text('게스트 #7b20'), findsOneWidget);
    // 1위 행의 걸린 시간(41초)
    expect(find.text('00:00:41'), findsOneWidget);
    expect(find.text('내 순위'), findsOneWidget);
    expect(find.text('#2 · 2회 · 00:03:41'), findsOneWidget);
    expect(find.text('아직 안 풀었어요'), findsNothing);
  });

  testWidgets('내 행은 강조된다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(
          entries: [
            fakeLeaderboardEntry(rank: 1),
            fakeLeaderboardEntry(rank: 2, isMe: true),
          ],
          me: const MyRank(rank: 2, attempts: 1, seconds: 41),
        ),
      ),
    );

    final rows = tester.widgetList<LeaderboardRow>(find.byType(LeaderboardRow));
    expect(rows.map((row) => row.isMe), [false, true]);
  });

  testWidgets('21위 밖이면 내 행을 목록 하단에 고정한다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(
          entries: _topTwenty(),
          me: const MyRank(rank: 23, attempts: 4, seconds: 754),
        ),
      ),
    );

    final pinned = find.byKey(RankingKeys.pinnedMeRow);
    expect(pinned, findsOneWidget);
    expect(
      find.descendant(of: pinned, matching: find.text('23')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: pinned, matching: find.text('나')),
      findsOneWidget,
    );
    // 스크롤하지 않아도 보인다 — 목록은 20줄이라 화면 밖으로 나간다.
    final pinnedRect = tester.getRect(pinned);
    expect(pinnedRect.bottom, lessThanOrEqualTo(844));
  });

  testWidgets('상위 목록에 내 행이 있으면 하단 고정 행은 없다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(
          entries: [fakeLeaderboardEntry(rank: 1, isMe: true)],
          me: const MyRank(rank: 1, attempts: 1, seconds: 41),
        ),
      ),
    );

    expect(find.byKey(RankingKeys.pinnedMeRow), findsNothing);
  });

  testWidgets('아직 안 풀었으면 내 순위 카드가 그렇게 말한다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(entries: [fakeLeaderboardEntry(rank: 1)]),
      ),
    );

    expect(find.text('아직 안 풀었어요'), findsOneWidget);
    expect(find.byKey(RankingKeys.pinnedMeRow), findsNothing);
  });

  testWidgets('빈 리더보드: 첫 번째가 되어보세요(OVERRIDES §7)', (tester) async {
    await _pumpRanking(tester, api: FakeApiClient());

    expect(find.text('아직 아무도 못 풀었어요. 첫 번째가 되어보세요'), findsOneWidget);
    expect(find.byType(LeaderboardRow), findsNothing);
  });

  testWidgets('오늘 퍼즐이 아직 없으면 오류가 아니라 빈 상태다', (tester) async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const NoPuzzleTodayApiException(
        code: 'NO_PUZZLE_TODAY',
        message: '아직 준비되지 않았습니다.',
      );

    await _pumpRanking(tester, api: api);

    expect(find.text('아직 아무도 못 풀었어요. 첫 번째가 되어보세요'), findsOneWidget);
    expect(find.text('순위를 불러오지 못했어요'), findsNothing);
  });

  testWidgets('로딩은 스켈레톤이다(스피너 금지)', (tester) async {
    final api = FakeApiClient();
    setViewSize(tester, const Size(390, 844));
    await tester.runAsync(() async {
      await tester.pumpWidget(_app(api: api));
    });
    await tester.pump();

    expect(find.byType(SkeletonBox), findsWidgets);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    await tester.pumpAndSettle();
  });

  testWidgets('오류는 인라인 카드 + 재시도이고, 재시도는 다시 읽는다', (tester) async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const ServerApiException(
        code: 'INTERNAL_ERROR',
        message: '서버 오류',
      );

    await _pumpRanking(tester, api: api);

    expect(find.text('순위를 불러오지 못했어요'), findsOneWidget);
    expect(find.byType(OfflineBanner), findsNothing);

    api
      ..fetchTodayLeaderboardError = null
      ..leaderboard = fakeLeaderboard(
        entries: [fakeLeaderboardEntry(rank: 1, display: '게스트 #a3f1')],
      );
    await tester.tap(find.text('다시 시도'));
    await tester.pumpAndSettle();

    expect(find.text('게스트 #a3f1'), findsOneWidget);
    expect(api.fetchTodayLeaderboardLimits.length, 2);
  });

  testWidgets('오프라인이면 상단 배너가 뜬다', (tester) async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );

    await _pumpRanking(tester, api: api);

    expect(find.byType(OfflineBanner), findsOneWidget);
    expect(find.text('순위를 불러오지 못했어요'), findsOneWidget);
  });

  // 로딩 스켈레톤은 고정 높이 8줄이라, 짧은 가로 화면에서는 Column 이 화면을
  // 넘었다(D-27-4). 세로 폭이 모자랄 때 레이아웃 예외를 내지 않아야 한다.
  testWidgets('로딩 스켈레톤은 짧은 가로 화면(844x390)에서도 넘치지 않는다', (tester) async {
    final api = FakeApiClient();
    setViewSize(tester, const Size(844, 390));
    await tester.runAsync(() async {
      await tester.pumpWidget(_app(api: api));
    });
    await tester.pump();

    expect(find.byType(SkeletonBox), findsWidgets);
    expect(tester.takeException(), isNull);
    await tester.pumpAndSettle();
  });

  testWidgets('영어 UI 에서도 같은 화면이 뜬다', (tester) async {
    await _pumpRanking(
      tester,
      api: FakeApiClient(
        leaderboard: fakeLeaderboard(
          language: PuzzleLanguage.en,
          entries: [fakeLeaderboardEntry(rank: 1)],
        ),
      ),
      locale: const Locale('en'),
    );

    expect(find.text('English'), findsOneWidget);
    expect(find.text('Not solved yet'), findsOneWidget);
  });
}
