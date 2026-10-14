import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

/// 알림 탭이 들어오는 자리.
///
/// 네이티브 콜백은 `ProviderScope` 보다 **먼저** 산다 — 종료 상태에서 알림으로
/// 켜지면 Dart 쪽은 아직 아무것도 없다. 그래서 시작 시점에 이 통로를 만들고
/// provider 로 넣어준다(Firebase 초기화 결과와 같은 방식).
class NotificationTaps {
  NotificationTaps({
    required this.launchedByNotification,
    StreamController<void>? controller,
  }) : _controller = controller ?? StreamController<void>.broadcast();

  /// 종료 상태에서 알림을 탭해 앱이 켜졌는가
  /// (`getNotificationAppLaunchDetails`).
  final bool launchedByNotification;

  final StreamController<void> _controller;

  /// 앱이 떠 있는 동안의 탭(`onDidReceiveNotificationResponse`).
  Stream<void> get stream => _controller.stream;

  void add() => _controller.add(null);

  Future<void> dispose() => _controller.close();
}

/// 기기의 IANA 시간대를 읽는 자리.
///
/// `timezone` 패키지는 기기 시간대를 알려주지 않아서(플랫폼 채널이 필요하다)
/// `flutter_timezone` 으로 이름을 받아 존을 고른다. 동기화마다 다시 읽는 이유는
/// **비행기에서 내린 사용자**다 — 복귀 때 존이 그대로면 계획도 그대로다.
// 멤버가 하나지만 함수 타입으로 두지 않는다 — 테스트가 "시간대가 바뀌었다" 를
// 만들려면 상태를 들고 있는 객체여야 하고(마지막으로 성공한 존), 이름이 있는
// 경계가 동기화 흐름에서 읽힌다.
// ignore: one_member_abstracts
abstract interface class DeviceTimeZone {
  Future<tz.Location> current();
}

class PluginDeviceTimeZone implements DeviceTimeZone {
  PluginDeviceTimeZone();

  /// 마지막으로 성공한 존. 한 번 읽히면 그 뒤의 일시적 실패에 UTC 로
  /// 떨어지지 않는다(UTC 로 계획하면 알림이 9시간 어긋난다).
  tz.Location _lastKnown = tz.UTC;

  @override
  Future<tz.Location> current() async {
    try {
      final info = await FlutterTimezone.getLocalTimezone();
      return _lastKnown = tz.getLocation(info.identifier);
    } on Exception catch (error) {
      debugPrint('기기 시간대를 읽지 못해 ${_lastKnown.name} 로 갑니다: $error');
      return _lastKnown;
    }
  }
}

final deviceTimeZoneProvider = Provider<DeviceTimeZone>(
  (ref) => PluginDeviceTimeZone(),
);

@immutable
class NotificationBootstrap {
  const NotificationBootstrap({required this.available, required this.taps});

  /// 시작할 때 알림 플러그인이 실제로 떴는가.
  ///
  /// 안 떴으면(미지원 플랫폼, 시작 경로를 안 거친 위젯 테스트) 알림 기능 전체를
  /// 끈다 — 플러그인 없이 OS 를 부르면 `late` 플랫폼 인스턴스에서 그냥 터진다.
  final bool available;

  final NotificationTaps taps;
}

/// 시작 경로를 거치지 않은 환경의 기본값 — 알림 없음(Firebase 와 같은 방식).
final notificationBootstrapProvider = Provider<NotificationBootstrap>((ref) {
  final taps = NotificationTaps(launchedByNotification: false);
  ref.onDispose(taps.dispose);
  return NotificationBootstrap(available: false, taps: taps);
});

/// 시간대 DB 를 올리고 알림 플러그인을 초기화한다(`main` 에서 한 번).
///
/// 권한은 여기서 묻지 않는다 — iOS 는 `requestXPermission: false` 로 꺼둔다.
/// 사전 안내 뒤에 묻는 건 온보딩(티켓 28)의 일이고, 초기화만으로 프롬프트가
/// 뜨면 그 순서가 깨진다.
Future<NotificationBootstrap> initializeNotifications({
  FlutterLocalNotificationsPlugin? plugin,
  Future<String> Function()? readTimeZoneName,
}) async {
  tz_data.initializeTimeZones();
  tz.setLocalLocation(await _localLocation(readTimeZoneName));

  final notifications = plugin ?? FlutterLocalNotificationsPlugin();
  final taps = StreamController<void>.broadcast();
  var launchedByNotification = false;
  var available = false;
  try {
    await notifications.initialize(
      settings: const InitializationSettings(
        // 알림 아이콘은 런처 아이콘을 쓴다(티켓 35 가 전용 아이콘을 넣기 전까지).
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(
          requestAlertPermission: false,
          requestBadgePermission: false,
          requestSoundPermission: false,
        ),
      ),
      onDidReceiveNotificationResponse: (_) => taps.add(null),
    );
    final launch = await notifications.getNotificationAppLaunchDetails();
    launchedByNotification = launch?.didNotificationLaunchApp ?? false;
    available = true;
    // 플러그인이 없는 환경(테스트·미지원 플랫폼)에서도 앱은 떠야 한다. `late`
    // 플랫폼 인스턴스는 Exception 이 아니라 Error 로 터지므로 둘 다 받는다.
  } on Exception catch (error) {
    debugPrint('알림 초기화를 건너뜁니다: $error');
    // 플랫폼 인스턴스가 `late` 필드라 LateInitializationError 로 터진다 —
    // Exception 이 아니라서 따로 받아야 한다.
    // ignore: avoid_catching_errors
  } on Error catch (error) {
    debugPrint('알림 플러그인이 없어 알림을 끕니다: $error');
  }

  return NotificationBootstrap(
    available: available,
    taps: NotificationTaps(
      launchedByNotification: launchedByNotification,
      controller: taps,
    ),
  );
}

Future<tz.Location> _localLocation(
  Future<String> Function()? readTimeZoneName,
) async {
  try {
    final name =
        await (readTimeZoneName ??
            () async =>
                (await FlutterTimezone.getLocalTimezone()).identifier)();
    return tz.getLocation(name);
  } on Exception catch (error) {
    // UTC 로 떨어지면 알림 시각이 어긋나지만, 여기서 던지면 앱이 아예 못 뜬다.
    debugPrint('기기 시간대를 읽지 못해 UTC 로 시작합니다: $error');
    return tz.UTC;
  }
}
