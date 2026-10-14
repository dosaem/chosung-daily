import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 권한 선언은 Dart 쪽 analyze/test 가 전혀 건드리지 않는 네이티브 설정이다.
/// 빠져 있으면 **빌드는 되고 실행 중에 조용히 실패한다** — Android 13+ 는
/// 권한 요청 다이얼로그가 아예 안 뜨고, iOS 는 ATT 프롬프트를 띄우는 순간
/// 앱이 죽는다(`NSUserTrackingUsageDescription` 없으면 크래시). 그래서
/// `ios_project_test.dart` 와 같은 방식으로 파일을 직접 읽어 지킨다.
void main() {
  test('Android 매니페스트가 POST_NOTIFICATIONS 를 선언한다', () {
    final manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();

    expect(
      manifest,
      contains('android.permission.POST_NOTIFICATIONS'),
      reason: 'Android 13+ 의 알림 런타임 권한',
    );
  });

  test('iOS Info.plist 에 ATT 설명 문구가 있다', () {
    final plist = File('ios/Runner/Info.plist').readAsStringSync();

    expect(plist, contains('<key>NSUserTrackingUsageDescription</key>'));
    // 빈 문자열이면 심사에서 반려된다 — 실제 문장이 들어 있어야 한다.
    final description = RegExp(
      r'<key>NSUserTrackingUsageDescription</key>\s*<string>([^<]*)</string>',
    ).firstMatch(plist)?.group(1);
    expect(description, isNotNull);
    expect(description!.trim().length, greaterThan(10));
  });

  test('한국어 기기에서는 ATT 설명도 한국어로 나온다', () {
    final strings = File(
      'ios/Runner/ko.lproj/InfoPlist.strings',
    ).readAsStringSync();

    expect(strings, contains('"NSUserTrackingUsageDescription"'));
  });
}
