import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:timezone/timezone.dart' as tz;

/// OS 대기 목록 자리. 플러그인은 플랫폼 채널을 타므로 이 경계만 메모리로
/// 바꾸고 계획·diff·구독은 실제 코드를 그대로 돌린다.
class FakeNotificationScheduler implements NotificationScheduler {
  final Set<int> pending = {};
  final List<ScheduledNotification> scheduled = [];
  final List<int> cancelled = [];

  /// 지금 걸려 있는 리마인더 ID(일일 알림 제외) — 기대값을 읽기 쉽게.
  Set<int> get pendingReminders =>
      pending.where((id) => id != NotificationPlan.dailyId).toSet();

  @override
  Future<Set<int>> pendingIds() async => {...pending};

  @override
  Future<void> cancel(int id) async {
    cancelled.add(id);
    pending.remove(id);
  }

  @override
  Future<void> schedule(ScheduledNotification notification) async {
    scheduled.add(notification);
    pending.add(notification.id);
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
