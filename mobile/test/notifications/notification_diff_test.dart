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
  late tz.Location newYork;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
    newYork = tz.getLocation('America/New_York');
  });

  ScheduledNotification reminderOn(int day, {tz.Location? zone}) {
    final when = tz.TZDateTime(zone ?? seoul, 2026, 10, day, 20);
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

  /// 걸려 있는 그대로 — 예약할 때 적어둔 발화 순간이 payload 로 되읽힌 상태.
  List<PendingNotification> alreadyScheduled(
    List<ScheduledNotification> entries,
  ) => [
    for (final entry in entries)
      PendingNotification(id: entry.id, when: entry.when),
  ];

  test('대기 목록이 비어 있으면 계획 전부를 새로 건다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(15), reminderOn(16)],
      pending: const [],
    );

    expect(actions.cancel, isEmpty);
    expect(actions.schedule, [dailyAt9(), reminderOn(15), reminderOn(16)]);
  });

  test('같은 순간에 이미 걸려 있는 리마인더는 다시 걸지 않는다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(15), reminderOn(16)],
      pending: alreadyScheduled([dailyAt9(), reminderOn(15)]),
    );

    expect(actions.schedule, contains(reminderOn(16)));
    expect(actions.schedule, isNot(contains(reminderOn(15))));
    expect(actions.cancel, isEmpty);
  });

  test('시간대가 바뀌어 발화 순간이 달라진 리마인더는 다시 건다', () {
    // 리마인더 ID 는 **로컬 날짜**다. 비행기에서 내리면 같은 10/15 라도 서울
    // 20:00 예약이 뉴욕에서는 07:00 에 울린다 — ID 가 같다고 넘기면 사용자는
    // 엉뚱한 시각에 알림을 받는다.
    final actions = diffPendingNotifications(
      desired: [reminderOn(15, zone: newYork)],
      pending: alreadyScheduled([reminderOn(15)]),
    );

    expect(actions.schedule, [reminderOn(15, zone: newYork)]);
    expect(actions.cancel, isEmpty);
  });

  test('걸려 있는 순간을 모르는 리마인더는 다시 건다', () {
    // payload 를 적기 전 버전이 건 예약, 또는 읽을 수 없는 payload.
    // "모른다" 를 "맞다" 로 보면 어긋난 예약이 영원히 남는다.
    final actions = diffPendingNotifications(
      desired: [reminderOn(15)],
      pending: const [PendingNotification(id: 20261015, when: null)],
    );

    expect(actions.schedule, [reminderOn(15)]);
    expect(actions.cancel, isEmpty);
  });

  test('일일 알림은 이미 걸려 있어도 다시 건다', () {
    // 반복 트리거라 적어둔 순간은 **첫 발화**일 뿐이다 — 한 번 울린 뒤에는
    // 그 순간이 과거로 남아 다음 발화와 맞지 않는다
    // (`zonedSchedule` 은 같은 ID 를 덮어쓴다 — 중복이 생기지 않는다).
    final actions = diffPendingNotifications(
      desired: [dailyAt9()],
      pending: alreadyScheduled([dailyAt9()]),
    );

    expect(actions.schedule, [dailyAt9()]);
    expect(actions.cancel, isEmpty);
  });

  test('계획에서 빠진 우리 알림은 취소한다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9(), reminderOn(16)],
      pending: alreadyScheduled([
        dailyAt9(),
        reminderOn(15),
        reminderOn(16),
      ]),
    );

    expect(actions.cancel, [20261015]);
  });

  test('우리가 걸지 않은 ID 는 건드리지 않는다', () {
    final actions = diffPendingNotifications(
      desired: [dailyAt9()],
      pending: [
        ...alreadyScheduled([dailyAt9()]),
        const PendingNotification(id: 7, when: null),
      ],
    );

    expect(actions.cancel, isEmpty);
  });

  test('계획이 비면 우리 알림을 전부 취소한다 (권한 거부·전부 완료)', () {
    final actions = diffPendingNotifications(
      desired: const [],
      pending: alreadyScheduled([
        dailyAt9(),
        reminderOn(15),
        reminderOn(16),
      ]),
    );

    expect(actions.cancel, [NotificationPlan.dailyId, 20261015, 20261016]);
    expect(actions.schedule, isEmpty);
  });
}
