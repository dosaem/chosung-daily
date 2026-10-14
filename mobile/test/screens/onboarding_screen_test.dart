import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:chosung/api/api_exception.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/guest/guest_token_store.dart';
import 'package:chosung/onboarding/onboarding_store.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/permissions/tracking_permission.dart';
import 'package:chosung/routing/app_routes.dart';
import 'package:chosung/screens/home_shell.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/theme/app_colors.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../fakes/fake_api_client.dart';
import '../fakes/fake_permissions.dart';
import '../fakes/in_memory_guest_token_store.dart';
import '../fakes/in_memory_onboarding_store.dart';

/// 온보딩은 **시작 흐름이 끝난 뒤 어디로 가느냐**가 전부라서, 화면만 떼어
/// 띄우지 않고 실제 앱 트리를 그대로 돌린다(앱 시작 분기 테스트와 같은 방식).
/// 가짜로 바꾸는 건 서버·저장소·OS 권한 세 경계뿐이다.
class OnboardingHarness {
  OnboardingHarness({
    FakeApiClient? api,
    InMemoryOnboardingStore? onboardingStore,
    FakeNotificationPermissionRequester? notifications,
    FakeTrackingAuthorization? tracking,
    this.isIos = true,
  }) : api = api ?? FakeApiClient(),
       onboardingStore = onboardingStore ?? InMemoryOnboardingStore(),
       notifications = notifications ?? FakeNotificationPermissionRequester(),
       tracking = tracking ?? FakeTrackingAuthorization();

  final FakeApiClient api;
  final InMemoryOnboardingStore onboardingStore;
  final FakeNotificationPermissionRequester notifications;
  final FakeTrackingAuthorization tracking;
  final bool isIos;

  late ProviderContainer _container;

  /// 권한 결과가 "상태로 남았는지" 는 티켓 30·31 이 읽을 provider 로 확인한다.
  NotificationPermission get notificationPermission =>
      _container.read(notificationPermissionProvider);

  TrackingStatus get trackingStatus => _container.read(trackingStatusProvider);

