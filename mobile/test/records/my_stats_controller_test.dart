import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

ProviderContainer _container(FakeApiClient api, {MyStats? startup}) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      startupStatsProvider.overrideWithValue(startup ?? fakeMyStats()),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('처음 값은 시작할 때 읽은 /me/stats 다 — 서버를 다시 부르지 않는다', () {
    final api = FakeApiClient();
    final container = _container(
      api,
      startup: fakeMyStats(currentStreak: 3, maxStreak: 7, solvedCount: 21),
    );

    expect(container.read(myStatsProvider).value?.currentStreak, 3);
    expect(api.fetchMyStatsCalls, 0);
  });

  test('refresh 는 서버에서 다시 읽는다', () async {
    final api = FakeApiClient(stats: fakeMyStats(currentStreak: 1));
    final container = _container(api);
    expect(container.read(myStatsProvider).value?.currentStreak, 0);

    await container.read(myStatsProvider.notifier).refresh();

    expect(api.fetchMyStatsCalls, 1);
    expect(container.read(myStatsProvider).value?.currentStreak, 1);
  });

  test('refresh 가 실패하면 보던 숫자가 그대로 남는다', () async {
    final api = FakeApiClient()
      ..fetchMyStatsError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api, startup: fakeMyStats(currentStreak: 5));

    await container.read(myStatsProvider.notifier).refresh();

    final state = container.read(myStatsProvider);
    expect(state.hasError, isFalse);
    expect(state.value?.currentStreak, 5);
  });
}
