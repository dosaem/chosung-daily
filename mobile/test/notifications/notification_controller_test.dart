import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_controller.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/notifications/notification_settings_controller.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

import '../fakes/fake_api_client.dart';
import '../fakes/fake_notifications.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_guest_token_store.dart';

/// 동기화는 "계획 → OS 대기 목록과 diff → 취소/추가" 한 줄이다. 여기서는
/// 그 흐름을 실제 provider 로 돌리고 OS 경계만 가짜로 바꾼다.
/// 고정한 기기 시각(로컬 시). 일일 알림 기본값 09:00 **전**이라 계획은 "일일 →
/// 리마인더" 순으로 나온다 — 09:00 뒤로 바꿔도 이 파일은 통과해야 한다.
const _fixedHour = 8;

void main() {
  // AppLifecycleListener 는 binding 이 있어야 만들어진다.
  final binding = TestWidgetsFlutterBinding.ensureInitialized();

  late tz.Location seoul;
  late tz.Location newYork;

  /// 계획은 "지금" 으로 다음 발화 순간을 고르고 발화 시각 순으로 걸린다. 기기
  /// 시계를 그대로 쓰면 돌리는 시각이 계획을 바꿔(일일 09:00 은 09:00 을
  /// 넘기면 '내일', 리마인더 20:00 은 아직 '오늘') 같은 코드가 아침엔 통과하고
  /// 낮엔 깨진다. 그래서 **시각만** 고정한다 — 날짜는 기기 날짜를 그대로 쓴다
  /// (완료 날짜 정리가 기기 시계의 KST 날짜를 본다 — `pruneCompletedDates`).
  late tz.TZDateTime fixedNow;

  setUpAll(() {
    tz_data.initializeTimeZones();
    seoul = tz.getLocation('Asia/Seoul');
    newYork = tz.getLocation('America/New_York');
  });

  late FakeNotificationScheduler scheduler;
  late InMemoryNotificationSettingsStore settings;
  late InMemoryCompletedPuzzleDateStore completed;
  late FakeDeviceTimeZone timeZone;
  late FakeNotificationPermissionRequester permission;
  late FakeApiClient api;
  late NotificationTaps taps;

  setUp(() {
    scheduler = FakeNotificationScheduler();
    settings = InMemoryNotificationSettingsStore();
    completed = InMemoryCompletedPuzzleDateStore();
    timeZone = FakeDeviceTimeZone(seoul);
    permission = FakeNotificationPermissionRequester();
    api = FakeApiClient();
    taps = NotificationTaps(launchedByNotification: false);
    addTearDown(taps.dispose);
    final deviceToday = tz.TZDateTime.now(seoul);
    fixedNow = tz.TZDateTime(
      seoul,
      deviceToday.year,
      deviceToday.month,
      deviceToday.day,
      _fixedHour,
    );
  });

  ProviderContainer container() {
    final result = ProviderContainer(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        clockProvider.overrideWithValue(() => fixedNow),
        guestTokenStoreProvider.overrideWithValue(
          InMemoryGuestTokenStore('guest-1'),
        ),
        notificationSchedulerProvider.overrideWithValue(scheduler),
        notificationSettingsStoreProvider.overrideWithValue(settings),
        completedPuzzleDateStoreProvider.overrideWithValue(completed),
        deviceTimeZoneProvider.overrideWithValue(timeZone),
        notificationPermissionRequesterProvider.overrideWithValue(permission),
        notificationBootstrapProvider.overrideWithValue(
          NotificationBootstrap(available: true, taps: taps),
        ),
      ],
    );
    addTearDown(result.dispose);
    return result;
  }

  /// 앱 시작처럼 동기화를 켜고 모든 비동기 작업이 가라앉기를 기다린다.
  Future<ProviderContainer> start() async {
    final result = container()..listen(notificationSyncProvider, (_, _) {});
    await pumpEventQueue();
    return result;
  }

  Future<void> resume() async {
    const [
      AppLifecycleState.inactive,
      AppLifecycleState.hidden,
      AppLifecycleState.paused,
      AppLifecycleState.hidden,
      AppLifecycleState.inactive,
      AppLifecycleState.resumed,
    ].forEach(binding.handleAppLifecycleStateChanged);
    await pumpEventQueue();
  }

  group('앱 시작', () {
    test('OS 에 권한 상태를 물어보고 그 결과로 예약한다', () async {
      permission.currentResult = NotificationPermission.granted;

      await start();

      // 28 이 남긴 "앱을 다시 켜면 notDetermined" 는 여기서 메꾼다 —
      // 권한의 정본은 OS 다.
      expect(permission.currentReads, greaterThanOrEqualTo(1));
      expect(
        scheduler.scheduled.map((entry) => entry.kind),
        unorderedEquals([
          NotificationKind.daily,
          ...List.filled(7, NotificationKind.reminder),
        ]),
      );
      // 거는 순서는 종류가 아니라 **발화 시각** 순이다 — 일일 알림이 몇 시인지에
      // 따라 그 자리가 달라진다.
      final when = scheduler.scheduled.map((entry) => entry.when).toList();
      expect(when, orderedEquals(when.toList()..sort()));
      expect(scheduler.pending.length, 8);
      expect(scheduler.cancelled, isEmpty);
    });

    test('권한이 없으면 아무것도 걸지 않고 걸려 있던 우리 알림을 취소한다', () async {
      permission.currentResult = NotificationPermission.denied;
      scheduler.pending.addAll({
        NotificationPlan.dailyId: null,
        20261015: null,
      });

      final result = await start();

      expect(scheduler.scheduled, isEmpty);
      expect(scheduler.cancelled, [NotificationPlan.dailyId, 20261015]);
      expect(result.read(notificationSyncProvider), isEmpty);
    });

    test('이미 걸려 있는 리마인더는 다시 걸지 않는다', () async {
      permission.currentResult = NotificationPermission.granted;
      final now = fixedNow;
      final todayId = NotificationPlan.reminderId(now);
      // 걸려 있는 예약은 **울릴 순간까지** 들고 있다(실제 플러그인은 payload
      // 에서 되읽는다) — 그 순간이 계획과 같으면 다시 걸지 않는다.
      scheduler.pending[todayId] = tz.TZDateTime(
        seoul,
        now.year,
        now.month,
        now.day,
        NotificationPlan.reminderHour,
      );

      await start();

      expect(
        scheduler.scheduled.map((entry) => entry.id),
        isNot(contains(todayId)),
      );
      // 일일 알림은 시각이 바뀌었을 수 있어 매번 다시 건다.
      expect(
        scheduler.scheduled.map((entry) => entry.id),
        contains(NotificationPlan.dailyId),
      );
    });

    test('저장된 설정을 읽어 그 시각으로 건다', () async {
      permission.currentResult = NotificationPermission.granted;
      settings.settings = const NotificationSettings(
        dailyTime: TimeOfDay(hour: 7, minute: 30),
        reminderEnabled: false,
      );

      final result = await start();

      final plan = result.read(notificationSyncProvider);
      expect(plan, hasLength(1));
      expect(plan.single.when.hour, 7);
      expect(plan.single.when.minute, 30);
    });
  });

  group('저장소 고장', () {
    /// 기기 로컬 저장소가 통째로 안 되는 상태. 알림이 **조용히 멈추는** 쪽보다
    /// 기본값으로라도 가는 쪽이 낫다 — 사용자는 알림이 왜 안 오는지 알 길이 없다.
    test('설정·완료 날짜를 못 읽어도 기본값으로 예약한다', () async {
      permission.currentResult = NotificationPermission.granted;
      final broken = ProviderContainer(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          clockProvider.overrideWithValue(() => fixedNow),
          guestTokenStoreProvider.overrideWithValue(
            InMemoryGuestTokenStore('guest-1'),
          ),
          notificationSchedulerProvider.overrideWithValue(scheduler),
          notificationSettingsStoreProvider.overrideWithValue(
            BrokenNotificationSettingsStore(),
          ),
          completedPuzzleDateStoreProvider.overrideWithValue(
            BrokenCompletedPuzzleDateStore(),
          ),
          deviceTimeZoneProvider.overrideWithValue(timeZone),
          notificationPermissionRequesterProvider.overrideWithValue(permission),
          notificationBootstrapProvider.overrideWithValue(
            NotificationBootstrap(available: true, taps: taps),
          ),
        ],
      )..listen(notificationSyncProvider, (_, _) {});
      addTearDown(broken.dispose);

      await pumpEventQueue();

      // 09:00 일일 + 리마인더 7개.
      expect(broken.read(notificationSyncProvider), hasLength(8));
      expect(scheduler.pending, hasLength(8));
    });
  });

  group('설정 변경', () {
    test('시각을 바꾸면 일일 알림을 그 시각으로 다시 건다', () async {
      permission.currentResult = NotificationPermission.granted;
      final result = await start();
      scheduler.scheduled.clear();

      await result
          .read(notificationSettingsProvider.notifier)
          .setDailyTime(const TimeOfDay(hour: 21, minute: 0));
      await pumpEventQueue();

      final daily = result
          .read(notificationSyncProvider)
          .singleWhere((entry) => entry.kind == NotificationKind.daily);
      expect(daily.when.hour, 21);
      expect(
        scheduler.scheduled.map((entry) => entry.when.hour),
        contains(21),
      );
      expect(settings.settings.dailyTime, const TimeOfDay(hour: 21, minute: 0));
    });

    test('리마인더를 끄면 걸려 있던 리마인더가 전부 취소된다', () async {
      permission.currentResult = NotificationPermission.granted;
      final result = await start();
      expect(scheduler.pendingReminders, hasLength(7));

      await result
          .read(notificationSettingsProvider.notifier)
          .setReminderEnabled(enabled: false);
      await pumpEventQueue();

      expect(scheduler.pendingReminders, isEmpty);
      expect(scheduler.pending.keys, {NotificationPlan.dailyId});
      expect(settings.settings.reminderEnabled, isFalse);
    });

    test('다시 켜면 7일치가 돌아온다', () async {
      permission.currentResult = NotificationPermission.granted;
      settings.settings = const NotificationSettings(reminderEnabled: false);
      final result = await start();

      await result
          .read(notificationSettingsProvider.notifier)
          .setReminderEnabled(enabled: true);
      await pumpEventQueue();

      expect(scheduler.pendingReminders, hasLength(7));
    });
  });

  group('퍼즐 완료', () {
    /// 오늘 퍼즐을 끝난 상태로 돌려주게 만든다 — 날짜는 KST 퍼즐 날짜다.
    void finishToday(tz.TZDateTime now) {
      api.puzzle = fakeTodayPuzzle(
        date: DateTime(now.year, now.month, now.day),
        status: PuzzleStatus.success,
        attemptsLeft: 4,
        answer: '지하철역',
      );
    }

    test('그 날짜 리마인더만 취소되고 다음 날 것은 그대로다', () async {
      permission.currentResult = NotificationPermission.granted;
      final now = fixedNow;
      finishToday(now);

      final result = await start();
      // 오늘 퍼즐을 읽는 것 자체가 완료 신호다(다른 기기에서 푼 날도 포함).
      await result.read(todayPuzzleProvider.future);
      await pumpEventQueue();

      final todayId = NotificationPlan.reminderId(now);
      final tomorrowId = NotificationPlan.reminderId(
        tz.TZDateTime(seoul, now.year, now.month, now.day + 1, 20),
      );
      expect(scheduler.pending, isNot(contains(todayId)));
      expect(scheduler.pending, contains(tomorrowId));
      expect(completed.dates, contains(NotificationPlan.kstDate(now)));
    });

    test('두 언어 중 하나만 끝내도 그 날짜는 완료로 적힌다', () async {
      permission.currentResult = NotificationPermission.granted;
      final now = fixedNow;
      finishToday(now);
      api.puzzle = fakeTodayPuzzle(
        date: DateTime(now.year, now.month, now.day),
        language: PuzzleLanguage.en,
        status: PuzzleStatus.fail,
        attemptsLeft: 0,
      );

      final result = await start();
      await result.read(todayPuzzleProvider.future);
      await pumpEventQueue();

      expect(completed.dates, {NotificationPlan.kstDate(now)});
      expect(
        scheduler.pending,
        isNot(contains(NotificationPlan.reminderId(now))),
      );
    });

    test('아직 안 끝난 퍼즐은 완료로 적지 않는다', () async {
      permission.currentResult = NotificationPermission.granted;
      api.puzzle = fakeTodayPuzzle(attemptsLeft: 3);

      final result = await start();
      await result.read(todayPuzzleProvider.future);
      await pumpEventQueue();

      expect(completed.dates, isEmpty);
      expect(scheduler.pendingReminders, hasLength(7));
    });

    test('다시 켜도 저장된 완료 날짜는 그대로 걸러진다', () async {
      permission.currentResult = NotificationPermission.granted;
      final now = fixedNow;
      completed.dates = {NotificationPlan.kstDate(now)};

      await start();

      expect(
        scheduler.pending,
        isNot(contains(NotificationPlan.reminderId(now))),
      );
      expect(scheduler.pendingReminders, hasLength(6));
    });
  });

  group('게스트 토큰·복귀', () {
    test('토큰이 바뀌면 다시 계산한다 (계정·백업 코드 전환)', () async {
      permission.currentResult = NotificationPermission.granted;
      final result = await start();
      scheduler.scheduled.clear();

      // 티켓 29 의 산출물이 아니라 22 의 토큰 상태만 구독한다.
      await result.read(guestTokenProvider.notifier).replaceWith('guest-2');
      await pumpEventQueue();

      expect(
        scheduler.scheduled.map((entry) => entry.kind),
        contains(NotificationKind.daily),
      );
    });

    test('복귀하면 기기 시간대를 다시 읽어 재계산한다', () async {
      permission.currentResult = NotificationPermission.granted;
      final result = await start();
      final before = result.read(notificationSyncProvider).first.when;
      expect(before.location.name, 'Asia/Seoul');

      timeZone.location = newYork;
      await resume();

      final after = result.read(notificationSyncProvider).first.when;
      expect(after.location.name, 'America/New_York');
      expect(timeZone.reads, greaterThan(1));
    });

    test('시간대가 바뀌면 걸려 있던 리마인더도 새 로컬 20:00 으로 다시 건다', () async {
      // 리마인더 ID 는 **로컬 날짜**다. 비행기에서 내리면 같은 날짜 ID 라도
      // 발화 순간이 달라지는데, ID 만 보고 skip 하면 서울 20:00 에 걸린 예약이
      // 뉴욕에서 07:00 에 울린다(D-30-1).
      permission.currentResult = NotificationPermission.granted;
      final result = await start();
      scheduler.scheduled.clear();

      timeZone.location = newYork;
      await resume();

      final plan = result.read(notificationSyncProvider);
      expect(plan, hasLength(8));
      expect(
        scheduler.scheduled,
        containsAll(plan),
        reason: '계획에 있는 알림은 실제로 OS 에 걸려 있어야 한다',
      );
    });

    test('복귀하면 권한도 다시 묻는다 (시스템 설정에서 켜고 돌아온 경우)', () async {
      permission.currentResult = NotificationPermission.denied;
      final result = await start();
      expect(scheduler.scheduled, isEmpty);

      permission.currentResult = NotificationPermission.granted;
      await resume();

      expect(result.read(notificationSyncProvider), hasLength(8));
      expect(scheduler.pending, hasLength(8));
    });
  });

  group('알림 탭', () {
    test('실행 중 탭하면 오늘 퍼즐을 다시 읽는다', () async {
      permission.currentResult = NotificationPermission.granted;
      await start();
      // 완료 감지를 위해 오늘 퍼즐을 구독하므로 시작에 한 번 읽혀 있다.
      expect(api.fetchTodayPuzzleCalls, 1);

      taps.add();
      await pumpEventQueue();

      expect(api.fetchTodayPuzzleCalls, 2);
    });

    test('종료 상태에서 알림으로 켜져도 오늘 퍼즐을 읽는다', () async {
      permission.currentResult = NotificationPermission.granted;
      await taps.dispose();
      taps = NotificationTaps(launchedByNotification: true);
      addTearDown(taps.dispose);

      await start();
      await pumpEventQueue();

      // 시작 조회 1번뿐이다 — 아직 끝나지 않은 첫 조회가 이미 최신 퍼즐을
      // 가져오는 중이라 탭 처리가 같은 조회를 또 띄우지 않는다
      // (`TodayPuzzleNotifier.refresh`). 화면이 오늘 탭으로 가는지는
      // `notification_tap_test.dart` 가 실제 앱으로 본다.
      expect(api.fetchTodayPuzzleCalls, 1);
    });
  });
}
