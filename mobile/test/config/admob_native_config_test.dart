import 'dart:io';

import 'package:chosung/ads/ad_unit_ids.dart';
import 'package:flutter_test/flutter_test.dart';

/// AdMob 앱 ID 는 유닛 ID 와 달리 `--dart-define` 으로 못 넘긴다 — SDK 가
/// 네이티브 매니페스트/plist 에서 읽고, **없으면 앱이 시작하자마자 죽는다**.
/// Dart 쪽 analyze·test 가 전혀 건드리지 않는 자리라 파일을 직접 읽어 지킨다
/// (`native_permissions_test.dart` 와 같은 방식).
void main() {
  test('Android 매니페스트가 AdMob 앱 ID 를 선언한다', () {
    final manifest = File(
      'android/app/src/main/AndroidManifest.xml',
    ).readAsStringSync();

    expect(manifest, contains('com.google.android.gms.ads.APPLICATION_ID'));
    expect(
      RegExp(r'android:value="(ca-app-pub-\d+~\d+)"').hasMatch(manifest),
      isTrue,
      reason: '앱 ID 는 `ca-app-pub-...~...` 꼴이다(유닛 ID 의 `/` 가 아니다)',
    );
  });

  test('iOS Info.plist 가 AdMob 앱 ID 를 선언한다', () {
    final plist = File('ios/Runner/Info.plist').readAsStringSync();

    final appId = RegExp(
      r'<key>GADApplicationIdentifier</key>\s*<string>([^<]*)</string>',
    ).firstMatch(plist)?.group(1);

    expect(appId, isNotNull);
    expect(RegExp(r'^ca-app-pub-\d+~\d+$').hasMatch(appId!), isTrue);
  });

  // 실제 앱 ID 는 AdMob 콘솔에서 사람이 만든다(`docs/RELEASE.md "### 31."`).
  // 그때까지는 Google 테스트 앱 ID 이고, 바꾸는 걸 잊으면 광고가 안 붙는다 —
  // 이 테스트가 "아직 테스트 ID" 라는 사실을 눈에 보이게 들고 있는다.
  test('지금 들어 있는 값은 Google 테스트 앱 ID 다', () {
    final publisher = testAdPublisherPrefix.replaceAll('/', '');

    expect(
      File('android/app/src/main/AndroidManifest.xml').readAsStringSync(),
      contains(publisher),
    );
    expect(
      File('ios/Runner/Info.plist').readAsStringSync(),
      contains(publisher),
    );
  });
}
