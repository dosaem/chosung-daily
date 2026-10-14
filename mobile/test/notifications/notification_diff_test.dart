import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_sync.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

/// 계획과 OS 대기 목록의 차이만 계산하는 순수 함수. 매번 전부 지우고 다시
/// 걸면 **대기 목록이 비는 순간**이 생기고(그 사이에 기기가 꺼지면 알림이
/// 사라진다) OS 호출도 8번씩 늘어난다.
void main() {
  late tz.Location seoul;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
  });

  ScheduledNotification reminderOn(int day) {
    final when = tz.TZDateTime(seoul, 2026, 10, day, 20);
    return ScheduledNotification(
      id: NotificationPlan.reminderId(when),
      kind: NotificationKind.reminder,
      when: when,
    );
  }

  // `seoul` 은 setUpAll 에서 채워지므로 테스트 안에서 만든다.
  ScheduledNotification dailyAt9() => ScheduledNotification(
    id: NotificationPlan.dailyId,
    kind: NotificationKind.daily,
    when: tz.TZDateTime(seoul, 2026, 10, 15, 9),
  );

  test('대기 목록이 비어 있으면 계획 전부를 새로 건다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(15), reminderOn(16)],
      pendingIds: const {},
    );

    expect(actions.cancel, isEmpty);
    expect(actions.schedule, [dailyAt9(), reminderOn(15), reminderOn(16)]);
  });

  test('이미 걸려 있는 리마인더는 다시 걸지 않는다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(15), reminderOn(16)],
      pendingIds: {NotificationPlan.dailyId, 20261015},
    );

    expect(actions.schedule, contains(reminderOn(16)));
    expect(actions.schedule, isNot(contains(reminderOn(15))));
    expect(actions.cancel, isEmpty);
  });

  test('일일 알림은 이미 걸려 있어도 다시 건다', () {
    // OS 대기 목록은 ID 만 알려주고 **발화 시각은 안 알려준다**. 설정에서 시각을
    // 바꿨는지 ID 로는 알 수 없으므로, 반복 예약 하나는 매번 다시 건다
    // (`zonedSchedule` 은 같은 ID 를 덮어쓴다 — 중복이 생기지 않는다).
    final actions = diffPendingNotifications(
      desired: [dailyAt9()],
      pendingIds: {NotificationPlan.dailyId},
    );

    expect(actions.schedule, [dailyAt9()]);
    expect(actions.cancel, isEmpty);
  });

  test('계획에서 빠진 우리 알림은 취소한다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(16)],
      pendingIds: {NotificationPlan.dailyId, 20261015, 20261016},
    );

    expect(actions.cancel, [20261015]);
  });

  test('우리가 걸지 않은 ID 는 건드리지 않는다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9()],
      pendingIds: {NotificationPlan.dailyId, 7},
    );

    expect(actions.cancel, isEmpty);
  });

  test('계획이 비면 우리 알림을 전부 취소한다 (권한 거부·전부 완료)', () {
    final actions = diffPendingNotifications(
      desired: const [],
      pendingIds: {NotificationPlan.dailyId, 20261015, 20261016},
    );

    expect(actions.cancel, [NotificationPlan.dailyId, 20261015, 20261016]);
    expect(actions.schedule, isEmpty);
  });
}
