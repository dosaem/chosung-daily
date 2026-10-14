import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 알림 설정(S4). 서버에 두지 않는다 — 알림은 **이 기기가 거는 것**이고,
/// 기기마다 다른 생활 시간에 맞추는 값이다(스펙 §A.9 "서버 변경 없음").
@immutable
class NotificationSettings {
  const NotificationSettings({
    this.dailyTime = defaultDailyTime,
    this.reminderEnabled = true,
  });

  /// 기본 09:00(스펙 §A.9).
  static const defaultDailyTime = TimeOfDay(hour: 9, minute: 0);

  final TimeOfDay dailyTime;
  final bool reminderEnabled;

  NotificationSettings copyWith({
    TimeOfDay? dailyTime,
    bool? reminderEnabled,
  }) => NotificationSettings(
    dailyTime: dailyTime ?? this.dailyTime,
    reminderEnabled: reminderEnabled ?? this.reminderEnabled,
  );

  @override
  bool operator ==(Object other) =>
      other is NotificationSettings &&
      other.dailyTime == dailyTime &&
      other.reminderEnabled == reminderEnabled;

  @override
  int get hashCode => Object.hash(dailyTime, reminderEnabled);

  @override
  String toString() =>
      'NotificationSettings(${dailyTime.hour}:${dailyTime.minute}, '
      'reminder: $reminderEnabled)';
}

/// 설정이 놓이는 자리. 테스트는 이 경계를 메모리로 바꿔 낀다
/// (`OnboardingStore` 와 같은 방식).
abstract interface class NotificationSettingsStore {
  Future<NotificationSettings> read();
  Future<void> write(NotificationSettings settings);
}

/// 기기 로컬 설정(Android SharedPreferences / iOS NSUserDefaults).
///
/// 시각은 **자정으로부터의 분**으로 저장한다 — `"09:00"` 같은 문자열은 읽을 때
/// 파싱 실패를 처리해야 하고, 두 칸(시·분)으로 쪼개면 반만 써진 상태가 생긴다.
class PreferencesNotificationSettingsStore
    implements NotificationSettingsStore {
  const PreferencesNotificationSettingsStore();

  static const _dailyMinutesKey = 'notification_daily_minutes';
  static const _reminderKey = 'notification_reminder_enabled';

  /// 저장소 객체는 **쓸 때** 만든다 — 생성자에서 만들면 플러그인이 없는 환경
  /// (위젯 테스트)에서 provider 를 만드는 순간 터지고, 알림과 상관없는 화면
  /// 테스트가 같이 넘어진다.
  SharedPreferencesAsync get _preferences => SharedPreferencesAsync();

  @override
  Future<NotificationSettings> read() async {
    final minutes = await _preferences.getInt(_dailyMinutesKey);
    final reminder = await _preferences.getBool(_reminderKey);
    return NotificationSettings(
      dailyTime: minutes == null
          ? NotificationSettings.defaultDailyTime
          : TimeOfDay(hour: minutes ~/ 60, minute: minutes % 60),
      reminderEnabled: reminder ?? true,
    );
  }

  @override
  Future<void> write(NotificationSettings settings) async {
    await _preferences.setInt(
      _dailyMinutesKey,
      settings.dailyTime.hour * 60 + settings.dailyTime.minute,
    );
    await _preferences.setBool(_reminderKey, settings.reminderEnabled);
  }
}

final notificationSettingsStoreProvider = Provider<NotificationSettingsStore>(
  (ref) => const PreferencesNotificationSettingsStore(),
);
