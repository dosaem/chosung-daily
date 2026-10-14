import 'dart:async';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/puzzle/share_text.dart';
import 'package:chosung/share/share_sheet.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:chosung/widgets/stat_bar.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 2번째 시도에 맞춘 ko 퍼즐("지하철역").
TodayPuzzle solvedPuzzle({PuzzleLanguage language = PuzzleLanguage.ko}) =>
    fakeTodayPuzzle(
      language: language,
      attemptsLeft: 3,
      status: PuzzleStatus.success,
      answer: '지하철역',
      attempts: const [
        PuzzleAttempt(guess: '지하철로', feedback: [true, true, true, false]),
        PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
      ],
    );

/// 5번 모두 틀린 퍼즐.
TodayPuzzle failedPuzzle() => fakeTodayPuzzle(
  attemptsLeft: 0,
  status: PuzzleStatus.fail,
  answer: '지하철역',
  attempts: const [
    PuzzleAttempt(guess: '지하철로', feedback: [true, true, true, false]),
    PuzzleAttempt(guess: '지하도로', feedback: [true, true, false, false]),
    PuzzleAttempt(guess: '지하실역', feedback: [true, true, false, true]),
    PuzzleAttempt(guess: '지하창역', feedback: [true, true, false, true]),
    PuzzleAttempt(guess: '지하터널', feedback: [true, true, false, false]),
  ],
);

/// 시트를 띄운 뒤 테스트가 들여다보는 것들.
class OpenedSheet {
  OpenedSheet({
    required this.api,
    required this.analytics,
    required this.shared,
    required this.rankingTaps,
  });

  final FakeApiClient api;
  final NoopAnalyticsService analytics;

  /// 네이티브 공유 시트로 나간 텍스트.
  final List<String> shared;
  final List<String> rankingTaps;
}

