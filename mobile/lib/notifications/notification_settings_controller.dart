import 'package:chosung/notifications/notification_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 가 바꾸고 동기화가 읽는 알림 설정.
///
/// 값은 기기 로컬 저장소에 먼저 쓰고 상태를 바꾼다 — 쓰기가 실패했는데 화면이
/// 새 값을 보여주면 다음 실행에 조용히 되돌아간다.
class NotificationSettingsNotifier extends AsyncNotifier<NotificationSettings> {
  @override
  Future<NotificationSettings> build() =>
      ref.read(notificationSettingsStoreProvider).read();

  Future<void> setDailyTime(TimeOfDay time) =>
      _update((current) => current.copyWith(dailyTime: time));

  Future<void> setReminderEnabled({required bool enabled}) =>
      _update((current) => current.copyWith(reminderEnabled: enabled));

  Future<void> _update(
    NotificationSettings Function(NotificationSettings current) change,
  ) async {
    final current = state.value;
    if (current == null) return;

    final next = change(current);
    if (next == current) return;

    await ref.read(notificationSettingsStoreProvider).write(next);
    if (ref.mounted) state = AsyncData(next);
  }
}

final notificationSettingsProvider =
    AsyncNotifierProvider<NotificationSettingsNotifier, NotificationSettings>(
      NotificationSettingsNotifier.new,
    );
