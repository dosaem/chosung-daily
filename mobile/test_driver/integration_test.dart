import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

/// `flutter drive` 드라이버 — integration test 의 `takeScreenshot` 바이트를
/// 파일로 떨어뜨린다. 저장 위치는 `STORE_SHOT_DIR`(기본 `screenshots`).
///
/// BASELINE(`~/Code/BuildUrPalace/test_driver/integration_test.dart`)과 같은
/// 구조다 — 드라이버는 스크린샷을 받는 통로일 뿐이라 바꿀 게 없다.
Future<void> main() async {
  await integrationDriver(
    onScreenshot: (name, bytes, [args]) async {
      final directory = Platform.environment['STORE_SHOT_DIR'] ?? 'screenshots';
      File('$directory/$name.png')
        ..createSync(recursive: true)
        ..writeAsBytesSync(bytes);
      stdout.writeln('saved $directory/$name.png (${bytes.length} bytes)');
      return true;
    },
  );
}
