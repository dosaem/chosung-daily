import 'package:chosung/notifications/notification_plan.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// OS 대기 목록을 읽고 고치는 경계. 플랫폼 채널을 타므로 테스트는 이걸
/// 메모리로 바꿔 끼우고 계획·diff 는 실제 코드를 돌린다.
abstract interface class NotificationScheduler {
  /// 지금 OS 에 걸려 있는 알림(ID 와, 걸 때 적어둔 발화 시각).
  Future<List<PendingNotification>> pendingNotifications();

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
  Future<List<PendingNotification>> pendingNotifications() async =>
      (await _plugin.pendingNotificationRequests())
          .map(
            (request) => PendingNotification(
              id: request.id,
              when: _whenFromPayload(request.payload),
            ),
          )
          .toList();

  @override
  Future<void> cancel(int id) => _plugin.cancel(id: id);

  @override
  Future<void> schedule(ScheduledNotification notification) =>
      _plugin.zonedSchedule(
        id: notification.id,
        scheduledDate: notification.when,
        title: 'notification.${notification.kind.name}_title'.tr(),
        body: 'notification.${notification.kind.name}_body'.tr(),
        // 대기 목록이 **언제 울릴지**를 되읽을 수 있는 유일한 길이다 —
        // 플러그인은 ID·문구·payload 만 돌려준다. 이게 없으면 시간대가 바뀌어
        // 발화 순간이 달라진 예약을 ID 만으로는 알아볼 수 없다.
        payload: _payloadOf(notification),
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

/// payload 에 적는 발화 순간(UTC ISO-8601). 기기 시간대가 바뀌어도 같은
/// 순간은 같은 문자열이라, 걸려 있는 예약과 새 계획을 순간으로 맞출 수 있다.
String _payloadOf(ScheduledNotification notification) =>
    notification.when.toUtc().toIso8601String();

DateTime? _whenFromPayload(String? payload) =>
    payload == null ? null : DateTime.tryParse(payload);

final notificationSchedulerProvider = Provider<NotificationScheduler>(
  (ref) => PluginNotificationScheduler(FlutterLocalNotificationsPlugin()),
);
