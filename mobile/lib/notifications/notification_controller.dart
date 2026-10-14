import 'dart:async';

import 'package:chosung/guest/guest_token_provider.dart';
import 'package:chosung/notifications/completed_puzzle_dates.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:chosung/notifications/notification_settings_controller.dart';
import 'package:chosung/notifications/notification_sync.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/puzzle/today_puzzle_controller.dart';
import 'package:chosung/puzzle/today_puzzle_state.dart';
import 'package:chosung/routing/app_router.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timezone/timezone.dart' as tz;

/// 로컬 알림 동기화. 상태는 **지금 OS 에 걸려 있어야 하는 계획**이다.
///
/// 계획을 바꿀 수 있는 사건을 전부 여기서 구독한다(스펙 §A.9) — 앱 시작,
/// 포그라운드 복귀, 퍼즐 완료, 알림 탭, 설정 변경, 게스트 토큰 교체. 사건마다
/// 다시 계산해 OS 대기 목록과 diff 하므로, 각 사건이 "무엇을 취소하고 무엇을
/// 걸지" 를 따로 알 필요가 없다.
class NotificationSyncController extends Notifier<List<ScheduledNotification>> {
  /// 동기화가 겹치면 OS 호출이 뒤섞여 **방금 건 알림을 취소**할 수 있다
  /// (앞선 동기화가 들고 있던 대기 목록이 이미 옛것이다). 그래서 한 번에
  /// 하나만 돌리고, 그 사이에 들어온 요청은 한 번으로 묶어 뒤에 돌린다.
  bool _syncing = false;
  bool _queued = false;

  /// OS 에 권한 상태를 한 번이라도 물어봤는가.
  ///
  /// 묻기 전에는 대기 목록을 건드리지 않는다 — 앱을 켠 직후의 사본은
  /// `notDetermined` 라서, 그대로 동기화하면 **지난 실행에서 걸어둔 알림을
  /// 전부 취소했다가 곧 다시 거는** 짓을 매번 한다(그 사이 기기가 꺼지면
  /// 알림이 사라진다).
  bool _permissionKnown = false;

  @override
  List<ScheduledNotification> build() {
    final bootstrap = ref.read(notificationBootstrapProvider);
    // 플러그인이 안 떴으면 아무것도 구독하지 않는다 — 구독만 걸어도 저장소·OS
    // 를 건드리게 되고, 알림과 상관없는 화면 테스트가 같이 넘어진다.
    if (!bootstrap.available) return const [];

    // 복귀: 기기 시간대와 권한이 밖에서 바뀌었을 수 있다(시스템 설정, 비행기).
    final lifecycle = AppLifecycleListener(
      onResume: () => unawaited(_refreshPermissionAndSync()),
    );
    ref
      ..onDispose(lifecycle.dispose)
      ..listen(notificationSettingsProvider, (_, _) => unawaited(sync()))
      ..listen(completedPuzzleDatesProvider, (_, _) => unawaited(sync()))
      ..listen(notificationPermissionProvider, (_, _) => unawaited(sync()))
      // 티켓 29 의 산출물이 아니라 22 의 토큰 상태만 본다 — 계정·백업 코드
      // 전환으로 기록의 주인이 바뀌면 계획도 다시 세운다.
      ..listen(guestTokenProvider, (_, _) => unawaited(sync()))
      ..listen(
        todayPuzzleProvider,
        (_, next) => unawaited(_recordCompleted(next)),
      );

    final taps = bootstrap.taps;
    final subscription = taps.stream.listen((_) => unawaited(_openToday()));
    ref.onDispose(subscription.cancel);
    // 종료 상태에서 알림으로 켜진 실행. 스트림에는 안 들어오고 시작 정보로만 온다.
    if (taps.launchedByNotification) unawaited(_openToday());

    unawaited(_refreshPermissionAndSync());
    return const [];
  }

  /// 계획을 다시 세우고 OS 대기 목록을 그 모양으로 맞춘다.
  Future<void> sync() async {
    if (!_permissionKnown) return;
    if (_syncing) {
      _queued = true;
      return;
    }
    _syncing = true;
    try {
      // 설정·완료 날짜는 **지금 상태**를 읽는다. `.future` 는 첫 build 가
      // 돌려준 값에 머물러서, 설정을 바꾼 직후의 동기화가 옛 값으로 돈다.
      // 아직 읽는 중이면 그냥 돌아간다 — 올라오면 구독이 다시 부른다.
      final settings = ref.read(notificationSettingsProvider).value;
      final completed = ref.read(completedPuzzleDatesProvider).value;
      if (settings == null || completed == null) return;

      final permission = ref.read(notificationPermissionProvider);
      final location = await ref.read(deviceTimeZoneProvider).current();
      if (!ref.mounted) return;

      // 권한이 없으면 계획이 빈다 — diff 가 걸려 있던 우리 알림을 전부 취소한다.
      // 못 뜰 알림을 걸어두면 나중에 권한이 켜질 때 지난 알림이 쏟아진다.
      final desired = permission.isGranted
          ? planNotifications(
              now: tz.TZDateTime.now(location),
              settings: settings,
              completedKstDates: completed,
            )
          : const <ScheduledNotification>[];

      final scheduler = ref.read(notificationSchedulerProvider);
      final actions = diffPendingNotifications(
        desired: desired,
        pending: await scheduler.pendingNotifications(),
      );
      for (final id in actions.cancel) {
        await scheduler.cancel(id);
      }
      for (final notification in actions.schedule) {
        await scheduler.schedule(notification);
      }
      if (ref.mounted) state = desired;
    } finally {
      _syncing = false;
      if (_queued) {
        _queued = false;
        await sync();
      }
    }
  }

  /// 권한의 정본은 OS 다 — 앱을 다시 켜면 이번 실행의 상태를 모른다(티켓 28).
  Future<void> _refreshPermissionAndSync() async {
    await ref.read(notificationPermissionProvider.notifier).refresh();
    _permissionKnown = true;
    await sync();
  }

  /// 끝난 보드를 보면 그 퍼즐 날짜를 완료로 적는다.
  ///
  /// 제출로 끝난 경우뿐 아니라 **다른 기기에서 푼 날**(앱을 켜자마자 끝난
  /// 보드가 오는 경우)도 같은 길로 들어온다 — 둘을 따로 다룰 이유가 없다.
  Future<void> _recordCompleted(AsyncValue<TodayState?> puzzle) async {
    final today = puzzle.value;
    if (today is! TodayPuzzleReady || !today.puzzle.status.isFinished) return;

    await ref
        .read(completedPuzzleDatesProvider.notifier)
        .markCompleted(today.puzzle.date);
  }

  /// 알림을 탭했다 — 오늘 탭으로 보내고 최신 퍼즐을 다시 읽는다(US 40).
  Future<void> _openToday() async {
    ref.read(appRouterProvider).go(AppRoutes.today);
    await ref.read(todayPuzzleProvider.notifier).refresh();
    // 탭도 계획을 바꾸는 사건이다(그 사이 날짜가 넘어갔을 수 있다).
    await sync();
  }
}

/// 앱이 떠 있는 동안 살아 있어야 한다 — `ChosungApp` 이 구독한다(값은 안 쓰고
/// 수명만 잡아둔다).
final notificationSyncProvider =
    NotifierProvider<NotificationSyncController, List<ScheduledNotification>>(
      NotificationSyncController.new,
    );
