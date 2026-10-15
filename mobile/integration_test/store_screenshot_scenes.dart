/// 스토어 스크린샷 5장의 장면(티켓 35, OVERRIDES §8).
///
/// 장면을 integration test 와 **따로** 둔 이유: `flutter drive` 는 시뮬레이터가
/// 있어야 돌아서 CI 가 못 돈다. 장면이 위젯 트리로 떨어져 있으면 같은 장면을
/// `flutter test`(test/store/store_screenshot_scenes_test.dart)가 폰·태블릿 폭
/// 양쪽으로 띄워 보고, 스크린샷을 찍기 전에 "장면이 깨졌다" 를 CI 가 먼저 잡는다.
///
/// 규칙 네 가지:
/// - **라이트 모드 강제**(OVERRIDES §8). 기기 다크 설정과 무관하게 같은 그림이
///   나와야 한다 — `themeMode` 를 고정하고 `darkTheme` 에도 라이트를 넣는다.
/// - **데이터는 `FakeApiClient` 뿐**. 서버 경계만 가짜고 화면·테마·레이아웃은 실제
///   코드다(README "22. 테스트 경계" 와 같은 선).
/// - **기기에 남는 상태도 가짜**(`localFlagStoreProvider`). 서버가 아니라 **기기**가
///   기억하는 1회성 안내가 있어서다 — 그대로 두면 같은 스크립트가 키체인 상태에
///   따라 다른 그림을 낸다. 화면 코드는 여기서도 실제다.
/// - **배너 슬롯 없음**. 광고 자리는 구독자에게 사라지는 영역이고(OVERRIDES §5),
///   스토어 스크린샷에 빈 회색 띠를 넣을 이유가 없다.
/// - **OS·동의·시계도 가짜**(티켓 40). 광고 게이트·알림 권한·알림 설정·시계는
///   기기가 들고 있는 값이라, 그대로 두면 같은 스크립트가 시뮬레이터 상태와
///   찍는 시각에 따라 다른 그림을 낸다. 아래 `storeScreenshot*` 상수 참고.
library;

import 'package:chosung/ads/ad_gate.dart';
import 'package:chosung/ads/ad_providers.dart';
import 'package:chosung/analytics/analytics_service.dart';
import 'package:chosung/api/api_models.dart';
import 'package:chosung/api/api_providers.dart';
import 'package:chosung/app.dart';
import 'package:chosung/config/clock.dart';
import 'package:chosung/config/provider_retry.dart';
import 'package:chosung/layout/adaptive_scaffold.dart';
import 'package:chosung/local/local_flags.dart';
import 'package:chosung/notifications/notification_settings.dart';
import 'package:chosung/notifications/notification_settings_controller.dart';
import 'package:chosung/permissions/notification_permission.dart';
import 'package:chosung/screens/onboarding_screen.dart';
import 'package:chosung/screens/ranking_tab.dart';
import 'package:chosung/screens/records_tab.dart';
import 'package:chosung/screens/today_tab.dart';
import 'package:chosung/startup/startup_controller.dart';
import 'package:chosung/theme/app_theme.dart';
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../test/fakes/fake_api_client.dart';
import '../test/fakes/fake_permissions.dart';
import '../test/fakes/in_memory_local_flag_store.dart';

/// 찍을 장면. 구독(S5)은 OVERRIDES §8 의 목록에 없어서 빼 둔다.
enum StoreScene {
  /// S1 오늘 — 시도 2행이 쌓인 보드.
  home('01_home'),

  /// S2 결과 — 보드에서 "결과 보기" 를 눌러 띄운 시트/다이얼로그.
  result('02_result'),

  /// S3 순위 — 21위 밖 내 순위까지 보이는 리더보드.
  leaderboard('03_leaderboard'),

  /// S4 내 기록 — 연속 기록 + 최근 7일 + 설정.
  records('04_records'),

  /// S6 온보딩 1장 — 퍼즐 언어를 고르는 칩이 있는 장(언어 선택).
  language('06_language')
  ;

  const StoreScene(this.slug);

  /// 파일 이름에 들어가는 조각. `{locale}_{slug}.png` 로 저장된다.
  final String slug;

