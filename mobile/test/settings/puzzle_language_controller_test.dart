import 'dart:async';

import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/ranking/leaderboard_controller.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';

ProviderContainer _container(
  FakeApiClient api, {
  PuzzleLanguage stored = PuzzleLanguage.ko,
  GuestTokenStore? tokenStore,
}) {
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      startupStatsProvider.overrideWithValue(
        fakeMyStats(puzzleLanguage: stored),
      ),
      // 토큰을 실제로 바꿔 보는 테스트만 저장소를 끼운다.
      if (tokenStore != null)
        guestTokenStoreProvider.overrideWithValue(tokenStore),
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

    expect(
      container.read(puzzleLanguageProvider).language,
      PuzzleLanguage.en,
    );
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
    expect(
      container.read(puzzleLanguageProvider).language,
      PuzzleLanguage.en,
    );
    await container.read(todayPuzzleProvider.future);
    await container.read(leaderboardProvider.future);
    expect(api.fetchTodayPuzzleCalls, 2);
    expect(api.fetchTodayLeaderboardLimits.length, 2);
  });

  test('언어를 바꾸면 옛 언어 보드는 새 보드가 오기 전에 사라진다', () async {
    // 다른 언어의 퍼즐은 "보던 걸 바꿔 끼우는 것" 이 아니라 다른 보드다 —
    // 무효화만으로는 다시 읽는 동안 옛 보드가 값으로 남는다(스펙 §A.2,
    // 계정 경계의 D-29-5 와 같은 이유).
    final api = FakeApiClient();
    final container = _container(api);
    expect(
      await container.read(todayPuzzleProvider.future),
      isA<TodayPuzzleReady>(),
    );

    final gate = Completer<void>();
    api.fetchTodayPuzzleGate = gate;
    addTearDown(() {
      if (!gate.isCompleted) gate.complete();
    });

    await container
        .read(puzzleLanguageProvider.notifier)
        .change(
          PuzzleLanguage.en,
        );

    expect(container.read(todayPuzzleProvider).value, isNull);
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
    final setting = container.read(puzzleLanguageProvider);
    expect(setting.language, PuzzleLanguage.ko);
    expect(setting.changing, isFalse);
  });

  // 리뷰(D-27 라운드 1)가 "늦은 응답을 버린다" 는 주장의 직접 사례가 없다고
  // 지적한 자리다 — 떠난 쓰기와 다시 빌드된 정본을 역순으로 도착시켜 본다.
  test('다시 빌드된 뒤 도착한 늦은 응답은 새 정본을 덮지 않는다', () async {
    final gate = Completer<void>();
    final api = FakeApiClient()..updatePuzzleLanguageGate = gate;
    final container = _container(api);

    final pending = container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.en);
    expect(container.read(puzzleLanguageProvider).changing, isTrue);

    // 그 사이 /me/stats 가 다시 읽히면(시작 재시도) 서버 값이 다시 정본이 된다.
    container.invalidate(puzzleLanguageProvider);
    expect(container.read(puzzleLanguageProvider).language, PuzzleLanguage.ko);
    expect(container.read(puzzleLanguageProvider).changing, isFalse);

    // 이제야 도착한 en 응답은 버려진다.
    gate.complete();
    expect(await pending, isFalse);
    expect(container.read(puzzleLanguageProvider).language, PuzzleLanguage.ko);
  });

  test('바꾸는 중에는 다음 요청을 받지 않는다 — 서버 쓰기를 직렬화한다', () async {
    final gate = Completer<void>();
    final api = FakeApiClient()..updatePuzzleLanguageGate = gate;
    final container = _container(api);

    final first = container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.en);
    expect(container.read(puzzleLanguageProvider).changing, isTrue);

    // 응답을 기다리는 동안 들어온 요청은 서버로 나가지 않는다.
    await container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.ko);
    expect(api.updatedPuzzleLanguages, [PuzzleLanguage.en]);

    gate.complete();
    expect(await first, isTrue);
    final setting = container.read(puzzleLanguageProvider);
    expect(setting.language, PuzzleLanguage.en);
    expect(setting.changing, isFalse);
  });

  test('계정이 바뀐 뒤의 탭은 새 계정 언어를 덮어쓰지 않는다', () async {
    // 이 행의 값은 지금 계정의 `/me/stats` 에서 왔다. 계정이 바뀌면 옛 계정
    // 화면에서 고른 언어가 새 계정으로 나가면 안 된다(D-29-5 와 같은 장치).
    final api = FakeApiClient();
    final container = _container(
      api,
      tokenStore: InMemoryGuestTokenStore('guest-a'),
    );
    expect(container.read(puzzleLanguageProvider).language, PuzzleLanguage.ko);

    await container.read(guestTokenProvider.notifier).replaceWith('guest-b');

    final changed = await container
        .read(puzzleLanguageProvider.notifier)
        .change(PuzzleLanguage.en);

    expect(changed, isFalse);
    expect(api.updatedPuzzleLanguages, isEmpty);
    // 행은 바꾸는 중에서 되돌아온다 — 새 계정 값은 그 계정의 stats 가 채운다.
    expect(container.read(puzzleLanguageProvider).language, PuzzleLanguage.ko);
    expect(container.read(puzzleLanguageProvider).changing, isFalse);
  });
}
