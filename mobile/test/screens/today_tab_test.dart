import 'dart:async';

import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/guess_input.dart';
import 'package:chosung/widgets/hint_card.dart';
import 'package:chosung/widgets/offline_banner.dart';
import 'package:chosung/widgets/puzzle_board.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:chosung/widgets/skeleton_box.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 오늘 탭만 띄운다 — 서버 경계(`ApiClient`)와 시작할 때 읽은 내 기록만 가짜다.
/// 날짜 줄이 `DateFormat` 을 쓰므로 실제 앱과 같은 `localizationDelegates` 가
/// 필요하다(그 델리게이트가 intl 의 로케일 데이터를 채운다).
Widget _app({
  required FakeApiClient api,
  MyStats? stats,
  NoopAnalyticsService? analytics,
  Brightness brightness = Brightness.light,
  Locale locale = const Locale('ko'),
  double textScale = 1,
  bool disableAnimations = false,
}) => ProviderScope(
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(
      stats ?? fakeMyStats(currentStreak: 7),
    ),
    analyticsServiceProvider.overrideWithValue(
      analytics ?? NoopAnalyticsService(),
    ),
    localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
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
          data: MediaQuery.of(context).copyWith(
            textScaler: TextScaler.linear(textScale),
            disableAnimations: disableAnimations,
          ),
          child: const Scaffold(body: TodayTab()),
        ),
      ),
    ),
  ),
);

