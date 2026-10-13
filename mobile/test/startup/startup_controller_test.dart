import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/startup/startup_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';

ProviderContainer _container({
  required FakeApiClient api,
  required GuestTokenStore store,
  String appVersion = '1.0.0',
  bool isIos = true,
  PuzzleLanguage deviceLanguage = PuzzleLanguage.ko,
}) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      guestTokenStoreProvider.overrideWithValue(store),
      appVersionProvider.overrideWith((_) async => appVersion),
      isIosProvider.overrideWithValue(isIos),
      devicePuzzleLanguageProvider.overrideWithValue(deviceLanguage),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('점검 중이면 점검 상태로 끝난다', () async {
    final api = FakeApiClient(
      config: fakeAppConfig(maintenance: true, maintenanceMessage: '오전 3시까지'),
    );
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    final state = await container.read(startupProvider.future);

    expect(state, isA<StartupMaintenance>());
    expect((state as StartupMaintenance).message, '오전 3시까지');
    // 점검 중에는 내 기록을 부르지 않는다.
    expect(api.fetchMyStatsCalls, 0);
  });

  test('최소 버전보다 낮으면 업데이트 상태로 끝난다', () async {
    final api = FakeApiClient(
      config: fakeAppConfig(minIos: '2.0.0', storeUrlIos: 'https://store'),
    );
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    final state = await container.read(startupProvider.future);

    expect(state, isA<StartupUpdateRequired>());
    expect((state as StartupUpdateRequired).storeUrl, 'https://store');
    expect(api.fetchMyStatsCalls, 0);
  });

  test('정상이면 내 기록까지 읽고 준비 상태가 된다', () async {
    final api = FakeApiClient(stats: fakeMyStats(currentStreak: 4));
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    final state = await container.read(startupProvider.future);

    expect(state, isA<StartupReady>());
    expect((state as StartupReady).stats.currentStreak, 4);
  });

  test('저장된 토큰이 없으면 게스트를 발급해 저장한다', () async {
    final api = FakeApiClient(nextGuestToken: 'issued');
    final store = InMemoryGuestTokenStore();
    final container = _container(api: api, store: store);

    await container.read(startupProvider.future);

    expect(api.createGuestLanguages, [PuzzleLanguage.ko]);
    expect(store.token, 'issued');
    expect(container.read(guestTokenProvider).value, 'issued');
  });

  test('기기 언어가 en 이면 en 게스트로 발급한다', () async {
    final api = FakeApiClient();
    final container = _container(
      api: api,
      store: InMemoryGuestTokenStore(),
      deviceLanguage: PuzzleLanguage.en,
    );

    await container.read(startupProvider.future);

    expect(api.createGuestLanguages, [PuzzleLanguage.en]);
  });

  test('저장된 토큰이 있으면 발급하지 않는다', () async {
    final api = FakeApiClient();
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    await container.read(startupProvider.future);

    expect(api.createGuestCalls, 0);
  });

  // 서버에서 지워진 토큰(계정 삭제·DB 초기화)으로 들어오면 401 이 온다.
  test('내 기록이 401 이면 새 게스트를 발급하고 다시 읽는다', () async {
    final api = FakeApiClient(nextGuestToken: 'fresh')
      ..fetchMyStatsError = const UnauthorizedApiException(
        code: 'UNAUTHORIZED',
        message: '인증이 필요합니다.',
      );
    final store = InMemoryGuestTokenStore('stale');
    final container = _container(api: api, store: store)
      // 두 번째 호출은 성공하도록, 첫 401 뒤에 에러를 치운다.
      ..listen(guestTokenProvider, (_, next) {
        if (next.value == 'fresh') api.fetchMyStatsError = null;
      });

    final state = await container.read(startupProvider.future);

    expect(state, isA<StartupReady>());
    expect(api.fetchMyStatsCalls, 2);
    expect(store.token, 'fresh');
    expect(container.read(guestTokenProvider).value, 'fresh');
  });

  test('새 게스트로도 401 이면 예외를 올린다', () async {
    final api = FakeApiClient()
      ..fetchMyStatsError = const UnauthorizedApiException(
        code: 'UNAUTHORIZED',
        message: '인증이 필요합니다.',
      );
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    await expectLater(
      container.read(startupProvider.future),
      throwsA(isA<UnauthorizedApiException>()),
    );
    expect(api.fetchMyStatsCalls, 2);
  });

  test('/config 가 실패하면 에러 상태가 된다', () async {
    final api = FakeApiClient()
      ..fetchConfigError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));

    await expectLater(
      container.read(startupProvider.future),
      throwsA(isA<NetworkApiException>()),
    );
  });

  test('retry 는 처음부터 다시 돌린다', () async {
    final api = FakeApiClient()
      ..fetchConfigError = const NetworkApiException(
        code: networkErrorCode,
        message: 'offline',
      );
    final container = _container(api: api, store: InMemoryGuestTokenStore('t'));
    await expectLater(
      container.read(startupProvider.future),
      throwsA(anything),
    );

    api.fetchConfigError = null;
    container.read(startupProvider.notifier).retry();

    expect(await container.read(startupProvider.future), isA<StartupReady>());
    expect(api.fetchConfigCalls, 2);
  });
}
