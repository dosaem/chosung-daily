import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:chosung/config/sentry_bootstrap.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('initializeFirebase', () {
    test('초기화가 되면 initialized', () async {
      var called = 0;

      final outcome = await initializeFirebase(
        initialize: () async => called++,
      );

      expect(outcome, FirebaseBootstrap.initialized);
      expect(called, 1);
    });

    // google-services.json / GoogleService-Info.plist 가 없으면 여기서 던진다.
    // CI·디버그 빌드는 그 파일 없이도 떠야 한다.
    test('설정 파일이 없어 초기화가 실패하면 건너뛰고 던지지 않는다', () async {
      final outcome = await initializeFirebase(
        initialize: () async => throw PlatformException(
          code: 'channel-error',
          message: 'FirebaseOptions cannot be null',
        ),
      );

      expect(outcome, FirebaseBootstrap.skipped);
    });

    test('플러그인 자체가 없어도 건너뛴다', () async {
      final outcome = await initializeFirebase(
        initialize: () async => throw MissingPluginException('no impl'),
      );

      expect(outcome, FirebaseBootstrap.skipped);
    });
  });

  group('runWithSentry', () {
    test('DSN 이 비어 있으면 Sentry 를 초기화하지 않고 앱만 띄운다', () async {
      var initialized = 0;
      var appRuns = 0;

      await runWithSentry(
        dsn: '',
        initialize: (_, _) async => initialized++,
        runApp: () => appRuns++,
      );

      expect(initialized, 0);
      expect(appRuns, 1);
    });

    test('DSN 이 있으면 Sentry 가 앱을 띄운다', () async {
      String? seenDsn;
      var appRuns = 0;

      await runWithSentry(
        dsn: 'https://key@example.test/1',
        initialize: (dsn, run) async {
          seenDsn = dsn;
          run();
        },
        runApp: () => appRuns++,
      );

      expect(seenDsn, 'https://key@example.test/1');
      expect(appRuns, 1);
    });
  });
}