/// 번역 JSON 과 가짜 ApiClient 의 Future 는 실제 이벤트 루프에서 완료된다 —
/// 그래서 첫 프레임은 runAsync 안에서 돌린다(앱 트리 테스트와 같은 방식).
Future<void> _pumpToday(
  WidgetTester tester, {
  required FakeApiClient api,
  MyStats? stats,
  NoopAnalyticsService? analytics,
  Brightness brightness = Brightness.light,
  Locale locale = const Locale('ko'),
  Size size = const Size(390, 844),
  double textScale = 1,
  bool disableAnimations = false,
}) async {
  setViewSize(tester, size);
  await tester.runAsync(() async {
    await tester.pumpWidget(
      _app(
        api: api,
        stats: stats,
        analytics: analytics,
        brightness: brightness,
        locale: locale,
        textScale: textScale,
        disableAnimations: disableAnimations,
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 백그라운드로 내려갔다 돌아오는 실제 순서(hidden 을 건너뛰면 binding 이
/// 전이를 무효로 본다). 복귀는 `GET /puzzles/today` 재조회를 띄운다.
Future<void> _resume(WidgetTester tester) async {
  await tester.runAsync(() async {
    const [
      AppLifecycleState.inactive,
      AppLifecycleState.hidden,
      AppLifecycleState.paused,
      AppLifecycleState.hidden,
      AppLifecycleState.inactive,
      AppLifecycleState.resumed,
    ].forEach(tester.binding.handleAppLifecycleStateChanged);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 뒤집히는 중인 시도 행. 다 열린 행은 변환을 걷어내므로 보드 안의
/// `Transform` 은 "지금 뒤집히는 행" 과 같은 뜻이다.
Finder _flippingRows() => find.descendant(
  of: find.byType(PuzzleBoard),
  matching: find.byType(Transform),
);

Future<void> _tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

void main() {
  group('상태 4종', () {
    testWidgets('로딩: 스켈레톤만 보이고 보드는 없다', (tester) async {
      // 응답을 붙잡아 로딩 상태를 세워 둔다.
      final gate = Completer<void>();
      final api = FakeApiClient()..fetchTodayPuzzleGate = gate;

      await _pumpToday(tester, api: api);

      expect(find.byType(SkeletonBox), findsWidgets);
      expect(find.byType(PuzzleBoard), findsNothing);
      expect(find.byType(GuessInput), findsNothing);

      gate.complete();
      await tester.runAsync(() => tester.pump());
      await tester.pumpAndSettle();

      expect(find.byType(PuzzleBoard), findsOne);
      expect(find.byType(SkeletonBox), findsNothing);
    });

    testWidgets('정상: 날짜 줄·칩·보드·힌트·입력이 다 있다', (tester) async {
      await _pumpToday(tester, api: FakeApiClient());

      expect(find.text('오늘의 초성'), findsOne);
      expect(find.text('10월 13일 · 일반 단어'), findsOne);
      expect(find.text('KST 00:00 새 퍼즐'), findsOne);
      expect(find.text('4글자'), findsOne);
      expect(find.text('남은 기회 5/5'), findsOne);
      expect(find.text('힌트는 3번째 오답 후 열려요'), findsOne);
      expect(find.text('제출'), findsOne);
      // 문제 행 4칸 + 시도 5행 × 4칸.
      expect(find.byType(BoardTile), findsNWidgets(24));
      expect(find.byType(OfflineBanner), findsNothing);
    });

    testWidgets('오류: 인라인 카드 + 재시도, 배너는 없다', (tester) async {
      final api = FakeApiClient()
        ..fetchTodayPuzzleError = const ServerApiException(
          code: 'INTERNAL_ERROR',
          message: '서버 오류',
        );

      await _pumpToday(tester, api: api);

      expect(find.text('퍼즐을 불러오지 못했어요'), findsOne);
      expect(find.text('다시 시도'), findsOne);
      expect(find.byType(OfflineBanner), findsNothing);
      expect(find.byType(PuzzleBoard), findsNothing);

      api.fetchTodayPuzzleError = null;
      await _tapAndSettle(tester, find.text('다시 시도'));

      expect(find.byType(PuzzleBoard), findsOne);
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    testWidgets('오프라인: 상단 배너 + 재시도', (tester) async {
      final api = FakeApiClient()
        ..fetchTodayPuzzleError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );

      await _pumpToday(tester, api: api);

      expect(find.byType(OfflineBanner), findsOne);
      expect(find.text('오프라인이에요. 연결을 확인해주세요'), findsOne);
      expect(find.text('다시 시도'), findsOne);
    });

    testWidgets('퍼즐 없음: 카운트다운 카드 + 재시도', (tester) async {
      final api = FakeApiClient()
        ..fetchTodayPuzzleError = const NoPuzzleTodayApiException(
          code: 'NO_PUZZLE_TODAY',
          message: '아직 준비되지 않았습니다.',
        );

      await _pumpToday(tester, api: api);

      expect(find.text('곧 새 퍼즐이 나와요'), findsOne);
      expect(find.textContaining('다음 퍼즐까지'), findsOne);
      expect(find.text('다시 시도'), findsOne);
      expect(find.byType(GuessInput), findsNothing);
    });

    testWidgets('완료: 입력 대신 "결과 보기" 버튼', (tester) async {
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          status: PuzzleStatus.success,
          attemptsLeft: 3,
          answer: '지하철역',
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
            PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
          ],
        ),
      );

      await _pumpToday(tester, api: api);

      expect(find.text('결과 보기'), findsOne);
      expect(find.byType(GuessInput), findsNothing);
      expect(find.byType(PuzzleBoard), findsOne);
    });
  });

  group('제출', () {
    testWidgets('글자 수가 맞을 때만 제출 버튼이 눌린다', (tester) async {
      await _pumpToday(tester, api: FakeApiClient());

      final submit = find.widgetWithText(FilledButton, '제출');
      expect(tester.widget<FilledButton>(submit).onPressed, isNull);
      expect(find.text('0/4'), findsOne);

      await tester.enterText(find.byType(TextField), '지하');
      await tester.pump();
      expect(find.text('2/4'), findsOne);
      expect(tester.widget<FilledButton>(submit).onPressed, isNull);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      expect(find.text('4/4'), findsOne);
      expect(tester.widget<FilledButton>(submit).onPressed, isNotNull);
    });

    // 카운터를 넣는 방식에 따라 입력 칸이 0폭이 될 수 있다(실제로 그랬다 —
    // 골든 스크린샷에서 안내 문구가 통째로 안 보였다).
    testWidgets('입력 칸과 안내 문구가 카운터에 밀려 사라지지 않는다', (tester) async {
      await _pumpToday(tester, api: FakeApiClient());

      final hint = tester.getRect(find.text('정답을 입력하세요'));
      final counter = tester.getRect(find.text('0/4'));

      expect(hint.width, greaterThan(100));
      expect(counter.left, greaterThan(hint.right));
    });

    testWidgets('제출하면 피드백 타일이 쌓이고 입력창이 비워진다', (tester) async {
      final api = FakeApiClient();
      await _pumpToday(tester, api: api);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(api.submittedGuesses.single.guess, '지하촌역');
      expect(find.text('남은 기회 4/5'), findsOne);
      expect(find.text('0/4'), findsOne);
      // 시도 행의 글자가 보드에 들어왔다.
      expect(find.text('지'), findsOne);
      expect(find.text('촌'), findsOne);
    });

    testWidgets('409 면 새 보드를 읽어오고 "새 퍼즐이 있어요" 가 보인다', (tester) async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..submitGuessError = const PuzzleChangedApiException(
          code: 'PUZZLE_CHANGED',
          message: '퍼즐이 바뀌었어요.',
        );
      await _pumpToday(tester, api: api);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      // 서버는 이미 다음 퍼즐을 들고 있다.
      api.puzzle = fakeTodayPuzzle(puzzleId: 42);
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.text('새 퍼즐이 있어요'), findsOne);
      expect(api.submittedGuesses.single.puzzleId, 41);
      expect(api.fetchTodayPuzzleCalls, 2);
      expect(find.byType(PuzzleBoard), findsOne);
    });

    testWidgets('제출이 오프라인이면 배너가 뜨고 입력이 잠긴다', (tester) async {
      final api = FakeApiClient()
        ..submitGuessError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      await _pumpToday(tester, api: api);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.byType(OfflineBanner), findsOne);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
      expect(
        tester
            .widget<FilledButton>(find.widgetWithText(FilledButton, '제출'))
            .onPressed,
        isNull,
      );
    });
  });

  group('결과 시트(S2)', () {
    /// 한 번 더 틀리면 끝나는 보드 + 정답/오답 응답.
    FakeApiClient lastAttempt({required bool correct}) => FakeApiClient(
      puzzle: fakeTodayPuzzle(
        attemptsLeft: 1,
        attempts: const [
          PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
          PuzzleAttempt(guess: '지하도역', feedback: [true, false, false, true]),
          PuzzleAttempt(guess: '지하실역', feedback: [true, false, false, true]),
          PuzzleAttempt(guess: '지하창역', feedback: [true, false, false, true]),
        ],
      ),
      guessResult: fakeGuessResult(
        isCorrect: correct,
        attemptsLeft: 0,
        answer: '지하철역',
      ),
    );

    testWidgets('정답 제출로 끝나면 시트가 뜨고 puzzle_complete 를 찍는다', (tester) async {
      final analytics = NoopAnalyticsService();
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          attemptsLeft: 4,
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
          ],
        ),
        guessResult: fakeGuessResult(
          isCorrect: true,
          attemptsLeft: 3,
          answer: '지하철역',
        ),
      );

      await _pumpToday(tester, api: api, analytics: analytics);
      await tester.enterText(find.byType(TextField), '지하철역');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.byType(ResultSheet), findsOne);
      expect(find.text('정답은 지하철역!'), findsOne);
      expect(analytics.logged.single.name, 'puzzle_complete');
      // 남은 기회 3 → 두 번째 시도에 맞췄다.
      expect(analytics.logged.single.parameters, {
        'language': 'ko',
        'success': 1,
        'attempts': 2,
      });
      expect(api.fetchTodayStatsCalls, 1);
    });

    testWidgets('마지막 시도가 오답이면 실패 시트 + success 0 · attempts 5', (tester) async {
      final analytics = NoopAnalyticsService();

      await _pumpToday(
        tester,
        api: lastAttempt(correct: false),
        analytics: analytics,
      );
      await tester.enterText(find.byType(TextField), '지하터널');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.text('아쉬워요, 정답은 지하철역'), findsOne);
      expect(analytics.logged.single.parameters, {
        'language': 'ko',
        'success': 0,
        'attempts': 5,
      });
    });

    testWidgets('아직 안 끝난 제출은 시트도 이벤트도 없다', (tester) async {
      final analytics = NoopAnalyticsService();
      final api = FakeApiClient();

      await _pumpToday(tester, api: api, analytics: analytics);
      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.byType(ResultSheet), findsNothing);
      expect(analytics.logged, isEmpty);
      expect(api.fetchTodayStatsCalls, 0);
    });

    // 다른 기기에서 이미 끝낸 퍼즐을 여는 경로 — 이벤트는 그때 이미 찍혔다.
    testWidgets('이미 끝난 퍼즐은 자동으로 안 뜨고, "결과 보기" 로만 열린다', (tester) async {
      final analytics = NoopAnalyticsService();
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          status: PuzzleStatus.success,
          attemptsLeft: 3,
          answer: '지하철역',
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
            PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
          ],
        ),
      );

      await _pumpToday(tester, api: api, analytics: analytics);

      expect(find.byType(ResultSheet), findsNothing);

      await _tapAndSettle(tester, find.text('결과 보기'));

      expect(find.byType(ResultSheet), findsOne);
      expect(find.text('정답은 지하철역!'), findsOne);
      expect(analytics.logged, isEmpty);
    });
  });

  group('보드', () {
    testWidgets('피드백은 색뿐 아니라 아이콘·취소선으로도 구분한다', (tester) async {
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          attemptsLeft: 4,
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
          ],
        ),
      );

      await _pumpToday(tester, api: api);

      // 맞은 칸 2개에만 체크 아이콘이 붙는다(US 3 — 색각 이상).
      expect(find.byIcon(LucideIcons.check), findsNWidgets(2));
      final wrong = tester.widget<Text>(find.text('하'));
      expect(wrong.style?.decoration, TextDecoration.lineThrough);
    });

    testWidgets('en 보드는 mask 의 `s` 자리에 간격이 다시 들어간다', (tester) async {
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          language: PuzzleLanguage.en,
          mask: const [
            MaskTile(type: MaskTileType.revealed, char: 'R'),
            MaskTile(type: MaskTileType.hidden, char: ''),
            MaskTile(type: MaskTileType.revealed, char: 'D'),
            MaskTile(type: MaskTileType.separator, char: ' '),
            MaskTile(type: MaskTileType.revealed, char: 'F'),
            MaskTile(type: MaskTileType.hidden, char: ''),
            MaskTile(type: MaskTileType.revealed, char: 'X'),
          ],
          attemptsLeft: 4,
          attempts: const [
            PuzzleAttempt(
              guess: 'REDFOX',
              feedback: [true, true, true, true, false, true],
            ),
          ],
        ),
        guessResult: fakeGuessResult(
          feedback: [true, true, true, true, true, true],
        ),
      );

      await _pumpToday(tester, locale: const Locale('en'), api: api);

      // 문제 행(타일 6개 + 간격 1개) + 시도 행 5줄 × 6개 = 36 타일.
      expect(find.byType(BoardTile), findsNWidgets(36));
      expect(find.byType(BoardGap), findsNWidgets(6));
      expect(find.text('6 letters'), findsOne);
    });
  });

  testWidgets('다크모드에서도 같은 화면이 그려진다', (tester) async {
    final api = FakeApiClient(
      puzzle: fakeTodayPuzzle(
        attemptsLeft: 4,
        hint: '서울에 많다',
        attempts: const [
          PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
        ],
      ),
    );

    await _pumpToday(tester, api: api, brightness: Brightness.dark);

    expect(tester.takeException(), isNull);
    expect(find.byType(PuzzleBoard), findsOne);
    expect(find.text('서울에 많다'), findsOne);
    // 다크 토큰(OVERRIDES §2 Dark 열)으로 그려졌다.
    final correct = tester.widget<Container>(
      find.ancestor(of: find.text('지'), matching: find.byType(Container)).first,
    );
    expect(
      (correct.decoration! as BoxDecoration).color,
      AppColors.dark.tileCorrect,
    );
  });

  testWidgets('포그라운드 복귀 시 오늘 퍼즐을 다시 읽는다', (tester) async {
    final api = FakeApiClient();
    await _pumpToday(tester, api: api);
    expect(api.fetchTodayPuzzleCalls, 1);

    api.puzzle = fakeTodayPuzzle(attemptsLeft: 2);
    await _resume(tester);

    expect(api.fetchTodayPuzzleCalls, 2);
    expect(find.text('남은 기회 2/5'), findsOne);
  });

  // 글자 크기를 키운 기기(접근성 설정)에서도 잘리거나 겹치지 않아야 한다.
  testWidgets('글자 1.3배에서도 넘치지 않는다', (tester) async {
    await _pumpToday(
      tester,
      api: FakeApiClient(
        puzzle: fakeTodayPuzzle(
          attemptsLeft: 4,
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
          ],
        ),
      ),
      textScale: 1.3,
    );

    expect(tester.takeException(), isNull);
    expect(find.byType(PuzzleBoard), findsOne);
    expect(find.text('제출'), findsOne);
  });

  testWidgets('힌트가 열리면 잠김 문구 대신 힌트가 보인다', (tester) async {
    final api = FakeApiClient(
      puzzle: fakeTodayPuzzle(attemptsLeft: 2, hint: '서울에 많다'),
    );

    await _pumpToday(tester, api: api);

    expect(find.byType(HintCard), findsOne);
    expect(find.text('서울에 많다'), findsOne);
    expect(find.text('힌트는 3번째 오답 후 열려요'), findsNothing);
  });

  // 리뷰 r1 D-25-2/D-25-3: 보드가 있는 상태에서 실패했을 때 복구 경로가 있어야
  // 하고, 앞선 안내가 지금의 오프라인을 가려선 안 된다(US 8, OVERRIDES §7).
  group('보드가 있을 때의 실패 복구', () {
    testWidgets('제출이 오프라인으로 실패해도 배너의 재시도로 입력이 다시 열린다', (tester) async {
      final api = FakeApiClient()
        ..submitGuessError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      await _pumpToday(tester, api: api);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.byType(OfflineBanner), findsOne);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
      // 연결이 돌아와도 앱을 내렸다 올릴 필요는 없다 — 보드 위에 재시도가 있다.
      final retry = find.widgetWithText(TextButton, '다시 시도');
      expect(retry, findsOne);

      api.submitGuessError = null;
      await _tapAndSettle(tester, retry);

      expect(find.byType(OfflineBanner), findsNothing);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isTrue);
      expect(api.fetchTodayPuzzleCalls, 2);
      expect(find.byType(PuzzleBoard), findsOne);
    });

    testWidgets('재조회가 서버 오류로 실패하면 보드 위에 안내 + 재시도가 남는다', (tester) async {
      final api = FakeApiClient();
      await _pumpToday(tester, api: api);

      api.fetchTodayPuzzleError = const ServerApiException(
        code: 'INTERNAL_ERROR',
        message: '서버 오류',
      );
      await _resume(tester);

      // 보드는 그대로 있고, 실패를 숨기지 않는다.
      expect(find.byType(PuzzleBoard), findsOne);
      expect(find.text('다시 불러오지 못했어요. 다시 시도해주세요'), findsOne);
      expect(find.widgetWithText(TextButton, '다시 시도'), findsOne);
      expect(find.byType(OfflineBanner), findsNothing);
      // 서버 오류는 입력을 잠그지 않는다 — 제출은 다시 보낼 수 있다.
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isTrue);

      api.fetchTodayPuzzleError = null;
      await _tapAndSettle(tester, find.widgetWithText(TextButton, '다시 시도'));

      expect(find.text('다시 불러오지 못했어요. 다시 시도해주세요'), findsNothing);
      expect(api.fetchTodayPuzzleCalls, 3);
    });

    // D-25-3: "새 퍼즐이 있어요" 가 떠 있으면 오프라인 판정을 건너뛰었다.
    testWidgets('앞선 안내가 있어도 재조회가 오프라인이면 배너가 뜨고 입력이 잠긴다', (
      tester,
    ) async {
      final api = FakeApiClient(puzzle: fakeTodayPuzzle(puzzleId: 41))
        ..submitGuessError = const PuzzleChangedApiException(
          code: 'PUZZLE_CHANGED',
          message: '퍼즐이 바뀌었어요.',
        );
      await _pumpToday(tester, api: api);

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      api.puzzle = fakeTodayPuzzle(puzzleId: 42);
      await _tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));
      expect(find.text('새 퍼즐이 있어요'), findsOne);

      api.fetchTodayPuzzleError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
      await _resume(tester);

      expect(find.byType(OfflineBanner), findsOne);
      expect(tester.widget<TextField>(find.byType(TextField)).enabled, isFalse);
      expect(
        tester
            .widget<FilledButton>(find.widgetWithText(FilledButton, '제출'))
            .onPressed,
        isNull,
      );
      expect(find.byType(PuzzleBoard), findsOne);
    });
  });

  // 리뷰 r1 D-25-4: OVERRIDES §7 의 타일 뒤집기(350ms, 행 단위 stagger 60ms).
  group('타일 피드백 모션', () {
    testWidgets('제출한 행은 뒤집히며 들어오고 끝나면 변환이 걷힌다', (tester) async {
      await _pumpToday(tester, api: FakeApiClient());
      expect(_flippingRows(), findsNothing, reason: '빈 보드엔 시도 행이 없다');

      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await tester.runAsync(() async {
        await tester.tap(find.widgetWithText(FilledButton, '제출'));
        await tester.pump();
      });

      // 350ms 가 지나기 전엔 아직 뒤집히는 중이다.
      await tester.pump(const Duration(milliseconds: 100));
      expect(_flippingRows(), findsWidgets);

      await tester.pumpAndSettle();
      expect(_flippingRows(), findsNothing);
      expect(find.text('촌'), findsOne);
    });

    testWidgets('모션 감소 설정이면 뒤집지 않고 바로 보여준다', (tester) async {
      final api = FakeApiClient(
        puzzle: fakeTodayPuzzle(
          attemptsLeft: 4,
          attempts: const [
            PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
          ],
        ),
      );

      await _pumpToday(tester, api: api, disableAnimations: true);

      expect(_flippingRows(), findsNothing);
      expect(find.text('촌'), findsOne);
      expect(tester.hasRunningAnimations, isFalse);
    });
  });
}
