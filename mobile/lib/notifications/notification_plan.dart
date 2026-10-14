import 'package:chosung/notifications/notification_settings.dart';
import 'package:flutter/foundation.dart';
import 'package:timezone/timezone.dart' as tz;

enum NotificationKind {
  /// 매일 같은 로컬 시각에 오는 반복 알림 1개("오늘 퍼즐 풀었어요?").
  daily,

  /// 그 날 아직 안 풀었을 때만 로컬 20:00 에 오는 1회성 알림.
  reminder,
}

/// "이 ID 로 이 순간에 알림이 떠 있어야 한다" 한 줄.
@immutable
class ScheduledNotification {
  const ScheduledNotification({
    required this.id,
    required this.kind,
    required this.when,
  });

  final int id;
  final NotificationKind kind;
  final tz.TZDateTime when;

  @override
  bool operator ==(Object other) =>
      other is ScheduledNotification &&
      other.id == id &&
      other.kind == kind &&
      other.when == when;

  @override
  int get hashCode => Object.hash(id, kind, when);

  @override
  String toString() => 'ScheduledNotification($id, ${kind.name}, $when)';
}

/// 예약 규칙의 상수와 ID 규칙(스펙 §A.9).
abstract final class NotificationPlan {
  /// 일일 알림은 ID 가 고정이다 — 반복 예약 하나라 날짜마다 쌓이지 않는다.
  static const dailyId = 1;

  /// 리마인더 발화 시각(로컬).
  static const reminderHour = 20;

  /// 앞으로 며칠치 리마인더를 미리 걸어두는가. 7일 넘게 앱을 안 열면
  /// 리마인더가 멈추는 건 감수한다(스펙 §A.9) — 더 멀리 걸어도 그 사이에
  /// 푼 날을 취소할 기회가 없다.
  static const reminderDays = 7;

  /// 대기 알림 상한(일일 1 + 리마인더 7). iOS 의 64개 상한과는 무관하게,
  /// **지금 OS 에 걸려 있는 게 몇 개인지 세서 설명할 수 있는 수**로 묶었다.
  static const int maxPending = 1 + reminderDays;

  /// 퍼즐 날짜는 서버가 KST 로 정한다 — 기기 시간대가 뭐든 이 기준이다.
  ///
  /// tz 데이터베이스를 뒤지지 않고 고정 +09:00 으로 계산한다. 한국은 1988년
  /// 이후 DST 가 없어서 KST 는 항상 UTC+9 다(서버도 `ZoneInfo("Asia/Seoul")`
  /// 로 같은 값을 쓴다 — `app/config.py`). 덕분에 완료 날짜 계산이 시간대 DB
  /// 초기화 여부와 무관해진다.
  static const kstOffset = Duration(hours: 9);

  /// 리마인더 ID = 발화하는 로컬 날짜(`20261015`). 날짜로 정해지므로 다시
  /// 계산해도 같은 ID 가 나오고, 그래서 OS 대기 목록과 ID 만으로 diff 할 수 있다.
  static int reminderId(tz.TZDateTime when) =>
      when.year * 10000 + when.month * 100 + when.day;

  /// 이 앱이 건 알림인가. 취소는 이 범위 안에서만 한다 — 다른 SDK(FCM 등)가
  /// 건 알림까지 쓸어버리지 않는다.
  static bool isPlanned(int id) => id == dailyId || id >= 20000101;

  /// [when] 이 속한 **KST 날짜**(`yyyy-MM-dd`). 미주 사용자의 로컬 20:00 은
  /// KST 로 다음 날이라, 완료 판정을 로컬 날짜로 하면 엉뚱한 날을 끈다.
  static String kstDate(DateTime when) {
    final inKst = when.toUtc().add(kstOffset);
    return '${inKst.year.toString().padLeft(4, '0')}-'
        '${inKst.month.toString().padLeft(2, '0')}-'
        '${inKst.day.toString().padLeft(2, '0')}';
  }

  /// 지금의 KST 날짜.
  static String todayKstDate() => kstDate(DateTime.now());
}

/// 원하는 대기 목록을 정하는 순수 함수.
///
/// [now] 는 **기기 시간대의** 지금이다(`TZDateTime` 이 존을 들고 다닌다) —
/// 비행기에서 내려 시간대가 바뀌면 같은 순간에도 다른 계획이 나온다. 그래서
/// 포그라운드 복귀마다 로컬 존을 다시 읽어 이 함수를 다시 돌린다.
///
/// [completedKstDates] 는 이 기기에서 이미 끝낸 퍼즐의 KST 날짜(`yyyy-MM-dd`)
/// 집합이다. 날짜 하나가 열쇠라서 **두 언어 중 하나만 풀어도** 그 날은 완료다
/// (7일 그리드·streak 과 같은 기준).
List<ScheduledNotification> planNotifications({
  required tz.TZDateTime now,
  required NotificationSettings settings,
  required Set<String> completedKstDates,
}) {
  final daily = ScheduledNotification(
    id: NotificationPlan.dailyId,
    kind: NotificationKind.daily,
    when: _nextOccurrence(
      now,
      hour: settings.dailyTime.hour,
      minute: settings.dailyTime.minute,
    ),
  );
  // 일일 알림이 이미 20:00 이면 리마인더는 같은 시각에 또 울리는 알림이 된다.
  final collidesWithDaily =
      settings.dailyTime.hour == NotificationPlan.reminderHour &&
      settings.dailyTime.minute == 0;
  if (!settings.reminderEnabled || collidesWithDaily) return [daily];

  final first = _nextOccurrence(now, hour: NotificationPlan.reminderHour);
  final plan = [daily];
  for (var day = 0; day < NotificationPlan.reminderDays; day++) {
    // 날짜 넘침은 생성자가 정리한다(월말·DST 포함) — 로컬 20:00 이 기준이다.
    final when = tz.TZDateTime(
      now.location,
      first.year,
      first.month,
      first.day + day,
      NotificationPlan.reminderHour,
    );
    if (completedKstDates.contains(NotificationPlan.kstDate(when))) continue;
    plan.add(
      ScheduledNotification(
        id: NotificationPlan.reminderId(when),
        kind: NotificationKind.reminder,
        when: when,
      ),
    );
  }

  return plan..sort((a, b) => a.when.compareTo(b.when));
}

/// 오늘의 [hour]:[minute] 이 아직 안 지났으면 오늘, 지났으면 내일.
///
/// 경계(정확히 그 시각)는 내일로 보낸다 — 지금 울릴 알림을 예약해 봐야
/// OS 가 즉시 띄우거나 그냥 버린다.
tz.TZDateTime _nextOccurrence(
  tz.TZDateTime now, {
  required int hour,
  int minute = 0,
}) {
  final today = tz.TZDateTime(
    now.location,
    now.year,
    now.month,
    now.day,
    hour,
    minute,
  );
  return today.isAfter(now)
      ? today
      : tz.TZDateTime(
          now.location,
          now.year,
          now.month,
          now.day + 1,
          hour,
          minute,
        );
}
