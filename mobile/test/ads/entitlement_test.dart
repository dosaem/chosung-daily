import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';

void main() {
  test('시작 직후에는 권한을 모른다 — null', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    expect(container.read(entitlementProvider), isNull);
  });

  // 티켓 32(구매)·33(갱신·타이머)이 이 한 줄로 광고 상태를 바꾼다.
  test('갱신하면 응답이 그대로 남는다 — 권한과 갱신일이 한 자리에 있다', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    container
        .read(entitlementProvider.notifier)
        .update(
          fakeEntitlement(active: true, until: DateTime.utc(2026, 11)),
        );
    expect(container.read(entitlementProvider)?.active, isTrue);
    expect(container.read(entitlementProvider)?.until, DateTime.utc(2026, 11));

    container.read(entitlementProvider.notifier).update(fakeEntitlement());
    expect(container.read(entitlementProvider)?.active, isFalse);
  });

  test('테스트는 Fake 로 끼운다 — 구독자 상태를 덮어쓸 수 있다', () {
    final container = ProviderContainer(
      overrides: [
        entitlementProvider.overrideWith(
          () => FakeEntitlement(initial: true),
        ),
      ],
    );
    addTearDown(container.dispose);

    expect(container.read(entitlementProvider)?.active, isTrue);
  });
}