  /// 전역 내비게이션이 있는 셸 화면인가. 온보딩은 rail 없이 읽기 폭 가운데로만
  /// 선다(SCREENS T0) — 그래서 폭 ≥600 에서 rail 을 단언하는 대상이 아니다.
  bool get hasShell => this != StoreScene.language;
}

/// 리더보드 익명 태그. 서버는 **언어 중립 태그만** 주고 "게스트 #" / "Guest #"
/// 접두사는 화면이 자기 UI 언어로 붙인다(티켓 38, `ranking.guest`,
/// README "38.") — 그래서 같은 태그로 ko·en 을 찍으면 각 로케일의 접두사가
/// 붙은 그림이 나온다.
const _leaderboardTags = ['a3f1', '7b20', '1c08', '92de', '4f61'];

/// ko "지하철역" — `fakeKoMask` 와 같은 퍼즐이다. 시도 두 줄은 **정답과 앞뒤가
/// 맞는** 피드백이어야 한다: 스토어 스크린샷은 사람이 들여다보는 그림이라,
/// 같은 글자가 한 줄에선 초록이고 다른 줄에선 회색이면 바로 눈에 띈다.
const _koAttempts = [
  PuzzleAttempt(guess: '전화초인', feedback: [false, false, false, false]),
  PuzzleAttempt(guess: '지하철앞', feedback: [true, true, true, false]),
];

/// en "PURPLE" — 모음을 빈칸으로 둔 자음 뼈대(CONTEXT "가림").
const _enMask = [
  MaskTile(type: MaskTileType.revealed, char: 'P'),
  MaskTile(type: MaskTileType.hidden, char: ''),
  MaskTile(type: MaskTileType.revealed, char: 'R'),
  MaskTile(type: MaskTileType.revealed, char: 'P'),
  MaskTile(type: MaskTileType.revealed, char: 'L'),
  MaskTile(type: MaskTileType.hidden, char: ''),
];

const _enAttempts = [
  PuzzleAttempt(
    guess: 'PEOPLE',
    feedback: [true, false, false, true, true, true],
  ),
  PuzzleAttempt(
    guess: 'PIMPLE',
    feedback: [true, false, false, true, true, true],
  ),
];

/// 장면 하나 = 띄울 위젯 + 찍기 전에 할 조작.
class StoreScreenshotScene {
  StoreScreenshotScene({
    required this.scene,
    required this.locale,
    required this.app,
    this.revealLabelKey,
  });

  final StoreScene scene;
  final Locale locale;
  final Widget app;

  /// 장면을 완성하려고 눌러야 하는 버튼의 **번역 키**(결과 시트의 "결과 보기").
  /// 글자가 아니라 키로 들고 있는 이유: `tr()` 은 앱이 떠서 Localization 이
  /// 자리를 잡은 뒤에야 번역을 돌려준다 — 장면을 만들 때 풀면 키가 그대로 남는다.
  final String? revealLabelKey;

  String get fileName => '${locale.languageCode}_${scene.slug}';
}

