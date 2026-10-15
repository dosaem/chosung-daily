import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/google_ad_service.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:chosung/config/sentry_bootstrap.dart';
import 'package:chosung/main.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

  // `adServiceProvider` 기본값은 no-op 이다(위젯 테스트가 플랫폼 채널을 타지
  // 않게). 이 override 가 빠지면 **앱에서 광고가 통째로 사라진다** — 테스트는
  // 전부 통과한 채로.
  testWidgets('시작 트리가 실제 광고 SDK 를 끼운다', (tester) async {
    late final Widget started;

    await bootstrapChosungApp(
      initializeFirebaseFn: () async => FirebaseBootstrap.skipped,
      initializeLocalizationFn: () async {},
      // 알림 초기화는 플러그인(플랫폼 채널)을 탄다 — 여기서 보려는 건 광고
      // override 뿐이라 티켓 30 의 "알림 없음" 기본값으로 대신한다.
      initializeNotificationsFn: () async => NotificationBootstrap(
        available: false,
        taps: NotificationTaps(launchedByNotification: false),
      ),
      start: (app) => started = app,
    );

    // 띄우지 않고 override 만 본다 — 실제로 pump 하면 광고 SDK 가 플랫폼
    // 채널을 타려 든다.
    final container = ProviderContainer(
      overrides: (started as ProviderScope).overrides,
    );
    addTearDown(container.dispose);

    expect(container.read(adServiceProvider), isA<GoogleAdService>());
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