  Future<void> pump(
    WidgetTester tester, {
    Size size = const Size(390, 844),
    Locale locale = const Locale('ko'),
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    final scope = ProviderScope(
      retry: noAutoRetry,
      overrides: [
        apiClientProvider.overrideWithValue(api),
        guestTokenStoreProvider.overrideWithValue(
          InMemoryGuestTokenStore('guest-token'),
        ),
        appVersionProvider.overrideWith((_) async => '1.0.0'),
        isIosProvider.overrideWithValue(isIos),
        onboardingStoreProvider.overrideWithValue(onboardingStore),
        notificationPermissionRequesterProvider.overrideWithValue(
          notifications,
        ),
        trackingAuthorizationProvider.overrideWithValue(tracking),
      ],
      child: AppLocalizationScope(
        startLocale: locale,
        child: const ChosungApp(),
      ),
    );

    // 번역 JSON 은 rootBundle 에서 실제로 읽어온다 — runAsync 안에서 첫 프레임을
    // 돌려야 그 Future 가 완료된다.
    await tester.runAsync(() async {
      await tester.pumpWidget(scope);
      await tester.pump();
    });
    await tester.pumpAndSettle();

    _container = ProviderScope.containerOf(
      tester.element(find.byType(AppLocalizationScope)),
    );
  }
}

/// 가짜 ApiClient·저장소의 Future 는 실제 이벤트 루프에서 끝난다 —
/// pumpAndSettle 만으로는 상태 변화가 들어오지 않는다.
Future<void> _tapAndSettle(WidgetTester tester, Finder finder) async {
  await tester.runAsync(() async {
    await tester.tap(finder);
    await tester.pump();
  });
  await tester.pumpAndSettle();
}

Future<void> _swipeToNextPage(WidgetTester tester) async {
  await tester.drag(find.byKey(OnboardingKeys.pages), const Offset(-400, 0));
  await tester.pumpAndSettle();
}

void main() {
  group('첫 실행', () {
    testWidgets('시작 흐름이 끝나면 홈이 아니라 온보딩 1장이 뜬다', (tester) async {
      final harness = OnboardingHarness();

      await harness.pump(tester);

      expect(find.byType(OnboardingScreen), findsOne);
      expect(find.byType(HomeShell), findsNothing);
      expect(find.text('하루 한 문제'), findsOne);
      // 1장의 가림 행(목업 e6_onboarding).
      expect(find.text('ㅈ'), findsOne);
      expect(find.text('ㅇ'), findsOne);
      // iOS 는 점 4개(ATT 안내 포함).
      expect(find.byKey(OnboardingKeys.dot(3)), findsOne);
      expect(find.byKey(OnboardingKeys.dot(4)), findsNothing);
    });

    testWidgets('다음을 누르면 2장·3장으로 넘어간다', (tester) async {
      await OnboardingHarness().pump(tester);

      await _tapAndSettle(tester, find.text('다음'));
      expect(find.text('5번의 기회'), findsOne);
      // 2장의 시도 행 — 앞 두 칸만 맞았다.
      expect(find.text('지'), findsOne);
      expect(find.text('주'), findsOne);
      expect(find.text('ㅈ'), findsNothing);

      await _tapAndSettle(tester, find.text('다음'));
      expect(find.text('매일 이어가기'), findsOne);
      expect(find.text('매일 아침 알려드릴까요?'), findsOne);
    });

    testWidgets('스와이프로도 장을 넘길 수 있다', (tester) async {
      await OnboardingHarness().pump(tester);

      await _swipeToNextPage(tester);
      expect(find.text('5번의 기회'), findsOne);

      await _swipeToNextPage(tester);
      expect(find.text('매일 이어가기'), findsOne);
    });
  });

  group('언어 칩(1장)', () {
    testWidgets('영어를 고르면 PATCH /me 가 가고 예시 타일이 영어로 바뀐다', (tester) async {
      final harness = OnboardingHarness();
      await harness.pump(tester);

      expect(find.text('ㅈ'), findsOne);

      await _tapAndSettle(
        tester,
        find.byKey(OnboardingKeys.languageChip(PuzzleLanguage.en)),
      );

      expect(harness.api.updatedPuzzleLanguages, [PuzzleLanguage.en]);
      expect(find.text('ㅈ'), findsNothing);
      expect(find.text('L'), findsOne);
      expect(find.text('P'), findsNWidgets(2));
    });

    testWidgets('언어를 바꾸지 못하면 칩 아래 한 줄로 알린다', (tester) async {
      final harness = OnboardingHarness()
        ..api.updatePuzzleLanguageError = const NetworkApiException(
          code: networkErrorCode,
          message: 'offline',
        );
      await harness.pump(tester);

      await _tapAndSettle(
        tester,
        find.byKey(OnboardingKeys.languageChip(PuzzleLanguage.en)),
      );

      expect(find.text('언어를 바꾸지 못했어요. 다시 시도해주세요'), findsOne);
      // 서버가 안 받았으면 예시도 한국어 그대로다.
      expect(find.text('ㅈ'), findsOne);
    });

    // 게스트를 처음 발급할 때 기기 언어를 보내고, 서버가 그 값을 돌려준다
    // (`/me/stats`). 칩의 기본 선택은 그 값이지 ko 고정이 아니다.
    testWidgets('기본 선택은 서버가 돌려준 퍼즐 언어다', (tester) async {
      final harness = OnboardingHarness(
        api: FakeApiClient(
          stats: fakeMyStats(puzzleLanguage: PuzzleLanguage.en),
        ),
      );

      await harness.pump(tester);

      expect(find.text('L'), findsOne);
      expect(harness.api.updatedPuzzleLanguages, isEmpty);
    });

    // 온보딩에서 고른 언어가 그 뒤 화면에도 그대로 남아야 "반영" 이다.
    testWidgets('온보딩에서 고른 언어가 S4 설정에도 그대로 보인다', (tester) async {
      final harness = OnboardingHarness(isIos: false);
      await harness.pump(tester);

      await _tapAndSettle(
        tester,
        find.byKey(OnboardingKeys.languageChip(PuzzleLanguage.en)),
      );
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('나중에'));

      expect(find.byType(HomeShell), findsOne);
      await _tapAndSettle(tester, find.text('내 기록'));

      expect(find.text('퍼즐 언어'), findsOne);
      expect(find.text('영어'), findsOne);
    });

    testWidgets('언어 칩은 1장에만 있다', (tester) async {
      await OnboardingHarness().pump(tester);

      await _tapAndSettle(tester, find.text('다음'));

      expect(
        find.byKey(OnboardingKeys.languageChip(PuzzleLanguage.ko)),
        findsNothing,
      );
    });
  });

