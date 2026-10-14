import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/widgets/leaderboard_row.dart';
import 'package:chosung/widgets/seven_day_grid.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 플레이 결과가 생긴 뒤 순위(S3)·내 기록(S4)이 그 결과를 읽는지 본다.
///
/// 탭을 유지하는 셸에서는 탭을 다시 열어도 위젯만 다시 보이고 provider 는
/// 그대로라, 제출이 다른 화면의 데이터를 무효화하지 않으면 방금 올린 기록이
/// 어디에도 안 나온다(US 12·14·16a·16b). 그래서 실제 앱 트리와 라우터로
/// "순위 먼저 보기 → 제출 → 돌아오기" 순서를 그대로 밟는다.
Future<void> _pumpApp(WidgetTester tester, {required FakeApiClient api}) async {
  setViewSize(tester, const Size(390, 844));
  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          guestTokenStoreProvider.overrideWithValue(
            InMemoryGuestTokenStore('guest-token'),
          ),
          // 온보딩은 이미 본 상태 — 여기서 보는 건 플레이 흐름이다.
          onboardingStoreProvider.overrideWithValue(
            InMemoryOnboardingStore(seen: true),
          ),
          appVersionProvider.overrideWith((_) async => '1.0.0'),
          isIosProvider.overrideWithValue(true),
        ],
        child: const AppLocalizationScope(
          startLocale: Locale('ko'),
          child: ChosungApp(),
        ),
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 가짜 ApiClient 의 Future 는 실제 이벤트 루프에서 끝난다 — 탭·제출 뒤에도
/// runAsync 안에서 한 프레임을 돌려야 그 응답이 들어온다.
Future<void> _tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 미풀이 상태로 시작하는 서버. 제출은 정답이고, 그 뒤 서버가 돌려줄 값은
/// 테스트가 직접 바꿔 끼운다(실제 서버가 기록을 올리는 것과 같은 순서다).
FakeApiClient _freshGuestApi() => FakeApiClient(
  // 기본값이 전부 0 이다 — 아직 아무것도 안 푼 게스트.
  stats: fakeMyStats(),
  leaderboard: fakeLeaderboard(
    entries: [fakeLeaderboardEntry(rank: 1, attempts: 2, seconds: 51)],
  ),
  guessResult: fakeGuessResult(isCorrect: true, answer: '지하철역'),
  history: fakeHistory(),
);

/// 정답을 맞힌 뒤의 서버 상태로 바꾼다.
void _serverAfterSolve(FakeApiClient api) {
  api
    ..leaderboard = fakeLeaderboard(
      entries: [
        fakeLeaderboardEntry(rank: 1, isMe: true),
      ],
      me: const MyRank(rank: 1, attempts: 1, seconds: 41),
    )
    ..stats = fakeMyStats(currentStreak: 1, maxStreak: 1, solvedCount: 1)
    ..history = fakeHistory(
      results: const [
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
        {
          PuzzleLanguage.ko: DayResult.success,
          PuzzleLanguage.en: DayResult.none,
        },
      ],
    );
}

/// 첫 오답 한 줄이 쌓인 뒤의 서버 상태로 바꾼다 — 서버 `day_result`
/// (`app/services/game_rules.py`)는 시도 1~4회 오답을 `in_progress` 로 센다.
void _serverAfterFirstWrongGuess(FakeApiClient api) {
  api.history = fakeHistory(
    results: const [
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {PuzzleLanguage.ko: DayResult.none, PuzzleLanguage.en: DayResult.none},
      {
        PuzzleLanguage.ko: DayResult.inProgress,
        PuzzleLanguage.en: DayResult.none,
      },
    ],
  );
}

/// 답을 제출한다(오늘 탭에 있어야 한다).
Future<void> _submit(WidgetTester tester, String guess) async {
  await tester.enterText(find.byType(TextField), guess);
  await tester.pump();
  final submit = find.widgetWithText(FilledButton, '제출');
  await tester.ensureVisible(submit);
  await tester.pumpAndSettle();
  await _tapAndSettle(tester, submit);
}

