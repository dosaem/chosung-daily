import 'package:chosung/analytics/analytics_event.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/analytics/firebase_analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/config/firebase_bootstrap.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('NoopAnalyticsService', () {
    test('보낸 이벤트를 순서대로 들고 있을 뿐 아무 데도 보내지 않는다', () async {
      final analytics = NoopAnalyticsService();

      await analytics.log(
        puzzleCompleteEvent(
          language: PuzzleLanguage.ko,
          success: true,
          attempts: 2,
        ),
      );
      await analytics.log(shareEvent);

      expect(analytics.logged.map((event) => event.name), [
        'puzzle_complete',
        'share',
      ]);
      expect(analytics.logged.first.parameters['attempts'], 2);
    });
  });

  group('FirebaseAnalyticsService', () {
    test('이벤트 이름과 파라미터를 그대로 넘긴다', () async {
      String? sentName;
      Map<String, Object>? sentParameters;
      final analytics = FirebaseAnalyticsService(
        logEvent: ({required name, parameters}) async {
          sentName = name;
          sentParameters = parameters;
        },
      );

      await analytics.log(
        puzzleCompleteEvent(
          language: PuzzleLanguage.en,
          success: false,
          attempts: 5,
        ),
      );

      expect(sentName, 'puzzle_complete');
      expect(sentParameters, {'language': 'en', 'success': 0, 'attempts': 5});
    });
  });

  group('analyticsServiceProvider', () {
    test('Firebase 를 건너뛴 빌드는 no-op 구현을 쓴다', () {
      final container = ProviderContainer(
        overrides: [
          firebaseBootstrapProvider.overrideWithValue(
            FirebaseBootstrap.skipped,
          ),
        ],
      );
      addTearDown(container.dispose);

      expect(
        container.read(analyticsServiceProvider),
        isA<NoopAnalyticsService>(),
      );
    });

    test('Firebase 가 떴으면 Firebase 구현을 쓴다', () {
      final container = ProviderContainer(
        overrides: [
          firebaseBootstrapProvider.overrideWithValue(
            FirebaseBootstrap.initialized,
          ),
        ],
      );
      addTearDown(container.dispose);

      expect(
        container.read(analyticsServiceProvider),
        isA<FirebaseAnalyticsService>(),
      );
    });

    // main 이 덮는 걸 잊어도 Firebase 를 부르다 죽지 않는다.
    test('아무것도 덮지 않으면 no-op 이다', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      expect(
        container.read(analyticsServiceProvider),
        isA<NoopAnalyticsService>(),
      );
    });
  });
}
