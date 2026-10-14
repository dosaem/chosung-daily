import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 알림 권한의 세 갈래. OS 가 돌려주는 값은 "켜졌나" 뿐이지만, **아직 묻지
/// 않은 상태**를 거부와 구분해야 S4 설정이 "알림 꺼짐 — 시스템 설정에서 켜기"
/// 를 언제 띄울지 정할 수 있다(티켓 30).
enum NotificationPermission {
  notDetermined,
  granted,
  denied
  ;

  bool get isGranted => this == granted;
}

/// OS 권한 프롬프트 자리. 플랫폼 채널을 타므로 테스트는 이 경계를 바꿔 낀다.
// 멤버가 하나뿐이라 함수 타입으로도 되지만, 스펙 §B.20 의 "알림 서비스 클래스"
// 자리를 이름 있는 타입으로 둔다 — 티켓 30 이 예약·취소를 같은 경계에 더한다.
// ignore: one_member_abstracts
abstract interface class NotificationPermissionRequester {
  Future<NotificationPermission> request();
}

/// `flutter_local_notifications` 의 권한 API. 알림을 실제로 예약하는 건
/// 티켓 30 이고, 여기서는 **사전 안내 뒤 한 번 묻는 것**만 한다.
///
/// Android 13+ 는 `POST_NOTIFICATIONS` 런타임 권한이고(12 이하는 권한 자체가
/// 없어 플러그인이 true 를 돌려준다), iOS 는 alert/badge/sound 를 한 번에 묻는다.
class PluginNotificationPermissionRequester
    implements NotificationPermissionRequester {
  const PluginNotificationPermissionRequester(
    this._plugin, {
    required this.isIos,
  });

  final FlutterLocalNotificationsPlugin _plugin;
  final bool isIos;

  @override
  Future<NotificationPermission> request() async {
    final granted = isIos
        ? await _plugin
              .resolvePlatformSpecificImplementation<
                IOSFlutterLocalNotificationsPlugin
              >()
              ?.requestPermissions(alert: true, badge: true, sound: true)
        : await _plugin
              .resolvePlatformSpecificImplementation<
                AndroidFlutterLocalNotificationsPlugin
              >()
              ?.requestNotificationsPermission();

    // 플러그인이 null 을 주는 건 "그 플랫폼 구현이 없다" 는 뜻이다. 묻지
    // 못했으니 거부로 적지 않는다 — 티켓 30 이 다시 물을 수 있어야 한다.
    return switch (granted) {
      true => NotificationPermission.granted,
      false => NotificationPermission.denied,
      null => NotificationPermission.notDetermined,
    };
  }
}

final notificationPermissionRequesterProvider =
    Provider<NotificationPermissionRequester>(
      (ref) => PluginNotificationPermissionRequester(
        FlutterLocalNotificationsPlugin(),
        isIos: defaultTargetPlatform == TargetPlatform.iOS,
      ),
    );

/// 이번 실행에서 알림 권한이 어떻게 됐는지. 티켓 30 이 알림을 예약할지
/// S4 에 "알림 꺼짐" 을 띄울지 고르는 입력이다.
///
/// 정본은 OS 고 이건 사본이다 — 앱을 껐다 켜면 다시 `notDetermined` 로
/// 시작한다. 30 이 시작할 때 OS 에 현재 상태를 물어 이 값을 채운다.
class NotificationPermissionNotifier extends Notifier<NotificationPermission> {
  @override
  NotificationPermission build() => NotificationPermission.notDetermined;

  /// 사전 안내에서 "알림 켜기" 를 눌렀을 때만 부른다 — 설명 없이 시스템
  /// 프롬프트부터 띄우면 거부당한 뒤 다시 물을 길이 없다(US 35).
  Future<NotificationPermission> request() async {
    final result = await ref
        .read(notificationPermissionRequesterProvider)
        .request();
    if (ref.mounted) state = result;
    return result;
  }
}

final notificationPermissionProvider =
    NotifierProvider<NotificationPermissionNotifier, NotificationPermission>(
      NotificationPermissionNotifier.new,
    );
