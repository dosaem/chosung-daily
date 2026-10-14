import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

ProviderContainer _container(FakeApiClient api) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [apiClientProvider.overrideWithValue(api)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('순위 탭을 열면 상위 20명을 한 번 읽는다', () async {
    final api = FakeApiClient(
      leaderboard: fakeLeaderboard(
        entries: [fakeLeaderboardEntry(rank: 1)],
        me: const MyRank(rank: 1, attempts: 1, seconds: 41),
      ),
    );
    final container = _container(api);

    final board = await container.read(leaderboardProvider.future);

    expect(board?.entries.single.rank, 1);
    expect(api.fetchTodayLeaderboardLimits, [20]);
  });

  test('오늘 그 언어의 퍼즐이 아직 없으면 null — 오류 카드가 아니다', () async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const NoPuzzleTodayApiException(
        code: 'NO_PUZZLE_TODAY',
        message: '아직 준비되지 않았습니다.',
      );
    final container = _container(api);

    expect(await container.read(leaderboardProvider.future), isNull);
  });

  test('네트워크 오류는 오류로 남긴다 — 화면이 오프라인 배너를 고른다', () async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api);

    await expectLater(
      container.read(leaderboardProvider.future),
      throwsA(isA<NetworkApiException>()),
    );
  });

  test('재시도는 다시 읽는다', () async {
    final api = FakeApiClient()
      ..fetchTodayLeaderboardError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api);
    await expectLater(
      container.read(leaderboardProvider.future),
      throwsA(isA<NetworkApiException>()),
    );

    api.fetchTodayLeaderboardError = null;
    container.read(leaderboardProvider.notifier).retry();

    final board = await container.read(leaderboardProvider.future);
    expect(board, isNotNull);
    expect(api.fetchTodayLeaderboardLimits.length, 2);
  });
}
