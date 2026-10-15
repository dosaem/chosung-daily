import 'dart:async';

import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/ads/ad_service.dart';
import 'package:chosung/ads/interstitial_store.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/subscription/entitlement_provider.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:chosung/widgets/hint_card.dart';
import 'package:chosung/widgets/result_sheet.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import '../fakes/fake_ad_service.dart';
import '../fakes/fake_api_client.dart';
import '../fakes/fake_entitlement.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_interstitial_store.dart';
import '../fakes/in_memory_local_flag_store.dart';
import '../layout/adaptive_scaffold_test.dart' show setViewSize;

const _consented = UmpStatus(
  consent: ConsentStatus.obtained,
  privacyOptionsRequired: false,
);

/// 오늘 탭 + 광고 경계. 서버(`ApiClient`)·광고(`AdService`)·전면 플래그
/// 저장소·구독 권한만 가짜고 나머지는 실제 코드다.
Future<void> pumpToday(
  WidgetTester tester, {
  required FakeApiClient api,
  required FakeAdService ads,
  InMemoryInterstitialStore? store,
  bool? entitled = false,
  UmpStatus consent = _consented,
}) async {
  setViewSize(tester, const Size(390, 844));
  ads.consent = consent;

  await tester.runAsync(() async {
    await tester.pumpWidget(
      ProviderScope(
        retry: noAutoRetry,
        overrides: [
          apiClientProvider.overrideWithValue(api),
          startupStatsProvider.overrideWithValue(fakeMyStats(currentStreak: 7)),
          analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
          isIosProvider.overrideWithValue(false),
          trackingAuthorizationProvider.overrideWithValue(
            FakeTrackingAuthorization(saved: TrackingStatus.notSupported),
          ),
          adServiceProvider.overrideWithValue(ads),
          interstitialStoreProvider.overrideWithValue(
            store ?? InMemoryInterstitialStore(),
          ),
          entitlementProvider.overrideWith(
            () => FakeEntitlement(initial: entitled),
          ),
          // 결과 시트의 "계정 연결" 안내가 읽는 기기 로컬 플래그(티켓 29).
          // flutter_secure_storage 는 플랫폼 채널을 탄다.
          localFlagStoreProvider.overrideWithValue(InMemoryLocalFlagStore()),
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
      ),
    );
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

/// 바텀시트 밖(배리어)을 눌러 닫는다 — 실제 사용자가 결과를 확인하고 내리는
/// 경로다. 전면 광고는 그 뒤에 뜬다.
Future<void> dismissSheet(WidgetTester tester) async {
  await tester.runAsync(() async {
    await tester.tapAt(const Offset(10, 10));
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

Finder previewButton() => find.descendant(
  of: find.byType(HintCard),
  matching: find.byType(OutlinedButton),
);

bool previewEnabled(WidgetTester tester) =>
    tester.widget<OutlinedButton>(previewButton()).onPressed != null;

void main() {
  group('보상형 힌트 미리 보기', () {
    testWidgets('비구독자는 광고를 보고 힌트를 연다 (US 4)', (tester) async {
      final api = FakeApiClient()..hintUnlockResponse = '서울에 가장 많다';
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads);

      expect(find.text('광고 보고 힌트 미리 보기'), findsOne);
      await tapAndSettle(tester, previewButton());

      expect(ads.rewardedShowCalls, 1);
      expect(api.unlockedHintPuzzleIds, [1]);
      expect(find.text('서울에 가장 많다'), findsOne);
      // 열리면 버튼 자체가 사라진다(잠김 상태의 UI 다).
      expect(previewButton(), findsNothing);
    });

    testWidgets('구독자는 광고 없이 바로 연다 (US 32)', (tester) async {
      final api = FakeApiClient()..hintUnlockResponse = '서울에 가장 많다';
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads, entitled: true);

      expect(find.text('힌트 미리 보기'), findsOne);
      expect(find.text('광고 보고 힌트 미리 보기'), findsNothing);

      await tapAndSettle(tester, previewButton());

      expect(ads.rewardedShowCalls, 0);
      expect(api.unlockedHintPuzzleIds, [1]);
      expect(find.text('서울에 가장 많다'), findsOne);
    });

    testWidgets('광고를 못 띄우면 버튼이 잠기고 안내가 뜬다', (tester) async {
      final api = FakeApiClient();
      final ads = FakeAdService(rewarded: RewardedOutcome.unavailable);

      await pumpToday(tester, api: api, ads: ads);
      await tapAndSettle(tester, previewButton());

      expect(ads.rewardedShowCalls, 1);
      expect(api.unlockedHintPuzzleIds, isEmpty);
      expect(find.text('지금은 광고를 불러올 수 없어요'), findsOne);
      expect(previewEnabled(tester), isFalse);
    });

    // 떴는데 중간에 닫은 건 다시 누르면 되는 일이다 — 버튼을 끄면 그 퍼즐에서
    // 힌트를 영영 못 연다.
    testWidgets('광고를 중간에 닫으면 안내만 뜨고 다시 누를 수 있다', (tester) async {
      final api = FakeApiClient();
      final ads = FakeAdService(rewarded: RewardedOutcome.dismissed);

      await pumpToday(tester, api: api, ads: ads);
      await tapAndSettle(tester, previewButton());

      expect(find.text('광고를 끝까지 봐야 힌트가 열려요'), findsOne);
      expect(api.unlockedHintPuzzleIds, isEmpty);
      expect(previewEnabled(tester), isTrue);

      ads.rewarded = RewardedOutcome.earned;
      await tapAndSettle(tester, previewButton());

      expect(ads.rewardedShowCalls, 2);
      expect(api.unlockedHintPuzzleIds, [1]);
      expect(find.text('서울에 가장 많다'), findsOne);
    });

    // 리뷰 r1 D-31-3: 광고를 못 띄워 버튼을 끈 뒤 구독 권한이 생길 수 있다
    // (티켓 32 구매·33 갱신이 같은 provider 를 쓴다). 그때는 광고가 필요하지
    // 않으니 "광고를 못 불러왔다" 기록도 더는 적용되지 않아야 한다(US 32).
    testWidgets('광고 실패 뒤 구독 권한이 생기면 바로 열 수 있다', (tester) async {
      final api = FakeApiClient()..hintUnlockResponse = '서울에 가장 많다';
      final ads = FakeAdService(rewarded: RewardedOutcome.unavailable);

      await pumpToday(tester, api: api, ads: ads);
      await tapAndSettle(tester, previewButton());
      expect(previewEnabled(tester), isFalse);

      ProviderScope.containerOf(
            tester.element(find.byType(HintCard)),
          )
          .read(entitlementProvider.notifier)
          .update(
            fakeEntitlement(active: true, until: DateTime.utc(2026, 11)),
          );
      await tester.pumpAndSettle();

      expect(find.text('힌트 미리 보기'), findsOne);
      expect(find.text('지금은 광고를 불러올 수 없어요'), findsNothing);
      expect(previewEnabled(tester), isTrue);

      await tapAndSettle(tester, previewButton());

      expect(ads.rewardedShowCalls, 1, reason: '구독자는 광고를 다시 요청하지 않는다');
      expect(api.unlockedHintPuzzleIds, [1]);
      expect(find.text('서울에 가장 많다'), findsOne);
    });

    testWidgets('광고를 띄울 수 없는 세션이면 처음부터 비활성이다', (tester) async {
      final api = FakeApiClient();
      final ads = FakeAdService();

      await pumpToday(
        tester,
        api: api,
        ads: ads,
        consent: const UmpStatus.failed(),
      );

      expect(previewEnabled(tester), isFalse);
      expect(find.text('지금은 광고를 불러올 수 없어요'), findsOne);
      expect(ads.rewardedShowCalls, 0);
    });

    // US 5a: 한 번 열었으면 다시 광고를 볼 필요가 없다 — 서버가 이미 열어둔
    // 상태라 재조회로 힌트가 채워져 온다.
    testWidgets('409 이미 열림이면 재조회로 힌트를 보여준다', (tester) async {
      final api = FakeApiClient()
        ..unlockHintError = const HintAlreadyUnlockedApiException(
          code: 'HINT_ALREADY_UNLOCKED',
          message: '이미 열었어요',
        );
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads);
      api.puzzle = fakeTodayPuzzle(hintUnlocked: true, hint: '서울에 가장 많다');

      await tapAndSettle(tester, previewButton());

      expect(find.text('서울에 가장 많다'), findsOne);
      expect(api.fetchTodayPuzzleCalls, 2);
    });

    testWidgets('열지 못하면 보드는 그대로 두고 안내만 띄운다', (tester) async {
      final api = FakeApiClient()
        ..unlockHintError = const NetworkApiException(
          code: 'NETWORK_ERROR',
          message: '연결 실패',
        );
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads);
      await tapAndSettle(tester, previewButton());

      expect(find.text('힌트를 열지 못했어요'), findsOne);
      expect(find.byType(HintCard), findsOne);
    });

    // 리뷰 r2 D-31-4: 광고까지 다 본 뒤 힌트 응답을 기다리는 사이에도 답 입력은
    // 살아 있다. 그 제출이 실패해도 서버가 이미 열어 준 힌트는 화면에 남아야
    // 한다 — 버리면 비구독자는 같은 힌트에 광고를 다시 봐야 한다(US 5a).
    // 리뷰 r3, 코디네이터 지시 3 — 경로 쌍 "힌트 × 힌트". 컨트롤러는 같은 퍼즐의
    // 두 번째 요청을 막지 않으므로(보드의 `hint` 는 응답 전까지 null 이다) 여기서
    // 막는다: 요청이 떠 있는 동안 버튼이 꺼져 있어야 보상형을 두 번 보지도,
    // hint-unlock 을 두 번 보내지도 않는다.
    testWidgets('힌트를 여는 동안에는 버튼이 꺼져 있다', (tester) async {
      final api = FakeApiClient()..hintUnlockResponse = '서울에 가장 많다';
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads);

      final gate = Completer<void>();
      api.unlockHintGate = gate;
      await tapAndSettle(tester, previewButton());

      expect(api.unlockedHintPuzzleIds, [1], reason: '첫 요청은 떠났다');
      expect(previewEnabled(tester), isFalse, reason: '응답을 기다리는 동안은 못 누른다');

      await tester.runAsync(() async {
        gate.complete();
        await Future<void>.delayed(Duration.zero);
      });
      await tester.pumpAndSettle();

      expect(find.text('서울에 가장 많다'), findsOne);
      expect(ads.rewardedShowCalls, 1, reason: '보상형을 두 번 보지 않는다');
      expect(api.unlockedHintPuzzleIds, [1], reason: 'hint-unlock 은 한 번뿐이다');
    });

    testWidgets('힌트를 기다리는 동안 제출이 실패해도 힌트가 열린다', (tester) async {
      final api = FakeApiClient()..hintUnlockResponse = '서울에 가장 많다';
      final ads = FakeAdService();

      await pumpToday(tester, api: api, ads: ads);

      final gate = Completer<void>();
      api.unlockHintGate = gate;
      await tapAndSettle(tester, previewButton());
      expect(ads.rewardedShowCalls, 1);
      expect(api.unlockedHintPuzzleIds, [1]);

      // 힌트 응답을 기다리는 사이의 제출. 이 요청만 끊긴다.
      api.submitGuessError = const NetworkApiException(
        code: 'NETWORK_ERROR',
        message: '연결 실패',
      );
      await tester.enterText(find.byType(TextField), '지하촌역');
      await tester.pump();
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      await tester.runAsync(() async {
        gate.complete();
        await Future<void>.delayed(Duration.zero);
      });
      await tester.pumpAndSettle();

      expect(find.text('서울에 가장 많다'), findsOne);
      expect(find.text('힌트를 열지 못했어요'), findsNothing);
      expect(previewButton(), findsNothing, reason: '열린 힌트에 광고를 다시 요구하지 않는다');
      expect(ads.rewardedShowCalls, 1);
      expect(api.unlockedHintPuzzleIds, [1]);
    });
  });

  group('전면 광고 타이밍', () {
    FakeApiClient finishing() => FakeApiClient(
      puzzle: fakeTodayPuzzle(
        attemptsLeft: 4,
        attempts: const [
          PuzzleAttempt(guess: '지하촌역', feedback: [true, false, false, true]),
        ],
      ),
      guessResult: fakeGuessResult(
        isCorrect: true,
        attemptsLeft: 3,
        answer: '지하철역',
      ),
    );

    testWidgets('결과 시트를 닫은 뒤 1회 뜬다 (US 24)', (tester) async {
      final ads = FakeAdService();
      final store = InMemoryInterstitialStore();

      await pumpToday(tester, api: finishing(), ads: ads, store: store);
      await tester.enterText(find.byType(TextField), '지하철역');
      await tester.pump();
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));

      expect(find.byType(ResultSheet), findsOne);
      // 시트가 떠 있는 동안에는 뜨지 않는다.
      expect(ads.interstitialShowCalls, 0);

      await dismissSheet(tester);

      expect(ads.interstitialShowCalls, 1);
      expect(store.reserved, {1});
    });

    testWidgets('구독자는 뜨지 않는다', (tester) async {
      final ads = FakeAdService();

      await pumpToday(
        tester,
        api: finishing(),
        ads: ads,
        entitled: true,
      );
      await tester.enterText(find.byType(TextField), '지하철역');
      await tester.pump();
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));
      await dismissSheet(tester);

      expect(ads.interstitialShowCalls, 0);
    });

    // US 25: 첫 제출 전에는 절대 안 뜬다 — 다른 기기에서 끝낸 퍼즐을 열어
    // "결과 보기" 를 눌러도 같다.
    testWidgets('제출 없이 결과만 다시 열면 뜨지 않는다', (tester) async {
      final ads = FakeAdService();
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

      await pumpToday(tester, api: api, ads: ads);
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '결과 보기'));
      expect(find.byType(ResultSheet), findsOne);
      await dismissSheet(tester);

      expect(ads.interstitialShowCalls, 0);
    });

    testWidgets('같은 퍼즐에서 시트를 다시 열어도 두 번은 없다', (tester) async {
      final ads = FakeAdService();

      await pumpToday(tester, api: finishing(), ads: ads);
      await tester.enterText(find.byType(TextField), '지하철역');
      await tester.pump();
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '제출'));
      await dismissSheet(tester);
      await tapAndSettle(tester, find.widgetWithText(FilledButton, '결과 보기'));
      await dismissSheet(tester);

      expect(ads.interstitialShowCalls, 1);
    });
  });
}
