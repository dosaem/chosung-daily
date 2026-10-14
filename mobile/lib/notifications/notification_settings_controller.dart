import 'package:chosung/notifications/notification_settings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// S4 가 바꾸고 동기화가 읽는 알림 설정.
///
/// 값은 기기 로컬 저장소에 먼저 쓰고 상태를 바꾼다 — 쓰기가 실패했는데 화면이
/// 새 값을 보여주면 다음 실행에 조용히 되돌아간다.
class NotificationSettingsNotifier extends AsyncNotifier<NotificationSettings> {
  @override
  Future<NotificationSettings> build() async {
    try {
      return await ref.read(notificationSettingsStoreProvider).read();
      // 기기 저장소가 안 되는 상태. 여기서 멈추면 **알림이 통째로 조용히
      // 멈춘다** — 사용자는 왜 안 오는지 알 길이 없다. 기본값으로 간다.
      // `shared_preferences` 는 플러그인이 없으면 Exception 이 아니라
      // StateError 로 터져서 둘 다 받는다.
      // ignore: avoid_catching_errors
    } on Error catch (error) {
      debugPrint('알림 설정을 읽지 못해 기본값으로 갑니다: $error');
      return const NotificationSettings();
    } on Exception catch (error) {
      debugPrint('알림 설정을 읽지 못해 기본값으로 갑니다: $error');
      return const NotificationSettings();
    }
  }

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
