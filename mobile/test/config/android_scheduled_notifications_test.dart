import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 예약 알림의 Android 쪽 배선은 매니페스트에 있다. 빠져 있으면 **Dart 테스트는
/// 전부 통과한 채 실제 기기에서 알림만 안 뜬다** — 플러그인은 16 버전부터
/// 리시버를 자기 매니페스트에 넣지 않고 앱에 맡긴다(D-28-1 과 같은 부류의 구멍).
void main() {
  final manifest = File(
    'android/app/src/main/AndroidManifest.xml',
  ).readAsStringSync();

  /// 실제로 선언된 권한 이름만 모은다 — 주석에 적힌 이름은 선언이 아니다.
  final declaredPermissions = RegExp(
    r'<uses-permission\s+android:name="android\.permission\.([\w.]+)"',
  ).allMatches(manifest).map((match) => match.group(1)).toSet();

  test('재부팅 뒤에도 예약이 살아남도록 BOOT_COMPLETED 를 받는다', () {
    expect(
      declaredPermissions,
      contains('RECEIVE_BOOT_COMPLETED'),
      reason: '없으면 재부팅 한 번에 대기 알림이 전부 사라진다',
    );
    expect(
      manifest,
      contains(
        'com.dexterous.flutterlocalnotifications'
        '.ScheduledNotificationBootReceiver',
      ),
    );
    expect(manifest, contains('android.intent.action.BOOT_COMPLETED'));
  });

  test('예약 알림을 띄우는 리시버가 선언돼 있다', () {
    expect(
      manifest,
      contains(
        'com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver',
      ),
      reason: '이게 없으면 예약 시각이 와도 알림이 안 뜬다',
    );
  });

  test('정확한 알람 권한은 선언하지 않는다', () {
    // Play 정책은 `SCHEDULE_EXACT_ALARM`·`USE_EXACT_ALARM` 을 알람·캘린더 같은
    // 앱에만 허용한다. 하루 한 번 알림은 몇 분 늦어도 되므로
    // `inexactAllowWhileIdle` 로 간다(스펙 §A.9).
    expect(declaredPermissions, isNot(contains('SCHEDULE_EXACT_ALARM')));
    expect(declaredPermissions, isNot(contains('USE_EXACT_ALARM')));
    expect(declaredPermissions, contains('POST_NOTIFICATIONS'));
  });
}
