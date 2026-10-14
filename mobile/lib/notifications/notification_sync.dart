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
/// 동기화마다 8번씩 늘어난다. 그래서 ID 로 맞춰 본다 — 리마인더 ID 가 날짜로
/// 정해져 있어서(`NotificationPlan.reminderId`) 다시 계산해도 같은 ID 가 나온다.
///
/// 예외가 하나 있다: **일일 알림은 매번 다시 건다.** 대기 목록은 ID 만 알려주고
/// 발화 시각은 안 알려줘서, 설정에서 시각을 바꿨는지 ID 로는 알 수 없다.
/// `zonedSchedule` 은 같은 ID 를 덮어쓰므로 중복이 생기지 않는다.
NotificationSyncActions diffPendingNotifications({
  required List<ScheduledNotification> desired,
  required Set<int> pendingIds,
}) {
  final desiredIds = desired.map((entry) => entry.id).toSet();

  return NotificationSyncActions(
    // 우리가 건 ID 범위 안에서만 취소한다 — 다른 SDK 가 건 알림은 남긴다.
    cancel:
        pendingIds
            .where(NotificationPlan.isPlanned)
            .where((id) => !desiredIds.contains(id))
            .toList()
          ..sort(),
    schedule: desired
        .where(
          (entry) =>
              entry.kind == NotificationKind.daily ||
              !pendingIds.contains(entry.id),
        )
        .toList(),
  );
}
