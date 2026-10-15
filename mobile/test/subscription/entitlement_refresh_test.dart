import 'dart:async';

import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/account_epoch.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/records/my_stats_controller.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/subscription/entitlement_refresh.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_permissions.dart';

/// 권한 재확인 타이머. 가짜는 셋뿐이다 — 서버(`ApiClient`), 기기 시계
/// (`clockProvider`), 광고 SDK(`AdService`). 타이머·앱 수명·광고 게이트는
/// 실제 코드가 돈다.
///
/// `testWidgets` 를 쓰는 이유: 테스트 본문이 가짜 비동기 구역에서 돌아
/// `tester.pump(간격)` 이 **시간을 건너뛰며 Timer 를 터뜨린다**. 1시간짜리
/// 타이머를 실제로 기다리지 않고 "정확히 그 시각" 을 재현하는 유일한 길이다.
void main() {
  // AppLifecycleListener 는 binding 이 있어야 만들어진다.
  final binding = TestWidgetsFlutterBinding.ensureInitialized();

  /// 기기 시계. 타이머가 터지는 순간 테스트가 이 값을 같이 옮긴다.
  late DateTime now;
  late FakeApiClient api;
  late FakeAdService ads;

  const hour = Duration(hours: 1);

  setUp(() {
    now = DateTime.utc(2026, 10, 15, 12);
    api = FakeApiClient();
    ads = FakeAdService();
  });

  /// 앱 시작. [startup] 은 시작 때 읽은 `/me/stats`(스플래시가 기다리는 응답)다.
  Future<ProviderContainer> start(
    WidgetTester tester, {
    MyStats? startup,
  }) async {
    final result = ProviderContainer(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        startupStatsProvider.overrideWithValue(startup),
        clockProvider.overrideWithValue(() => now),
        isIosProvider.overrideWithValue(false),
        adServiceProvider.overrideWithValue(ads),
        trackingAuthorizationProvider.overrideWithValue(
          FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
        ),
      ],
    );
    // 본문 끝에서 `container.dispose()` 로 끈다 — `testWidgets` 는 본문이
    // 끝나는 자리에서 "남은 Timer 가 없는가" 를 먼저 보고, `addTearDown` 은
    // 그보다 늦게 돌아서 보험으로만 쓸 수 있다.
    addTearDown(result.dispose);
    // 앱 루트(`ChosungApp`)가 하는 일 — 값은 안 쓰고 수명만 잡아둔다.
    result.listen(entitlementRefreshProvider, (_, _) {});
    await tester.pump();
    return result;
  }

  /// 가짜 시계를 [elapsed] 만큼 옮기고 그 시간을 타이머에도 흘려준다.
  Future<void> advance(WidgetTester tester, Duration elapsed) async {
    now = now.add(elapsed);
    await tester.pump(elapsed);
  }

  /// 포그라운드를 떠난다(홈 버튼). 실제 OS 가 보내는 순서 그대로다.
  Future<void> leave(WidgetTester tester) async {
    const [
      AppLifecycleState.inactive,
      AppLifecycleState.hidden,
      AppLifecycleState.paused,
    ].forEach(binding.handleAppLifecycleStateChanged);
    await tester.pump();
  }

  Future<void> comeBack(WidgetTester tester) async {
    const [
      AppLifecycleState.hidden,
      AppLifecycleState.inactive,
      AppLifecycleState.resumed,
    ].forEach(binding.handleAppLifecycleStateChanged);
    await tester.pump();
  }

  group('앱 시작', () {
    testWidgets('시작 응답의 권한이 광고 게이트에 들어간다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      // 상태는 지금 걸린 타이머의 발화 시각이다.
      expect(container.read(entitlementRefreshProvider), now.add(hour));
      expect(api.fetchMyStatsCalls, 0, reason: '시작 응답을 다시 부르지 않는다');
      container.dispose();
    });

    testWidgets('시작이 끝난 뒤 응답이 와도 같은 길로 반영된다', (tester) async {
      final container = await start(tester);

      expect(container.read(entitlementProvider), isNull);
      expect(container.read(entitlementRefreshProvider), isNull);

      await container
          .read(myStatsProvider.notifier)
          .adopt(fakeMyStats(entitled: true, nextCheckAt: now.add(hour)));
      await tester.pump();

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(entitlementRefreshProvider), now.add(hour));
      container.dispose();
    });

    testWidgets('구독 행이 없는 게스트는 타이머가 안 걸린다', (tester) async {
      final container = await start(tester, startup: fakeMyStats());

      expect(container.read(entitlementProvider)?.active, isFalse);
      expect(container.read(entitlementRefreshProvider), isNull);

      await advance(tester, const Duration(hours: 6));

      expect(api.fetchMyStatsCalls, 0);
      container.dispose();
    });
  });

  group('next_check_at 타이머 (가짜 시계)', () {
    testWidgets('정확히 그 시각에 /me/stats 를 부르고 권한 해제를 반영한다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );
      // 환불이 확인돼 서버가 권한 없음을 돌려주기 시작했다(US 30c).
      api.stats = fakeMyStats();
      await tester.pump();

      await advance(tester, hour - const Duration(seconds: 1));
      expect(api.fetchMyStatsCalls, 0, reason: '1초 전에는 아직 안 부른다');
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);

      await advance(tester, const Duration(seconds: 1));

      expect(api.fetchMyStatsCalls, 1);
      expect(container.read(entitlementProvider)?.active, isFalse);
      // 배너 슬롯이 돌아오고 전면 광고도 다시 띄울 수 있다.
      expect(container.read(adGateProvider).showsBannerSlot, isTrue);
      expect(container.read(adGateProvider).canLoadAds, isTrue);
      expect(container.read(entitlementRefreshProvider), isNull);
      container.dispose();
    });

    testWidgets('권한이 유지되면 새 next_check_at 으로 다시 걸린다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );
      api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour * 2));
      await tester.pump();

      await advance(tester, hour);
      expect(api.fetchMyStatsCalls, 1);
      expect(container.read(entitlementRefreshProvider), now.add(hour));

      await advance(tester, hour);

      expect(api.fetchMyStatsCalls, 2);
      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      container.dispose();
    });

    testWidgets('권한이 생기면 배너 슬롯이 사라진다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );
      api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour * 2));
      await tester.pump();

      expect(container.read(adGateProvider).showsBannerSlot, isTrue);

      await advance(tester, hour);

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      container.dispose();
    });

    // 서버는 스토어 조회가 실패하거나 다시 물어볼 이유가 없는 행
    // (expired·revoked)이면 `last_verified_at` 을 올리지 않는다 — 그러면
    // `next_check_at` 이 계속 과거다. "지났으니 지금" 을 그대로 따르면 응답이
    // 다음 호출을 바로 부르는 고리가 된다.
    testWidgets('이미 지난 next_check_at 은 고리가 되지 않고 5분 뒤다', (tester) async {
      final stale = fakeMyStats(
        entitled: true,
        nextCheckAt: now.subtract(const Duration(minutes: 30)),
      );
      final container = await start(tester, startup: stale);
      // 스토어 조회가 계속 실패해 서버가 같은 과거 시각을 다시 준다.
      api.stats = stale;

      expect(
        container.read(entitlementRefreshProvider),
        now.add(EntitlementRefreshController.retryGap),
      );
      expect(api.fetchMyStatsCalls, 0);

      await advance(tester, EntitlementRefreshController.retryGap);
      expect(api.fetchMyStatsCalls, 1);

      // 응답이 또 같은 과거 시각을 줘도 호출은 5분에 한 번이다.
      await advance(tester, EntitlementRefreshController.retryGap * 3);
      expect(api.fetchMyStatsCalls, 4);
      container.dispose();
    });

    testWidgets('조회가 실패하면 보던 권한을 그대로 두고 5분 뒤 다시 묻는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );
      api.fetchMyStatsError = Exception('서버가 죽었다');
      await tester.pump();

      await advance(tester, hour);

      expect(api.fetchMyStatsCalls, 1);
      expect(
        container.read(entitlementProvider)?.active,
        isTrue,
        reason: '저장값 유지',
      );
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      expect(
        container.read(entitlementRefreshProvider),
        now.add(EntitlementRefreshController.retryGap),
      );

      api
        ..fetchMyStatsError = null
        ..stats = fakeMyStats();
      await advance(tester, EntitlementRefreshController.retryGap);

      expect(api.fetchMyStatsCalls, 2);
      expect(container.read(entitlementProvider)?.active, isFalse);
      container.dispose();
    });
  });

  group('앱 상태', () {
    testWidgets('백그라운드에서는 타이머가 멈춘다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );

      await leave(tester);
      expect(container.read(entitlementRefreshProvider), isNull);

      await advance(tester, hour * 5);

      expect(api.fetchMyStatsCalls, 0, reason: '안 보이는 앱은 서버를 부르지 않는다');
      container.dispose();
    });

    testWidgets('복귀하면 next_check_at 을 기다리지 않고 바로 묻는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour * 10)),
      );
      api.stats = fakeMyStats();

      await leave(tester);
      await advance(tester, const Duration(minutes: 3));
      await comeBack(tester);

      expect(api.fetchMyStatsCalls, 1);
      expect(container.read(entitlementProvider)?.active, isFalse);
      expect(container.read(adGateProvider).showsBannerSlot, isTrue);
      container.dispose();
    });

    testWidgets('복귀 뒤에는 새 응답의 시각으로 타이머가 다시 돈다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );

      await leave(tester);
      await advance(tester, hour * 2);
      api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour));
      await comeBack(tester);

      expect(api.fetchMyStatsCalls, 1);
      expect(container.read(entitlementRefreshProvider), now.add(hour));

      await advance(tester, hour);

      expect(api.fetchMyStatsCalls, 2);
      container.dispose();
    });

    // `AppLifecycleListener` 는 직전 상태로 콜백을 고르고, 직전 상태를 모르면
    // (컨트롤러가 선 뒤 첫 알림) 나가는 길에 onHide·onPause 중 하나만 온다 —
    // 그래서 두 쌍을 다 듣는다.
    testWidgets('첫 알림이 paused 로 바로 와도 멈추고 다시 돈다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );

      api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour));

      binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      expect(container.read(entitlementRefreshProvider), isNull);

      await comeBack(tester);

      expect(api.fetchMyStatsCalls, 1);
      expect(container.read(entitlementRefreshProvider), now.add(hour));
      container.dispose();
    });
  });

  // 구현 메모의 "비동기 경로 쌍 표" 에서 막아야 하는 칸들. 조회를 Completer 로
  // 붙잡아 두고 그 사이에 다른 경로를 끼운다(증거 문서 §4 표).
  group('떠난 조회 × 그 사이 끼어든 경로', () {
    /// 타이머를 깨워 조회를 **떠나 있는 상태**로 만든다. 돌려주는 함수를
    /// 부르면 그 조회가 도착한다.
    Future<Future<void> Function()> fetchInFlight(
      WidgetTester tester,
      ProviderContainer container,
    ) async {
      final gate = Completer<void>();
      api.fetchMyStatsGate = gate;
      await advance(tester, hour);
      expect(api.fetchMyStatsCalls, 1, reason: '조회가 떠났다');

      return () async {
        api.fetchMyStatsGate = null;
        gate.complete();
        await tester.pump();
      };
    }

    // 조회가 떠난 뒤 32 의 verify 가 권한을 넣으면, 늦게 도착한 **구매 전**
    // 응답이 그걸 덮어선 안 된다 — `next_check_at` 이 null 이라 타이머도 안
    // 걸려서 돈 낸 사용자가 세션 내내 광고를 본다.
    testWidgets('32 의 구매 응답이 뒤늦은 옛 조회에 덮이지 않는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );
      final arrive = await fetchInFlight(tester, container);

      // 떠난 조회는 "구독 없음" 을 들고 있다. 그 사이 구매가 끝났다.
      container
          .read(entitlementProvider.notifier)
          .update(
            fakeEntitlement(active: true),
          );
      await arrive();

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      container.dispose();
    });

    // 반대 방향은 막지 않는다 — 구매 **뒤에** 떠난 조회는 더 최신 사실이라
    // 환불·hold 를 그대로 반영해야 한다(US 30c).
    testWidgets('구매 뒤에 떠난 조회는 환불을 그대로 반영한다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );
      container
          .read(entitlementProvider.notifier)
          .update(
            fakeEntitlement(active: true),
          );
      api.stats = fakeMyStats();

      final arrive = await fetchInFlight(tester, container);
      await arrive();

      expect(container.read(entitlementProvider)?.active, isFalse);
      expect(container.read(adGateProvider).showsBannerSlot, isTrue);
      container.dispose();
    });

    // D-33-1. 조회 **둘**이 동시에 떠나 있을 수 있다 — 타이머 조회가 아직
    // 안 왔는데 사용자가 홈 → 복귀하면 복귀 조회가 하나 더 떠난다. 떠난
    // 시각을 컨트롤러 필드 한 칸에 들고 있으면 먼저 풀린 조회가 그 칸을
    // 비워서, 나중 조회가 "지금 관측" 으로 들어가 구매를 덮는다.
    testWidgets('타이머 조회와 복귀 조회가 겹쳐도 구매를 덮지 않는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );
      // 조회 A — 타이머가 깨워 떠났다.
      final arrive = await fetchInFlight(tester, container);

      // 홈 → 복귀. 조회 B 가 하나 더 떠난다(A 는 취소되지 않는다).
      await leave(tester);
      await advance(tester, const Duration(minutes: 1));
      await comeBack(tester);
      expect(api.fetchMyStatsCalls, 2, reason: '조회 둘이 떠나 있다');

      // B 가 떠난 뒤 구매가 끝났다.
      now = now.add(const Duration(minutes: 1));
      container
          .read(entitlementProvider.notifier)
          .update(fakeEntitlement(active: true));

      // 둘 다 "구독 없음"(구매 전 사실)을 들고 도착한다.
      await arrive();

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      container.dispose();
    });

    // D-33-2. 플레이 결과 뒤 재조회(25·26)도 같은 `/me/stats` 다 — 이
    // 컨트롤러가 떠나보낸 조회가 아니라고 "지금 관측" 으로 다루면 그 응답이
    // 구매를 덮는다.
    testWidgets('플레이 결과 재조회가 뒤늦게 와도 구매를 덮지 않는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );

      // 제출 → 결과 시트가 떠나보내는 재조회. 이 컨트롤러는 부른 적이 없다.
      final gate = Completer<void>();
      api.fetchMyStatsGate = gate;
      unawaited(container.read(myStatsProvider.notifier).refresh());
      await tester.pump();
      expect(api.fetchMyStatsCalls, 1, reason: '재조회가 떠났다');

      // 결과 시트 → Paywall → 구매가 10초 안에 끝난 경우.
      await advance(tester, const Duration(seconds: 5));
      container
          .read(entitlementProvider.notifier)
          .update(fakeEntitlement(active: true));

      api.fetchMyStatsGate = null;
      gate.complete();
      await tester.pump();

      expect(container.read(entitlementProvider)?.active, isTrue);
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);
      container.dispose();
    });

    // 계정 경계는 29 의 `fetchIfSameAccount` 가 막는다 — 떠난 조회가 돌아와도
    // 남의 계정 값이라 상태에 쓰지 않는다.
    testWidgets('계정이 바뀌면 떠난 조회의 권한을 쓰지 않는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );
      api.stats = fakeMyStats(entitled: true, nextCheckAt: now.add(hour * 5));

      final arrive = await fetchInFlight(tester, container);
      // 계정 전환(연결·전환·삭제)이 토큰을 갈아끼운 자리.
      container.read(accountEpochProvider.notifier).bump();
      container.read(myStatsProvider.notifier).discard();
      await tester.pump();
      await arrive();

      expect(container.read(entitlementProvider), isNull, reason: '아직 모른다');
      expect(container.read(entitlementRefreshProvider), isNull);
      container.dispose();
    });
  });

  group('32 의 구매 응답과 같은 자리를 쓴다', () {
    testWidgets('구매가 넣은 권한을 다음 /me/stats 가 덮는다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(nextCheckAt: now.add(hour)),
      );

      // 티켓 32 의 verify 응답이 하는 일.
      container
          .read(entitlementProvider.notifier)
          .update(
            fakeEntitlement(active: true),
          );
      expect(container.read(adGateProvider).showsBannerSlot, isFalse);

      api.stats = fakeMyStats(nextCheckAt: now.add(hour * 2));
      await advance(tester, hour);

      expect(container.read(entitlementProvider)?.active, isFalse);
      expect(container.read(adGateProvider).showsBannerSlot, isTrue);
      container.dispose();
    });

    testWidgets('계정이 바뀌면 옛 계정 권한을 버린다', (tester) async {
      final container = await start(
        tester,
        startup: fakeMyStats(entitled: true, nextCheckAt: now.add(hour)),
      );
      expect(container.read(entitlementProvider)?.active, isTrue);

      // 계정 경계(연결·전환·삭제)에서 기록을 버리는 자리(티켓 29).
      container.read(myStatsProvider.notifier).discard();
      await tester.pump();

      expect(container.read(entitlementProvider), isNull, reason: '아직 모른다');
      expect(container.read(entitlementRefreshProvider), isNull);

      await advance(tester, hour * 3);
      expect(api.fetchMyStatsCalls, 0, reason: '남의 계정 시각으로 부르지 않는다');
      container.dispose();
    });
  });
}
