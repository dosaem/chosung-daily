import 'dart:async';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/settings/legal_links.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/settings_row.dart';
import 'package:chosung/widgets/seven_day_grid.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 내 기록 탭만 띄운다. 홈 탭은 실제 셸에서 계속 살아 있으므로
/// (`StatefulShellRoute` 가 분기를 유지한다) 같은 상태를 만들려고 오늘 퍼즐
/// provider 를 watch 하는 위젯을 하나 끼운다 — 언어를 바꾼 뒤 홈이 다시
/// 읽히는지 보려면 홈이 떠 있어야 한다.
Widget _app({
  required FakeApiClient api,
  required List<String> openedUrls,
  MyStats? stats,
  Brightness brightness = Brightness.light,
  Locale locale = const Locale('ko'),
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(
      stats ?? fakeMyStats(currentStreak: 12, maxStreak: 30, solvedCount: 41),
    ),
    appVersionProvider.overrideWith((ref) async => '1.2.3'),
    webLinkLauncherProvider.overrideWithValue((url) async {
      openedUrls.add(url);
    }),
    localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
    // 알림 설정은 기기 로컬 저장소에서 온다(티켓 30). 알림 행 자체는
    // `records_notifications_test.dart` 가 따로 본다.
    notificationSettingsStoreProvider.overrideWithValue(
      InMemoryNotificationSettingsStore(),
    ),
  ],
  child: AppLocalizationScope(
    startLocale: locale,
    child: Builder(
      builder: (context) => MaterialApp(
        theme: appTheme(brightness),
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: const Scaffold(
          body: Column(
            children: [
              SizedBox(height: 0, child: _LiveHomeTab()),
              Expanded(child: RecordsTab()),
            ],
          ),
        ),
      ),
    ),
  ),
);

class _LiveHomeTab extends ConsumerWidget {
  const _LiveHomeTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(todayPuzzleProvider);
    return const SizedBox.shrink();
  }
}

