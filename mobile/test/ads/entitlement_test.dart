import 'package:chosung/config/clock.dart';
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

  // 티켓 33 이 더한 순서 규칙. 떠난 `/me/stats` 조회가 그 사이 들어온 구매
  // 응답(32)을 덮지 않게 하는 자리다 — 둘이 같은 provider 를 쓰기 때문에
  // "같은 곳" 만으로는 순서가 안 정해진다.
  group('관측 시각(observedAt)', () {
    final noon = DateTime.utc(2026, 10, 15, 12);

    ProviderContainer containerAt(DateTime now) {
      final result = ProviderContainer(
        overrides: [clockProvider.overrideWithValue(() => now)],
      );
      addTearDown(result.dispose);
      return result;
    }

    test('시각을 안 넘긴 갱신은 늘 이긴다 (구매·복원 경로)', () {
      final container = containerAt(noon);

      container.read(entitlementProvider.notifier)
        ..update(fakeEntitlement(), observedAt: noon)
        ..update(fakeEntitlement(active: true));

      expect(container.read(entitlementProvider)?.active, isTrue);
    });

    test('지금 값보다 오래된 관측은 버린다', () {
      final container = containerAt(noon);

      container.read(entitlementProvider.notifier)
        ..update(fakeEntitlement(active: true))
        ..update(
          fakeEntitlement(),
          observedAt: noon.subtract(const Duration(minutes: 1)),
        );

      expect(container.read(entitlementProvider)?.active, isTrue);
    });

    test('같은 시각의 관측도 버린다 — 떠난 시각은 묵음의 하한일 뿐이다', () {
      final container = containerAt(noon);

      container.read(entitlementProvider.notifier)
        ..update(fakeEntitlement(active: true))
        ..update(fakeEntitlement(), observedAt: noon);

      expect(container.read(entitlementProvider)?.active, isTrue);
    });

    test('더 뒤에 관측한 사실은 반영한다 — 환불이 늦게 반영되면 안 된다', () {
      final container = containerAt(noon);

      container.read(entitlementProvider.notifier)
        ..update(fakeEntitlement(active: true))
        ..update(
          fakeEntitlement(),
          observedAt: noon.add(const Duration(seconds: 1)),
        );

      expect(container.read(entitlementProvider)?.active, isFalse);
    });

    test('계정이 바뀌면 관측 시각도 버린다', () {
      final container = containerAt(noon);

      container.read(entitlementProvider.notifier)
        ..update(fakeEntitlement(active: true))
        ..clear()
        // 새 계정의 조회는 옛 계정의 관측보다 먼저 떠났을 수 있다.
        ..update(
          fakeEntitlement(),
          observedAt: noon.subtract(const Duration(minutes: 5)),
        );

      expect(container.read(entitlementProvider)?.active, isFalse);
    });
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
