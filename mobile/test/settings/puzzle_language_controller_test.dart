import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

ProviderContainer _container(
  FakeApiClient api, {
  PuzzleLanguage stored = PuzzleLanguage.ko,
}) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      startupStatsProvider.overrideWithValue(
        fakeMyStats(puzzleLanguage: stored),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  test('처음 값은 시작할 때 읽은 /me/stats 의 퍼즐 언어다', () {
    final container = _container(FakeApiClient(), stored: PuzzleLanguage.en);

    expect(container.read(puzzleLanguageProvider), PuzzleLanguage.en);
  });

  test('언어를 바꾸면 PATCH /me 를 보내고 홈·순위를 다시 읽는다', () async {
    final api = FakeApiClient();
    final container = _container(api);
    // 홈 탭과 순위 탭이 이미 떠 있는 상태를 만든다(셸이 세 탭을 다 살려 둔다).
    await container.read(todayPuzzleProvider.future);
    await container.read(leaderboardProvider.future);

    final changed = await container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.en);

    expect(changed, isTrue);
    expect(api.updatedPuzzleLanguages, [PuzzleLanguage.en]);
    expect(container.read(puzzleLanguageProvider), PuzzleLanguage.en);
    await container.read(todayPuzzleProvider.future);
    await container.read(leaderboardProvider.future);
    expect(api.fetchTodayPuzzleCalls, 2);
    expect(api.fetchTodayLeaderboardLimits.length, 2);
  });

  test('같은 언어를 다시 고르면 서버를 부르지 않는다', () async {
    final api = FakeApiClient();
    final container = _container(api);

    final changed = await container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.ko);

    expect(changed, isTrue);
    expect(api.updatedPuzzleLanguages, isEmpty);
  });

  test('바꾸지 못하면 false 를 돌려주고 언어는 그대로다', () async {
    final api = FakeApiClient()
      ..updatePuzzleLanguageError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api);

    final changed = await container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.en);

    expect(changed, isFalse);
    expect(container.read(puzzleLanguageProvider), PuzzleLanguage.ko);
  });
}
