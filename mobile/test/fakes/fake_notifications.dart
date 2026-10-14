import 'dart:async';

import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:timezone/timezone.dart' as tz;

/// OS 대기 목록 자리. 플러그인은 플랫폼 채널을 타므로 이 경계만 메모리로
/// 바꾸고 계획·diff·구독은 실제 코드를 그대로 돌린다.
class FakeNotificationScheduler implements NotificationScheduler {
  /// 지금 OS 에 걸려 있는 것: ID → 울릴 순간. 실제 플러그인은 걸 때 적어둔
  /// payload 에서 그 순간을 되읽으므로, 테스트가 **시각을 모른 채** 걸려 있는
  /// 예약(이전 버전이 건 것)을 만들려면 값에 `null` 을 넣는다.
  final Map<int, tz.TZDateTime?> pending = {};
  final List<ScheduledNotification> scheduled = [];
  final List<int> cancelled = [];

  /// 지금 걸려 있는 리마인더 ID(일일 알림 제외) — 기대값을 읽기 쉽게.
  Set<int> get pendingReminders =>
      pending.keys.where((id) => id != NotificationPlan.dailyId).toSet();

  @override
  Future<List<PendingNotification>> pendingNotifications() async => [
    for (final entry in pending.entries)
      PendingNotification(id: entry.key, when: entry.value),
  ];

  @override
  Future<void> cancel(int id) async {
    cancelled.add(id);
    pending.remove(id);
  }

  @override
  Future<void> schedule(ScheduledNotification notification) async {
    scheduled.add(notification);
    pending[notification.id] = notification.when;
  }
}

class InMemoryNotificationSettingsStore implements NotificationSettingsStore {
  InMemoryNotificationSettingsStore({
    this.settings = const NotificationSettings(),
  });

  NotificationSettings settings;
  int writes = 0;

  @override
  Future<NotificationSettings> read() async => settings;

  @override
  Future<void> write(NotificationSettings next) async {
    settings = next;
    writes++;
  }
}

/// 기기 저장소가 통째로 고장난 상태(읽기 실패). 알림이 **조용히 멈추지 않는지**
/// 보는 데 쓴다.
class BrokenNotificationSettingsStore implements NotificationSettingsStore {
  @override
  Future<NotificationSettings> read() async =>
      throw StateError('preferences unavailable');

  @override
  Future<void> write(NotificationSettings settings) async =>
      throw StateError('preferences unavailable');
}

class BrokenCompletedPuzzleDateStore implements CompletedPuzzleDateStore {
  @override
  Future<Set<String>> read() async =>
      throw StateError('preferences unavailable');

  @override
  Future<void> write(Set<String> dates) async =>
      throw StateError('preferences unavailable');
}

/// 시작 read 가 **늦게** 돌아오는 순서를 만드는 저장소. 읽기는 [readGate] 를
/// 열어줄 때까지 매달려 있다 — 그 사이에 퍼즐을 끝내면 두 결과의 도착 순서가
/// 뒤집힌다(D-30-3).
class GatedCompletedPuzzleDateStore implements CompletedPuzzleDateStore {
  final Completer<Set<String>> readGate = Completer<Set<String>>();
  Set<String> dates = <String>{};
  int writes = 0;

  @override
  Future<Set<String>> read() => readGate.future;

  @override
  Future<void> write(Set<String> next) async {
    dates = {...next};
    writes++;
  }
}

class InMemoryCompletedPuzzleDateStore implements CompletedPuzzleDateStore {
  InMemoryCompletedPuzzleDateStore({Set<String>? dates})
    : dates = dates ?? <String>{};

  Set<String> dates;

  @override
  Future<Set<String>> read() async => {...dates};

  @override
  Future<void> write(Set<String> next) async => dates = {...next};
}

/// 기기 시간대 자리. 비행기에서 내린 상황은 [location] 을 바꿔서 만든다.
class FakeDeviceTimeZone implements DeviceTimeZone {
  FakeDeviceTimeZone(this.location);

  tz.Location location;
  int reads = 0;

  @override
  Future<tz.Location> current() async {
    reads++;
    return location;
  }
}
