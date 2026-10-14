import 'package:chosung/onboarding/onboarding_controller.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/in_memory_onboarding_store.dart';

ProviderContainer _container(InMemoryOnboardingStore store) {
  final container = ProviderContainer(
    overrides: [onboardingStoreProvider.overrideWithValue(store)],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  test('기기에 플래그가 없으면 "아직 안 봤다"', () async {
    final store = InMemoryOnboardingStore();
    final container = _container(store);

    expect(await container.read(onboardingSeenProvider.future), isFalse);
    expect(store.reads, 1);
  });

  test('플래그가 있으면 "봤다" — 다시 보여주지 않는다', () async {
    final container = _container(InMemoryOnboardingStore(seen: true));

    expect(await container.read(onboardingSeenProvider.future), isTrue);
  });

  test('complete() 는 기기에 쓰고 상태도 바로 바꾼다', () async {
    final store = InMemoryOnboardingStore();
    final container = _container(store);
    await container.read(onboardingSeenProvider.future);

    await container.read(onboardingSeenProvider.notifier).complete();

    expect(store.seen, isTrue);
    expect(store.writes, 1);
    expect(container.read(onboardingSeenProvider).value, isTrue);
  });

  // 설정의 "하는 법" 으로 다시 열어도 플래그는 그대로 true 다 — 다시 보기가
  // 첫 실행 분기를 되돌리면 앱을 껐다 켤 때 온보딩이 또 뜬다.
  test('이미 봤으면 complete() 를 다시 불러도 플래그가 유지된다', () async {
    final store = InMemoryOnboardingStore(seen: true);
    final container = _container(store);
    await container.read(onboardingSeenProvider.future);

    await container.read(onboardingSeenProvider.notifier).complete();

    expect(store.seen, isTrue);
    expect(container.read(onboardingSeenProvider).value, isTrue);
  });
}