  group('알림 사전 안내(3장)', () {
    Future<void> toNotificationPage(WidgetTester tester) async {
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
    }

    testWidgets('"알림 켜기" 를 눌러야 OS 권한을 묻고 결과가 상태로 남는다', (tester) async {
      final harness = OnboardingHarness();
      await harness.pump(tester);
      await toNotificationPage(tester);

      expect(harness.notifications.requests, 0);

      await _tapAndSettle(tester, find.text('알림 켜기'));

      expect(harness.notifications.requests, 1);
      expect(harness.notificationPermission, NotificationPermission.granted);
    });

    testWidgets('거부하면 denied 가 남는다(티켓 30 이 "알림 꺼짐" 을 띄우는 입력)', (tester) async {
      final harness = OnboardingHarness(
        notifications: FakeNotificationPermissionRequester(
          result: NotificationPermission.denied,
        ),
      );
      await harness.pump(tester);
      await toNotificationPage(tester);

      await _tapAndSettle(tester, find.text('알림 켜기'));

      expect(harness.notificationPermission, NotificationPermission.denied);
    });

    testWidgets('"나중에" 는 OS 프롬프트를 띄우지 않고 다음으로 넘어간다', (tester) async {
      final harness = OnboardingHarness();
      await harness.pump(tester);
      await toNotificationPage(tester);

      await _tapAndSettle(tester, find.text('나중에'));

      expect(harness.notifications.requests, 0);
      expect(
        harness.notificationPermission,
        NotificationPermission.notDetermined,
      );
      expect(find.text('맞춤 광고 허용'), findsOne);
    });
  });

