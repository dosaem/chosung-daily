import 'package:chosung/account/account_controller.dart';
import 'package:chosung/account/social_sign_in.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/records/history_controller.dart';
import 'package:chosung/settings/puzzle_language_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_local_flag_store.dart';

/// 넘긴 자격 증명을 그대로 돌려주는 가짜 네이티브 로그인. null 을 넣으면
/// "사용자가 창을 닫음", 예외를 넣으면 SDK 실패다.
SocialSignIn _signInReturning(
  SocialCredential? credential, {
  Exception? throwing,
  List<AccountProvider>? calls,
}) => (provider) async {
  calls?.add(provider);
  if (throwing != null) throw throwing;
  return credential;
};

({
  ProviderContainer container,
  InMemoryGuestTokenStore store,
  InMemoryLocalFlagStore flags,
})
_container(
  FakeApiClient api, {
  required SocialSignIn signIn,
  String token = 'guest-token',
  MyStats? startup,
}) {
  final store = InMemoryGuestTokenStore(token);
  final flags = InMemoryLocalFlagStore();
  final container = ProviderContainer(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      guestTokenStoreProvider.overrideWithValue(store),
      localFlagStoreProvider.overrideWithValue(flags),
      socialSignInProvider.overrideWithValue(signIn),
      startupStatsProvider.overrideWithValue(startup ?? fakeMyStats()),
    ],
  );
  addTearDown(container.dispose);
  return (container: container, store: store, flags: flags);
}

const _googleCredential = SocialCredential(
  provider: AccountProvider.google,
  idToken: 'google-id-token',
);

