import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_permissions.dart';

ProviderContainer _container({
  required bool isIos,
  FakeNotificationPermissionRequester? notifications,
  FakeTrackingAuthorization? tracking,
}) {
  final container = ProviderContainer(
    overrides: [
      isIosProvider.overrideWithValue(isIos),
      notificationPermissionRequesterProvider.overrideWithValue(
        notifications ?? FakeNotificationPermissionRequester(),
      ),
      trackingAuthorizationProvider.overrideWithValue(
        tracking ?? FakeTrackingAuthorization(),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  group('알림 권한', () {
    test('아직 묻지 않았으면 notDetermined 다', () {
      final container = _container(isIos: true);

      expect(
        container.read(notificationPermissionProvider),
        NotificationPermission.notDetermined,
      );
    });

    test('허용하면 granted 가 상태로 남는다(티켓 30 이 읽는다)', () async {
      final requester = FakeNotificationPermissionRequester();
      final container = _container(isIos: false, notifications: requester);

      final result = await container
          .read(notificationPermissionProvider.notifier)
          .request();

      expect(result, NotificationPermission.granted);
      expect(
        container.read(notificationPermissionProvider),
        NotificationPermission.granted,
      );
      expect(requester.requests, 1);
    });

    test('거부하면 denied 가 상태로 남는다', () async {
      final container = _container(
        isIos: true,
        notifications: FakeNotificationPermissionRequester(
          result: NotificationPermission.denied,
        ),
      );

      await container.read(notificationPermissionProvider.notifier).request();

      expect(
        container.read(notificationPermissionProvider),
        NotificationPermission.denied,
      );
    });
  });

  group('ATT', () {
    test('Android 는 추적 권한 자체가 없다 — notSupported 로 시작한다', () {
      final container = _container(isIos: false);

      expect(
        container.read(trackingStatusProvider),
        TrackingStatus.notSupported,
      );
    });

    test('iOS 는 아직 묻기 전이면 notDetermined 다', () {
      final container = _container(isIos: true);

      expect(
        container.read(trackingStatusProvider),
        TrackingStatus.notDetermined,
      );
    });

    // 프롬프트는 기기당 한 번이다 — 두 번째 실행에서 notDetermined 로 남으면
    // 광고 게이트(티켓 31)가 ATT 대기로 영원히 닫힌다.
    test('iOS 두 번째 실행은 시스템에 남은 선택을 읽어온다', () async {
      final container = _container(
        isIos: true,
        tracking: FakeTrackingAuthorization(saved: TrackingStatus.denied),
      );

      expect(
        container.read(trackingStatusProvider),
        TrackingStatus.notDetermined,
      );
      await pumpEventQueue();

      expect(container.read(trackingStatusProvider), TrackingStatus.denied);
    });

    test('프롬프트 결과가 상태로 남는다(티켓 31 광고 게이트가 읽는다)', () async {
      final tracking = FakeTrackingAuthorization(result: TrackingStatus.denied);
      final container = _container(isIos: true, tracking: tracking);

      final result = await container
          .read(trackingStatusProvider.notifier)
          .request();

      expect(result, TrackingStatus.denied);
      expect(container.read(trackingStatusProvider), TrackingStatus.denied);
      expect(tracking.requests, 1);
    });

    test('Android 에서는 프롬프트를 띄우지 않는다', () async {
      final tracking = FakeTrackingAuthorization();
      final container = _container(isIos: false, tracking: tracking);

      final result = await container
          .read(trackingStatusProvider.notifier)
          .request();

      expect(result, TrackingStatus.notSupported);
      expect(tracking.requests, 0);
    });
  });
}
