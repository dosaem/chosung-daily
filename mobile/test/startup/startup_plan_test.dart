import 'package:chosung/startup/startup_plan.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';

void main() {
  group('planStartup', () {
    test('점검 중이면 점검 화면으로, 메시지를 그대로 들고 간다', () {
      final plan = planStartup(
        config: fakeAppConfig(maintenance: true, maintenanceMessage: '오전 3시까지'),
        appVersion: '1.0.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.maintenance);
      expect(plan.maintenanceMessage, '오전 3시까지');
    });

    test('점검 메시지가 없어도 점검 화면으로 간다', () {
      final plan = planStartup(
        config: fakeAppConfig(maintenance: true),
        appVersion: '1.0.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.maintenance);
      expect(plan.maintenanceMessage, isNull);
    });

    // 점검이 업데이트보다 먼저다 — 점검 중에는 업데이트해도 못 쓴다.
    test('점검과 구버전이 겹치면 점검 화면이 이긴다', () {
      final plan = planStartup(
        config: fakeAppConfig(maintenance: true, minIos: '9.9.9'),
        appVersion: '1.0.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.maintenance);
    });

    test('버전이 최소 버전보다 낮으면 업데이트 화면 + 스토어 링크', () {
      final plan = planStartup(
        config: fakeAppConfig(
          minIos: '1.2.0',
          storeUrlIos: 'https://apps.apple.com/app/id1',
        ),
        appVersion: '1.1.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.updateRequired);
      expect(plan.storeUrl, 'https://apps.apple.com/app/id1');
    });

    test('플랫폼마다 자기 최소 버전과 자기 스토어 링크를 본다', () {
      // minIos 는 기본값 1.0.0 — 안드로이드만 더 높게 둔다.
      final config = fakeAppConfig(
        minAndroid: '2.0.0',
        storeUrlIos: 'https://apps.apple.com/app/id1',
        storeUrlAndroid: 'https://play.google.com/store/apps/details?id=x',
      );

      expect(
        planStartup(
          config: config,
          appVersion: '1.0.0',
          isIos: true,
        ).destination,
        StartupDestination.home,
      );
      final android = planStartup(
        config: config,
        appVersion: '1.0.0',
        isIos: false,
      );
      expect(android.destination, StartupDestination.updateRequired);
      expect(
        android.storeUrl,
        'https://play.google.com/store/apps/details?id=x',
      );
    });

    // 스토어 등록 전에는 store_urls 가 null 이다 — 화면은 버튼 없이 안내만 띄운다.
    test('스토어 링크가 없어도 업데이트 판정 자체는 그대로다', () {
      final plan = planStartup(
        config: fakeAppConfig(minIos: '2.0.0'),
        appVersion: '1.0.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.updateRequired);
      expect(plan.storeUrl, isNull);
    });

    test('점검도 아니고 버전도 충분하면 홈으로 간다', () {
      final plan = planStartup(
        config: fakeAppConfig(),
        appVersion: '1.0.0',
        isIos: true,
      );

      expect(plan.destination, StartupDestination.home);
      expect(plan.maintenanceMessage, isNull);
      expect(plan.storeUrl, isNull);
    });
  });
}