void main() {
  // todayPuzzleProvider 가 AppLifecycleListener 를 만든다.
  TestWidgetsFlutterBinding.ensureInitialized();

  group('구글·애플 연결', () {
    test('id_token 을 교환해 받은 토큰을 저장하고 기록을 다시 읽는다', () async {
      final api = FakeApiClient(
        stats: fakeMyStats(currentStreak: 9),
        nextLinkedToken: 'guest-token',
      );
      final world = _container(
        api,
        signIn: _signInReturning(_googleCredential),
      );
      // 홈·기록이 떠 있는 상태를 만든다 — 전환 뒤 다시 읽는지 보려면 한 번은
      // 읽혀 있어야 한다.
      await world.container.read(todayPuzzleProvider.future);
      await world.container.read(historyProvider.future);
      final puzzleCalls = api.fetchTodayPuzzleCalls;

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(api.exchangedCredentials.single.provider, 'google');
      expect(api.exchangedCredentials.single.idToken, 'google-id-token');
      expect(api.exchangedCredentials.single.authorizationCode, isNull);
      expect(world.store.token, 'guest-token');
      // 로컬 상태 폐기: 보던 퍼즐·기록을 버리고 새 토큰으로 다시 읽는다.
      await world.container.read(todayPuzzleProvider.future);
      await world.container.read(historyProvider.future);
      expect(api.fetchTodayPuzzleCalls, puzzleCalls + 1);
      expect(api.fetchMyStatsCalls, 1);
      expect(world.container.read(accountProvider).error, isNull);
    });

    test('애플은 authorization_code 를 같이 보낸다', () async {
      final api = FakeApiClient();
      final world = _container(
        api,
        signIn: _signInReturning(
          const SocialCredential(
            provider: AccountProvider.apple,
            idToken: 'apple-id-token',
            authorizationCode: 'apple-auth-code',
          ),
        ),
      );

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.apple);

      expect(api.exchangedCredentials.single.provider, 'apple');
      expect(
        api.exchangedCredentials.single.authorizationCode,
        'apple-auth-code',
      );
    });

    test('다른 토큰이 오면 전환이다', () async {
      final api = FakeApiClient(nextLinkedToken: 'other-device-token');
      final world = _container(
        api,
        signIn: _signInReturning(_googleCredential),
      );

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(world.store.token, 'other-device-token');
      expect(world.container.read(accountProvider).switched, isTrue);
    });

    test('같은 토큰이 오면 전환이 아니라 연결이다', () async {
      final api = FakeApiClient(nextLinkedToken: 'guest-token');
      final world = _container(
        api,
        signIn: _signInReturning(_googleCredential),
      );

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(world.container.read(accountProvider).switched, isFalse);
    });

    test('계정을 전환하면 퍼즐 언어도 새 계정 값이 된다', () async {
      final api = FakeApiClient(
        stats: fakeMyStats(puzzleLanguage: PuzzleLanguage.en),
        nextLinkedToken: 'other-device-token',
      );
      final world = _container(
        api,
        signIn: _signInReturning(_googleCredential),
        startup: fakeMyStats(),
      );
      expect(
        world.container.read(puzzleLanguageProvider).language,
        PuzzleLanguage.ko,
      );

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(
        world.container.read(puzzleLanguageProvider).language,
        PuzzleLanguage.en,
      );
    });

    test('사용자가 로그인 창을 닫으면 아무 일도 없다', () async {
      final api = FakeApiClient();
      final world = _container(api, signIn: _signInReturning(null));

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(api.exchangedCredentials, isEmpty);
      expect(world.store.token, 'guest-token');
      final state = world.container.read(accountProvider);
      expect(state.error, isNull);
      expect(state.busy, isFalse);
    });

    test('이미 연결된 계정·틀린 id_token 은 각각의 문구다', () async {
      final already = FakeApiClient()
        ..exchangeIdTokenError = const AccountAlreadyLinkedApiException(
          code: 'ACCOUNT_ALREADY_LINKED',
          message: '',
        );
      final invalid = FakeApiClient()
        ..exchangeIdTokenError = const InvalidIdTokenApiException(
          code: 'INVALID_ID_TOKEN',
          message: '',
        );

      final first = _container(
        already,
        signIn: _signInReturning(_googleCredential),
      );
      await first.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);
      expect(
        first.container.read(accountProvider).error,
        'account.error_already_linked',
      );
      // 실패해도 쓰던 토큰은 그대로다.
      expect(first.store.token, 'guest-token');

      final second = _container(
        invalid,
        signIn: _signInReturning(_googleCredential),
      );
      await second.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);
      expect(
        second.container.read(accountProvider).error,
        'account.error_invalid_id_token',
      );
    });

    test('SDK 가 실패하면 로그인 실패 문구로 눕힌다', () async {
      final api = FakeApiClient();
      final world = _container(
        api,
        signIn: _signInReturning(
          null,
          throwing: const SocialSignInException('no activity'),
        ),
      );

      await world.container
          .read(accountProvider.notifier)
          .link(AccountProvider.google);

      expect(
        world.container.read(accountProvider).error,
        'account.error_sign_in',
      );
    });
  });

  group('백업 코드', () {
    test('200 이면 그 토큰으로 갈아끼우고 다시 읽는다', () async {
      final api = FakeApiClient()
        ..statsByToken['backup-code'] = fakeMyStats(currentStreak: 4);
      final world = _container(api, signIn: _signInReturning(null));

      await world.container
          .read(accountProvider.notifier)
          .restoreWithBackupCode('  backup-code  ');

      // 앞뒤 공백은 붙여넣기에서 흔하다 — 서버로 보내기 전에 떼어낸다.
      expect(api.statsTokens, ['backup-code']);
      expect(world.store.token, 'backup-code');
      expect(world.container.read(accountProvider).switched, isTrue);
      expect(api.fetchMyStatsCalls, 1);
    });

    test('401 이면 토큰을 바꾸지 않고 코드가 틀렸다고 말한다', () async {
      final api = FakeApiClient();
      final world = _container(api, signIn: _signInReturning(null));

      await world.container
          .read(accountProvider.notifier)
          .restoreWithBackupCode('nope');

      expect(world.store.token, 'guest-token');
      expect(
        world.container.read(accountProvider).error,
        'account.error_backup_code',
      );
    });
  });

  group('계정 삭제', () {
    test('DELETE /me 뒤 새 게스트를 발급받아 갈아끼운다', () async {
      final api = FakeApiClient(nextGuestToken: 'fresh-guest');
      final world = _container(api, signIn: _signInReturning(null));
      await world.flags.set(LocalFlag.linkAccountNoticeSeen);
      // 티켓 28 이 더할 기기 단위 플래그 자리 — 삭제가 이것까지 쓸어가면 안 된다.
      world.flags.values['onboarding_done'] = '1';

      await world.container.read(accountProvider.notifier).deleteAccount();

      expect(api.deleteAccountCalls, 1);
      expect(api.createGuestCalls, 1);
      expect(world.store.token, 'fresh-guest');
      expect(await world.flags.isSet(LocalFlag.linkAccountNoticeSeen), isFalse);
      expect(world.flags.values['onboarding_done'], '1');
      expect(world.container.read(accountProvider).error, isNull);
    });

    test('새 게스트 발급이 실패해도 앱이 토큰 없이 남지 않는다', () async {
      // 지운 토큰이라 다음 호출은 401 이지만, 그건 시작 흐름이 새 게스트를
      // 발급해 스스로 복구하는 길이다(StartupNotifier._fetchStats).
      // 토큰이 아예 없으면 그 길조차 없다.
      final api = FakeApiClient()
        ..createGuestError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      final world = _container(api, signIn: _signInReturning(null));

      await world.container.read(accountProvider.notifier).deleteAccount();

      expect(api.deleteAccountCalls, 1);
      expect(world.store.token, isNotNull);
      expect(
        world.container.read(accountProvider).error,
        'account.error_network',
      );
    });

    test('삭제가 실패하면 토큰도 플래그도 그대로다', () async {
      final api = FakeApiClient()
        ..deleteAccountError = const ServerApiException(
          code: 'INTERNAL_ERROR',
          message: '',
        );
      final world = _container(api, signIn: _signInReturning(null));
      await world.flags.set(LocalFlag.linkAccountNoticeSeen);

      await world.container.read(accountProvider.notifier).deleteAccount();

      expect(api.createGuestCalls, 0);
      expect(world.store.token, 'guest-token');
      expect(await world.flags.isSet(LocalFlag.linkAccountNoticeSeen), isTrue);
      expect(
        world.container.read(accountProvider).error,
        'account.error_failed',
      );
    });
  });

  test('도는 동안에는 다음 요청을 받지 않는다', () async {
    final api = FakeApiClient();
    final calls = <AccountProvider>[];
    final world = _container(
      api,
      signIn: _signInReturning(_googleCredential, calls: calls),
    );

    final notifier = world.container.read(accountProvider.notifier);
    final first = notifier.link(AccountProvider.google);
    await notifier.link(AccountProvider.apple);
    await first;

    expect(calls, [AccountProvider.google]);
  });

  test('maskEmail 은 앞 두 글자와 도메인만 남긴다', () {
    expect(maskEmail('hsseo@gmail.com'), 'hs***@gmail.com');
    expect(maskEmail('a@b.com'), 'a***@b.com');
    expect(maskEmail('@b.com'), '***@b.com');
    // 애플 비공개 메일도 같은 규칙이다.
    expect(
      maskEmail('abc123@privaterelay.appleid.com'),
      'ab***@privaterelay.appleid.com',
    );
  });
}
