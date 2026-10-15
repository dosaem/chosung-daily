import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

/// 카운트다운(US 6)이 읽는 시계는 [clockProvider] 다 — 티켓 40.
///
/// 왜 이 테스트가 있나: 두 카운트다운(결과 시트 S2, 퍼즐 없음 카드 S1)은
/// 원래 `DateTime.now` 를 직접 불렀다. 그러면 스토어 스크린샷이 **찍는 시각**
/// 마다 다른 숫자로 나와서 ko·en 세트가 어긋나고, 자정 직전에 돌리면
/// `00:00:03` 같은 그림이 남는다. 호출부가 provider 의 시계를 넘기도록 바꿨고
/// (기본값은 `DateTime.now` 라 앱 동작은 그대로다), 그게 되돌아가지 않게
/// 여기서 고정한다. 되돌리면 두 단언 모두 실제 시각을 보고 깨진다.
void main() {
  // KST 23:47:27 = UTC 14:47:27. 다음 KST 자정까지 12분 33초.
  DateTime fixedNow() => DateTime.utc(2026, 10, 13, 14, 47, 27);

  Widget app(FakeApiClient api) => ProviderScope(
    retry: noAutoRetry,
    overrides: [
      apiClientProvider.overrideWithValue(api),
      startupStatsProvider.overrideWithValue(fakeMyStats()),
      analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
      localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
      clockProvider.overrideWithValue(fixedNow),
    ],
    child: AppLocalizationScope(
      startLocale: const Locale('ko'),
      child: Builder(
        builder: (context) => MaterialApp(
          theme: appTheme(Brightness.light),
          locale: context.locale,
          supportedLocales: context.supportedLocales,
          localizationsDelegates: context.localizationDelegates,
          home: const Scaffold(body: TodayTab()),
        ),
      ),
    ),
  );

  Future<void> pump(WidgetTester tester, FakeApiClient api) async {
    setViewSize(tester, const Size(390, 844));
    await tester.runAsync(() async {
      await tester.pumpWidget(app(api));
      await tester.pump();
    });
    await tester.pumpAndSettle();
  }

  testWidgets('퍼즐 없음 카드(S1)의 카운트다운이 clockProvider 를 쓴다', (tester) async {
    final api = FakeApiClient()
      ..fetchTodayPuzzleError = const NoPuzzleTodayApiException(
        code: 'NO_PUZZLE_TODAY',
        message: '아직 준비되지 않았습니다.',
      );

    await pump(tester, api);

    expect(find.textContaining('다음 퍼즐까지 00:12:33'), findsOne);
  });

  testWidgets('결과 시트(S2)의 카운트다운이 clockProvider 를 쓴다', (tester) async {
    final api = FakeApiClient(
      puzzle: fakeTodayPuzzle(
        status: PuzzleStatus.success,
        attemptsLeft: 3,
        answer: '지하철역',
        attempts: const [
          PuzzleAttempt(guess: '지하철역', feedback: [true, true, true, true]),
        ],
      ),
    );

    await pump(tester, api);
    await tester.tap(find.text('결과 보기'));
    await tester.pumpAndSettle();

    expect(find.text('다음 퍼즐까지 00:12:33'), findsOne);
  });
}
