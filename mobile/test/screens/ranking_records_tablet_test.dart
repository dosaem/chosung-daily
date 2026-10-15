import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/leaderboard_row.dart';
import 'package:chosung/widgets/seven_day_grid.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_permissions.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 실제 셸과 같은 자리에 탭을 넣는다 — 폭 판정이 rail 을 뺀 콘텐츠 열 기준이
/// 되는지까지 보려면 `AdaptiveScaffold` 안이어야 한다(SCREENS T0·T3·T4).
Widget _shell({required FakeApiClient api, required Widget tab}) =>
    ProviderScope(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        startupStatsProvider.overrideWithValue(
          fakeMyStats(currentStreak: 12, maxStreak: 30, solvedCount: 41),
        ),
        appVersionProvider.overrideWith((ref) async => '1.2.3'),
        // T4 의 열 배치는 "광고 개인정보 설정" 행이 있는 구성(EEA)에서 본다 —
        // 그 행은 UMP privacy options 가 required 일 때만 뜬다(티켓 31).
        isIosProvider.overrideWithValue(false),
        trackingAuthorizationProvider.overrideWithValue(
          FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
        ),
        adServiceProvider.overrideWithValue(
          FakeAdService(
            consent: const UmpStatus(
              consent: ConsentStatus.obtained,
              privacyOptionsRequired: true,
            ),
          ),
        ),
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
              selectedIndex: 1,
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

Future<void> _pump(
  WidgetTester tester, {
  required FakeApiClient api,
  required Widget tab,
  required Size size,
}) async {
  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(_shell(api: api, tab: tab));
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

FakeApiClient _rankingApi() => FakeApiClient(
  leaderboard: fakeLeaderboard(
    entries: [
      for (var rank = 1; rank <= 20; rank++) fakeLeaderboardEntry(rank: rank),
    ],
    me: const MyRank(rank: 23, attempts: 4, seconds: 754),
  ),
);

Finder _myRankCard() => find.ancestor(
  of: find.text('내 순위'),
  matching: find.byType(DecoratedBox),
);

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  group('SCREENS T3 순위', () {
    testWidgets('폰 폭(390): 표 머리글 없이 1열, 내 순위 카드는 날짜 아래', (tester) async {
      await _pump(
        tester,
        api: _rankingApi(),
        tab: const RankingTab(),
        size: const Size(390, 844),
      );

      expect(find.text('이름'), findsNothing);
      final card = tester.getRect(_myRankCard().first);
      final date = tester.getRect(find.text('10월 13일'));
      expect(card.top, greaterThan(date.bottom));
      expect(
        tester.getRect(find.byType(LeaderboardRow).first).width,
        lessThanOrEqualTo(390),
      );
    });

    testWidgets('medium(744): 4열 표 + 내 순위 카드는 날짜와 한 줄', (tester) async {
      await _pump(
        tester,
        api: _rankingApi(),
        tab: const RankingTab(),
        size: const Size(744, 1133),
      );

      // 머리글 4칸이 생긴다(순위·이름·시도·시간). "순위" 는 rail 탭 라벨에도
      // 있으므로 탭 안쪽으로 좁혀서 센다.
      expect(
        find.descendant(
          of: find.byType(RankingTab),
          matching: find.text('순위'),
        ),
        findsOneWidget,
      );
      expect(find.text('이름'), findsOneWidget);
      expect(find.text('시도'), findsOneWidget);
      expect(find.text('시간'), findsOneWidget);

      final card = tester.getRect(_myRankCard().first);
      final date = tester.getRect(find.text('10월 13일'));
      expect(card.top, lessThan(date.bottom));
      expect(card.left, greaterThan(date.right));
    });

    testWidgets('expanded(1024): 표 폭은 840 을 넘지 않는다', (tester) async {
      await _pump(
        tester,
        api: _rankingApi(),
        tab: const RankingTab(),
        size: const Size(1024, 768),
      );

      final row = tester.getRect(find.byType(LeaderboardRow).first);
      expect(row.width, lessThanOrEqualTo(840));
      expect(find.text('이름'), findsOneWidget);
      // 21위 밖 내 행은 폭과 무관하게 하단 고정이다.
      expect(find.byKey(RankingKeys.pinnedMeRow), findsOneWidget);
    });
  });

  group('SCREENS T4 내 기록', () {
    /// 자리의 가로 중심. 2열에서는 왼쪽/오른쪽 열이 이 값으로 갈린다.
    double centerX(WidgetTester tester, Key key) =>
        tester.getRect(find.byKey(key)).center.dx;

    testWidgets('폰 폭(390): 1열 — 설정이 기록 아래로 이어진다', (tester) async {
      await _pump(
        tester,
        api: FakeApiClient(),
        tab: const RecordsTab(),
        size: const Size(390, 844),
      );

      expect(
        centerX(tester, RecordsSlot.account),
        centerX(tester, RecordsSlot.dailyNotification),
      );
      expect(
        tester.getRect(find.byKey(RecordsSlot.dailyNotification)).top,
        greaterThan(tester.getRect(find.byKey(RecordsSlot.account)).bottom),
      );
      expect(find.byType(DayCell), findsNWidgets(7));
    });

    testWidgets('medium(744): 아직 1열, 읽기 폭 600 가운데', (tester) async {
      await _pump(
        tester,
        api: FakeApiClient(),
        tab: const RecordsTab(),
        size: const Size(744, 1133),
      );

      expect(
        centerX(tester, RecordsSlot.account),
        centerX(tester, RecordsSlot.dailyNotification),
      );
      final grid = tester.getRect(find.byType(SevenDayGrid));
      expect(grid.width, lessThanOrEqualTo(600));
    });

    testWidgets('expanded(1024): T4 2열 — 자리마다 열이 고정된다', (tester) async {
      await _pump(
        tester,
        api: FakeApiClient(),
        tab: const RecordsTab(),
        size: const Size(1024, 768),
      );

      // 왼쪽 열 = 기록 + 계정·구독·백업 코드(티켓 29·32).
      final leftSlots = [
        RecordsSlot.account,
        RecordsSlot.subscription,
        RecordsSlot.backupCode,
      ];
      // 오른쪽 열 = 설정 리스트 + 계정 삭제(티켓 28·29·30·31).
      final rightSlots = [
        RecordsSlot.dailyNotification,
        RecordsSlot.reminder,
        RecordsSlot.adPrivacy,
        RecordsSlot.howTo,
        RecordsSlot.deleteAccount,
      ];
      final boundary = tester.getRect(find.byType(SevenDayGrid)).right;

      for (final slot in leftSlots) {
        expect(
          centerX(tester, slot),
          lessThanOrEqualTo(boundary),
          reason: '$slot 는 왼쪽 열에 있어야 한다',
        );
      }
      for (final slot in rightSlots) {
        expect(
          centerX(tester, slot),
          greaterThan(boundary),
          reason: '$slot 는 오른쪽 열에 있어야 한다',
        );
      }
      // 열마다 최대 480.
      expect(
        tester.getRect(find.byType(SevenDayGrid)).width,
        lessThanOrEqualTo(480),
      );
    });

    // 폭이 바뀌면 1열↔2열로 스크롤 위젯 트리가 교체된다. 그때 읽던 위치를
    // 잃으면 화면 맨 위로 돌아간다(D-27-3) — SCREENS "태블릿 레이아웃" 공통
    // 규칙은 현재 탭과 스크롤 위치를 유지하라고 한다.
    testWidgets('390 → 1024 → 390 왕복에도 읽던 스크롤 위치가 남는다', (tester) async {
      await _pump(
        tester,
        api: FakeApiClient(),
        tab: const RecordsTab(),
        size: const Size(390, 844),
      );

      final column = find.descendant(
        of: find.byType(RecordsTab),
        matching: find.byType(Scrollable),
      );
      double offset() => tester.state<ScrollableState>(column).position.pixels;

      await tester.drag(column, const Offset(0, -184));
      await tester.pumpAndSettle();
      final scrolled = offset();
      expect(scrolled, greaterThan(0));

      setViewSize(tester, const Size(1024, 768));
      await tester.pumpAndSettle();
      setViewSize(tester, const Size(390, 844));
      await tester.pumpAndSettle();

      expect(offset(), scrolled);
    });

    testWidgets('1024 → 390 으로 좁아져도 같은 자리들이 남는다', (tester) async {
      await _pump(
        tester,
        api: FakeApiClient(),
        tab: const RecordsTab(),
        size: const Size(1024, 768),
      );

      setViewSize(tester, const Size(390, 844));
      await tester.pumpAndSettle();

      expect(find.byKey(RecordsSlot.account), findsOneWidget);
      expect(find.byKey(RecordsSlot.deleteAccount), findsOneWidget);
      expect(
        centerX(tester, RecordsSlot.account),
        centerX(tester, RecordsSlot.deleteAccount),
      );
    });
  });
}
