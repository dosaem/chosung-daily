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

/// OS 권한 경계. 플랫폼 채널을 타므로 테스트는 이걸 바꿔 낀다.
///
/// 묻는 것([request])과 지금 상태를 읽는 것([current])이 갈려 있다 — 프롬프트는
/// 한 번만 뜨지만(티켓 28, 사전 안내 뒤) 상태는 앱을 켤 때마다·시스템 설정에서
/// 돌아올 때마다 다시 읽어야 한다(티켓 30).
abstract interface class NotificationPermissionRequester {
  Future<NotificationPermission> request();

  Future<NotificationPermission> current();
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
    return _of(granted);
  }

  /// 지금 알림이 켜져 있는가.
  ///
  /// iOS 는 `checkPermissions` 로 "허용/임시 허용" 을 구분해 묻고, Android 는
  /// `areNotificationsEnabled`(13+ 는 `POST_NOTIFICATIONS`, 12 이하는 채널
  /// 설정)을 읽는다. **아직 안 물어본 상태와 거부가 구분되지 않는** 플랫폼이
  /// 있어서(Android), 꺼져 있으면 S4 는 어느 쪽이든 "시스템 설정에서 켜기" 를
  /// 안내한다 — 그 화면이 두 경우 모두에서 사용자가 할 수 있는 유일한 일이다.
  @override
  Future<NotificationPermission> current() async {
    if (!isIos) {
      return _of(
        await _plugin
            .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin
            >()
            ?.areNotificationsEnabled(),
      );
    }

    final options = await _plugin
        .resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin
        >()
        ?.checkPermissions();
    if (options == null) return NotificationPermission.notDetermined;
    return _of(options.isEnabled || options.isProvisionalEnabled);
  }

  static NotificationPermission _of(bool? granted) => switch (granted) {
    true => NotificationPermission.granted,
    false => NotificationPermission.denied,
    null => NotificationPermission.notDetermined,
  };
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
/// 정본은 OS 고 이건 사본이다 — 앱을 껐다 켜면 `notDetermined` 로 시작하고,
/// 알림 동기화(티켓 30)가 시작·복귀마다 [NotificationPermissionNotifier.refresh]
/// 로 OS 에 현재 상태를 물어 채운다.
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

  /// OS 에 지금 상태를 물어 사본을 맞춘다. 앱 시작과 포그라운드 복귀 때
  /// 알림 동기화(티켓 30)가 부른다 — 사용자가 시스템 설정에서 끄고 돌아와도
  /// S4 안내와 예약이 같이 따라가야 한다.
  Future<NotificationPermission> refresh() async {
    final result = await ref
        .read(notificationPermissionRequesterProvider)
        .current();
    if (ref.mounted) state = result;
    return result;
  }
}

final notificationPermissionProvider =
    NotifierProvider<NotificationPermissionNotifier, NotificationPermission>(
      NotificationPermissionNotifier.new,
    );
