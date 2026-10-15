import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/in_memory_guest_token_store.dart';

ProviderContainer _container(GuestTokenStore store) {
  final container = ProviderContainer(
    overrides: [guestTokenStoreProvider.overrideWithValue(store)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('secure storage 에 있던 토큰을 복원한다', () async {
    final container = _container(InMemoryGuestTokenStore('stored-token'));

    expect(await container.read(guestTokenProvider.future), 'stored-token');
  });

  test('저장된 토큰이 없으면 null 로 시작한다', () async {
    final container = _container(InMemoryGuestTokenStore());

    expect(await container.read(guestTokenProvider.future), isNull);
  });

  // 티켓 29(계정 연결·전환)이 교환받은 토큰으로 갈아끼운다.
  test('replaceWith 는 상태와 저장소를 함께 갱신한다', () async {
    final store = InMemoryGuestTokenStore('guest-token');
    final container = _container(store);
    await container.read(guestTokenProvider.future);

    await container
        .read(guestTokenProvider.notifier)
        .replaceWith('linked-token');

    expect(container.read(guestTokenProvider).value, 'linked-token');
    expect(store.token, 'linked-token');
  });

  test('clear 는 저장소에서도 지운다', () async {
    final store = InMemoryGuestTokenStore('guest-token');
    final container = _container(store);
    await container.read(guestTokenProvider.future);

    await container.read(guestTokenProvider.notifier).clear();

    expect(container.read(guestTokenProvider).value, isNull);
    expect(store.token, isNull);
    expect(store.deletes, 1);
  });

  // 티켓 30(로컬 알림)이 토큰 변경을 구독한다.
  test('토큰 변경을 구독할 수 있다', () async {
    final container = _container(InMemoryGuestTokenStore('first'));
    final seen = <String?>[];
    container.listen(guestTokenProvider, (_, next) => seen.add(next.value));
    await container.read(guestTokenProvider.future);

    await container.read(guestTokenProvider.notifier).replaceWith('second');
    await container.read(guestTokenProvider.notifier).clear();

    expect(seen, ['first', 'second', null]);
  });

  // ApiClient 는 이 provider 의 값을 매 요청마다 읽어간다(토큰을 품지 않는다).
  test('현재 토큰을 동기로 읽어 Bearer 헤더에 쓸 수 있다', () async {
    final container = _container(InMemoryGuestTokenStore('guest-token'));
    await container.read(guestTokenProvider.future);

    expect(container.read(guestTokenProvider).value, 'guest-token');
  });
}