/// S1 자리에 버튼 하나를 두고 거기서 결과 시트를 띄운다 — `showResultSheet` 를
/// 거치지 않으면 폭에 따른 시트/다이얼로그 분기와 "닫고 순위로" 를 못 본다.
Future<OpenedSheet> openResultSheet(
  WidgetTester tester, {
  TodayPuzzle? puzzle,
  FakeApiClient? client,
  Size size = const Size(390, 844),
  Brightness brightness = Brightness.light,
  Locale locale = const Locale('ko'),
  double textScale = 1,
}) async {
  final api = client ?? FakeApiClient();
  final analytics = NoopAnalyticsService();
  final shared = <String>[];
  final rankingTaps = <String>[];

  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          analyticsServiceProvider.overrideWithValue(analytics),
          shareTextProvider.overrideWithValue((text) async => shared.add(text)),
        ],
        child: AppLocalizationScope(
          startLocale: locale,
          child: Builder(
            builder: (context) => MaterialApp(
              theme: appTheme(brightness),
              locale: context.locale,
              supportedLocales: context.supportedLocales,
              localizationsDelegates: context.localizationDelegates,
              home: MediaQuery(
                data: MediaQuery.of(
                  context,
                ).copyWith(textScaler: TextScaler.linear(textScale)),
                child: Builder(
                  builder: (context) => Scaffold(
                    body: TextButton(
                      onPressed: () => unawaited(
                        showResultSheet(
                          context: context,
                          puzzle: puzzle ?? solvedPuzzle(),
                          onShowRanking: () => rankingTaps.add('ranking'),
                        ),
                      ),
                      child: const Text('결과 보기'),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();

  await tester.runAsync(() async {
    await tester.tap(find.text('결과 보기'));
    await tester.pump();
  });
  await tester.pumpAndSettle();

  return OpenedSheet(
    api: api,
    analytics: analytics,
    shared: shared,
    rankingTaps: rankingTaps,
  );
}

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

void main() {
  group('결과 헤더', () {
    testWidgets('성공: 정답과 몇 번째 시도였는지 보여준다', (tester) async {
      await openResultSheet(tester);

      expect(find.text('정답은 지하철역!'), findsOne);
      expect(find.text('2번째 시도에 맞췄어요'), findsOne);
      // 제출한 2행 × 4칸만 — 문제 행도 빈 행도 시트엔 없다.
      expect(find.byType(BoardTile), findsNWidgets(8));
    });

    testWidgets('실패: 아쉬움 문구와 정답을 보여준다', (tester) async {
      await openResultSheet(tester, puzzle: failedPuzzle());

      expect(find.text('아쉬워요, 정답은 지하철역'), findsOne);
      expect(find.text('5번 모두 아쉬웠어요'), findsOne);
      expect(find.byType(BoardTile), findsNWidgets(20));
    });

    testWidgets('정답이 안 왔으면 "정답은 !" 대신 짧은 문구다', (tester) async {
      await openResultSheet(
        tester,
        puzzle: fakeTodayPuzzle(
          attemptsLeft: 3,
          status: PuzzleStatus.success,
          attempts: const [
            PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
          ],
        ),
      );

      expect(find.text('정답이에요!'), findsOne);
    });

    testWidgets('en 기기는 영어 문구다', (tester) async {
      await openResultSheet(tester, locale: const Locale('en'));

      expect(find.text('The answer is 지하철역!'), findsOne);
      expect(find.text('Solved on try 2'), findsOne);
    });
  });

  group('분포 막대', () {
    testWidgets('시도 1~5 비율과 내 행 강조(US 9)', (tester) async {
      final opened = await openResultSheet(tester);

      expect(find.text('오늘의 통계'), findsOne);
      expect(find.byType(StatBar), findsOne);
      for (final (attempt, percent) in [
        (1, '8%'),
        (2, '31%'),
        (3, '40%'),
        (4, '15%'),
        (5, '6%'),
      ]) {
        expect(find.text('$attempt회'), findsOne);
        expect(find.text(percent), findsOne);
      }
      expect(opened.api.fetchTodayStatsCalls, 1);

      // 내 행(2회)만 굵게 + `primary-button` 면. 나머지는 보조색이다.
      const colors = AppColors.light;
      expect(_fillColor(tester, 2), colors.primaryButton);
      expect(_fillColor(tester, 3), colors.mutedForeground);
      expect(_labelWeight(tester, '2회'), FontWeight.w700);
      expect(_labelWeight(tester, '3회'), FontWeight.w400);
    });

    testWidgets('막대 길이가 비율에 비례한다', (tester) async {
      await openResultSheet(tester);

      final track = tester.getSize(find.byKey(const ValueKey('stat-track-3')));
      final fill = tester.getSize(find.byKey(const ValueKey('stat-fill-3')));

      expect(fill.width, closeTo(track.width * 0.4, 0.5));
      expect(fill.height, StatBar.barHeight);
    });

    testWidgets('실패한 사람은 분포에 내 행이 없다', (tester) async {
      await openResultSheet(tester, puzzle: failedPuzzle());

      const colors = AppColors.light;
      for (var attempt = 1; attempt <= 5; attempt++) {
        expect(_fillColor(tester, attempt), colors.mutedForeground);
      }
    });

    testWidgets('조회 중엔 스켈레톤(스피너 금지)', (tester) async {
      final gate = Completer<void>();
      final api = FakeApiClient()..fetchTodayStatsGate = gate;

      await openResultSheet(tester, client: api);

      expect(find.byType(SkeletonBox), findsNWidgets(5));
      expect(find.byType(StatBar), findsNothing);
      // 통계가 늦어도 공유·순위·카운트다운은 이미 쓸 수 있다.
      expect(find.text('결과 공유'), findsOne);

      gate.complete();
      await tester.runAsync(() => tester.pump());
      await tester.pumpAndSettle();

      expect(find.byType(StatBar), findsOne);
      expect(find.byType(SkeletonBox), findsNothing);
    });

    testWidgets('실패하면 시트 안에서 다시 시도한다', (tester) async {
      final api = FakeApiClient()
        ..fetchTodayStatsError = const ServerApiException(
          code: 'INTERNAL_ERROR',
          message: '서버 오류',
        );

      final opened = await openResultSheet(tester, client: api);

      expect(find.text('통계를 불러오지 못했어요'), findsOne);
      expect(find.byType(StatBar), findsNothing);
      // 헤더·공유는 통계와 무관하게 그대로 있다.
      expect(find.text('정답은 지하철역!'), findsOne);

      api.fetchTodayStatsError = null;
      await tapAndSettle(tester, find.text('다시 시도'));

      expect(find.byType(StatBar), findsOne);
      expect(opened.api.fetchTodayStatsCalls, 2);
    });

    testWidgets('아직 아무도 못 풀었으면 막대 대신 한 줄', (tester) async {
      final api = FakeApiClient()
        ..todayStats = fakeTodayStats(
          totalSolved: 0,
          byAttempt: const {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        );

      await openResultSheet(tester, client: api);

      expect(find.text('아직 아무도 못 풀었어요'), findsOne);
      expect(find.byType(StatBar), findsNothing);
    });

    testWidgets('조회는 결과 퍼즐의 언어로 못 박는다(D-26-1)', (tester) async {
      final opened = await openResultSheet(
        tester,
        puzzle: solvedPuzzle(language: PuzzleLanguage.en),
        client: FakeApiClient()
          ..todayStats = fakeTodayStats(language: PuzzleLanguage.en),
      );

      // 게스트 선호 언어(서버 기본)가 아니라 시트가 그린 퍼즐의 언어로 묻는다.
      expect(opened.api.fetchTodayStatsLanguages, [PuzzleLanguage.en]);
    });

    testWidgets('날짜가 다른 통계는 분포 대신 새 퍼즐 안내다(D-26-1)', (tester) async {
      // 자정을 넘긴 뒤 '다시 시도' 가 받아오는 응답 — 어제 결과 시트에 오늘
      // 분포가 붙으면 안 된다.
      final api = FakeApiClient()
        ..todayStats = fakeTodayStats(
          date: DateTime(2026, 10, 14),
          totalSolved: 10,
          byAttempt: const {1: 1, 2: 0, 3: 0, 4: 0, 5: 0},
        );

      await openResultSheet(tester, client: api);

      expect(find.byType(StatBar), findsNothing);
      expect(find.text('내 결과'), findsNothing);
      expect(find.text('새 퍼즐이 시작돼 이 결과의 통계는 더 보여줄 수 없어요'), findsOne);
      // 헤더·공유는 통계와 무관하게 그대로 있다.
      expect(find.text('정답은 지하철역!'), findsOne);
    });

    testWidgets('언어가 다른 통계도 분포를 보류한다(D-26-1)', (tester) async {
      final api = FakeApiClient()
        ..todayStats = fakeTodayStats(
          language: PuzzleLanguage.en,
          totalSolved: 10,
          byAttempt: const {1: 1, 2: 0, 3: 0, 4: 0, 5: 0},
        );

      await openResultSheet(tester, client: api);

      expect(find.byType(StatBar), findsNothing);
      expect(find.text('새 퍼즐이 시작돼 이 결과의 통계는 더 보여줄 수 없어요'), findsOne);
    });

    testWidgets('날짜가 달라도 아무도 못 풀었다고 하지 않는다(D-26-1)', (tester) async {
      // `totalSolved == 0` 이 먼저 걸리면 내가 맞춘 퍼즐에 '아직 아무도 못
      // 풀었어요' 가 붙는다.
      final api = FakeApiClient()
        ..todayStats = fakeTodayStats(
          date: DateTime(2026, 10, 14),
          totalSolved: 0,
          byAttempt: const {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        );

      await openResultSheet(tester, client: api);

      expect(find.text('아직 아무도 못 풀었어요'), findsNothing);
      expect(find.text('새 퍼즐이 시작돼 이 결과의 통계는 더 보여줄 수 없어요'), findsOne);
    });
  });

  group('카운트다운', () {
    testWidgets('다음 퍼즐까지 남은 시간을 보여준다(US 6)', (tester) async {
      await openResultSheet(tester);

      expect(
        find.textContaining(RegExp(r'^다음 퍼즐까지 \d\d:\d\d:\d\d$')),
        findsOne,
      );
    });
  });

  group('공유', () {
    testWidgets('공유 텍스트는 웹과 같은 포맷 + 링크다(US 10·11)', (tester) async {
      final opened = await openResultSheet(tester);

      await tapAndSettle(tester, find.text('결과 공유'));

      expect(opened.shared.single, '''
오늘의 초성 2026-10-13
ㅈㅎㅊㅇ (4글자)
2/5 성공

🟩🟩🟩⬜
🟩🟩🟩🟩

$shareUrl''');
      // 공유 텍스트에 정답이 들어가면 안 푼 사람에게 답이 새어나간다.
      expect(opened.shared.single, isNot(contains('지하철역')));
    });

    testWidgets('실패한 결과도 공유한다', (tester) async {
      final opened = await openResultSheet(tester, puzzle: failedPuzzle());

      await tapAndSettle(tester, find.text('결과 공유'));

      expect(opened.shared.single, contains('5/5 실패'));
      expect(opened.shared.single, contains(shareUrl));
    });

    testWidgets('share 이벤트를 찍는다', (tester) async {
      final opened = await openResultSheet(tester);

      await tapAndSettle(tester, find.text('결과 공유'));

      expect(opened.analytics.logged.map((event) => event.name), ['share']);
    });
  });

  group('순위 보기', () {
    testWidgets('시트를 닫고 순위로 보낸다', (tester) async {
      final opened = await openResultSheet(tester);

      await tapAndSettle(tester, find.text('순위 보기'));

      expect(opened.rankingTaps, ['ranking']);
      expect(find.byType(ResultSheet), findsNothing);
    });
  });

  group('계정 연결 안내(US 20)', () {
    testWidgets('자리가 있고 닫으면 사라진다', (tester) async {
      await openResultSheet(tester);

      expect(find.text('기록을 지키려면 계정을 연결하세요 →'), findsOne);

      await tapAndSettle(tester, find.byTooltip('안내 닫기'));

      expect(find.text('기록을 지키려면 계정을 연결하세요 →'), findsNothing);
      // 닫아도 시트는 그대로 있다.
      expect(find.text('정답은 지하철역!'), findsOne);
    });
  });

  group('그 밖의 상태', () {
    testWidgets('다크모드에서도 토큰 색만 쓴다', (tester) async {
      await openResultSheet(tester, brightness: Brightness.dark);

      const colors = AppColors.dark;
      expect(_fillColor(tester, 2), colors.primaryButton);
      expect(_fillColor(tester, 1), colors.mutedForeground);
    });

    testWidgets('글자를 1.3배로 키워도 잘리지 않는다', (tester) async {
      await openResultSheet(tester, textScale: 1.3);

      expect(tester.takeException(), isNull);
      expect(find.text('정답은 지하철역!'), findsOne);
      expect(find.text('결과 공유'), findsOne);
    });
  });
}

Color _fillColor(WidgetTester tester, int attempt) =>
    tester.widget<ColoredBox>(find.byKey(ValueKey('stat-fill-$attempt'))).color;

FontWeight? _labelWeight(WidgetTester tester, String label) =>
    tester.widget<Text>(find.text(label)).style?.fontWeight;