  group('ATT 안내(iOS 만)', () {
    testWidgets('iOS 는 마지막 장에서 안내 뒤 프롬프트를 띄우고 홈으로 간다', (tester) async {
      final harness = OnboardingHarness(
        tracking: FakeTrackingAuthorization(result: TrackingStatus.denied),
      );
      await harness.pump(tester);

      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('나중에'));

      expect(find.text('맞춤 광고 허용'), findsOne);
      expect(harness.tracking.requests, 0);

      await _tapAndSettle(tester, find.text('계속'));

      expect(harness.tracking.requests, 1);
      expect(harness.trackingStatus, TrackingStatus.denied);
      expect(find.byType(HomeShell), findsOne);
      expect(find.byType(TodayTab), findsOne);
    });

    testWidgets('Android 는 ATT 안내가 없고 3장에서 끝난다', (tester) async {
      final harness = OnboardingHarness(isIos: false);
      await harness.pump(tester);

      // 점이 3개다 — ATT 안내 장이 없다.
      expect(find.byKey(OnboardingKeys.dot(2)), findsOne);
      expect(find.byKey(OnboardingKeys.dot(3)), findsNothing);

      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('알림 켜기'));

      expect(find.text('맞춤 광고 허용'), findsNothing);
      expect(harness.tracking.requests, 0);
      expect(find.byType(HomeShell), findsOne);
    });
  });

  group('완료 플래그', () {
    testWidgets('끝까지 보면 기기에 플래그가 남는다', (tester) async {
      final harness = OnboardingHarness(isIos: false);
      await harness.pump(tester);

      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('나중에'));

      expect(harness.onboardingStore.seen, isTrue);
      expect(harness.onboardingStore.writes, 1);
    });

    testWidgets('건너뛰기도 완료로 친다 — 다시 띄우지 않는다', (tester) async {
      final harness = OnboardingHarness();
      await harness.pump(tester);

      await _tapAndSettle(tester, find.text('건너뛰기'));

      expect(harness.onboardingStore.seen, isTrue);
      expect(find.byType(HomeShell), findsOne);
      expect(harness.notifications.requests, 0);
      expect(harness.tracking.requests, 0);
    });

    testWidgets('플래그가 있으면 두 번째 실행은 홈으로 직행한다', (tester) async {
      final harness = OnboardingHarness(
        onboardingStore: InMemoryOnboardingStore(seen: true),
      );

      await harness.pump(tester);

      expect(find.byType(OnboardingScreen), findsNothing);
      expect(find.byType(HomeShell), findsOne);
    });
  });

  group('설정에서 다시 보기', () {
    testWidgets('S4 "하는 법" 으로 열고 닫으면 내 기록으로 돌아온다', (tester) async {
      final harness = OnboardingHarness(
        onboardingStore: InMemoryOnboardingStore(seen: true),
      );
      await harness.pump(tester);

      await _tapAndSettle(tester, find.text('내 기록'));
      await tester.ensureVisible(find.byKey(RecordsSlot.howTo));
      await _tapAndSettle(tester, find.byKey(RecordsSlot.howTo));

      expect(find.byType(OnboardingScreen), findsOne);
      expect(find.text('하루 한 문제'), findsOne);
      // 다시 보기엔 "건너뛰기" 대신 "닫기" 가 있다 — 건너뛸 첫 실행이 아니다.
      expect(find.text('닫기'), findsOne);
      expect(find.text('건너뛰기'), findsNothing);

      await _tapAndSettle(tester, find.text('닫기'));

      expect(find.byType(RecordsTab), findsOne);
      expect(find.byType(OnboardingScreen), findsNothing);
      // 이미 true 인 플래그를 다시 쓰지 않는다.
      expect(harness.onboardingStore.writes, 0);
    });

    // 설정을 거치지 않고 /how-to 로 바로 들어오면(딥링크·상태 복원) 닫을
    // 자리가 없다. 그때도 앱이 멈추지 않고 설정으로 간다.
    testWidgets('닫을 자리가 없으면 내 기록으로 보낸다', (tester) async {
      final harness = OnboardingHarness(
        onboardingStore: InMemoryOnboardingStore(seen: true),
      );
      await harness.pump(tester);

      // go 는 스택을 통째로 바꾼다 — 설정을 거쳐 push 한 게 아니라 이 경로
      // 하나만 열린 상태가 된다.
      GoRouter.of(
        tester.element(find.byType(HomeShell)),
      ).go(AppRoutes.howTo);
      await tester.pumpAndSettle();

      expect(find.byType(OnboardingScreen), findsOne);

      await _tapAndSettle(tester, find.text('닫기'));

      expect(find.byType(RecordsTab), findsOne);
    });

    testWidgets('다시 보기에서도 마지막 장까지 가면 설정으로 돌아온다', (tester) async {
      final harness = OnboardingHarness(
        isIos: false,
        onboardingStore: InMemoryOnboardingStore(seen: true),
      );
      await harness.pump(tester);

      await _tapAndSettle(tester, find.text('내 기록'));
      await tester.ensureVisible(find.byKey(RecordsSlot.howTo));
      await _tapAndSettle(tester, find.byKey(RecordsSlot.howTo));

      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('나중에'));

      expect(find.byType(RecordsTab), findsOne);
      expect(harness.onboardingStore.writes, 0);
    });
  });

  group('접근성·테마', () {
    testWidgets('진행 상황은 점 모양이 아니라 말로도 읽힌다', (tester) async {
      final handle = tester.ensureSemantics();
      await OnboardingHarness().pump(tester);

      expect(find.bySemanticsLabel('안내 1/4'), findsOne);

      await _tapAndSettle(tester, find.text('다음'));
      expect(find.bySemanticsLabel('안내 2/4'), findsOne);

      handle.dispose();
    });

    // 레이아웃이 넘치면 RenderFlex overflow 가 FlutterError 로 잡혀 테스트가
    // 바로 실패한다. audit.native 접근성 항목.
    testWidgets('글자 크기를 1.3배로 키워도 네 장 모두 넘치지 않는다', (tester) async {
      tester.platformDispatcher.textScaleFactorTestValue = 1.3;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

      await OnboardingHarness().pump(tester);

      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('다음'));
      await _tapAndSettle(tester, find.text('나중에'));

      expect(find.text('맞춤 광고 허용'), findsOne);
    });

    testWidgets('다크 모드에서도 같은 토큰으로 그린다', (tester) async {
      tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
      addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

      await OnboardingHarness().pump(tester);

      final context = tester.element(find.byType(OnboardingScreen));
      expect(AppColors.from(context), AppColors.dark);
      expect(find.text('하루 한 문제'), findsOne);
    });

    testWidgets('기기 언어가 영어면 안내도 영어로 나온다', (tester) async {
      await OnboardingHarness().pump(tester, locale: const Locale('en'));

      expect(find.text('One puzzle a day'), findsOne);
      // 퍼즐 언어(ko)와 UI 언어(en)는 별개다 — 예시는 여전히 초성이다.
      expect(find.text('ㅈ'), findsOne);
    });
  });
}