/// 정답을 제출한다(오늘 탭에 있어야 한다).
Future<void> _submitAnswer(WidgetTester tester) => _submit(tester, '지하철역');

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('D-27-1: 순위를 먼저 본 뒤 정답을 제출하면 내 순위가 갱신된다', (tester) async {
    final api = _freshGuestApi();
    await _pumpApp(tester, api: api);

    // 먼저 순위를 본다 — 아직 미풀이다.
    await _tapAndSettle(tester, find.text('순위'));
    expect(find.text('아직 안 풀었어요'), findsOne);
    expect(api.fetchTodayLeaderboardLimits.length, 1);

    // 오늘 탭으로 돌아가 정답을 맞힌다.
    await _tapAndSettle(tester, find.text('오늘'));
    _serverAfterSolve(api);
    await _submitAnswer(tester);

    // 순위로 복귀하면 내 순위가 보인다.
    await _tapAndSettle(tester, find.text('순위'));
    expect(api.fetchTodayLeaderboardLimits.length, 2);
    expect(find.text('아직 안 풀었어요'), findsNothing);
    // 내 순위 카드가 서버가 준 1위로 바뀌었다("내 순위 #1 · 1회 · 00:00:41").
    expect(find.text('#1 · 1회 · 00:00:41'), findsOne);
    expect(
      tester
          .widgetList<LeaderboardRow>(find.byType(LeaderboardRow))
          .where((row) => row.isMe)
          .length,
      1,
    );
  });

  testWidgets('D-27-2: 내 기록을 먼저 본 뒤 정답을 제출하면 streak·누적·7일이 갱신된다', (
    tester,
  ) async {
    final api = _freshGuestApi();
    await _pumpApp(tester, api: api);

    // 먼저 내 기록을 본다 — 0일/0문제, 오늘은 미플레이다.
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(find.text('0일'), findsNWidgets(2));
    expect(find.text('0문제'), findsOne);
    expect(
      tester.widgetList<DayCell>(find.byType(DayCell)).last.result,
      DayResult.none,
    );

    // 오늘 탭으로 돌아가 정답을 맞힌다.
    await _tapAndSettle(tester, find.text('오늘'));
    _serverAfterSolve(api);
    await _submitAnswer(tester);

    // 내 기록으로 복귀하면 1일/1문제, 오늘 칸은 성공이다.
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(api.fetchMyHistoryDays.length, 2);
    expect(api.fetchMyStatsCalls, 2);
    expect(find.text('1일'), findsNWidgets(2));
    expect(find.text('1문제'), findsOne);
    expect(
      tester.widgetList<DayCell>(find.byType(DayCell)).last.result,
      DayResult.success,
    );
  });

  testWidgets('D-27-2: 제출 뒤 내 기록을 처음 열어도 갱신된 streak 이 보인다', (tester) async {
    final api = _freshGuestApi();
    await _pumpApp(tester, api: api);

    _serverAfterSolve(api);
    await _submitAnswer(tester);

    await _tapAndSettle(tester, find.text('내 기록'));
    expect(find.text('1일'), findsNWidgets(2));
    expect(find.text('1문제'), findsOne);
  });

  testWidgets('D-27-5: 내 기록을 먼저 본 뒤 첫 오답을 내면 오늘 칸이 진행 중으로 바뀐다', (
    tester,
  ) async {
    final api = _freshGuestApi()
      // 기본값이 오답 + 남은 기회 4 다 — 오늘이 끝나지 않는 제출.
      ..guessResult = fakeGuessResult();
    await _pumpApp(tester, api: api);

    // 먼저 내 기록을 본다 — 오늘은 미플레이다.
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(
      tester.widgetList<DayCell>(find.byType(DayCell)).last.result,
      DayResult.none,
    );

    // 오늘 탭으로 돌아가 오답 한 줄을 쌓는다(남은 기회 4 — 아직 안 끝났다).
    await _tapAndSettle(tester, find.text('오늘'));
    _serverAfterFirstWrongGuess(api);
    await _submit(tester, '지하촌역');
    expect(api.submittedGuesses.single.guess, '지하촌역');

    // 내 기록으로 복귀하면 오늘 칸이 진행 중이다 — 서버의 none → in_progress
    // 전이를 화면이 읽어야 한다(US 16a).
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(api.fetchMyHistoryDays.length, 2);
    expect(
      tester.widgetList<DayCell>(find.byType(DayCell)).last.result,
      DayResult.inProgress,
    );
  });

  testWidgets('끝나지 않은 제출은 순위·streak 을 다시 읽지 않고 7일도 첫 줄에만 반응한다', (
    tester,
  ) async {
    final api = _freshGuestApi()..guessResult = fakeGuessResult();
    await _pumpApp(tester, api: api);

    await _tapAndSettle(tester, find.text('순위'));
    await _tapAndSettle(tester, find.text('내 기록'));
    await _tapAndSettle(tester, find.text('오늘'));
    await _submit(tester, '지하촌역');

    // 첫 오답은 7일 칸의 분류를 미플레이 → 진행 중으로 바꾼다.
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(api.fetchMyHistoryDays.length, 2);

    // 두 번째 오답은 같은 진행 중이라 다시 읽을 게 없다.
    await _tapAndSettle(tester, find.text('오늘'));
    api.guessResult = fakeGuessResult(attemptsLeft: 3);
    await _submit(tester, '지하천역');
    await _tapAndSettle(tester, find.text('내 기록'));
    expect(api.submittedGuesses.length, 2);
    expect(api.fetchMyHistoryDays.length, 2);

    // 순위는 푼 사람만 올라가고 streak·누적도 끝난 뒤에 바뀐다.
    await _tapAndSettle(tester, find.text('순위'));
    expect(api.fetchTodayLeaderboardLimits.length, 1);
    expect(api.fetchMyStatsCalls, 1);
  });
}
