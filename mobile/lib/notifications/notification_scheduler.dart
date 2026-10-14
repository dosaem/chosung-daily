import 'package:chosung/notifications/notification_plan.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// OS 대기 목록을 읽고 고치는 경계. 플랫폼 채널을 타므로 테스트는 이걸
/// 메모리로 바꿔 끼우고 계획·diff 는 실제 코드를 돌린다.
abstract interface class NotificationScheduler {
  /// 지금 OS 에 걸려 있는 알림 ID. 시각은 알려주지 않는다.
  Future<Set<int>> pendingIds();

  Future<void> cancel(int id);

  Future<void> schedule(ScheduledNotification notification);
}

/// `flutter_local_notifications` 구현.
///
/// 문구는 **예약하는 순간**에 번역한다 — 알림은 앱이 안 떠 있을 때 뜨므로
/// 그때 언어를 고를 방법이 없다. 앱 시작마다 다시 동기화하니 기기 언어를
/// 바꾸면 다음 실행에서 문구가 따라간다.
class PluginNotificationScheduler implements NotificationScheduler {
  const PluginNotificationScheduler(this._plugin);

  /// Android 알림 채널. 사용자가 OS 설정에서 이 채널만 끌 수 있다.
  static const channelId = 'daily_puzzle';

  final FlutterLocalNotificationsPlugin _plugin;

  @override
  Future<Set<int>> pendingIds() async =>
      (await _plugin.pendingNotificationRequests())
          .map((request) => request.id)
          .toSet();

  @override
  Future<void> cancel(int id) => _plugin.cancel(id: id);

  @override
  Future<void> schedule(ScheduledNotification notification) =>
      _plugin.zonedSchedule(
        id: notification.id,
        scheduledDate: notification.when,
        title: 'notification.${notification.kind.name}_title'.tr(),
        body: 'notification.${notification.kind.name}_body'.tr(),
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(
            channelId,
            'notification.channel_name'.tr(),
            channelDescription: 'notification.channel_description'.tr(),
          ),
          iOS: const DarwinNotificationDetails(),
        ),
        // 정확한 알람 권한(`SCHEDULE_EXACT_ALARM`)은 요청하지 않는다 — Play 정책은
        // 알람·캘린더 앱에만 허용하고, 하루 한 번 알림은 몇 분 늦어도 된다.
        // `AllowWhileIdle` 은 Doze 중에도 깨우라는 뜻이다(없으면 하루를 넘겨 뜬다).
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        // 일일 알림만 매일 같은 시각에 반복한다. 리마인더는 1회성이다 —
        // iOS 의 `time` 반복 트리거는 날짜를 버려서 "내일부터" 가 성립하지 않는다.
        matchDateTimeComponents: notification.kind == NotificationKind.daily
            ? DateTimeComponents.time
            : null,
      );
}

final notificationSchedulerProvider = Provider<NotificationScheduler>(
  (ref) => PluginNotificationScheduler(FlutterLocalNotificationsPlugin()),
);
