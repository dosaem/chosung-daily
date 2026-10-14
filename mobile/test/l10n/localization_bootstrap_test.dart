import 'package:chosung/app.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:chosung/l10n/app_localization.dart';
import 'package:chosung/l10n/localization_bootstrap.dart';
import 'package:chosung/main.dart';
import 'package:chosung/notifications/notification_bootstrap.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  // easy_localization 의 초기화는 기기 언어를 읽기 전에 저장된 언어를
  // shared_preferences 에서 확인한다. 앱은 `saveLocale: false` 라 저장하지
  // 않지만 초기화 자체는 그 저장소를 거치므로 테스트에서 빈 값을 넣어준다.
  setUp(() => SharedPreferences.setMockInitialValues({}));

  testWidgets('기기 언어를 강제하지 않는 실제 시작 경로가 예외 없이 뜬다', (tester) async {
    await initializeLocalization();
    Locale? seen;

    // 번역 JSON 을 rootBundle 에서 실제로 읽으므로 runAsync 안에서 첫 프레임을
    // 돌려야 자식까지 그려진다.
    await tester.runAsync(() async {
      await tester.pumpWidget(
        AppLocalizationScope(
          child: Builder(
            builder: (context) {
              seen = context.locale;
              return const SizedBox();
            },
          ),
        ),
      );
      await tester.pump();
    });
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(AppLocalization.supportedLocales, contains(seen));
  });

  test('시작 순서: Firebase → 국제화 초기화 → 알림 초기화 → runApp', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final calls = <String>[];

    await bootstrapChosungApp(
      initializeFirebaseFn: () async {
        calls.add('firebase');
        return FirebaseBootstrap.skipped;
      },
      initializeLocalizationFn: () async => calls.add('localization'),
      // 알림 예약은 문구를 번역해서 넣으므로 국제화 **뒤**여야 한다(티켓 30).
      initializeNotificationsFn: () async {
        calls.add('notifications');
        return NotificationBootstrap(
          available: false,
          taps: NotificationTaps(launchedByNotification: false),
        );
      },
      start: (_) => calls.add('runApp'),
    );

    expect(calls, ['firebase', 'localization', 'notifications', 'runApp']);
  });
}
