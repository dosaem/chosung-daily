import 'dart:convert';
import 'dart:io';

import 'package:chosung/notifications/notification_plan.dart';
import 'package:chosung/notifications/notification_scheduler.dart';
import 'package:flutter_test/flutter_test.dart';

/// 알림 문구는 `'notification.${kind.name}_title'` 처럼 **종류 이름으로 조립한**
/// 열쇠로 찾는다(`PluginNotificationScheduler`). 열쇠가 하나 비면 analyze 도
/// 위젯 테스트도 못 잡고, 기기에 `notification.daily_title` 이 그대로 뜬다.
void main() {
  Map<String, dynamic> dictionary(String language) =>
      jsonDecode(
            File('assets/translations/$language.json').readAsStringSync(),
          )
          as Map<String, dynamic>;

  for (final language in const ['ko', 'en']) {
    test('$language 사전에 알림 문구가 다 있다', () {
      final notification = dictionary(language)['notification'];
      expect(notification, isA<Map<String, dynamic>>());

      final keys = (notification as Map<String, dynamic>).keys.toSet();
      for (final kind in NotificationKind.values) {
        expect(keys, contains('${kind.name}_title'));
        expect(keys, contains('${kind.name}_body'));
      }
      // Android 알림 채널 이름·설명도 같은 사전에서 온다.
      expect(keys, containsAll(['channel_name', 'channel_description']));

      for (final value in notification.values) {
        expect(value, isA<String>());
        expect((value as String).trim(), isNotEmpty);
      }
    });
  }

  test('채널 ID 는 하나로 고정이다', () {
    // 채널 ID 가 바뀌면 사용자가 OS 설정에서 끈 채널이 되살아나고, 새 채널이
    // 기본값으로 다시 생긴다 — 끄기 설정이 조용히 풀린다.
    expect(PluginNotificationScheduler.channelId, 'daily_puzzle');
  });
}
