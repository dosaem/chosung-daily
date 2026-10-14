import 'package:chosung/notifications/notification_plan.dart';
import 'package:flutter/foundation.dart';

/// 계획을 OS 대기 목록에 맞추려면 무엇을 취소하고 무엇을 새로 걸어야 하는가.
@immutable
class NotificationSyncActions {
  const NotificationSyncActions({required this.cancel, required this.schedule});

  final List<int> cancel;
  final List<ScheduledNotification> schedule;

  bool get isEmpty => cancel.isEmpty && schedule.isEmpty;
}

/// 계획과 OS 대기 목록의 차이만 계산한다(순수 함수).
///
/// 매번 전부 지우고 다시 걸면 **대기 목록이 비는 순간**이 생기고, OS 호출도
/// 동기화마다 8번씩 늘어난다. 그래서 걸려 있는 것과 맞춰 본다 — 리마인더 ID 가
/// 날짜로 정해져 있어서(`NotificationPlan.reminderId`) 다시 계산해도 같은 ID 가
/// 나온다.
///
/// 단, **ID 만으로는 모자란다.** 리마인더 ID 는 로컬 날짜라서 기기 시간대가
/// 바뀌면 같은 ID 라도 울릴 순간이 달라진다(서울 20:00 예약은 뉴욕에서
/// 07:00 이다). 그래서 걸 때 payload 에 적어둔 발화 순간까지 비교해, 순간이
/// 다르거나 **모르는** 예약은 다시 건다(`zonedSchedule` 은 같은 ID 를
/// 덮어쓰므로 중복이 생기지 않는다).
///
/// 일일 알림은 언제나 다시 건다. 반복 트리거라 적어둔 순간은 **첫 발화**일
/// 뿐이고, 한 번 울린 뒤에는 그 순간이 과거로 남아 다음 발화와 맞지 않는다.
NotificationSyncActions diffPendingNotifications({
  required List<ScheduledNotification> desired,
  required List<PendingNotification> pending,
}) {
  final desiredIds = desired.map((entry) => entry.id).toSet();
  final pendingWhen = {for (final entry in pending) entry.id: entry.when};

  return NotificationSyncActions(
    // 우리가 건 ID 범위 안에서만 취소한다 — 다른 SDK 가 건 알림은 남긴다.
    cancel:
        pendingWhen.keys
            .where(NotificationPlan.isPlanned)
            .where((id) => !desiredIds.contains(id))
            .toList()
          ..sort(),
    schedule: desired.where((entry) {
      if (entry.kind == NotificationKind.daily) return true;
      if (!pendingWhen.containsKey(entry.id)) return true;
      final scheduled = pendingWhen[entry.id];
      return scheduled == null || !entry.when.isAtSameMomentAs(scheduled);
    }).toList(),
  );
}
