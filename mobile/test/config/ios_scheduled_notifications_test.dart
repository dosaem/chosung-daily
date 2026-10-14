import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 예약 알림의 iOS 쪽 배선은 `AppDelegate.swift` 에 있다. 빠져 있으면
/// **Dart 테스트는 전부 통과한 채 실제 기기에서 알림 탭만 안 먹는다** —
/// OS 의 `didReceiveNotificationResponse` 가 플러그인까지 오지 않아서
/// `onDidReceiveNotificationResponse` 콜백도, 종료 상태 launch 판별도
/// 비어 있는 채로 돈다(`android_scheduled_notifications_test.dart` 와 같은 부류).
void main() {
  /// 주석에 적힌 건 선언이 아니다 — 실제 코드 줄만 본다
  /// (`android_scheduled_notifications_test.dart` 와 같은 이유).
  final appDelegate = File('ios/Runner/AppDelegate.swift')
      .readAsLinesSync()
      .where((line) => !line.trimLeft().startsWith('//'))
      .join('\n');

  test('알림 센터 delegate 를 앱에 연결한다', () {
    expect(
      appDelegate,
      contains('import UserNotifications'),
      reason: 'UNUserNotificationCenter 를 쓰려면 이 모듈이 필요하다',
    );
    // `self` 를 그대로 건다 — `FlutterAppDelegate` 는
    // `FlutterAppLifeCycleProvider` 를 통해 `UNUserNotificationCenterDelegate`
    // 를 상속 채택하고(엔진 헤더 `FlutterPlugin.h`), 엔진이 그 전달 메서드를
    // 구현해 등록된 플러그인에게 넘긴다.
    expect(
      appDelegate,
      contains('UNUserNotificationCenter.current().delegate = self'),
      reason:
          'flutter_local_notifications 는 이 연결을 앱에 맡긴다 — 없으면 '
          'OS 알림 응답이 플러그인에 전달되지 않는다',
    );
  });

  test('delegate 연결은 앱이 뜨는 시점에 한다', () {
    final launch = appDelegate.indexOf('didFinishLaunchingWithOptions');
    final delegate = appDelegate.indexOf(
      'UNUserNotificationCenter.current().delegate',
    );
    final returnSuper = appDelegate.indexOf('return super.application');

    expect(launch, greaterThanOrEqualTo(0));
    expect(delegate, greaterThan(launch));
    expect(
      delegate,
      lessThan(returnSuper),
      reason: '응답이 먼저 와도 받을 수 있게 launch 가 끝나기 전에 연결한다',
    );
  });
}
