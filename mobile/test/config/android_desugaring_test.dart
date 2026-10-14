import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// `flutter_local_notifications` 10+ 는 **알림 예약을 안 쓰더라도** 소비하는 앱이
/// core library desugaring 을 켜두기를 요구한다. 안 켜면 Dart 테스트·analyze 는
/// 전부 통과한 채 Android 빌드만 깨진다 —
/// `Dependency ':flutter_local_notifications' requires core library desugaring
/// to be enabled for :app.` (AGP `checkDebugAarMetadata`). 위젯 테스트는 권한
/// requester 를 fake 로 치환하므로 이 통합 결함을 잡지 못한다(D-28-1).
///
/// 요구 버전은 하드코딩하지 않고 **설치된 플러그인의 `android/build.gradle`**
/// 에서 읽는다. 플러그인이 desugar 버전을 올리면 이 테스트가 먼저 깨진다.
void main() {
  /// pub cache 경로는 기기마다 다르므로 `flutter pub get` 이 쓴 매핑에서 찾는다.
  Directory pluginRoot(String package) {
    final config =
        jsonDecode(File('.dart_tool/package_config.json').readAsStringSync())
            as Map<String, dynamic>;
    final packages = (config['packages'] as List).cast<Map<String, dynamic>>();
    final entry = packages.firstWhere((p) => p['name'] == package);
    return Directory.fromUri(Uri.parse(entry['rootUri'] as String));
  }

  /// `com.android.tools:desugar_jdk_libs:2.1.4` → `[2, 1, 4]`.
  List<int> parseVersion(String coordinate) =>
      coordinate.split(':').last.split('.').map(int.parse).toList();

  int compareVersions(List<int> a, List<int> b) {
    for (var i = 0; i < a.length && i < b.length; i++) {
      if (a[i] != b[i]) return a[i].compareTo(b[i]);
    }
    return a.length.compareTo(b.length);
  }

  test('앱 Gradle 설정이 알림 플러그인의 desugaring 요구를 만족한다', () {
    final pluginGradle = File(
      '${pluginRoot('flutter_local_notifications').path}/android/build.gradle',
    ).readAsStringSync();
    final required = RegExp(
      '''coreLibraryDesugaring ['"]([^'"]+)['"]''',
    ).firstMatch(pluginGradle)?.group(1);
    expect(
      required,
      isNotNull,
      reason: '플러그인이 desugaring 을 요구하지 않게 됐다면 이 테스트를 지워도 된다',
    );

    final appGradle = File('android/app/build.gradle.kts').readAsStringSync();

    // Java 언어 수준 17 지정은 라이브러리 desugaring 활성화가 아니다 —
    // 플래그가 따로 켜져 있어야 한다.
    expect(
      appGradle,
      contains('isCoreLibraryDesugaringEnabled = true'),
      reason: 'compileOptions 에서 라이브러리 desugaring 을 켜야 한다',
    );

    final declared = RegExp(
      r'coreLibraryDesugaring\("([^"]+)"\)',
    ).firstMatch(appGradle)?.group(1);
    expect(
      declared,
      isNotNull,
      reason: '플래그만 켜고 desugar_jdk_libs 의존성이 없으면 빌드가 깨진다',
    );
    expect(
      declared!.split(':').take(2).join(':'),
      required!.split(':').take(2).join(':'),
      reason: '플러그인이 요구하는 것과 같은 artifact 여야 한다',
    );
    expect(
      compareVersions(parseVersion(declared), parseVersion(required)),
      greaterThanOrEqualTo(0),
      reason: 'desugar_jdk_libs 가 플러그인 요구 버전($required)보다 낮으면 AGP 가 빌드를 막는다',
    );
  });
}
