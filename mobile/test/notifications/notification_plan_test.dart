import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

/// 예약 계획은 순수 함수다 — OS·플러그인·화면 없이 "지금 · 설정 · 완료한 날짜 ·
/// 기기 시간대" 만으로 원하는 대기 목록이 정해진다(스펙 §A.9).
void main() {
  late tz.Location seoul;
  late tz.Location newYork;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
    newYork = tz.getLocation('America/New_York');
  });

  /// 계획의 리마인더 발화 시각만 'MM-dd HH:mm' 로 뽑는다.
  List<String> reminders(List<ScheduledNotification> plan) => plan
      .where((entry) => entry.kind == NotificationKind.reminder)
      .map(
        (entry) =>
            '${_two(entry.when.month)}-${_two(entry.when.day)} '
            '${_two(entry.when.hour)}:${_two(entry.when.minute)}',
      )
      .toList();

  ScheduledNotification daily(List<ScheduledNotification> plan) =>
      plan.singleWhere((entry) => entry.kind == NotificationKind.daily);

  group('일일 알림', () {
    test('아직 안 지난 오늘 시각이면 오늘 발화한다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      expect(daily(plan).when, tz.TZDateTime(seoul, 2026, 10, 15, 9));
      // 반복 예약 1개라 ID 가 고정이다 — 매일 새로 쌓지 않는다.
      expect(daily(plan).id, NotificationPlan.dailyId);
    });

    test('오늘 시각이 지났으면 내일 발화한다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 9, 0, 1),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      expect(daily(plan).when, tz.TZDateTime(seoul, 2026, 10, 16, 9));
    });

    test('이미 푼 날짜여도 일일 알림은 그대로다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {'2026-10-15'},
      );

      expect(daily(plan).when, tz.TZDateTime(seoul, 2026, 10, 15, 9));
    });

    test('고른 시각이 바뀌면 발화 시각도 바뀐다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(
          dailyTime: TimeOfDay(hour: 7, minute: 30),
        ),
        completedKstDates: const {},
      );

      expect(daily(plan).when, tz.TZDateTime(seoul, 2026, 10, 16, 7, 30));
    });
  });

  group('리마인더', () {
    test('앞으로 7일치를 20:00 에 하나씩 잡고 전체는 8개를 넘지 않는다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      expect(reminders(plan), [
        '10-15 20:00',
        '10-16 20:00',
        '10-17 20:00',
        '10-18 20:00',
        '10-19 20:00',
        '10-20 20:00',
        '10-21 20:00',
      ]);
      expect(plan.length, lessThanOrEqualTo(NotificationPlan.maxPending));
      expect(plan.length, 8);
    });

    test('오늘 20:00 이 지났으면 내일부터 7일치다 (롤링 보충)', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 20, 0, 1),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      expect(reminders(plan).first, '10-16 20:00');
      expect(reminders(plan).last, '10-22 20:00');
    });

    test('3일 뒤에 다시 계산하면 지난 것은 빠지고 뒤로 3일이 보충된다', () {
      final before = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );
      final after = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 18, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      expect(reminders(after).first, '10-18 20:00');
      expect(reminders(after).last, '10-24 20:00');
      // 겹치는 날짜는 ID 가 같아야 한다 — 그래야 diff 가 "그대로 두기" 로 읽는다.
      final overlap = before.where(
        (entry) => after.any((kept) => kept.id == entry.id),
      );
      expect(overlap.length, 5, reason: '10-18~10-21 + 일일 알림');
    });

    test('완료한 KST 날짜의 리마인더만 빠지고 다음 날 것은 그대로다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {'2026-10-15'},
      );

      expect(reminders(plan), isNot(contains('10-15 20:00')));
      expect(reminders(plan).first, '10-16 20:00');
      expect(reminders(plan).length, 6);
    });

    test('두 언어 중 하나만 완료해도 그 날짜는 빠진다', () {
      // 완료 집합의 열쇠는 날짜 하나뿐이다 — 언어를 섞어 담지 않는다.
      // 그래서 ko 만 푼 날도 en 만 푼 날도 같은 한 줄이 된다(streak 과 같은 기준).
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {'2026-10-16'},
      );

      expect(reminders(plan), isNot(contains('10-16 20:00')));
      expect(reminders(plan), contains('10-15 20:00'));
      expect(reminders(plan), contains('10-17 20:00'));
    });

    test('스위치를 끄면 리마인더가 하나도 없다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(reminderEnabled: false),
        completedKstDates: const {},
      );

      expect(reminders(plan), isEmpty);
      expect(plan.length, 1);
    });

    test('일일 알림이 20:00 이면 리마인더는 전부 빠진다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(
          dailyTime: TimeOfDay(hour: 20, minute: 0),
        ),
        completedKstDates: const {},
      );

      expect(reminders(plan), isEmpty);
      expect(daily(plan).when, tz.TZDateTime(seoul, 2026, 10, 15, 20));
    });

    test('ID 는 발화 날짜로 정해져 다시 계산해도 같다', () {
      final first = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );
      final second = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 12),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      // 08:00 과 12:00 은 일일 알림의 순서만 다르다(12:00 에는 오늘 09:00 이
      // 지나서 내일로 가고, 오늘 20:00 리마인더가 먼저 온다). ID 집합은 같다.
      expect(
        first.map((entry) => entry.id).toSet(),
        second.map((entry) => entry.id).toSet(),
      );
      expect(
        first.map((entry) => entry.id),
        containsAll([20261015, 20261021]),
      );
    });
  });

  group('기기 시간대', () {
    test('미주 사용자의 20:00 은 KST 로 다음 날이라 그 날짜로 걸러진다', () {
      // 뉴욕 10-15 20:00 EDT = 서울 10-16 09:00. "오늘 풀었으니 리마인더 끄기" 를
      // 로컬 날짜로 판정하면 엉뚱한 날을 끈다.
      final plan = planNotifications(
        now: tz.TZDateTime(newYork, 2026, 10, 15, 7),
        settings: const NotificationSettings(),
        completedKstDates: const {'2026-10-16'},
      );

      expect(reminders(plan), isNot(contains('10-15 20:00')));
      expect(reminders(plan), contains('10-16 20:00'));
      expect(
        NotificationPlan.kstDate(tz.TZDateTime(newYork, 2026, 10, 15, 20)),
        '2026-10-16',
      );
    });

    test('같은 순간이어도 기기 시간대가 바뀌면 발화 순간이 다시 계산된다', () {
      final instant = DateTime.utc(2026, 10, 15);
      final inSeoul = planNotifications(
        now: tz.TZDateTime.from(instant, seoul),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );
      final inNewYork = planNotifications(
        now: tz.TZDateTime.from(instant, newYork),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      // 둘 다 로컬 09:00 이지만 가리키는 순간이 다르다.
      expect(daily(inSeoul).when.hour, 9);
      expect(daily(inNewYork).when.hour, 9);
      expect(
        daily(inSeoul).when.toUtc(),
        isNot(daily(inNewYork).when.toUtc()),
      );
      expect(daily(inSeoul).when.location.name, 'Asia/Seoul');
      expect(daily(inNewYork).when.location.name, 'America/New_York');
    });

    test('DST 가 끝나는 주에도 리마인더는 매일 로컬 20:00 이다', () {
      // 미국 동부는 2026-11-01 에 EDT(-04:00) → EST(-05:00) 로 바뀐다.
      final plan = planNotifications(
        now: tz.TZDateTime(newYork, 2026, 10, 29, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );
      final reminderEntries = plan.where(
        (entry) => entry.kind == NotificationKind.reminder,
      );

      expect(
        reminderEntries.every(
          (entry) => entry.when.hour == 20 && entry.when.minute == 0,
        ),
        isTrue,
      );
      final offsets = reminderEntries
          .map((entry) => entry.when.timeZoneOffset.inHours)
          .toSet();
      expect(offsets, {-4, -5}, reason: 'DST 전·후가 한 창에 같이 들어 있다');
    });
  });

  group('계획의 모양', () {
    test('발화 순서대로 돌려주고 ID 가 겹치지 않는다', () {
      final plan = planNotifications(
        now: tz.TZDateTime(seoul, 2026, 10, 15, 8),
        settings: const NotificationSettings(),
        completedKstDates: const {},
      );

      final times = plan.map((entry) => entry.when).toList();
      expect(times, orderedEquals(List.of(times)..sort()));
      expect(plan.map((entry) => entry.id).toSet(), hasLength(plan.length));
    });

    test('이 앱이 거는 ID 만 우리 것으로 센다', () {
      expect(NotificationPlan.isPlanned(NotificationPlan.dailyId), isTrue);
      expect(NotificationPlan.isPlanned(20261015), isTrue);
      // 다른 SDK(예: Firebase)가 건 알림은 우리가 취소하지 않는다.
      expect(NotificationPlan.isPlanned(42), isFalse);
    });
  });
}

String _two(int value) => value.toString().padLeft(2, '0');