Future<void> _pumpRecords(
  WidgetTester tester, {
  required FakeApiClient api,
  List<String>? openedUrls,
  MyStats? stats,
  Size size = const Size(390, 844),
  Locale locale = const Locale('ko'),
}) async {
  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(
      _app(
        api: api,
        openedUrls: openedUrls ?? [],
        stats: stats,
        locale: locale,
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 라벨로 설정 행을 찾는다 — 자리(28~32)는 키로 찾는다.
Finder _row(String label) => find.ancestor(
  of: find.text(label),
  matching: find.byType(SettingsRow),
);

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('streak 3칸 카드는 현재·최고·누적을 보여준다', (tester) async {
    await _pumpRecords(tester, api: FakeApiClient());

    expect(find.text('현재'), findsOneWidget);
    expect(find.text('12일'), findsOneWidget);
    expect(find.text('최고'), findsOneWidget);
    expect(find.text('30일'), findsOneWidget);
    expect(find.text('누적'), findsOneWidget);
    expect(find.text('41문제'), findsOneWidget);
  });

  // 티켓 38: en 에서 `1 days` / `1 puzzles` 가 나오던 자리. ko 는 단·복수가 같다.
  testWidgets('en: 1 일·1 문제는 단수, 2 이상은 복수다', (tester) async {
    await _pumpRecords(
      tester,
      api: FakeApiClient(),
      stats: fakeMyStats(currentStreak: 1, maxStreak: 2, solvedCount: 1),
      locale: const Locale('en'),
    );

    expect(find.text('1 day'), findsOneWidget);
    expect(find.text('2 days'), findsOneWidget);
    expect(find.text('1 puzzle'), findsOneWidget);
    expect(find.text('1 days'), findsNothing);
    expect(find.text('1 puzzles'), findsNothing);
  });

  testWidgets('ko: 1 일·1 문제 문구는 2 이상과 같은 꼴이다', (tester) async {
    await _pumpRecords(
      tester,
      api: FakeApiClient(),
      stats: fakeMyStats(currentStreak: 1, maxStreak: 2, solvedCount: 1),
    );

    expect(find.text('1일'), findsOneWidget);
    expect(find.text('2일'), findsOneWidget);
    expect(find.text('1문제'), findsOneWidget);
  });

  testWidgets('7일 그리드는 날짜 7칸을 한 언어라도 풀었으면 성공으로 칠한다', (tester) async {
    final api = FakeApiClient(
      history: fakeHistory(
        results: const [
          {
            PuzzleLanguage.ko: DayResult.success,
            PuzzleLanguage.en: DayResult.none,
          },
          {
            PuzzleLanguage.ko: DayResult.fail,
            PuzzleLanguage.en: DayResult.none,
          },
          {
            PuzzleLanguage.ko: DayResult.none,
            PuzzleLanguage.en: DayResult.success,
          },
          {
            PuzzleLanguage.ko: DayResult.none,
            PuzzleLanguage.en: DayResult.none,
          },
          {
            PuzzleLanguage.ko: DayResult.success,
            PuzzleLanguage.en: DayResult.fail,
          },
          {
            PuzzleLanguage.ko: DayResult.fail,
            PuzzleLanguage.en: DayResult.fail,
          },
          {
            PuzzleLanguage.ko: DayResult.inProgress,
            PuzzleLanguage.en: DayResult.none,
          },
        ],
      ),
    );

    await _pumpRecords(tester, api: api);

    final cells = tester.widgetList<DayCell>(find.byType(DayCell));
    expect(cells.map((cell) => cell.result).toList(), [
      DayResult.success,
      DayResult.fail,
      DayResult.success,
      DayResult.none,
      DayResult.success,
      DayResult.fail,
      DayResult.inProgress,
    ]);
    expect(api.fetchMyHistoryDays, [7]);
  });

  testWidgets('최근 기록을 못 읽으면 인라인 안내 + 재시도', (tester) async {
    final api = FakeApiClient()
      ..fetchMyHistoryError = const ServerApiException(
        code: 'INTERNAL_ERROR',
        message: '서버 오류',
      );

    await _pumpRecords(tester, api: api);

    expect(find.text('최근 기록을 불러오지 못했어요'), findsOneWidget);
    expect(find.byType(DayCell), findsNothing);

    api.fetchMyHistoryError = null;
    await tester.tap(find.text('다시 시도'));
    await tester.pumpAndSettle();

    expect(find.byType(DayCell), findsNWidgets(7));
    expect(api.fetchMyHistoryDays.length, 2);
  });

  testWidgets('설정 리스트에 퍼즐 언어·법적 문서·라이선스·버전이 있다', (tester) async {
    await _pumpRecords(tester, api: FakeApiClient());

    expect(_row('퍼즐 언어'), findsOneWidget);
    expect(find.text('한국어'), findsOneWidget);
    expect(_row('개인정보처리방침'), findsOneWidget);
    expect(_row('이용약관'), findsOneWidget);
    expect(_row('오픈소스 라이선스'), findsOneWidget);
    expect(_row('버전'), findsOneWidget);
    expect(find.text('1.2.3'), findsOneWidget);
  });

  testWidgets('퍼즐 언어를 바꾸면 PATCH /me 뒤 홈을 다시 읽는다', (tester) async {
    final api = FakeApiClient();
    await _pumpRecords(tester, api: api);
    expect(api.fetchTodayPuzzleCalls, 1);

    await tester.tap(_row('퍼즐 언어'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('영어').last);
    await tester.pumpAndSettle();

    expect(api.updatedPuzzleLanguages, [PuzzleLanguage.en]);
    expect(api.fetchTodayPuzzleCalls, 2);
    expect(find.text('영어'), findsOneWidget);
  });

  testWidgets('바꾸는 동안 퍼즐 언어 행은 다시 눌리지 않는다', (tester) async {
    final gate = Completer<void>();
    final api = FakeApiClient()..updatePuzzleLanguageGate = gate;
    await _pumpRecords(tester, api: api);

    await tester.tap(_row('퍼즐 언어'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('영어').last);
    await tester.pumpAndSettle();

    // 응답을 기다리는 동안은 비활성이다(쓰기 직렬화).
    expect(tester.widget<SettingsRow>(_row('퍼즐 언어')).onTap, isNull);

    gate.complete();
    await tester.pumpAndSettle();

    expect(tester.widget<SettingsRow>(_row('퍼즐 언어')).onTap, isNotNull);
    expect(api.updatedPuzzleLanguages, [PuzzleLanguage.en]);
  });

  testWidgets('언어를 바꾸지 못하면 그 행 아래에 안내가 남는다', (tester) async {
    final api = FakeApiClient()
      ..updatePuzzleLanguageError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    await _pumpRecords(tester, api: api);

    await tester.tap(_row('퍼즐 언어'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('영어').last);
    await tester.pumpAndSettle();

    expect(find.text('언어를 바꾸지 못했어요. 다시 시도해주세요'), findsOneWidget);
    expect(find.text('한국어'), findsOneWidget);
  });

  testWidgets('법적 문서는 UI 언어를 붙여 웹으로 연다', (tester) async {
    final openedUrls = <String>[];
    await _pumpRecords(
      tester,
      api: FakeApiClient(),
      openedUrls: openedUrls,
    );

    await tester.tap(_row('개인정보처리방침'));
    await tester.pumpAndSettle();
    await tester.tap(_row('이용약관'));
    await tester.pumpAndSettle();

    expect(openedUrls.length, 2);
    expect(openedUrls.first, endsWith('/privacy?lang=ko'));
    expect(openedUrls.last, endsWith('/terms?lang=ko'));
  });

  testWidgets('오픈소스 라이선스 행은 라이선스 화면을 연다', (tester) async {
    await _pumpRecords(tester, api: FakeApiClient());

    // 1열 S4 는 계정 카드(29)와 알림 두 행(30)까지 얹혀 마지막 행이 화면
    // 밖이다 — 실제 사용자처럼 먼저 스크롤한다.
    await tester.ensureVisible(_row('오픈소스 라이선스'));
    await tester.pumpAndSettle();
    await tester.tap(_row('오픈소스 라이선스'));
    await tester.pumpAndSettle();

    expect(find.byType(LicensePage), findsOneWidget);
  });

  testWidgets('31·32 가 채울 자리는 전부 있고 아직 눌리지 않는다', (tester) async {
    await _pumpRecords(tester, api: FakeApiClient());

    for (final slot in [
      RecordsSlot.account,
      RecordsSlot.subscription,
      RecordsSlot.backupCode,
      RecordsSlot.dailyNotification,
      RecordsSlot.reminder,
      RecordsSlot.adPrivacy,
      RecordsSlot.howTo,
      RecordsSlot.deleteAccount,
    ]) {
      expect(find.byKey(slot), findsOneWidget, reason: '$slot 자리가 없다');
    }

    // 이미 동작하는 자리: "하는 법" 은 티켓 28, 백업 코드는 티켓 29(그 동작은
    // `records_account_test.dart`), 일일 알림 시각은 티켓 30 이 채웠다.
    // 리마인더는 행 대신 스위치가 탭을 받으므로 onTap 은 비어 있는 게 맞다.
    final filled = [
      RecordsSlot.howTo,
      RecordsSlot.backupCode,
      RecordsSlot.dailyNotification,
    ];
    for (final row in tester.widgetList<SettingsRow>(
      find.byType(SettingsRow),
    )) {
      if (row.key == null || filled.contains(row.key)) continue;
      expect(row.onTap, isNull, reason: '${row.key} 는 아직 비활성이어야 한다');
    }
    for (final key in filled) {
      expect(
        tester.widget<SettingsRow>(find.byKey(key)).onTap,
        isNotNull,
        reason: '$key 는 이미 동작해야 한다',
      );
    }
  });

  testWidgets('영어 UI 에서도 같은 화면이 뜬다', (tester) async {
    await _pumpRecords(
      tester,
      api: FakeApiClient(),
      locale: const Locale('en'),
    );

    expect(_row('Puzzle language'), findsOneWidget);
    expect(find.text('Korean'), findsOneWidget);
    expect(_row('Privacy policy'), findsOneWidget);
  });
}