/// 한 로케일의 5장. 순서가 스토어에 올라가는 순서다.
///
/// `isIos` 는 **찍는 기기의 플랫폼**이다. 온보딩 장 수가 여기서 갈려서
/// (`onboardingPages`: iOS 는 ATT 안내 1장이 더 붙는다) 고정값을 넣으면 Android
/// 에뮬레이터에서 찍어도 iPhone 구성이 나온다 — Play 는 실제 앱 경험을 보여
/// 주도록 요구한다(최종 리뷰 D-35-5).
List<StoreScreenshotScene> storeScreenshotScenes({
  required Locale locale,
  required bool isIos,
}) {
  final isKorean = locale.languageCode == 'ko';
  final language = isKorean ? PuzzleLanguage.ko : PuzzleLanguage.en;
  final mask = isKorean ? fakeKoMask : _enMask;
  final attempts = isKorean ? _koAttempts : _enAttempts;
  final answer = isKorean ? '지하철역' : 'PURPLE';

  TodayPuzzle puzzle({required bool finished}) => fakeTodayPuzzle(
    language: language,
    mask: mask,
    attemptsLeft: 3,
    attempts: finished
        ? [
            attempts.first,
            PuzzleAttempt(
              guess: answer,
              feedback: List.filled(
                mask
                    .where((tile) => tile.type != MaskTileType.separator)
                    .length,
                true,
              ),
            ),
          ]
        : attempts,
    status: finished ? PuzzleStatus.success : PuzzleStatus.inProgress,
    answer: finished ? answer : null,
  );

  FakeApiClient api({bool finished = false}) => FakeApiClient(
    config: fakeAppConfig(),
    stats: fakeMyStats(
      puzzleLanguage: language,
      currentStreak: 12,
      maxStreak: 30,
      solvedCount: 41,
    ),
    puzzle: puzzle(finished: finished),
    todayStats: fakeTodayStats(language: language),
    leaderboard: fakeLeaderboard(
      language: language,
      entries: [
        fakeLeaderboardEntry(rank: 1, anonTag: _leaderboardTags[0]),
        fakeLeaderboardEntry(
          rank: 2,
          anonTag: _leaderboardTags[1],
          seconds: 63,
        ),
        fakeLeaderboardEntry(
          rank: 3,
          anonTag: _leaderboardTags[2],
          attempts: 2,
          seconds: 95,
        ),
        fakeLeaderboardEntry(
          rank: 4,
          anonTag: _leaderboardTags[3],
          attempts: 3,
          seconds: 188,
        ),
        fakeLeaderboardEntry(
          rank: 5,
          anonTag: _leaderboardTags[4],
          attempts: 3,
          seconds: 402,
        ),
      ],
      me: const MyRank(rank: 23, attempts: 4, seconds: 754),
    ),
    history: fakeHistory(
      results: [
        for (final result in [
          DayResult.success,
          DayResult.success,
          DayResult.fail,
          DayResult.success,
          DayResult.none,
          DayResult.success,
          DayResult.inProgress,
        ])
          {language: result, _otherLanguage(language): DayResult.none},
      ],
    ),
  );

  return [
    StoreScreenshotScene(
      scene: StoreScene.home,
      locale: locale,
      app: _shell(
        scene: StoreScene.home,
        api: api(),
        locale: locale,
        isIos: isIos,
        selectedIndex: 0,
        tab: const TodayTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.result,
      locale: locale,
      app: _shell(
        scene: StoreScene.result,
        api: api(finished: true),
        locale: locale,
        isIos: isIos,
        selectedIndex: 0,
        tab: const TodayTab(),
      ),
      revealLabelKey: 'today.show_result',
    ),
    StoreScreenshotScene(
      scene: StoreScene.leaderboard,
      locale: locale,
      app: _shell(
        scene: StoreScene.leaderboard,
        api: api(),
        locale: locale,
        isIos: isIos,
        selectedIndex: 1,
        tab: const RankingTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.records,
      locale: locale,
      app: _shell(
        scene: StoreScene.records,
        api: api(),
        locale: locale,
        isIos: isIos,
        selectedIndex: 2,
        tab: const RecordsTab(),
      ),
    ),
    StoreScreenshotScene(
      scene: StoreScene.language,
      locale: locale,
      app: _root(
        scene: StoreScene.language,
        api: api(),
        locale: locale,
        isIos: isIos,
        home: const OnboardingScreen(),
      ),
    ),
  ];
}

PuzzleLanguage _otherLanguage(PuzzleLanguage language) =>
    language == PuzzleLanguage.ko ? PuzzleLanguage.en : PuzzleLanguage.ko;

/// 탭 셸 — 실제 앱의 `HomeShell` 과 같은 목록·같은 아이콘을 쓴다. 다른 점은
/// go_router 대신 탭을 직접 꽂는 것(스크린샷은 탭 이동을 찍지 않는다)과
/// 배너 슬롯이 없는 것뿐이다.
Widget _shell({
  required StoreScene scene,
  required FakeApiClient api,
  required Locale locale,
  required bool isIos,
  required int selectedIndex,
  required Widget tab,
}) => _root(
  scene: scene,
  api: api,
  locale: locale,
  isIos: isIos,
  home: Builder(
    builder: (context) => AdaptiveScaffold(
      selectedIndex: selectedIndex,
      onDestinationSelected: (_) {},
      destinations: [
        AdaptiveDestination(icon: LucideIcons.grid, label: 'tabs.today'.tr()),
        AdaptiveDestination(
          icon: LucideIcons.trophy,
          label: 'tabs.ranking'.tr(),
        ),
        AdaptiveDestination(
          icon: LucideIcons.calendar,
          label: 'tabs.records'.tr(),
        ),
      ],
      body: tab,
    ),
  ),
);

/// 스토어 장면의 로컬 플래그 저장소. **모든 1회성 안내를 "이미 봤다" 로 켜 둔다** —
/// OVERRIDES §8 의 S2 는 "결과 보기를 눌러 띄운 시트" 이고, 성장 유도 배너가 결과
/// 보드를 덮으면 스토어 그림이 핵심 경험을 덜 보여준다.
///
/// `LocalFlag.values` 를 돌려서 켜는 이유: 나중에 1회성 안내가 더 붙어도 장면이
/// 저절로 따라간다. 하나씩 적으면 새 안내가 조용히 스크린샷에 끼어든다.
LocalFlagStore storeScreenshotFlagStore() {
  final store = InMemoryLocalFlagStore();
  for (final flag in LocalFlag.values) {
    store.values[flag.key] = '1';
  }
  return store;
}

/// 장면이 쓰는 고정 시계(티켓 40). KST 19:14:41 — 결과 시트(S2)의 "다음
/// 퍼즐까지" 가 `04:45:19` 로 찍힌다.
///
/// 왜 고정하나: 카운트다운은 다음 KST 자정까지를 **지금 시각**으로 세므로,
/// 고정하지 않으면 같은 세트의 ko·en 이 몇 분 차이로 다른 숫자가 되고 밤에
/// 돌리면 `00:00:03` 같은 그림이 남는다. 퍼즐 날짜(`fakeTodayPuzzle` 10/13)와
/// 같은 날로 맞춰 둔다 — 보드의 날짜와 카운트다운이 어긋나지 않게.
DateTime storeScreenshotNow() => DateTime.utc(2026, 10, 13, 10, 14, 41);

/// 장면의 광고 게이트(티켓 40). 값을 박아 두는 이유: 게이트의 세 입력(UMP
/// 동의·ATT·구독 권한)이 전부 **기기와 세션**에서 오고, 장면은 `NoopAdService`
/// 를 쓰므로 UMP 가 늘 `failed` 로 떨어져 S1·S2 의 힌트 카드에 "지금은 광고를
/// 불러올 수 없어요" 가 박힌 채로 찍힌다(실측 2026-10-15).
///
/// 기준은 **동의를 마친 비구독자**다 — 스토어 그림의 기본 사용자다.
/// [AdGate.showsPrivacyOptions] 만 false 로 둔다: 그 행은 UMP 가
/// `privacyOptionsRequired` 를 주는 EEA 에서만 보이는 조건부 행이라, 주 시장
/// (한국·미국)의 기본 화면에는 없다(코디네이터 결정, 티켓 40).
const storeScreenshotAdGate = AdGate(
  canLoadAds: true,
  showsBannerSlot: true,
  hintPreviewNeedsAd: true,
  showsPrivacyOptions: false,
);

/// 장면의 알림 설정(티켓 40). 기본값 그대로(09:00 · 리마인더 켬)지만 **기기
/// 저장소를 타지 않고, 첫 프레임부터 값이 들어 있다**.
///
/// 저장소만 메모리로 바꾸면(`notificationSettingsStoreProvider`) 모자란다.
/// 그때도 `build()` 는 Future 라 첫 프레임이 `AsyncLoading` 이고, 리마인더
/// 스위치가 `false → true` 로 **애니메이션**한다 — `takeScreenshot` 은 기기
/// 표면을 찍어서 그 전환 중에 걸리면 꺼진 스위치가 남는다. 실측: 같은 코드로
/// 찍은 iOS 폰 4장 중 2장(`iphone69_en`·`iphone65_ko`)이 꺼진 채였고 나머지
/// 2장은 켜져 있었다(2026-10-15). [SynchronousFuture] 는 Riverpod 이
/// `then` 을 부르는 순간 값을 돌려줘서 첫 읽기가 이미 `AsyncData` 다 —
/// 상태가 바뀌지 않으니 애니메이션 자체가 없다.
class StoreScreenshotNotificationSettings extends NotificationSettingsNotifier {
  @override
  Future<NotificationSettings> build() =>
      SynchronousFuture(const NotificationSettings());
}

/// 장면의 알림 권한(티켓 40). `granted` 로 둔다 — 기본값 `notDetermined` 는
/// S4 에 "알림 꺼짐 — 시스템 설정에서 켜기" 경고 행을 끼워 넣어서, 스토어
/// 그림이 알림 2행(SCREENS S4) 대신 고장난 상태로 찍힌다.
NotificationPermissionNotifier storeScreenshotNotificationPermission() =>
    FixedNotificationPermissionNotifier(NotificationPermission.granted);

Widget _root({
  required StoreScene scene,
  required FakeApiClient api,
  required Locale locale,
  required bool isIos,
  required Widget home,
}) => ProviderScope(
  // 장면 하나 = provider 그래프 하나. 키가 없으면 장면을 잇따라 띄울 때
  // Flutter 가 같은 Element 를 재사용해서 앞 장면의 응답이 그대로 남는다.
  key: ValueKey(scene),
  retry: noAutoRetry,
  overrides: [
    apiClientProvider.overrideWithValue(api),
    startupStatsProvider.overrideWithValue(api.stats),
    analyticsServiceProvider.overrideWithValue(NoopAnalyticsService()),
    appVersionProvider.overrideWith((ref) async => '1.0.0'),
    // 온보딩 장 수는 플랫폼으로 갈린다 — 찍는 기기를 그대로 따른다.
    isIosProvider.overrideWithValue(isIos),
    // 기기에 남은 "이미 봤다" 표시도 가짜로 바꾼다. 티켓 29 가 결과 시트에 넣은
    // 계정 연결 안내는 **1회성**이라, 이 provider 를 그대로 두면 같은 스크립트가
    // 키체인 상태에 따라 다른 그림을 낸다 — 깨끗한 시뮬레이터에선 안내가 결과
    // 보드를 덮어 찍히고 두 번째 실행부터는 안 찍힌다(D-35-5·D-35-8 과 같은 부류).
    localFlagStoreProvider.overrideWithValue(storeScreenshotFlagStore()),
    // 아래 넷은 **기기·세션이 들고 있는 값**이다. 바꿔 끼우지 않으면 같은
    // 스크립트가 시뮬레이터 상태와 찍는 시각에 따라 다른 그림을 낸다
    // (티켓 40 — 위 상수들의 주석에 각각의 실측 근거가 있다).
    clockProvider.overrideWithValue(storeScreenshotNow),
    adGateProvider.overrideWithValue(storeScreenshotAdGate),
    notificationSettingsProvider.overrideWith(
      StoreScreenshotNotificationSettings.new,
    ),
    notificationPermissionProvider.overrideWith(
      storeScreenshotNotificationPermission,
    ),
  ],
  child: AppLocalizationScope(
    startLocale: locale,
    child: Builder(
      builder: (context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        // 라이트 모드 강제(OVERRIDES §8): darkTheme 에도 라이트를 넣어 둔다 —
        // themeMode 만 고정하면 플랫폼 밝기를 보는 위젯이 남을 수 있다.
        theme: appTheme(Brightness.light),
        darkTheme: appTheme(Brightness.light),
        themeMode: ThemeMode.light,
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        // 시각 표기(S4 "일일 알림")는 **기기 설정**을 탄다 — 시뮬레이터가
        // 24시간제로 맞춰져 있으면 `09:00`, 아니면 `오전 9:00` 이 찍힌다.
        // 두 로케일의 세트가 같은 표기를 쓰도록 12시간제로 고정한다(티켓 40).
        builder: (context, child) => MediaQuery.withNoTextScaling(
          child: MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(alwaysUse24HourFormat: false),
            child: child ?? const SizedBox.shrink(),
          ),
        ),
        home: home,
      ),
    ),
  ),
);
